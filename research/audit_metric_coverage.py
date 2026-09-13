"""逐条核对用户列出的战报指标是否都已暴露，并打印真实数值。

    python research/audit_metric_coverage.py

对应需求原文：
「55个星区和262颗星球的详细状况，包括区域内的绝地潜兵在线数、解放程度、星球所属区域、
占领星球的阵营、星球的环境参数、敌人变种、解放战役进度、解放度、解放度每小时增长速度、
星球影响系数、敌人抵抗度、防御战役双方的推进速度、敌人入侵等级、需要的增援量、
防御战役预测胜利/失败、已完成的任务数、失败的任务数、总开火数、总命中数、开火/击中比、
击杀/死亡比、三大敌对阵营的击杀数、绝地潜兵死亡数、意外阵亡数、银河影响系数」
"""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8808"


def get(path, timeout=120):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        with e:
            raise SystemExit(f"{path} -> HTTP {e.code}: {e.read()[:200]!r}")


def dig(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if cur is None:
            return None
        cur = cur.get(part) if isinstance(cur, dict) else None
    if isinstance(cur, list):
        cur = cur[0] if cur else None
    return cur


def main() -> int:
    print(f"目标: {BASE}\n")

    war = get("/api/v1/war")
    planets = get("/api/v1/planets?limit=2000")["planets"]
    sectors = get("/api/v1/sectors")["sectors"]
    defenses = get("/api/v1/defenses")["defenses"]
    campaigns = get("/api/v1/campaigns")["campaigns"]

    busiest = max(planets, key=lambda p: p["players"])
    # 速率类指标要挑一颗「敌方占有且有人在打」的星球，否则己方星球恒为 0，看不出东西
    contested = [p for p in planets if not p["is_liberated"] and p["players"] > 0]
    rate_sample = max(contested, key=lambda p: p["players"]) if contested else busiest
    # 挑一颗有可读效果的星球
    with_effects = next((p for p in planets if p.get("active_effects")), None)
    defense = defenses[0] if defenses else None
    region_planet = next((p for p in planets if p.get("regions")), None)

    # (需求条目, API 字段路径, 取数对象, 说明)
    rows = [
        ("星区数量", "len(sectors)", len(sectors), f"{len(sectors)} 个星区"),
        ("星球数量", "len(planets)", len(planets), f"{len(planets)} 颗（含超级地球等特殊星球）"),
        ("区域内的潜兵在线数", "planets[].regions[].players",
         dig(region_planet, "regions.players"),
         f"{region_planet['name']} / {region_planet['regions'][0]['name']}"),
        ("区域控制度", "planets[].regions[].controlled_percent",
         dig(region_planet, "regions.controlled_percent"), ""),
        ("解放程度（解放度）", "planets[].liberation_percent",
         busiest["liberation_percent"], busiest["name"]),
        ("星球所属区域", "planets[].sector", busiest["sector"], busiest["name"]),
        ("占领星球的阵营", "planets[].owner.zh", busiest["owner"]["zh"], busiest["name"]),
        ("交战对象阵营", "planets[].enemy_faction.zh",
         busiest["enemy_faction"]["zh"], "与站点 playerCountXXX 同口径"),
        ("星球环境参数（生物群系）", "planets[].biome",
         f"{busiest['biome']['en']} / {busiest['biome']['zh']}", ""),
        ("环境危害", "planets[].hazards",
         ", ".join(h["zh"] for h in busiest.get("hazards") or []) or "（无）", ""),
        ("敌人变种 / 星球生效效果", "planets[].active_effects[].label + .category",
         ", ".join(f"{e['label']}（{e['category'] or '未分类'}）"
                   for e in (with_effects or {}).get("active_effects") or []) or "（无）",
         f"星球 = {(with_effects or {}).get('name', '?')}；"
         f"game_/pawn_ 成对出现，是同一变种的玩法效果与刷怪效果"),
        ("解放战役进度", "planets[].campaign.count",
         dig(busiest, "campaign.count"), "战役等级"),
        ("解放度每小时增长速度", "liberation_rate.net_percent_per_hour",
         rate_sample["liberation_rate"]["net_percent_per_hour"],
         f"{rate_sample['name']}；官网卡片同口径为 "
         f"impact_percent_per_hour={rate_sample['liberation_rate']['impact_percent_per_hour']}"),
        ("星球影响系数（抵抗度）", "planets[].resistance.percent_per_hour",
         rate_sample["resistance"]["percent_per_hour"], rate_sample["name"]),
        ("防御战役敌方推进速度", "defenses[].enemy_rate_percent_per_hour",
         defense and defense["enemy_rate_percent_per_hour"], defense and defense["planet_name"]),
        ("防御战役我方推进速度", "defenses[].estimated_diver_rate_percent_per_hour",
         defense and defense["estimated_diver_rate_percent_per_hour"], ""),
        ("敌人入侵等级", "defenses[].invasion_level",
         defense and f"{defense['invasion_level']['current']}/{defense['invasion_level']['max']}",
         defense and defense["planet_name"]),
        ("需要的增援量", "defenses[].required_divers",
         defense and defense["required_divers"], defense and f"当前 {defense['players']}"),
        ("防御预测胜利/失败", "defenses[].predicted_outcome_text",
         defense and defense["predicted_outcome_text"],
         defense and f"覆盖比 {defense.get('diver_coverage_ratio')}"),
        ("已完成的任务数", "galaxy_statistics.missions_won",
         war["galaxy_statistics"]["missions_won"], ""),
        ("失败的任务数", "galaxy_statistics.missions_lost",
         war["galaxy_statistics"]["missions_lost"], ""),
        ("总开火数", "galaxy_statistics.bullets_fired",
         war["galaxy_statistics"]["bullets_fired"], ""),
        ("总命中数", "galaxy_statistics.bullets_hit",
         war["galaxy_statistics"]["bullets_hit"], ""),
        ("开火/击中比", "galaxy_statistics.shots_per_hit",
         war["galaxy_statistics"]["shots_per_hit"],
         f"命中率 {war['galaxy_statistics']['accuracy_percent']}%"),
        ("击杀/死亡比", "galaxy_statistics.kill_death_ratio",
         war["galaxy_statistics"]["kill_death_ratio"], ""),
        ("三大敌对阵营击杀数", "galaxy_statistics.kills",
         "/".join(f"{k}={v:,}" for k, v in war["galaxy_statistics"]["kills"].items()
                  if k != "total"), f"合计 {war['galaxy_statistics']['kills']['total']:,}"),
        ("绝地潜兵死亡数", "galaxy_statistics.deaths",
         war["galaxy_statistics"]["deaths"], ""),
        ("意外阵亡数", "galaxy_statistics.accidental_deaths",
         war["galaxy_statistics"]["accidental_deaths"],
         f"占死亡 {war['galaxy_statistics']['accidental_death_percent']}%"),
        ("银河影响系数", "war.galactic_impact_multiplier",
         war["war"]["galactic_impact_multiplier"], ""),
    ]

    missing = []
    print("%-24s %-46s %s" % ("需求条目", "API 字段", "真实取值"))
    print("-" * 110)
    for label, path, value, note in rows:
        ok = value is not None and value != ""
        if not ok:
            missing.append(label)
        shown = value
        if isinstance(shown, float):
            shown = round(shown, 6)
        elif isinstance(shown, int):
            shown = f"{shown:,}"
        print("%-24s %-46s %s%s"
              % (label, path, "（缺失）" if not ok else shown,
                 f"   [{note}]" if note else ""))

    print()
    print("=" * 110)
    print(f"共 {len(rows)} 项指标，缺失 {len(missing)} 项")
    for m in missing:
        print("  !!", m)

    # 额外：效果名称表规模
    ref = get("/api/v1/reference")
    print(f"\n参照表: {ref['planet_count']} 星球 / {ref['sector_count']} 星区 "
          f"/ 效果名称 {ref.get('effect_count', 'n/a')} 条")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
