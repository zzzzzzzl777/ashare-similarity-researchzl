from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any


class _StatusCliHarness:
    def __init__(self) -> None:
        self.config = SimpleNamespace(
            build_defaults=SimpleNamespace(
                daily_window_sizes=(5, 8, 10, 20),
                minute_window_sizes=(60, 120, 240),
            )
        )

    def get_system_status(self) -> dict[str, Any]:
        return {
            "universe_count": 3,
            "filtered_universe_count": 3,
            "cache_status": {
                "daily": {
                    "frequency": "daily",
                    "cached_symbols": 2,
                    "data_freshness": {
                        "last_refresh_at": "2026-04-23T09:35:00",
                        "latest_data_at": "2026-04-23T15:00:00",
                        "data_source": "synthetic-fixture",
                        "notice": None,
                    },
                }
            },
            "index_status": {
                "daily_10": {
                    "frequency": "daily",
                    "window_size": 10,
                    "backend": "sklearn-nearest",
                    "metadata": {
                        "symbol_count": 1,
                        "built_from": {"latest_data_at": "2026-04-22T15:00:00"},
                    },
                }
            },
            "latest_backfill": {
                "run_id": "run-001",
                "frequency": "daily",
                "status": "running",
            },
        }

    def get_backfill_status(self, *, frequency: str) -> dict[str, Any]:
        return {
            "run_id": "run-001",
            "frequency": frequency,
            "status": "running",
        }

    def exists(self, frequency: str, window_size: int) -> bool:
        return frequency == "daily" and window_size == 10


def test_cli_status_reuses_shared_index_health_for_selected_frequency(
    monkeypatch,
    capsys,
    load_module_or_fail,
):
    cli_module = load_module_or_fail("ashare_similarity.cli")
    harness = _StatusCliHarness()
    runtime = SimpleNamespace(config=harness.config, data_service=harness, index_service=harness)

    monkeypatch.setattr(cli_module, "get_runtime", lambda: runtime)

    cli_module.handle_status(frequency="daily")

    payload = json.loads(capsys.readouterr().out.strip())
    assert set(payload["cache_status"]) == {"daily"}
    assert set(payload["index_health"]) == {"daily"}

    daily_health = payload["index_health"]["daily"]
    daily_index = payload["index_status"]["daily_10"]

    assert daily_health["built_windows"] == [10]
    assert daily_health["missing_windows"] == [5, 8, 20]
    assert daily_health["stale_windows"] == [10]
    assert daily_health["current_index_symbol_count"] == 1
    assert daily_health["cache_gap"] == 1
    assert daily_health["research_ready"] is False
    assert daily_health["search_ready"] is False
    assert daily_index["stale"] is True
    assert payload["latest_backfill"]["frequency"] == "daily"
