from __future__ import annotations

from datetime import date
from typing import Any

from ashare_similarity.schemas import SearchResponse


def _select_default_symbol(runtime: Any | None) -> str:
    preferred_symbols = ("000333", "600036", "600900", "601166", "300750", "002594")
    if runtime is None:
        return "000333"
    store = getattr(runtime, "store", None)
    list_cached_symbols = getattr(store, "list_cached_symbols", None)
    if not callable(list_cached_symbols):
        return "000333"
    try:
        cached_symbols = list_cached_symbols("daily")
    except Exception:
        return "000333"
    if not cached_symbols:
        return "000333"
    for symbol in preferred_symbols:
        if symbol in cached_symbols:
            return symbol
    return str(cached_symbols[0])


def _select_default_end_date(runtime: Any | None, symbol: str) -> str:
    fallback = date.today().isoformat()
    if runtime is None:
        return fallback
    store = getattr(runtime, "store", None)
    load_bars = getattr(store, "load_bars", None)
    if not callable(load_bars):
        return fallback
    try:
        bars = load_bars(symbol, "daily")
    except Exception:
        return fallback
    if getattr(bars, "empty", True) or "date" not in getattr(bars, "columns", []):
        return fallback
    latest = bars["date"].max()
    if hasattr(latest, "date"):
        return latest.date().isoformat()
    return str(latest)[:10]


def build_initial_view_model(runtime: Any | None = None) -> dict[str, Any]:
    default_symbol = _select_default_symbol(runtime)
    return {
        "defaults": {
            "symbol": default_symbol,
            "end_date": _select_default_end_date(runtime, default_symbol),
            "frequency": "daily",
            "window_size": 10,
            "top_k": 10,
            "search_scope": "historical",
        },
        "response_json": None,
    }


def build_response_view_model(response: SearchResponse) -> dict[str, Any]:
    return {
        "response_json": response.model_dump(mode="json"),
        "warnings": response.warnings,
        "notice": response.data_freshness.notice,
    }
