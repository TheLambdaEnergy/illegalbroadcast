"""访问 helldiversbot API 的异步客户端。

只做三件事：发 GET、解析 JSON、把各种失败翻译成**给用户看的中文提示**。
所有异常都收敛成 `Hd2ApiError`，调用方只需要 `str(exc)` 就能拿到一句人话。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp

DEFAULT_BASE = "http://127.0.0.1:8808"
DEFAULT_TIMEOUT = 20.0


class Hd2ApiError(Exception):
    """对用户友好的 API 错误。`message` 可直接作为回复内容。"""

    def __init__(self, message: str, *, status: int | None = None, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.status = status
        self.detail = detail


class Hd2Client:
    """线程/协程安全的轻量客户端。复用同一个 aiohttp session。"""

    def __init__(self, base_url: str = DEFAULT_BASE, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = (base_url or DEFAULT_BASE).rstrip("/")
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ 生命周期
    async def _get_session(self) -> aiohttp.ClientSession:
        """拿到可用的 session。

        aiohttp 的 session 绑定在创建它的 event loop 上，换一个 loop 再用就会
        `Event loop is closed`。机器人本身是单 loop 长跑，但测试、脚本或
        框架重启 loop 时会踩到，所以这里检测到 loop 变了就重建。
        """
        loop = asyncio.get_running_loop()
        if (self._session is None or self._session.closed
                or self._loop is not loop or loop.is_closed()):
            async with self._lock:
                loop = asyncio.get_running_loop()
                if (self._session is None or self._session.closed
                        or self._loop is not loop or loop.is_closed()):
                    self._session = aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        headers={"Accept": "application/json, text/plain"},
                    )
                    self._loop = loop
        return self._session

    async def close(self) -> None:
        """关闭 session。只在 session 所属的 loop 里调用才安全。"""
        session, self._session = self._session, None
        self._loop = None
        if session is not None and not session.closed:
            try:
                await session.close()
            except RuntimeError:
                # loop 已经关了，session 随之作废，忽略
                pass

    # ------------------------------------------------------------------ 请求
    async def get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        """取回原始响应体（文本或 JSON 字符串都行）。"""
        if not path.startswith("/"):
            path = "/" + path
        url = self.base_url + path
        try:
            session = await self._get_session()
            async with session.get(url, params=params) as resp:
                body = await resp.text()
                if resp.status == 200:
                    return body
                raise self._translate_error(resp.status, body)
        except Hd2ApiError:
            raise
        except aiohttp.ClientConnectorError as exc:
            raise Hd2ApiError(
                f"战报服务连不上（{self.base_url}）。\n"
                "请先在项目根目录运行 `python run.py` 启动 API。",
                detail=str(exc),
            ) from exc
        except asyncio.TimeoutError as exc:
            raise Hd2ApiError("战报服务响应超时，稍后再试。", detail=str(exc)) from exc
        except aiohttp.ClientError as exc:
            raise Hd2ApiError(f"请求战报服务失败：{type(exc).__name__}", detail=str(exc)) from exc

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        body = await self.get_text(path, params)
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise Hd2ApiError("战报服务返回了无法解析的内容。", detail=body[:200]) from exc

    # ------------------------------------------------------------------ 错误翻译
    @staticmethod
    def _translate_error(status: int, body: str) -> Hd2ApiError:
        detail = ""
        message = ""
        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                message = str(payload.get("error") or "")
                detail = str(payload.get("detail") or "")
        except json.JSONDecodeError:
            detail = body[:200]

        if status == 404:
            return Hd2ApiError(message or "没有找到这个星球。", status=status, detail=detail)
        if status == 400:
            return Hd2ApiError(message or "请求参数不对。", status=status, detail=detail)
        if status == 503:
            return Hd2ApiError(
                "战报服务暂时拿不到上游数据，稍后再试。", status=status, detail=detail)
        return Hd2ApiError(
            f"战报服务返回了错误（HTTP {status}）。", status=status, detail=detail)

    # ------------------------------------------------------------------ 业务封装
    async def planet_text(self, key: str) -> str:
        """单颗星球的可读文本（API 侧的 `?mode=md`）。"""
        return (await self.get_text(f"/api/v1/planets/{_quote(key)}",
                                    {"mode": "md"})).strip()

    async def dispatch_text(self) -> str:
        """最新一条游戏内快讯的可读文本。"""
        return (await self.get_text("/api/v1/dispatches", {"mode": "md"})).strip()

    async def trending(self, limit: int = 5) -> dict[str, Any]:
        """在线绝地潜兵最多的若干星球 + 全银河总数。"""
        planets = await self.get_json("/api/v1/planets", {
            "sort": "players", "order": "desc", "limit": limit, "compact": 1,
        })
        war = await self.get_json("/api/v1/war")
        return {"planets": planets.get("planets") or [],
                "totals": war.get("totals") or {}}


def _quote(value: str) -> str:
    from urllib.parse import quote
    return quote(str(value), safe="")
