"""
构建静态参照表 data/reference.json。

背景
----
helldiverscompanion 的实时载荷 (get-api-data-live) 里**不含任何可读名称**：
`warInfo.planetInfos[].planetNameId32` 与 `planetBiomeId32` 全被置为 0，
`sector` 只是一个整数。因此必须外挂一张「游戏内 ID -> 可读文本」的静态表。

这张表来自社区镜像 API 的 `/api/v1/planets`（与游戏官方 WarInfo 同源），
它给出的 `hash` 与实时载荷里的 `settingsHash` **逐条严格相等**（273/273 已验证），
所以可以作为权威的 ID 对齐依据。

本脚本把该数据固化成 data/reference.json，之后 API 运行时**完全不需要**再访问它。

用法:
    python scripts/refresh_reference.py            # 联网刷新并覆盖 data/reference.json
    python scripts/refresh_reference.py --check    # 只校验现有文件与实时载荷是否仍然对齐
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "reference.json")

REFERENCE_SOURCE = "https://api.helldivers2.dev/api/v1/planets"
LIVE_SOURCE = "https://helldiverscompanion.com/api/hell-divers-2-api/get-api-data-live"

USER_AGENT = "helldiversbot/1.0 (+local research tool)"

# 阵营编号 —— 已用 273 颗星球的 owner 与参照表 currentOwner 逐条交叉验证，0 处不一致
FACTIONS = {
    0: {"id": 0, "en": "None", "zh": "无", "color": "#7f8f71"},
    1: {"id": 1, "en": "Humans", "zh": "超级地球", "color": "#4a9de0"},
    2: {"id": 2, "en": "Terminids", "zh": "终结族", "color": "#f0a020"},
    3: {"id": 3, "en": "Automatons", "zh": "机器人", "color": "#e04545"},
    4: {"id": 4, "en": "Illuminate", "zh": "光能者", "color": "#a855f7"},
}

BIOME_ZH = {
    "Super Earth": "超级地球",
    "Desert Dunes": "沙漠沙丘",
    "Plains": "平原",
    "Moon": "月球",
    "Ionic Jungle": "离子丛林",
    "Desert Cliffs": "沙漠峭壁",
    "Rocky Canyons": "岩石峡谷",
    "Acidic Badlands": "酸性荒地",
    "Basic Swamp": "原始沼泽",
    "Tundra": "苔原",
    "Icy Glaciers": "冰川",
    "Boneyard": "骸骨场",
    "Ionic Crimson": "赤红离子",
    "Ethereal Jungle": "空灵丛林",
    "Volcanic Jungle": "火山丛林",
    "Haunted Swamp": "阴魂沼泽",
    "Deadlands": "死地",
    "Scorched Moor": "焦灼荒原",
    "Supercolony": "超级虫巢",
    "Deciduous Autumn Forest": "秋色落叶林",
    "Hive World": "巢都世界",
    "ACCESS DENIED": "机密（权限不足）",
    "Cyberstan Megafactory": "赛博斯坦巨型工厂",
    "Magma": "熔岩",
    "Desert Oasis": "沙漠绿洲",
    "Deciduous Forest": "落叶林",
}

HAZARD_ZH = {
    "None": "无",
    "Sandstorms": "沙暴",
    "Meteor Storms": "流星风暴",
    "Ion Storms": "离子风暴",
    "Tremors": "地震活动",
    "Acid Storms": "酸雨风暴",
    "Blizzards": "暴风雪",
    "Volcanic Activity": "火山活动",
    "Fire Tornadoes": "火焰龙卷",
}

REGION_SIZE_ZH = {
    "City": "城市",
    "MegaCity": "巨型城市",
    "Town": "城镇",
    "Settlement": "定居点",
    "Outpost": "前哨站",
}

# 参照表里的阵营名 -> 游戏内 race 编号
OWNER_TO_RACE = {
    "Humans": 1,
    "Terminids": 2,
    "Automaton": 3,
    "Automatons": 3,
    "Illuminate": 4,
}


def http_json(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        # 社区镜像 API 要求的标识头
        "X-Super-Client": "helldiversbot",
        "X-Super-Contact": "local-research",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return json.loads(raw)


def build(planets_raw: list, war_id: int | None,
          payload_sectors: dict[int, int] | None = None) -> dict:
    """组装参照表。

    `payload_sectors` 是实时载荷里 `warInfo.planetInfos[].sector` 的
    {planet_index: sector_int}。**注意它和 wiki 星区不是一回事**：
      * wiki 星区（本表的 `sector` 字段）是按坐标聚出来的紧密区块，
        中位半径 0.122，名字形如 Altus / Sol / Valdis；
      * 载荷里的 `sector` 整数是另一套更粗的划分，而且 0 号是个兜底桶
        （半径 0.926，横跨全图）。53 个整数里有 36 个与星区名冲突。
    所以两者都存，字段名上区分清楚，避免混用。
    """
    payload_sectors = payload_sectors or {}
    factions_out = {str(k): v for k, v in FACTIONS.items()}

    planets_out: dict[str, dict] = {}
    sectors_out: dict[str, dict] = {}

    for p in planets_raw:
        biome = p.get("biome") or {}
        biome_name = biome.get("name") or "Unknown"
        hazards = []
        for h in p.get("hazards") or []:
            hn = h.get("name") or "None"
            hazards.append({
                "en": hn,
                "zh": HAZARD_ZH.get(hn, hn),
                "description": h.get("description") or "",
            })

        regions = {}
        for r in p.get("regions") or []:
            size = r.get("size")
            regions[str(r["id"])] = {
                "index": r["id"],
                "name": r.get("name") or f"Region {r['id']}",
                "size": size,
                "size_zh": REGION_SIZE_ZH.get(size, size),
                "hash": r.get("hash"),
            }

        sector = p.get("sector") or "Unknown"
        entry = {
            "index": p["index"],
            "name": p.get("name") or f"PLANET-{p['index']}",
            "sector": sector,
            # 原始载荷里的 sector 整数（与 wiki 星区不同，见 build() 的说明）
            "payload_sector": payload_sectors.get(p["index"]),
            "biome": {
                "en": biome_name,
                "zh": BIOME_ZH.get(biome_name, biome_name),
                "description": biome.get("description") or "",
            },
            "hazards": hazards,
            "hash": p.get("hash"),
            "position": p.get("position") or {"x": 0, "y": 0},
            "waypoints": p.get("waypoints") or [],
            "max_health": p.get("maxHealth"),
            "initial_owner": OWNER_TO_RACE.get(p.get("initialOwner") or "", 0),
            "regions": regions,
        }
        planets_out[str(p["index"])] = entry

        sec = sectors_out.setdefault(sector, {"name": sector, "planets": []})
        sec["planets"].append(p["index"])

    for sec in sectors_out.values():
        sec["planets"].sort()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": REFERENCE_SOURCE,
        "war_id": war_id,
        "planet_count": len(planets_out),
        "sector_count": len(sectors_out),
        "factions": factions_out,
        "biomes_zh": BIOME_ZH,
        "hazards_zh": HAZARD_ZH,
        "region_size_zh": REGION_SIZE_ZH,
        "sectors": dict(sorted(sectors_out.items())),
        "planets": dict(sorted(planets_out.items(), key=lambda kv: int(kv[0]))),
    }


def cmd_refresh() -> int:
    print(f"[1/2] 拉取参照表: {REFERENCE_SOURCE}")
    planets_raw = http_json(REFERENCE_SOURCE)
    print(f"      -> {len(planets_raw)} 颗星球")

    war_id = None
    payload_sectors: dict[int, int] = {}
    try:
        print(f"[2/2] 拉取实时载荷以记录 warId 与载荷里的 sector 整数: {LIVE_SOURCE}")
        live = http_json(LIVE_SOURCE)
        war_id = live.get("warId")
        for info in (live.get("warInfo") or {}).get("planetInfos") or []:
            payload_sectors[int(info["index"])] = int(info.get("sector") or 0)
        print(f"      -> warId={war_id}，planetInfos {len(payload_sectors)} 条")
    except Exception as exc:  # noqa: BLE001
        print(f"      !! 实时载荷拉取失败（不影响参照表主体）: {exc}")

    doc = build(planets_raw, war_id, payload_sectors)
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)

    sizes = sorted({r["size"] for p in doc["planets"].values() for r in p["regions"].values() if r["size"]})
    groups = {p["payload_sector"] for p in doc["planets"].values() if p["payload_sector"] is not None}
    print(f"已写入 {DATA_PATH}")
    print(f"  星球 {doc['planet_count']} 颗 / 星区 {doc['sector_count']} 个 / 区域尺寸类型 {sizes}")
    if groups:
        print(f"  载荷里的 sector 整数取值 {len(groups)} 个（注意：与星区不是一回事）")
    return 0


def cmd_check() -> int:
    """校验参照表的 hash 是否仍与实时载荷的 settingsHash 完全对齐。"""
    with open(DATA_PATH, encoding="utf-8") as fh:
        ref = json.load(fh)
    live = http_json(LIVE_SOURCE)

    mismatches, checked = [], 0
    for info in live["warInfo"]["planetInfos"]:
        entry = ref["planets"].get(str(info["index"]))
        if not entry or entry.get("hash") is None:
            continue
        checked += 1
        if entry["hash"] != info["settingsHash"]:
            mismatches.append((info["index"], entry["hash"], info["settingsHash"], entry["name"]))

    print(f"校验 {checked} 颗星球的 settingsHash：{len(mismatches)} 处不一致")
    for m in mismatches[:20]:
        print(f"  index={m[0]} ref={m[1]} live={m[2]} name={m[3]}")

    missing = [i["index"] for i in live["warInfo"]["planetInfos"] if str(i["index"]) not in ref["planets"]]
    if missing:
        print(f"参照表缺失 {len(missing)} 个索引: {missing[:40]}")
    return 1 if mismatches else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="构建/校验静态参照表")
    ap.add_argument("--check", action="store_true", help="只校验，不覆盖")
    args = ap.parse_args()
    return cmd_check() if args.check else cmd_refresh()


if __name__ == "__main__":
    sys.exit(main())
