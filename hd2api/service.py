"""服务层：负责抓取、缓存、后台轮询，并把归一化快照提供给 HTTP 层。"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from . import config
from .httpclient import FetchError, HttpClient
from .normalize import (
    ImpactCalibration,
    build_snapshot,
    collect_calibration_samples,
    steam_news_block,
)
from .reference import get_reference
from .sources import Sources


class WarService:
    """线程安全的战报服务。

    数据流：
      helldiverscompanion live  -->  归一化  -->  内存快照  -->  HTTP 层
      CDN 星球历史              -->  标定每绝地潜兵影响力  -->  实测速率
    """

    def __init__(
        self,
        sources: Sources | None = None,
        enable_poller: bool | None = None,
    ) -> None:
        self.sources = sources or Sources(HttpClient())
        self.ref = get_reference()
        self.enable_poller = config.ENABLE_POLLER if enable_poller is None else enable_poller

        self._lock = threading.RLock()
        self._snapshot: dict[str, Any] | None = None
        self._live_raw: dict[str, Any] | None = None
        self._histories: dict[int, Any] = {}
        self._calibration = ImpactCalibration(config.DEFAULT_HP_PER_DIVER_PER_SECOND)
        self._steam: dict[str, Any] | None = None

        self._live_at = 0.0
        self._history_at = 0.0
        self._steam_at = 0.0

        self.last_error: str | None = None
        self.last_error_at: str | None = None
        self.refresh_count = 0

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ 生命周期
    def start(self, blocking_initial: bool = True) -> None:
        """首次同步加载，然后（可选）启动后台轮询线程。"""
        if blocking_initial:
            self.refresh(force=True)
        if self.enable_poller and self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="hd2-poller", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    # ------------------------------------------------------------------ 轮询
    def _loop(self) -> None:
        while not self._stop.wait(2.0):
            try:
                self.refresh()
            except Exception as exc:  # noqa: BLE001 — 轮询线程绝不能因异常退出
                self._record_error(exc)

    def _record_error(self, exc: Exception) -> None:
        with self._lock:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.last_error_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ------------------------------------------------------------------ 刷新
    def refresh(self, force: bool = False) -> bool:
        """按各自的 TTL 刷新；返回是否有数据被更新。"""
        now = time.monotonic()
        updated = False

        need_live = force or self._live_raw is None or (now - self._live_at) >= config.LIVE_REFRESH_SECONDS
        if need_live:
            try:
                live = self.sources.live()
            except (FetchError, OSError) as exc:
                self._record_error(exc)
                # 已有旧快照时降级继续服务，而不是直接失败
                if self._live_raw is None:
                    raise
            else:
                with self._lock:
                    self._live_raw = live
                    self._live_at = time.monotonic()
                updated = True

        need_hist = (
            force
            or not self._histories
            or (now - self._history_at) >= config.HISTORY_REFRESH_SECONDS
        )
        if need_hist and self._live_raw is not None:
            try:
                indices = self._active_indices()
                histories = self.sources.planet_histories(indices)
                got = {i: h for i, h in histories.items() if h}
                if got:
                    with self._lock:
                        self._histories.update(got)
                        self._calibration = ImpactCalibration(
                            config.DEFAULT_HP_PER_DIVER_PER_SECOND,
                            collect_calibration_samples(self._histories),
                        )
                        self._history_at = time.monotonic()
                    updated = True
            except (FetchError, OSError) as exc:
                self._record_error(exc)

        if updated:
            self._rebuild()
        return updated

    def refresh_steam_news(self, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if not force and self._steam is not None and (now - self._steam_at) < config.NEWS_REFRESH_SECONDS:
            return self._steam
        try:
            payload = self.sources.steam_news()
        except (FetchError, OSError) as exc:
            self._record_error(exc)
            return self._steam or {"count": 0, "items": [], "error": str(exc)}
        block = steam_news_block(payload)
        with self._lock:
            self._steam = block
            self._steam_at = time.monotonic()
        return block

    def _active_indices(self) -> list[int]:
        """需要跟踪历史的星球：正在打战役/防御的，加上在线人数最多的那些。"""
        live = self._live_raw or {}
        ws = live.get("warStatus") or {}
        indices: set[int] = set()
        for c in ws.get("campaigns") or []:
            indices.add(int(c.get("planetIndex", -1)))
        for e in ws.get("planetEvents") or []:
            indices.add(int(e.get("planetIndex", -1)))
        statuses = ws.get("planetStatus") or []
        top = sorted(statuses, key=lambda s: -(s.get("players") or 0))[:15]
        indices.update(int(s.get("index", -1)) for s in top)
        indices.discard(-1)
        return sorted(indices)

    def _rebuild(self) -> None:
        with self._lock:
            live = self._live_raw
            histories = dict(self._histories)
            calibration = self._calibration
        if live is None:
            return
        snapshot = build_snapshot(live, self.ref, histories, calibration)
        with self._lock:
            self._snapshot = snapshot
            self.refresh_count += 1

    # ------------------------------------------------------------------ 读取
    def snapshot(self, auto_refresh: bool = True) -> dict[str, Any]:
        if self._snapshot is None:
            if auto_refresh:
                self.refresh(force=True)
            if self._snapshot is None:
                raise FetchError(config.LIVE_URL, "尚无可用快照，且首次抓取失败")
        return self._snapshot  # type: ignore[return-value]

    def raw(self) -> dict[str, Any] | None:
        return self._live_raw

    def calibration(self) -> ImpactCalibration:
        return self._calibration

    def health(self) -> dict[str, Any]:
        snap = self._snapshot
        age = None
        if snap:
            try:
                gen = datetime.fromisoformat(snap["generated_at"].replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - gen).total_seconds()
            except (KeyError, ValueError):
                age = None
        state = "ok"
        if snap is None:
            state = "starting"
        elif age is not None and age > config.MAX_STALE_SECONDS:
            state = "degraded"
        return {
            "state": state,
            "snapshot_age_seconds": round(age, 1) if age is not None else None,
            "snapshot_generated_at": (snap or {}).get("generated_at"),
            "refresh_count": self.refresh_count,
            "tracked_planet_histories": len(self._histories),
            "calibration": self._calibration.to_dict(),
            "last_error": self.last_error,
            "last_error_at": self.last_error_at,
            "poller_enabled": self.enable_poller,
            "reference": {
                "generated_at": self.ref.generated_at,
                "planets": self.ref.planet_count,
                "sectors": self.ref.sector_count,
            },
        }
