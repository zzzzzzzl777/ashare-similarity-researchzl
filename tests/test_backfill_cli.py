from __future__ import annotations

import argparse
import json
from types import SimpleNamespace
from typing import Any

import pytest


class _ParserStub:
    def __init__(self, args: SimpleNamespace) -> None:
        self._args = args

    def parse_args(self) -> SimpleNamespace:
        return self._args

    def error(self, message: str) -> None:
        raise AssertionError(message)


class _RecordingBackfillService:
    def __init__(self, summary: dict[str, Any]) -> None:
        self.summary = summary
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def _record(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((args, kwargs))
        return self.summary

    def backfill(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record(*args, **kwargs)

    def run_backfill(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._record(*args, **kwargs)

    def backfill_market_data(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
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


def test_cli_parser_exposes_backfill_subcommand(load_public_attr):
    build_parser = load_public_attr("ashare_similarity.cli", "_build_parser")
    parser = build_parser()

    subparser_actions = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]
    if not subparser_actions:
        pytest.fail("CLI baseline expects argparse subcommands so new workflow commands can be added safely.")

    choices = subparser_actions[0].choices
    assert "backfill" in choices, (
        "CLI should expose a `backfill` subcommand for resumable cache population, alongside "
        "`bootstrap`, `build`, and `search`."
    )


def test_cli_backfill_command_delegates_to_runtime_and_prints_summary(
    monkeypatch,
    capsys,
    load_module_or_fail,
):
    cli_module = load_module_or_fail("ashare_similarity.cli")
    summary = {
        "frequency": "daily",
        "batch_size": 2,
        "requested_symbols": 3,
        "symbols_processed": 2,
        "failed_symbols": [{"symbol": "000002", "error": "timeout"}],
        "resume_cursor": 2,
        "completed": False,
    }
    recording_service = _RecordingBackfillService(summary)
    runtime = SimpleNamespace(data_service=recording_service)

    parser_args = SimpleNamespace(
        command="backfill",
        frequency="daily",
        batch_size=2,
        max_symbols=3,
        resume=True,
        retry_failures=False,
        start_date="2024-01-01",
        end_date="2024-01-31",
        symbols=None,
    )

    monkeypatch.setattr(cli_module, "get_runtime", lambda: runtime)
    monkeypatch.setattr(cli_module, "_build_parser", lambda: _ParserStub(parser_args))

    cli_module.main()

    captured = capsys.readouterr().out.strip()
    assert recording_service.calls, "Backfill CLI should delegate to a runtime backfill/data service."

    payload = json.loads(captured)
    assert payload["frequency"] == "daily"
    assert payload["batch_size"] == 2
    assert payload["resume_cursor"] == 2
    assert payload["failed_symbols"][0]["symbol"] == "000002"

    call = recording_service.calls[0]
    resume_value = _extract_scalar(call, ("resume",))
    if resume_value is not None:
        assert resume_value is True, "CLI should pass the resume flag through to the backfill workflow."

    batch_size = _extract_scalar(call, ("batch_size",))
    if batch_size is not None:
        assert batch_size == 2, "CLI should propagate batch size to the backfill workflow."
