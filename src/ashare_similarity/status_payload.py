from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ashare_similarity.indexing.health import index_entry_is_stale, index_symbol_count, latest_data_at


DEFAULT_INDEX_HEALTH_FREQUENCIES = ("daily", "1", "5", "15", "30", "60")


def _expected_windows(runtime, frequency: str) -> list[int]:
    defaults = getattr(runtime.config, "build_defaults", None)
    if frequency == "daily":
        return list(getattr(defaults, "daily_window_sizes", []) or [])
    return list(getattr(defaults, "minute_window_sizes", []) or [])


def _index_exists(runtime, frequency: str, window_size: int, fallback_existing: bool) -> bool:
    index_service = getattr(runtime, "index_service", None)
    if index_service is not None and hasattr(index_service, "exists"):
        return bool(index_service.exists(frequency, window_size))
    return fallback_existing


def _target_frequencies(frequencies: Sequence[str] | None) -> list[str]:
    selected = frequencies or DEFAULT_INDEX_HEALTH_FREQUENCIES
    return list(dict.fromkeys(str(value) for value in selected))


def attach_index_health(
    runtime,
    payload: dict[str, Any],
    *,
    frequencies: Sequence[str] | None = None,
) -> dict[str, Any]:
    cache_status = payload.get("cache_status") or {}
    index_status = payload.get("index_status") or {}
    cache_mapping = cache_status if isinstance(cache_status, Mapping) else {}
    index_mapping = dict(index_status) if isinstance(index_status, Mapping) else {}
    index_health: dict[str, dict[str, Any]] = {}
    stale_windows_by_frequency: dict[str, set[int]] = {}
    missing_windows_by_frequency: dict[str, set[int]] = {}

    for frequency in _target_frequencies(frequencies):
        expected_windows = _expected_windows(runtime, frequency)
        cache_entry = cache_mapping.get(frequency, {})
        if not isinstance(cache_entry, Mapping):
            cache_entry = {}
        cached_symbols = int(cache_entry.get("cached_symbols", 0) or 0)
        cache_latest_data_at = latest_data_at(cache_entry.get("data_freshness") or {})
        matching_entries = {
            int(value.get("window_size")): value
            for value in index_mapping.values()
            if isinstance(value, Mapping)
            and value.get("frequency") == frequency
            and value.get("window_size") is not None
        }
        built_windows = sorted(matching_entries)
        missing_windows = [
            window_size
            for window_size in expected_windows
            if not _index_exists(runtime, frequency, window_size, window_size in matching_entries)
        ]
        stale_windows = sorted(
            window_size
            for window_size, entry in matching_entries.items()
            if index_entry_is_stale(entry, cached_symbols=cached_symbols, latest_data_at=cache_latest_data_at)
        )
        window_symbol_counts = {
            str(window_size): index_symbol_count(entry)
            for window_size, entry in sorted(matching_entries.items())
        }
        current_index_symbol_count = max((index_symbol_count(entry) for entry in matching_entries.values()), default=0)
        cache_gap = max(cached_symbols - current_index_symbol_count, 0)
        index_health[frequency] = {
            "expected_windows": expected_windows,
            "built_windows": built_windows,
            "missing_windows": missing_windows,
            "stale_windows": stale_windows,
            "cached_symbols": cached_symbols,
            "current_index_symbol_count": current_index_symbol_count,
            "window_symbol_counts": window_symbol_counts,
            "cache_gap": cache_gap,
            "research_ready": bool(cached_symbols) and not missing_windows and not stale_windows,
            "search_ready": bool(cached_symbols)
            and bool(expected_windows or built_windows)
            and not missing_windows
            and not stale_windows,
            "latest_data_at": cache_latest_data_at,
        }
        stale_windows_by_frequency[frequency] = set(stale_windows)
        missing_windows_by_frequency[frequency] = set(missing_windows)

    for key, value in list(index_mapping.items()):
        if not isinstance(value, Mapping):
            continue
        frequency = value.get("frequency")
        window_size = value.get("window_size")
        if frequency is None or window_size is None:
            continue
        entry = dict(value)
        frequency_key = str(frequency)
        window = int(window_size)
        entry["stale"] = window in stale_windows_by_frequency.get(frequency_key, set())
        entry["artifact_missing"] = window in missing_windows_by_frequency.get(frequency_key, set())
        index_mapping[key] = entry

    payload["index_health"] = index_health
    payload["index_status"] = index_mapping
    return payload
