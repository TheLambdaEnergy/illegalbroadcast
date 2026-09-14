"""把 planet_index.csv 里手工填的 name_zh / sector_zh 抽出来，存成正式的数据文件。

背景：planet_index.csv 是**生成物**，直接手改会被 `scripts/build_index_map.py`
覆盖。这个脚本负责把已经填进去的中文名抢救到 `data/translations_zh.json`，
之后生成器会读那个文件，两边就一致了。
"""

from __future__ import annotations

import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "planet_index.csv")
OUT_PATH = os.path.join(ROOT, "data", "translations_zh.json")

planets: dict[str, str] = {}
sectors: dict[str, str] = {}

with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
    for row in csv.DictReader(fh):
        index = (row.get("index") or "").strip()
        if not index:
            continue  # 末尾空行
        name_zh = (row.get("name_zh") or "").strip()
        sector_zh = (row.get("sector_zh") or "").strip()
        if name_zh:
            planets[index] = name_zh
        sector = (row.get("sector") or "").strip()
        if sector and sector_zh:
            sectors[sector] = sector_zh

doc = {
    "_comment": (
        "星球与星区的中文译名，供 scripts/build_index_map.py 合并进对照表。"
        "这里是**手写**数据，不会被 refresh_reference.py 覆盖。"
        "缺项留空即可，对照表里会显示为空。"
    ),
    "planets": dict(sorted(planets.items(), key=lambda kv: int(kv[0]))),
    "sectors": dict(sorted(sectors.items())),
}

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, ensure_ascii=False, indent=1)

print(f"已写入 {os.path.relpath(OUT_PATH, ROOT)}")
print(f"  星球译名 {len(planets)} 条 / 星区译名 {len(sectors)} 条")
for k, v in list(planets.items())[:5]:
    print(f"    {k:>4} -> {v}")
print("    ...")
for k, v in sectors.items():
    print(f"    {k:<14} -> {v}")
