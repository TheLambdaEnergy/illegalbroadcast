"""QQ 机器人的测试。

分两层：
  * **离线**：命令解析、格式化、错误分支——用假客户端，不碰网络
  * **在线**：对着真实的 helldiversbot API 跑三个命令（API 没起就自动跳过）

    python tests/test_qqbot.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bot"))

from commands import (  # noqa: E402
    MISSING_PLANET_ARG,
    UNKNOWN_INPUT,
    USAGE,
    execute_command,
    format_trending,
    parse_command,
    strip_mention,
    truncate,
)
from hd2_api import Hd2ApiError, Hd2Client  # noqa: E402

API_BASE = os.environ.get("QQBOT_API_BASE", "http://127.0.0.1:8808")


def api_alive() -> bool:
    try:
        with urllib.request.urlopen(API_BASE + "/health", timeout=5):
            return True
    except Exception:  # noqa: BLE001
        return False


requires_api = unittest.skipUnless(api_alive(), f"战报 API 未运行（{API_BASE}）")


class FakeClient:
    """按预设返回内容或抛错，用来测命令层。"""

    def __init__(self, planet="PLANET TEXT", dispatch="DISPATCH TEXT", trending=None, error=None):
        self._planet = planet
        self._dispatch = dispatch
        self._trending = trending if trending is not None else {"planets": [], "totals": {}}
        self._error = error
        self.calls: list[tuple] = []

    def _maybe_raise(self):
        if self._error:
            raise self._error

    async def planet_text(self, key):
        self.calls.append(("planet", key))
        self._maybe_raise()
        return self._planet

    async def dispatch_text(self):
        self.calls.append(("dispatch",))
        self._maybe_raise()
        return self._dispatch

    async def trending(self, limit=5):
        self.calls.append(("trending", limit))
        self._maybe_raise()
        return self._trending


def run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- 解析
class TestStripMention(unittest.TestCase):
    def test_channel_mention(self):
        self.assertEqual(strip_mention("<@!1234567890> /p KARLIA"), "/p KARLIA")

    def test_group_mention(self):
        self.assertEqual(strip_mention("<@1234567890> /p KARLIA"), "/p KARLIA")

    def test_multiple_mentions(self):
        self.assertEqual(strip_mention("<@!111> <@!222> /d"), "/d")

    def test_no_mention(self):
        self.assertEqual(strip_mention("/d"), "/d")
        self.assertEqual(strip_mention("  /d  "), "/d")

    def test_empty(self):
        self.assertEqual(strip_mention(""), "")
        self.assertEqual(strip_mention(None), "")

    def test_mention_without_space(self):
        self.assertEqual(strip_mention("<@!111>/p KARLIA"), "/p KARLIA")


class TestParseCommand(unittest.TestCase):
    def test_all_aliases(self):
        cases = {
            "/p": "planet", "/planet": "planet",
            "/d": "dispatch", "/dispatch": "dispatch",
            "/t": "trending", "/trending": "trending",
            "/help": "help", "/h": "help",
        }
        for text, expected in cases.items():
            cmd = parse_command(text)
            self.assertIsNotNone(cmd, text)
            self.assertEqual(cmd.name, expected, text)

    def test_case_insensitive_command(self):
        self.assertEqual(parse_command("/P KARLIA").name, "planet")
        self.assertEqual(parse_command("/Planet KARLIA").name, "planet")

    def test_argument_is_kept_verbatim(self):
        self.assertEqual(parse_command("/p BEKVAM III").arg, "BEKVAM III")
        self.assertEqual(parse_command("/p 262").arg, "262")
        # 星球名里可能有连字符、点、撇号
        self.assertEqual(parse_command("/p CHARBAL-VII").arg, "CHARBAL-VII")
        self.assertEqual(parse_command("/p WIDOW'S HARBOR").arg, "WIDOW'S HARBOR")

    def test_mention_prefix_is_stripped(self):
        self.assertEqual(parse_command("<@!111> /p 262").arg, "262")

    def test_not_a_command(self):
        for text in ("", "hello", "/", "p KARLIA", "@bot 你好"):
            self.assertIsNone(parse_command(text), repr(text))

    def test_unknown_command(self):
        cmd = parse_command("/xyz abc")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.name, "unknown")
        self.assertEqual(cmd.arg, "abc")

    def test_cjk_after_slash_is_not_a_command(self):
        # "/你好" 不该被当成命令
        self.assertIsNone(parse_command("/你好"))


class TestTruncate(unittest.TestCase):
    def test_short_text_untouched(self):
        self.assertEqual(truncate("abc", 10), "abc")

    def test_long_text_marked(self):
        out = truncate("x" * 100, 40)
        self.assertLessEqual(len(out), 40)
        self.assertIn("已截断", out)

    def test_zero_limit_disables(self):
        self.assertEqual(truncate("x" * 100, 0), "x" * 100)


# --------------------------------------------------------------------------- 格式化
class TestFormatTrending(unittest.TestCase):
    LIB = {"name": "BRILLIANCE", "enemy_faction_zh": "终结族",
           "liberation_percent": 42.5, "players": 13287, "is_defending": False}
    DEF = {"name": "K", "enemy_faction_zh": "机器人",
           "liberation_percent": 100.0, "defense_progress_percent": 37.8949,
           "players": 16963, "is_defending": True}

    def test_defense_uses_defense_progress(self):
        out = format_trending([self.DEF], {"players_online": 100000})
        self.assertIn("防御 37.8949%", out)
        self.assertNotIn("解放 100", out)   # 防御中的己方星球 liberation 恒为 100，没意义

    def test_liberation_uses_liberation_percent(self):
        out = format_trending([self.LIB], {"players_online": 100000})
        self.assertIn("解放 42.5%", out)

    def test_shows_total_and_numbering(self):
        out = format_trending([self.LIB, self.DEF], {"players_online": 99000})
        self.assertIn("99,000", out)
        self.assertIn("1. BRILLIANCE", out)
        self.assertIn("2. K", out)

    def test_empty_planets(self):
        self.assertIn("拿不到", format_trending([], {}))

    def test_limit_respected(self):
        out = format_trending([self.LIB] * 10, {}, limit=3)
        self.assertIn("3. ", out)
        self.assertNotIn("4. ", out)

    def test_missing_fields_do_not_crash(self):
        out = format_trending([{}], {})
        self.assertIn("—", out)


# --------------------------------------------------------------------------- 执行
class TestExecuteCommand(unittest.TestCase):
    def test_planet_passes_argument_through(self):
        c = FakeClient(planet="星球名：KARLIA")
        out = run(execute_command("/p KARLIA", c))
        self.assertEqual(out, "星球名：KARLIA")
        self.assertEqual(c.calls, [("planet", "KARLIA")])

    def test_planet_accepts_index(self):
        c = FakeClient()
        run(execute_command("/p 262", c))
        self.assertEqual(c.calls, [("planet", "262")])

    def test_planet_without_argument_shows_hint(self):
        """少给参数 -> 更具体的提示（不是「未知参数」）。"""
        c = FakeClient()
        out = run(execute_command("/p", c))
        self.assertEqual(out, MISSING_PLANET_ARG)
        self.assertEqual(c.calls, [])

    def test_dispatch(self):
        c = FakeClient(dispatch="信息：MAJOR ORDER FAILED")
        out = run(execute_command("/d", c))
        self.assertEqual(out, "信息：MAJOR ORDER FAILED")

    def test_no_arg_command_rejects_extra_argument(self):
        """/d /t 不接受参数，给了就是「未知参数」。"""
        for text in ("/d whatever", "/dispatch 123", "/t 5", "/trending x"):
            c = FakeClient()
            self.assertEqual(run(execute_command(text, c)), UNKNOWN_INPUT, text)
            self.assertEqual(c.calls, [], f"{text} 不该真的去请求 API")

    def test_help_with_extra_argument_still_shows_help(self):
        """/help 不吃参数这个概念 —— 多给点东西也照常显示帮助。"""
        c = FakeClient()
        self.assertEqual(run(execute_command("/help me", c)), USAGE)
        self.assertEqual(c.calls, [])

    def test_trending(self):
        c = FakeClient(trending={"planets": [TestFormatTrending.LIB],
                                 "totals": {"players_online": 1234}})
        out = run(execute_command("/t", c))
        self.assertIn("BRILLIANCE", out)
        self.assertIn("1,234", out)

    def test_help_returns_documented_message(self):
        c = FakeClient()
        self.assertEqual(run(execute_command("/help", c)), USAGE)
        self.assertEqual(run(execute_command("/h", c)), USAGE)
        self.assertEqual(c.calls, [])

    def test_help_message_matches_qqbot_md(self):
        """帮助文案以 qqbot.md 里写的那段为准。"""
        with open(os.path.join(ROOT, "qqbot.md"), encoding="utf-8") as fh:
            doc = fh.read()
        self.assertIn(USAGE, doc, "commands.USAGE 与 qqbot.md 的 Help Message 不一致")

    def test_unknown_command_shows_unknown_message(self):
        c = FakeClient()
        for text in ("/zzz", "/xyz abc", "/foo"):
            self.assertEqual(run(execute_command(text, c)), UNKNOWN_INPUT, text)
        self.assertEqual(c.calls, [])

    def test_non_command_shows_unknown_message(self):
        c = FakeClient()
        for text in ("你好", "hello", "/", "随便说点什么"):
            self.assertEqual(run(execute_command(text, c)), UNKNOWN_INPUT, text)

    def test_unknown_message_wording(self):
        self.assertEqual(UNKNOWN_INPUT, "未知的参数或命令。请使用/help查看相关帮助")
        self.assertIn("/help", UNKNOWN_INPUT)

    def test_api_error_becomes_readable_text(self):
        c = FakeClient(error=Hd2ApiError("没有找到这个星球。", status=404))
        out = run(execute_command("/p NOPE", c))
        self.assertEqual(out, "没有找到这个星球。")

    def test_long_reply_is_truncated(self):
        c = FakeClient(dispatch="字" * 2000)
        out = run(execute_command("/d", c, max_reply_chars=100))
        self.assertLessEqual(len(out), 100)

    def test_survives_unexpected_exception(self):
        class Boom(FakeClient):
            async def planet_text(self, key):
                raise RuntimeError("boom")
        # execute_command 只吞 Hd2ApiError；其它异常由 qqbot._handle 兜底
        with self.assertRaises(RuntimeError):
            run(execute_command("/p X", Boom()))


# --------------------------------------------------------------------------- 在线
@requires_api
class TestAgainstLiveApi(unittest.TestCase):
    """对着真实 API 跑。每个用例在**同一个 event loop 里**建客户端、用、关。

    不能跨 `asyncio.run()` 复用同一个 Hd2Client —— aiohttp 的 session 绑定在
    创建它的 loop 上。客户端本身也会检测并重建（见 `Hd2Client._get_session`），
    但测试里一个 loop 走完更干净。
    """

    @staticmethod
    def with_client(fn):
        async def body():
            client = Hd2Client(API_BASE)
            try:
                return await fn(client)
            finally:
                await client.close()
                # Windows 的 ProactorEventLoop 在 loop 关闭时若还有 transport
                # 没走完收尾，会甩一堆 ResourceWarning。让出一次控制权给它收干净。
                await asyncio.sleep(0)
        return asyncio.run(body())

    def test_planet_by_name_and_index_agree(self):
        async def body(client):
            return await client.planet_text("KARLIA"), await client.planet_text("185")
        by_name, by_index = self.with_client(body)
        self.assertIn("星球名：KARLIA", by_name)
        self.assertEqual(by_name, by_index)

    def test_planet_output_has_expected_labels(self):
        out = self.with_client(lambda c: c.planet_text("KARLIA"))
        for label in ("星球名：", "分区：", "所属阵营：", "部署的绝地潜兵数：", "数据获取时间："):
            self.assertIn(label, out)
        # 解放战或防御战，二者必有其一
        self.assertTrue(
            ("解放进度：" in out and "解放预计剩余时间：" in out)
            or ("已防御：" in out and "预测：" in out and "剩余时间：" in out),
            out,
        )

    def test_defense_planet_uses_defense_layout(self):
        async def body(client):
            data = await client.get_json("/api/v1/defenses")
            if not data.get("defenses"):
                return None
            name = data["defenses"][0]["planet_name"]
            return name, await client.planet_text(name)
        got = self.with_client(body)
        if got is None:
            self.skipTest("当前没有防御战")
        _, out = got
        self.assertIn("已防御：", out)
        self.assertIn("预测：", out)
        self.assertIn("剩余时间：", out)

    def test_planet_404_raises_friendly_error(self):
        with self.assertRaises(Hd2ApiError) as ctx:
            self.with_client(lambda c: c.planet_text("_NO_SUCH_PLANET_"))
        self.assertEqual(ctx.exception.status, 404)
        self.assertIn("未找到", ctx.exception.message)

    def test_dispatch(self):
        out = self.with_client(lambda c: c.dispatch_text())
        self.assertTrue(out.startswith("时间："), out[:50])
        self.assertIn("信息：", out)

    def test_trending_shape(self):
        data = self.with_client(lambda c: c.trending(5))
        self.assertEqual(len(data["planets"]), 5)
        players = [p["players"] for p in data["planets"]]
        self.assertEqual(players, sorted(players, reverse=True))
        self.assertGreater(data["totals"]["players_online"], 0)

    def test_full_command_flow(self):
        """端到端：走一遍 execute_command，确认回复是人能读的。"""
        out = self.with_client(lambda c: execute_command("/p KARLIA", c))
        self.assertIn("星球名：KARLIA", out)
        self.assertNotIn("{", out)          # 不是 JSON
        self.assertNotIn("null", out)

    def test_all_three_commands_end_to_end(self):
        async def body(client):
            return {
                "p": await execute_command("/p KARLIA", client),
                "d": await execute_command("/d", client),
                "t": await execute_command("/t", client),
            }
        out = self.with_client(body)
        self.assertIn("星球名：", out["p"])
        self.assertTrue(out["d"].startswith("时间："), out["d"][:60])
        self.assertIn("在线绝地潜兵最多的", out["t"])
        for key, text in out.items():
            self.assertLessEqual(len(text), 900, f"/{key} 回复超长")
            self.assertNotIn("战报服务", text, f"/{key} 出现了服务错误提示")

    def test_group_mention_prefix_works_end_to_end(self):
        """群聊里收到的是 `<@!机器人> /p KARLIA`，剥掉前缀后要能正常执行。"""
        out = self.with_client(
            lambda c: execute_command("<@!1234567890> /p KARLIA", c))
        self.assertIn("星球名：KARLIA", out)

    def test_client_rebuilds_session_when_loop_changes(self):
        """换了 event loop 之后应当重建 session 而不是炸掉。

        aiohttp 的 session 绑定在创建它的 loop 上，跨 loop 复用会报
        `Event loop is closed`。机器人是单 loop 长跑，但脚本/测试/框架重启 loop
        时会踩到，所以客户端要能自己发现并重建。

        这里不留下任何未关闭的真实 session：第一个 loop 正常收尾，
        然后塞一个「属于别的 loop」的替身进去，验证检测分支。
        """
        client = Hd2Client(API_BASE)

        async def once(close_after: bool = False):
            out = await client.planet_text("KARLIA")
            if close_after:
                await client.close()
            return out

        first = asyncio.run(once(close_after=True))

        class _StaleSession:
            closed = False

        client._session = _StaleSession()   # type: ignore[assignment]
        client._loop = object()             # type: ignore[assignment]

        second = asyncio.run(once(close_after=True))    # 全新的 loop
        self.assertEqual(first, second)
        self.assertIsNone(client._session, "收尾后不该留着 session")

    def test_connection_error_is_friendly(self):
        """指到一个没人监听的端口，应当给出可操作的提示而不是堆栈。"""
        async def body():
            bad = Hd2Client("http://127.0.0.1:9", timeout=3)
            try:
                await bad.planet_text("KARLIA")
            finally:
                await bad.close()
        with self.assertRaises(Hd2ApiError) as ctx:
            asyncio.run(body())
        self.assertIn("python run.py", ctx.exception.message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
