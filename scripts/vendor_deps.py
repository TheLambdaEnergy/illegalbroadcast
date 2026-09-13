"""绕过 pip，直接从 PyPI 下载 wheel 并解压到 .deps/。

为什么需要这个脚本
------------------
本机的 pip 在沙箱里跑不起来：它下载元数据时会往 `tempfile.gettempdir()`
写文件，而那一步被文件沙箱拒绝（`PermissionError: [Errno 13]`），
无论把 TMPDIR 指到工作区内还是区外都一样。

所以这里自己做一遍 pip 的活儿：
  1. 查 PyPI 的 JSON API 拿到每个包的 wheel 列表；
  2. 按当前解释器的 wheel 标签挑最合适的（优先 cp3xx-win_amd64，其次 py3-none-any）；
  3. 读 wheel 里 METADATA 的 `Requires-Dist` 递归解析依赖；
  4. 全部解压到 .deps/。

装好之后用 `PYTHONPATH=.deps` 就能 import fastapi / uvicorn。

    python scripts/vendor_deps.py                 # 装 FastAPI（可选前端）
    python scripts/vendor_deps.py --list          # 只解析依赖不下载
    python scripts/vendor_deps.py --clean         # 先清空 .deps
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
import sysconfig
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPS = os.path.join(ROOT, ".deps")
PYPI = "https://pypi.org/pypi/{name}/json"

# 想装的顶层包
ROOTS = ["fastapi", "uvicorn"]

PY_TAG = f"cp{sys.version_info.major}{sys.version_info.minor}"
PLAT_PREFERENCE = ["win_amd64", "win32", "any"]
# 自由线程构建（cp314t）与普通 GIL 构建的扩展模块互不兼容，
# 必须按当前解释器是否启用 GIL 来过滤 ABI 标签，否则会装到一个 import 不了的轮子。
FREE_THREADED = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
ABI_TAG = PY_TAG + ("t" if FREE_THREADED else "")
VALID_ABIS = {ABI_TAG, "abi3", "none"}

MARKER_ENV = {
    "sys_platform": sys.platform,
    "os_name": os.name,
    "platform_system": "Windows" if os.name == "nt" else "Linux",
    "platform_machine": sysconfig.get_platform().split("-")[-1],
    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
    "python_full_version": sys.version.split()[0],
    "extra": "",
}


# --------------------------------------------------------------------- 工具
def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "helldiversbot-vendor"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def http_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "helldiversbot-vendor"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def parse_wheel_name(filename: str) -> tuple[str, str, str] | None:
    """返回 (python_tag, abi_tag, platform_tag)。"""
    if not filename.endswith(".whl"):
        return None
    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return None
    return parts[-3], parts[-2], parts[-1]


def wheel_score(filename: str) -> int:
    """越小越好。999 表示不兼容。"""
    tags = parse_wheel_name(filename)
    if tags is None:
        return 999
    py_tag, abi_tag, plat_tag = tags
    py_tags = py_tag.split(".")
    abi_tags = abi_tag.split(".")
    plat_tags = plat_tag.split(".")

    # 纯 Python 轮子：任何解释器都能用
    if "py3" in py_tags or "py2.py3" in py_tags:
        return 10 if "any" in plat_tags else 11

    if PY_TAG not in py_tags:
        return 999
    # 关键：ABI 必须匹配当前构建（GIL / 自由线程不能混用）
    if not (VALID_ABIS & set(abi_tags)):
        return 999
    for i, want in enumerate(PLAT_PREFERENCE):
        if want in plat_tags:
            return i
    return 50


def marker_ok(marker: str | None) -> bool:
    """粗略评估环境标记。只处理常见形式，拿不准就当作满足。"""
    if not marker:
        return True
    expr = marker.strip()
    if "extra" in expr:
        # 我们不要任何 optional extra
        return False
    expr = expr.replace(" and ", " and ").replace(" or ", " or ")

    def repl(m: re.Match) -> str:
        name, op, value = m.group(1), m.group(2), m.group(3)
        actual = MARKER_ENV.get(name)
        if actual is None:
            return "True"
        return json.dumps(f"{actual}{op}{value}")

    # 把 `name op "value"` 换成对一个常量字符串表达式的比较
    expr = re.sub(r'(\w+)\s*(==|!=|>=|<=|>|<)\s*"([^"]*)"', repl, expr)
    try:
        return bool(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307
    except Exception:  # noqa: BLE001
        return True


def strip_extras(req: str) -> str:
    """`uvicorn[standard]>=0.30` -> `uvicorn>=0.30`"""
    return re.sub(r"\[[^\]]*\]", "", req).strip()


def req_name_version(req: str) -> tuple[str, str | None]:
    req = strip_extras(req)
    m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(.*)$", req)
    if not m:
        return req.lower(), None
    name = m.group(1).lower().replace("_", "-")
    rest = m.group(2).strip()
    vm = re.search(r"==\s*([0-9][0-9A-Za-z.\-]*)", rest)
    return name, (vm.group(1) if vm else None)


# --------------------------------------------------------------------- 解析
def resolve(roots: list[str]) -> dict[str, dict]:
    """广度优先解析依赖，返回 {包名: {version, filename, url, requires}}。"""
    chosen: dict[str, dict] = {}
    queue: list[tuple[str, str | None]] = [(r, None) for r in roots]
    seen: set[str] = set()

    while queue:
        name, pinned = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        if name in ("python",):
            continue

        try:
            data = http_json(PYPI.format(name=name))
        except Exception as exc:  # noqa: BLE001
            print(f"  ! 跳过 {name}: {exc}")
            continue

        version = pinned or data["info"]["version"]
        files = data["releases"].get(version) or []
        wheels = [f for f in files if f["filename"].endswith(".whl")]
        if not wheels:
            print(f"  ! {name} {version} 没有 wheel（需要源码编译），跳过")
            continue
        wheels.sort(key=lambda f: wheel_score(f["filename"]))
        best = wheels[0]
        if wheel_score(best["filename"]) >= 999:
            print(f"  ! {name} {version} 没有适配 {PY_TAG} 的 wheel，跳过")
            continue

        chosen[name] = {
            "version": version,
            "filename": best["filename"],
            "url": best["url"],
            "requires": [],
        }

        # 读 METADATA 拿依赖
        try:
            raw = http_bytes(best["url"])
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                meta_name = next(n for n in zf.namelist()
                                 if n.endswith(".dist-info/METADATA"))
                meta = zf.read(meta_name).decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {name} 读取 METADATA 失败: {exc}")
            continue

        for line in meta.splitlines():
            if not line.startswith("Requires-Dist:"):
                continue
            spec = line.split(":", 1)[1].strip()
            if ";" in spec:
                dep, marker = spec.split(";", 1)
                if not marker_ok(marker):
                    continue
            else:
                dep = spec
            dep_name, dep_ver = req_name_version(dep)
            if dep_name and dep_name not in seen:
                queue.append((dep_name, dep_ver))
                chosen[name]["requires"].append(dep_name)

    return chosen


# --------------------------------------------------------------------- 安装
def install(chosen: dict[str, dict]) -> None:
    os.makedirs(DEPS, exist_ok=True)
    for name, info in sorted(chosen.items()):
        raw = http_bytes(info["url"])
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            zf.extractall(DEPS)
        info["bytes"] = len(raw)
        print(f"  ✓ {name:22s} {info['version']:12s} {info['filename']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="从 PyPI 手动 vendoring 依赖到 .deps/")
    ap.add_argument("--list", action="store_true", help="只解析依赖，不下载")
    ap.add_argument("--clean", action="store_true", help="先删除 .deps/")
    ap.add_argument("--packages", nargs="*", default=ROOTS)
    args = ap.parse_args()

    if args.clean and os.path.isdir(DEPS):
        shutil.rmtree(DEPS, ignore_errors=True)
        print(f"已清空 {DEPS}")

    print(f"解释器 {sys.version.split()[0]} ({PY_TAG})  ->  {DEPS}")
    print("解析依赖…")
    chosen = resolve(args.packages)
    print(f"\n解析到 {len(chosen)} 个包:")
    for name, info in sorted(chosen.items()):
        print(f"    {name:22s} {info['version']}")
        if info["requires"]:
            print(f"        -> {', '.join(info['requires'])}")

    if args.list:
        return 0

    print("\n下载并解压…")
    install(chosen)

    print(f"\n完成。用法:")
    print(f'    $env:PYTHONPATH="{DEPS}"')
    print("    python run.py --fastapi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
