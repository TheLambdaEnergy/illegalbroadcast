"""HTTP 层：极简路由 + 查询过滤 + 自动生成的 OpenAPI 文档（纯标准库）。"""

from __future__ import annotations

import json
import re
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__, config
from .httpclient import FetchError
from .normalize import planet_summary, population_history_block
from .service import WarService
from .textview import render_dispatch, render_planet, wants_text

# --------------------------------------------------------------------------- 路由表
class Route:
    def __init__(
        self,
        method: str,
        path: str,
        handler: Callable[..., Any],
        summary: str,
        description: str = "",
        tags: tuple[str, ...] = (),
        query: dict[str, str] | None = None,
    ) -> None:
        self.method = method
        self.path = path
        self.handler = handler
        self.summary = summary
        self.description = description
        self.tags = tags
        self.query = query or {}
        self.regex = re.compile(
            "^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path) + "$"
        )
        self.path_params = re.findall(r"\{(\w+)\}", path)


class Request:
    def __init__(self, method: str, path: str, query: dict[str, list[str]], body: bytes):
        self.method = method
        self.path = path
        self.query = query
        self.body = body

    def get(self, name: str, default: str | None = None) -> str | None:
        vals = self.query.get(name)
        return vals[0] if vals else default

    def get_int(self, name: str, default: int | None = None) -> int | None:
        raw = self.get(name)
        if raw is None or raw == "":
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def get_float(self, name: str, default: float | None = None) -> float | None:
        raw = self.get(name)
        if raw is None or raw == "":
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    def flag(self, name: str) -> bool:
        raw = self.get(name)
        return raw is not None and raw.lower() not in ("0", "false", "no", "")

    def csv(self, name: str) -> list[str]:
        raw = self.get(name)
        if not raw:
            return []
        return [x.strip() for x in raw.split(",") if x.strip()]


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# --------------------------------------------------------------------------- 辅助
OWNER_ALIASES = {
    "1": 1, "humans": 1, "human": 1, "superearth": 1, "超级地球": 1,
    "2": 2, "terminids": 2, "terminid": 2, "bugs": 2, "终结族": 2,
    "3": 3, "automatons": 3, "automaton": 3, "bots": 3, "机器人": 3,
    "4": 4, "illuminate": 4, "squids": 4, "光能者": 4,
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def _project(obj: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    if not fields:
        return obj
    out: dict[str, Any] = {}
    for f in fields:
        if f in obj:
            out[f] = obj[f]
    return out


def find_planet(snapshot: dict[str, Any], key: str) -> dict[str, Any]:
    """支持按 index、settingsHash、名称或 slug 查找星球。"""
    planets = snapshot.get("planets") or []
    if key.isdigit():
        idx = int(key)
        for p in planets:
            if p["index"] == idx:
                return p
        # 也可能是跨战争稳定的 settingsHash
        for p in planets:
            if str(p.get("settings_hash") or "") == key:
                return p
    want = slug(key)
    for p in planets:
        if slug(p["name"]) == want:
            return p
    for p in planets:
        if want and want in slug(p["name"]):
            return p
    raise ApiError(404, f"未找到星球: {key}")


# --------------------------------------------------------------------------- 处理器
class Handlers:
    def __init__(self, service: WarService) -> None:
        self.service = service

    # ---------------------------------------------------------------- 元信息
    def health(self, req: Request) -> dict[str, Any]:
        return self.service.health()

    def index(self, req: Request) -> dict[str, Any]:
        return {
            "name": "helldiversbot API",
            "version": __version__,
            "description": "《Helldivers 2》实时战报 API —— 数据源 helldiverscompanion.com",
            "endpoints": sorted(
                [f"{r.method} {r.path}" for r in ROUTES], key=lambda s: s
            ),
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    # ---------------------------------------------------------------- 战报
    def war(self, req: Request) -> dict[str, Any]:
        s = self.service.snapshot()
        return {
            "generated_at": s["generated_at"],
            "war": s["war"],
            "totals": s["totals"],
            "faction_labels": s["faction_labels"],
            "impact_calibration": s["impact_calibration"],
            "galaxy_statistics": s["galaxy_statistics"],
            "reference": s["reference"],
        }

    def snapshot(self, req: Request) -> dict[str, Any]:
        s = self.service.snapshot()
        if req.flag("compact"):
            out = dict(s)
            out["planets"] = [planet_summary(p) for p in s["planets"]]
            return out
        return s

    def stats(self, req: Request) -> dict[str, Any]:
        s = self.service.snapshot()
        return {
            "generated_at": s["generated_at"],
            "galactic_impact_multiplier": s["war"]["galactic_impact_multiplier"],
            "totals": s["totals"],
            "galaxy_statistics": s["galaxy_statistics"],
            "impact_calibration": s["impact_calibration"],
        }

    # ---------------------------------------------------------------- 星球
    def planets(self, req: Request) -> dict[str, Any]:
        s = self.service.snapshot()
        items = list(s["planets"])

        sector = req.get("sector")
        if sector:
            want = slug(sector)
            items = [p for p in items if slug(p["sector"]) == want]

        owner = req.get("owner")
        if owner:
            race = OWNER_ALIASES.get(slug(owner).replace("-", "") or owner.lower())
            if race is None:
                raise ApiError(400, f"未知阵营: {owner}（可用 1-4 或 humans/terminids/automatons/illuminate）")
            items = [p for p in items if p["owner"]["id"] == race]

        status = req.get("status")
        if status:
            items = [p for p in items if status in (p.get("status") or "") or slug(status) == slug(p.get("status") or "")]

        q = req.get("q")
        if q:
            if len(q) < 2:
                raise ApiError(400, "q 至少需要 2 个字符")
            nq = q.lower()
            items = [p for p in items if nq in p["name"].lower() or nq in p["sector"].lower()]

        if req.flag("active"):
            items = [p for p in items if p["players"] > 0 or p.get("event") or p.get("campaign")]

        if req.flag("defending"):
            items = [p for p in items if p.get("event")]

        if req.flag("contested"):
            items = [p for p in items if not p["is_liberated"] and p["players"] > 0]

        min_players = req.get_int("min_players")
        if min_players is not None:
            items = [p for p in items if p["players"] >= min_players]

        sort = req.get("sort", "players")
        reverse = (req.get("order", "desc").lower() != "asc")

        def key_of(p: dict[str, Any]):
            if sort == "name":
                return p["name"]
            if sort == "index":
                return p["index"]
            if sort == "sector":
                return p["sector"]
            if sort == "liberation":
                return p["liberation_percent"]
            if sort == "resistance":
                return (p.get("resistance") or {}).get("percent_per_hour") or 0
            if sort == "rate":
                return (p.get("liberation_rate") or {}).get("net_percent_per_hour") or -999
            if sort == "eta":
                return p.get("eta_liberation_seconds") or 9e18
            if sort == "health":
                return p["health"]
            return p["players"]

        if sort == "eta":
            reverse = not reverse  # ETA 越小越靠前才是「快」
        items.sort(key=key_of, reverse=reverse)

        total = len(items)
        offset = max(0, req.get_int("offset", 0) or 0)
        limit = req.get_int("limit")
        limited = items
        if limit is not None:
            limit = max(0, min(limit, 2000))
            limited = items[offset: offset + limit]
        elif offset:
            limited = items[offset:]

        fields = req.csv("fields")
        want_slim = req.flag("compact") or req.flag("brief")
        rows = [planet_summary(p) if want_slim else p for p in limited]
        if fields:
            rows = [_project(r, fields) for r in rows]

        return {
            "generated_at": s["generated_at"],
            "count": total,
            "returned": len(rows),
            "offset": offset,
            "planets": rows,
        }

    def planet(self, req: Request, key: str) -> Any:
        s = self.service.snapshot()
        p = find_planet(s, unquote(key))
        # ?mode=pt / ?mode=md -> 可读文本；其余（含缺省）-> JSON
        if wants_text(req):
            return render_planet(p, s["generated_at"])
        return {"generated_at": s["generated_at"], "planet": p}

    def planet_history(self, req: Request, key: str) -> dict[str, Any]:
        s = self.service.snapshot()
        p = find_planet(s, unquote(key))
        history = self.service.sources.planet_history(p["index"])
        data = history.get("data") or []
        return {
            "planet_index": p["index"],
            "planet_name": p["name"],
            "max_health": p["max_health"],
            "samples": len(data),
            "history": data,
        }

    def planet_regions(self, req: Request, key: str) -> dict[str, Any]:
        s = self.service.snapshot()
        p = find_planet(s, unquote(key))
        return {
            "planet_index": p["index"],
            "planet_name": p["name"],
            "regions": p.get("regions") or [],
        }

    # ---------------------------------------------------------------- 星区
    def sectors(self, req: Request) -> dict[str, Any]:
        s = self.service.snapshot()
        items = list(s["sectors"])
        owner = req.get("owner")
        if owner:
            race = OWNER_ALIASES.get(slug(owner).replace("-", "") or owner.lower())
            if race is None:
                raise ApiError(400, f"未知阵营: {owner}")
            from .reference import FACTION_FALLBACK
            en = FACTION_FALLBACK[race]["en"]
            items = [x for x in items if (x.get("owned_by") or {}).get(en)]
        if req.flag("active"):
            items = [x for x in items if x["players"] > 0]
        sort = req.get("sort", "players")
        reverse = req.get("order", "desc").lower() != "asc"
        if sort == "name":
            items.sort(key=lambda x: x["name"], reverse=reverse)
        elif sort == "liberated":
            items.sort(key=lambda x: x["liberated_percent"] or 0, reverse=reverse)
        elif sort == "planets":
            items.sort(key=lambda x: x["planet_count"], reverse=reverse)
        else:
            items.sort(key=lambda x: x["players"], reverse=reverse)
        return {
            "generated_at": s["generated_at"],
            "count": len(items),
            # sectors[].owned_by 用英文阵营名做键，这里给出中文映射
            "faction_labels": s["faction_labels"],
            "sectors": items,
        }

    def sector(self, req: Request, name: str) -> dict[str, Any]:
        s = self.service.snapshot()
        want = slug(unquote(name))
        for sec in s["sectors"]:
            if slug(sec["name"]) == want:
                planets = [p for p in s["planets"] if p["index"] in set(sec["planets"])]
                planets.sort(key=lambda p: -p["players"])
                return {
                    "generated_at": s["generated_at"],
                    "sector": sec,
                    "planets": planets,
                }
        raise ApiError(404, f"未找到星区: {name}")

    # ---------------------------------------------------------------- 战役
    def campaigns(self, req: Request) -> dict[str, Any]:
        s = self.service.snapshot()
        items = list(s["campaigns"])
        index = req.get_int("planet")
        if index is not None:
            items = [c for c in items if c["planet_index"] == index]
        return {"generated_at": s["generated_at"], "count": len(items), "campaigns": items}

    def defenses(self, req: Request) -> dict[str, Any]:
        s = self.service.snapshot()
        items = list(s["defenses"])
        if req.flag("active"):
            items = [e for e in items if (e.get("seconds_remaining") or 0) > 0]
        outcome = req.get("outcome")
        if outcome:
            items = [e for e in items if e.get("predicted_outcome") == outcome]
        return {"generated_at": s["generated_at"], "count": len(items), "defenses": items}

    def major_orders(self, req: Request) -> dict[str, Any]:
        s = self.service.snapshot()
        items = list(s["major_orders"])
        if req.flag("active"):
            items = [m for m in items if m["is_active"]]
        if not req.flag("all"):
            items = [m for m in items if m["is_active"]] or items[:1]
        return {"generated_at": s["generated_at"], "count": len(items), "major_orders": items}

    def dispatches(self, req: Request) -> Any:
        s = self.service.snapshot()
        items = list(s["dispatches"])
        # ?mode=pt / ?mode=md -> 只输出最新一条的可读文本
        if wants_text(req):
            return render_dispatch(items)
        limit = req.get_int("limit", 20) or 20
        return {
            "generated_at": s["generated_at"],
            "count": len(items),
            "dispatches": items[: max(0, min(limit, 500))],
        }

    def news(self, req: Request) -> dict[str, Any]:
        block = self.service.refresh_steam_news()
        limit = req.get_int("limit", 20) or 20
        items = block.get("items") or []
        return {
            "source": config.STEAM_NEWS_URL,
            "count": block.get("count", len(items)),
            "news": items[: max(0, min(limit, 200))],
        }

    def space_stations(self, req: Request) -> dict[str, Any]:
        s = self.service.snapshot()
        return {"generated_at": s["generated_at"], "space_stations": s["space_stations"]}

    def global_events(self, req: Request) -> dict[str, Any]:
        s = self.service.snapshot()
        return {"generated_at": s["generated_at"], "global_events": s["global_events"]}

    def population(self, req: Request) -> dict[str, Any]:
        """全银河在线人数时间序列（站点自己记录的口径）。"""
        payload = self.service.sources.extended_api_information_2days()
        hours = req.get_float("hours")
        block = population_history_block(payload, hours)
        # 顺带给出本 API 当前快照的口径，方便比对
        snap = self.service.snapshot()
        block["snapshot_players_online"] = snap["totals"]["players_online"]
        block["snapshot_players_by_owner_faction"] = snap["totals"].get("players_by_owner_faction")
        block["snapshot_players_by_enemy_faction"] = snap["totals"].get("players_by_enemy_faction")
        block["snapshot_generated_at"] = snap["generated_at"]
        if req.flag("compact"):
            block["samples"] = block["samples"][-40:]
        return block

    # ---------------------------------------------------------------- 调试
    def raw(self, req: Request) -> dict[str, Any]:
        raw = self.service.raw()
        if raw is None:
            raise ApiError(503, "尚无原始载荷")
        part = req.get("part")
        if part:
            if part not in raw:
                raise ApiError(404, f"原始载荷中没有字段 {part}；可用: {sorted(raw.keys())}")
            return {part: raw[part]}
        return raw

    def reference(self, req: Request) -> dict[str, Any]:
        ref = self.service.ref
        if req.flag("full"):
            return {
                "generated_at": ref.generated_at,
                "source": ref.source,
                "planets": ref.planets(),
                "sectors": ref.sectors(),
            }
        return {
            "generated_at": ref.generated_at,
            "source": ref.source,
            "war_id": ref.war_id,
            "planet_count": ref.planet_count,
            "sector_count": ref.sector_count,
            "effect_count": ref.effect_count,
            "factions": ref.factions,
        }


# --------------------------------------------------------------------------- 路由定义
def build_routes(h: Handlers) -> list[Route]:
    return [
        Route("GET", "/", h.index, "API 索引", "列出全部可用端点。", ("meta",)),
        Route("GET", "/health", h.health, "健康检查", "快照新鲜度、标定状态、上游错误。", ("meta",)),
        Route("GET", "/api/v1/war", h.war, "战争概览",
              "warId、warTime、银河影响系数、总在线人数、各阵营星球数、银河累计统计。", ("war",)),
        Route("GET", "/api/v1/snapshot", h.snapshot, "完整快照",
              "一次性返回全部数据（大，约 1-3 MB）。?compact=1 返回精简星球列表。", ("war",)),
        Route("GET", "/api/v1/stats", h.stats, "银河统计",
              "任务数、击杀数、开火/命中、死亡数、K/D 等。", ("war",)),

        Route("GET", "/api/v1/planets", h.planets, "星球列表",
              "支持筛选/排序/字段裁剪。是消费战报的主力端点。", ("planets",),
              query={
                  "sector": "按星区名过滤，例如 ?sector=Altus",
                  "owner": "按阵营过滤：1-4 或 humans/terminids/automatons/illuminate",
                  "status": "按状态过滤：解放中 / 已解放 / 被占领 / 防御中",
                  "q": "名称或星区模糊匹配（至少 2 字符）",
                  "active": "=1 只看有绝地潜兵或有战役的星球",
                  "defending": "=1 只看正在防御战的星球",
                  "contested": "=1 只看有绝地潜兵且尚未解放的星球",
                  "min_players": "最少在线绝地潜兵数",
                  "sort": "index | name | sector | players(默认) | liberation | rate | resistance | eta | health",
                  "order": "asc | desc(默认)",
                  "limit": "返回条数上限（默认全部，最多 2000）",
                  "offset": "分页偏移",
                  "compact": "=1 返回精简字段",
                  "fields": "逗号分隔的字段白名单，例如 ?fields=name,players,liberation_percent",
              }),
        Route("GET", "/api/v1/planets/{key}", h.planet, "单颗星球详情",
              "key 可以是 index（如 114）、名称（Aurora Bay 或 aurora-bay）或 settingsHash。"
              "加 `?mode=pt` 或 `?mode=md` 返回可读文本（见根目录 README_fancy.md）。",
              ("planets",),
              query={"mode": "pt / md 返回可读文本；raw 或缺省返回 JSON"}),
        # README_fancy.md 里的示例写的是单数 /api/v1/planet/{key}，一并注册
        Route("GET", "/api/v1/planet/{key}", h.planet, "单颗星球详情（单数别名）",
              "与 /api/v1/planets/{key} 完全相同，为兼容 README_fancy.md 的示例路径而设。",
              ("planets",),
              query={"mode": "pt / md 返回可读文本；raw 或缺省返回 JSON"}),
        Route("GET", "/api/v1/planets/{key}/history", h.planet_history, "星球历史",
              "直通 CDN 的近期采样（约 15 分钟一个点），用于画曲线。", ("planets",)),
        Route("GET", "/api/v1/planets/{key}/regions", h.planet_regions, "星球区域战况",
              "区域名称、尺寸、控制阵营、控制度、区域在线绝地潜兵数。", ("planets",)),

        Route("GET", "/api/v1/sectors", h.sectors, "星区列表",
              "每个星区的星球数、已解放数、各阵营占有数、在线绝地潜兵数。", ("sectors",),
              query={"owner": "只看含该阵营星球的星区", "active": "=1 只看有绝地潜兵的星区",
                     "sort": "players(默认) | name | liberated | planets"}),
        Route("GET", "/api/v1/sectors/{name}", h.sector, "单个星区详情", "含该星区全部星球的完整战报。", ("sectors",)),

        Route("GET", "/api/v1/campaigns", h.campaigns, "战役列表",
              "含解放战役与防御战役，带战役等级(count)。", ("campaigns",),
              query={"planet": "按星球 index 过滤"}),
        Route("GET", "/api/v1/defenses", h.defenses, "防御战 / 入侵",
              "入侵等级、防御进度、敌方推进速率、所需增援人数、胜负预测、倒计时。", ("campaigns",),
              query={"active": "=1 只看未结束的", "outcome": "defense_will_hold | too_close_to_call | defense_will_fail"}),

        Route("GET", "/api/v1/major-orders", h.major_orders, "重大指令",
              "默认只返回当前生效的指令；?all=1 返回历史全部。", ("story",),
              query={"active": "=1 只返回进行中的", "all": "=1 返回全部历史"}),
        Route("GET", "/api/v1/dispatches", h.dispatches, "游戏内快讯",
              "已剥离 <i=N> 富文本标记的原文。"
              "加 `?mode=pt` 或 `?mode=md` 只返回最新一条的可读文本。", ("story",),
              query={"limit": "默认 20",
                     "mode": "pt / md 只返回最新一条的可读文本；raw 或缺省返回 JSON"}),

        Route("GET", "/api/v1/news", h.news, "Steam 新闻", "官方公告与更新日志。", ("story",),
              query={"limit": "默认 20"}),
        Route("GET", "/api/v1/space-stations", h.space_stations, "民主空间站",
              "当前所在星球、战术行动、投票状态与生效效果。", ("story",)),
        Route("GET", "/api/v1/global-events", h.global_events, "银河级事件", "战争层面的叙事事件。", ("story",)),
        Route("GET", "/api/v1/population", h.population, "在线人数趋势",
              "全银河在线潜兵数时间序列（约 15 分钟一个采样点，覆盖近两天），"
              "含分阵营明细与银河影响系数。这是站点自己记录的口径，"
              "可用来核对 totals.players_online。", ("war",),
              query={"hours": "只保留最近 N 小时，例如 ?hours=6",
                     "compact": "=1 只保留最后 40 个采样点"}),

        Route("GET", "/api/v1/reference", h.reference, "静态参照表信息",
              "planet/sector 名称映射表的元信息；?full=1 返回整张表。", ("meta",)),
        Route("GET", "/api/v1/raw", h.raw, "上游原始载荷",
              "调试用。?part=warInfo 可只取一部分。", ("meta",)),
    ]


ROUTES: list[Route] = []


# --------------------------------------------------------------------------- OpenAPI
def openapi_spec(routes: list[Route]) -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for r in routes:
        if r.path == "/":
            continue
        params = [
            {"name": p, "in": "path", "required": True,
             "schema": {"type": "string"} if p != "key" else {"type": "string"},
             "description": "路径参数"}
            for p in r.path_params
        ]
        for qname, qdesc in r.query.items():
            params.append({
                "name": qname, "in": "query", "required": False,
                "schema": {"type": "string"}, "description": qdesc,
            })
        paths.setdefault(r.path, {})[r.method.lower()] = {
            "summary": r.summary,
            "description": r.description,
            "tags": list(r.tags),
            "parameters": params,
            "responses": {
                "200": {
                    "description": "成功",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                },
                "400": {"description": "参数错误"},
                "404": {"description": "未找到"},
                "503": {"description": "上游暂不可用"},
            },
        }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "helldiversbot API",
            "version": __version__,
            "description": (
                "《Helldivers 2》实时战报 API。\n\n"
                "* 实时数据：`https://helldiverscompanion.com/api/hell-divers-2-api/get-api-data-live`\n"
                "* 历史数据：`https://cdn.helldiverscompanion.com/live/...`\n"
                "* 名称映射：由 `scripts/refresh_reference.py` 固化的静态参照表\n\n"
                "所有速率单位为「百分比/小时」，所有时长单位为「秒」。"
            ),
        },
        "servers": [{"url": f"http://{config.HOST}:{config.PORT}"}],
        "tags": [
            {"name": "war", "description": "战争全局"},
            {"name": "planets", "description": "星球"},
            {"name": "sectors", "description": "星区"},
            {"name": "campaigns", "description": "战役与防御战"},
            {"name": "story", "description": "叙事：重大指令、快讯、新闻、空间站"},
            {"name": "meta", "description": "元信息与调试"},
        ],
        "paths": paths,
    }


DOCS_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>helldiversbot API 文档</title>
<style>
:root{--bg:#0c1116;--panel:#141b22;--line:#243039;--fg:#dfe7ee;--dim:#8fa3b3;--acc:#ffe710;--ok:#5fd38d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 "Segoe UI",system-ui,sans-serif}
header{padding:28px 24px 18px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#121a21,#0c1116)}
h1{margin:0 0 6px;font-size:22px;letter-spacing:.04em}
h1 span{color:var(--acc)}
p.sub{margin:0;color:var(--dim)}
main{max-width:1080px;margin:0 auto;padding:20px 24px 80px}
.tag{margin:28px 0 10px;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--acc)}
.route{background:var(--panel);border:1px solid var(--line);border-radius:8px;margin-bottom:10px;overflow:hidden}
.route .top{display:flex;gap:12px;align-items:baseline;padding:12px 14px}
.m{font-weight:700;font-size:11px;letter-spacing:.08em;color:#0c1116;background:var(--ok);border-radius:4px;padding:2px 7px}
.path{font-family:ui-monospace,Consolas,monospace;font-size:13.5px;color:#fff}
.sum{color:var(--fg);font-weight:600}
.desc{color:var(--dim);padding:0 14px 12px;font-size:13px}
.q{color:var(--dim);padding:0 14px 12px;font-size:12.5px}
.q code{background:#0c1116;border:1px solid var(--line);border-radius:4px;padding:1px 5px;color:#a9c8e0}
a.try{display:inline-block;margin:0 14px 12px;font-size:12.5px;color:var(--acc);text-decoration:none;border:1px solid #4a4410;border-radius:5px;padding:3px 10px}
a.try:hover{background:#2a2708}
.note{background:#141b22;border-left:3px solid var(--acc);border-radius:0 8px 8px 0;padding:12px 16px;color:var(--dim);margin-bottom:22px}
.note b{color:var(--fg)}
code.k{background:#0c1116;border:1px solid var(--line);border-radius:4px;padding:1px 5px;color:#a9c8e0}
</style></head><body>
<header><h1>HELLDIVERS <span>2</span> 战报 API</h1>
<p class="sub">数据源 helldiverscompanion.com · 静态名称映射 · 纯标准库实现</p></header>
<main>
<div class="note"><b>单位约定</b>：所有速率均为「百分比 / 小时」，所有时长均为「秒」。
派生字段都给出公式来源；数据不足时返回 <code class="k">null</code> 而非 0。
完整机器可读描述见 <a class="try" style="margin:0" href="/openapi.json">/openapi.json</a></div>
<div id="app"></div>
</main>
<script>
const TAGS={war:"战争全局",planets:"星球",sectors:"星区",campaigns:"战役与防御战",story:"叙事与新闻",meta:"元信息与调试"};
fetch("/openapi.json").then(r=>r.json()).then(spec=>{
  const byTag={};
  for(const [path,ops] of Object.entries(spec.paths)){
    for(const [method,op] of Object.entries(ops)){
      const t=(op.tags&&op.tags[0])||"meta";
      (byTag[t]=byTag[t]||[]).push({path,method,op});
    }
  }
  const app=document.getElementById("app");
  for(const t of Object.keys(TAGS)){
    if(!byTag[t]) continue;
    const h=document.createElement("div");h.className="tag";h.textContent=TAGS[t];app.appendChild(h);
    byTag[t].sort((a,b)=>a.path.localeCompare(b.path));
    for(const {path,method,op} of byTag[t]){
      const d=document.createElement("div");d.className="route";
      const example=path.replace(/\\{(\\w+)\\}/,(m,n)=>n==="key"?"114":n==="name"?"Altus":"1");
      let q="";
      const qs=(op.parameters||[]).filter(p=>p.in==="query");
      if(qs.length) q='<div class="q">查询参数：'+qs.map(p=>'<code>'+p.name+'</code> '+p.description).join(" · ")+'</div>';
      d.innerHTML='<div class="top"><span class="m">'+method.toUpperCase()+'</span>'
        +'<span class="path">'+path+'</span><span class="sum">'+op.summary+'</span></div>'
        +'<div class="desc">'+(op.description||"")+'</div>'+q
        +'<a class="try" href="'+example+'" target="_blank">试一下 →</a>';
      app.appendChild(d);
    }
  }
});
</script></body></html>
"""


# --------------------------------------------------------------------------- HTTP
class _Handler(BaseHTTPRequestHandler):
    server_version = f"helldiversbot/{__version__}"
    protocol_version = "HTTP/1.1"

    service: WarService
    routes: list[Route]

    # 关掉默认的逐请求 stderr 日志噪音，改由子类控制
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        if getattr(self.server, "quiet", True):
            return
        super().log_message(fmt, *args)

    # -------------------------------------------------------------- 输出
    def _send(self, status: int, payload: Any, pretty: bool = False) -> None:
        if isinstance(payload, (dict, list)):
            body = json.dumps(
                payload,
                ensure_ascii=False,
                indent=2 if pretty else None,
                separators=None if pretty else (",", ":"),
            ).encode("utf-8")
            ctype = "application/json; charset=utf-8"
        else:
            body = str(payload).encode("utf-8")
            ctype = "text/plain; charset=utf-8"

        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    # -------------------------------------------------------------- 分发
    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query, keep_blank_values=True)
        req = Request(method, path, query, b"")

        try:
            if path == "/docs":
                return self._send_html(200, DOCS_HTML)
            if path == "/openapi.json":
                return self._send(200, openapi_spec(self.routes))
            if path == "/favicon.ico":
                return self._send(404, {"error": "not found"})

            for route in self.routes:
                if route.method != method:
                    continue
                m = route.regex.match(path)
                if not m:
                    continue
                kwargs = {k: unquote(v) for k, v in m.groupdict().items()}
                result = route.handler(req, **kwargs)
                if isinstance(result, tuple):
                    status, payload = result
                else:
                    status, payload = 200, result
                return self._send(status, payload, pretty=req.flag("pretty"))

            self._send(404, {
                "error": "not found",
                "path": path,
                "hint": "GET / 可列出全部端点，GET /docs 是可视化文档",
            })
        except ApiError as exc:
            self._send(exc.status, {"error": exc.message, "path": path})
        except FetchError as exc:
            self._send(503, {"error": "上游数据源暂不可用", "detail": str(exc)})
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001 — 兜底，避免单个请求打挂服务器
            self._send(500, {
                "error": "internal error",
                "detail": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc().splitlines()[-6:],
            })


def make_server(service: WarService, host: str | None = None, port: int | None = None,
                quiet: bool = True) -> ThreadingHTTPServer:
    """构建（但不启动）HTTP 服务。

    注意：`port=0` 表示「让内核挑一个空闲端口」，所以必须用 `is None` 判断。
    写成 `port or config.PORT` 会把 0 当成 falsy 静默换回默认端口。
    """
    global ROUTES
    handlers = Handlers(service)
    ROUTES = build_routes(handlers)

    cls = type("BoundHandler", (_Handler,), {"service": service, "routes": ROUTES})
    bind_host = config.HOST if host is None else host
    bind_port = config.PORT if port is None else port
    httpd = ThreadingHTTPServer((bind_host, bind_port), cls)
    httpd.daemon_threads = True
    httpd.quiet = quiet  # type: ignore[attr-defined]
    return httpd


def serve(service: WarService | None = None, host: str | None = None,
          port: int | None = None, quiet: bool = True) -> None:
    svc = service or WarService()
    svc.start()
    httpd = make_server(svc, host, port, quiet)
    addr = f"http://{host or config.HOST}:{port or config.PORT}"
    print(f"helldiversbot API 已启动 -> {addr}")
    print(f"  文档: {addr}/docs    索引: {addr}/    健康: {addr}/health")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止…")
    finally:
        httpd.shutdown()
        svc.stop()


__all__ = ["serve", "make_server", "build_routes", "openapi_spec", "WarService", "Handlers"]
