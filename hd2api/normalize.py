"""归一化层：把游戏内 ID 构成的原始载荷翻译成人类可读的战报。

设计原则
--------
1. **不改动上游语义**：只做 ID→文本、原始值→百分比/时长的换算，不臆造数据。
2. **每个派生指标都可追溯**：给出所用公式的字段来源，缺失数据一律返回 null 而不是 0。
3. **单位统一**：所有速率都是「百分比/小时」，所有时长都是「秒」，并附带可读文本。

公式出处（反编译自 helldiverscompanion 线上包，见 README）
--------------------------------------------------------
* 解放度          progress = (1 - health / maxHealth) * 100
* 抵抗度（敌方）  resistance%/h = regenPerSecond * 3600 / maxHealth * 100
* 入侵/战役等级   level = ceil(health / 50000)，满级 = floor(maxHealth / 50000)
* 防御战敌方速率  enemy%/h = 3600 / (expireTime - startTime) * 100
* 防御战所需速率  required%/h = (1 - progressFraction) / secondsRemaining * 3600 * 100
* 每绝地潜兵影响力  由 CDN 历史实测标定: impact = (Δhealth/Δt + regen) HP/秒
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from .reference import (
    CAMPAIGN_TYPE_LABEL,
    DSS_ACTION_STATUS_LABEL,
    EFFECT_TYPE_LABEL,
    EPISODE_STATUS_LABEL,
    EVENT_TYPE_LABEL,
    Reference,
)
from . import config

# --------------------------------------------------------------------------- 常量
INVASION_LEVEL_DIVISOR = 50_000
DEFAULT_MAX_HEALTH = 1_000_000
HOUR = 3600.0
# 平滑速率所用的回看时长。单个 15 分钟窗口噪声约 ±12%，
# 用 1 小时（约 4 个窗口）能显著压下来。
RATE_SMOOTHING_SECONDS = 3600.0

_MARKUP_RE = re.compile(r"<[^>]{0,40}>")


# --------------------------------------------------------------------------- 小工具
def _num(value: Any, default: float | None = None) -> float | None:
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    n = _num(value)
    return default if n is None else int(n)


def _round(value: float | None, nd: int = 4) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return round(value, nd)


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return a / b


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def strip_markup(text: str | None) -> str:
    """去掉游戏内富文本标记，例如 `<i=3>MAJOR ORDER WON</i>`。"""
    if not text:
        return ""
    out = _MARKUP_RE.sub("", text)
    out = out.replace("\\r\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    return out.strip()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def humanize_seconds(seconds: float | None) -> str | None:
    """把秒数变成「3天4小时」这类中文短语。"""
    if seconds is None:
        return None
    if seconds <= 0:
        return "已结束"
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}天{hours}小时"
    if hours:
        return f"{hours}小时{minutes}分"
    if minutes:
        return f"{minutes}分{rem % 60}秒"
    return f"{rem}秒"


# --------------------------------------------------------------------------- 战场时钟
class WarClock:
    """把 warTime 换算成真实 UTC 时间。

    载荷同时给出 `clientTime`（毫秒时间戳）与 `warStatus.time`（warTime 秒），
    两者的差值就是固定偏移量，因此任何 warTime 都能还原成绝对时间。
    这比用 warInfo.startDate 推算可靠（战争期间 warTime 会暂停）。
    """

    def __init__(self, client_time_ms: Any, war_time: Any) -> None:
        self.client_time = _num(client_time_ms)
        self.war_time = _num(war_time) or 0.0
        self.offset = None
        if self.client_time is not None:
            self.offset = self.client_time / 1000.0 - self.war_time

    def to_datetime(self, war_time: Any) -> datetime | None:
        wt = _num(war_time)
        if wt is None or self.offset is None:
            return None
        return datetime.fromtimestamp(self.offset + wt, tz=timezone.utc)

    def to_iso(self, war_time: Any) -> str | None:
        return iso(self.to_datetime(war_time))

    def seconds_until(self, war_time: Any) -> float | None:
        wt = _num(war_time)
        if wt is None:
            return None
        return wt - self.war_time

    @property
    def now(self) -> datetime | None:
        return self.to_datetime(self.war_time)


# --------------------------------------------------------------------------- 统计
_STAT_FIELDS = {
    "missionsWon": "missions_won",
    "missionsLost": "missions_lost",
    "missionTime": "mission_time_seconds",
    "bugKills": "terminid_kills",
    "automatonKills": "automaton_kills",
    "illuminateKills": "illuminate_kills",
    "bulletsFired": "bullets_fired",
    "bulletsHit": "bullets_hit",
    "timePlayed": "time_played_seconds",
    "deaths": "deaths",
    "revives": "revives",
    "friendlies": "accidental_deaths",
    "missionSuccessRate": "mission_success_rate",
}

# 这些字段本质是计数/时长，序列化成 1034241264 比 1034241264.0 可读得多
_INT_STAT_FIELDS = {
    "missions_won", "missions_lost", "missions_total", "mission_time_seconds",
    "terminid_kills", "automaton_kills", "illuminate_kills",
    "bullets_fired", "bullets_hit", "time_played_seconds",
    "deaths", "revives", "accidental_deaths",
}


def normalize_stats(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    """把 warStats 的字段名与拼写错误（accurracy）整理成规范的战报结构。"""
    if not raw:
        return None
    out: dict[str, Any] = {}
    for src, dst in _STAT_FIELDS.items():
        if src in raw:
            value = _num(raw[src])
            if value is not None and dst in _INT_STAT_FIELDS:
                value = int(value)
            out[dst] = value

    won = out.get("missions_won")
    lost = out.get("missions_lost")
    if won is not None or lost is not None:
        out["missions_total"] = (won or 0) + (lost or 0)
    rate = _safe_div(won, out.get("missions_total"))
    if rate is not None:
        out["mission_success_rate_calc"] = _round(rate * 100, 4)

    kills = {
        "terminids": out.get("terminid_kills"),
        "automatons": out.get("automaton_kills"),
        "illuminate": out.get("illuminate_kills"),
    }
    if any(v is not None for v in kills.values()):
        kills["total"] = sum(int(v or 0) for v in kills.values())
    out["kills"] = kills

    fired, hit = out.get("bullets_fired"), out.get("bullets_hit")
    acc = _safe_div(hit, fired)
    if acc is not None:
        out["accuracy_percent"] = _round(acc * 100, 4)
        # 上游的 bulletsHit 统计口径使命中数可能大于开火数（>100%），
        # 这是游戏自身计数器的特性，不是我们算错了，因此显式标注。
        out["accuracy_exceeds_100"] = acc > 1.0
    shots_per_hit = _safe_div(fired, hit)
    if shots_per_hit is not None:
        out["shots_per_hit"] = _round(shots_per_hit, 4)

    deaths = out.get("deaths")
    total_kills = kills.get("total")
    if deaths and total_kills is not None:
        out["kill_death_ratio"] = _round(total_kills / deaths, 4)

    acc_deaths = out.get("accidental_deaths")
    if deaths and acc_deaths is not None:
        out["accidental_death_percent"] = _round(acc_deaths / deaths * 100, 4)

    if "time_played_seconds" in out:
        out["time_played_hours"] = _round((out["time_played_seconds"] or 0) / HOUR, 2)

    # 上游原样保留的、语义可疑的字段（accuracy>100、revives=2）另立一处
    out["raw_gamemode_accuracy"] = _num(raw.get("accuracy"))
    out["raw_accurracy_typo"] = _num(raw.get("accurracy"))
    return out


# --------------------------------------------------------------------------- 速率标定
class ImpactCalibration:
    """每绝地潜兵影响力（HP/秒）的估计值。

    站点自己也是实测出来的（`registerImpact()` 用 impactAmtDiver/diversAmt），
    我们做同样的事：从 CDN 的星球历史里统计「绝地潜兵造成的 HP/秒 ÷ 在线人数」。

    关键细节：只有 `health < maxHealth` 时敌方 regen 才真正生效；
    满血时 regen 被截断，此时 Δhealth 直接就是绝地潜兵的输出，不能再加 regen。
    """

    def __init__(self, default: float, samples: list[tuple[float, float]] | None = None):
        self.default = default
        self.samples = samples or []
        self.value, self.source, self.sample_count = self._calibrate()

    @classmethod
    def fixed(cls, value: float, source: str = "fixed") -> "ImpactCalibration":
        """构造一个写死的标定值。测试与「禁用自动标定」场景用。"""
        obj = cls.__new__(cls)
        obj.default = value
        obj.samples = []
        obj.value = value
        obj.source = source
        obj.sample_count = 0
        return obj

    def _calibrate(self) -> tuple[float, str, int]:
        total_impact = sum(impact for impact, _ in self.samples)
        total_players = sum(players for _, players in self.samples)
        if total_players >= 500 and total_impact > 0:
            return total_impact / total_players, "measured", len(self.samples)
        return self.default, "default", len(self.samples)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hp_per_diver_per_second": _round(self.value, 9),
            "hp_per_diver_per_hour": _round(self.value * HOUR, 4),
            "source": self.source,
            "samples_used": self.sample_count,
            "default_hp_per_diver_per_second": self.default,
        }


def diver_impact_sample(a: dict[str, Any], b: dict[str, Any], dt: float) -> tuple[float, float] | None:
    """从相邻两个历史采样点提取 (绝地潜兵HP/秒, 平均在线人数)。

    物理模型：`health` 表示敌方对该星球的掌控度。
      dHealth/dt = regen - divers          （regen 抬高掌控度，绝地潜兵压低它）
    => divers = regen - dHealth/dt

    注意满血（health == maxHealth）时游戏会把 regen 截断：此时掌控度被钉在
    maxHealth 上，只要它没往下掉，就只能推断「绝地潜兵输出 ≤ regen」，
    真实数值不可观测，必须丢弃这个样本而不是当成 0。
    """
    if dt <= 60 or dt > 2 * HOUR:
        return None
    ha, hb = _num(a.get("health")), _num(b.get("health"))
    if ha is None or hb is None:
        return None
    max_health = _num(a.get("maxHealth")) or _num(b.get("maxHealth"))
    regen = _num(a.get("regenPerSecond")) or 0.0
    net = (hb - ha) / dt
    if max_health is not None and ha >= max_health:
        if net >= 0:
            return None          # 不可观测
        divers = -net            # 从满血往下掉：只有绝地潜兵在起作用
    else:
        divers = regen - net
    players = (_num(a.get("players"), 0.0) or 0.0)
    if players <= 0 or divers <= 0:
        return None
    return divers, players


def empirical_windows(
    history: dict[str, Any],
    max_seconds: float = 3600.0,
    max_windows: int = 8,
) -> list[dict[str, Any]]:
    """取最近若干个连续采样窗口（时间正序），用于算平滑速率。

    单个 15 分钟窗口的噪声很大——实测同一颗星球的相邻窗口能差 12%，
    所以除了「最新窗口」之外再给一个 1 小时的平均值会稳得多。
    """
    data = (history or {}).get("data") or []
    if len(data) < 2:
        return []

    windows: list[dict[str, Any]] = []
    span = 0.0
    for older, newest in zip(reversed(data[:-1]), reversed(data[1:])):
        t_old = parse_iso(older.get("timestampUtc"))
        t_new = parse_iso(newest.get("timestampUtc"))
        if t_old is None or t_new is None:
            continue
        dt = (t_new - t_old).total_seconds()
        if dt < 300:
            continue
        ha, hb = _num(older.get("health")), _num(newest.get("health"))
        if ha is None or hb is None:
            continue
        max_health = _num(older.get("maxHealth")) or _num(newest.get("maxHealth"))
        regen = _num(older.get("regenPerSecond")) or 0.0
        regen_clamped = bool(max_health is not None and ha >= max_health)
        if regen_clamped:
            regen = 0.0
        net = (hb - ha) / dt
        divers = (-net) if regen_clamped else (regen - net)
        players = (_num(older.get("players"), 0.0) or 0.0)
        diver_observable = not (regen_clamped and net >= 0) and divers > 0
        windows.append({
            "seconds": dt,
            "health_delta": hb - ha,
            "health_start": ha,
            "health_end": hb,
            "max_health": max_health,
            "regen_at_start": _num(older.get("regenPerSecond")) or 0.0,
            "regen_clamped": regen_clamped,
            "health_per_second": net,
            "diver_hp_per_second": divers,
            "diver_observable": diver_observable,
            "players": players,
            "from": older.get("timestampUtc"),
            "to": newest.get("timestampUtc"),
        })
        span += dt
        if span >= max_seconds or len(windows) >= max_windows:
            break

    windows.reverse()
    return windows


def empirical_window(history: dict[str, Any]) -> dict[str, Any] | None:
    """最新的一段有效窗口（`empirical_windows` 的最后一个）。

    约定（很重要）：
      * `health_per_second`         = dHealth/dt，正数表示敌方在推进
      * `diver_hp_per_second`       = regen - dHealth/dt，绝地潜兵的输出（正数）
      * `diver_observable`          = 该输出是否真的可观测

    这样 `diver_rate - resistance == net_rate` 恒成立。
    """
    windows = empirical_windows(history, max_seconds=0)
    return windows[-1] if windows else None


def smooth_windows(windows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """把多个窗口汇总成一个更稳的速率估计。

    net 用全部窗口的 Δhealth 总和；impact（绝地潜兵贡献）只用可观测的窗口，
    因为满血停摆的窗口会把绝地潜兵输出掩盖成 0。
    """
    if not windows:
        return None
    total_seconds = sum(w["seconds"] for w in windows)
    if total_seconds <= 0:
        return None
    max_health = next((w["max_health"] for w in reversed(windows) if w["max_health"]), None)
    if not max_health:
        return None

    health_delta = sum(w["health_delta"] for w in windows)
    observable = [w for w in windows if w["diver_observable"]]
    obs_seconds = sum(w["seconds"] for w in observable)
    obs_hp = sum(w["diver_hp_per_second"] * w["seconds"] for w in observable)

    k = HOUR / max_health * 100.0
    net_pct_h = -health_delta / total_seconds * k
    impact_pct_h = (obs_hp / obs_seconds * k) if obs_seconds > 0 else None

    return {
        "windows": len(windows),
        "window_seconds": _round(total_seconds, 1),
        "from": windows[0]["from"],
        "to": windows[-1]["to"],
        "net_percent_per_hour": _round(net_pct_h, 4),
        "impact_percent_per_hour": _round(impact_pct_h, 4) if impact_pct_h is not None else None,
        "observable_windows": len(observable),
        "players_avg": _round(
            sum(w["players"] * w["seconds"] for w in windows) / total_seconds, 1),
    }


# --------------------------------------------------------------------------- 星球
def _planet_status_block(
    info: dict[str, Any],
    status: dict[str, Any],
    ref_planet: dict[str, Any] | None,
    ref: Reference,
    window: dict[str, Any] | None,
    calibration: ImpactCalibration,
    total_players: float,
    attacking_race: int = 1,
    windows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    index = _int(info.get("index"))
    max_health = _num(info.get("maxHealth")) or DEFAULT_MAX_HEALTH
    health = _num(status.get("health"))
    if health is None:
        health = max_health
    regen = _num(status.get("regenPerSecond")) or 0.0
    owner_race = _int(status.get("owner"))
    players = _num(status.get("players"), 0.0) or 0.0

    # 控制度 / 解放度
    health_fraction = _clamp(health / max_health, 0.0, 1.0) if max_health else 0.0
    if owner_race == 1:
        # 己方星球：health 恒等于 maxHealth，没有「未解放」的概念
        liberation_percent = 100.0
    else:
        liberation_percent = (1.0 - health_fraction) * 100.0

    resistance_pct_h = regen * HOUR / max_health * 100.0 if max_health else 0.0

    # 「正在对抗的敌人」——站点内部叫 enemyRace，用在地图配色和 playerCountXXX 统计上：
    #   enemyRace = attackingRace == Humans ? owner : attackingRace
    # 也就是说：己方星球被打时算攻击方，否则算星球占有者。
    enemy_race = attacking_race if attacking_race != 1 else owner_race

    # 实测窗口（方向约定：解放度上升为正）
    measured = None
    if window and window.get("max_health"):
        w_max = window["max_health"]
        k = HOUR / w_max * 100.0
        measured = {
            "window_seconds": _round(window["seconds"], 1),
            "from": window["from"],
            "to": window["to"],
            "players_avg": _round(window["players"], 1),
            "regen_clamped": bool(window.get("regen_clamped")),
            "diver_rate_observable": bool(window.get("diver_observable")),
            # 官网把这一项显示为「Helldivers planetary control impact per hour」
            "diver_rate_percent_per_hour": _round(window["diver_hp_per_second"] * k, 4)
            if window.get("diver_observable") else None,
            # 解放度上下变动：正数 = 在往前推进
            "net_rate_percent_per_hour": _round(-window["health_per_second"] * k, 4),
            "health_delta": _round(window["health_delta"], 1),
        }

    smoothed = smooth_windows(windows or [])
    # 估算（按当前在线人数）
    hp_per_hour = players * calibration.value * HOUR
    est_diver_pct_h = hp_per_hour / max_health * 100.0 if max_health else 0.0
    est_net_pct_h = est_diver_pct_h - resistance_pct_h

    # 敌方掌控度已经顶到 maxHealth（解放度 0）时：
    # 解放度不可能再往下走，此刻「-抵抗度」只是模型的外推，不是正在发生的丢失。
    at_enemy_floor = owner_race != 1 and liberation_percent <= 0.0
    is_secured = owner_race == 1

    if is_secured:
        # 己方星球没有「解放速率」这个概念
        net_rate = 0.0
        rate_source = "not_applicable"
        est_diver_pct_h = None
        est_net_pct_h = None
    elif measured and measured["net_rate_percent_per_hour"] is not None:
        net_rate = measured["net_rate_percent_per_hour"]
        rate_source = "measured"
    else:
        net_rate = _round(est_net_pct_h, 4)
        rate_source = "estimated"

    unclamped_net_rate = net_rate
    if at_enemy_floor and net_rate is not None and net_rate < 0:
        # 夹在 0 上：真实进度条不会动
        net_rate = 0.0

    # 官网首页卡片显示的「Helldivers planetary control impact per hour」= 绝地潜兵贡献，
    # 不含敌方抵抗度，因此**永远非负**，与净增速不是一回事。
    # 实测可观测时用实测，否则退回估算。
    impact_rate = None
    impact_source = None
    if is_secured:
        impact_rate, impact_source = 0.0, "not_applicable"
    elif measured and measured.get("diver_rate_percent_per_hour") is not None:
        impact_rate, impact_source = measured["diver_rate_percent_per_hour"], "measured"
    else:
        impact_rate, impact_source = _round(est_diver_pct_h, 4), "estimated"

    # 解放 ETA
    eta_seconds = None
    if owner_race != 1 and net_rate and net_rate > 0:
        remaining_pct = max(100.0 - liberation_percent, 0.0)
        eta_seconds = remaining_pct / net_rate * HOUR

    # 趋势：净增速的符号比绝对数值更有信息量
    if is_secured:
        trend, trend_zh = "secured", "已控制"
    elif at_enemy_floor and players <= 0:
        # 敌方完全控制且无人进攻：既没在推进，也没在丢失
        trend, trend_zh = "uncontested", "被占领（无进攻）"
    elif net_rate is None:
        trend, trend_zh = "unknown", "未知"
    elif net_rate > 0.01:
        trend, trend_zh = "advancing", "推进中"
    elif net_rate < -0.01:
        trend, trend_zh = "losing", "被反推"
    else:
        trend, trend_zh = "stalled", "停滞"
        if measured and not measured["diver_rate_observable"]:
            trend, trend_zh = "contested_stalled", "被抵抗抵消"
    biome = (ref_planet or {}).get("biome") or {}
    hazards = (ref_planet or {}).get("hazards") or []
    waypoints = (ref_planet or {}).get("waypoints") or []
    wp_names = [ref.planet(w)["name"] for w in waypoints if ref.planet(w)]

    return {
        "index": index,
        "name": (ref_planet or {}).get("name") or f"PLANET-{index}",
        # settingsHash 是这颗星球跨战争稳定的身份标识（站点自身也用 fs1 枚举它），
        # 因此单独暴露，便于按它查询。
        "settings_hash": (ref_planet or {}).get("hash") or info.get("settingsHash"),
        "sector": (ref_planet or {}).get("sector") or "Unknown",
        # 原始载荷 warInfo.planetInfos[].sector 的整数值。**注意它和上面的 sector
        # 不是一回事**——那是另一套更粗的空间划分，0 号还是个兜底桶。
        # 详见根目录 INDEX_MAP.md 的说明。
        "payload_sector": (ref_planet or {}).get("payload_sector")
        if (ref_planet or {}).get("payload_sector") is not None
        else info.get("sector"),
        "biome": {
            "en": biome.get("en"),
            "zh": biome.get("zh"),
            "description": biome.get("description"),
        },
        "hazards": hazards,
        "position": (ref_planet or {}).get("position") or info.get("position"),
        "waypoints": wp_names,
        "max_health": _round(max_health, 1),
        "health": _round(health, 1),
        "health_percent": _round(health_fraction * 100.0, 4),
        "owner": ref.faction(owner_race),
        "enemy_faction": ref.faction(enemy_race),
        "is_under_attack": attacking_race != 1,
        "liberation_percent": _round(liberation_percent, 4),
        "is_liberated": owner_race == 1,
        "players": int(players),
        "player_share_percent": _round(_safe_div(players, total_players) * 100.0 if total_players else None, 4),
        "resistance": {
            "regen_per_second": _round(regen, 6),
            "regen_per_hour": _round(regen * HOUR, 2),
            "percent_per_hour": _round(resistance_pct_h, 4),
        },
        "liberation_rate": {
            # 官网同口径：绝地潜兵对星球控制度的影响（%/h），永远非负
            "impact_percent_per_hour": impact_rate,
            "impact_source": impact_source,
            # 扣掉敌方抵抗度后的净变化（%/h），可能为负——这才是「有没有在赢」
            "net_percent_per_hour": net_rate,
            "source": rate_source,
            "measured": measured,
            # 单个 15 分钟窗口噪声很大（实测相邻窗口能差 12%），
            # 这里给出最近最多 1 小时的平滑值
            "smoothed": smoothed,
            "estimated_diver_percent_per_hour": _round(est_diver_pct_h, 4)
            if est_diver_pct_h is not None else None,
            "estimated_net_percent_per_hour": _round(est_net_pct_h, 4)
            if est_net_pct_h is not None else None,
            # 未做「解放度不可能低于 0」夹取前的模型值，保留以便排查
            "unclamped_net_percent_per_hour": unclamped_net_rate,
            "clamped_at_enemy_floor": bool(at_enemy_floor and unclamped_net_rate != net_rate),
        },
        "trend": trend,
        "trend_zh": trend_zh,
        "eta_liberation_seconds": _round(eta_seconds, 0),
        "eta_liberation_text": humanize_seconds(eta_seconds) if owner_race != 1 else None,
        "is_homeworld": False,   # 由上层填充
        "disabled": bool(info.get("disabled")),
        "active_effects": [],    # 由上层填充（可读名称）
        "active_effect_ids": [],  # 由上层填充（原始 ID）
        "campaign": None,        # 由上层填充
        "event": None,           # 由上层填充
        "regions": [],           # 由上层填充
        "statistics": None,      # 由上层填充
    }


def _region_block(
    raw: dict[str, Any],
    ref: Reference,
    planet_index: int,
) -> dict[str, Any]:
    r_index = _int(raw.get("regionIndex"))
    meta = ref.region(planet_index, r_index) or {}
    health = _num(raw.get("health")) or 0.0
    max_health = _num(raw.get("maxHealth"))
    if max_health is None:
        max_health = health
    regen = _num(raw.get("regerPerSecond")) or 0.0  # 上游字段名确实拼错了
    owner = _int(raw.get("owner"))
    frac = _clamp(health / max_health, 0.0, 1.0) if max_health else 0.0
    return {
        "index": r_index,
        "name": meta.get("name") or f"Region {r_index}",
        "size": meta.get("size"),
        "size_zh": meta.get("size_zh"),
        "owner": ref.faction(owner),
        "health": _round(health, 1),
        "max_health": _round(max_health, 1),
        "health_percent": _round(frac * 100.0, 4),
        "controlled_percent": _round(frac * 100.0, 4),
        "regen_per_second": _round(regen, 6),
        "regen_percent_per_hour": _round(regen * HOUR / max_health * 100.0, 4) if max_health else None,
        "availability_factor": _round(_num(raw.get("availabilityFactor")), 6),
        "is_available": bool(raw.get("isAvailable")),
        "players": _int(raw.get("players")),
    }


def _event_block(raw: dict[str, Any], ref: Reference, clock: WarClock) -> dict[str, Any]:
    planet_index = _int(raw.get("planetIndex"))
    event_type = _int(raw.get("eventType"))
    health = _num(raw.get("health")) or 0.0
    max_health = _num(raw.get("maxHealth")) or 0.0
    start = _num(raw.get("startTime"))
    expire = _num(raw.get("expireTime"))

    progress = _clamp(1.0 - (health / max_health), 0.0, 1.0) if max_health else 0.0
    seconds_remaining = clock.seconds_until(expire)
    duration = (expire - start) if (expire is not None and start is not None) else None

    enemy_pct_h = (HOUR / duration * 100.0) if duration and duration > 0 else None
    required_pct_h = None
    if seconds_remaining and seconds_remaining > 0:
        required_pct_h = (1.0 - progress) / seconds_remaining * HOUR * 100.0

    label = EVENT_TYPE_LABEL.get(event_type, {"en": "Unknown", "zh": "未知"})
    return {
        "id": _int(raw.get("id")),
        "planet_index": planet_index,
        "planet_name": (ref.planet(planet_index) or {}).get("name") or f"PLANET-{planet_index}",
        "event_type": event_type,
        "event_type_label": label["zh"],
        "event_type_label_en": label["en"],
        "faction": ref.faction(raw.get("race") or raw.get("race")),
        "health": _round(health, 1),
        "max_health": _round(max_health, 1),
        "defense_progress_percent": _round(progress * 100.0, 4),
        "invasion_level": {
            "current": math.ceil(health / INVASION_LEVEL_DIVISOR) if health else 0,
            "max": int(max_health // INVASION_LEVEL_DIVISOR) if max_health else 0,
        },
        "start_war_time": _int(start) if start is not None else None,
        "expire_war_time": _int(expire) if expire is not None else None,
        "started_at": clock.to_iso(start),
        "expires_at": clock.to_iso(expire),
        "seconds_remaining": _round(seconds_remaining, 0),
        "time_remaining_text": humanize_seconds(seconds_remaining),
        "duration_seconds": _round(duration, 0),
        "enemy_rate_percent_per_hour": _round(enemy_pct_h, 4),
        "required_rate_percent_per_hour": _round(required_pct_h, 4),
        "required_divers": None,   # 由上层填充
        "predicted_outcome": None,  # 由上层填充
        "campaign_id": _int(raw.get("campaignId")),
        "joint_operation_ids": [ _int(x) for x in (raw.get("jointOperationIds") or []) ],
        "potential_build_up": _round(_num(raw.get("potentialBuildUp")), 2),
    }


def _campaign_block(raw: dict[str, Any], ref: Reference) -> dict[str, Any]:
    planet_index = _int(raw.get("planetIndex"))
    ctype = _int(raw.get("type"))
    label = CAMPAIGN_TYPE_LABEL.get(ctype, {"en": "Unknown", "zh": "未知"})
    return {
        "id": _int(raw.get("id")),
        "planet_index": planet_index,
        "planet_name": (ref.planet(planet_index) or {}).get("name") or f"PLANET-{planet_index}",
        "type": ctype,
        "type_label": label["zh"],
        "type_label_en": label["en"],
        "count": _int(raw.get("count")),
        "faction": ref.faction(raw.get("race")),
    }


# --------------------------------------------------------------------------- 星区
def _sector_blocks(planets: Iterable[dict[str, Any]], ref: Reference) -> list[dict[str, Any]]:
    by_sector: dict[str, list[dict[str, Any]]] = {}
    for p in planets:
        by_sector.setdefault(p["sector"], []).append(p)

    out = []
    for name, members in by_sector.items():
        owned: dict[str, int] = {}
        for m in members:
            key = m["owner"]["en"]
            owned[key] = owned.get(key, 0) + 1
        # 星区解放度 = 已解放星球占比（与游戏内星区条一致）
        liberated = sum(1 for m in members if m["is_liberated"])
        out.append({
            "name": name,
            "planet_count": len(members),
            "liberated_count": liberated,
            "liberated_percent": _round(liberated / len(members) * 100.0, 2) if members else None,
            "owned_by": owned,
            "players": sum(m["players"] for m in members),
            "planets": [m["index"] for m in members],
        })
    out.sort(key=lambda s: (-s["players"], s["name"]))
    return out


# --------------------------------------------------------------------------- 重大指令
def _major_order_blocks(live: dict[str, Any], ref: Reference, clock: WarClock) -> list[dict[str, Any]]:
    episodes = live.get("episodes") or []
    latest_phase: dict[int, int] = {}
    for es in live.get("episodesStatus") or []:
        latest_phase[_int(es.get("episodeId32"))] = _int(es.get("latestPhaseId32"))

    out = []
    for ep in episodes:
        eid = _int(ep.get("id32"))
        start = _num(ep.get("startWarTime"))
        end = _num(ep.get("endWarTime"))
        war_time = clock.war_time
        # 注意：进行中的指令常常没有 endWarTime（未公布结束时间），
        # 只判断 start <= warTime 会把它们漏掉。
        has_end = end is not None
        is_active = bool(start is not None and start <= war_time and (end is None or war_time <= end))
        status = _int(ep.get("status"))
        status_label = EPISODE_STATUS_LABEL.get(status, EPISODE_STATUS_LABEL[0])

        phase_id = latest_phase.get(eid)
        phases = []
        current_phase = None
        for ph in ep.get("phases") or []:
            entry = {
                "id32": _int(ph.get("id32")),
                "intro_title": ph.get("introTitle"),
                "intro_message": strip_markup(ph.get("introMessage")),
                "outro_title": ph.get("outroTitle"),
                "outro_message": strip_markup(ph.get("outroMessage")),
                "is_current": False,
            }
            phases.append(entry)

        for entry in phases:
            if entry["id32"] == phase_id:
                entry["is_current"] = True
                current_phase = entry
                break

        out.append({
            "id32": eid,
            "title": ep.get("title"),
            "description": strip_markup(ep.get("description")),
            "faction": ref.faction(ep.get("race")),
            "status": status,
            "status_label": status_label["zh"],
            "is_active": is_active,
            "has_announced_end": has_end,
            "start_war_time": _int(start) if start is not None else None,
            "end_war_time": _int(end) if end is not None else None,
            "started_at": clock.to_iso(start),
            "ends_at": clock.to_iso(end),
            "seconds_remaining": _round(clock.seconds_until(end), 0) if end is not None else None,
            "time_remaining_text": humanize_seconds(clock.seconds_until(end)) if end is not None
            else ("进行中（未公布结束时间）" if is_active else None),
            "rewards": [
                {"mix_id": _int(r.get("mixId")), "amount": _int(r.get("amount"))}
                for r in (ep.get("rewards") or [])
            ],
            "current_phase": current_phase,
            "phases": phases,
        })
    out.sort(key=lambda e: (not e["is_active"], e["title"] or ""))
    return out


# --------------------------------------------------------------------------- 空间站
def _space_station_blocks(live: dict[str, Any], ref: Reference, clock: WarClock) -> list[dict[str, Any]]:
    """空间站信息分散在两处，需要合并：

    * `live.spaceStations`          —— 完整条目（含 tacticalActions 战术行动）
    * `warStatus.spaceStations`     —— 精简条目（含 activeEffectIds 生效效果）

    取并集，以顶层条目为准，缺失的字段从 warStatus 补。
    """
    rich = {_int(s.get("id32")): s for s in (live.get("spaceStations") or [])}
    lean = {
        _int(s.get("id32")): s
        for s in ((live.get("warStatus") or {}).get("spaceStations") or [])
    }

    out = []
    for id32 in sorted(set(rich) | set(lean)):
        st = dict(lean.get(id32) or {})
        st.update({k: v for k, v in (rich.get(id32) or {}).items() if v is not None})
        planet_index = _int(st.get("planetIndex"))
        actions = []
        for a in st.get("tacticalActions") or []:
            status = _int(a.get("status"))
            label = DSS_ACTION_STATUS_LABEL.get(status, DSS_ACTION_STATUS_LABEL[0])
            actions.append({
                "id32": _int(a.get("id32")),
                "name": a.get("name"),
                "description": strip_markup(a.get("description")),
                "strategic_description": strip_markup(a.get("strategicDescription")),
                "status": status,
                "status_label": label["zh"],
                "expires_at": clock.to_iso(a.get("statusExpireAtWarTimeSeconds")),
                "seconds_remaining": _round(clock.seconds_until(a.get("statusExpireAtWarTimeSeconds")), 0),
                "cost": [
                    {
                        "item_mix_id": _int(c.get("itemMixId")),
                        "target_value": _num(c.get("targetValue")),
                        "current_value": _num(c.get("currentValue")),
                        "delta_per_second": _num(c.get("deltaPerSecond")),
                        "max_donation_amount": _num(c.get("maxDonationAmount")),
                        "max_donation_period_seconds": _num(c.get("maxDonationPeriodSeconds")),
                    }
                    for c in (a.get("cost") or [])
                ],
                "effect_ids": [_int(x) for x in (a.get("effectIds") or [])],
                "effects": ref.effects([_int(x) for x in (a.get("effectIds") or [])]),
                "active_effect_ids": [_int(x) for x in (a.get("activeEffectIds") or [])],
                "active_effects": ref.effects([_int(x) for x in (a.get("activeEffectIds") or [])]),
            })
        out.append({
            "id32": id32,
            "planet_index": planet_index,
            "planet_name": (ref.planet(planet_index) or {}).get("name") or f"PLANET-{planet_index}",
            "current_election_end": clock.to_iso(st.get("currentElectionEndWarTime")),
            "election_seconds_remaining": _round(clock.seconds_until(st.get("currentElectionEndWarTime")), 0),
            "flags": _int(st.get("flags")),
            "active_effect_ids": [_int(x) for x in (st.get("activeEffectIds") or [])],
            "active_effects": ref.effects([_int(x) for x in (st.get("activeEffectIds") or [])]),
            "tactical_actions": actions,
        })
    return out


# --------------------------------------------------------------------------- 快照组装
def build_snapshot(
    live: dict[str, Any],
    ref: Reference,
    histories: dict[int, Any] | None = None,
    calibration: ImpactCalibration | None = None,
    fetched_at: datetime | None = None,
) -> dict[str, Any]:
    """把一份 live 载荷 + 历史数据组装成完整的可读战报快照。"""
    histories = histories or {}
    cal = calibration or ImpactCalibration(0.0)

    war_info = live.get("warInfo") or {}
    war_status = live.get("warStatus") or {}
    war_stats = live.get("warStats") or {}

    clock = WarClock(live.get("clientTime"), war_status.get("time"))

    infos = {_int(p.get("index")): p for p in (war_info.get("planetInfos") or [])}
    statuses = {_int(p.get("index")): p for p in (war_status.get("planetStatus") or [])}

    total_players = sum((_num(s.get("players"), 0.0) or 0.0) for s in statuses.values())

    # 每个星球「正在对抗谁」：有防御/入侵事件就取事件的攻击方，否则视作人类在进攻
    attacking_by_planet: dict[int, int] = {}
    for ev in war_status.get("planetEvents") or []:
        attacking_by_planet[_int(ev.get("planetIndex"))] = _int(ev.get("race"))

    # 主循环：构造每颗星球的报告
    planets: list[dict[str, Any]] = []
    by_index: dict[int, dict[str, Any]] = {}
    for index in sorted(infos):
        info = infos[index]
        status = statuses.get(index)
        if status is None:
            continue
        history = histories.get(index) or {}
        windows = empirical_windows(history, max_seconds=RATE_SMOOTHING_SECONDS)
        window = windows[-1] if windows else None
        block = _planet_status_block(
            info, status, ref.planet(index), ref, window, cal, total_players,
            attacking_by_planet.get(index, 1), windows,
        )
        planets.append(block)
        by_index[index] = block

    # 填充 homeworld 标记
    for hw in war_info.get("homeWorlds") or []:
        for pi in hw.get("planetIndices") or []:
            blk = by_index.get(_int(pi))
            if blk:
                blk["is_homeworld"] = True
                blk["homeworld_faction"] = ref.faction(hw.get("race"))

    # 行星级持久效果（敌人变种 / 设施 / 环境异常等）
    effect_ids_by_planet: dict[int, list[int]] = {}
    for eff in war_status.get("planetActiveEffects") or []:
        effect_ids_by_planet.setdefault(_int(eff.get("index")), []).append(_int(eff.get("galacticEffectId")))
    for index, ids in effect_ids_by_planet.items():
        blk = by_index.get(index)
        if blk:
            unique = sorted(set(ids))
            blk["active_effect_ids"] = unique
            blk["active_effects"] = ref.effects(unique)

    # 战役
    campaigns = [_campaign_block(c, ref) for c in (war_status.get("campaigns") or [])]
    for c in campaigns:
        blk = by_index.get(c["planet_index"])
        if blk:
            blk["campaign"] = c

    # 防御 / 入侵事件
    events = [_event_block(e, ref, clock) for e in (war_status.get("planetEvents") or [])]
    for ev in events:
        blk = by_index.get(ev["planet_index"])
        if blk:
            blk["event"] = ev

    # 区域
    for raw in war_status.get("planetRegions") or []:
        pi = _int(raw.get("planetIndex"))
        blk = by_index.get(pi)
        if blk:
            blk["regions"].append(_region_block(raw, ref, pi))
    for blk in planets:
        blk["regions"].sort(key=lambda r: r["index"])

    # 星球统计
    stats_by_planet: dict[int, dict[str, Any]] = {}
    for raw in (war_stats.get("planets_stats") or []):
        pi = _int(raw.get("planetIndex"))
        # 上游混有 index 为负的哨兵记录，丢弃
        if pi < 0 or pi not in by_index:
            continue
        stats_by_planet[pi] = normalize_stats(raw)
    for pi, stats in stats_by_planet.items():
        by_index[pi]["statistics"] = stats

    # 防御战：结合在线人数估算「预计结果」与「所需增援」
    for ev in events:
        blk = by_index.get(ev["planet_index"])
        if not blk:
            continue
        players = blk["players"]
        max_health = ev["max_health"] or 0.0
        est_diver_pct_h = players * cal.value * HOUR / max_health * 100.0 if max_health else 0.0
        ev["estimated_diver_rate_percent_per_hour"] = _round(est_diver_pct_h, 4)
        req = ev.get("required_rate_percent_per_hour")
        if req is not None:
            # 覆盖比 = 当前投入 / 守住所需。把它交出去，
            # 让调用方可以按自己的阈值判断，而不是只信我们的标签。
            ratio = (est_diver_pct_h / req) if req > 0 else None
            ev["diver_coverage_ratio"] = _round(ratio, 4)
            if ratio is None:
                ev["predicted_outcome"] = "unknown"
                ev["predicted_outcome_text"] = "缺少数据"
            elif ratio >= 1.0:
                ev["predicted_outcome"] = "defense_will_hold"
                ev["predicted_outcome_text"] = "按当前投入预计守住"
            elif ratio >= 0.8:
                ev["predicted_outcome"] = "too_close_to_call"
                ev["predicted_outcome_text"] = "胜负难料"
            else:
                ev["predicted_outcome"] = "defense_will_fail"
                ev["predicted_outcome_text"] = "按当前投入预计失守"
            # 守住所需人数 = 所需速率 / 每人速率
            per_diver_pct_h = cal.value * HOUR / max_health * 100.0 if max_health else 0.0
            if per_diver_pct_h > 0:
                needed = req / per_diver_pct_h
                ev["required_divers"] = int(math.ceil(needed))
                ev["diver_surplus"] = int(math.floor(players - needed))
        ev["players"] = players

    # 防御战按剩余时间排序
    defenses = sorted(
        events, key=lambda e: (e["seconds_remaining"] is None, e["seconds_remaining"] or 0)
    )

    # 状态标签
    for blk in planets:
        if blk["event"]:
            blk["status"] = "防御中" if blk["event"]["event_type"] == 1 else "战斗中"
        elif blk["is_liberated"]:
            blk["status"] = "已解放"
        elif blk["players"] > 0 or blk["liberation_percent"] > 0:
            blk["status"] = "解放中"
        else:
            blk["status"] = "被占领"

    # ---- 汇总
    owned: dict[str, int] = {}
    players_by_owner: dict[str, int] = {}
    players_by_enemy: dict[str, int] = {}
    for blk in planets:
        owner_key = blk["owner"]["en"]
        owned[owner_key] = owned.get(owner_key, 0) + 1
        players_by_owner[owner_key] = players_by_owner.get(owner_key, 0) + blk["players"]
        enemy_key = blk["enemy_faction"]["en"]
        players_by_enemy[enemy_key] = players_by_enemy.get(enemy_key, 0) + blk["players"]

    active_major_orders = [mo for mo in _major_order_blocks(live, ref, clock) if mo["is_active"]]

    galaxy_stats = normalize_stats(war_stats.get("galaxy_stats"))

    snapshot = {
        "ok": True,
        "generated_at": iso(fetched_at or datetime.now(timezone.utc)),
        "war": {
            "war_id": _int(live.get("warId")),
            "layout_version": _int(war_info.get("layoutVersion")),
            "client_time": iso(
                datetime.fromtimestamp(clock.client_time / 1000.0, tz=timezone.utc)
            ) if clock.client_time else None,
            "war_time_seconds": _int(clock.war_time),
            "time_since_start_seconds": _int(live.get("timeSinceStart")),
            "galactic_impact_multiplier": _round(_num(war_status.get("impactMultiplier")), 9),
            "app_version": live.get("appVersion"),
            "story_beat_id32": _int(war_status.get("storyBeatId32")),
        },
        "totals": {
            "players_online": int(total_players),
            "planets_total": len(planets),
            "planets_with_divers": sum(1 for p in planets if p["players"] > 0),
            "owned_by_faction": owned,
            # 按「星球当前占有阵营」归类在线绝地潜兵（直觉口径）
            "players_by_owner_faction": players_by_owner,
            # 按「正在对抗的敌人」归类在线绝地潜兵 —— 与站点 extendedApiInformation
            # 里的 playerCountHumans / playerCountTerminids / ... 完全同口径。
            # 注意二者含义不同：己方星球被打时，人算在攻击方名下，不算在 Humans 名下。
            "players_by_enemy_faction": players_by_enemy,
            "liberated_planets": sum(1 for p in planets if p["is_liberated"]),
            "active_campaigns": len(campaigns),
            "active_defenses": len(events),
            "active_major_orders": len(active_major_orders),
        },
        "impact_calibration": cal.to_dict(),
        # 像 `owned_by_faction` / `players_by_enemy_faction` 这种计数 map 用的是
        # 英文阵营名做键（稳定标识，且与站点的 playerCountXXX 同名）。
        # 这里给出一次性映射，消费方不必自己硬编码中文。
        "faction_labels": {
            f["en"]: f["zh"] for f in ref.factions.values() if f["en"] != "None"
        },
        "galaxy_statistics": galaxy_stats,
        "sectors": _sector_blocks(planets, ref),
        "planets": planets,
        "campaigns": campaigns,
        "defenses": defenses,
        "major_orders": _major_order_blocks(live, ref, clock),
        "space_stations": _space_station_blocks(live, ref, clock),
        "global_events": [
            {
                "event_id": _int(g.get("eventId")),
                "id32": _int(g.get("id32")),
                "title": g.get("title"),
                "message": strip_markup(g.get("message")),
                "faction": ref.faction(g.get("race")),
                "expires_at": clock.to_iso(g.get("expireTime")),
                "seconds_remaining": _round(clock.seconds_until(g.get("expireTime")), 0),
            }
            for g in (war_status.get("globalEvents") or [])
        ],
        "dispatches": [
            {
                "id": _int(n.get("id")),
                "type": _int(n.get("type")),
                "published_war_time": _int(n.get("published")),
                "published_at": clock.to_iso(n.get("published")),
                "tag_ids": [_int(x) for x in (n.get("tagIds") or [])],
                "message": strip_markup(n.get("message")),
                "message_raw": n.get("message"),
            }
            for n in sorted(
                live.get("news") or [], key=lambda n: _int(n.get("published")), reverse=True
            )
        ],
        "reference": {
            "generated_at": ref.generated_at,
            "source": ref.source,
            "planet_count": ref.planet_count,
            "sector_count": ref.sector_count,
        },
    }
    return snapshot


def collect_calibration_samples(histories: dict[int, Any]) -> list[tuple[float, float]]:
    """从所有历史里收集 (HP/秒, 在线人数) 样本，用于标定每绝地潜兵影响力。"""
    samples: list[tuple[float, float]] = []
    for history in histories.values():
        data = (history or {}).get("data") or []
        for a, b in zip(data, data[1:]):
            ta, tb = parse_iso(a.get("timestampUtc")), parse_iso(b.get("timestampUtc"))
            if ta is None or tb is None:
                continue
            got = diver_impact_sample(a, b, (tb - ta).total_seconds())
            if got is not None:
                samples.append(got)
    return samples


def planet_summary(p: dict[str, Any], full: bool = False) -> dict[str, Any]:
    """把星球报告压成一行摘要，适合列表消费。

    full=True 时额外保留战役/事件/统计等稍大的块。
    """
    ev = p.get("event") or {}
    camp = p.get("campaign") or {}
    out: dict[str, Any] = {
        "index": p["index"],
        "name": p["name"],
        "sector": p["sector"],
        "payload_sector": p.get("payload_sector"),
        "biome": (p.get("biome") or {}).get("en"),
        "biome_zh": (p.get("biome") or {}).get("zh"),
        "owner": p["owner"]["en"],
        "owner_zh": p["owner"]["zh"],
        "enemy_faction": (p.get("enemy_faction") or {}).get("en"),
        "enemy_faction_zh": (p.get("enemy_faction") or {}).get("zh"),
        "status": p.get("status"),
        "health": p["health"],
        "max_health": p["max_health"],
        "liberation_percent": p["liberation_percent"],
        "players": p["players"],
        "player_share_percent": p.get("player_share_percent"),
        "resistance_percent_per_hour": (p.get("resistance") or {}).get("percent_per_hour"),
        # 与官网卡片同口径（绝地潜兵影响力，非负）
        "impact_percent_per_hour": (p.get("liberation_rate") or {}).get("impact_percent_per_hour"),
        # 净变化，可能为负
        "liberation_rate_percent_per_hour": (p.get("liberation_rate") or {}).get("net_percent_per_hour"),
        "rate_source": (p.get("liberation_rate") or {}).get("source"),
        "smoothed_net_percent_per_hour":
            ((p.get("liberation_rate") or {}).get("smoothed") or {}).get("net_percent_per_hour"),
        "smoothed_impact_percent_per_hour":
            ((p.get("liberation_rate") or {}).get("smoothed") or {}).get("impact_percent_per_hour"),
        "eta_liberation_seconds": p.get("eta_liberation_seconds"),
        "eta_liberation_text": p.get("eta_liberation_text"),
        "is_defending": bool(ev),
        "trend": p.get("trend"),
        "trend_zh": p.get("trend_zh"),
        "invasion_level": (ev.get("invasion_level") or {}).get("current"),
        "invasion_level_max": (ev.get("invasion_level") or {}).get("max"),
        "defense_progress_percent": ev.get("defense_progress_percent"),
        "event_expires_at": ev.get("expires_at"),
        "predicted_outcome": ev.get("predicted_outcome_text"),
        "campaign_id": camp.get("id"),
        "campaign_level": camp.get("count"),
    }
    if full:
        out["campaign"] = p.get("campaign")
        out["event"] = p.get("event")
        out["hazards"] = p.get("hazards")
        out["regions"] = p.get("regions")
        out["statistics"] = p.get("statistics")
        out["position"] = p.get("position")
        out["waypoints"] = p.get("waypoints")
        out["is_homeworld"] = p.get("is_homeworld")
        out["active_effects"] = p.get("active_effects")
    return out


def population_history_block(payload: dict[str, Any] | None, hours: float | None = None) -> dict[str, Any]:
    """整理站点的全银河时间序列（总在线人数 / 分阵营 / 影响系数 / 累计统计）。

    数据源：`live/extendedApiInformation/2days.json`，约 15 分钟一个采样点。

    这个文件的 `totalPlayerCount` 就是站点自己用的「总在线潜兵数」分母，
    因此可以直接用来核对我们的 `players_online`（见 README）。
    """
    rows = (payload or {}).get("data") or []
    faction_keys = {
        "playerCountHumans": "humans",
        "playerCountTerminids": "terminids",
        "playerCountAutomatons": "automatons",
        "playerCountIlluminate": "illuminate",
    }

    samples: list[dict[str, Any]] = []
    for row in rows:
        ts = parse_iso(row.get("timestampUtc"))
        if ts is None:
            continue
        total = _num(row.get("totalPlayerCount"))
        if total is None:
            continue
        samples.append({
            "timestamp": row.get("timestampUtc"),
            "total_players": int(total),
            "players_by_faction": {
                name: int(_num(row.get(key), 0) or 0)
                for key, name in faction_keys.items()
                if key in row
            },
            "galactic_impact_multiplier": _round(_num(row.get("impactMultiplier")), 9),
        })

    samples.sort(key=lambda s: s["timestamp"] or "")

    if hours is not None and samples:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        kept = []
        for s in samples:
            ts = parse_iso(s["timestamp"])
            if ts is not None and ts >= cutoff:
                kept.append(s)
        samples = kept

    totals = [s["total_players"] for s in samples]
    latest = samples[-1] if samples else None
    summary = None
    if totals:
        summary = {
            "samples": len(samples),
            "latest_total_players": totals[-1],
            "latest_at": latest["timestamp"] if latest else None,
            "min_total_players": min(totals),
            "max_total_players": max(totals),
            "avg_total_players": int(sum(totals) / len(totals)),
            "latest_players_by_faction": (latest or {}).get("players_by_faction"),
        }

    return {
        "source": config.CDN_EXTENDED_API_INFO_2D,
        "window_hours": hours,
        "summary": summary,
        "samples": samples,
    }


def steam_news_block(payload: dict[str, Any] | None) -> dict[str, Any]:
    """整理 Steam 新闻源。"""
    news = ((payload or {}).get("appnews") or {}).get("newsitems") or []
    items = []
    for n in news:
        items.append({
            "gid": str(n.get("gid")),
            "title": n.get("title"),
            "url": n.get("url"),
            "author": n.get("author"),
            "contents": strip_markup(n.get("contents")),
            "feedlabel": n.get("feedlabel"),
            "date_unix": n.get("date"),
            "date": iso(datetime.fromtimestamp(n["date"], tz=timezone.utc)) if n.get("date") else None,
            "is_external": bool(n.get("is_external_url")),
        })
    items.sort(key=lambda x: x["date_unix"] or 0, reverse=True)
    return {"count": len(items), "items": items}
