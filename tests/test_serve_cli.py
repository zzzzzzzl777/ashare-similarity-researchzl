from __future__ import annotations

import argparse

from ashare_similarity.web_launcher import DEFAULT_PORT_SCAN_LIMIT, DEFAULT_WEB_HOST, DEFAULT_WEB_PORT


def _subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    subparser_actions = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]
    assert subparser_actions, "CLI should continue using argparse subcommands."
    return subparser_actions[0].choices


def test_cli_parser_exposes_serve_subcommand(load_public_attr):
    build_parser = load_public_attr("ashare_similarity.cli", "_build_parser")
    parser = build_parser()

    assert "serve" in _subcommands(parser), (
        "CLI should expose a `serve` subcommand so the packaged web UI can be started from the operator entrypoint."
    )
    assert "doctor" in _subcommands(parser), (
        "CLI should expose a `doctor` subcommand so operators can self-check readiness before using or reporting issues."
    )


def test_cli_serve_parser_uses_web_launcher_defaults(load_public_attr):
    build_parser = load_public_attr("ashare_similarity.cli", "_build_parser")
    parser = build_parser()

    args = parser.parse_args(["serve"])

    assert args.command == "serve"
    assert args.host == DEFAULT_WEB_HOST
    assert args.port == DEFAULT_WEB_PORT
    assert args.log_level == "info"
    assert args.reload is False
    assert args.port_scan_limit == DEFAULT_PORT_SCAN_LIMIT


def test_cli_serve_help_and_overrides_cover_web_startup_flags(load_public_attr):
    build_parser = load_public_attr("ashare_similarity.cli", "_build_parser")
    parser = build_parser()
    serve_parser = _subcommands(parser)["serve"]

    help_text = serve_parser.format_help()
    assert "--host" in help_text
    assert "--port" in help_text
    assert "--reload" in help_text
    assert "--port-scan-limit" in help_text

    args = parser.parse_args(
        [
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            "9020",
            "--log-level",
            "debug",
            "--reload",
            "--port-scan-limit",
            "4",
        ]
    )

    assert args.host == "127.0.0.1"
    assert args.port == 9020
    assert args.log_level == "debug"
    assert args.reload is True
    assert args.port_scan_limit == 4


def test_cli_doctor_parser_supports_optional_search_overrides(load_public_attr):
    build_parser = load_public_attr("ashare_similarity.cli", "_build_parser")
    parser = build_parser()

    args = parser.parse_args(
        [
            "doctor",
            "--symbol",
            "000333",
            "--end-date",
            "2026-04-23",
            "--frequency",
            "daily",
            "--window-size",
            "10",
            "--top-k",
            "12",
        ]
    )

    assert args.command == "doctor"
    assert args.symbol == "000333"
    assert args.end_date == "2026-04-23"
    assert args.frequency == "daily"
    assert args.window_size == 10
    assert args.top_k == 12
