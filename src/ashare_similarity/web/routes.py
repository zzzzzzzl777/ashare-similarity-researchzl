from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from ashare_similarity.doctor import build_acceleration_status
from ashare_similarity.runtime import get_runtime
from ashare_similarity.schemas import PredictionRequest, SearchRequest
from ashare_similarity.search.exporters import render_search_response_csv, render_search_response_html
from ashare_similarity.status_payload import attach_index_health
from ashare_similarity.web.viewmodels import build_initial_view_model

router = APIRouter()
PACKAGE_DIR = Path(__file__).resolve().parents[1]
template_dir = PACKAGE_DIR / "templates"
templates = Jinja2Templates(directory=str(template_dir))


def _static_asset_version() -> str:
    static_dir = PACKAGE_DIR / "static"
    candidates = [
        static_dir / "styles.css",
        static_dir / "app.js",
        static_dir / "vendor" / "echarts.min.js",
    ]
    mtimes = [path.stat().st_mtime_ns for path in candidates if path.exists()]
    return str(max(mtimes)) if mtimes else "dev"


def get_search_service(request: Request | None = None):
    if request is not None and hasattr(request.app.state, "runtime"):
        return request.app.state.runtime.search_service
    return get_runtime().search_service


def _resolve_search_service(request: Request):
    try:
        return get_search_service(request)
    except TypeError:
        return get_search_service()


def _resolve_runtime(request: Request):
    if hasattr(request.app.state, "runtime"):
        return request.app.state.runtime
    return get_runtime()


def _resolve_search_cache(request: Request):
    return getattr(request.app.state, "search_response_cache", None)


def _resolve_prediction_cache(request: Request):
    return getattr(request.app.state, "prediction_response_cache", None)


def _execute_search(service, payload: SearchRequest):
    try:
        return service.search(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _execute_search_async(service, payload: SearchRequest):
    return await run_in_threadpool(_execute_search, service, payload)


async def _get_or_execute_search_response(request: Request, payload: SearchRequest):
    payload = _resolve_search_payload(_resolve_runtime(request), payload)
    cache = _resolve_search_cache(request)
    if cache is not None:
        cached = cache.get(payload)
        if cached is not None:
            return cached

    service = _resolve_search_service(request)
    response = await _execute_search_async(service, payload)
    if cache is not None:
        cache.put(payload, response)
    return response


def _execute_prediction(runtime, payload: PredictionRequest):
    try:
        return runtime.prediction_service.predict(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _get_or_execute_prediction_response(request: Request, payload: PredictionRequest):
    runtime = _resolve_runtime(request)
    payload = _resolve_prediction_payload(runtime, payload)
    cache = _resolve_prediction_cache(request)
    if cache is not None:
        cached = cache.get(payload)
        if cached is not None:
            return cached

    response = await run_in_threadpool(_execute_prediction, runtime, payload)
    if cache is not None:
        cache.put(payload, response)
    return response


def _build_search_request(
    *,
    symbol: str,
    end_date: str,
    frequency: str,
    window_size: int,
    top_k: int,
    search_scope: str = "historical",
) -> SearchRequest:
    return SearchRequest(
        symbol=symbol,
        end_date=end_date,
        frequency=frequency,
        window_size=window_size,
        top_k=top_k,
        search_scope=search_scope,
    )


async def _render_export_response(request: Request, payload: SearchRequest, *, export_format: str):
    runtime = _resolve_runtime(request)
    payload = _resolve_search_payload(runtime, payload)
    response = await _get_or_execute_search_response(request, payload)
    if export_format == "csv":
        csv_bytes = render_search_response_csv(response, forward_windows=runtime.config.ranking.forward_windows)
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="similarity_{payload.symbol}_{payload.frequency}_{payload.window_size}.csv"'
                )
            },
        )
    if export_format == "html":
        return HTMLResponse(render_search_response_html(response))
    raise HTTPException(status_code=500, detail=f"Unsupported export format: {export_format}")


def _to_jsonable_payload(value) -> dict[str, object]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    if isinstance(value, Mapping):
        return dict(value)
    try:
        dumped = dict(value)
    except (TypeError, ValueError):
        return {}
    return dumped


def _status_query_defaults(runtime) -> tuple[str, int]:
    defaults = build_initial_view_model(runtime).get("defaults", {})
    frequency = str(defaults.get("frequency") or "daily")
    try:
        window_size = int(defaults.get("window_size") or 10)
    except (TypeError, ValueError):
        window_size = 10
    return frequency, window_size


def _normalize_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip()
    return raw.zfill(6) if raw.isdigit() else raw


def _resolve_symbol_query(runtime, query: str, *, frequency: str | None = None) -> str:
    raw_query = str(query or "").strip()
    if not raw_query:
        return raw_query

    data_service = getattr(runtime, "data_service", None)
    resolver = getattr(data_service, "resolve_symbol_query", None)
    if callable(resolver):
        resolved = resolver(raw_query, frequency=frequency, prefer_cached=True)
        if isinstance(resolved, Mapping) and resolved.get("symbol"):
            return _normalize_symbol(str(resolved["symbol"]))

    if raw_query.isdigit():
        return _normalize_symbol(raw_query)
    raise HTTPException(
        status_code=400,
        detail=f"无法识别股票代码或名称：{raw_query}。请换成 6 位代码，或输入更完整的股票名称。",
    )


def _resolve_search_payload(runtime, payload: SearchRequest) -> SearchRequest:
    resolved_symbol = _resolve_symbol_query(runtime, payload.symbol, frequency=payload.frequency)
    if resolved_symbol == payload.symbol:
        return payload
    return payload.model_copy(update={"symbol": resolved_symbol})


def _resolve_prediction_payload(runtime, payload: PredictionRequest) -> PredictionRequest:
    resolved_symbol = _resolve_symbol_query(runtime, payload.symbol, frequency=payload.frequency)
    if resolved_symbol == payload.symbol:
        return payload
    return payload.model_copy(update={"symbol": resolved_symbol})


def _cached_symbol_payload(runtime, *, frequency: str, query: str | None = None, limit: int = 12) -> dict[str, object]:
    data_service = getattr(runtime, "data_service", None)
    if data_service is not None and hasattr(data_service, "get_cached_symbol_choices"):
        payload = data_service.get_cached_symbol_choices(
            frequency,
            query=query,
            limit=limit,
        )
        return _to_jsonable_payload(payload)

    store = getattr(runtime, "store", None)
    if store is None or not hasattr(store, "list_cached_symbols"):
        return {
            "frequency": frequency,
            "query": _normalize_symbol(query or ""),
            "total_cached": 0,
            "match_count": 0,
            "exact_match": None,
            "items": [],
        }

    cached_symbols = [str(symbol).strip().zfill(6) for symbol in store.list_cached_symbols(frequency)]
    items = [{"symbol": symbol, "name": None} for symbol in cached_symbols[: max(int(limit), 1)]]
    normalized_query = _normalize_symbol(query or "")
    exact_match = next((item for item in items if item["symbol"] == normalized_query), None)
    return {
        "frequency": frequency,
        "query": normalized_query,
        "total_cached": len(cached_symbols),
        "match_count": len(cached_symbols),
        "exact_match": exact_match,
        "items": items,
    }


def _to_date_value(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def _prepare_symbol_for_query(runtime, payload: SearchRequest) -> dict[str, object]:
    payload = _resolve_search_payload(runtime, payload)
    data_service = getattr(runtime, "data_service", None)
    index_service = getattr(runtime, "index_service", None)
    store = getattr(runtime, "store", None)
    if data_service is None or index_service is None or store is None:
        raise HTTPException(status_code=500, detail="运行时依赖不完整，无法补齐当前标的。")

    symbol = _normalize_symbol(payload.symbol)
    frequency = payload.frequency
    end_date = _to_date_value(payload.end_date)
    cached_before = symbol in set(store.list_cached_symbols(frequency))
    index_ready_before = bool(index_service.exists(frequency, payload.window_size))

    refresh_summary = data_service.refresh_market_data(
        frequency=frequency,
        symbols=[symbol],
        end_date=end_date,
    )
    cached_after_symbols = [str(item).strip().zfill(6) for item in store.list_cached_symbols(frequency)]
    cached_after = symbol in set(cached_after_symbols)

    index_ready_after = bool(index_service.exists(frequency, payload.window_size))
    failed_map = {
        _normalize_symbol(item.get("symbol", "")): item.get("error")
        for item in refresh_summary.get("failed_symbols", [])
        if isinstance(item, Mapping)
    }
    warnings: list[str] = []
    if cached_after and not cached_before and index_ready_before:
        warnings.append("当前标的已经补齐，本次查询可以直接执行；如果希望它也参与其他股票的历史样本库，请稍后重建对应窗口索引。")
    if failed_map.get(symbol):
        warnings.append(f"补齐过程中有错误：{failed_map[symbol]}")
    if symbol in [str(item).strip().zfill(6) for item in refresh_summary.get("ignored_st_symbols", [])]:
        warnings.append("当前标的已被 ST 过滤规则排除。")
    if symbol in [str(item).strip().zfill(6) for item in refresh_summary.get("skipped_recent_listing_symbols", [])]:
        warnings.append("当前标的上市时间较短，暂不纳入可比样本。")

    if cached_after and index_ready_after:
        message = f"标的 {symbol} 已准备完成，现在可以直接检索。"
    elif cached_after:
        message = f"标的 {symbol} 已补齐本地缓存，但当前窗口索引仍不可用。"
    elif failed_map.get(symbol):
        message = f"标的 {symbol} 补齐失败：{failed_map[symbol]}"
    else:
        message = f"标的 {symbol} 还没有准备好，请稍后重试。"

    return {
        "symbol": symbol,
        "name": getattr(data_service, "get_symbol_name", lambda _symbol: None)(symbol),
        "frequency": frequency,
        "cached_before": cached_before,
        "cached_after": cached_after,
        "index_ready": index_ready_after,
        "search_ready": bool(cached_after and index_ready_after),
        "refresh_summary": _to_jsonable_payload(refresh_summary),
        "build_summary": None,
        "warnings": warnings,
        "message": message,
    }


def _build_status_payload(runtime):
    data_service = getattr(runtime, "data_service", None)
    if data_service is not None and hasattr(data_service, "get_system_status"):
        payload = _to_jsonable_payload(data_service.get_system_status())
        frequency, window_size = _status_query_defaults(runtime)
        payload["acceleration"] = build_acceleration_status(
            runtime,
            payload,
            frequency=frequency,
            window_size=window_size,
        )
        return attach_index_health(runtime, payload)

    payload: dict[str, object] = {
        "universe_count": 0,
        "filtered_universe_count": 0,
        "cache_status": {},
        "index_status": {},
        "latest_backfill": None,
    }

    if data_service is not None and hasattr(data_service, "get_status"):
        value = data_service.get_status()
        if isinstance(value, dict):
            payload.update(value)

    if payload.get("latest_backfill") is None and data_service is not None:
        for method_name in ("get_backfill_status", "backfill_status"):
            if hasattr(data_service, method_name):
                payload["latest_backfill"] = getattr(data_service, method_name)()
                break

    if (not payload.get("cache_status")) and data_service is not None:
        if hasattr(data_service, "get_cache_status"):
            payload["cache_status"] = data_service.get_cache_status()
        else:
            store = getattr(runtime, "store", None)
            if store is not None and hasattr(store, "list_cached_symbols"):
                cache_status = {}
                for frequency in ("daily", "1", "5", "15", "30", "60"):
                    freshness = None
                    if hasattr(data_service, "get_data_freshness"):
                        freshness = data_service.get_data_freshness(frequency)
                    cache_status[frequency] = {
                        "frequency": frequency,
                        "cached_symbols": len(store.list_cached_symbols(frequency)),
                        "data_freshness": freshness.model_dump(mode="json") if hasattr(freshness, "model_dump") else freshness,
                    }
                payload["cache_status"] = cache_status

    frequency, window_size = _status_query_defaults(runtime)
    payload["acceleration"] = build_acceleration_status(
        runtime,
        payload,
        frequency=frequency,
        window_size=window_size,
    )
    return attach_index_health(runtime, payload)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    context = build_initial_view_model(_resolve_runtime(request))
    context["static_version"] = _static_asset_version()
    return templates.TemplateResponse(request, "index.html", {"request": request, **context})


@router.get("/api/healthz")
async def api_healthz():
    return {"status": "ok"}


@router.post("/api/search")
async def api_search(payload: SearchRequest, request: Request):
    return await _get_or_execute_search_response(request, payload)


@router.post("/api/predict")
async def api_predict(payload: PredictionRequest, request: Request):
    return await _get_or_execute_prediction_response(request, payload)


@router.get("/api/status")
async def api_status(request: Request):
    runtime = _resolve_runtime(request)
    if not hasattr(runtime, "data_service"):
        raise HTTPException(status_code=500, detail="数据服务不可用")
    return _build_status_payload(runtime)


@router.get("/api/cached-symbols")
async def api_cached_symbols(
    request: Request,
    frequency: str = Query(default="daily"),
    q: str | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
):
    runtime = _resolve_runtime(request)
    return _cached_symbol_payload(runtime, frequency=frequency, query=q, limit=limit)


@router.post("/api/prepare-symbol")
async def api_prepare_symbol(payload: SearchRequest, request: Request):
    runtime = _resolve_runtime(request)
    return _prepare_symbol_for_query(runtime, payload)


@router.get("/api/export/csv")
async def export_csv(
    request: Request,
    symbol: str,
    end_date: str,
    frequency: str = Query(default="daily"),
    window_size: int = Query(default=10, ge=3, le=240),
    top_k: int = Query(default=10, ge=1, le=50),
    search_scope: str = Query(default="historical"),
):
    payload = _build_search_request(
        symbol=symbol,
        end_date=end_date,
        frequency=frequency,
        window_size=window_size,
        top_k=top_k,
        search_scope=search_scope,
    )
    return await _render_export_response(request, payload, export_format="csv")


@router.post("/api/export/csv")
async def export_csv_post(payload: SearchRequest, request: Request):
    return await _render_export_response(request, payload, export_format="csv")


@router.get("/api/export/html", response_class=HTMLResponse)
async def export_html(
    request: Request,
    symbol: str,
    end_date: str,
    frequency: str = Query(default="daily"),
    window_size: int = Query(default=10, ge=3, le=240),
    top_k: int = Query(default=10, ge=1, le=50),
    search_scope: str = Query(default="historical"),
):
    payload = _build_search_request(
        symbol=symbol,
        end_date=end_date,
        frequency=frequency,
        window_size=window_size,
        top_k=top_k,
        search_scope=search_scope,
    )
    return await _render_export_response(request, payload, export_format="html")


@router.post("/api/export/html", response_class=HTMLResponse)
async def export_html_post(payload: SearchRequest, request: Request):
    return await _render_export_response(request, payload, export_format="html")


@router.get("/api/view-model")
async def get_view_model(request: Request):
    service = _resolve_search_service(request)
    if service is None:
        raise HTTPException(status_code=500, detail="搜索服务不可用")
    return build_initial_view_model(_resolve_runtime(request))
