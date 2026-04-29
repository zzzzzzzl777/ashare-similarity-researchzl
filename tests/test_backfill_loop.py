from __future__ import annotations

import argparse
import json
from datetime import date
from types import SimpleNamespace
from typing import Any

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


class _RecordingBackfillLoopService:
    def __init__(self, summary: dict[str, Any]) -> None:
        self.summary = summary
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def _record(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((args, kwargs))
        return self.summary

    def run_backfill_loop(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record(*args, **kwargs)

    def backfill_loop(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record(*args, **kwargs)

    def loop_backfill(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record(*args, **kwargs)


def _extract_scalar(call: tuple[tuple[Any, ...], dict[str, Any]], candidate_names: tuple[str, ...]) -> Any:
    args, kwargs = call
    for name in candidate_names:
        if name in kwargs:
            return kwargs[name]
    if args:
        first = args[0]
        for name in candidate_names:
            if hasattr(first, name):
                return getattr(first, name)
        if isinstance(first, dict):
            for name in candidate_names:
                if name in first:
                    return first[name]
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


def _build_loop_service(
    *,
    app_config,
    load_public_attr,
    stub_factory,
    symbols: list[str],
    failing_symbols: set[str] | None = None,
):
    store_cls = load_public_attr("ashare_similarity.data.storage", "LocalDataStore")
    data_service_cls = load_public_attr("ashare_similarity.data.service", "DataService")
    store = store_cls(app_config)
    failing_symbols = failing_symbols or set()

    universe = pd.DataFrame(
        {
            "symbol": symbols,
            "name": [f"Synthetic-{symbol}" for symbol in symbols],
            "is_st": [False] * len(symbols),
        }
    )

    def fetch_price_history(symbol: str, *args: Any, **kwargs: Any) -> pd.DataFrame:
        if symbol in failing_symbols:
            raise RuntimeError(f"{symbol} timeout")
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
    return data_service_cls(app_config, store, provider, universe_service, context_service)


def test_cli_parser_exposes_automated_backfill_subcommand(load_public_attr):
    build_parser = load_public_attr("ashare_similarity.cli", "_build_parser")
    parser = build_parser()

    subparser_actions = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]
    if not subparser_actions:
        pytest.fail("CLI baseline expects argparse subcommands so looped automation commands can be added safely.")

    choices = tuple(subparser_actions[0].choices)
    automated_loop_commands = [name for name in choices if "backfill" in name and "loop" in name]

    assert automated_loop_commands, (
        "CLI should expose an automated backfill loop subcommand, such as `backfill-loop`, "
        "for repeated resumable cache expansion."
    )


def test_cli_backfill_loop_command_delegates_to_runtime_and_prints_summary(
    monkeypatch,
    capsys,
    load_module_or_fail,
):
    cli_module = load_module_or_fail("ashare_similarity.cli")
    summary = {
        "frequency": "daily",
        "rounds_completed": 2,
        "stop_reason": "completed",
        "latest_status": {"run_id": "run-loop-001", "resume_cursor": 4, "status": "completed"},
        "rounds": [
            {"round": 1, "retry_failures": False, "symbols_scheduled": 2},
            {"round": 2, "retry_failures": True, "symbols_scheduled": 1},
        ],
    }
    recording_service = _RecordingBackfillLoopService(summary)
    runtime = SimpleNamespace(data_service=recording_service)

    parser_args = SimpleNamespace(
        command="backfill-loop",
        frequency="daily",
        batch_size=2,
        max_symbols_per_round=3,
        max_rounds=4,
        round_interval_seconds=1.5,
        retry_failures_every=2,
        stop_after_idle_rounds=1,
        start_date="2024-01-01",
        end_date="2024-01-31",
        symbols=["000001", "000002"],
        resume=False,
    )

    monkeypatch.setattr(cli_module, "get_runtime", lambda: runtime)
    monkeypatch.setattr(cli_module, "_build_parser", lambda: _ParserStub(parser_args))

    cli_module.main()

    captured = capsys.readouterr().out.strip()
    assert recording_service.calls, "Automated backfill CLI should delegate to a runtime loop/backfill service."

    payload = json.loads(captured)
    assert payload["rounds_completed"] == 2
    assert payload["stop_reason"] == "completed"
    assert payload["latest_status"]["run_id"] == "run-loop-001"

    call = recording_service.calls[0]
    assert _extract_scalar(call, ("max_rounds",)) == 4
    assert _extract_scalar(call, ("batch_size",)) == 2
    assert _extract_scalar(call, ("max_symbols_per_round",)) == 3
    assert _extract_scalar(call, ("round_interval_seconds",)) == 1.5
    assert _extract_scalar(call, ("retry_failures_every",)) == 2
    assert _extract_scalar(call, ("stop_after_idle_rounds",)) == 1
    assert _extract_scalar(call, ("resume",)) is False


def test_backfill_loop_runs_multiple_rounds_until_completed(
    app_config,
    load_public_attr,
    stub_factory,
):
    service = _build_loop_service(
        app_config=app_config,
        load_public_attr=load_public_attr,
        stub_factory=stub_factory,
        symbols=["000001", "000002", "000003"],
    )
    sleep_calls: list[float] = []

    summary = service.run_backfill_loop(
        frequency="daily",
        batch_size=1,
        max_symbols_per_round=1,
        max_rounds=5,
        round_interval_seconds=0.25,
        retry_failures_every=0,
        stop_after_idle_rounds=2,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        sleep_fn=sleep_calls.append,
    )

    assert summary["stop_reason"] == "completed"
    assert summary["rounds_completed"] == 3, "Loop should keep invoking resumable backfill rounds until all symbols are processed."

    latest_status = summary["latest_status"]
    assert latest_status is not None
    assert latest_status["status"] == "completed"
    assert latest_status["completed_symbols"] == 3

    rounds = summary["rounds"]
    assert len(rounds) == 3
    assert rounds[0]["symbols_scheduled"] == 1
    assert any(round_data["continued_run"] for round_data in rounds[1:]), (
        "Later rounds should continue the same persisted backfill run rather than starting over."
    )
    assert sleep_calls == [0.25, 0.25], "The loop should wait between unfinished rounds, but not after the terminal round."


def test_backfill_marks_already_cached_symbols_complete_without_refetching_full_universe(
    app_config,
    load_public_attr,
    stub_factory,
):
    service = _build_loop_service(
        app_config=app_config,
        load_public_attr=load_public_attr,
        stub_factory=stub_factory,
        symbols=["000001", "000002", "000003"],
    )
    service.refresh_market_data(frequency="daily", symbols=["000001"])

    summary = service.backfill_market_data(
        frequency="daily",
        batch_size=10,
        resume=False,
    )

    assert summary["cached_symbols_before"] == 1
    assert summary["cached_symbols_after"] == 3
    assert summary["already_cached_symbols"] == 1
    assert summary["symbols_scheduled_this_invocation"] == 2
    assert summary["new_completed_symbols"] == 2
    assert summary["latest_status"]["completed_symbols"] == 3
    assert summary["latest_status"]["status"] == "completed"


def test_backfill_does_not_skip_explicitly_requested_cached_symbol(
    app_config,
    load_public_attr,
    stub_factory,
):
    service = _build_loop_service(
        app_config=app_config,
        load_public_attr=load_public_attr,
        stub_factory=stub_factory,
        symbols=["000001"],
    )
    service.refresh_market_data(frequency="daily", symbols=["000001"])

    summary = service.backfill_market_data(
        frequency="daily",
        batch_size=10,
        symbols=["000001"],
        resume=False,
    )

    assert summary["already_cached_symbols"] == 0
    assert summary["symbols_scheduled_this_invocation"] == 1
    assert summary["new_completed_symbols"] == 1
    assert summary["latest_status"]["completed_symbols"] == 1


def test_backfill_loop_retries_failed_symbols_on_configured_cadence_and_stops_when_idle(
    app_config,
    load_public_attr,
    stub_factory,
):
    service = _build_loop_service(
        app_config=app_config,
        load_public_attr=load_public_attr,
        stub_factory=stub_factory,
        symbols=["000001"],
        failing_symbols={"000001"},
    )
    sleep_calls: list[float] = []

    summary = service.run_backfill_loop(
        frequency="daily",
        batch_size=1,
        max_symbols_per_round=1,
        max_rounds=4,
        round_interval_seconds=0.5,
        retry_failures_every=2,
        stop_after_idle_rounds=1,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        sleep_fn=sleep_calls.append,
    )

    assert summary["rounds_completed"] == 2
    assert summary["stop_reason"] == "idle_round_limit_reached"

    rounds = summary["rounds"]
    assert [rounds[0]["retry_failures"], rounds[1]["retry_failures"]] == [False, True], (
        "Loop automation should only retry historical failures on the configured cadence, not every round."
    )
    assert rounds[0]["symbols_scheduled"] == 1
    assert rounds[1]["symbols_scheduled"] == 1

    latest_status = summary["latest_status"]
    assert latest_status is not None
    assert latest_status["status"] != "completed"
    assert latest_status["failed_symbols"] >= 1
    assert sleep_calls == [0.5], "The loop should not sleep again after an idle-stop condition is reached."


def test_backfill_loop_waits_for_future_retry_round_instead_of_stopping_early(
    app_config,
    load_public_attr,
    stub_factory,
):
    service = _build_loop_service(
        app_config=app_config,
        load_public_attr=load_public_attr,
        stub_factory=stub_factory,
        symbols=["000001"],
        failing_symbols={"000001"},
    )
    sleep_calls: list[float] = []

    summary = service.run_backfill_loop(
        frequency="daily",
        batch_size=1,
        max_symbols_per_round=1,
        max_rounds=4,
        round_interval_seconds=0.5,
        retry_failures_every=3,
        stop_after_idle_rounds=1,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        sleep_fn=sleep_calls.append,
    )

    assert summary["rounds_completed"] == 3
    assert summary["stop_reason"] == "idle_round_limit_reached"

    rounds = summary["rounds"]
    assert [rounds[0]["retry_failures"], rounds[1]["retry_failures"], rounds[2]["retry_failures"]] == [False, False, True]
    assert rounds[1]["symbols_scheduled"] == 0
    assert rounds[1]["awaiting_retry_window"] is True
    assert rounds[2]["symbols_scheduled"] == 1
    assert rounds[2]["awaiting_retry_window"] is False
    assert sleep_calls == [0.5, 0.5], "The loop should keep sleeping through retry-wait rounds until the next retry slot."
