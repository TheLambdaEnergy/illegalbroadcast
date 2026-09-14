"""从 data/reference.json 生成项目根目录下的 index 对照表。

产物（都在项目根目录，方便直接翻）:
    INDEX_MAP.md      人类可读的对照表
    planet_index.csv  机器可读（Excel / pandas 直接打开）

    python scripts/build_index_map.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_PATH = os.path.join(ROOT, "data", "reference.json")
TRANS_PATH = os.path.join(ROOT, "data", "translations_zh.json")
MD_PATH = os.path.join(ROOT, "INDEX_MAP.md")
CSV_PATH = os.path.join(ROOT, "planet_index.csv")

RACE_ZH = {0: "无", 1: "超级地球", 2: "终结族", 3: "机器人", 4: "光能者"}


def load() -> dict:
    with open(REF_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def load_translations() -> dict:
    """手工维护的中文译名（星球 index -> 中文名、星区名 -> 中文名）。

    单独放在 data/translations_zh.json，**不要**并进 reference.json ——
    那个文件由 refresh_reference.py 重新生成，会把手写内容冲掉。
    """
    if not os.path.exists(TRANS_PATH):
        return {"planets": {}, "sectors": {}}
    try:
        with open(TRANS_PATH, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"planets": {}, "sectors": {}}
    return {
        "planets": {str(k): v for k, v in (doc.get("planets") or {}).items()},
        "sectors": {k: v for k, v in (doc.get("sectors") or {}).items()},
    }


def fmt_hazards(planet: dict) -> str:
    names = [h["zh"] for h in planet.get("hazards") or [] if h.get("en") not in (None, "None")]
    return " / ".join(names) if names else "—"


def fmt_regions(planet: dict) -> str:
    regs = planet.get("regions") or {}
    if not regs:
        return ""
    return " / ".join(
        f"{r['name']}（{r.get('size_zh') or r.get('size') or '?'}）"
        for r in sorted(regs.values(), key=lambda r: r["index"])
    )


def build_markdown(doc: dict, trans: dict | None = None) -> str:
    trans = trans or {"planets": {}, "sectors": {}}
    name_zh = trans["planets"]
    sector_zh = trans["sectors"]
    planets = doc["planets"]
    sectors = doc["sectors"]
    by_index = sorted(planets.values(), key=lambda p: p["index"])

    def zh_planet(p: dict) -> str:
        return name_zh.get(str(p["index"]), "")

    def zh_sector(name: str) -> str:
        return sector_zh.get(name, "")

    out: list[str] = []
    w = out.append

    w("# 《Helldivers 2》Index 对照表")
    w("")
    w("本文件由 `python scripts/build_index_map.py` 从 `data/reference.json` 生成，**不要手改**。")
    w("")
    w(f"* 参照表生成时间：`{doc.get('generated_at')}`")
    w(f"* 战争 ID：`{doc.get('war_id')}`　星球 **{doc.get('planet_count')}** 颗　星区 **{doc.get('sector_count')}** 个")
    w("* 机器可读版本：`planet_index.csv`")
    if name_zh or sector_zh:
        w(f"* 中文译名 {len(name_zh)} 个星球 / {len(sector_zh)} 个星区，"
          f"来自 `data/translations_zh.json`（手写，不会被覆盖）")
    w("")
    w("---")
    w("")

    # ---------------------------------------------------------------- 怎么用
    w("## 0. 三个容易混淆的「index」")
    w("")
    w("| 名称 | 出现在哪 | 含义 |")
    w("|---|---|---|")
    w("| **星球 index** | `warInfo.planetInfos[].index`、`warStatus.planetStatus[].index`、"
      "本 API 的 `planets[].index` | 0–273 的连续编号，**本表的主键**。缺 263 |")
    w("| **settingsHash** | `warInfo.planetInfos[].settingsHash` | 星球跨战争稳定的身份标识。"
      "站点自己用它（线上包里的 `{WIDOWS_HARBOR: 2768073863, ...}` 枚举） |")
    w("| **载荷里的 `sector` 整数** | `warInfo.planetInfos[].sector` | ⚠️ **不是 wiki 星区**，见下 |")
    w("")
    w("### ⚠️ 载荷里的 `sector` 整数 ≠ wiki 星区")
    w("")
    w("两者是**两套不同的划分**，实测：")
    w("")
    w("| | wiki 星区（本表的 `sector` 字段） | 载荷里的 `sector` 整数 |")
    w("|---|---|---|")
    w("| 取值个数 | 56 个名字 | 53 个整数 |")
    w("| 空间聚集度 | 紧密，成员半径中位数 **0.122** | 多数较紧，但 `sector 0` 半径 **0.926**、`sector 29` 达 1.144 |")
    w("| 一致性 | 一一对应 | **53 个里有 36 个与星区名冲突** |")
    w("")
    w("例：`sector 0` 同时包含 Sol、Trigon、Rigel、Jin Xi、TBD 等散落全图的星球，是个兜底桶；")
    w("而 `Trigon` 这一个星区横跨 `sector` 0 / 32 / 46 / 48 / 49 五个整数。")
    w("")
    w("本表两个都列（`载荷sector` 列），**请按 `星区` 列理解，不要用整数当星区**。")
    w("")
    w("---")
    w("")

    # ---------------------------------------------------------------- 星球主表
    w("## 1. 星球 index 对照表")
    w("")
    w(f"共 {len(by_index)} 颗，按 index 升序。")
    w("")
    w("| index | 星球 | 中文名 | 星区 | 星区中文 | 载荷sector | settingsHash | 生物群系 | 环境危害 | 最大血量 | 初始阵营 | 区域 |")
    w("|---:|---|---|---|---|---:|---|---|---|---:|---|---|")
    for p in by_index:
        biome = p.get("biome") or {}
        sector = p.get("sector") or ""
        w("| {idx} | **{name}** | {zh} | {sector} | {sector_zh} | {ps} | `{hash}` | {biome} | {haz} | {hp:,} | {owner} | {reg} |".format(
            idx=p["index"],
            name=p["name"],
            zh=zh_planet(p) or "—",
            sector=sector or "—",
            sector_zh=zh_sector(sector) or "—",
            ps=p.get("payload_sector") if p.get("payload_sector") is not None else "—",
            hash=p.get("hash"),
            biome=f"{biome.get('en', '?')} / {biome.get('zh', '?')}",
            haz=fmt_hazards(p),
            hp=p.get("max_health") or 0,
            owner=RACE_ZH.get(p.get("initial_owner"), "?"),
            reg=fmt_regions(p) or "—",
        ))
    w("")
    w("---")
    w("")

    # ---------------------------------------------------------------- 星区表
    w("## 2. 星区 → 星球")
    w("")
    w("| 星区 | 中文名 | 星球数 | 星球（index 名称） |")
    w("|---|---|---:|---|")
    for name in sorted(sectors):
        sec = sectors[name]
        members = ", ".join(
            f"{i} {planets[str(i)]['name']}" for i in sec["planets"] if str(i) in planets
        )
        w(f"| **{name}** | {zh_sector(name) or '—'} | {len(sec['planets'])} | {members} |")
    w("")
    w("---")
    w("")

    # ---------------------------------------------------------------- 名称反查
    w("## 3. 按名称反查 index")
    w("")
    w("星区归属也一并给出，方便对照 wiki。")
    w("")
    w("| 星球 | 中文名 | index | 星区 | 星区中文 |")
    w("|---|---|---:|---|---|")
    for p in sorted(by_index, key=lambda x: x["name"]):
        sector = p.get("sector") or ""
        w(f"| {p['name']} | {zh_planet(p) or '—'} | {p['index']} | "
          f"{sector or '—'} | {zh_sector(sector) or '—'} |")
    w("")
    w("---")
    w("")

    # ---------------------------------------------------------------- 按星区聚集
    w("## 4. 按星区分组的 index 区间")
    w("")
    w("| 星区 | 中文名 | index 列表 |")
    w("|---|---|---|")
    for name in sorted(sectors):
        idxs = sectors[name]["planets"]
        w(f"| {name} | {zh_sector(name) or '—'} | {', '.join(str(i) for i in idxs)} |")
    w("")

    return "\n".join(out) + "\n"


def csv_rows(doc: dict, trans: dict | None = None) -> list[list]:
    """CSV 的数据行（不含表头）。单独抽出来是为了让测试能做同步比对。"""
    trans = trans or {"planets": {}, "sectors": {}}
    name_zh = trans["planets"]
    sector_zh = trans["sectors"]
    planets = doc["planets"]
    rows = []
    for p in sorted(planets.values(), key=lambda x: x["index"]):
        biome = p.get("biome") or {}
        pos = p.get("position") or {}
        regs = p.get("regions") or {}
        sector = p.get("sector") or ""
        rows.append([
            p["index"], p["name"], name_zh.get(str(p["index"]), ""),
            sector, sector_zh.get(sector, ""),
            p.get("payload_sector"), p.get("hash"),
            biome.get("en", ""), biome.get("zh", ""),
            fmt_hazards(p).replace("—", ""), p.get("max_health"),
            p.get("initial_owner"), RACE_ZH.get(p.get("initial_owner"), ""),
            pos.get("x"), pos.get("y"), len(regs),
            " | ".join(r["name"] for r in sorted(regs.values(), key=lambda r: r["index"])),
        ])
    return rows


CSV_HEADER = [
    "index", "name", "name_zh", "sector", "sector_zh", "payload_sector",
    "settings_hash", "biome_en", "biome_zh", "hazards_zh", "max_health",
    "initial_owner", "initial_owner_zh", "pos_x", "pos_y", "region_count", "regions",
]


def build_csv(doc: dict, trans: dict | None = None) -> str:
    """写 CSV（utf-8-sig，Excel 直接双击不乱码）。"""
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_HEADER)
        writer.writerows(csv_rows(doc, trans))
    return CSV_PATH


def main() -> int:
    if not os.path.exists(REF_PATH):
        print(f"缺少 {REF_PATH}；请先运行 python scripts/refresh_reference.py", file=sys.stderr)
        return 1

    doc = load()
    trans = load_translations()
    md = build_markdown(doc, trans)
    with open(MD_PATH, "w", encoding="utf-8") as fh:
        fh.write(md)
    build_csv(doc, trans)

    planets = doc["planets"]
    missing_hash = [p["index"] for p in planets.values() if not p.get("hash")]
    missing_ps = [p["index"] for p in planets.values() if p.get("payload_sector") is None]

    print(f"已写入 {os.path.relpath(MD_PATH, ROOT)}  （{len(md):,} 字符）")
    print(f"已写入 {os.path.relpath(CSV_PATH, ROOT)}  （{len(planets)} 行）")
    print(f"  星球 {len(planets)} / 星区 {len(doc['sectors'])}")
    n_planet_zh = len(trans["planets"])
    n_sector_zh = len(trans["sectors"])
    if n_planet_zh or n_sector_zh:
        print(f"  中文译名 {n_planet_zh}/{len(planets)} 个星球、"
              f"{n_sector_zh}/{len(doc['sectors'])} 个星区"
              f"（来自 {os.path.relpath(TRANS_PATH, ROOT)}）")
    if missing_hash:
        print(f"  ⚠️ 缺 settingsHash 的星球: {missing_hash[:10]}")
    if missing_ps:
        print(f"  ⚠️ 缺 payload_sector 的星球: {missing_ps[:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
