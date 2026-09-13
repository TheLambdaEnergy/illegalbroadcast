"""精确检查 pydantic-core 是否有适配 cp314 + win_amd64 的 wheel。

上一版脚本用手写打分，`"any" in filename` 会被 `manylinux` 命中（m-any-linux），
于是误判成"有可用 wheel"。这里改成严格解析 wheel 文件名标签。
"""

from __future__ import annotations

import json
import sys
import sysconfig
import urllib.request

WANT_PY = f"cp{sys.version_info.major}{sys.version_info.minor}"
WANT_PLAT = "win_amd64"

ABI_OK = {WANT_PY, f"{WANT_PY}t"}          # 3.14 及其 free-threaded 变体
PLAT_OK = {WANT_PLAT, "any"}


def wheel_tags(filename: str) -> tuple[str, str, str] | None:
    """wheel 文件名的规范形式是 {name}-{ver}(-{build})?-{pytag}-{abitag}-{plattag}.whl"""
    if not filename.endswith(".whl"):
        return None
    stem = filename[:-4]
    parts = stem.split("-")
    if len(parts) < 5:
        return None
    return parts[-3], parts[-2], parts[-1]


def matches(filename: str) -> bool:
    tags = wheel_tags(filename)
    if tags is None:
        return False
    py_tag, abi_tag, plat_tag = tags
    py_ok = any(t in ABIOK for t in py_tag.split(".")) or py_tag in ("py3", "py2.py3")
    plat_ok = any(t in PLATOK for t in plat_tag.split("."))
    return py_ok and plat_ok


ABIOK = ABI_OK
PLATOK = PLAT_OK


def main() -> int:
    print(f"目标解释器标签: {WANT_PY} / 平台: {WANT_PLAT}")
    print()

    for name in ("pydantic-core", "uvicorn", "fastapi"):
        url = f"https://pypi.org/pypi/{name}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "helldiversbot-research"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        version = data["info"]["version"]
        files = data["releases"].get(version) or []
        names = [f["filename"] for f in files if f["filename"].endswith(".whl")]
        good = [n for n in names if matches(n)]

        print(f"### {name} {version}   共 {len(names)} 个 wheel")
        if good:
            for n in good:
                print(f"    ✓ {n}")
        else:
            print("    ✗ 没有匹配的 wheel")
            plat_tags = sorted({wheel_tags(n)[2] for n in names if wheel_tags(n)})
            print(f"    可用平台标签: {plat_tags}")
            py_tags = sorted({wheel_tags(n)[0] for n in names if wheel_tags(n)})
            print(f"    可用 Python 标签: {py_tags}")
        print()

    # 结论
    pc = json.loads(urllib.request.urlopen(urllib.request.Request(
        "https://pypi.org/pypi/pydantic-core/json",
        headers={"User-Agent": "helldiversbot-research"}), timeout=30).read())
    ver = pc["info"]["version"]
    ok = [f["filename"] for f in pc["releases"].get(ver) or [] if matches(f["filename"])]
    print("=" * 70)
    if ok:
        print("结论: pydantic-core 在 cp314/win_amd64 上有 wheel -> FastAPI 可行")
        return 0
    print("结论: pydantic-core 缺少 cp314/win_amd64 wheel -> FastAPI 在 Python 3.14 上装不了")
    return 1


if __name__ == "__main__":
    sys.exit(main())
