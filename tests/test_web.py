"""Web 层集成测试：真实起一个 HTTP 服务，完全离线。

    python -m unittest discover -s tests -v
    python tests/test_web.py
"""

from __future__ import annotations

import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures import DEFAULT_HISTORY, StubService, history, iso_ago  # noqa: E402
from hd2api.web import make_server  # noqa: E402


class WebTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = StubService()
        # 端口 0 -> 让内核分配一个空闲端口，避免与正在跑的服务冲突
        cls.httpd = make_server(cls.service, host="127.0.0.1", port=0, quiet=True)
        cls.port = cls.httpd.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def get(self, path: str, expect: int = 200):
        url = self.base + path
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                raw = resp.read()
                status = resp.status
                ctype = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            with exc:  # 显式关闭，避免 tempfile ResourceWarning 噪音
                raw = exc.read()
                status = exc.code
                ctype = exc.headers.get("Content-Type", "")
        self.assertEqual(status, expect,
                         f"{path} 期望 {expect} 实际 {status}: {raw[:200]!r}")
        return raw, ctype

    def get_json(self, path: str, expect: int = 200):
        raw, ctype = self.get(path, expect)
        self.assertIn("application/json", ctype)
        return json.loads(raw)


class TestMetaEndpoints(WebTestBase):
    def test_index_lists_endpoints(self):
        body = self.get_json("/")
        self.assertEqual(body["name"], "helldiversbot API")
        self.assertIn("GET /api/v1/planets", body["endpoints"])
        self.assertIn("GET /api/v1/defenses", body["endpoints"])

    def test_health(self):
        body = self.get_json("/health")
        self.assertEqual(body["state"], "ok")
        self.assertFalse(body["poller_enabled"])
        self.assertEqual(body["reference"]["planets"], 3)

    def test_openapi_is_valid_and_covers_routes(self):
        spec = self.get_json("/openapi.json")
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertIn("/api/v1/planets", spec["paths"])
        self.assertIn("/api/v1/planets/{key}", spec["paths"])
        op = spec["paths"]["/api/v1/planets/{key}"]["get"]
        self.assertEqual(op["summary"], "单颗星球详情")
        params = {p["name"] for p in op["parameters"]}
        self.assertIn("key", params)
        # 每个路由都必须有 summary 与 tags，否则文档会出现空白条目
        for path, methods in spec["paths"].items():
            for method, o in methods.items():
                self.assertTrue(o["summary"], f"{method} {path} 缺少 summary")
                self.assertTrue(o["tags"], f"{method} {path} 缺少 tags")

    def test_docs_page(self):
        raw, ctype = self.get("/docs")
        self.assertIn("text/html", ctype)
        self.assertIn(b"HELLDIVERS", raw)

    def test_trailing_slash_is_normalised(self):
        a = self.get_json("/api/v1/war")
        b = self.get_json("/api/v1/war/")
        self.assertEqual(a["war"]["war_id"], b["war"]["war_id"])

    def test_options_preflight(self):
        req = urllib.request.Request(self.base + "/api/v1/war", method="OPTIONS")
        with urllib.request.urlopen(req, timeout=30) as resp:
            self.assertEqual(resp.status, 204)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")


class TestWarEndpoints(WebTestBase):
    def test_war(self):
        body = self.get_json("/api/v1/war")
        self.assertEqual(body["war"]["war_id"], 801)
        self.assertEqual(body["totals"]["players_online"], 5010)
        self.assertEqual(body["totals"]["active_defenses"], 1)

    def test_stats(self):
        body = self.get_json("/api/v1/stats")
        self.assertEqual(body["galaxy_statistics"]["missions_total"], 125)
        self.assertEqual(body["galaxy_statistics"]["kills"]["total"], 60)

    def test_snapshot_compact_has_no_heavy_blocks(self):
        full = self.get_json("/api/v1/snapshot")
        self.assertIn("regions", full["planets"][1])
        compact = self.get_json("/api/v1/snapshot?compact=1")
        self.assertNotIn("regions", compact["planets"][1])
        self.assertIn("liberation_percent", compact["planets"][1])

    def test_pretty_printing(self):
        raw, _ = self.get("/api/v1/war?pretty=1")
        self.assertIn(b"\n  ", raw)


class TestPlanetEndpoints(WebTestBase):
    def test_list_default(self):
        body = self.get_json("/api/v1/planets")
        self.assertEqual(body["count"], 3)
        self.assertEqual(body["returned"], 3)
        # 默认按在线人数降序
        self.assertEqual([p["index"] for p in body["planets"]], [1, 0, 2])

    def test_limit_and_offset(self):
        body = self.get_json("/api/v1/planets?limit=1")
        self.assertEqual(body["count"], 3)
        self.assertEqual(body["returned"], 1)
        self.assertEqual(body["planets"][0]["index"], 1)
        body2 = self.get_json("/api/v1/planets?limit=1&offset=1")
        self.assertEqual(body2["offset"], 1)
        self.assertEqual(body2["planets"][0]["index"], 0)

    def test_owner_filter_accepts_number_and_alias(self):
        from urllib.parse import quote
        for spec in ("3", "automatons", "Automaton", "bots", "机器人"):
            body = self.get_json(f"/api/v1/planets?owner={quote(spec)}")
            self.assertEqual(body["count"], 1, f"owner={spec} 过滤结果不对")
            self.assertEqual(body["planets"][0]["index"], 1)

    def test_sector_filter(self):
        body = self.get_json("/api/v1/planets?sector=Altus")
        self.assertEqual({p["index"] for p in body["planets"]}, {1, 2})
        body2 = self.get_json("/api/v1/planets?sector=altus")
        self.assertEqual(body2["count"], 2)

    def test_query_filter_and_min_length(self):
        body = self.get_json("/api/v1/planets?q=aurora")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["planets"][0]["name"], "AURORA BAY")
        self.get_json("/api/v1/planets?q=a", expect=400)

    def test_status_and_flags(self):
        self.assertEqual(self.get_json("/api/v1/planets?defending=1")["count"], 1)
        self.assertEqual(self.get_json("/api/v1/planets?active=1")["count"], 2)
        self.assertEqual(self.get_json("/api/v1/planets?contested=1")["count"], 1)
        self.assertEqual(self.get_json("/api/v1/planets?min_players=1000")["count"], 1)

    def test_sorting(self):
        body = self.get_json("/api/v1/planets?sort=name&order=asc")
        self.assertEqual([p["name"] for p in body["planets"]],
                         ["AURORA BAY", "HEETH", "SUPER EARTH"])
        body2 = self.get_json("/api/v1/planets?sort=liberation&order=desc")
        self.assertEqual(body2["planets"][0]["name"], "SUPER EARTH")

    def test_compact_and_fields_projection(self):
        body = self.get_json("/api/v1/planets?compact=1")
        self.assertNotIn("regions", body["planets"][0])
        self.assertIn("trend", body["planets"][0])
        proj = self.get_json("/api/v1/planets?fields=name,players")
        self.assertEqual(set(proj["planets"][0]), {"name", "players"})

    def test_lookup_by_index_name_slug(self):
        a = self.get_json("/api/v1/planets/1")["planet"]
        b = self.get_json("/api/v1/planets/AURORA%20BAY")["planet"]
        c = self.get_json("/api/v1/planets/aurora-bay")["planet"]
        self.assertEqual(a["index"], b["index"], c["index"])
        self.assertEqual(a["name"], "AURORA BAY")

    def test_lookup_by_settings_hash(self):
        p = self.get_json("/api/v1/planets/222")["planet"]
        self.assertEqual(p["name"], "AURORA BAY")

    def test_planet_not_found(self):
        body = self.get_json("/api/v1/planets/99999", expect=404)
        self.assertIn("未找到星球", body["error"])

    def test_regions_endpoint(self):
        body = self.get_json("/api/v1/planets/1/regions")
        self.assertEqual(body["planet_name"], "AURORA BAY")
        self.assertEqual(body["regions"][0]["name"], "BATU BELIG")

    def test_history_endpoint_goes_through_sources(self):
        body = self.get_json("/api/v1/planets/1/history")
        self.assertEqual(body["planet_index"], 1)
        self.assertEqual(body["samples"], 2)
        self.assertIn(1, self.service.sources.planet_history_calls)

    def test_history_endpoint_handles_missing_upstream_data(self):
        body = self.get_json("/api/v1/planets/2/history")
        self.assertEqual(body["samples"], 0)
        self.assertEqual(body["history"], [])


class TestSectorEndpoints(WebTestBase):
    def test_list(self):
        body = self.get_json("/api/v1/sectors")
        self.assertEqual(body["count"], 2)
        names = [s["name"] for s in body["sectors"]]
        self.assertEqual(names[0], "Altus")  # 默认按人数降序

    def test_detail(self):
        body = self.get_json("/api/v1/sectors/Altus")
        self.assertEqual(body["sector"]["planet_count"], 2)
        self.assertEqual(len(body["planets"]), 2)
        self.assertEqual(body["planets"][0]["index"], 1)  # 人数多的在前

    def test_detail_not_found(self):
        self.get_json("/api/v1/sectors/Nope", expect=404)

    def test_owner_filter(self):
        self.assertEqual(self.get_json("/api/v1/sectors?owner=humans")["count"], 1)


class TestCampaignEndpoints(WebTestBase):
    def test_campaigns(self):
        body = self.get_json("/api/v1/campaigns")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["campaigns"][0]["planet_name"], "AURORA BAY")

    def test_campaigns_by_planet(self):
        self.assertEqual(self.get_json("/api/v1/campaigns?planet=1")["count"], 1)
        self.assertEqual(self.get_json("/api/v1/campaigns?planet=2")["count"], 0)

    def test_defenses(self):
        body = self.get_json("/api/v1/defenses")
        self.assertEqual(body["count"], 1)
        d = body["defenses"][0]
        self.assertEqual(d["planet_name"], "SUPER EARTH")
        self.assertEqual(d["invasion_level"]["max"], 40)
        self.assertIn("predicted_outcome_text", d)
        self.assertIsNotNone(d["required_divers"])

    def test_defenses_outcome_filter(self):
        outcome = self.get_json("/api/v1/defenses")["defenses"][0]["predicted_outcome"]
        self.assertEqual(
            self.get_json(f"/api/v1/defenses?outcome={outcome}")["count"], 1)
        self.assertEqual(
            self.get_json("/api/v1/defenses?outcome=nonexistent")["count"], 0)


class TestStoryEndpoints(WebTestBase):
    def test_major_orders_defaults_to_active(self):
        body = self.get_json("/api/v1/major-orders")
        self.assertTrue(all(m["is_active"] for m in body["major_orders"]))
        self.assertTrue(any(m["title"] == "OPEN ENDED" for m in body["major_orders"]))

    def test_major_orders_all(self):
        body = self.get_json("/api/v1/major-orders?all=1")
        self.assertEqual(body["count"], 2)

    def test_dispatches(self):
        body = self.get_json("/api/v1/dispatches")
        self.assertEqual(body["count"], 2)
        self.assertEqual(body["dispatches"][0]["id"], 2)
        self.assertEqual(self.get_json("/api/v1/dispatches?limit=1")["count"], 2)

    def test_news(self):
        body = self.get_json("/api/v1/news?limit=1")
        self.assertEqual(body["news"][0]["title"], "Patch")

    def test_space_stations(self):
        body = self.get_json("/api/v1/space-stations")
        self.assertEqual(body["space_stations"][0]["tactical_actions"][0]["name"], "EAGLE STORM")

    def test_global_events(self):
        body = self.get_json("/api/v1/global-events")
        self.assertEqual(body["global_events"][0]["message"], "hi there")


class TestDebugEndpoints(WebTestBase):
    def test_reference_summary(self):
        body = self.get_json("/api/v1/reference")
        self.assertEqual(body["planet_count"], 3)
        self.assertEqual(body["effect_count"], 3)  # 夹具里放了 2 条 effect + 1 条 presence
        self.assertEqual(body["factions"]["3"]["zh"], "机器人")

    def test_reference_full(self):
        body = self.get_json("/api/v1/reference?full=1")
        self.assertIn("1", body["planets"])

    def test_raw_full_and_partial(self):
        full = self.get_json("/api/v1/raw")
        self.assertIn("warStatus", full)
        part = self.get_json("/api/v1/raw?part=warInfo")
        self.assertEqual(list(part), ["warInfo"])

    def test_raw_unknown_part(self):
        self.get_json("/api/v1/raw?part=nope", expect=404)

    def test_unknown_route(self):
        body = self.get_json("/api/v1/nope", expect=404)
        self.assertIn("hint", body)


class TestDegradedService(WebTestBase):
    """上游挂掉时，接口应保持可用而不是抛 500。"""

    def test_missing_snapshot_returns_503(self):
        class Dead:
            ref = StubService().ref
            sources = StubService().sources
            last_error = "FetchError: boom"
            last_error_at = None
            refresh_count = 0
            enable_poller = False

            def snapshot(self, auto_refresh=True):
                from hd2api.httpclient import FetchError
                raise FetchError("https://example.invalid", "连接失败")

            def calibration(self):
                from hd2api.normalize import ImpactCalibration
                return ImpactCalibration(0.0)

            def health(self):
                return {"state": "starting", "last_error": self.last_error}

        httpd = make_server(Dead(), host="127.0.0.1", port=0, quiet=True)
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=30) as resp:
                self.assertEqual(resp.status, 200)
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/war", timeout=30)
                self.fail("应当返回 503")
            except urllib.error.HTTPError as exc:
                with exc:
                    self.assertEqual(exc.code, 503)
                    body = json.loads(exc.read())
                    self.assertIn("上游数据源暂不可用", body["error"])
        finally:
            httpd.shutdown()
            httpd.server_close()
            t.join(timeout=5)


class TestSectorLiberationWithRealShape(WebTestBase):
    """星区解放度 = 已解放星球占比，与游戏内星区条口径一致。"""

    def test_partial_sector(self):
        # 让 Altus 的一颗星球变成人类所有
        snap = self.service.snapshot()
        idx = {p["index"]: p for p in snap["planets"]}
        before = next(s for s in snap["sectors"] if s["name"] == "Altus")
        self.assertEqual(before["liberated_count"], 0)
        self.assertEqual(idx[0]["sector"], "Sol")
        sol = next(s for s in snap["sectors"] if s["name"] == "Sol")
        self.assertEqual(sol["liberated_percent"], 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
