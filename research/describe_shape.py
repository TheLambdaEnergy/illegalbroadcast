"""输出 live 载荷的结构树与字段分布 -> research/analysis/shape.txt

默认直接抓上游；也可以用 --from-api 走本地服务的 /api/v1/raw（省一次请求）。

    python research/describe_shape.py
    python research/describe_shape.py --from-api http://127.0.0.1:8808
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "analysis", "shape.txt")
LIVE = "https://helldiverscompanion.com/api/hell-divers-2-api/get-api-data-live"

OUT_LINES: list[str] = []


def p(*a) -> None:
    line = " ".join(str(x) for x in a)
    OUT_LINES.append(line)
    print(line)


def shape(v, depth: int = 0, maxdepth: int = 3, maxkeys: int = 40) -> str:
    pad = "  " * depth
    if isinstance(v, dict):
        if depth >= maxdepth:
            return f"dict[{len(v)}]"
        lines = [f"dict[{len(v)}] {{"]
        for k, vv in list(v.items())[:maxkeys]:
            lines.append(f"{pad}  {k}: {shape(vv, depth + 1, maxdepth, maxkeys)}")
        if len(v) > maxkeys:
            lines.append(f"{pad}  ... +{len(v) - maxkeys} more keys")
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if isinstance(v, list):
        if not v:
            return "list[0]"
        return f"list[{len(v)}] of {shape(v[0], depth + 1, maxdepth, maxkeys)}"
    return f"{type(v).__name__} {v!r}"[:140]


def fetch(from_api: str | None) -> dict:
    url = (from_api.rstrip("/") + "/api/v1/raw") if from_api else LIVE
    req = urllib.request.Request(url, headers={
        "User-Agent": "helldiversbot-research", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-api", help="本地 API 基址，例如 http://127.0.0.1:8808")
    args = ap.parse_args()

    live = fetch(args.from_api)
    p("=" * 100)
    p("### live 载荷结构树（上游 helldiverscompanion.com）")
    p("=" * 100)
    p(shape(live, maxdepth=3))
    p()

    from collections import Counter
    infos = live["warInfo"]["planetInfos"]
    statuses = live["warStatus"]["planetStatus"]

    p("=" * 100)
    p("### 关键字段分布（用于确认哪些 ID 是「被抹掉的」）")
    p("=" * 100)
    p("planetInfos 数量:", len(infos))
    p("planetStatus 数量:", len(statuses))
    p("planetInfos[].planetNameId32 分布:", Counter(x.get("planetNameId32") for x in infos).most_common(5))
    p("planetInfos[].planetBiomeId32 分布:", Counter(x.get("planetBiomeId32") for x in infos).most_common(5))
    p("planetInfos[].sector 去重数:", len({x.get("sector") for x in infos}))
    p("planetStatus[].owner 分布:", Counter(x.get("owner") for x in statuses).most_common())
    p("planetStatus 键:", sorted({k for x in statuses for k in x}))
    p("planetInfos  键:", sorted({k for x in infos for k in x}))
    p("warStatus.planetRegions 键:",
      sorted({k for x in live["warStatus"].get("planetRegions") or [] for k in x}))
    p("warStats.planets_stats 键:",
      sorted({k for x in live["warStats"].get("planets_stats") or [] for k in x}))
    p("warStats.planets_stats 里的哨兵记录（index<0）:",
      [x.get("planetIndex") for x in live["warStats"].get("planets_stats") or []
       if (x.get("planetIndex") or 0) < 0])
    p("索引缺号:",
      sorted(set(range(0, max(x["index"] for x in infos) + 1)) - {x["index"] for x in infos}))
    p()
    p("### 顶层键")
    p(sorted(live.keys()))
    p("### warStatus 键")
    p(sorted(live["warStatus"].keys()))
    p("### warInfo 键")
    p(sorted(live["warInfo"].keys()))
    p("### 一条完整的 planetStatus 样例")
    p(json.dumps(statuses[0], ensure_ascii=False))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT_LINES))
    print(f"\n已写入 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
