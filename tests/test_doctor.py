from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from ashare_similarity.doctor import build_acceleration_status, build_doctor_report
from ashare_similarity.schemas import DataFreshness


class _DoctorSearchService:
    def __init__(self, sample_search_response) -> None:
        self._response = sample_search_response

    def search(self, request):
        response = self._response.model_copy(deep=True)
        response.query_meta.symbol = request.symbol
        response.query_meta.frequency = request.frequency
        response.query_meta.window_size = request.window_size
        response.query_meta.end_date = str(request.end_date)[:10]
        response.data_freshness = DataFreshness(
            last_refresh_at=datetime(2026, 4, 23, 10, 20, 0),
            latest_data_at=datetime(2026, 4, 23, 15, 0, 0),
            data_source="synthetic-fixture",
            notice=None,
        )
        return response


class _DoctorDataService:
    def get_system_status(self):
        return {
            "universe_count": 100,
            "filtered_universe_count": 80,
            "cache_status": {
                "daily": {
                    "frequency": "daily",
                    "cached_symbols": 61,
                    "data_freshness": {
                        "last_refresh_at": "2026-04-23T10:20:00",
                        "latest_data_at": "2026-04-23T15:00:00",
                        "data_source": "synthetic-fixture",
                        "notice": None,
                    },
                }
            },
            "index_status": {
                "daily_5": {"frequency": "daily", "window_size": 5, "backend": "sklearn-nearest"},
                "daily_8": {"frequency": "daily", "window_size": 8, "backend": "sklearn-nearest"},
                "daily_10": {"frequency": "daily", "window_size": 10, "backend": "sklearn-nearest"},
                "daily_20": {"frequency": "daily", "window_size": 20, "backend": "sklearn-nearest"},
            },
            "latest_backfill": {
                "run_id": "run-001",
                "frequency": "daily",
                "status": "partial",
                "batch_size": 10,
                "requested_symbols": 80,
                "attempted_symbols": 61,
                "completed_symbols": 61,
                "failed_symbols": 0,
                "remaining_symbols": 19,
                "processed_count": 61,
                "started_at": "2026-04-23T09:00:00",
                "resume_cursor": 61,
                "sample_failures": [],
            },
        }


class _DoctorRuntimeIndexService:
    def __init__(
        self,
        *,
        active_backend: str = "torch-cuda-bruteforce",
        artifact_backend: str = "sklearn-nearest",
        active_device: str = "cuda:0",
        active_device_name: str = "Synthetic GPU",
    ) -> None:
        self._payload = {
            "active_backend": active_backend,
            "artifact_backend": artifact_backend,
            "active_device": active_device,
            "active_device_name": active_device_name,
        }

    def get_cached(self, frequency: str, window_size: int):
        assert frequency == "daily"
        assert window_size == 10
        return SimpleNamespace(
            search_index=SimpleNamespace(runtime_metadata=lambda: dict(self._payload))
        )


class _MissingArtifactIndexService:
    def exists(self, frequency: str, window_size: int) -> bool:
        return False


class _DoctorStore:
    def list_cached_symbols(self, frequency: str) -> list[str]:
        if frequency == "daily":
            return ["000333", "600036"]
        return []

    def load_bars(self, symbol: str, frequency: str):
        import pandas as pd

        return pd.DataFrame({"date": pd.to_datetime(["2026-04-22", "2026-04-23"])})


def test_build_doctor_report_marks_default_daily_query_ready(app_config, sample_search_response):
    runtime = SimpleNamespace(
        config=app_config,
        data_service=_DoctorDataService(),
        search_service=_DoctorSearchService(sample_search_response),
        store=_DoctorStore(),
    )

    report = build_doctor_report(runtime)

    assert report["overall_ready"] is True
    assert report["coverage"]["cached_symbols"] == 61
    assert report["indexes"]["missing_windows"] == []
    assert report["search_smoke"]["status"] == "ok"
    assert "acceleration" in report
    assert report["query"]["symbol"] == "000333"
    assert report["query"]["end_date"] == "2026-04-23"
    assert report["acceleration"]["status_backend"] == "sklearn-nearest"
    assert report["acceleration"]["active_backend_source"] == "status-snapshot"


def test_build_doctor_report_flags_missing_artifacts_even_when_registry_has_builds(app_config, sample_search_response):
    runtime = SimpleNamespace(
        config=app_config,
        data_service=_DoctorDataService(),
        search_service=_DoctorSearchService(sample_search_response),
        store=_DoctorStore(),
        index_service=_MissingArtifactIndexService(),
    )

    report = build_doctor_report(runtime)

    assert report["overall_ready"] is False
    assert report["indexes"]["missing_windows"] == [5, 8, 10, 20]
    assert report["indexes"]["selected_window_artifact_missing"] is True
    assert "索引工件" in "".join(report["recommendations"])


def test_build_doctor_report_prefers_runtime_backend_over_status_snapshot(app_config, sample_search_response):
    runtime = SimpleNamespace(
        config=app_config,
        data_service=_DoctorDataService(),
        search_service=_DoctorSearchService(sample_search_response),
        store=_DoctorStore(),
        index_service=_DoctorRuntimeIndexService(),
    )

    report = build_doctor_report(runtime)

    assert report["acceleration"]["active_backend"] == "torch-cuda-bruteforce"
    assert report["acceleration"]["artifact_backend"] == "sklearn-nearest"
    assert report["acceleration"]["status_backend"] == "sklearn-nearest"
    assert report["acceleration"]["active_backend_source"] == "runtime-index"
    assert report["acceleration"]["active_device"] == "cuda:0"
    assert report["acceleration"]["active_device_name"] == "Synthetic GPU"
    assert report["acceleration"]["gpu_enabled"] is True


def test_acceleration_status_projects_gpu_runtime_for_compact_artifact(app_config, monkeypatch):
    from ashare_similarity.indexing import backend as ann_backend

    monkeypatch.setattr(
        ann_backend,
        "get_acceleration_environment",
        lambda: {
            "torch_cuda_available": True,
            "torch_device_name": "Synthetic GPU",
            "torch_version": "synthetic",
            "torch_cuda_device_count": 1,
        },
    )
    runtime = SimpleNamespace(config=app_config)
    status = {
        "index_status": {
            "daily_10": {
                "frequency": "daily",
                "window_size": 10,
                "backend": "compact-recall-v1",
            }
        }
    }

    acceleration = build_acceleration_status(runtime, status, frequency="daily", window_size=10)

    assert acceleration["active_backend"] == "torch-cuda-chunked"
    assert acceleration["active_backend_source"] == "runtime-projected"
    assert acceleration["active_device"] == "cuda:0"
    assert acceleration["gpu_enabled"] is True


def test_build_doctor_report_flags_stale_selected_window(app_config, sample_search_response):
    runtime = SimpleNamespace(
        config=app_config,
        data_service=_DoctorDataService(),
        search_service=_DoctorSearchService(sample_search_response),
        store=_DoctorStore(),
    )
    runtime.data_service.get_system_status = lambda: {
        "universe_count": 100,
        "filtered_universe_count": 80,
        "cache_status": {
            "daily": {
                "frequency": "daily",
                "cached_symbols": 80,
                "data_freshness": {
                    "last_refresh_at": "2026-04-23T10:20:00",
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
                "rows_count": 999,
                "symbol_count": 61,
            }
        },
        "latest_backfill": None,
    }

    report = build_doctor_report(runtime)

    assert report["overall_ready"] is False
    assert report["indexes"]["stale_windows"] == [10]
    assert "请先重建该窗口索引" in "".join(report["recommendations"])


def test_build_doctor_report_flags_index_built_before_latest_cached_data(app_config, sample_search_response):
    runtime = SimpleNamespace(
        config=app_config,
        data_service=_DoctorDataService(),
        search_service=_DoctorSearchService(sample_search_response),
        store=_DoctorStore(),
    )
    runtime.data_service.get_system_status = lambda: {
        "universe_count": 100,
        "filtered_universe_count": 80,
        "cache_status": {
            "daily": {
                "frequency": "daily",
                "cached_symbols": 61,
                "data_freshness": {
                    "last_refresh_at": "2026-04-23T10:20:00",
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
                "rows_count": 999,
                "metadata": {
                    "symbol_count": 61,
                    "built_from": {"latest_data_at": "2026-04-22T15:00:00"},
                },
            }
        },
        "latest_backfill": None,
    }

    report = build_doctor_report(runtime)

    assert report["overall_ready"] is False
    assert report["indexes"]["stale_windows"] == [10]
