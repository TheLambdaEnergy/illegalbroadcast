"""检查原始载荷里的 sector 整数与参照表里的星区名是否一一对应。"""

import json
import urllib.request

UA = {"User-Agent": "helldiversbot-check", "Accept": "application/json"}

print("拉取实时载荷…")
req = urllib.request.Request(
    "https://helldiverscompanion.com/api/hell-divers-2-api/get-api-data-live",
    headers=UA)
with urllib.request.urlopen(req, timeout=60) as r:
    live = json.loads(r.read())

ref = json.load(open("data/reference.json", encoding="utf-8"))
planets = ref["planets"]

pairs: dict[int, dict[str, int]] = {}
missing = []
for info in live["warInfo"]["planetInfos"]:
    entry = planets.get(str(info["index"]))
    if not entry:
        missing.append(info["index"])
        continue
    sid = info["sector"]
    name = entry["sector"]
    pairs.setdefault(sid, {})
    pairs[sid][name] = pairs[sid].get(name, 0) + 1

print(f"planetInfos {len(live['warInfo']['planetInfos'])} 条，参照表缺失 {len(missing)} 条")
print(f"出现 {len(pairs)} 个不同的 sector 整数，参照表有 {ref['sector_count']} 个星区名")
print()

bad = 0
for sid in sorted(pairs):
    names = pairs[sid]
    flag = "" if len(names) == 1 else "   <<< 一个整数对应多个星区名！"
    if len(names) != 1:
        bad += 1
    label = next(iter(names))
    print(f"  sector {sid:>3}  ->  {label:<16} {dict(names)}{flag}")

print()
print(f"冲突数: {bad}")

# 反向：有没有星区名横跨多个整数
by_name: dict[str, set[int]] = {}
for sid, names in pairs.items():
    for n in names:
        by_name.setdefault(n, set()).add(sid)
conflict = {n: sorted(s) for n, s in by_name.items() if len(s) > 1}
print(f"同名星区跨多个整数的: {conflict if conflict else '无'}")

# 参照表里有但载荷里没出现的星区名
used = set(by_name)
unused = sorted(set(ref["sectors"]) - used)
print(f"参照表里有、但当前载荷没出现的星区: {unused}")
