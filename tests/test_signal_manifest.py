from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ashare_similarity.prediction.signals.config import SignalConfig
from ashare_similarity.prediction.signals.service import SignalService


def _write_frozen(report_dir: Path) -> Path:
    frozen = {
        "candidates": [
            {"tag": "accuracy_priority", "run_id": "run_abc", "feature_hash": "fh1", "data_hash": "dh1", "split_hash": "sh1", "code_hash": "ch1", "config": {}, "metrics": {}},
        ]
    }
    frozen_path = report_dir / "frozen_candidates_20260503.json"
    frozen_path.write_text(json.dumps(frozen), encoding="utf-8")
    return frozen_path


def _write_manifest(build_dir: Path, *, run_id: str = "run_abc") -> None:
    manifest = {
        "schema_version": 1,
        "build_id": build_dir.name,
        "candidates": [
            {"candidate_tag": "accuracy_priority", "run_id": run_id, "feature_hash": "fh1", "data_hash": "dh1", "split_hash": "sh1", "code_hash": "ch1"},
        ],
    }
    (build_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _write_parquet(build_dir: Path) -> None:
    df = pd.DataFrame({
        "date": pd.to_datetime(["2025-08-01"]),
        "symbol": ["600519"],
        "model_tag": ["accuracy_priority"],
        "best_model": ["gpu_logistic"],
        "selector_method": ["candidate_agreement"],
        "probability": [0.72],
        "confident": [True],
        "actual": [1.0],
        "split_layer": ["dev_valid"],
        "decision_threshold": [0.36],
        "predicted_positive": [True],
        "correct": [True],
    })
    df.to_parquet(build_dir / "signal_cache.parquet", index=False)


def _make_config(tmp_path: Path, *, write_parquet: bool = True, tamper_run_id: bool = False, omit_frozen: bool = False) -> SignalConfig:
    cache_root = tmp_path / "cache" / "prediction" / "signals" / "v1"
    report_dir = tmp_path / "reports" / "prediction"
    report_dir.mkdir(parents=True)

    if omit_frozen:
        frozen_path = report_dir / "frozen_candidates_20260503.json"
    else:
        frozen_path = _write_frozen(report_dir)

    build_id = "20260503T000000Z_test"
    build_dir = cache_root / build_id
    build_dir.mkdir(parents=True)

    _write_manifest(build_dir, run_id="run_WRONG" if tamper_run_id else "run_abc")
    if write_parquet:
        _write_parquet(build_dir)

    (cache_root / "current.json").write_text(json.dumps({"build_id": build_id}), encoding="utf-8")

    return SignalConfig(
        cache_root=cache_root,
        report_dir=report_dir,
        frozen_candidates_path=frozen_path,
        artifact_base_dir=report_dir / "runs",
    )


def test_manifest_valid_with_parquet(tmp_path: Path) -> None:
    sc = _make_config(tmp_path, write_parquet=True)
    svc = SignalService(sc)
    status = svc.get_status()
    assert status.status == "ready"


def test_manifest_valid_missing_parquet(tmp_path: Path) -> None:
    sc = _make_config(tmp_path, write_parquet=False)
    svc = SignalService(sc)
    status = svc.get_status()
    assert status.status == "not_built"


def test_manifest_mismatch_rejects(tmp_path: Path) -> None:
    sc = _make_config(tmp_path, tamper_run_id=True)
    svc = SignalService(sc)
    status = svc.get_status()
    assert status.status == "manifest_mismatch"


def test_manifest_mismatch_when_frozen_missing(tmp_path: Path) -> None:
    sc = _make_config(tmp_path, omit_frozen=True)
    svc = SignalService(sc)
    status = svc.get_status()
    assert status.status == "manifest_mismatch"


def test_manifest_required_fields() -> None:
    manifest = {
        "schema_version": 1,
        "build_id": "test",
        "candidates": [
            {"candidate_tag": "t", "run_id": "r", "feature_hash": "f", "data_hash": "d", "split_hash": "s", "code_hash": "c"},
        ],
    }
    required_keys = {"candidate_tag", "run_id", "feature_hash", "data_hash", "split_hash", "code_hash"}
    for c in manifest["candidates"]:
        assert required_keys.issubset(set(c.keys()))


def test_manifest_mismatch_when_manifest_missing_candidate(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache" / "prediction" / "signals" / "v1"
    report_dir = tmp_path / "reports" / "prediction"
    report_dir.mkdir(parents=True)

    frozen = {
        "candidates": [
            {"tag": "accuracy_priority", "run_id": "run_a", "feature_hash": "fh1", "data_hash": "dh1", "split_hash": "sh1", "code_hash": "ch1"},
            {"tag": "coverage_priority", "run_id": "run_b", "feature_hash": "fh2", "data_hash": "dh2", "split_hash": "sh2", "code_hash": "ch2"},
        ]
    }
    frozen_path = report_dir / "frozen_candidates_20260503.json"
    frozen_path.write_text(json.dumps(frozen), encoding="utf-8")

    build_id = "20260503T000000Z_test"
    build_dir = cache_root / build_id
    build_dir.mkdir(parents=True)

    manifest = {
        "schema_version": 1,
        "build_id": build_id,
        "candidates": [
            {"candidate_tag": "accuracy_priority", "run_id": "run_a", "feature_hash": "fh1", "data_hash": "dh1", "split_hash": "sh1", "code_hash": "ch1"},
        ],
    }
    (build_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _write_parquet(build_dir)
    (cache_root / "current.json").write_text(json.dumps({"build_id": build_id}), encoding="utf-8")

    sc = SignalConfig(
        cache_root=cache_root,
        report_dir=report_dir,
        frozen_candidates_path=frozen_path,
        artifact_base_dir=report_dir / "runs",
    )
    svc = SignalService(sc)
    status = svc.get_status()
    assert status.status == "manifest_mismatch"
