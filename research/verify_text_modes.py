"""核对 `?mode=pt` / `?mode=md` 的真实输出是否符合 README_fancy.md。

    python research/verify_text_modes.py
"""

import json
import urllib.error
import urllib.parse
import urllib.request

BASES = {
    "stdlib": "http://127.0.0.1:8808",
    "fastapi": "http://127.0.0.1:8809",
}


def fetch(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=90) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        with e:
            return e.code, e.headers.get("Content-Type", ""), e.read().decode("utf-8")


def show(title, base, path):
    status, ctype, body = fetch(base, path)
    print(f"--- {title}")
    print(f"    GET {path}")
    print(f"    -> {status}  {ctype}")
    for line in body.rstrip("\n").split("\n"):
        print(f"    | {line}")
    print()
    return status, ctype, body


fails = []

print("=" * 88)
print("文档示例端点 1：单颗星球")
print("=" * 88)
_, c1, t1 = show("mode=pt", BASES["stdlib"], "/api/v1/planet/KARLIA?mode=pt")
_, c2, t2 = show("mode=md", BASES["stdlib"], "/api/v1/planets/KARLIA?mode=md")
if "星球名：KARLIA" not in t1:
    fails.append("pt 输出缺少 星球名：KARLIA")
if t1 != t2:
    fails.append("md 与 pt 输出不一致")
if "text/plain" not in c1:
    fails.append(f"Content-Type 不是 text/plain: {c1}")

_, _, j = show("默认（应仍是 JSON）", BASES["stdlib"], "/api/v1/planet/KARLIA")
try:
    json.loads(j)
except json.JSONDecodeError:
    fails.append("默认模式没有返回合法 JSON")

print("=" * 88)
print("文档示例端点 1b：防御战役星球（敌人入侵）")
print("=" * 88)

# 动态找一颗正在防御的星球，而不是写死 K
d = json.loads(fetch(BASES["stdlib"], "/api/v1/defenses")[2])
if d.get("defenses"):
    ev = d["defenses"][0]
    name = ev["planet_name"]
    q = urllib.parse.quote(name)
    _, _, dt = show(f"mode=pt（{name} 正在防御）", BASES["stdlib"],
                    f"/api/v1/planet/{q}?mode=pt")
    need = ("已防御：", "预测：", "剩余时间：")
    for label in need:
        if label not in dt:
            fails.append(f"防御战输出缺少「{label}」")
    for unwanted in ("解放进度", "解放预计剩余时间"):
        if unwanted in dt:
            fails.append(f"防御战输出不应出现「{unwanted}」")
    if len(dt.strip().split("\n")) != 8:
        fails.append(f"防御战输出应为 8 行，实际 {len(dt.strip().split(chr(10)))} 行")

    # 预测只允许三个值
    pred = next((ln for ln in dt.split("\n") if ln.startswith("预测：")), "")
    if pred not in ("预测：成功", "预测：失败", "预测：不确定"):
        fails.append(f"预测值不合规: {pred!r}")

    # 对照原始 JSON，确认取的是入侵方而不是星球占有者
    raw = json.loads(fetch(BASES["stdlib"], f"/api/v1/planet/{q}")[2])["planet"]
    print(f"    原始 JSON: owner.zh={raw['owner']['zh']}  "
          f"enemy_faction.zh={raw['enemy_faction']['zh']}  "
          f"event.faction.zh={raw['event']['faction']['zh']}")
    print(f"    输出里的所属阵营 -> {next(ln for ln in dt.split(chr(10)) if ln.startswith('所属阵营'))}")
    print()

    # 两种版式的行数差异
    _, _, lt = fetch(BASES["stdlib"], "/api/v1/planet/KARLIA?mode=pt")
    print(f"    解放版式 {len(lt.strip().split(chr(10)))} 行 / "
          f"防御版式 {len(dt.strip().split(chr(10)))} 行")
    print()
else:
    print("    当前没有防御战，跳过\n")

print("=" * 88)
print("文档示例端点 2：游戏内快讯")
print("=" * 88)
_, _, d1 = show("mode=pt（只应有一条）", BASES["stdlib"], "/api/v1/dispatches?mode=pt")
if len(d1.rstrip("\n").split("\n")) < 2:
    fails.append("快讯 pt 输出少于 2 行")
if not d1.startswith("时间："):
    fails.append("快讯 pt 输出没有以「时间：」开头")

print("=" * 88)
print("两个前端的输出格式是否一致")
print("=" * 88)
print("注意：这是两个**独立运行的服务器**，各自轮询、各有缓存，快照天然有时差，")
print("所以这里比的是「格式是否一致」而不是「字节是否相同」。")
print("字节级一致性由 tests/test_textview.py::TestFrontendsAgreeOnText 用共享实例覆盖。")
print()


def shape_of(text: str) -> list[str]:
    """只保留每行的标签部分与行数，忽略具体数值。"""
    out = []
    for line in text.rstrip("\n").split("\n"):
        out.append(line.split("：", 1)[0] + "：" if "：" in line else f"<{len(line)}字>")
    return out


for path in ("/api/v1/planet/KARLIA?mode=pt", "/api/v1/planet/KARLIA?mode=md",
             "/api/v1/dispatches?mode=pt"):
    a = fetch(BASES["stdlib"], path)[2]
    b = fetch(BASES["fastapi"], path)[2]
    same = shape_of(a) == shape_of(b)
    print(f"  {'OK ' if same else 'DIFF'} {path:44s} 行数与标签一致={same}")
    if not same:
        fails.append(f"{path} 两个前端输出格式不一致")
        print("       stdlib :", shape_of(a))
        print("       fastapi:", shape_of(b))
    else:
        # 找出到底哪里不同，确认只是数字
        if a != b:
            for i, (la, lb) in enumerate(zip(a.split("\n"), b.split("\n")), 1):
                if la != lb:
                    print(f"       第 {i} 行数值不同（属于时差）：")
                    print(f"         stdlib : {la}")
                    print(f"         fastapi: {lb}")
                    break

for path in ("/api/v1/planet/KARLIA", "/api/v1/dispatches"):
    a = fetch(BASES["stdlib"], path)[2]
    b = fetch(BASES["fastapi"], path)[2]
    same = sorted(json.loads(a)) == sorted(json.loads(b))
    print(f"  {'OK ' if same else 'DIFF'} {path:44s} JSON 字段集合一致={same}")
    if not same:
        fails.append(f"{path} 两个前端字段集合不一致")

print()
print("=" * 88)
print("其它端点不受影响（应仍为 JSON）")
print("=" * 88)
for path in ("/api/v1/planets?mode=pt", "/api/v1/sectors?mode=pt",
             "/api/v1/war?mode=pt", "/api/v1/defenses?mode=pt"):
    status, ctype, _ = fetch(BASES["stdlib"], path)
    ok = "application/json" in ctype
    print(f"  {'OK ' if ok else 'DIFF'} {path:36s} {status}  {ctype}")
    if not ok:
        fails.append(f"{path} 被 mode 影响了")

print()
print("=" * 88)
print(f"结论: {'全部通过' if not fails else '存在问题'}")
for f in fails:
    print("  !!", f)
raise SystemExit(1 if fails else 0)
