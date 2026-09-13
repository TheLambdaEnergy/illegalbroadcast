"""全局配置。所有可调项都允许用环境变量覆盖。"""

from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
REFERENCE_PATH = os.path.join(DATA_DIR, "reference.json")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- 数据源
# 主快照：一次请求拿到 warInfo + warStatus + warStats + news + episodes
LIVE_URL = os.environ.get(
    "HD2_LIVE_URL",
    "https://helldiverscompanion.com/api/hell-divers-2-api/get-api-data-live",
)
# 站点自身也支持 beta 通道: /api/hell-divers-2-api/get-api-data-beta
LIVE_URL_BETA = os.environ.get(
    "HD2_LIVE_URL_BETA",
    "https://helldiverscompanion.com/api/hell-divers-2-api/get-api-data-beta",
)

CDN_BASE = os.environ.get("HD2_CDN_BASE", "https://cdn.helldiverscompanion.com/live")
CDN_PLANET_HISTORY = CDN_BASE + "/planets/{index}/recent.json"
CDN_PLANET_EVENTS_2D = CDN_BASE + "/planetEvents/2days.json"
CDN_PLANET_REGIONS_RECENT = CDN_BASE + "/planetRegions/recent.json"
CDN_GLOBAL_RESOURCES_RECENT = CDN_BASE + "/globalResources/recent.json"
CDN_ASSIGNMENTS_RECENT = CDN_BASE + "/assignments/recent.json"
CDN_SPACE_STATION_2D = CDN_BASE + "/spaceStations/{id32}/2days.json"
# 站点自己记录的全银河时间序列：总在线人数、分阵营在线人数、银河影响系数、累计统计。
# 这是校验 players_online 分母的权威口径（见 README「与官网数值的核对」）。
CDN_EXTENDED_API_INFO_2D = CDN_BASE + "/extendedApiInformation/2days.json"
CDN_ELECTIONS_CURRENT = CDN_BASE + "/elections/current.json"
CDN_PERSONAL_ORDERS_CURRENT = CDN_BASE + "/personalOrders/current.json"

STEAM_NEWS_URL = os.environ.get(
    "HD2_STEAM_NEWS_URL", "https://helldiverscompanion.com/api/steam-api/news"
)

# ---------------------------------------------------------------- 刷新节奏（秒）
LIVE_REFRESH_SECONDS = _int("HD2_LIVE_REFRESH_SECONDS", 40)
HISTORY_REFRESH_SECONDS = _int("HD2_HISTORY_REFRESH_SECONDS", 300)
NEWS_REFRESH_SECONDS = _int("HD2_NEWS_REFRESH_SECONDS", 900)
EVENTS_REFRESH_SECONDS = _int("HD2_EVENTS_REFRESH_SECONDS", 300)

# 允许的最大陈旧时间：超过则 /health 报 degraded
MAX_STALE_SECONDS = _int("HD2_MAX_STALE_SECONDS", 300)

# ---------------------------------------------------------------- 网络
HTTP_TIMEOUT = _float("HD2_HTTP_TIMEOUT", 30.0)
HTTP_RETRIES = _int("HD2_HTTP_RETRIES", 3)
HTTP_BACKOFF = _float("HD2_HTTP_BACKOFF", 1.2)
HTTP_MAX_WORKERS = _int("HD2_HTTP_MAX_WORKERS", 12)

# ---------------------------------------------------------------- 服务
HOST = os.environ.get("HD2_HOST", "127.0.0.1")
PORT = _int("HD2_PORT", 8808)
ENABLE_POLLER = os.environ.get("HD2_POLLER", "1") not in ("0", "false", "False")

# 每绝地潜兵影响力（HP/秒）的兜底值。运行时会用真实历史数据自动重新标定，
# 该常量只在历史数据不足时使用。标定依据见 README「指标口径」。
DEFAULT_HP_PER_DIVER_PER_SECOND = _float("HD2_HP_PER_DIVER", 0.0004443)

# 计算实测解放速率时使用的历史窗口（秒）
RATE_WINDOW_SECONDS = _int("HD2_RATE_WINDOW_SECONDS", 3600)

USER_AGENT = os.environ.get(
    "HD2_USER_AGENT",
    "helldiversbot/1.0 (local read-only war data aggregator)",
)
