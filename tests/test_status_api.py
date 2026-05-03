from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
import pytest

from ashare_similarity.schemas import DataFreshness


def _flatten_keys(value: Any) -> set[str]:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")

    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_flatten_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_flatten_keys(item))
    return keys


def _flatten_values(value: Any) -> list[Any]:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")

    if isinstance(value, Mapping):
        flattened: list[Any] = []
        for item in value.values():
            flattened.extend(_flatten_values(item))
        return flattened
    if isinstance(value, list):
        flattened = []
        for item in value:
            flattened.extend(_flatten_values(item))
        return flattened
    return [value]


def _find_nested_value(value: Any, candidate_keys: tuple[str, ...]) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="python")

    if isinstance(value, Mapping):
        for key in candidate_keys:
            if key in value:
                return value[key]
        for item in value.values():
            found = _find_nested_value(item, candidate_keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_nested_value(item, candidate_keys)
            if found is not None:
                return found
    return None


class _StatusHarness:
    def __init__(self) -> None:
        self.backfill_payload = {
            "run_id": "run-001",
            "frequency": "daily",
            "status": "running",
            "batch_size": 2,
            "requested_symbols": 3,
            "attempted_symbols": 1,
            "completed_symbols": 1,
            "failed_symbols": 1,
            "remaining_symbols": 2,
            "last_symbol": "000001",
            "sample_failures": [{"symbol": "000002", "error": "timeout"}],
            "updated_at": "2026-04-23T09:30:00",
        }
        self.cache_payload = {
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
        }

    def get_status(self) -> dict[str, Any]:
        return {"latest_backfill": self.backfill_payload, "cache_status": self.cache_payload}

    def get_backfill_status(self) -> dict[str, Any]:
        return self.backfill_payload

    def backfill_status(self) -> dict[str, Any]:
        return self.backfill_payload

    def get_cache_status(self) -> dict[str, Any]:
        return self.cache_payload

    def get_system_status(self) -> dict[str, Any]:
        return {
            "universe_count": 3,
            "filtered_universe_count": 3,
            "cache_status": self.cache_payload,
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
            "latest_backfill": self.backfill_payload,
        }

    def list_cached_symbols(self, frequency: str) -> list[str]:
        if frequency == "daily":
            return ["000001", "000003"]
        return []

    def get_data_freshness(self, frequency: str) -> DataFreshness:
        return DataFreshness(
            data_source="synthetic-fixture",
            notice=None,
            last_refresh_at=datetime(2026, 4, 23, 9, 35, 0),
        )


class _RuntimeIndexHarness:
    def exists(self, frequency: str, window_size: int) -> bool:
        return frequency == "daily" and window_size == 10

    def get_cached(self, frequency: str, window_size: int):
        assert frequency == "daily"
        assert window_size == 10
        return SimpleNamespace(
            search_index=SimpleNamespace(
                runtime_metadata=lambda: {
                    "active_backend": "torch-cuda-bruteforce",
                    "artifact_backend": "sklearn-nearest",
                    "active_device": "cuda:0",
                    "active_device_name": "Synthetic GPU",
                }
            )
        )


@pytest.fixture
def status_api_client(monkeypatch, load_public_attr, maybe_patch_attr, app_config):
    create_app = load_public_attr("ashare_similarity.app", "create_app")
    harness = _StatusHarness()
    runtime = SimpleNamespace(
        config=app_config,
        data_service=harness,
        store=harness,
        search_service=SimpleNamespace(),
        feature_service=SimpleNamespace(),
        index_service=_RuntimeIndexHarness(),
        context_service=SimpleNamespace(),
    )

    maybe_patch_attr(monkeypatch, "ashare_similarity.runtime.get_runtime", lambda: runtime)
    maybe_patch_attr(monkeypatch, "ashare_similarity.web.routes.get_runtime", lambda: runtime)

    app = create_app()
    app.state.runtime = runtime
    app.state.app_config = app_config

    with TestClient(app) as client:
        yield client, app


def test_api_registers_status_endpoint(status_api_client):
    _, app = status_api_client
    status_paths = [
        route.path
        for route in app.routes
        if hasattr(route, "path") and route.path.startswith("/api/") and "status" in route.path
    ]

    assert status_paths, (
        "Web API should expose a status endpoint for backfill/cache visibility, for example `/api/status` "
        "or `/api/backfill/status`."
    )


def test_status_endpoint_surfaces_backfill_progress_and_cache_summary(status_api_client):
    client, app = status_api_client
    status_paths = [
        route.path
        for route in app.routes
        if hasattr(route, "path") and route.path.startswith("/api/") and "status" in route.path
    ]
    if not status_paths:
        pytest.fail("No status route is registered, so the backfill/cache contract cannot be exercised.")

    response = client.get("/api/status")
    assert response.status_code == 200, response.text

    payload = response.json()
    keys = _flatten_keys(payload)
    values = {str(item) for item in _flatten_values(payload)}

    assert {"latest_backfill", "backfill", "backfill_status"} & keys, "Status API should include a backfill status section."
    assert {"cache", "cache_status", "cached_symbols"} & keys, "Status API should include cache-level visibility."
    assert "000002" in values, "Status API should surface failed-symbol diagnostics from the backfill workflow."
    assert "timeout" in values, "Status API should preserve operator-facing failure reasons."

    resume_marker = _find_nested_value(payload, ("resume_cursor", "cursor", "next_cursor", "next_offset", "remaining_symbols", "last_symbol", "run_id"))
    assert resume_marker is not None, "Status API should surface enough progress metadata to resume the next backfill batch."

    cached_count = _find_nested_value(payload, ("cached_symbols", "cache_count", "symbol_count"))
    assert isinstance(cached_count, int) and cached_count >= 2, (
        "Status API should expose how much cache is currently available, not just whether a task exists."
    )


def test_status_endpoint_surfaces_runtime_acceleration_truth(status_api_client):
    client, _ = status_api_client

    response = client.get("/api/status")
    assert response.status_code == 200, response.text

    payload = response.json()
    acceleration = payload.get("acceleration") or {}

    assert acceleration["active_backend"] == "torch-cuda-bruteforce"
    assert acceleration["artifact_backend"] == "sklearn-nearest"
    assert acceleration["status_backend"] == "sklearn-nearest"
    assert acceleration["active_backend_source"] == "runtime-index"
    assert acceleration["active_device"] == "cuda:0"
    assert acceleration["active_device_name"] == "Synthetic GPU"
    assert acceleration["gpu_enabled"] is True


def test_status_endpoint_surfaces_explicit_index_health(status_api_client):
    client, _ = status_api_client

    response = client.get("/api/status")
    assert response.status_code == 200, response.text

    payload = response.json()
    daily_health = payload.get("index_health", {}).get("daily", {})
    daily_index = payload.get("index_status", {}).get("daily_10", {})

    assert daily_health["built_windows"] == [10]
    assert daily_health["missing_windows"] == [5, 8, 20]
    assert daily_health["stale_windows"] == [10]
    assert daily_health["current_index_symbol_count"] == 1
    assert daily_health["cache_gap"] == 1
    assert daily_health["research_ready"] is False
    assert daily_index["stale"] is True
