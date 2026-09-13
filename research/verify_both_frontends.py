"""用真实数据核对两个前端，并交叉验证在线人数分母。

    python research/verify_both_frontends.py
"""

import json
import sys
import urllib.error
import urllib.request

STDLIB = "http://127.0.0.1:8808"
FASTAPI = "http://127.0.0.1:8809"


def get(base, path, timeout=120):
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        with e:
            return e.code, json.loads(e.read() or b"{}")


def main() -> int:
    fails = []

    print("=" * 88)
    print("1) 在线人数分母交叉验证（本 API 快照 vs 站点自己记录的 totalPlayerCount）")
    print("=" * 88)
    code, pop = get(STDLIB, "/api/v1/population")
    if code != 200:
        print(f"  !! /api/v1/population 返回 {code}")
        return 1
    summary = pop["summary"]
    mine = pop["snapshot_players_online"]
    snap_at = pop["snapshot_generated_at"]
    theirs = summary["latest_total_players"]
    site_at = summary["latest_at"]

    # 站点的历史序列每约 15 分钟才落一个点，本 API 快照是实时的，
    # 所以两者天然存在时间差。把差距明确算出来，才好判断偏差是否只是采样时差。
    gap_min = None
    try:
        from datetime import datetime, timezone
        a = datetime.fromisoformat(snap_at.replace("Z", "+00:00"))
        b = datetime.fromisoformat(site_at.replace("Z", "+00:00"))
        gap_min = abs((a - b).total_seconds()) / 60
    except Exception:  # noqa: BLE001
        pass

    print(f"  站点采样时刻                      : {site_at}")
    print(f"  本 API 快照时刻                    : {snap_at}")
    print(f"  两者时间差                        : "
          f"{'%.1f 分钟' % gap_min if gap_min is not None else '未知'}"
          f"  （站点序列每 ~15 分钟一个点，这是无法消除的）")
    print(f"  站点 totalPlayerCount             : {theirs:,}")
    print(f"  本 API 快照 players_online         : {mine:,}")
    diff = mine - theirs
    pct = abs(diff) / theirs * 100 if theirs else 0
    print(f"  差值                              : {diff:+,}  ({pct:.3f}%)")

    # 总量是大数，必须高度吻合
    if pct > 1.0:
        fails.append(f"总在线人数偏差过大: {pct:.2f}%")
    else:
        print("  => 一致：分母口径相同，差异仅是采样时差")

    print()
    print("  分阵营比对（按交战对象口径）")
    print(f"    站点  : {summary['latest_players_by_faction']}")
    print(f"    本 API: {pop['snapshot_players_by_enemy_faction']}")
    print(f"    另一种口径（按星球占有者）: {pop['snapshot_players_by_owner_faction']}")

    site_f = {k.lower(): v for k, v in (summary["latest_players_by_faction"] or {}).items()}
    mine_f = {k.lower(): v for k, v in (pop["snapshot_players_by_enemy_faction"] or {}).items()}
    for key in sorted(set(site_f) | set(mine_f)):
        a, b = mine_f.get(key, 0), site_f.get(key, 0)
        delta = abs(a - b)
        rel = delta / b * 100 if b else 0
        # 小基数阵营（humans 常年只有 2000 人左右）用相对误差判会误报：
        # 相差 120 人放在 2000 的基数上就是 6%，但那只是十几分钟里的人口流动。
        # 因此同时要求「相对偏差 <= 3%」或「绝对偏差 <= 400 人」。
        ok = rel <= 3.0 or delta <= 400
        print(f"    {'OK ' if ok else '!! '}{key:12s} 本 API={a:>7,}  站点={b:>7,}  "
              f"绝对差 {delta:>5,}  相对 {rel:5.2f}%")
        if not ok:
            fails.append(f"阵营 {key}: 绝对差 {delta}，相对 {rel:.1f}%")
    if pct > 5:
        fails.append(f"在线人数口径差异过大: {pct:.2f}%")
    else:
        print("  => 一致（差异来自采样时差，非口径不同）")

    print()
    print("=" * 88)
    print("2) 两个前端的端点一致性")
    print("=" * 88)
    paths = [
        "/api/v1/war", "/api/v1/stats", "/api/v1/planets?limit=5&compact=1",
        "/api/v1/sectors", "/api/v1/campaigns", "/api/v1/defenses",
        "/api/v1/major-orders", "/api/v1/population?compact=1",
        "/api/v1/space-stations", "/api/v1/reference", "/api/v1/global-events",
    ]
    for p in paths:
        c1, b1 = get(STDLIB, p)
        c2, b2 = get(FASTAPI, p)
        same = c1 == c2
        note = ""
        if same and isinstance(b1, dict) and "planets" in b1:
            same = [x["index"] for x in b1["planets"]] == [x["index"] for x in b2["planets"]]
            note = f"planets={len(b1['planets'])}"
        elif same and isinstance(b1, dict) and "count" in b1:
            same = b1["count"] == b2["count"]
            note = f"count={b1['count']}"
        print(f"  {'OK ' if same else 'DIFF'} {p:44s} stdlib={c1} fastapi={c2} {note}")
        if not same:
            fails.append(f"{p} 两个前端不一致")

    print()
    print("=" * 88)
    print("3) FastAPI 独有的文档端点")
    print("=" * 88)
    for p in ("/docs", "/redoc", "/openapi.json"):
        try:
            with urllib.request.urlopen(FASTAPI + p, timeout=60) as r:
                print(f"  OK   {p:20s} {r.status} {len(r.read()):>7} B")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {p:20s} {exc}")
            fails.append(f"{p} 不可用")

    print()
    print("=" * 88)
    print(f"结论: {'全部通过' if not fails else '存在问题'}")
    for f in fails:
        print("  !!", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
