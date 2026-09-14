"""搞清 warInfo.planetInfos[].sector 这个整数到底是什么。

假设：它不是 wiki 星区，而是按坐标做的空间分组。用成员星球的坐标离散度验证。
"""

import json
import math
import urllib.request

UA = {"User-Agent": "helldiversbot-check", "Accept": "application/json"}
req = urllib.request.Request(
    "https://helldiverscompanion.com/api/hell-divers-2-api/get-api-data-live",
    headers=UA)
with urllib.request.urlopen(req, timeout=60) as r:
    live = json.loads(r.read())

ref = json.load(open("data/reference.json", encoding="utf-8"))
planets = ref["planets"]

groups: dict[int, list[tuple[int, str, float, float]]] = {}
for info in live["warInfo"]["planetInfos"]:
    entry = planets[str(info["index"])]
    pos = info["position"]
    groups.setdefault(info["sector"], []).append(
        (info["index"], entry["name"], pos["x"], pos["y"]))

print("按载荷里的 sector 整数分组，看成员的坐标是否聚在一起")
print("（如果聚得很紧 -> 它是按坐标分的空间区块；如果散得很开 -> 是别的东西）")
print()
print(f"{'sector':>7} {'星球数':>6} {'质心':>18} {'最大半径':>10}  成员示例")
print("-" * 100)

spreads = []
for sid in sorted(groups):
    members = groups[sid]
    cx = sum(m[2] for m in members) / len(members)
    cy = sum(m[3] for m in members) / len(members)
    radius = max(math.hypot(m[2] - cx, m[3] - cy) for m in members)
    spreads.append((sid, len(members), radius))
    names = ", ".join(m[1] for m in members[:4])
    print(f"{sid:>7} {len(members):>6} ({cx:>7.3f},{cy:>7.3f}) {radius:>10.3f}  {names}")

print()
all_radius = max(r for _, _, r in spreads)
print(f"所有分组的最大半径: {all_radius:.3f}")
print("（银河地图半径约为 1.0，所以半径接近 1 说明该组横跨整个银河）")

# 和 wiki 星区对比
print()
print("对比：按 wiki 星区名分组，半径是多少")
by_sector: dict[str, list[tuple[float, float]]] = {}
for info in live["warInfo"]["planetInfos"]:
    entry = planets[str(info["index"])]
    pos = info["position"]
    by_sector.setdefault(entry["sector"], []).append((pos["x"], pos["y"]))

radii = []
for name, pts in by_sector.items():
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    radii.append((max(math.hypot(p[0] - cx, p[1] - cy) for p in pts), name))
radii.sort(reverse=True)
print(f"  wiki 星区共 {len(radii)} 个")
print(f"  最大半径 {radii[0][0]:.3f} ({radii[0][1]})")
print(f"  中位半径 {radii[len(radii)//2][0]:.3f} ({radii[len(radii)//2][1]})")
print(f"  最小半径 {radii[-1][0]:.3f} ({radii[-1][1]})")
