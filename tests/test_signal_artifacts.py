from __future__ import annotations

import json
from pathlib import Path

import pytest

from ashare_similarity.prediction.signals.artifacts import (
    CandidateArtifact,
    _extract_selector_params,
    hash_selected_features,
    hash_selector_config,
    load_candidate_artifact,
    load_frozen_candidates,
)
from ashare_similarity.prediction.signals.config import SignalConfig


def _make_frozen(tmp_path: Path) -> Path:
    report_dir = tmp_path / "reports" / "prediction"
    report_dir.mkdir(parents=True)
    frozen_path = report_dir / "frozen_candidates_20260503.json"
    run_id = "gpu_probe_20260502T163051Z_test1234"
    run_dir = report_dir / "runs" / run_id
    run_dir.mkdir(parents=True)

    artifact = {
        "generated_at": "2026-05-02T16:30:51+00:00",
        "kind": "gpu_probe",
        "run_id": run_id,
        "result": {
            "classification_threshold": 0.36,
            "feature_selection": {
                "selected_features": ["ret_1", "ret_2", "ret_3"],
            },
            "confidence_selector": {
                "method": "candidate_agreement",
                "agreement_threshold": 0.60,
                "margin_threshold": 0.26,
                "side_match_required": True,
                "models": ["gpu_logistic", "stacking_average_top3"],
            },
            "candidate_reports": [
                {"model_name": "gpu_logistic", "threshold": 0.36},
                {"model_name": "stacking_average_top3", "threshold": 0.52},
            ],
            "feature_cache": {"fingerprint": "abc123", "path": str(tmp_path / "fake.parquet")},
        },
    }
    (run_dir / "artifact.json").write_text(json.dumps(artifact), encoding="utf-8")
    (run_dir / "feature_manifest.json").write_text(
        json.dumps({"feature_cache": {"fingerprint": "abc123", "path": str(tmp_path / "fake.parquet")}}),
        encoding="utf-8",
    )

    frozen = {
        "candidates": [
            {
                "tag": "accuracy_priority",
                "run_id": run_id,
                "feature_hash": "d3f1983cc48e6dd5",
                "data_hash": "babf3de889463a5b",
                "split_hash": "26da336b535579ab",
                "code_hash": "bb6aff4c16fff884",
                "config": {
                    "seed": 42,
                    "test_rows": 120000,
                    "train_end": "2025-06-30",
                    "test_start": "2025-07-01",
                    "end": "2026-04-30",
                    "candidate_family": "all",
                },
                "metrics": {"model": "gpu_logistic", "hc_accuracy": 0.812, "hc_coverage": 0.106},
            }
        ]
    }
    frozen_path.write_text(json.dumps(frozen), encoding="utf-8")
    return tmp_path


def test_load_frozen_candidates(tmp_path: Path) -> None:
    base = _make_frozen(tmp_path)
    sc = SignalConfig(
        cache_root=base / "cache",
        report_dir=base / "reports" / "prediction",
        frozen_candidates_path=base / "reports" / "prediction" / "frozen_candidates_20260503.json",
        artifact_base_dir=base / "reports" / "prediction" / "runs",
    )
    candidates = load_frozen_candidates(sc)
    assert len(candidates) == 1
    assert candidates[0]["tag"] == "accuracy_priority"


def test_load_candidate_artifact(tmp_path: Path) -> None:
    base = _make_frozen(tmp_path)
    sc = SignalConfig(
        cache_root=base / "cache",
        report_dir=base / "reports" / "prediction",
        frozen_candidates_path=base / "reports" / "prediction" / "frozen_candidates_20260503.json",
        artifact_base_dir=base / "reports" / "prediction" / "runs",
    )
    candidates = load_frozen_candidates(sc)
    art = load_candidate_artifact(sc, candidates[0])
    assert isinstance(art, CandidateArtifact)
    assert art.tag == "accuracy_priority"
    assert art.classification_threshold == 0.36
    assert len(art.selected_features) == 3
    assert art.selector_method == "candidate_agreement"
    assert art.selector_params["agreement_threshold"] == pytest.approx(0.60)
    assert art.selector_params["model_thresholds"]["gpu_logistic"] == pytest.approx(0.36)
    assert art.selector_params["model_thresholds"]["stacking_average_top3"] == pytest.approx(0.52)
    assert art.selector_params["best_model_threshold"] == pytest.approx(0.36)


def test_missing_frozen_candidates(tmp_path: Path) -> None:
    sc = SignalConfig(
        cache_root=tmp_path,
        report_dir=tmp_path,
        frozen_candidates_path=tmp_path / "nonexistent.json",
        artifact_base_dir=tmp_path,
    )
    with pytest.raises(FileNotFoundError):
        load_frozen_candidates(sc)


def test_extract_selector_params_agreement() -> None:
    selector = {"method": "candidate_agreement", "agreement_threshold": 0.7, "margin_threshold": 0.3, "side_match_required": True, "models": ["a", "b"]}
    reports = [{"model_name": "a", "threshold": 0.5}, {"model_name": "b", "threshold": 0.6}]
    params = _extract_selector_params("candidate_agreement", selector, candidate_reports=reports, classification_threshold=0.5)
    assert params["model_thresholds"]["a"] == 0.5
    assert params["model_thresholds"]["b"] == 0.6
    assert params["best_model_threshold"] == 0.5


def test_extract_selector_params_regime() -> None:
    selector = {"method": "regime_probability_gate", "feature": "test_feat", "feature_side": "low", "feature_quantile": 0.15, "feature_threshold_standardized": -0.2, "probability_side": "long", "probability_margin": 0.09}
    params = _extract_selector_params("regime_probability_gate", selector, classification_threshold=0.64)
    assert params["classification_threshold"] == 0.64
    assert params["probability_margin"] == pytest.approx(0.09)


def test_hash_selected_features() -> None:
    h1 = hash_selected_features(["a", "b", "c"])
    h2 = hash_selected_features(["c", "a", "b"])
    assert h1 == h2
    h3 = hash_selected_features(["a", "b"])
    assert h1 != h3


def test_hash_selector_config() -> None:
    h1 = hash_selector_config({"a": 1, "b": 2})
    h2 = hash_selector_config({"b": 2, "a": 1})
    assert h1 == h2
