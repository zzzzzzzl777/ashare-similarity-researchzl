from __future__ import annotations

import argparse
import json
from types import SimpleNamespace
from typing import Any


class _ParserStub:
    def __init__(self, args: SimpleNamespace) -> None:
        self._args = args

    def parse_args(self) -> SimpleNamespace:
        return self._args

    def error(self, message: str) -> None:
        raise AssertionError(message)


class _RecordingLoopService:
    def __init__(self, summary: dict[str, Any]) -> None:
        self.summary = summary
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def run_backfill_loop(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((args, kwargs))
        return self.summary


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


def test_cli_parser_exposes_backfill_loop_subcommand(load_public_attr):
    build_parser = load_public_attr("ashare_similarity.cli", "_build_parser")
    parser = build_parser()

    subparser_actions = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]
    assert subparser_actions, "CLI should continue using argparse subcommands."

    choices = subparser_actions[0].choices
    assert "backfill-loop" in choices, (
        "CLI should expose a `backfill-loop` subcommand for automated multi-round cache expansion."
    )


def test_cli_backfill_loop_delegates_to_runtime_and_prints_summary(
    monkeypatch,
    capsys,
    load_module_or_fail,
):
    cli_module = load_module_or_fail("ashare_similarity.cli")
    summary = {
        "frequency": "daily",
        "rounds_completed": 2,
        "stop_reason": "completed",
        "retry_failures_every": 2,
        "latest_status": {"run_id": "run-001", "resume_cursor": 40},
        "rounds": [
            {"round": 1, "retry_failures": False, "resume_cursor_after": 20},
            {"round": 2, "retry_failures": True, "resume_cursor_after": 40},
        ],
    }
    recording_service = _RecordingLoopService(summary)
    runtime = SimpleNamespace(data_service=recording_service)

    parser_args = SimpleNamespace(
        command="backfill-loop",
        frequency="daily",
        batch_size=10,
        max_symbols_per_round=25,
        max_rounds=4,
        round_interval_seconds=0.0,
        retry_failures_every=2,
        stop_after_idle_rounds=1,
        start_date="2024-01-01",
        end_date="2024-01-31",
        symbols=None,
        resume=True,
    )

    monkeypatch.setattr(cli_module, "get_runtime", lambda: runtime)
    monkeypatch.setattr(cli_module, "_build_parser", lambda: _ParserStub(parser_args))

    cli_module.main()

    captured = capsys.readouterr().out.strip()
    assert recording_service.calls, "Backfill loop CLI should delegate to the runtime data service."

    payload = json.loads(captured)
    assert payload["rounds_completed"] == 2
    assert payload["stop_reason"] == "completed"
    assert payload["latest_status"]["run_id"] == "run-001"
    assert payload["rounds"][1]["retry_failures"] is True

    call = recording_service.calls[0]
    assert _extract_scalar(call, ("max_rounds",)) == 4
    assert _extract_scalar(call, ("max_symbols_per_round",)) == 25
    assert _extract_scalar(call, ("retry_failures_every",)) == 2
