"""拉取站点的 extendedApiInformation 历史，查清 totalPlayerCount 的口径。

这是站点自己记录的「全银河在线潜兵数」时间序列，正好可以用来判定
我们 API 里 players_online / player_share_percent 的分母是否一致。

    python research/probe_extended.py
"""

from __future__ import annotations

import gzip
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "helldiversbot-research", "Accept": "application/json",
      "Accept-Encoding": "gzip"}

CANDIDATES = [
    "https://cdn.helldiverscompanion.com/live/extendedApiInformation/2days.json",
    "https://cdn.helldiverscompanion.com/live/extendedApiInformation/recent.json",
    "https://livedatacdn.helldiverscompanion.com/live/extendedApiInformation/2days.json",
    "https://cdn.helldiverscompanion.com/live/elections/current.json",
    "https://cdn.helldiverscompanion.com/live/personalOrders/current.json",
    "https://cdn.helldiverscompanion.com/live/store/current.json",
    "https://livedatacdn.helldiverscompanion.com/live/freedomallianceradio/stats.json",
    # 也试一下其它可能的汇总文件
    "https://cdn.helldiverscompanion.com/live/warSummary/2days.json",
    "https://cdn.helldiverscompanion.com/live/warSummary/recent.json",
]


def get(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw


def main() -> int:
    got = {}
    for url in CANDIDATES:
        try:
            raw = get(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ {url}\n      {type(exc).__name__}: {exc}")
            continue
        print(f"  ✓ {url}  ({len(raw):,} B)")
        got[url] = raw
        os.makedirs(os.path.join(HERE, "raw"), exist_ok=True)
        name = url.split("/live/")[-1].replace("/", "_")
        with open(os.path.join(HERE, "raw", name), "wb") as fh:
            fh.write(raw)

    ext = got.get(CANDIDATES[0]) or got.get(CANDIDATES[2])
    if not ext:
        print("\n没拿到 extendedApiInformation，无法继续分析")
        return 1

    doc = json.loads(ext)
    data = doc.get("data") or []
    print(f"\nextendedApiInformation: {len(data)} 个采样点")
    if not data:
        return 1

    last = data[-1]
    print(f"最新采样 {last.get('timestampUtc')}")
    print("字段:", sorted(last.keys()))
    print()
    print("最新一条的非统计字段:")
    for k in sorted(last):
        if k in ("totalPlayerCount",) or k.startswith("playerCount"):
            print(f"    {k} = {last[k]}")
    print()
    print("impactMultiplier =", last.get("impactMultiplier"))
    print()

    # 用最近 5 个点的 totalPlayerCount 看看量级
    print("最近 5 个采样点的 totalPlayerCount 与分阵营:")
    for row in data[-5:]:
        parts = [f"{k}={row[k]}" for k in sorted(row) if k.startswith("playerCount")]
        print(f"    {row.get('timestampUtc')}  total={row.get('totalPlayerCount')}  {' '.join(parts)}")

    # 与实时载荷的求和对比
    live_path = os.path.join(HERE, "raw", "live.json")
    if os.path.exists(live_path):
        live = json.load(open(live_path, encoding="utf-8"))
        mine = sum(p.get("players") or 0 for p in live["warStatus"]["planetStatus"])
        theirs = last.get("totalPlayerCount")
        print()
        print("=" * 70)
        print(f"实时载荷 planetStatus.players 求和 = {mine:,}")
        print(f"站点 extendedApiInformation.totalPlayerCount = {theirs:,}")
        if theirs:
            print(f"比值 = {mine / theirs:.4f}   （差值 {mine - theirs:+,}）")
        print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
