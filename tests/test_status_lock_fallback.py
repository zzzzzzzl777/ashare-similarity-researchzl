from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import polars as pl

from ashare_similarity.data.service import DataService
from ashare_similarity.data.storage import LocalDataStore


def _lock_error(app_config) -> RuntimeError:
    return RuntimeError(
        f'IO Error: Cannot open file "{app_config.storage.db_path}": 另一个程序正在使用此文件，进程无法访问。'
    )


def _write_daily_bars(store: LocalDataStore, symbol: str) -> None:
    path = store.bars_path(symbol, "daily")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        {
            "symbol": [symbol, symbol],
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [10.0, 10.1],
            "high": [10.2, 10.3],
            "low": [9.9, 10.0],
            "close": [10.1, 10.2],
            "volume": [1_000_000, 1_010_000],
            "turnover": [10_100_000, 10_302_000],
        }
    )
    pl.from_pandas(frame).write_parquet(path)


def test_store_list_cached_symbols_falls_back_to_filesystem_when_duckdb_is_locked(app_config, monkeypatch):
    store = LocalDataStore(app_config)
    _write_daily_bars(store, "000001")
    monkeypatch.setattr(store, "_query_registry", lambda *args, **kwargs: (_ for _ in ()).throw(_lock_error(app_config)))

    assert store.list_cached_symbols("daily") == ["000001"]


def test_data_service_system_status_falls_back_to_snapshot_and_filesystem_when_duckdb_is_locked(
    app_config,
    monkeypatch,
    stub_factory,
):
    store = LocalDataStore(app_config)
    _write_daily_bars(store, "000001")

    build_dir = app_config.storage.index_dir / "daily" / "window_10"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "manifest.json").write_text(
        json.dumps(
            {
                "frequency": "daily",
                "window_size": 10,
                "row_count": 123,
                "symbol_count": 1,
                "built_at": "2026-04-24T16:00:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (build_dir / "backend.json").write_text(json.dumps({"backend": "sklearn-nearest"}), encoding="utf-8")

    snapshot_path = app_config.storage.report_dir / "backfill_runtime_daily.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "frequency": "daily",
                "status": "running",
                "batch_size": 64,
                "requested_symbols": 5327,
                "attempted_symbols": 100,
                "completed_symbols": 95,
                "failed_symbols": 5,
                "skipped_recent_listing": 0,
                "ignored_st_symbols": 0,
                "remaining_symbols": 5232,
                "processed_count": 95,
                "cursor": 100,
                "next_cursor": 100,
                "resume_cursor": 100,
                "started_at": "2026-04-24T16:00:00",
                "finished_at": None,
                "start_date": None,
                "end_date": None,
                "last_symbol": "000001",
                "retry_failures": True,
                "sample_failures": [],
                "captured_at": "2026-04-24T16:05:00",
                "cached_symbols": 1,
                "data_freshness": {
                    "data_source": "akshare",
                    "last_refresh_at": "2026-04-24T16:05:00",
                    "latest_data_at": None,
                    "notice": None,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    original_connect = store._connect

    def _locked_connect(*, read_only: bool = False):
        if read_only:
            raise _lock_error(app_config)
        return original_connect(read_only=read_only)

    monkeypatch.setattr(store, "_query_registry", lambda *args, **kwargs: (_ for _ in ()).throw(_lock_error(app_config)))
    monkeypatch.setattr(store, "_connect", _locked_connect)

    universe = pd.DataFrame(
        {
            "symbol": ["000001"],
            "name": ["PingAn"],
            "is_st": [False],
        }
    )
    provider = stub_factory(handlers={"get_frequency_notice": lambda frequency: None})
    universe_service = stub_factory(
        handlers={
            "get_universe": lambda allow_bootstrap=False: universe.copy(),
            "get_filtered_universe": lambda allow_bootstrap=False: universe.copy(),
        }
    )
    context_service = stub_factory()
    service = DataService(app_config, store, provider, universe_service, context_service)

    status = service.get_system_status()

    assert status.cache_status["daily"].cached_symbols == 1
    assert status.latest_backfill is not None
    assert status.latest_backfill.run_id == "run-1"
    assert status.latest_backfill.completed_symbols == 95
    assert "daily_10" in status.index_status
    assert status.index_status["daily_10"]["backend"] == "sklearn-nearest"
