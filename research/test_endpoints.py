"""端点检查（标准库前端与 FastAPI 前端通用）。

    python research/test_endpoints.py                          # 默认检查 127.0.0.1:8808
    python research/test_endpoints.py http://127.0.0.1:8809    # 检查 FastAPI 前端
    python research/test_endpoints.py --both                   # 两个都查

FastAPI 前端多出 /redoc 与 Swagger 版 /docs，脚本会自动识别并调整预期。
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

STDLIB = "http://127.0.0.1:8808"
FASTAPI = "http://127.0.0.1:8809"

# (路径, 期望状态码)
COMMON = [
    ("/", 200),
    ("/health", 200),
    ("/openapi.json", 200),
    ("/docs", 200),
    ("/api/v1/war", 200),
    ("/api/v1/stats", 200),
    ("/api/v1/population", 200),
    ("/api/v1/population?hours=6&compact=1", 200),
    ("/api/v1/planets?limit=3&compact=1", 200),
    ("/api/v1/planets?defending=1", 200),
    ("/api/v1/planets?owner=terminids&sort=players&limit=2", 200),
    ("/api/v1/planets?sector=Trigon", 200),
    ("/api/v1/planets?q=cyberstan", 200),
    ("/api/v1/planets?fields=name,players", 200),
    ("/api/v1/planets?active=1&sort=rate&order=desc", 200),
    ("/api/v1/planets/114", 200),
    ("/api/v1/planets/aurora-bay", 200),
    ("/api/v1/planets/114/regions", 200),
    ("/api/v1/planets/114/history", 200),
    ("/api/v1/sectors", 200),
    ("/api/v1/sectors/Altus", 200),
    ("/api/v1/campaigns", 200),
    ("/api/v1/defenses", 200),
    ("/api/v1/defenses?outcome=defense_will_fail", 200),
    ("/api/v1/major-orders", 200),
    ("/api/v1/major-orders?all=1", 200),
    ("/api/v1/dispatches?limit=2", 200),
    ("/api/v1/news?limit=1", 200),
    ("/api/v1/space-stations", 200),
    ("/api/v1/global-events", 200),
    ("/api/v1/reference", 200),
    ("/api/v1/raw?part=warStatus", 200),
    # 错误路径
    ("/api/v1/planets?q=a", 400),
    ("/api/v1/planets?owner=nope", 400),
    ("/api/v1/planets/99999", 404),
    ("/api/v1/nope", 404),
]

FASTAPI_ONLY = [("/redoc", 200), ("/guide", 200)]


def check(base: str, extra: list[tuple[str, int]]) -> int:
    print(f"===== {base} =====")
    fails = []
    for path, want in COMMON + extra:
        url = base + path
        try:
            req = urllib.request.Request(url, headers={"Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=120) as r:
                body, status = r.read(), r.status
        except urllib.error.HTTPError as e:
            with e:
                body, status = e.read(), e.code
        except Exception as e:  # noqa: BLE001
            print(f"ERR  {path:52s} {e}")
            fails.append((path, str(e)))
            continue

        ok = status == want
        note = ""
        if path.startswith("/openapi.json") and ok:
            note = f"paths={len(json.loads(body)['paths'])}"
        print(f"{'PASS' if ok else 'FAIL'} {path:52s} {status:>4}  {len(body):>8} B  {note}")
        if not ok:
            fails.append((path, want, status, body[:160]))

    print(f"\n共 {len(COMMON) + len(extra)} 项，失败 {len(fails)} 项")
    for f in fails:
        print("   ", f)
    return 1 if fails else 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        return check(STDLIB, [])
    if args[0] == "--both":
        rc = check(STDLIB, [])
        print()
        rc |= check(FASTAPI, FASTAPI_ONLY)
        return rc
    return check(args[0], FASTAPI_ONLY if "8809" in args[0] else [])


if __name__ == "__main__":
    sys.exit(main())
