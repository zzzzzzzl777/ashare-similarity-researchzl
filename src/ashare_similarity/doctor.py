from __future__ import annotations

from pathlib import Path
from typing import Any

from ashare_similarity.indexing.health import index_entry_is_stale, latest_data_at
from ashare_similarity.schemas import SearchRequest
from ashare_similarity.status_payload import attach_index_health
from ashare_similarity.web.viewmodels import build_initial_view_model


def _load_runtime_backend_status(runtime, *, frequency: str, window_size: int) -> dict[str, Any]:
    index_service = getattr(runtime, "index_service", None)
    if index_service is None:
        return {}

    searchable = None
    if hasattr(index_service, "get_cached"):
        try:
            searchable = index_service.get_cached(frequency, window_size)
        except Exception as exc:
            return {"runtime_probe_error": str(exc)}

    if searchable is None:
        return {}

    search_index = getattr(searchable, "search_index", searchable)
    if search_index is None:
        return {}

    runtime_metadata = getattr(search_index, "runtime_metadata", None)
    if callable(runtime_metadata):
        data = runtime_metadata()
        if isinstance(data, dict):
            return data

    return {
        "active_backend": getattr(search_index, "backend_name", None),
        "artifact_backend": getattr(search_index, "artifact_backend", getattr(search_index, "backend_name", None)),
        "active_device": getattr(search_index, "device", None),
        "active_device_name": getattr(search_index, "device_name", None),
    }


def build_acceleration_status(runtime, status_payload: dict[str, Any], *, frequency: str, window_size: int) -> dict[str, Any]:
    try:
        from ashare_similarity.indexing import backend as ann_backend
    except Exception:
        ann_backend = None

    index_key = f"{frequency}_{window_size}"
    status_backend = ((status_payload.get("index_status") or {}).get(index_key) or {}).get("backend")
    runtime_backend_status = _load_runtime_backend_status(runtime, frequency=frequency, window_size=window_size)
    environment = (
        ann_backend.get_acceleration_environment()
        if ann_backend is not None and hasattr(ann_backend, "get_acceleration_environment")
        else {}
    )

    active_backend = runtime_backend_status.get("active_backend") or status_backend
    artifact_backend = runtime_backend_status.get("artifact_backend") or status_backend
    active_device = runtime_backend_status.get("active_device")
    active_device_name = runtime_backend_status.get("active_device_name") or environment.get("torch_device_name")
    active_backend_source = "runtime-index" if runtime_backend_status.get("active_backend") else "status-snapshot"
    if (
        not runtime_backend_status.get("active_backend")
        and status_backend == "compact-recall-v1"
        and environment.get("torch_cuda_available")
    ):
        active_backend = "torch-cuda-chunked"
        active_device = "cuda:0"
        active_backend_source = "runtime-projected"
    gpu_enabled = bool(
        (active_device and str(active_device).startswith("cuda"))
        or (active_backend and ("gpu" in str(active_backend) or "cuda" in str(active_backend)))
    )

    return {
        "active_backend": active_backend,
        "artifact_backend": artifact_backend,
        "status_backend": status_backend,
        "active_backend_source": active_backend_source,
        "active_device": active_device or ("cuda:0" if gpu_enabled else "cpu"),
        "active_device_name": active_device_name,
        "gpu_enabled": gpu_enabled,
        "runtime_probe_error": runtime_backend_status.get("runtime_probe_error"),
        **environment,
        **{
            key: value
            for key, value in runtime_backend_status.items()
            if key
            not in {
                "active_backend",
                "artifact_backend",
                "active_device",
                "active_device_name",
                "runtime_probe_error",
            }
        },
    }


def _compact_status(status_payload: dict[str, Any]) -> dict[str, Any]:
    compact_indexes = {}
    for key, value in (status_payload.get("index_status") or {}).items():
        compact_indexes[key] = {
            "frequency": value.get("frequency"),
            "window_size": value.get("window_size"),
            "backend": value.get("backend"),
            "rows_count": value.get("rows_count"),
            "built_at": value.get("built_at"),
            "symbol_count": (value.get("metadata") or {}).get("symbol_count"),
        }

    latest_backfill = status_payload.get("latest_backfill") or None
    compact_backfill = None
    if latest_backfill:
        compact_backfill = {
            "run_id": latest_backfill.get("run_id"),
            "frequency": latest_backfill.get("frequency"),
            "status": latest_backfill.get("status"),
            "completed_symbols": latest_backfill.get("completed_symbols"),
            "requested_symbols": latest_backfill.get("requested_symbols"),
            "remaining_symbols": latest_backfill.get("remaining_symbols"),
            "last_symbol": latest_backfill.get("last_symbol"),
            "sample_failures": latest_backfill.get("sample_failures", [])[:3],
        }

    return {
        "universe_count": status_payload.get("universe_count", 0),
        "filtered_universe_count": status_payload.get("filtered_universe_count", 0),
        "cache_status": status_payload.get("cache_status", {}),
        "index_status": compact_indexes,
        "latest_backfill": compact_backfill,
    }
def build_doctor_report(runtime, request: SearchRequest | None = None) -> dict[str, Any]:
    status = runtime.data_service.get_system_status()
    status_payload = status.model_dump(mode="json") if hasattr(status, "model_dump") else dict(status)

    defaults = build_initial_view_model(runtime)["defaults"]
    query_request = request or SearchRequest(
        symbol=defaults["symbol"],
        end_date=defaults["end_date"],
        frequency=defaults["frequency"],
        window_size=defaults["window_size"],
        top_k=defaults["top_k"],
    )

    expected_windows = (
        list(runtime.config.build_defaults.daily_window_sizes)
        if query_request.frequency == "daily"
        else list(runtime.config.build_defaults.minute_window_sizes)
    )
    status_payload = attach_index_health(runtime, status_payload, frequencies=[query_request.frequency])
    index_status = status_payload.get("index_status", {})
    matching_indexes = [
        value
        for value in index_status.values()
        if value.get("frequency") == query_request.frequency and value.get("window_size") is not None
    ]
    health = (status_payload.get("index_health") or {}).get(query_request.frequency, {})
    existing_windows = sorted(int(window) for window in health.get("built_windows", []) or [])
    missing_windows = sorted(int(window) for window in health.get("missing_windows", []) or [])

    cache_status = status_payload.get("cache_status", {})
    cache_for_frequency = cache_status.get(query_request.frequency, {})
    cached_symbols = int(cache_for_frequency.get("cached_symbols", 0) or 0)
    cache_latest_data_at = latest_data_at(cache_for_frequency.get("data_freshness") or {})
    filtered_universe_count = int(status_payload.get("filtered_universe_count", 0) or 0)
    coverage_ratio = round(cached_symbols / filtered_universe_count, 4) if filtered_universe_count else None
    stale_windows = sorted(int(window) for window in health.get("stale_windows", []) or [])
    index_symbol_counts = {str(key): int(value) for key, value in (health.get("window_symbol_counts") or {}).items()}
    selected_index = next(
        (value for value in matching_indexes if int(value.get("window_size")) == int(query_request.window_size)),
        None,
    )
    selected_index_symbol_count = int(
        ((selected_index or {}).get("metadata") or {}).get("symbol_count")
        or (selected_index or {}).get("symbol_count")
        or 0
    )
    selected_index_missing = int(query_request.window_size) in missing_windows or bool(
        selected_index and selected_index.get("artifact_missing")
    )
    selected_index_stale = bool(
        selected_index
        and (
            selected_index.get("stale")
            or index_entry_is_stale(selected_index, cached_symbols=cached_symbols, latest_data_at=cache_latest_data_at)
        )
    )

    search_smoke: dict[str, Any]
    warnings: list[str] = []
    ready_for_search = False
    try:
        response = runtime.search_service.search(query_request)
        warnings = list(getattr(response, "warnings", []) or [])
        search_smoke = {
            "status": "ok",
            "balanced_matches": len(response.balanced_matches),
            "shape_matches": len(response.shape_matches),
            "universe_size": response.query_meta.universe_size,
            "candidate_pool_size": response.query_meta.candidate_pool_size,
            "data_source": response.data_freshness.data_source,
            "notice": response.data_freshness.notice,
        }
        ready_for_search = bool(response.balanced_matches) and bool(response.shape_matches)
    except Exception as exc:
        search_smoke = {
            "status": "failed",
            "error": str(exc),
        }

    recommendations: list[str] = []
    if int(status_payload.get("universe_count", 0) or 0) == 0:
        recommendations.append("先运行 bootstrap 初始化股票池和基础市场环境。")
    if cached_symbols == 0:
        recommendations.append("当前没有本地缓存，请先运行 maintain 或 backfill-loop。")
    if missing_windows:
        missing_text = ", ".join(str(window) for window in missing_windows)
        recommendations.append(f"当前缺少 {query_request.frequency} 窗口索引或索引工件：{missing_text}。")
    if selected_index_stale:
        recommendations.append(
            f"当前查询窗口索引已陈旧，请先重建该窗口索引。当前有效窗口覆盖 {selected_index_symbol_count}/{cached_symbols} 个已缓存标的。"
        )
    if stale_windows:
        recommendations.append("默认窗口索引仍有 stale 项，请先运行 prepare_daily_ready.ps1 完成全量重建。")
    if not ready_for_search:
        recommendations.append("默认查询烟测未通过，请检查缓存、索引和查询日期是否匹配。")
    if filtered_universe_count and cached_symbols < filtered_universe_count:
        recommendations.append("当前仍是部分缓存，继续运行 maintain/backfill-loop 可以扩大免费数据覆盖。")
    if query_request.frequency != "daily":
        recommendations.append("分钟线仅适合近期窗口检索，默认不作为长期全历史能力。")

    web_state_path = Path.cwd() / "run_logs" / "web_server.json"

    return {
        "overall_ready": bool(int(status_payload.get("universe_count", 0) or 0))
        and ready_for_search
        and bool(filtered_universe_count)
        and bool(cached_symbols)
        and not missing_windows
        and not stale_windows
        and not selected_index_missing
        and not selected_index_stale,
        "storage": {
            "root_dir": str(runtime.config.storage.root_dir),
            "db_path": str(runtime.config.storage.db_path),
            "db_exists": runtime.config.storage.db_path.exists(),
            "web_state_path": str(web_state_path.resolve()),
            "web_state_exists": web_state_path.exists(),
        },
        "query": query_request.model_dump(mode="json"),
        "coverage": {
            "frequency": query_request.frequency,
            "cached_symbols": cached_symbols,
            "filtered_universe_count": filtered_universe_count,
            "coverage_ratio": coverage_ratio,
        },
        "indexes": {
            "frequency": query_request.frequency,
            "expected_windows": expected_windows,
            "existing_windows": existing_windows,
            "missing_windows": missing_windows,
            "stale_windows": stale_windows,
            "search_ready": bool(health.get("search_ready")),
            "selected_window_symbol_count": selected_index_symbol_count,
            "selected_window_artifact_missing": selected_index_missing,
            "window_symbol_counts": index_symbol_counts,
        },
        "search_smoke": search_smoke,
        "acceleration": build_acceleration_status(
            runtime,
            status_payload,
            frequency=query_request.frequency,
            window_size=query_request.window_size,
        ),
        "status": _compact_status(status_payload),
        "warnings": warnings,
        "recommendations": recommendations,
    }


_acceleration_status = build_acceleration_status
