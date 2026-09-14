"""FastAPI/ASGI 前端的测试。

不依赖 httpx 或 TestClient —— 这里直接按 ASGI 协议调用应用，
所以哪怕只装了 fastapi（没装 httpx）也能跑。

未安装 FastAPI 时整个模块会被 skip，标准库版的测试不受影响。

    python tests/test_asgi.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 仓库自带的 .deps/（scripts/vendor_deps.py 装出来的）
_DEPS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".deps")
if os.path.isdir(_DEPS) and _DEPS not in sys.path:
    sys.path.insert(0, _DEPS)

from fixtures import AsgiHarness, StubService  # noqa: E402

try:
    from hd2api.asgi import FASTAPI_AVAILABLE, IMPORT_ERROR, create_app
except Exception as exc:  # noqa: BLE001
    FASTAPI_AVAILABLE = False
    IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

requires_fastapi = unittest.skipUnless(
    FASTAPI_AVAILABLE, f"未安装 FastAPI（{IMPORT_ERROR}）；先跑 python scripts/vendor_deps.py"
)


@requires_fastapi
class TestFastApiApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = StubService()
        cls.app = create_app(cls.service)
        cls.h = AsgiHarness(cls.app)

    def json(self, path, query="", expect=200):
        status, headers, body = self.h.request(path, query)
        self.assertEqual(status, expect,
                         f"{path}?{query} 期望 {expect} 实际 {status}: {body[:200]!r}")
        self.assertIn("application/json", headers.get("content-type", ""))
        return json.loads(body)

    # ------------------------------------------------------------ 基本路由
    def test_root_and_health(self):
        self.assertEqual(self.json("/")["name"], "helldiversbot API")
        self.assertEqual(self.json("/health")["state"], "ok")

    def test_openapi_is_served_with_tags_and_params(self):
        spec = self.json("/openapi.json")
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertIn("/api/v1/planets", spec["paths"])
        self.assertIn("/api/v1/planets/{key}", spec["paths"])
        params = {p["name"] for p in spec["paths"]["/api/v1/planets"]["get"]["parameters"]}
        self.assertIn("sort", params)
        self.assertIn("compact", params)
        # 每个 operation 都要有 summary 和 tags，否则 Swagger 里会出现空白条目
        for path, methods in spec["paths"].items():
            for method, op in methods.items():
                self.assertTrue(op.get("summary"), f"{method} {path} 缺少 summary")
                self.assertTrue(op.get("tags"), f"{method} {path} 缺少 tags")

    def test_docs_and_redoc_and_guide(self):
        for path in ("/docs", "/redoc", "/guide"):
            status, headers, body = self.h.request(path)
            self.assertEqual(status, 200, path)
            self.assertIn("text/html", headers.get("content-type", ""))
            self.assertGreater(len(body), 200, path)

    # ------------------------------------------------------------ 业务路由
    def test_war_and_totals(self):
        body = self.json("/api/v1/war")
        self.assertEqual(body["war"]["war_id"], 801)
        self.assertEqual(body["totals"]["players_online"], 5010)
        # 两种口径都要有：按占有者 / 按正在对抗的敌人
        self.assertIn("players_by_owner_faction", body["totals"])
        self.assertIn("players_by_enemy_faction", body["totals"])
        # 己方星球被打时，人算在攻击方名下
        self.assertEqual(
            body["totals"]["players_by_enemy_faction"].get("Automatons"), 5010)
        self.assertEqual(
            body["totals"]["players_by_owner_faction"].get("Humans"), 10)

    def test_planets_filtering_parity_with_stdlib(self):
        allp = self.json("/api/v1/planets")
        self.assertEqual(allp["count"], 3)
        self.assertEqual([p["index"] for p in allp["planets"]], [1, 0, 2])

        self.assertEqual(self.json("/api/v1/planets", "limit=1")["returned"], 1)
        self.assertEqual(self.json("/api/v1/planets", "owner=automatons")["count"], 1)
        self.assertEqual(self.json("/api/v1/planets", "sector=Altus")["count"], 2)
        self.assertEqual(self.json("/api/v1/planets", "defending=1")["count"], 1)
        proj = self.json("/api/v1/planets", "fields=name,players")
        self.assertEqual(set(proj["planets"][0]), {"name", "players"})

    def test_path_params_are_forwarded(self):
        a = self.json("/api/v1/planets/1")["planet"]
        b = self.json("/api/v1/planets/aurora-bay")["planet"]
        self.assertEqual(a["index"], b["index"])
        self.assertEqual(self.json("/api/v1/sectors/Altus")["sector"]["planet_count"], 2)

    def test_history_endpoint_uses_sources(self):
        body = self.json("/api/v1/planets/1/history")
        self.assertEqual(body["samples"], 2)

    def test_population_endpoint(self):
        body = self.json("/api/v1/population")
        self.assertEqual(body["summary"]["samples"], 5)
        self.assertEqual(body["summary"]["latest_total_players"], 1400)
        self.assertEqual(body["summary"]["min_total_players"], 1000)
        self.assertEqual(body["summary"]["latest_players_by_faction"]["automatons"], 920)
        self.assertEqual(body["snapshot_players_online"], 5010)

    def test_population_compact_trims_samples(self):
        body = self.json("/api/v1/population", "compact=1")
        self.assertLessEqual(len(body["samples"]), 40)

    def test_pretty_printing_matches_stdlib_behaviour(self):
        status, _, body = self.h.request("/api/v1/war", "pretty=1")
        self.assertEqual(status, 200)
        self.assertIn(b"\n  ", body)

    # ------------------------------------------------------------ 错误语义
    def test_api_error_maps_to_http_status(self):
        body = self.json("/api/v1/planets", "q=a", expect=400)
        self.assertIn("至少", body["error"])
        self.assertEqual(body["path"], "/api/v1/planets")

        self.json("/api/v1/planets?owner=nope".split("?")[0], "owner=nope", expect=400)
        self.json("/api/v1/planets/99999", expect=404)
        self.json("/api/v1/nope", expect=404)

    def test_unknown_query_params_are_ignored_not_rejected(self):
        # 未在签名里声明的参数不应导致 422
        body = self.json("/api/v1/planets", "totally_unknown=1&limit=2")
        self.assertEqual(body["returned"], 2)

    def test_cors_header_present(self):
        _, headers, _ = self.h.request("/api/v1/war")
        self.assertEqual(headers.get("access-control-allow-origin"), "*")


@requires_fastapi
class TestFastApiSharesServiceWithStdlib(unittest.TestCase):
    """两种前端必须共用同一份业务逻辑与快照。"""

    def test_same_snapshot_served_by_both_frontends(self):
        import threading
        import urllib.request

        from hd2api.web import make_server

        service = StubService()
        app = create_app(service)
        harness = AsgiHarness(app)

        httpd = make_server(service, host="127.0.0.1", port=0, quiet=True)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/v1/planets?sort=name", timeout=30) as resp:
                stdlib_body = json.loads(resp.read())
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=5)

        fastapi_body = json.loads(harness.request("/api/v1/planets", "sort=name")[2])

        # 路由不同（FastAPI 多了 /docs 等），但同一端点的数据必须一致
        self.assertEqual(stdlib_body["count"], fastapi_body["count"])
        self.assertEqual([p["name"] for p in stdlib_body["planets"]],
                         [p["name"] for p in fastapi_body["planets"]])
        self.assertEqual(stdlib_body["generated_at"], fastapi_body["generated_at"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
