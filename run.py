#!/usr/bin/env python3
"""一键启动《Helldivers 2》实时战报 API。

默认用**纯标准库**服务器（零依赖，开箱即用）:

    python run.py
    python run.py --port 9000
    python run.py --no-poller

想用 FastAPI（Swagger UI + ReDoc）:

    python scripts/vendor_deps.py                 # 把依赖装到 .deps/
    python run.py --fastapi                       # 会自动把 .deps 加进 sys.path

环境变量覆盖见 hd2api/config.py。
"""

from __future__ import annotations

import argparse
import os
import sys

# 尽早把自带的 .deps/ 加进搜索路径，这样 --fastapi 不用手动设 PYTHONPATH
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEPS = os.path.join(_HERE, ".deps")
if os.path.isdir(_DEPS) and _DEPS not in sys.path:
    sys.path.insert(0, _DEPS)

from hd2api import config  # noqa: E402
from hd2api.web import serve  # noqa: E402


def _fastapi_available() -> bool:
    try:
        from hd2api import asgi  # noqa: F401
        return asgi.FASTAPI_AVAILABLE
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    ap = argparse.ArgumentParser(
        description="启动 Helldivers 2 战报 API",
        epilog="默认走纯标准库实现；--fastapi 需要先运行 python scripts/vendor_deps.py",
    )
    ap.add_argument("--host", default=config.HOST)
    ap.add_argument("--port", type=int, default=config.PORT)
    ap.add_argument("--no-poller", action="store_true",
                    help="不启动后台轮询线程，改为按需刷新")
    ap.add_argument("--fastapi", action="store_true",
                    help="用 FastAPI + uvicorn（需要 .deps/ 里的依赖）")
    ap.add_argument("-v", "--verbose", action="store_true", help="打印访问日志")
    args = ap.parse_args()

    if args.no_poller:
        config.ENABLE_POLLER = False

    try:
        if args.fastapi:
            if not _fastapi_available():
                print("FastAPI 不可用。请先运行:  python scripts/vendor_deps.py", file=sys.stderr)
                try:
                    from hd2api import asgi
                    print(f"原始错误: {asgi.IMPORT_ERROR}", file=sys.stderr)
                except Exception:  # noqa: BLE001
                    pass
                return 1
            from hd2api.asgi import serve as serve_asgi
            serve_asgi(host=args.host, port=args.port)
        else:
            serve(host=args.host, port=args.port, quiet=not args.verbose)
    except OSError as exc:
        print(f"启动失败: {exc}", file=sys.stderr)
        print("端口可能被占用，试试 --port 8809", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
