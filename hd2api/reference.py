"""静态参照表：把游戏内 ID 翻译成可读文本。"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from . import config

# 阵营编号 —— 已用 273 颗星球交叉验证
FACTION_FALLBACK: dict[int, dict[str, Any]] = {
    0: {"id": 0, "en": "None", "zh": "无", "color": "#7f8f71"},
    1: {"id": 1, "en": "Humans", "zh": "超级地球", "color": "#4a9de0"},
    2: {"id": 2, "en": "Terminids", "zh": "终结族", "color": "#f0a020"},
    3: {"id": 3, "en": "Automatons", "zh": "机器人", "color": "#e04545"},
    4: {"id": 4, "en": "Illuminate", "zh": "光能者", "color": "#a855f7"},
}

# planetEvents.eventType
EVENT_TYPE_LABEL = {
    1: {"en": "Defense", "zh": "防御战"},
    2: {"en": "Attack", "zh": "进攻战"},
}

# campaigns.type
CAMPAIGN_TYPE_LABEL = {
    0: {"en": "Liberation", "zh": "解放战役"},
    1: {"en": "Defense", "zh": "防御战役"},
}

# episodes.status
EPISODE_STATUS_LABEL = {
    0: {"en": "Unknown", "zh": "未知"},
    1: {"en": "Upcoming", "zh": "未开始"},
    2: {"en": "Active", "zh": "进行中"},
    3: {"en": "Ended", "zh": "已结束"},
}

# spaceStations.tacticalActions[].status
DSS_ACTION_STATUS_LABEL = {
    0: {"en": "Unknown", "zh": "未知"},
    1: {"en": "Voting", "zh": "投票中"},
    2: {"en": "Donating", "zh": "捐赠中"},
    3: {"en": "Activated", "zh": "已激活"},
    4: {"en": "Recovering", "zh": "冷却中"},
}

# galacticWarEffects.effectType（游戏内效果大类）
EFFECT_TYPE_LABEL: dict[int, str] = {
    1: "行星效果",
    43: "战略效果",
    44: "战略效果",
}

# 效果 slug 前缀 -> 中文分类。取自站点枚举里的命名约定。
#
# 注意 `game_X` 与 `pawn_X` 是同一敌人变种的两个效果（玩法效果 / 刷怪效果），
# ID 不同、可读名相同，靠 category 区分。
EFFECT_PREFIX_LABEL: dict[str, str] = {
    "mark": "设施 / 标记",
    "fog": "环境异常",
    "game": "战术行动",
    "war": "战争效果",
    "pres": "存在标记",
    "pawn": "敌人变种",
    "ammo": "弹药修正",
    "boost": "增益",
    "eagle": "飞鹰支援",
    "extract": "撤离修正",
    "event": "事件效果",
    "planet": "行星效果",
    "UNK": "未命名（站点也未给出名称）",
}

# 这些前缀在生成可读名时会被剥掉；UNK 保留，否则就只剩一串数字
_STRIPPABLE_PREFIXES = set(EFFECT_PREFIX_LABEL) - {"UNK"}

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
# 只在「小写字母 + 数字」之间插空格："Pickup1" -> "Pickup 1"，
# 但 "M2" / "TCS2" 这类缩写保持原样。
_DIGIT_RE = re.compile(r"(?<=[a-z])(?=\d)")


def humanize_identifier(slug: str) -> str:
    """`mark_JetBrigadeFactory` -> `Jet Brigade Factory`；`fog_GloomM2` -> `Gloom M2`。"""
    if not slug:
        return ""
    parts = slug.split("_", 1)
    body = parts[1] if len(parts) == 2 and parts[0] in _STRIPPABLE_PREFIXES else slug
    body = _DIGIT_RE.sub(" ", body)
    body = _CAMEL_RE.sub(" ", body)
    body = body.replace("_", " ").strip()
    return " ".join(body.split())


def _clamp_race(race: Any) -> int:
    try:
        value = int(race)
    except (TypeError, ValueError):
        return 0
    return value if value in FACTION_FALLBACK else 0


class Reference:
    """加载 data/reference.json 并提供查询。"""

    def __init__(self, path: str = config.REFERENCE_PATH,
                 effects_path: str | None = None) -> None:
        self.path = path
        self.effects_path = effects_path or os.path.join(
            os.path.dirname(path), "effects.json")
        self._doc: dict[str, Any] = {}
        self._planets: dict[int, dict[str, Any]] = {}
        self._sectors: dict[str, dict[str, Any]] = {}
        self._effects: dict[int, str] = {}
        self._presence: dict[int, str] = {}
        self.load()

    # ------------------------------------------------------------------ 加载
    def load(self) -> None:
        if not os.path.exists(self.path):
            raise FileNotFoundError(
                f"缺少静态参照表 {self.path}；请先运行: python scripts/refresh_reference.py"
            )
        with open(self.path, encoding="utf-8") as fh:
            self._doc = json.load(fh)
        self._planets = {int(k): v for k, v in (self._doc.get("planets") or {}).items()}
        self._sectors = dict(self._doc.get("sectors") or {})
        self._load_effects()

    def _load_effects(self) -> None:
        """效果名称表是可选的：没有就退化成一个数字 ID。"""
        self._effects = {}
        self._presence = {}
        if not os.path.exists(self.effects_path):
            return
        try:
            with open(self.effects_path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        self._effects = {int(k): v for k, v in (doc.get("effect_ids") or {}).items()}
        self._presence = {int(k): v for k, v in (doc.get("presence_ids") or {}).items()}

    # ------------------------------------------------------------------ 元信息
    @property
    def generated_at(self) -> str:
        return self._doc.get("generated_at", "")

    @property
    def source(self) -> str:
        return self._doc.get("source", "")

    @property
    def war_id(self) -> int | None:
        return self._doc.get("war_id")

    @property
    def planet_count(self) -> int:
        return len(self._planets)

    @property
    def sector_count(self) -> int:
        return len(self._sectors)

    # ------------------------------------------------------------------ 查询
    def planet(self, index: int) -> dict[str, Any] | None:
        return self._planets.get(index)

    def planets(self) -> dict[int, dict[str, Any]]:
        return self._planets

    def sectors(self) -> dict[str, dict[str, Any]]:
        return self._sectors

    def sector_of(self, index: int) -> str:
        p = self._planets.get(index)
        return (p or {}).get("sector") or "Unknown"

    def region(self, planet_index: int, region_index: int) -> dict[str, Any] | None:
        p = self._planets.get(planet_index) or {}
        return (p.get("regions") or {}).get(str(region_index))

    def faction(self, race: Any) -> dict[str, Any]:
        return dict(FACTION_FALLBACK.get(_clamp_race(race), FACTION_FALLBACK[0]))

    def faction_by_name(self, name: str | None) -> dict[str, Any]:
        if not name:
            return dict(FACTION_FALLBACK[0])
        low = name.lower().rstrip("s")
        for f in FACTION_FALLBACK.values():
            if f["en"].lower().rstrip("s") == low:
                return dict(f)
        return dict(FACTION_FALLBACK[0])

    @property
    def factions(self) -> dict[int, dict[str, Any]]:
        return {k: dict(v) for k, v in FACTION_FALLBACK.items()}

    # 静态表里额外的中文映射（供 biome/hazard 兜底翻译）
    def biome_zh(self, en: str) -> str:
        return (self._doc.get("biomes_zh") or {}).get(en, en)

    def hazard_zh(self, en: str) -> str:
        return (self._doc.get("hazards_zh") or {}).get(en, en)

    def region_size_zh(self, en: str | None) -> str | None:
        if en is None:
            return None
        return (self._doc.get("region_size_zh") or {}).get(en, en)

    # ------------------------------------------------------------------ 效果
    def _effect_tables(self) -> tuple[dict[int, str], dict[int, str]]:
        """容错取表：Reference 可能由 __new__ 直接构造（测试夹具），此时没有 _effects。"""
        return self.__dict__.get("_effects") or {}, self.__dict__.get("_presence") or {}

    @property
    def effect_count(self) -> int:
        effects, presence = self._effect_tables()
        return len(effects) + len(presence)

    def effect(self, effect_id: Any) -> dict[str, Any] | None:
        """把 planetActiveEffects[].galacticEffectId 变成可读效果。

        同一个 ID 在站点枚举里可能是小整数（m1）也可能是 32 位哈希（Yt），
        两张表都查一遍。
        """
        effects, presence = self._effect_tables()
        try:
            eid = int(effect_id)
        except (TypeError, ValueError):
            return None
        slug = effects.get(eid) or presence.get(eid)
        if not slug:
            return None
        prefix = slug.split("_", 1)[0] if "_" in slug else ""
        return {
            "id": eid,
            "slug": slug,
            "label": humanize_identifier(slug),
            "category": EFFECT_PREFIX_LABEL.get(prefix),
        }

    def effects(self, effect_ids: Any) -> list[dict[str, Any]]:
        out = []
        for eid in effect_ids or []:
            got = self.effect(eid)
            out.append(got if got else {"id": eid, "slug": None, "label": None, "category": None})
        return out


_reference: Reference | None = None


def get_reference(reload: bool = False) -> Reference:
    """进程级单例。"""
    global _reference
    if _reference is None or reload:
        _reference = Reference()
    return _reference
