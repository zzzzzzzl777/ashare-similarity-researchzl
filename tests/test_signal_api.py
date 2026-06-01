from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ashare_similarity.prediction.signals.config import SignalConfig
from ashare_similarity.prediction.signals.service import SignalService


def _make_test_cache(tmp_path: Path) -> tuple[SignalConfig, Path]:
    cache_root = tmp_path / "cache" / "prediction" / "signals" / "v1"
    report_dir = tmp_path / "reports" / "prediction"
    report_dir.mkdir(parents=True)

    frozen = {
        "candidates": [
            {"tag": "accuracy_priority", "run_id": "run_a", "feature_hash": "fh1", "data_hash": "dh1", "split_hash": "sh1", "code_hash": "ch1", "config": {}, "metrics": {}},
        ]
    }
    frozen_path = report_dir / "frozen_candidates_20260503.json"
    frozen_path.write_text(json.dumps(frozen), encoding="utf-8")

    build_id = "20260503T000000Z_api_test"
    build_dir = cache_root / build_id
    build_dir.mkdir(parents=True)

    df = pd.DataFrame({
        "date": pd.to_datetime(["2025-08-01", "2025-08-01", "2026-02-01", "2026-02-01"]),
        "symbol": ["600519", "000001", "600519", "000001"],
        "model_tag": ["accuracy_priority"] * 4,
        "best_model": ["gpu_logistic"] * 4,
        "selector_method": ["candidate_agreement"] * 4,
        "probability": [0.72, 0.45, 0.68, 0.52],
        "confident": [True, False, True, False],
        "actual": [1.0, 0.0, 1.0, 0.0],
        "split_layer": ["dev_valid", "dev_valid", "seen_research", "seen_research"],
        "decision_threshold": [0.36] * 4,
        "predicted_positive": [True, True, True, True],
        "correct": [True, False, True, False],
    })
    df.to_parquet(build_dir / "signal_cache.parquet", index=False)

    manifest = {
        "schema_version": 1,
        "build_id": build_id,
        "generated_at": "2026-05-03T00:00:00+00:00",
        "research_only": True,
        "test_date_range": ["2025-08-01", "2026-02-01"],
        "candidates": [
            {
                "candidate_tag": "accuracy_priority",
                "run_id": "run_a",
                "feature_hash": "fh1",
                "data_hash": "dh1",
                "split_hash": "sh1",
                "code_hash": "ch1",
                "best_model": "gpu_logistic",
                "selector_method": "candidate_agreement",
                "artifact_reference": {"hc_accuracy": 0.81},
            },
        ],
    }
    (build_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (cache_root / "current.json").write_text(json.dumps({"build_id": build_id}), encoding="utf-8")

    sc = SignalConfig(
        cache_root=cache_root,
        report_dir=report_dir,
        frozen_candidates_path=frozen_path,
        artifact_base_dir=report_dir / "runs",
    )
    return sc, build_dir


def _create_test_app(signal_service: SignalService):
    from fastapi import FastAPI
    from ashare_similarity.web.routes import router

    app = FastAPI()
    app.state.signal_service = signal_service
    app.state.runtime = SimpleNamespace(
        config=SimpleNamespace(ranking=SimpleNamespace(forward_windows=(1, 3, 5, 10))),
        data_service=SimpleNamespace(
            get_system_status=lambda: {},
            resolve_symbol_query=lambda q, **kw: {"symbol": q, "name": ""},
        ),
        search_service=None,
        index_service=SimpleNamespace(),
    )
    app.include_router(router)
    return app


def test_status_always_200_no_cache(tmp_path: Path) -> None:
    sc = SignalConfig(
        cache_root=tmp_path / "empty",
        report_dir=tmp_path / "reports" / "prediction",
        frozen_candidates_path=tmp_path / "nonexistent.json",
        artifact_base_dir=tmp_path / "runs",
    )
    svc = SignalService(sc)
    app = _create_test_app(svc)
    client = TestClient(app)
    r = client.get("/api/signals/v1/status")
    assert r.status_code == 200
    assert r.json()["status"] == "not_built"


def test_status_ready_with_cache(tmp_path: Path) -> None:
    sc, _ = _make_test_cache(tmp_path)
    svc = SignalService(sc)
    app = _create_test_app(svc)
    client = TestClient(app)
    r = client.get("/api/signals/v1/status")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_dates_503_no_cache(tmp_path: Path) -> None:
    sc = SignalConfig(
        cache_root=tmp_path / "empty",
        report_dir=tmp_path,
        frozen_candidates_path=tmp_path / "nonexistent.json",
        artifact_base_dir=tmp_path,
    )
    svc = SignalService(sc)
    app = _create_test_app(svc)
    client = TestClient(app)
    r = client.get("/api/signals/v1/dates")
    assert r.status_code == 503


def test_dates_with_cache(tmp_path: Path) -> None:
    sc, _ = _make_test_cache(tmp_path)
    svc = SignalService(sc)
    app = _create_test_app(svc)
    client = TestClient(app)
    r = client.get("/api/signals/v1/dates")
    assert r.status_code == 200
    data = r.json()
    assert "2025-08-01" in data["dates"]


def test_daily_with_cache(tmp_path: Path) -> None:
    sc, _ = _make_test_cache(tmp_path)
    svc = SignalService(sc)
    app = _create_test_app(svc)
    client = TestClient(app)
    r = client.get("/api/signals/v1/daily?date=2025-08-01")
    assert r.status_code == 200
    data = r.json()
    assert len(data["signals"]) > 0
    assert data["split_layer"] == "dev_valid"


def test_backtest_with_cache(tmp_path: Path) -> None:
    sc, _ = _make_test_cache(tmp_path)
    svc = SignalService(sc)
    app = _create_test_app(svc)
    client = TestClient(app)
    r = client.get("/api/signals/v1/backtest")
    assert r.status_code == 200
    data = r.json()
    assert data["research_only"] is True
    assert len(data["by_model"]) >= 1


def test_no_local_paths_in_response(tmp_path: Path) -> None:
    sc, _ = _make_test_cache(tmp_path)
    svc = SignalService(sc)
    app = _create_test_app(svc)
    client = TestClient(app)
    for url in ["/api/signals/v1/status", "/api/signals/v1/dates", "/api/signals/v1/backtest"]:
        r = client.get(url)
        text = r.text
        assert "E:\\" not in text
        assert "C:\\" not in text
        assert "\\Users\\" not in text
