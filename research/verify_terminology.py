"""确认术语统一后 API 的实际输出。"""

import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8808"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=90) as r:
        return json.loads(r.read())


ref = get("/api/v1/reference")
print("阵营表（/api/v1/reference）:")
for k, v in sorted(ref["factions"].items()):
    print(f"    race={k}  {v['en']:<12} {v['zh']}")

print()
print("中文译名可直接用于过滤：")
for zh in ("超级地球", "终结族", "机器人", "光能者"):
    body = get("/api/v1/planets?owner=" + urllib.parse.quote(zh) + "&limit=1&compact=1")
    if body["count"]:
        p = body["planets"][0]
        print(f"    ?owner={zh:<6} -> {body['count']:>3} 颗   例：{p['name']} ({p['owner_zh']})")
    else:
        print(f"    ?owner={zh:<6} ->   0 颗（当前无人占有）")

print()
print("星球输出里的中文标签：")
for name in ("ZZANIAH PRIME", "HEETH"):
    p = get("/api/v1/planets/" + urllib.parse.quote(name))["planet"]
    print(f"    {p['name']:<16} 占有={p['owner']['zh']:<6} 交战对象={p['enemy_faction']['zh']:<6} "
          f"生物群系={p['biome']['zh']}")

print()
print("星区与总览：")
sec = get("/api/v1/sectors?sort=players")["sectors"][0]
labels = get("/api/v1/sectors")["faction_labels"]
pretty = {labels.get(k, k): v for k, v in sec["owned_by"].items()}
print(f"    {sec['name']}  占有分布={sec['owned_by']}")
print(f"    {' ' * len(sec['name'])}  中文渲染={pretty}")
war = get("/api/v1/war")
print(f"    总在线绝地潜兵={war['totals']['players_online']:,}")
print(f"    faction_labels={war['faction_labels']}")
for key in ("players_by_enemy_faction", "players_by_owner_faction"):
    zh = {war["faction_labels"].get(k, k): v for k, v in war["totals"][key].items()}
    print(f"    {key}: {zh}")
