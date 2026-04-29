from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import json
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from ashare_similarity.data.base import SecurityProfile


_WRITE_HOOK_NAMES = (
    "save_backfill_progress",
    "record_backfill_progress",
    "upsert_backfill_progress",
    "update_backfill_progress",
    "save_backfill_status",
    "backfill",
    "run_backfill",
    "backfill_market_data",
)

_STATUS_HOOK_NAMES = (
    "get_backfill_status",
    "load_backfill_status",
    "load_backfill_progress",
    "get_backfill_progress",
    "backfill_status",
    "status",
)


def _find_first_callable(target: Any, names: tuple[str, ...]) -> Any:
    for name in names:
        candidate = getattr(target, name, None)
        if callable(candidate):
            return candidate
    return None


def _to_python(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _to_python(value.model_dump(mode="python"))
    if is_dataclass(value):
        return _to_python(asdict(value))
    if isinstance(value, Mapping):
        return {key: _to_python(item) for key, item in value.items()}
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, (list, tuple, set)):
        return [_to_python(item) for item in value]
    if hasattr(value, "__dict__"):
        return {
            key: _to_python(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _flatten_keys(value: Any) -> set[str]:
    payload = _to_python(value)
    keys: set[str] = set()
    if isinstance(payload, Mapping):
        for key, item in payload.items():
            keys.add(str(key))
            keys.update(_flatten_keys(item))
    elif isinstance(payload, list):
        for item in payload:
            keys.update(_flatten_keys(item))
    return keys


def _flatten_values(value: Any) -> list[Any]:
    payload = _to_python(value)
    if isinstance(payload, Mapping):
        flattened: list[Any] = []
        for item in payload.values():
            flattened.extend(_flatten_values(item))
        return flattened
    if isinstance(payload, list):
        flattened = []
        for item in payload:
            flattened.extend(_flatten_values(item))
        return flattened
    return [payload]


def _find_nested_value(value: Any, candidate_keys: tuple[str, ...]) -> Any:
    payload = _to_python(value)
    if isinstance(payload, Mapping):
        for key in candidate_keys:
            if key in payload:
                return payload[key]
        for item in payload.values():
            found = _find_nested_value(item, candidate_keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_nested_value(item, candidate_keys)
            if found is not None:
                return found
    return None


def _make_daily_frame(symbol: str) -> pd.DataFrame:
    dates = pd.bdate_range(start="2024-01-02", periods=5)
    return pd.DataFrame(
        {
            "symbol": [symbol] * len(dates),
            "date": dates,
            "open": [10.0, 10.2, 10.4, 10.3, 10.6],
            "high": [10.3, 10.5, 10.7, 10.6, 10.9],
            "low": [9.9, 10.0, 10.2, 10.1, 10.4],
            "close": [10.2, 10.4, 10.3, 10.6, 10.8],
            "volume": [1_000_000, 1_010_000, 1_020_000, 1_030_000, 1_040_000],
            "turnover": [10_200_000, 10_504_000, 10_506_000, 10_918_000, 11_232_000],
        }
    )


def _build_progress_target(app_config, load_public_attr, stub_factory):
    store_cls = load_public_attr("ashare_similarity.data.storage", "LocalDataStore")
    store = store_cls(app_config)

    if _find_first_callable(store, _WRITE_HOOK_NAMES) and _find_first_callable(store, _STATUS_HOOK_NAMES):
        return store, lambda: store_cls(app_config)

    data_service_cls = load_public_attr("ashare_similarity.data.service", "DataService")

    universe = pd.DataFrame(
        {
            "symbol": ["000001", "000002", "000003"],
            "name": ["PingAn", "Timeout", "Midea"],
            "is_st": [False, False, False],
        }
    )

    def fetch_price_history(symbol: str, *args: Any, **kwargs: Any) -> pd.DataFrame:
        if symbol == "000002":
            raise RuntimeError("timeout")
        return _make_daily_frame(symbol)

    provider = stub_factory(
        handlers={
            "fetch_price_history": fetch_price_history,
            "get_frequency_notice": lambda frequency: None,
        }
    )
    universe_service = stub_factory(
        handlers={
            "get_filtered_universe": lambda: universe.copy(),
            "get_universe": lambda: universe.copy(),
            "get_listing_days": lambda symbol, as_of=None: 365,
            "get_profile": lambda symbol: SecurityProfile(
                symbol=symbol,
                name=f"Synthetic-{symbol}",
                industry="finance",
                listing_date=date(2020, 1, 1),
                is_st=False,
            ),
        }
    )
    context_service = stub_factory(
        handlers={
            "refresh_market_context": lambda *args, **kwargs: pd.DataFrame(),
            "build_industry_context": lambda *args, **kwargs: pd.DataFrame(),
        }
    )

    service = data_service_cls(app_config, store, provider, universe_service, context_service)

    if _find_first_callable(service, _WRITE_HOOK_NAMES) and _find_first_callable(service, _STATUS_HOOK_NAMES):
        def _rebuild() -> Any:
            next_store = store_cls(app_config)
            return data_service_cls(app_config, next_store, provider, universe_service, context_service)

        return service, _rebuild

    pytest.fail(
        "Backfill baseline needs either store-level or data-service-level hooks for resumable progress/status. "
        "Expected a write hook like `save_backfill_progress(...)` or `backfill(...)`, plus a read hook like "
        "`get_backfill_status(...)`."
    )


def test_backfill_progress_persists_failed_symbols_and_resume_cursor(
    app_config,
    load_public_attr,
    stub_factory,
    invoke_with_supported_kwargs,
):
    target, rebuild_target = _build_progress_target(app_config, load_public_attr, stub_factory)
    write_hook = _find_first_callable(target, _WRITE_HOOK_NAMES)
    status_hook = _find_first_callable(target, _STATUS_HOOK_NAMES)

    assert callable(write_hook), "Backfill contract needs a callable write/backfill hook."
    assert callable(status_hook), "Backfill contract needs a callable status/read hook."

    started_at = datetime(2026, 4, 23, 9, 30, 0)
    first_payload = {
        "task_id": "daily-backfill",
        "frequency": "daily",
        "status": "running",
        "symbols": ["000001", "000002", "000003"],
        "requested_symbols": 3,
        "processed_count": 1,
        "processed_symbols": ["000001"],
        "failed_count": 1,
        "failed_symbols": [{"symbol": "000002", "error": "timeout"}],
        "batch_size": 2,
        "cursor": 1,
        "next_cursor": 1,
        "resume_cursor": 1,
        "resume": False,
        "max_symbols": 2,
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 1, 31),
        "started_at": started_at,
        "updated_at": started_at,
    }
    second_payload = {
        **first_payload,
        "status": "completed",
        "processed_count": 2,
        "processed_symbols": ["000001", "000003"],
        "resume": True,
        "max_symbols": 1,
        "cursor": 2,
        "next_cursor": 2,
        "resume_cursor": 2,
        "completed": True,
        "updated_at": datetime(2026, 4, 23, 9, 35, 0),
    }

    first_result = invoke_with_supported_kwargs(
        write_hook,
        **first_payload,
        request=SimpleNamespace(**first_payload),
        payload=first_payload,
        progress=first_payload,
    )
    second_result = invoke_with_supported_kwargs(
        write_hook,
        **second_payload,
        request=SimpleNamespace(**second_payload),
        payload=second_payload,
        progress=second_payload,
    )

    rehydrated_target = rebuild_target()
    rehydrated_status_hook = _find_first_callable(rehydrated_target, _STATUS_HOOK_NAMES)
    assert callable(rehydrated_status_hook), "Backfill status must be readable after recreating the store/service."

    status = invoke_with_supported_kwargs(
        rehydrated_status_hook,
        frequency="daily",
        task_id="daily-backfill",
        request=SimpleNamespace(frequency="daily", task_id="daily-backfill"),
        payload={"frequency": "daily", "task_id": "daily-backfill"},
    )

    keys = _flatten_keys(status)
    values = {str(item) for item in _flatten_values(status)}

    resumability_markers = {"cursor", "next_cursor", "resume_cursor", "run_id", "remaining_symbols", "last_symbol"}
    assert resumability_markers & keys, (
        "Persisted backfill status should surface enough progress metadata to resume the next invocation."
    )
    assert {"failed_symbols", "sample_failures", "failures", "failed"} & keys, (
        "Persisted backfill status should retain failed-symbol details for operator review."
    )
    assert "000002" in values, "The failed symbol should still be present after recreating the store/service."
    assert "timeout" in values, "Failure diagnostics should persist with the backfill status."

    processed_count = _find_nested_value(
        status,
        ("processed_count", "symbols_processed", "processed_symbols_count", "completed_count", "completed_symbols"),
    )
    if isinstance(processed_count, int):
        assert processed_count >= 2, "Status should reflect progress from the resumed batch, not only the first batch."
    else:
        processed_symbols = _find_nested_value(status, ("processed_symbols", "completed_symbols"))
        assert processed_symbols is not None, "Status should expose either a processed count or a processed symbol list."
        processed_values = {str(item) for item in _flatten_values(processed_symbols)}
        assert "000003" in processed_values, "Resumed progress should include symbols handled after the first batch."

    first_result_run_id = _find_nested_value(first_result, ("run_id",))
    second_result_run_id = _find_nested_value(second_result, ("run_id",))
    if first_result_run_id is not None and second_result_run_id is not None:
        assert first_result_run_id == second_result_run_id, (
            "A resumed backfill invocation should continue the same persisted run instead of silently starting over."
        )


def test_get_backfill_status_downgrades_stale_running_run_to_partial(
    app_config,
    load_public_attr,
    stub_factory,
    monkeypatch,
):
    data_service_cls = load_public_attr("ashare_similarity.data.service", "DataService")
    store_cls = load_public_attr("ashare_similarity.data.storage", "LocalDataStore")
    store = store_cls(app_config)
    app_config.backfill.stale_run_after_minutes = 10

    universe = pd.DataFrame({"symbol": ["000001"], "name": ["PingAn"], "is_st": [False]})
    provider = stub_factory(handlers={"fetch_price_history": lambda *args, **kwargs: _make_daily_frame("000001")})
    universe_service = stub_factory(
        handlers={
            "get_filtered_universe": lambda: universe.copy(),
            "get_universe": lambda: universe.copy(),
            "get_listing_days": lambda symbol, as_of=None: 365,
            "get_profile": lambda symbol: SecurityProfile(
                symbol=symbol,
                name=f"Synthetic-{symbol}",
                industry="finance",
                listing_date=date(2020, 1, 1),
                is_st=False,
            ),
        }
    )
    context_service = stub_factory(
        handlers={
            "refresh_market_context": lambda *args, **kwargs: pd.DataFrame(),
            "build_industry_context": lambda *args, **kwargs: pd.DataFrame(),
        }
    )
    service = data_service_cls(app_config, store, provider, universe_service, context_service)

    run_id = store.create_backfill_run(
        frequency="daily",
        symbols=["000001"],
        batch_size=1,
        start_date=None,
        end_date=None,
        retry_failures=False,
    )
    with store._connect() as connection:  # type: ignore[attr-defined]
        connection.execute(
            "UPDATE backfill_runs SET started_at = ? WHERE run_id = ?",
            [datetime(2026, 4, 24, 9, 0, 0), run_id],
        )

    monkeypatch.setattr(service, "_utcnow", lambda: datetime(2026, 4, 24, 10, 0, 1))

    status = service.get_backfill_status(frequency="daily")

    assert status is not None
    assert status.run_id == run_id
    assert status.status == "partial"


def test_get_backfill_status_marks_dead_snapshot_process_as_partial(
    app_config,
    load_public_attr,
    stub_factory,
    monkeypatch,
):
    data_service_cls = load_public_attr("ashare_similarity.data.service", "DataService")
    store_cls = load_public_attr("ashare_similarity.data.storage", "LocalDataStore")
    store = store_cls(app_config)
    app_config.backfill.stale_run_after_minutes = 30

    universe = pd.DataFrame({"symbol": ["000001"], "name": ["PingAn"], "is_st": [False]})
    provider = stub_factory(handlers={"fetch_price_history": lambda *args, **kwargs: _make_daily_frame("000001")})
    universe_service = stub_factory(
        handlers={
            "get_filtered_universe": lambda: universe.copy(),
            "get_universe": lambda: universe.copy(),
            "get_listing_days": lambda symbol, as_of=None: 365,
            "get_profile": lambda symbol: SecurityProfile(
                symbol=symbol,
                name=f"Synthetic-{symbol}",
                industry="finance",
                listing_date=date(2020, 1, 1),
                is_st=False,
            ),
        }
    )
    context_service = stub_factory(
        handlers={
            "refresh_market_context": lambda *args, **kwargs: pd.DataFrame(),
            "build_industry_context": lambda *args, **kwargs: pd.DataFrame(),
        }
    )
    service = data_service_cls(app_config, store, provider, universe_service, context_service)

    run_id = store.create_backfill_run(
        frequency="daily",
        symbols=["000001"],
        batch_size=1,
        start_date=None,
        end_date=None,
        retry_failures=False,
    )
    with store._connect() as connection:  # type: ignore[attr-defined]
        connection.execute(
            "UPDATE backfill_runs SET started_at = ?, attempted_symbols = ?, completed_symbols = ?, remaining_symbols = ? WHERE run_id = ?",
            [datetime(2026, 4, 24, 9, 50, 0), 0, 0, 1, run_id],
        )

    snapshot_path = app_config.storage.report_dir / "backfill_runtime_daily.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "frequency": "daily",
                "status": "running",
                "batch_size": 1,
                "requested_symbols": 1,
                "attempted_symbols": 0,
                "completed_symbols": 0,
                "failed_symbols": 0,
                "skipped_recent_listing": 0,
                "ignored_st_symbols": 0,
                "remaining_symbols": 1,
                "processed_count": 0,
                "cursor": 0,
                "next_cursor": 0,
                "resume_cursor": 0,
                "started_at": "2026-04-24T09:50:00",
                "finished_at": None,
                "start_date": None,
                "end_date": None,
                "last_symbol": None,
                "retry_failures": False,
                "sample_failures": [],
                "captured_at": "2026-04-24T09:50:05",
                "process_id": 999999,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(service, "_utcnow", lambda: datetime(2026, 4, 24, 9, 55, 0))

    status = service.get_backfill_status(frequency="daily")

    assert status is not None
    assert status.run_id == run_id
    assert status.status == "partial"
