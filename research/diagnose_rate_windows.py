"""诊断 KARLIA 速率差异：15 分钟窗口之间的自然波动有多大？

站点的速率是「最近一个 CDN 采样点 -> 当前实时载荷」的增量；
我们的速率是「CDN 最近两个采样点」的增量。两者窗口错开约一个采样间隔，
如果相邻窗口本身就能差 10%，那这 0.011 的差异就只是错位，不是口径问题。

    python research/diagnose_rate_windows.py [星球名]
"""

import json
import sys
import urllib.request
from datetime import datetime

BASE = "http://127.0.0.1:8808"
NAME = sys.argv[1] if len(sys.argv) > 1 else "KARLIA"


def get(path, timeout=120):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read())


planet = get("/api/v1/planets/" + NAME)["planet"]
hist = get(f"/api/v1/planets/{planet['index']}/history")
data = hist["history"]

print("=" * 92)
print(f"{planet['name']}  maxHealth={hist['max_health']:,.0f}  样本 {len(data)} 个")
print("=" * 92)
print(f"{'窗口起点':<26}{'窗口终点':<26}{'Δt(s)':>8}{'Δhealth':>12}"
      f"{'人数':>8}{'绝地潜兵%/h':>12}{'净%/h':>10}")
print("-" * 92)

mh = hist["max_health"]
rates = []
for a, b in zip(data, data[1:]):
    ta = datetime.fromisoformat(a["timestampUtc"].replace("Z", "+00:00"))
    tb = datetime.fromisoformat(b["timestampUtc"].replace("Z", "+00:00"))
    dt = (tb - ta).total_seconds()
    if dt <= 60:
        continue
    dh = b["health"] - a["health"]
    net = dh / dt
    regen = a.get("regenPerSecond") or 0.0
    # 满血时 regen 被截断
    if a["health"] >= (a.get("maxHealth") or mh):
        regen = 0.0
    diver = (-net) if a["health"] >= (a.get("maxHealth") or mh) else (regen - net)
    k = 3600 / mh * 100
    diver_pct = diver * k
    net_pct = -net * k
    rates.append((a["timestampUtc"], diver_pct, net_pct, a.get("players") or 0))
    print(f"{a['timestampUtc'][:24]:<26}{b['timestampUtc'][:24]:<26}{dt:>8.0f}"
          f"{dh:>12.0f}{a.get('players') or 0:>8}{diver_pct:>12.4f}{net_pct:>10.4f}")

if len(rates) >= 2:
    vals = [r[1] for r in rates]
    mean = sum(vals) / len(vals)
    spread = max(vals) - min(vals)
    print()
    print(f"绝地潜兵影响力 %/h: 最小 {min(vals):.4f}  最大 {max(vals):.4f}  "
          f"均值 {mean:.4f}  极差 {spread:.4f}")
    if mean:
        print(f"相对极差: {spread / mean * 100:.1f}%  "
              f"（相邻窗口的平均跳变 "
              f"{sum(abs(vals[i+1]-vals[i]) for i in range(len(vals)-1))/max(len(vals)-1,1):.4f}）")
    print()
    print("结论：如果相邻窗口本身就能差这么多，那么与官网的差异属于窗口错位，"
          "不是口径不同。")

print()
print(f"本 API 当前报告: 绝地潜兵 {planet['liberation_rate']['measured'].get('diver_rate_percent_per_hour')} %/h"
      f"  (窗口 {planet['liberation_rate']['measured'].get('from')} -> "
      f"{planet['liberation_rate']['measured'].get('to')})")
print(f"官网读到:        0.113 %/h")
