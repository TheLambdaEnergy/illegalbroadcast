"""确认 QQ 机器人 SDK 在 PyPI 上的正确发行包名。"""

import json
import urllib.error
import urllib.request

CANDIDATES = ["qq-botpy-v2", "qqbot-py-v2", "qq-botpy", "qqbot", "botpy"]


def probe(name: str) -> None:
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "helldiversbot-check"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        print(f"  ✗ {name:16s} 不存在（HTTP {exc.code}）")
        return
    info = data["info"]
    print(f"  ✓ {name:16s} 版本 {info['version']:10s} {info.get('summary', '')[:60]}")
    if info.get("project_urls"):
        for k, v in list(info["project_urls"].items())[:2]:
            print(f"      {k}: {v}")


print("PyPI 查询结果：")
for n in CANDIDATES:
    probe(n)

print()
print("本机已装的是哪个：")
import importlib.metadata as md  # noqa: E402

for dist in md.distributions():
    if any(str(f).startswith("botpy/") for f in (dist.files or [])):
        print(f"  {dist.metadata['Name']} {dist.version}")
        break
