from __future__ import annotations

from typing import Any


def latest_data_at(value: Any) -> Any | None:
    if isinstance(value, dict):
        return value.get("latest_data_at")
    return getattr(value, "latest_data_at", None)


def index_symbol_count(entry: dict[str, Any]) -> int:
    return int((entry.get("metadata") or {}).get("symbol_count") or entry.get("symbol_count") or 0)


def index_built_latest_data_at(entry: dict[str, Any]) -> Any | None:
    return ((entry.get("metadata") or {}).get("built_from") or {}).get("latest_data_at")


def index_built_symbols_count(entry: dict[str, Any]) -> int:
    return int(((entry.get("metadata") or {}).get("built_from") or {}).get("symbols_count") or 0)


def index_entry_is_stale(entry: dict[str, Any], *, cached_symbols: int, latest_data_at: Any | None) -> bool:
    symbol_count = index_symbol_count(entry)
    built_symbols_count = index_built_symbols_count(entry)
    covered_symbols = max(symbol_count, built_symbols_count)
    if cached_symbols and covered_symbols and covered_symbols < cached_symbols:
        return True

    built_latest_data_at = index_built_latest_data_at(entry)
    if built_latest_data_at and latest_data_at:
        return str(built_latest_data_at) < str(latest_data_at)
    return False
