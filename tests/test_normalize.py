"""归一化层的单元测试（纯标准库 unittest，无需网络）。

    python -m unittest discover -s tests -v
    python tests/test_normalize.py
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hd2api.normalize import (  # noqa: E402
    ImpactCalibration,
    WarClock,
    build_snapshot,
    collect_calibration_samples,
    diver_impact_sample,
    empirical_window,
    humanize_seconds,
    normalize_stats,
    planet_summary,
    steam_news_block,
    strip_markup,
)
from hd2api.reference import Reference  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# --------------------------------------------------------------------------- 夹具
# 夹具集中在 tests/fixtures.py，供本文件与 test_web.py 共用
from fixtures import (  # noqa: E402
    DEFAULT_HISTORY,
    build_test_snapshot,
    history,
    iso_ago,
    make_live,
    make_reference,
)

class TestHelpers(unittest.TestCase):
    def test_strip_markup(self):
        self.assertEqual(strip_markup("<i=3>MAJOR ORDER WON</i>\n\nWe did it."),
                         "MAJOR ORDER WON\n\nWe did it.")
        self.assertEqual(strip_markup(None), "")
        self.assertEqual(strip_markup("plain"), "plain")

    def test_humanize_seconds(self):
        self.assertEqual(humanize_seconds(None), None)
        self.assertEqual(humanize_seconds(0), "已结束")
        self.assertEqual(humanize_seconds(-5), "已结束")
        self.assertEqual(humanize_seconds(45), "45秒")
        self.assertEqual(humanize_seconds(90), "1分30秒")
        self.assertEqual(humanize_seconds(3600), "1小时0分")
        self.assertEqual(humanize_seconds(3660), "1小时1分")
        self.assertEqual(humanize_seconds(86400), "1天0小时")
        self.assertEqual(humanize_seconds(86400 + 4 * 3600), "1天4小时")

    def test_war_clock_uses_payload_offset(self):
        # clientTime 与 warTime 的差值就是固定偏移，不该用 startDate 推算
        clock = WarClock(1_700_000_000_000, 1000)
        self.assertEqual(clock.to_datetime(1000), datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc))
        self.assertEqual(clock.seconds_until(1600), 600)
        self.assertIsNone(clock.seconds_until(None))

    def test_normalize_stats(self):
        st = normalize_stats({
            "missionsWon": 100, "missionsLost": 25,
            "bugKills": 10, "automatonKills": 20, "illuminateKills": 30,
            "bulletsFired": 1000, "bulletsHit": 500, "deaths": 5, "friendlies": 1,
            "accuracy": 50.0, "accurracy": 100,
        })
        self.assertEqual(st["missions_total"], 125)
        self.assertEqual(st["kills"]["total"], 60)
        self.assertEqual(st["accuracy_percent"], 50.0)
        self.assertFalse(st["accuracy_exceeds_100"])
        self.assertEqual(st["shots_per_hit"], 2.0)
        self.assertEqual(st["kill_death_ratio"], 12.0)
        self.assertEqual(st["accidental_death_percent"], 20.0)
        # 上游口径导致的命中率 >100% 必须被标记而不是被静默修正
        st2 = normalize_stats({"bulletsFired": 100, "bulletsHit": 150})
        self.assertTrue(st2["accuracy_exceeds_100"])
        self.assertIsNone(normalize_stats(None))

    def test_diver_impact_sample_clamps_regen_at_full_health(self):
        # 满血且掌控度下降：只有绝地潜兵在起作用，不能加 regen
        a = {"health": 1000, "maxHealth": 1000, "players": 100, "regenPerSecond": 5.0}
        b = {"health": 990, "maxHealth": 1000}
        impact, players = diver_impact_sample(a, b, 900)
        self.assertEqual(players, 100)
        self.assertAlmostEqual(impact, 10.0 / 900)

    def test_diver_impact_sample_is_unobservable_at_pinned_full_health(self):
        # 满血且纹丝不动：只能推断「输出 <= regen」，必须丢弃
        a = {"health": 1000, "maxHealth": 1000, "players": 100, "regenPerSecond": 5.0}
        b = {"health": 1000, "maxHealth": 1000}
        self.assertIsNone(diver_impact_sample(a, b, 900))

    def test_diver_impact_sample_subtracts_regen_below_full(self):
        # 掌控度在涨（+4/s），说明 regen 5/s 压过了绝地潜兵：divers = 5 - 4 = 1/s
        a = {"health": 500_000, "maxHealth": 1_000_000, "players": 100, "regenPerSecond": 5.0}
        b = {"health": 503_600, "maxHealth": 1_000_000}
        impact, players = diver_impact_sample(a, b, 900)
        self.assertAlmostEqual(impact, 1.0, places=6)
        self.assertEqual(players, 100)

        # 掌控度在跌（-10/s），regen 2/s：divers = 2 + 10 = 12/s
        a2 = {"health": 500_000, "maxHealth": 1_000_000, "players": 100, "regenPerSecond": 2.0}
        b2 = {"health": 491_000, "maxHealth": 1_000_000}
        impact2, _ = diver_impact_sample(a2, b2, 900)
        self.assertAlmostEqual(impact2, 12.0, places=6)

    def test_diver_impact_sample_rejects_negative_impact(self):
        # 掌控度涨得比 regen 还快 -> divers 为负，纯属噪声，必须丢弃
        a = {"health": 500_000, "maxHealth": 1_000_000, "players": 100, "regenPerSecond": 1.0}
        b = {"health": 520_000, "maxHealth": 1_000_000}
        self.assertIsNone(diver_impact_sample(a, b, 900))

    def test_diver_impact_sample_rejects_too_short_intervals(self):
        a = {"health": 500, "maxHealth": 1000, "players": 100, "regenPerSecond": 2.0}
        b = {"health": 400, "maxHealth": 1000}
        self.assertIsNone(diver_impact_sample(a, b, 10))

    def test_calibration_falls_back_when_samples_are_thin(self):
        cal = ImpactCalibration(0.001, [(0.5, 10)])
        self.assertEqual(cal.source, "default")
        self.assertEqual(cal.value, 0.001)
        cal2 = ImpactCalibration(0.001, [(1.0, 1000), (1.0, 1000)])
        self.assertEqual(cal2.source, "measured")
        self.assertAlmostEqual(cal2.value, 0.001)


class TestEmpiricalWindow(unittest.TestCase):
    def test_picks_freshest_valid_window(self):
        h = history([
            (iso_ago(60), 900_000, 100, 5.0),
            (iso_ago(45), 890_000, 110, 5.0),
            (iso_ago(30), 880_000, 120, 5.0),
            (iso_ago(15), 870_000, 130, 5.0),
        ], 1_000_000)
        w = empirical_window(h)
        # 取最新的一对相邻采样点：30 分钟前 -> 15 分钟前
        self.assertEqual(w["from"], h["data"][-2]["timestampUtc"])
        self.assertEqual(w["to"], h["data"][-1]["timestampUtc"])
        self.assertEqual(w["health_delta"], -10_000)
        self.assertEqual(w["players"], 120)          # 窗口起点的人数
        self.assertFalse(w["regen_clamped"])
        self.assertTrue(w["diver_observable"])
        # divers = regen - net = 5 + 10000/900
        self.assertAlmostEqual(w["diver_hp_per_second"], 5.0 + 10_000 / 900, places=4)
        # 掌控度在下降 -> 解放度在上升
        self.assertLess(w["health_per_second"], 0)

    def test_health_rising_means_enemy_advancing(self):
        h = history([
            (iso_ago(30), 800_000, 100, 2.0),
            (iso_ago(15), 809_000, 100, 2.0),
        ], 1_000_000)
        w = empirical_window(h)
        self.assertGreater(w["health_per_second"], 0)   # 敌方掌控度上升
        self.assertLess(w["diver_hp_per_second"], w["regen_at_start"])  # 绝地潜兵压不过 regen

    def test_flags_clamped_regen_at_full_health(self):
        h = history([
            (iso_ago(30), 1_000_000, 100, 5.0),
            (iso_ago(15), 1_000_000, 100, 5.0),
        ], 1_000_000)
        w = empirical_window(h)
        self.assertTrue(w["regen_clamped"])
        self.assertEqual(w["health_per_second"], 0.0)
        # 满血纹丝不动 -> 绝地潜兵输出不可观测
        self.assertFalse(w["diver_observable"])

    def test_returns_none_for_thin_history(self):
        self.assertIsNone(empirical_window({}))
        self.assertIsNone(empirical_window({"data": [{"timestampUtc": iso_ago(1), "health": 1}]}))

    def test_collect_calibration_samples(self):
        h = {"data": [
            {"timestampUtc": iso_ago(30), "health": 500_000, "maxHealth": 1_000_000,
             "players": 1000, "regenPerSecond": 2.0},
            {"timestampUtc": iso_ago(15), "health": 490_000, "maxHealth": 1_000_000,
             "players": 1000, "regenPerSecond": 2.0},
        ]}
        samples = collect_calibration_samples({1: h})
        self.assertEqual(len(samples), 1)
        # divers = regen - net = 2 + 10000/900
        self.assertAlmostEqual(samples[0][0], 2.0 + 10_000 / 900, places=4)
        self.assertEqual(samples[0][1], 1000)


class TestBuildSnapshot(unittest.TestCase):
    def setUp(self):
        self.ref = make_reference()
        self.live = make_live()
        self.histories = {
            1: history([(iso_ago(30), 1_510_000, 5000, 20.0),
                        (iso_ago(15), 1_500_000, 5000, 20.0)], 2_000_000),
        }
        self.snap = build_snapshot(
            self.live, self.ref, self.histories,
            ImpactCalibration.fixed(0.0004443),
        )
        self.by_index = {p["index"]: p for p in self.snap["planets"]}

    # ---------------------------------------------------------------- 结构
    def test_snapshot_shape(self):
        for key in ("ok", "generated_at", "war", "totals", "galaxy_statistics",
                    "sectors", "planets", "campaigns", "defenses", "major_orders",
                    "space_stations", "global_events", "dispatches", "reference"):
            self.assertIn(key, self.snap)
        self.assertEqual(self.snap["war"]["war_id"], 801)
        self.assertEqual(len(self.snap["planets"]), 3)
        self.assertEqual(self.snap["reference"]["planet_count"], 3)

    def test_names_are_resolved(self):
        self.assertEqual(self.by_index[1]["name"], "AURORA BAY")
        self.assertEqual(self.by_index[1]["sector"], "Altus")
        self.assertEqual(self.by_index[1]["biome"]["zh"], "月球")
        self.assertEqual(self.by_index[1]["waypoints"], ["SUPER EARTH"])
        # 参照表里没有的索引必须有可识别兜底名，而不是 None
        for p in self.snap["planets"]:
            self.assertTrue(p["name"])
            self.assertTrue(p["sector"])

    # ---------------------------------------------------------------- 指标
    def test_liberation_and_resistance(self):
        p = self.by_index[1]
        self.assertEqual(p["liberation_percent"], 25.0)          # 1 - 1.5M/2M
        self.assertEqual(p["health_percent"], 75.0)
        self.assertEqual(p["owner"]["en"], "Automaton" if False else "Automatons")
        # regen 20/s * 3600 / 2M * 100 = 3.6 %/h
        self.assertAlmostEqual(p["resistance"]["percent_per_hour"], 3.6, places=4)
        self.assertFalse(p["is_liberated"])

    def test_human_planet_is_fully_liberated_and_gets_no_eta(self):
        p = self.by_index[0]
        self.assertTrue(p["is_liberated"])
        self.assertEqual(p["liberation_percent"], 100.0)
        self.assertIsNone(p["eta_liberation_text"])
        self.assertEqual(p["trend"], "secured")
        self.assertTrue(p["is_homeworld"])

    def test_empirical_rate_beats_estimate(self):
        p = self.by_index[1]
        self.assertEqual(p["liberation_rate"]["source"], "measured")
        # 900 秒掉 10000 血，占 2M 的 0.5% -> 0.5% / 0.25h = 2.0%/h 的解放净增速
        self.assertAlmostEqual(p["liberation_rate"]["net_percent_per_hour"], 2.0, places=3)
        self.assertEqual(p["trend"], "advancing")
        # 绝地潜兵贡献 = 净增速 + 抵抗度 = 2.0 + 3.6 = 5.6%/h
        m = p["liberation_rate"]["measured"]
        self.assertTrue(m["diver_rate_observable"])
        self.assertAlmostEqual(m["diver_rate_percent_per_hour"], 5.6, places=3)
        # 恒等式：绝地潜兵贡献 - 抵抗度 == 净增速
        self.assertAlmostEqual(
            m["diver_rate_percent_per_hour"] - p["resistance"]["percent_per_hour"],
            m["net_rate_percent_per_hour"], places=3)
        # ETA = (100-25)/2.0 h = 37.5h
        self.assertAlmostEqual(p["eta_liberation_seconds"], 37.5 * 3600, delta=1)

    def test_estimate_used_when_no_history(self):
        p = self.by_index[2]
        self.assertEqual(p["liberation_rate"]["source"], "estimated")
        self.assertIsNone(p["liberation_rate"]["measured"])
        # resistance 5*3600/1M*100 = 1.8 %/h，估算绝地潜兵贡献应为 0（无人）
        self.assertAlmostEqual(p["resistance"]["percent_per_hour"], 1.8, places=4)
        self.assertAlmostEqual(p["liberation_rate"]["estimated_net_percent_per_hour"], -1.8, places=4)

    def test_full_health_planet_reports_unobservable_diver_rate(self):
        snap = build_snapshot(
            self.live, self.ref,
            {1: history([(iso_ago(30), 2_000_000, 5000, 20.0),
                         (iso_ago(15), 2_000_000, 5000, 20.0)], 2_000_000)},
            ImpactCalibration.fixed(0.0004443),
        )
        p = next(x for x in snap["planets"] if x["index"] == 1)
        m = p["liberation_rate"]["measured"]
        self.assertTrue(m["regen_clamped"])
        self.assertFalse(m["diver_rate_observable"])
        self.assertIsNone(m["diver_rate_percent_per_hour"])
        self.assertEqual(m["net_rate_percent_per_hour"], 0.0)
        self.assertEqual(p["trend"], "contested_stalled")
        self.assertIsNone(p["eta_liberation_seconds"])
    # ---------------------------------------------------------------- 事件
    def test_defense_event_metrics(self):
        d = self.snap["defenses"][0]
        self.assertEqual(d["planet_name"], "SUPER EARTH")
        self.assertEqual(d["event_type_label"], "防御战")
        self.assertEqual(d["faction"]["en"], "Automatons")
        # 进度 = 1 - 1.5M/2M = 25%
        self.assertEqual(d["defense_progress_percent"], 25.0)
        # 等级 = ceil(1.5M/50000)=30，满级 floor(2M/50000)=40
        self.assertEqual(d["invasion_level"], {"current": 30, "max": 40})
        # 时长 1800s -> 敌方速率 3600/1800*100 = 200%/h
        self.assertAlmostEqual(d["enemy_rate_percent_per_hour"], 200.0, places=4)
        self.assertEqual(d["duration_seconds"], 1800.0)
        self.assertEqual(d["seconds_remaining"], 1200.0)
        self.assertIsNotNone(d["predicted_outcome_text"])
        self.assertIn("defense_will", d["predicted_outcome"])
        self.assertGreater(d["required_divers"], 0)
        self.assertEqual(d["time_remaining_text"], "20分0秒")

    def test_campaign_attached_to_planet(self):
        c = self.snap["campaigns"][0]
        self.assertEqual(c["planet_name"], "AURORA BAY")
        self.assertEqual(c["type_label"], "解放战役")
        self.assertEqual(c["count"], 12)
        self.assertEqual(self.by_index[1]["campaign"]["id"], 9)

    # ---------------------------------------------------------------- 汇总
    def test_totals_and_sectors(self):
        t = self.snap["totals"]
        self.assertEqual(t["players_online"], 5010)
        self.assertEqual(t["planets_total"], 3)
        self.assertEqual(t["owned_by_faction"]["Humans"], 1)
        self.assertEqual(t["owned_by_faction"]["Automatons"], 1)
        self.assertEqual(t["active_campaigns"], 1)
        self.assertEqual(t["active_defenses"], 1)

        # 两种在线人数口径含义不同，必须都对
        # 按占有者：Super Earth(Humans) 10 / Aurora Bay(Automatons) 5000
        self.assertEqual(t["players_by_owner_faction"]["Humans"], 10)
        self.assertEqual(t["players_by_owner_faction"]["Automatons"], 5000)
        # 按正在对抗的敌人：Super Earth 正被机器人打，所以那 10 人也算机器人
        self.assertEqual(t["players_by_enemy_faction"]["Automatons"], 5010)
        self.assertNotIn("Humans", t["players_by_enemy_faction"])

        sectors = {s["name"]: s for s in self.snap["sectors"]}
        self.assertEqual(sectors["Altus"]["planet_count"], 2)
        self.assertEqual(sectors["Altus"]["players"], 5000)
        self.assertAlmostEqual(sectors["Altus"]["liberated_percent"], 0.0)
        self.assertAlmostEqual(sectors["Sol"]["liberated_percent"], 100.0)

    def test_major_orders_include_open_ended(self):
        titles = {m["title"]: m for m in self.snap["major_orders"]}
        self.assertTrue(titles["TEST ORDER"]["is_active"])
        self.assertTrue(titles["TEST ORDER"]["has_announced_end"])
        self.assertEqual(titles["TEST ORDER"]["seconds_remaining"], 100.0)
        # 没有 endWarTime 但已开始的指令同样算进行中
        self.assertTrue(titles["OPEN ENDED"]["is_active"])
        self.assertFalse(titles["OPEN ENDED"]["has_announced_end"])
        self.assertIsNone(titles["OPEN ENDED"]["seconds_remaining"])
        self.assertIn("进行中", titles["OPEN ENDED"]["time_remaining_text"])
        self.assertEqual(titles["TEST ORDER"]["current_phase"]["intro_message"], "hello world")

    def test_regions_and_effects(self):
        p = self.by_index[1]
        self.assertEqual(len(p["regions"]), 1)
        r = p["regions"][0]
        self.assertEqual(r["name"], "BATU BELIG")
        self.assertEqual(r["size_zh"], "城市")
        self.assertEqual(r["health_percent"], 100.0)
        # 上游字段名拼写就是 regerPerSecond
        self.assertEqual(r["regen_per_second"], 2.0)
        self.assertEqual(r["players"], 120)
        # 效果：既有原始 ID，也有可读名称
        self.assertEqual(p["active_effect_ids"], [1190])
        self.assertEqual(p["active_effects"][0]["id"], 1190)
        self.assertEqual(p["active_effects"][0]["slug"], "mark_Hidden")
        self.assertEqual(p["active_effects"][0]["label"], "Hidden")
        self.assertEqual(p["active_effects"][0]["category"], "设施 / 标记")

    def test_unknown_effect_degrades_to_bare_id(self):
        live = make_live()
        live["warStatus"]["planetActiveEffects"] = [{"index": 1, "galacticEffectId": 999999}]
        snap = build_snapshot(live, self.ref, {}, ImpactCalibration.fixed(0.0004443))
        p = next(x for x in snap["planets"] if x["index"] == 1)
        self.assertEqual(p["active_effect_ids"], [999999])
        self.assertEqual(p["active_effects"], [
            {"id": 999999, "slug": None, "label": None, "category": None}])

    def test_enemy_faction_reflects_who_you_fight(self):
        # Super Earth 是己方星球但正被机器人攻击 -> 交战对象是机器人
        self.assertEqual(self.by_index[0]["owner"]["en"], "Humans")
        self.assertEqual(self.by_index[0]["enemy_faction"]["en"], "Automatons")
        self.assertTrue(self.by_index[0]["is_under_attack"])
        # Aurora Bay 是机器人占有的星球，没有事件 -> 交战对象就是占有者
        self.assertEqual(self.by_index[1]["enemy_faction"]["en"], "Automatons")
        self.assertFalse(self.by_index[1]["is_under_attack"])
        # Terminid 星球
        self.assertEqual(self.by_index[2]["enemy_faction"]["en"], "Terminids")

    def test_statistics_attached_and_sentinels_dropped(self):
        p = self.by_index[1]
        self.assertEqual(p["statistics"]["missions_won"], 50)
        self.assertEqual(p["statistics"]["kills"]["total"], 6)
        self.assertNotIn(-1337, self.by_index)

    def test_dispatches_sorted_newest_first_and_markup_stripped(self):
        d = self.snap["dispatches"]
        self.assertEqual([x["id"] for x in d], [2, 1])
        self.assertEqual(d[1]["message"], "MAJOR ORDER WON\n\nWe did it.")
        self.assertIn("<i=3>", d[1]["message_raw"])

    def test_space_station_merges_rich_and_lean_sources(self):
        st = self.snap["space_stations"][0]
        self.assertEqual(st["planet_name"], "SUPER EARTH")
        # 战术行动只存在于顶层条目
        self.assertEqual(st["tactical_actions"][0]["name"], "EAGLE STORM")
        self.assertEqual(st["tactical_actions"][0]["status_label"], "已激活")
        self.assertEqual(st["tactical_actions"][0]["effect_ids"], [1, 2])
        self.assertEqual(st["tactical_actions"][0]["cost"][0]["item_mix_id"], 3992382197)
        # activeEffectIds 只存在于 warStatus.spaceStations，必须被合并进来
        self.assertEqual(st["active_effect_ids"], [1209, 1212])
        self.assertEqual(self.snap["global_events"][0]["message"], "hi there")

    def test_status_labels(self):
        self.assertEqual(self.by_index[0]["status"], "防御中")  # 有事件优先
        self.assertEqual(self.by_index[1]["status"], "解放中")
        self.assertEqual(self.by_index[2]["status"], "被占领")

    def test_summary_projection(self):
        s = planet_summary(self.by_index[1])
        for key in ("index", "name", "sector", "players", "liberation_percent",
                    "liberation_rate_percent_per_hour", "trend", "resistance_percent_per_hour"):
            self.assertIn(key, s)
        self.assertNotIn("regions", s)
        full = planet_summary(self.by_index[1], full=True)
        self.assertIn("regions", full)
        self.assertIn("statistics", full)


class TestTrendAndFloorClamping(unittest.TestCase):
    """趋势标签与「解放度不可能低于 0」的夹取逻辑。"""

    def setUp(self):
        self.ref = make_reference()
        self.live = make_live()

    def build(self, histories=None, hp_per_diver=0.0004443, live=None):
        cal = ImpactCalibration.fixed(hp_per_diver)
        return build_snapshot(live or self.live, self.ref, histories or {}, cal)

    def planet(self, snap, index):
        return next(p for p in snap["planets"] if p["index"] == index)

    def test_secured_planet_has_no_liberation_rate(self):
        p = self.planet(self.build(), 0)
        self.assertEqual(p["trend"], "secured")
        self.assertEqual(p["liberation_rate"]["net_percent_per_hour"], 0.0)
        self.assertEqual(p["liberation_rate"]["source"], "not_applicable")
        self.assertIsNone(p["liberation_rate"]["estimated_net_percent_per_hour"])
        self.assertIsNone(p["liberation_rate"]["estimated_diver_percent_per_hour"])

    def test_full_enemy_control_with_nobody_is_not_losing(self):
        """敌方掌控度顶格且无人进攻时，不该报「被反推」。"""
        p = self.planet(self.build(), 2)
        self.assertEqual(p["liberation_percent"], 0.0)
        self.assertEqual(p["players"], 0)
        self.assertEqual(p["trend"], "uncontested")
        self.assertEqual(p["liberation_rate"]["net_percent_per_hour"], 0.0)
        # 未夹取的模型值仍然保留，便于排查
        self.assertAlmostEqual(
            p["liberation_rate"]["unclamped_net_percent_per_hour"], -1.8, places=4)
        self.assertTrue(p["liberation_rate"]["clamped_at_enemy_floor"])

    def test_partial_progress_planet_can_lose_ground(self):
        """已经打下一部分却在下滑，这才是真正的「被反推」。"""
        live = make_live()
        live["warStatus"]["planetStatus"][1]["players"] = 10
        p = self.planet(self.build(live=live), 1)
        self.assertGreater(p["liberation_percent"], 0)
        self.assertEqual(p["trend"], "losing")
        self.assertLess(p["liberation_rate"]["net_percent_per_hour"], 0)
        self.assertFalse(p["liberation_rate"]["clamped_at_enemy_floor"])

    def test_defense_coverage_ratio_matches_outcome(self):
        d = self.build()["defenses"][0]
        self.assertIn("diver_coverage_ratio", d)
        ratio = d["diver_coverage_ratio"]
        self.assertIsNotNone(ratio)
        if ratio >= 1.0:
            self.assertEqual(d["predicted_outcome"], "defense_will_hold")
        elif ratio >= 0.8:
            self.assertEqual(d["predicted_outcome"], "too_close_to_call")
        else:
            self.assertEqual(d["predicted_outcome"], "defense_will_fail")

    def test_defense_hold_when_overwhelming_force(self):
        # 该夹具的防御战要求 225%/h（因为合成事件只有 30 分钟）。
        # 2M HP 的星球要产出 225%/h 需要 4.5M HP/h；按 0.05 HP/s/人 = 180 HP/h/人，
        # 需要 25,000 人，这里给 50,000 人以制造「稳守」局面。
        live = make_live()
        live["warStatus"]["planetStatus"][0]["players"] = 50_000
        cal = ImpactCalibration.fixed(0.05)
        snap = build_snapshot(live, self.ref, {}, cal)
        d = snap["defenses"][0]
        self.assertAlmostEqual(d["required_rate_percent_per_hour"], 225.0, places=2)
        self.assertGreaterEqual(d["diver_coverage_ratio"], 1.0)
        self.assertEqual(d["predicted_outcome"], "defense_will_hold")
        self.assertGreater(d["diver_surplus"], 0)

    def test_coverage_ratio_is_null_when_required_rate_is_zero(self):
        live = make_live()
        live["warStatus"]["planetEvents"][0]["health"] = 0  # 已 100% 防住
        snap = build_snapshot(live, self.ref, {},
                              ImpactCalibration.fixed(0.0004443))
        d = snap["defenses"][0]
        self.assertEqual(d["defense_progress_percent"], 100.0)
        self.assertIsNone(d["diver_coverage_ratio"])
        self.assertEqual(d["predicted_outcome"], "unknown")


class TestImpactVsNetRate(unittest.TestCase):
    """官网卡片上的「planetary control impact per hour」是绝地潜兵贡献，不是净增速。

    两个量的区别在抵抗度大的星球上才会显现，所以这里专门造一颗高抵抗的星球来区分。
    """

    def setUp(self):
        self.ref = make_reference()
        self.live = make_live()

    def build(self, histories=None, hp_per_diver=0.0004443):
        cal = ImpactCalibration.fixed(hp_per_diver)
        return build_snapshot(self.live, self.ref, histories or {}, cal)

    def planet(self, snap, index):
        return next(p for p in snap["planets"] if p["index"] == index)

    def test_impact_is_non_negative_while_net_can_be_negative(self):
        # Aurora Bay：2M 血，抵抗 20/秒 = 3.6%/h。让血几乎不动 -> 净增速为负。
        h = {1: history([(iso_ago(30), 1_500_000, 5000, 20.0),
                         (iso_ago(15), 1_517_000, 5000, 20.0)], 2_000_000)}
        p = self.planet(self.build(h), 1)
        lr = p["liberation_rate"]
        # 掌控度上升 17000/900 = 18.9 HP/s，regen 20 HP/s -> 绝地潜兵只有 1.1 HP/s
        self.assertGreater(lr["impact_percent_per_hour"], 0)
        self.assertLess(lr["net_percent_per_hour"], 0)
        self.assertEqual(lr["impact_source"], "measured")
        # 恒等式：贡献 - 抵抗度 == 净增速
        self.assertAlmostEqual(
            lr["impact_percent_per_hour"] - p["resistance"]["percent_per_hour"],
            lr["net_percent_per_hour"], places=3)

    def test_impact_matches_measured_diver_rate(self):
        h = {1: history([(iso_ago(30), 1_510_000, 5000, 20.0),
                         (iso_ago(15), 1_500_000, 5000, 20.0)], 2_000_000)}
        lr = self.planet(self.build(h), 1)["liberation_rate"]
        self.assertEqual(lr["impact_percent_per_hour"],
                         lr["measured"]["diver_rate_percent_per_hour"])
        self.assertEqual(lr["impact_source"], "measured")

    def test_impact_falls_back_to_estimate_without_history(self):
        p = self.planet(self.build(), 1)
        lr = p["liberation_rate"]
        self.assertEqual(lr["impact_source"], "estimated")
        self.assertIsNone(lr["measured"])
        # 5000 人 × 0.0004443 × 3600 / 2M × 100
        self.assertAlmostEqual(lr["impact_percent_per_hour"], 0.3999, places=3)
        # 净 = 贡献 - 抵抗(3.6)
        self.assertAlmostEqual(lr["net_percent_per_hour"],
                               lr["impact_percent_per_hour"] - 3.6, places=3)

    def test_secured_planet_has_zero_impact(self):
        p = self.planet(self.build(), 0)
        self.assertEqual(p["liberation_rate"]["impact_percent_per_hour"], 0.0)
        self.assertEqual(p["liberation_rate"]["impact_source"], "not_applicable")


class TestRateSmoothing(unittest.TestCase):
    """单窗口噪声大，1 小时平滑值应当更稳。"""

    def setUp(self):
        self.ref = make_reference()
        self.live = make_live()

    def build(self, histories):
        return build_snapshot(self.live, self.ref, histories,
                              ImpactCalibration.fixed(0.0004443))

    def test_empirical_windows_are_chronological(self):
        from hd2api.normalize import empirical_windows
        h = history([(iso_ago(60), 900_000, 100, 5.0),
                     (iso_ago(45), 890_000, 110, 5.0),
                     (iso_ago(30), 880_000, 120, 5.0),
                     (iso_ago(15), 870_000, 130, 5.0)], 1_000_000)
        ws = empirical_windows(h)
        self.assertEqual(len(ws), 3)
        times = [w["from"] for w in ws]
        self.assertEqual(times, sorted(times))
        self.assertEqual(ws[-1]["health_delta"], -10_000)

    def test_empirical_window_equals_last_of_windows(self):
        from hd2api.normalize import empirical_window, empirical_windows
        h = history([(iso_ago(45), 900_000, 100, 5.0),
                     (iso_ago(30), 890_000, 110, 5.0),
                     (iso_ago(15), 880_000, 120, 5.0)], 1_000_000)
        self.assertEqual(empirical_window(h), empirical_windows(h)[-1])

    def test_smoothed_averages_multiple_windows(self):
        h = {1: history([(iso_ago(60), 1_530_000, 5000, 20.0),
                         (iso_ago(45), 1_520_000, 5000, 20.0),
                         (iso_ago(30), 1_510_000, 5000, 20.0),
                         (iso_ago(15), 1_500_000, 5000, 20.0)], 2_000_000)}
        lr = self.build(h)["planets"][1]["liberation_rate"]
        sm = lr["smoothed"]
        self.assertIsNotNone(sm)
        self.assertEqual(sm["windows"], 3)
        self.assertEqual(sm["observable_windows"], 3)
        # 3 个窗口都是 900s、各掉 10000 血 -> 净增速恒为 2%/h
        self.assertAlmostEqual(sm["net_percent_per_hour"], 2.0, places=3)
        # 贡献 = 净 + 抵抗 = 2.0 + 3.6
        self.assertAlmostEqual(sm["impact_percent_per_hour"], 5.6, places=3)
        self.assertAlmostEqual(sm["players_avg"], 5000, places=1)
        self.assertAlmostEqual(sm["window_seconds"], 2700, places=0)

    def test_smoothing_is_more_stable_than_single_window(self):
        # 造一段速率抖动的历史：最新窗口特别快，前面几个慢
        h = {1: history([(iso_ago(75), 1_600_000, 5000, 20.0),
                         (iso_ago(60), 1_590_000, 5000, 20.0),   # -10000
                         (iso_ago(45), 1_580_000, 5000, 20.0),   # -10000
                         (iso_ago(30), 1_570_000, 5000, 20.0),   # -10000
                         (iso_ago(15), 1_520_000, 5000, 20.0)],  # -50000 突发
                        2_000_000)}
        lr = self.build(h)["planets"][1]["liberation_rate"]
        latest = lr["measured"]["net_rate_percent_per_hour"]
        smooth = lr["smoothed"]["net_percent_per_hour"]
        self.assertAlmostEqual(latest, 10.0, places=2)      # 突发窗口
        self.assertAlmostEqual(smooth, 4.0, places=2)       # 4 窗口平均
        # 平滑值必然落在各窗口之间，不会跟着突发跑
        self.assertLess(smooth, latest)

    def test_smoothed_is_none_without_history(self):
        snap = self.build({})
        self.assertIsNone(snap["planets"][1]["liberation_rate"]["smoothed"])

    def test_summary_exposes_both_rates(self):
        h = {1: history([(iso_ago(30), 1_510_000, 5000, 20.0),
                         (iso_ago(15), 1_500_000, 5000, 20.0)], 2_000_000)}
        p = self.build(h)["planets"][1]
        s = planet_summary(p)
        self.assertIn("impact_percent_per_hour", s)
        self.assertIn("liberation_rate_percent_per_hour", s)
        self.assertEqual(s["impact_percent_per_hour"],
                         p["liberation_rate"]["impact_percent_per_hour"])
        self.assertEqual(s["liberation_rate_percent_per_hour"],
                         p["liberation_rate"]["net_percent_per_hour"])


class TestSteamNews(unittest.TestCase):
    def test_block(self):
        block = steam_news_block({"appnews": {"newsitems": [
            {"gid": "1", "title": "A", "url": "u", "author": "x",
             "contents": "<b>hi</b>", "feedlabel": "f", "date": 1_700_000_000},
            {"gid": "2", "title": "B", "url": "u2", "author": "y",
             "contents": "plain", "feedlabel": "f", "date": 1_700_100_000},
        ]}})
        self.assertEqual(block["count"], 2)
        self.assertEqual(block["items"][0]["title"], "B")
        self.assertEqual(block["items"][1]["contents"], "hi")
        self.assertIsNone(steam_news_block(None)["items"] or None)


class TestReferenceIntegrity(unittest.TestCase):
    """对随仓库发布的真实参照表做完整性检查。"""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(ROOT, "data", "reference.json")
        if not os.path.exists(path):
            raise unittest.SkipTest("data/reference.json 不存在")
        cls.ref = Reference(path)

    def test_counts(self):
        self.assertGreaterEqual(self.ref.planet_count, 262)
        self.assertGreaterEqual(self.ref.sector_count, 50)

    def test_every_planet_has_name_sector_biome(self):
        for index, p in self.ref.planets().items():
            self.assertTrue(p.get("name"), f"planet {index} 缺少名称")
            self.assertTrue(p.get("sector"), f"planet {index} 缺少星区")
            self.assertTrue((p.get("biome") or {}).get("en"), f"planet {index} 缺少生物群系")

    def test_hashes_are_unique(self):
        hashes = [p["hash"] for p in self.ref.planets().values() if p.get("hash")]
        self.assertEqual(len(hashes), len(set(hashes)), "settingsHash 出现重复，参照表可能错位")

    def test_sector_membership_is_consistent(self):
        for name, sec in self.ref.sectors().items():
            for index in sec["planets"]:
                self.assertEqual(self.ref.sector_of(index), name)

    def test_faction_table(self):
        self.assertEqual(self.ref.faction(1)["zh"], "超级地球")
        self.assertEqual(self.ref.faction(2)["en"], "Terminids")
        self.assertEqual(self.ref.faction(3)["en"], "Automatons")
        self.assertEqual(self.ref.faction(4)["en"], "Illuminate")
        self.assertEqual(self.ref.faction(99)["en"], "None")

    def test_planet_lookup_by_hash_helper(self):
        p = self.ref.planet(0)
        self.assertIsNotNone(p)
        self.assertEqual(p["name"], "SUPER EARTH")


if __name__ == "__main__":
    unittest.main(verbosity=2)
