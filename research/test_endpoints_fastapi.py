"""对 FastAPI 前端跑与标准库版相同的端点检查。

    python research/test_endpoints_fastapi.py [base_url]
"""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"

CHECKS = [
    ("/openapi.json", 200),
    ("/docs", 200),
    ("/redoc", 200),
    ("/guide", 200),
    ("/", 200),
    ("/health", 200),
    ("/api/v1/war", 200),
    ("/api/v1/stats", 200),
    ("/api/v1/planets?limit=3&compact=1", 200),
    ("/api/v1/planets?defending=1", 200),
    ("/api/v1/planets?owner=terminids&sort=players&limit=2", 200),
    ("/api/v1/planets?sector=Trigon", 200),
    ("/api/v1/planets?q=cyberstan", 200),
    ("/api/v1/planets?fields=name,players", 200),
    ("/api/v1/planets?pretty=1", 200),
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

fails = []
for path, want in CHECKS:
    try:
        req = urllib.request.Request(BASE + path, headers={"Accept": "*/*"})
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
    if path.endswith("openapi.json"):
        note = f"paths={len(json.loads(body)['paths'])}"
    print(f"{'PASS' if ok else 'FAIL'} {path:52s} {status:>4}  {len(body):>7} B  {note}")
    if not ok:
        fails.append((path, want, status, body[:200]))

print()
print("=" * 72)
print(f"FastAPI 前端: 共 {len(CHECKS)} 项，失败 {len(fails)} 项")
for f in fails:
    print("   ", f)
sys.exit(1 if fails else 0)
