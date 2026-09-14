"""`?mode=pt` / `?mode=md` 的可读文本输出测试。

规格见项目根目录 `README_fancy.md`。覆盖：
  * 渲染函数的逐字格式（含文档里的示例值）
  * 两种模式在标准库前端与 FastAPI 前端上的行为一致
  * JSON 默认行为未被破坏

    python tests/test_textview.py
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
_DEPS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".deps")
if os.path.isdir(_DEPS) and _DEPS not in sys.path:
    sys.path.insert(0, _DEPS)

from fixtures import AsgiHarness, StubService  # noqa: E402
from hd2api.textview import (  # noqa: E402
    data_timestamp,
    is_defense,
    latest_dispatch,
    outcome_label,
    render_dispatch,
    render_planet,
    wants_text,
)
from hd2api.web import make_server  # noqa: E402

# README_fancy.md 里的示例星球（值取自文档中的 JSON）
KARLIA = {
    "name": "KARLIA",
    "sector": "Omega",
    "owner": {"zh": "光能者"},
    "liberation_percent": 85.448,
    "eta_liberation_text": "6天1小时",
    "players": 2606,
    "liberation_rate": {"measured": {"to": "2026-09-14T01:31:44.2973993Z"}},
}

DOC_PLANET_TEXT = """\
星球名：KARLIA
分区：OMEGA
所属阵营：光能者
解放进度：85.448%
解放预计剩余时间：6天1小时
部署的绝地潜兵数：2606
数据获取时间：2026-09-14T01:31:44.2973993Z
"""

# README_fancy.md 里的防御战示例（planet 块按真实数据补全：K 的 owner 是超级地球，
# 但文档写的是「机器人」，即入侵方）
K_DEFENSE = {
    "name": "K",
    "sector": "Trigon",
    "is_under_attack": True,
    "players": 24548,
    "owner": {"zh": "超级地球"},
    "liberation_percent": 100.0,
    "eta_liberation_text": None,
    "liberation_rate": {"measured": {"to": "2026-09-14T01:31:44.2973993Z"}},
    "event": {
        "id": 5692,
        "event_type": 1,
        "event_type_label": "防御战",
        "faction": {"id": 3, "en": "Automatons", "zh": "机器人", "color": "#e04545"},
        "defense_progress_percent": 23.2293,
        "predicted_outcome": "defense_will_fail",
        "predicted_outcome_text": "按当前投入预计失守",
        "time_remaining_text": "18小时3分",
        "invasion_level": {"current": 31, "max": 40},
    },
}

DOC_DEFENSE_TEXT = """\
星球名：K
分区：TRIGON
所属阵营：机器人
已防御：23.2293%
预测：失败
剩余时间：18小时3分
部署的绝地潜兵数：24548
数据获取时间：2026-09-14T01:31:44.2973993Z
"""


class FakeRequest:
    """只实现 wants_text 需要的那个 get()。"""

    def __init__(self, query: dict[str, str] | None = None):
        self.query = query or {}

    def get(self, name, default=None):
        return self.query.get(name, default)


class TestModeResolution(unittest.TestCase):
    def test_pt_and_md_both_mean_text(self):
        for mode in ("pt", "md", "PT", "MD", " pt ", "Md"):
            self.assertTrue(wants_text(FakeRequest({"mode": mode})), f"mode={mode!r}")

    def test_default_is_json(self):
        self.assertFalse(wants_text(FakeRequest()))
        self.assertFalse(wants_text(FakeRequest({"mode": ""})))

    def test_raw_is_json(self):
        for mode in ("raw", "json", "JSON"):
            self.assertFalse(wants_text(FakeRequest({"mode": mode})))

    def test_unknown_mode_falls_back_to_json(self):
        # 文档只定义了 pt / raw；未知值不报错，按默认 JSON 走
        for mode in ("pt2", "text", "markdown", "1"):
            self.assertFalse(wants_text(FakeRequest({"mode": mode})), f"mode={mode!r}")


class TestRenderPlanet(unittest.TestCase):
    def test_matches_document_example_exactly(self):
        self.assertEqual(render_planet(KARLIA, "2026-09-14T01:56:34.677Z"),
                         DOC_PLANET_TEXT)

    def test_sector_is_uppercased(self):
        out = render_planet({**KARLIA, "sector": "Xi Tauri"})
        self.assertIn("分区：XI TAURI", out)

    def test_numbers_render_without_trailing_zero(self):
        out = render_planet({**KARLIA, "liberation_percent": 100.0, "players": 0})
        self.assertIn("解放进度：100%", out)
        self.assertIn("部署的绝地潜兵数：0", out)

    def test_null_eta_uses_placeholder(self):
        out = render_planet({**KARLIA, "eta_liberation_text": None})
        self.assertIn("解放预计剩余时间：—", out)

    def test_missing_fields_do_not_crash(self):
        out = render_planet({})
        self.assertEqual(len(out.strip().splitlines()), 7)
        self.assertIn("星球名：—", out)

    def test_blank_strings_become_placeholder(self):
        out = render_planet({**KARLIA, "eta_liberation_text": "   "})
        self.assertIn("解放预计剩余时间：—", out)

    def test_line_count_is_stable(self):
        self.assertEqual(len(render_planet(KARLIA).strip().splitlines()), 7)

    def test_ends_with_newline(self):
        self.assertTrue(render_planet(KARLIA).endswith("\n"))


class TestRenderDefensePlanet(unittest.TestCase):
    """防御战役（敌人入侵）走另一套版式，见 README_fancy.md。"""

    def test_matches_document_example_exactly(self):
        self.assertEqual(render_planet(K_DEFENSE, "2026-09-14T01:56:34.677Z"),
                         DOC_DEFENSE_TEXT)

    def test_has_eight_lines(self):
        self.assertEqual(len(render_planet(K_DEFENSE).strip().splitlines()), 8)

    def test_uses_invading_faction_not_owner(self):
        """文档示例里 K 的 owner 是超级地球，输出的却是入侵方机器人。"""
        self.assertEqual(K_DEFENSE["owner"]["zh"], "超级地球")
        out = render_planet(K_DEFENSE)
        self.assertIn("所属阵营：机器人", out)
        self.assertNotIn("超级地球", out)

    def test_switches_to_liberation_format_when_not_invaded(self):
        planet = {**K_DEFENSE, "is_under_attack": False}
        out = render_planet(planet)
        self.assertIn("所属阵营：超级地球", out)   # 非防御战时用 owner
        self.assertIn("解放进度：100%", out)
        self.assertNotIn("已防御", out)
        self.assertNotIn("预测", out)
        self.assertEqual(len(out.strip().splitlines()), 7)

    def test_requires_event_object(self):
        """is_under_attack 为真但没有 event 数据时，退回解放版式而不是崩掉。"""
        planet = {**K_DEFENSE, "event": None}
        out = render_planet(planet)
        self.assertIn("解放进度", out)
        self.assertEqual(len(out.strip().splitlines()), 7)

    def test_outcome_mapping_covers_all_api_values(self):
        expected = {
            "defense_will_hold": "成功",
            "defense_will_fail": "失败",
            "too_close_to_call": "不确定",
            "unknown": "不确定",
            None: "不确定",
        }
        for api_value, label in expected.items():
            event = {**K_DEFENSE["event"], "predicted_outcome": api_value}
            out = render_planet({**K_DEFENSE, "event": event})
            self.assertIn(f"预测：{label}", out, f"predicted_outcome={api_value!r}")

    def test_only_three_outcome_labels_are_possible(self):
        for api_value in ("defense_will_hold", "defense_will_fail", "too_close_to_call",
                          "unknown", None, "something_new"):
            event = {**K_DEFENSE["event"], "predicted_outcome": api_value}
            out = render_planet({**K_DEFENSE, "event": event})
            line = next(ln for ln in out.splitlines() if ln.startswith("预测："))
            self.assertIn(line, ("预测：成功", "预测：失败", "预测：不确定"))

    def test_does_not_use_the_long_outcome_text(self):
        """`预测` 用的是短标签，不是 predicted_outcome_text 的长句。"""
        out = render_planet(K_DEFENSE)
        self.assertNotIn("按当前投入预计失守", out)

    def test_null_remaining_time(self):
        event = {**K_DEFENSE["event"], "time_remaining_text": None}
        out = render_planet({**K_DEFENSE, "event": event})
        self.assertIn("剩余时间：—", out)

    def test_defense_progress_number_format(self):
        event = {**K_DEFENSE["event"], "defense_progress_percent": 100.0}
        out = render_planet({**K_DEFENSE, "event": event})
        self.assertIn("已防御：100%", out)

    def test_is_defense_helper(self):
        self.assertTrue(is_defense(K_DEFENSE))
        self.assertFalse(is_defense({**K_DEFENSE, "is_under_attack": False}))
        self.assertFalse(is_defense({**K_DEFENSE, "event": None}))
        self.assertFalse(is_defense(KARLIA))


class TestDataTimestamp(unittest.TestCase):
    """文档注释写 generated_at，但示例值是 measured.to —— 这里跟示例值。"""

    def test_prefers_measured_window_end(self):
        got = data_timestamp(KARLIA, "2026-09-14T01:56:34.677Z")
        self.assertEqual(got, "2026-09-14T01:31:44.2973993Z")

    def test_falls_back_to_generated_at(self):
        planet = {**KARLIA, "liberation_rate": {}}
        self.assertEqual(data_timestamp(planet, "2026-09-14T01:56:34.677Z"),
                         "2026-09-14T01:56:34.677Z")

    def test_falls_back_when_measured_is_null(self):
        planet = {**KARLIA, "liberation_rate": {"measured": None}}
        self.assertEqual(data_timestamp(planet, "GENERATED"), "GENERATED")


class TestRenderDispatch(unittest.TestCase):
    def test_latest_is_max_id(self):
        items = [{"id": 1, "published_at": "a"}, {"id": 9, "published_at": "b"},
                 {"id": 5, "published_at": "c"}]
        self.assertEqual(latest_dispatch(items)["id"], 9)

    def test_real_newlines_are_preserved(self):
        msg = "MAJOR ORDER FAILED\n\nThe Helldivers recaptured CHARBAL-VII."
        out = render_dispatch([{"id": 3920, "published_at": "2026-09-13T12:07:17.308Z",
                                "message": msg}])
        self.assertIn("MAJOR ORDER FAILED\n\nThe Helldivers", out)
        self.assertNotIn("\\n", out)  # 不能把换行输出成字面量 \n

    def test_format(self):
        out = render_dispatch([{"id": 1, "published_at": "T", "message": "M"}])
        self.assertEqual(out, "时间：T\n信息：M\n")

    def test_empty_list(self):
        self.assertIsNone(latest_dispatch([]))
        out = render_dispatch([])
        self.assertIn("时间：—", out)
        self.assertIn("暂无快讯", out)

    def test_only_one_dispatch_is_rendered(self):
        items = [{"id": i, "published_at": f"T{i}", "message": f"M{i}"} for i in range(1, 20)]
        out = render_dispatch(items)
        self.assertEqual(len(out.strip().splitlines()), 2)
        self.assertIn("M19", out)


class HttpTestBase(unittest.TestCase):
    """两种前端共用同一批断言。"""

    base = ""

    def fetch(self, path: str):
        try:
            with urllib.request.urlopen(self.base + path, timeout=60) as resp:
                return resp.status, resp.headers.get("Content-Type", ""), resp.read()
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, exc.headers.get("Content-Type", ""), exc.read()


class TestStdlibFrontend(HttpTestBase):
    @classmethod
    def setUpClass(cls):
        cls.service = StubService()
        cls.httpd = make_server(cls.service, host="127.0.0.1", port=0, quiet=True)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def test_planet_pt_is_plain_text(self):
        status, ctype, body = self.fetch("/api/v1/planets/AURORA%20BAY?mode=pt")
        self.assertEqual(status, 200)
        self.assertIn("text/plain", ctype)
        text = body.decode("utf-8")
        self.assertIn("星球名：AURORA BAY", text)
        self.assertIn("分区：ALTUS", text)
        self.assertEqual(len(text.strip().splitlines()), 7)

    def test_defense_planet_uses_defense_layout(self):
        """夹具里 SUPER EARTH 是己方星球、正被机器人入侵 -> 走防御版式。"""
        status, ctype, body = self.fetch("/api/v1/planets/SUPER%20EARTH?mode=pt")
        self.assertEqual(status, 200)
        self.assertIn("text/plain", ctype)
        text = body.decode("utf-8")
        self.assertIn("已防御：", text)
        self.assertIn("预测：", text)
        self.assertIn("剩余时间：", text)
        self.assertNotIn("解放进度", text)
        self.assertNotIn("解放预计剩余时间", text)
        self.assertEqual(len(text.strip().splitlines()), 8)

    def test_defense_and_liberation_have_different_line_counts(self):
        _, _, a = self.fetch("/api/v1/planets/SUPER%20EARTH?mode=pt")   # 防御战
        _, _, b = self.fetch("/api/v1/planets/AURORA%20BAY?mode=pt")    # 解放战
        self.assertEqual(len(a.decode().strip().splitlines()), 8)
        self.assertEqual(len(b.decode().strip().splitlines()), 7)

    def test_defense_pt_and_md_identical(self):
        _, _, a = self.fetch("/api/v1/planets/SUPER%20EARTH?mode=pt")
        _, _, b = self.fetch("/api/v1/planets/SUPER%20EARTH?mode=md")
        self.assertEqual(a, b)

    def test_planet_md_same_as_pt(self):
        _, _, a = self.fetch("/api/v1/planets/AURORA%20BAY?mode=pt")
        _, _, b = self.fetch("/api/v1/planets/AURORA%20BAY?mode=md")
        self.assertEqual(a, b)

    def test_singular_alias_matches_plural(self):
        _, _, a = self.fetch("/api/v1/planets/AURORA%20BAY?mode=pt")
        _, _, b = self.fetch("/api/v1/planet/AURORA%20BAY?mode=pt")
        self.assertEqual(a, b)

    def test_planet_default_is_still_json(self):
        status, ctype, body = self.fetch("/api/v1/planets/AURORA%20BAY")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        self.assertIn("planet", json.loads(body))

    def test_planet_raw_is_json(self):
        _, ctype, body = self.fetch("/api/v1/planets/AURORA%20BAY?mode=raw")
        self.assertIn("application/json", ctype)
        self.assertIn("planet", json.loads(body))

    def test_dispatches_pt_only_latest(self):
        status, ctype, body = self.fetch("/api/v1/dispatches?mode=pt")
        self.assertEqual(status, 200)
        self.assertIn("text/plain", ctype)
        text = body.decode("utf-8")
        self.assertEqual(len(text.strip().splitlines()), 2)
        self.assertTrue(text.startswith("时间："))
        # 夹具里 id 最大的是 2
        self.assertIn("newer dispatch", text)
        self.assertNotIn("We did it.", text)

    def test_dispatches_default_is_still_json(self):
        _, ctype, body = self.fetch("/api/v1/dispatches")
        self.assertIn("application/json", ctype)
        self.assertEqual(json.loads(body)["count"], 2)

    def test_other_endpoints_ignore_mode(self):
        """"特定 API" —— 其它端点即使带 mode 也照常返回 JSON。"""
        for path in ("/api/v1/war?mode=pt", "/api/v1/sectors?mode=pt",
                     "/api/v1/planets?mode=pt"):
            _, ctype, _ = self.fetch(path)
            self.assertIn("application/json", ctype, path)

    def test_unknown_planet_still_404_in_text_mode(self):
        status, _, _ = self.fetch("/api/v1/planet/NOPE?mode=pt")
        self.assertEqual(status, 404)


class TestFastApiFrontend(HttpTestBase):
    @classmethod
    def setUpClass(cls):
        try:
            from hd2api.asgi import FASTAPI_AVAILABLE, create_app
        except Exception as exc:  # noqa: BLE001
            raise unittest.SkipTest(f"未安装 FastAPI: {exc}")
        if not FASTAPI_AVAILABLE:
            raise unittest.SkipTest("未安装 FastAPI")
        cls.harness = AsgiHarness(create_app(StubService()))

    def fetch(self, path: str):
        assert path.startswith("/")
        route, _, query = path.partition("?")
        status, headers, body = self.harness.request(route, query)
        return status, headers.get("content-type", ""), body

    def test_planet_pt_is_plain_text(self):
        status, ctype, body = self.fetch("/api/v1/planets/AURORA%20BAY?mode=pt")
        self.assertEqual(status, 200)
        self.assertIn("text/plain", ctype)
        self.assertIn("星球名：", body.decode("utf-8"))

    def test_planet_default_is_still_json(self):
        _, ctype, _ = self.fetch("/api/v1/planets/AURORA%20BAY")
        self.assertIn("application/json", ctype)

    def test_dispatches_pt_only_latest(self):
        status, ctype, body = self.fetch("/api/v1/dispatches?mode=pt")
        self.assertEqual(status, 200)
        self.assertIn("text/plain", ctype)
        self.assertEqual(len(body.decode("utf-8").strip().splitlines()), 2)


class TestFrontendsAgreeOnText(unittest.TestCase):
    """两个前端的文本输出必须逐字节相同。"""

    @classmethod
    def setUpClass(cls):
        cls.service = StubService()
        cls.httpd = make_server(cls.service, host="127.0.0.1", port=0, quiet=True)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def test_same_bytes(self):
        try:
            from hd2api.asgi import FASTAPI_AVAILABLE, create_app
            if not FASTAPI_AVAILABLE:
                self.skipTest("未安装 FastAPI")
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"未安装 FastAPI: {exc}")

        harness = AsgiHarness(create_app(StubService()))
        for path, query in (("/api/v1/planets/AURORA%20BAY", "mode=pt"),
                            ("/api/v1/dispatches", "mode=pt")):
            with urllib.request.urlopen(f"{self.base}{path}?{query}", timeout=60) as resp:
                stdlib_body = resp.read()
            _, _, fastapi_body = harness.request(path, query)
            self.assertEqual(stdlib_body, fastapi_body, f"{path} 两个前端输出不一致")


if __name__ == "__main__":
    unittest.main(verbosity=2)
