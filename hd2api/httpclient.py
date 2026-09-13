"""带重试、超时与并发能力的极简 HTTP 客户端（纯标准库）。"""

from __future__ import annotations

import gzip
import json
import random
import socket
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable

from . import config


class FetchError(RuntimeError):
    """上游请求最终失败。"""

    def __init__(self, url: str, message: str, status: int | None = None):
        super().__init__(f"{url} -> {message}")
        self.url = url
        self.status = status


class HttpClient:
    """线程安全、可复用的 HTTP JSON 客户端。"""

    def __init__(
        self,
        timeout: float = config.HTTP_TIMEOUT,
        retries: int = config.HTTP_RETRIES,
        backoff: float = config.HTTP_BACKOFF,
        user_agent: str = config.USER_AGENT,
    ) -> None:
        self.timeout = timeout
        self.retries = max(1, retries)
        self.backoff = backoff
        # 每个线程独立的 opener（urllib 的 opener 不是线程安全的）
        self._local = threading.local()
        self.user_agent = user_agent

    # ------------------------------------------------------------------ 内部
    def _opener(self) -> urllib.request.OpenerDirector:
        op = getattr(self._local, "opener", None)
        if op is None:
            op = urllib.request.build_opener()
            self._local.opener = op
        return op

    # ------------------------------------------------------------------ 公开
    def get_bytes(self, url: str, accept: str = "application/json") -> bytes:
        last: Exception | None = None
        for attempt in range(self.retries):
            req = urllib.request.Request(url, headers={
                "User-Agent": self.user_agent,
                "Accept": accept,
                "Accept-Encoding": "gzip",
                "Cache-Control": "no-cache",
            })
            try:
                with self._opener().open(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    return raw
            except urllib.error.HTTPError as exc:
                last = exc
                # 4xx（除 429）不重试，没意义
                if exc.code != 429 and 400 <= exc.code < 500:
                    raise FetchError(url, f"HTTP {exc.code}", exc.code) from exc
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
                last = exc
            if attempt + 1 < self.retries:
                # 指数退避 + 抖动，避免并发请求同时重试
                time.sleep(self.backoff ** attempt * (0.6 + random.random() * 0.8))
        raise FetchError(url, f"{type(last).__name__}: {last}")

    def get_json(self, url: str) -> Any:
        raw = self.get_bytes(url)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            head = raw[:180].decode("utf-8", "replace")
            raise FetchError(url, f"JSON 解析失败: {exc} | 开头: {head!r}") from exc

    def get_many_json(self, urls: Iterable[str], max_workers: int | None = None) -> dict[str, Any]:
        """并发抓取多个 URL，返回 {url: parsed}；失败的条目值为 None。"""
        urls = list(urls)
        if not urls:
            return {}
        workers = min(max_workers or config.HTTP_MAX_WORKERS, len(urls))

        def one(u: str):
            try:
                return u, self.get_json(u)
            except Exception:  # noqa: BLE001 — 单点失败不应拖垮整批
                return u, None

        with ThreadPoolExecutor(max_workers=workers) as pool:
            return dict(pool.map(one, urls))
