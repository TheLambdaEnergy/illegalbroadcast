"""上游数据源封装：把 helldiverscompanion 的若干接口收敛成少量方法。"""

from __future__ import annotations

from typing import Any

from . import config
from .httpclient import HttpClient


class Sources:
    """helldiverscompanion.com 的数据源集合。"""

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient()

    # ------------------------------------------------------------ 主快照
    def live(self, channel: str = "live") -> dict[str, Any]:
        """warInfo + warStatus + warStats + news + episodes 的完整快照（约 400 KB）。"""
        url = config.LIVE_URL if channel == "live" else config.LIVE_URL_BETA
        return self.client.get_json(url)

    # ------------------------------------------------------------ CDN 历史
    def planet_history(self, index: int) -> dict[str, Any]:
        """单颗星球的近期历史（health / players / regen，约 15 分钟一个采样点）。"""
        return self.client.get_json(config.CDN_PLANET_HISTORY.format(index=index))

    def planet_histories(self, indices: list[int]) -> dict[int, Any]:
        urls = {i: config.CDN_PLANET_HISTORY.format(index=i) for i in indices}
        got = self.client.get_many_json(urls.values())
        return {i: got.get(u) for i, u in urls.items()}

    def planet_events_2days(self) -> dict[str, Any]:
        """近两天的星球事件（防御/入侵）历史。"""
        return self.client.get_json(config.CDN_PLANET_EVENTS_2D)

    def planet_regions_recent(self) -> dict[str, Any]:
        """近期区域级历史（含各区域绝地潜兵分布）。"""
        return self.client.get_json(config.CDN_PLANET_REGIONS_RECENT)

    def global_resources_recent(self) -> dict[str, Any]:
        return self.client.get_json(config.CDN_GLOBAL_RESOURCES_RECENT)

    def assignments_recent(self) -> dict[str, Any]:
        return self.client.get_json(config.CDN_ASSIGNMENTS_RECENT)

    def space_station_history(self, id32: int) -> dict[str, Any]:
        return self.client.get_json(config.CDN_SPACE_STATION_2D.format(id32=id32))

    def extended_api_information_2days(self) -> dict[str, Any]:
        """全银河时间序列（站点自己记录的 totalPlayerCount 等）。"""
        return self.client.get_json(config.CDN_EXTENDED_API_INFO_2D)

    def elections_current(self) -> dict[str, Any]:
        return self.client.get_json(config.CDN_ELECTIONS_CURRENT)

    def personal_orders_current(self) -> dict[str, Any]:
        return self.client.get_json(config.CDN_PERSONAL_ORDERS_CURRENT)

    # ------------------------------------------------------------ Steam 新闻
    def steam_news(self) -> dict[str, Any]:
        return self.client.get_json(config.STEAM_NEWS_URL)
