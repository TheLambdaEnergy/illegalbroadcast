"""HELLDIVERSBOT —— 把 helldiversbot 的 API 接到 QQ 上。

覆盖 QQ 开放平台的四类消息（见 botpy 的 `Intents` 与 `flags.py`）：

| 场景 | Intents 标志 | 事件 |
|---|---|---|
| 频道里 @机器人 | `public_guild_messages` | `on_at_message_create` |
| 频道的私信 | `direct_message` | `on_direct_message_create` |
| QQ 群里 @机器人 | `public_messages` | `on_group_at_message_create` |
| QQ 私聊 | `public_messages` | `on_c2c_message_create` |

命令表与回复格式在 `commands.py`，那儿不依赖 botpy，可以单独测。

启动：

    python run.py                 # 先起战报 API（另一个终端）
    python bot/qqbot.py           # 再起机器人

凭据来源见 `bot/config.example.yaml`。
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import botpy  # noqa: E402
from botpy import logging  # noqa: E402
from botpy.message import C2CMessage, DirectMessage, GroupMessage, Message  # noqa: E402

from commands import execute_command  # noqa: E402
from hd2_api import Hd2Client  # noqa: E402

_log = logging.get_logger()

DEFAULT_API_BASE = "http://127.0.0.1:8808"
DEFAULT_MAX_CHARS = 900
DEFAULT_TIMEOUT = 20.0


# --------------------------------------------------------------------------- 配置
def load_config(path: str | None = None) -> dict:
    """读取配置。

    优先级：环境变量 > config.yaml > 默认值。
    这样部署时可以用环境变量注入凭据，不必把密钥写进文件。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = path or os.path.join(here, "config.yaml")

    cfg: dict = {}
    if os.path.exists(path):
        from botpy.ext.cog_yaml import read
        try:
            cfg = dict(read(path) or {})
        except Exception as exc:  # noqa: BLE001
            _log.warning(f"读取 {path} 失败：{exc}")
    else:
        _log.warning(f"没找到 {path}；请从 config.example.yaml 复制一份。")

    for key, env in (("appid", "QQBOT_APPID"),
                     ("secret", "QQBOT_SECRET"),
                     ("api_base", "QQBOT_API_BASE"),
                     ("max_reply_chars", "QQBOT_MAX_CHARS"),
                     ("http_timeout", "QQBOT_HTTP_TIMEOUT")):
        value = os.environ.get(env)
        if value:
            cfg[key] = value

    cfg.setdefault("api_base", DEFAULT_API_BASE)
    cfg["max_reply_chars"] = int(cfg.get("max_reply_chars") or DEFAULT_MAX_CHARS)
    cfg["http_timeout"] = float(cfg.get("http_timeout") or DEFAULT_TIMEOUT)
    return cfg


# --------------------------------------------------------------------------- 客户端
class HelldiversClient(botpy.Client):
    def __init__(self, *args, api_base: str = DEFAULT_API_BASE,
                 max_reply_chars: int = DEFAULT_MAX_CHARS,
                 http_timeout: float = DEFAULT_TIMEOUT, **kwargs):
        super().__init__(*args, **kwargs)
        self.hd2 = Hd2Client(api_base, timeout=http_timeout)
        self.max_reply_chars = max_reply_chars

    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")
        _log.info(f"战报 API: {self.hd2.base_url}")

    async def close(self):
        await self.hd2.close()
        await super().close()

    # ------------------------------------------------------------------ 统一处理
    async def _handle(self, message, scene: str, reply):
        """四类事件共用的处理流程：解析 -> 取数 -> 回复。"""
        content = getattr(message, "content", "") or ""
        _log.info(f"[{scene}] {content!r}")
        try:
            text = await execute_command(
                content, self.hd2, max_reply_chars=self.max_reply_chars)
        except Exception as exc:  # noqa: BLE001 — 任何意外都不能让机器人掉线
            _log.error(f"[{scene}] 处理失败: {type(exc).__name__}: {exc}")
            text = "处理这条命令时出错了，稍后再试。"

        if not text:
            return
        try:
            await reply(text)
        except Exception as exc:  # noqa: BLE001
            _log.error(f"[{scene}] 回复失败: {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ 频道
    async def on_at_message_create(self, message: Message):
        """频道里 @机器人。"""
        async def reply(text):
            await message.reply(content=text)
        await self._handle(message, "频道@", reply)

    async def on_direct_message_create(self, message: DirectMessage):
        """频道的私信。"""
        async def reply(text):
            await message.reply(content=text)
        await self._handle(message, "频道私信", reply)

    # ------------------------------------------------------------------ QQ 群 / 私聊
    async def on_group_at_message_create(self, message: GroupMessage):
        """QQ 群里 @机器人。"""
        async def reply(text):
            await message.reply(content=text)
        await self._handle(message, "QQ群@", reply)

    async def on_c2c_message_create(self, message: C2CMessage):
        """QQ 私聊。"""
        async def reply(text):
            await message.reply(content=text)
        await self._handle(message, "QQ私聊", reply)


# --------------------------------------------------------------------------- 入口
def build_client(cfg: dict) -> HelldiversClient:
    intents = botpy.Intents(
        public_guild_messages=True,   # 频道 @机器人
        direct_message=True,          # 频道私信
        public_messages=True,         # QQ 群 / QQ 私聊
    )
    return HelldiversClient(
        intents=intents,
        api_base=cfg["api_base"],
        max_reply_chars=cfg["max_reply_chars"],
        http_timeout=cfg["http_timeout"],
        timeout=30,
        is_sandbox=False,
    )


def main(argv: list[str] | None = None) -> int:
    cfg = load_config()
    appid, secret = cfg.get("appid"), cfg.get("secret")
    if not appid or not secret:
        _log.error("缺少 appid/secret。请复制 bot/config.example.yaml 为 bot/config.yaml "
                   "并填写，或设置环境变量 QQBOT_APPID / QQBOT_SECRET。")
        return 1

    client = build_client(cfg)
    client.run(appid=str(appid), secret=str(secret))
    return 0


if __name__ == "__main__":
    sys.exit(main())
