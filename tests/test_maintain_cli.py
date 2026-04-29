from __future__ import annotations

import argparse
import json
from datetime import date
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest

from ashare_similarity.data.base import SecurityProfile


class _ParserStub:
    def __init__(self, args: SimpleNamespace) -> None:
        self._args = args

    def parse_args(self) -> SimpleNamespace:
        return self._args

    def error(self, message: str) -> None:
        raise AssertionError(message)


class _MaintainHarness:
    def __init__(
        self,
        *,
        backfill_summary: dict[str, Any],
        cached_symbols: list[str],
        existing_indexes: set[int],
        build_defaults: tuple[int, ...],
        events: list[tuple[str, Any]],
        cache_latest_data_at: str = "2024-01-31T15:00:00",
        index_entries: dict[int, dict[str, Any]] | None = None,
    ) -> None:
        self.backfill_summary = backfill_summary
        self.cached_symbols = list(cached_symbols)
        self.existing_indexes = set(existing_indexes)
        self.events = events
        self.cache_latest_data_at = cache_latest_data_at
        self.index_entries = dict(index_entries or {})
        self.backfill_calls: list[dict[str, Any]] = []
        self.feature_calls: list[dict[str, Any]] = []
        self.build_calls: list[dict[str, Any]] = []
        self.exists_calls: list[dict[str, Any]] = []
        self.config = SimpleNamespace(
            build_defaults=SimpleNamespace(
                daily_window_sizes=build_defaults,
                minute_window_sizes=(60, 120, 240),
            )
        )

    def run_backfill_loop(self, **kwargs: Any) -> dict[str, Any]:
        self.events.append(("backfill", kwargs.copy()))
        self.backfill_calls.append(kwargs.copy())
        return self.backfill_summary

    def list_cached_symbols(self, frequency: str) -> list[str]:
        self.events.append(("cached_symbols", {"frequency": frequency}))
        return list(self.cached_symbols)

    def exists(self, frequency: str, window_size: int) -> bool:
        payload = {"frequency": frequency, "window_size": window_size}
        self.events.append(("exists", payload))
        self.exists_calls.append(payload)
        return window_size in self.existing_indexes

    def get_system_status(self) -> dict[str, Any]:
        index_status = {}
        for window_size in sorted(self.existing_indexes):
            index_status[f"daily_{window_size}"] = self.index_entries.get(
                window_size,
                {
                    "frequency": "daily",
                    "window_size": window_size,
                    "metadata": {
                        "symbol_count": len(self.cached_symbols),
                        "built_from": {"latest_data_at": self.cache_latest_data_at},
                    },
                },
            )
        return {
            "filtered_universe_count": len(self.cached_symbols),
            "cache_status": {
                "daily": {
                    "cached_symbols": len(self.cached_symbols),
                    "data_freshness": {"latest_data_at": self.cache_latest_data_at},
                }
            },
            "index_status": index_status,
        }

    def build_feature_frame(self, *, frequency: str, window_size: int, symbols: list[str], **kwargs: Any) -> Any:
        payload = {
            "frequency": frequency,
            "window_size": window_size,
            "symbols": list(symbols),
            "extra": kwargs,
        }
        self.events.append(("feature", payload))
        self.feature_calls.append(payload)
        rows = max(len(symbols), 1)
        return SimpleNamespace(matrix=np.ones((rows, 4), dtype=float))

    def build(self, *, feature_frame: Any, frequency: str, window_size: int) -> dict[str, Any]:
        payload = {
            "frequency": frequency,
            "window_size": window_size,
            "rows": int(feature_frame.matrix.shape[0]),
        }
        self.events.append(("build", payload))
        self.build_calls.append(payload)
        return {
            "frequency": frequency,
            "window_size": window_size,
            "symbols_processed": int(feature_frame.matrix.shape[0]),
            "windows_created": int(feature_frame.matrix.shape[0]),
            "index_backend": "synthetic-test",
            "output_paths": {},
        }


def _make_maintain_args(
    *,
    force_rebuild: bool = False,
    skip_rebuild: bool = False,
    window_sizes: list[int] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        command="maintain",
        frequency="daily",
        batch_size=2,
        max_symbols_per_round=3,
        max_rounds=4,
        round_interval_seconds=0.0,
        retry_failures_every=2,
        stop_after_idle_rounds=1,
        start_date="2024-01-01",
        end_date="2024-01-31",
        symbols=["000001", "000002", "000003"],
        resume=True,
        window_sizes=window_sizes,
        skip_rebuild=skip_rebuild,
        force_rebuild=force_rebuild,
    )


def _make_runtime(harness: _MaintainHarness) -> SimpleNamespace:
    return SimpleNamespace(
        config=harness.config,
        data_service=harness,
        store=harness,
        feature_service=harness,
        index_service=harness,
    )


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


def _build_backfill_service(
    *,
    app_config,
    load_public_attr,
    stub_factory,
    symbols: list[str],
    listing_days_by_symbol: dict[str, int] | None = None,
):
    store_cls = load_public_attr("ashare_similarity.data.storage", "LocalDataStore")
    data_service_cls = load_public_attr("ashare_similarity.data.service", "DataService")
    store = store_cls(app_config)

    universe = pd.DataFrame(
        {
            "symbol": symbols,
            "name": [f"Synthetic-{symbol}" for symbol in symbols],
            "is_st": [False] * len(symbols),
        }
    )

    provider = stub_factory(
        handlers={
            "fetch_price_history": lambda symbol, *args, **kwargs: _make_daily_frame(symbol),
            "get_frequency_notice": lambda frequency: None,
        }
    )
    universe_service = stub_factory(
        handlers={
            "get_filtered_universe": lambda: universe.copy(),
            "get_universe": lambda: universe.copy(),
            "get_listing_days": lambda symbol, as_of=None: (listing_days_by_symbol or {}).get(symbol, 365),
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

    return data_service_cls(app_config, store, provider, universe_service, context_service)


def test_cli_parser_exposes_maintain_subcommand(load_public_attr):
    build_parser = load_public_attr("ashare_similarity.cli", "_build_parser")
    parser = build_parser()

    subparser_actions = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]
    assert subparser_actions, "CLI should continue exposing operator workflows through argparse subcommands."

    choices = tuple(subparser_actions[0].choices)
    assert "maintain" in choices, (
        "CLI should expose an end-to-end maintenance command, such as `maintain`, for operator-driven upkeep."
    )


def test_cli_maintain_runs_backfill_then_rebuilds_default_indexes_when_cache_grows(
    monkeypatch,
    capsys,
    load_module_or_fail,
):
    cli_module = load_module_or_fail("ashare_similarity.cli")
    events: list[tuple[str, Any]] = []
    harness = _MaintainHarness(
        backfill_summary={
            "frequency": "daily",
            "new_completed_symbols_total": 2,
            "latest_status": {"run_id": "run-maintain-001", "status": "completed"},
            "rounds": [{"round": 1, "symbols_scheduled": 2}],
        },
        cached_symbols=["000001", "000002", "000003"],
        existing_indexes={5, 8},
        build_defaults=(5, 8),
        events=events,
    )

    monkeypatch.setattr(cli_module, "get_runtime", lambda: _make_runtime(harness))
    monkeypatch.setattr(cli_module, "_build_parser", lambda: _ParserStub(_make_maintain_args()))

    cli_module.main()

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["maintenance_completed"] is True
    assert payload["backfill"]["new_completed_symbols_total"] == 2
    assert payload["rebuild"]["rebuild_triggered"] is True
    assert payload["rebuild"]["reason"] == "new_cached_symbols"
    assert payload["rebuild"]["window_sizes"] == [5, 8]
    assert payload["rebuild"]["target_window_sizes"] == [5, 8]
    assert len(payload["rebuild"]["builds"]) == 2

    assert harness.backfill_calls, "Maintenance should begin by running the automated backfill workflow."
    assert [call["window_size"] for call in harness.build_calls] == [5, 8], (
        "Maintenance should rebuild the default daily indexes when fresh cache was added."
    )
    assert events[0][0] == "backfill", "Maintenance orchestration should backfill before rebuilding indexes."


def test_cli_maintain_rebuilds_when_required_indexes_are_missing_even_without_new_cache(
    monkeypatch,
    capsys,
    load_module_or_fail,
):
    cli_module = load_module_or_fail("ashare_similarity.cli")
    harness = _MaintainHarness(
        backfill_summary={
            "frequency": "daily",
            "new_completed_symbols_total": 0,
            "latest_status": {"run_id": "run-maintain-002", "status": "partial"},
            "rounds": [{"round": 1, "symbols_scheduled": 0}],
        },
        cached_symbols=["000001", "000002"],
        existing_indexes={5},
        build_defaults=(5, 8),
        events=[],
    )

    monkeypatch.setattr(cli_module, "get_runtime", lambda: _make_runtime(harness))
    monkeypatch.setattr(cli_module, "_build_parser", lambda: _ParserStub(_make_maintain_args()))

    cli_module.main()

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["rebuild"]["rebuild_triggered"] is True
    assert payload["rebuild"]["reason"] == "missing_indexes"
    assert payload["rebuild"]["missing_indexes"] == [8]
    assert [call["window_size"] for call in harness.build_calls] == [8], (
        "Maintenance should only rebuild the missing windows when existing indexes are still fresh."
    )


@pytest.mark.parametrize(
    ("force_rebuild", "expected_triggered", "expected_reason"),
    [
        (False, False, "no_cache_change"),
        (True, True, "forced"),
    ],
)
def test_cli_maintain_skips_rebuild_when_nothing_changed_unless_forced(
    force_rebuild: bool,
    expected_triggered: bool,
    expected_reason: str,
    monkeypatch,
    capsys,
    load_module_or_fail,
):
    cli_module = load_module_or_fail("ashare_similarity.cli")
    harness = _MaintainHarness(
        backfill_summary={
            "frequency": "daily",
            "new_completed_symbols_total": 0,
            "latest_status": {"run_id": "run-maintain-003", "status": "partial"},
            "rounds": [{"round": 1, "symbols_scheduled": 0}],
        },
        cached_symbols=["000001", "000002"],
        existing_indexes={5, 8},
        build_defaults=(5, 8),
        events=[],
    )

    monkeypatch.setattr(cli_module, "get_runtime", lambda: _make_runtime(harness))
    monkeypatch.setattr(
        cli_module,
        "_build_parser",
        lambda: _ParserStub(_make_maintain_args(force_rebuild=force_rebuild)),
    )

    cli_module.main()

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["rebuild"]["rebuild_triggered"] is expected_triggered
    assert payload["rebuild"]["reason"] == expected_reason

    if expected_triggered:
        assert harness.build_calls, "Forced maintenance should rebuild indexes even without fresh cache growth."
    else:
        assert not harness.build_calls, "Maintenance should skip rebuild work when nothing changed and force is off."


def test_cli_maintain_rebuilds_stale_indexes_when_cached_symbol_coverage_outgrows_index(
    monkeypatch,
    capsys,
    load_module_or_fail,
):
    cli_module = load_module_or_fail("ashare_similarity.cli")
    harness = _MaintainHarness(
        backfill_summary={
            "frequency": "daily",
            "new_completed_symbols_total": 0,
            "latest_status": {"run_id": "run-maintain-004", "status": "partial"},
            "rounds": [{"round": 1, "symbols_scheduled": 0}],
        },
        cached_symbols=["000001", "000002", "000003"],
        existing_indexes={5, 8},
        build_defaults=(5, 8),
        events=[],
        index_entries={
            5: {
                "frequency": "daily",
                "window_size": 5,
                "metadata": {
                    "symbol_count": 2,
                    "built_from": {"latest_data_at": "2024-01-31T15:00:00"},
                },
            },
            8: {
                "frequency": "daily",
                "window_size": 8,
                "metadata": {
                    "symbol_count": 3,
                    "built_from": {"latest_data_at": "2024-01-31T15:00:00"},
                },
            },
        },
    )

    monkeypatch.setattr(cli_module, "get_runtime", lambda: _make_runtime(harness))
    monkeypatch.setattr(cli_module, "_build_parser", lambda: _ParserStub(_make_maintain_args()))

    cli_module.main()

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["rebuild"]["rebuild_triggered"] is True
    assert payload["rebuild"]["reason"] == "stale_indexes"
    assert payload["rebuild"]["stale_indexes"] == [5]
    assert [call["window_size"] for call in harness.build_calls] == [5]


def test_cli_maintain_rebuilds_stale_indexes_when_cache_has_newer_trading_day(
    monkeypatch,
    capsys,
    load_module_or_fail,
):
    cli_module = load_module_or_fail("ashare_similarity.cli")
    harness = _MaintainHarness(
        backfill_summary={
            "frequency": "daily",
            "new_completed_symbols_total": 0,
            "latest_status": {"run_id": "run-maintain-005", "status": "partial"},
            "rounds": [{"round": 1, "symbols_scheduled": 0}],
        },
        cached_symbols=["000001", "000002"],
        existing_indexes={5, 8},
        build_defaults=(5, 8),
        events=[],
        cache_latest_data_at="2024-02-01T15:00:00",
        index_entries={
            5: {
                "frequency": "daily",
                "window_size": 5,
                "metadata": {
                    "symbol_count": 2,
                    "built_from": {"latest_data_at": "2024-02-01T15:00:00"},
                },
            },
            8: {
                "frequency": "daily",
                "window_size": 8,
                "metadata": {
                    "symbol_count": 2,
                    "built_from": {"latest_data_at": "2024-01-31T15:00:00"},
                },
            },
        },
    )

    monkeypatch.setattr(cli_module, "get_runtime", lambda: _make_runtime(harness))
    monkeypatch.setattr(cli_module, "_build_parser", lambda: _ParserStub(_make_maintain_args()))

    cli_module.main()

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["rebuild"]["rebuild_triggered"] is True
    assert payload["rebuild"]["reason"] == "stale_indexes"
    assert payload["rebuild"]["stale_indexes"] == [8]
    assert [call["window_size"] for call in harness.build_calls] == [8]


def test_resumed_backfill_updates_batch_size_and_reports_effective_scope(
    app_config,
    load_public_attr,
    stub_factory,
):
    service = _build_backfill_service(
        app_config=app_config,
        load_public_attr=load_public_attr,
        stub_factory=stub_factory,
        symbols=["000001", "000002", "000003"],
    )

    first = service.backfill_market_data(
        frequency="daily",
        batch_size=1,
        max_symbols=1,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        resume=False,
    )
    second = service.backfill_market_data(
        frequency="daily",
        batch_size=3,
        max_symbols=10,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        resume=True,
    )

    assert first["completed"] is False
    assert first["batch_size"] == 1
    assert first["symbols_scheduled_this_invocation"] == 1

    assert second["resume_used"] is True
    assert second["run_id"] == first["run_id"], (
        "Resuming a backfill should continue the same persisted run rather than silently starting a new one."
    )
    assert second["batch_size"] == 3, (
        "A resumed run should report the current operator-requested batch size instead of stale values from the first pass."
    )
    assert second["latest_status"]["batch_size"] == 3
    assert second["symbols_scheduled_this_invocation"] == 2, (
        "Backfill summaries should distinguish the configured batch size from the actual remaining symbol count."
    )
    assert second["processed_batches"] == 1
    assert second["latest_status"]["resume_cursor"] == 3


def test_backfill_caches_recent_listing_symbols_instead_of_skipping_them(
    app_config,
    load_public_attr,
    stub_factory,
):
    app_config.quality.min_listing_days = 120
    service = _build_backfill_service(
        app_config=app_config,
        load_public_attr=load_public_attr,
        stub_factory=stub_factory,
        symbols=["000001"],
        listing_days_by_symbol={"000001": 30},
    )

    summary = service.backfill_market_data(
        frequency="daily",
        batch_size=1,
        max_symbols=1,
        resume=False,
    )

    assert summary["completed"] is True
    assert summary["latest_status"]["completed_symbols"] == 1
    assert summary["latest_status"]["skipped_recent_listing"] == 0
    assert service.store.list_cached_symbols("daily") == ["000001"]
