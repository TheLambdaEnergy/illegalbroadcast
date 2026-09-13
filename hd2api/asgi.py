"""可选的 FastAPI/ASGI 前端。

设计要点
--------
**复用，而不是重写。** 所有业务逻辑都在 `web.Handlers` 里，两种前端共用：

    web.py   ->  标准库 ThreadingHTTPServer（默认，零依赖）
    asgi.py  ->  FastAPI + uvicorn（可选，带 Swagger UI 和 ReDoc）

路由表同样取自 `web.build_routes()`，所以两边的端点、参数、错误语义完全一致，
不会出现「文档里有、标准库版没有」这种漂移。

FastAPI 不是必需依赖。没装的时候这个模块 import 会失败，但标准库版照常工作。

安装（pip 在受限环境里可能用不了，用自带脚本绕开）:

    python scripts/vendor_deps.py
    $env:PYTHONPATH="$PWD/.deps"     # PowerShell
    python run.py --fastapi
"""

from __future__ import annotations

import json
from inspect import Parameter, Signature
from typing import Any

from . import __version__
from .config import ENABLE_POLLER, HOST, PORT
from .httpclient import FetchError
from .service import WarService
from .web import DOCS_HTML, ApiError, Handlers, Request, build_routes

try:  # pragma: no cover - 取决于是否安装了可选依赖
    from fastapi import FastAPI, Query
    from fastapi import Request as FastAPIRequest
    from fastapi.responses import HTMLResponse, JSONResponse, Response
    FASTAPI_AVAILABLE = True
    IMPORT_ERROR: str | None = None
except Exception as exc:  # noqa: BLE001
    FASTAPI_AVAILABLE = False
    IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


def _json_response(payload: Any, pretty: bool) -> Response:
    """与标准库版保持一致的 JSON 序列化（含 ?pretty=1）。"""
    if isinstance(payload, (dict, list)):
        body = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        ).encode("utf-8")
        return Response(content=body, media_type="application/json; charset=utf-8")
    return Response(content=str(payload).encode("utf-8"),
                    media_type="text/plain; charset=utf-8")

DESCRIPTION = """\
《Helldivers 2》实时战报 API —— 把 helldiverscompanion.com 那些全是游戏内 ID 的
JSON 翻译成人类可读的字段。

* **实时数据**：`/api/hell-divers-2-api/get-api-data-live`
* **历史数据**：`cdn.helldiverscompanion.com/live/...`
* **名称映射**：仓库内固化的静态参照表（273 星球 / 56 星区）

**单位约定**：所有速率都是「百分比/小时」，所有时长都是「秒」。
派生字段在数据不足时返回 `null` 而不是 0。
"""


def _build_signature(route) -> Signature:
    """按路由声明动态生成函数签名，好让 Swagger UI 渲染出输入框。

    真实函数用 `**kwargs` 接收，这里只是告诉 FastAPI 有哪些参数、什么类型。
    """
    params = [
        Parameter("request", Parameter.POSITIONAL_OR_KEYWORD, annotation=FastAPIRequest)
    ]
    for name in route.path_params:
        params.append(Parameter(name, Parameter.POSITIONAL_OR_KEYWORD, annotation=str))
    for name, desc in route.query.items():
        params.append(Parameter(
            name,
            Parameter.POSITIONAL_OR_KEYWORD,
            annotation=str | None,
            default=Query(None, description=desc),
        ))
    return Signature(params)


def create_app(service: WarService | None = None, start_service: bool = True) -> Any:
    """构建 FastAPI 应用。`service` 传入时复用（便于测试与共享缓存）。"""
    if not FASTAPI_AVAILABLE:  # pragma: no cover
        raise RuntimeError(
            "未安装 FastAPI。请先运行 `python scripts/vendor_deps.py`，"
            f"然后设置 PYTHONPATH 指向 .deps。原始错误: {IMPORT_ERROR}"
        )

    svc = service or WarService(enable_poller=ENABLE_POLLER)
    if start_service and service is None:
        svc.start()

    handlers = Handlers(svc)
    routes = build_routes(handlers)

    app = FastAPI(
        title="helldiversbot API",
        version=__version__,
        description=DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "war", "description": "战争全局"},
            {"name": "planets", "description": "星球"},
            {"name": "sectors", "description": "星区"},
            {"name": "campaigns", "description": "战役与防御战"},
            {"name": "story", "description": "叙事：重大指令、快讯、新闻、空间站"},
            {"name": "meta", "description": "元信息与调试"},
        ],
    )

    # ---------------------------------------------------------------- 异常
    @app.exception_handler(ApiError)
    async def _api_error(req: FastAPIRequest, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": exc.message, "path": req.url.path},
        )

    @app.exception_handler(FetchError)
    async def _fetch_error(_req: FastAPIRequest, exc: FetchError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": "上游数据源暂不可用", "detail": str(exc)},
        )

    # ---------------------------------------------------------------- 路由
    for route in routes:
        def make(route=route):
            def endpoint(**kwargs: Any) -> Any:
                request = kwargs.pop("request")
                # 从原始 query 重建内部 Request，这样未在签名里声明的参数
                # （例如 pretty=1）也不会丢
                query: dict[str, list[str]] = {}
                for key in request.query_params:
                    if key not in query:
                        query[key] = request.query_params.getlist(key)
                internal = Request(method=route.method, path=request.url.path,
                                   query=query, body=b"")
                # 只把**路径参数**传下去：查询参数是 Handler 从 internal 里读的，
                # 签名里声明它们只是为了 Swagger UI 能渲染出输入框。
                path_kwargs = {k: v for k, v in kwargs.items() if k in route.path_params}
                result = route.handler(internal, **path_kwargs)
                status, payload = result if isinstance(result, tuple) else (200, result)
                resp = _json_response(payload, internal.flag("pretty"))
                resp.headers["Access-Control-Allow-Origin"] = "*"
                resp.headers["Cache-Control"] = "no-store"
                if status != 200:
                    resp.status_code = status
                return resp

            endpoint.__signature__ = _build_signature(route)  # type: ignore[attr-defined]
            endpoint.__name__ = f"ep_{route.path.strip('/').replace('/', '_').replace('{', '').replace('}', '') or 'root'}"
            return endpoint

        app.add_api_route(
            route.path,
            make(),
            methods=[route.method],
            summary=route.summary,
            description=route.description,
            tags=list(route.tags),
            name=route.summary,
            operation_id=f"{route.method.lower()}_{route.path.strip('/').replace('/', '_') or 'root'}",
        )

    # 标准库版的中文速查页，在 FastAPI 里改挂到 /guide（/docs 归 Swagger）
    @app.get("/guide", include_in_schema=False, response_class=HTMLResponse)
    def guide() -> HTMLResponse:
        return HTMLResponse(DOCS_HTML)

    return app


def serve(service: WarService | None = None, host: str | None = None,
          port: int | None = None) -> None:
    """用 uvicorn 启动。"""
    if not FASTAPI_AVAILABLE:  # pragma: no cover
        raise RuntimeError(
            "未安装 FastAPI。请先运行 `python scripts/vendor_deps.py`。"
            f"原始错误: {IMPORT_ERROR}"
        )
    import uvicorn

    svc = service or WarService(enable_poller=ENABLE_POLLER)
    svc.start()
    app = create_app(svc, start_service=False)

    bind_host = HOST if host is None else host
    bind_port = PORT if port is None else port
    print(f"helldiversbot API (FastAPI) 已启动 -> http://{bind_host}:{bind_port}")
    print(f"  Swagger UI : http://{bind_host}:{bind_port}/docs")
    print(f"  ReDoc      : http://{bind_host}:{bind_port}/redoc")
    print(f"  OpenAPI    : http://{bind_host}:{bind_port}/openapi.json")
    try:
        uvicorn.run(app, host=bind_host, port=bind_port, log_level="warning")
    finally:
        svc.stop()


__all__ = ["create_app", "serve", "FASTAPI_AVAILABLE", "IMPORT_ERROR"]
