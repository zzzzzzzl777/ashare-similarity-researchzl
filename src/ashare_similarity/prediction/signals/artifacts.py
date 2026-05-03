from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ashare_similarity.prediction.signals.config import SignalConfig

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CandidateArtifact:
    tag: str
    run_id: str
    feature_hash: str
    data_hash: str
    split_hash: str
    code_hash: str
    config: dict[str, Any]
    metrics: dict[str, Any]
    selected_features: list[str]
    classification_threshold: float
    selector_method: str
    selector_params: dict[str, Any]
    feature_cache_fingerprint: str
    feature_cache_path: Path
    candidate_family: str
    best_model: str
    candidate_reports: list[dict[str, Any]]
    seed: int
    test_rows: int
    train_end: str
    test_start: str
    end: str


def load_frozen_candidates(signal_config: SignalConfig) -> list[dict[str, Any]]:
    path = signal_config.frozen_candidates_path
    if not path.exists():
        raise FileNotFoundError(f"Frozen candidates not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("frozen_candidates.json contains no candidates")
    return candidates


def load_candidate_artifact(
    signal_config: SignalConfig,
    candidate: dict[str, Any],
) -> CandidateArtifact:
    run_id = candidate["run_id"]
    tag = candidate["tag"]
    artifact_dir = signal_config.artifact_base_dir / run_id
    artifact_path = artifact_dir / "artifact.json"
    if not artifact_path.exists():
        raise FileNotFoundError(f"Artifact not found for {tag}: {artifact_path}")
    with open(artifact_path, encoding="utf-8") as f:
        artifact = json.load(f)

    result = artifact["result"]

    selected_features = result["feature_selection"]["selected_features"]
    classification_threshold = float(result["classification_threshold"])

    selector = result["confidence_selector"]
    selector_method = selector["method"]
    selector_params = _extract_selector_params(
        selector_method,
        selector,
        candidate_reports=result.get("candidate_reports", []),
        classification_threshold=classification_threshold,
    )

    feature_cache_info = result.get("feature_cache", {})
    feature_cache_fingerprint = feature_cache_info.get("fingerprint", "")
    feature_cache_path = Path(feature_cache_info.get("path", ""))

    feature_manifest_path = artifact_dir / "feature_manifest.json"
    if feature_manifest_path.exists():
        with open(feature_manifest_path, encoding="utf-8") as f:
            fm = json.load(f)
        fc = fm.get("feature_cache", {})
        if fc.get("fingerprint"):
            feature_cache_fingerprint = fc["fingerprint"]
        if fc.get("path"):
            feature_cache_path = Path(fc["path"])

    cfg = candidate.get("config", {})
    return CandidateArtifact(
        tag=tag,
        run_id=run_id,
        feature_hash=candidate.get("feature_hash", ""),
        data_hash=candidate.get("data_hash", ""),
        split_hash=candidate.get("split_hash", ""),
        code_hash=candidate.get("code_hash", ""),
        config=cfg,
        metrics=candidate.get("metrics", {}),
        selected_features=selected_features,
        classification_threshold=classification_threshold,
        selector_method=selector_method,
        selector_params=selector_params,
        feature_cache_fingerprint=feature_cache_fingerprint,
        feature_cache_path=feature_cache_path,
        candidate_family=cfg.get("candidate_family", "all"),
        best_model=candidate.get("metrics", {}).get("model", ""),
        candidate_reports=result.get("candidate_reports", []),
        seed=cfg.get("seed", 42),
        test_rows=cfg.get("test_rows", 120_000),
        train_end=cfg.get("train_end", "2025-06-30"),
        test_start=cfg.get("test_start", "2025-07-01"),
        end=cfg.get("end", "2026-04-30"),
    )


def _extract_selector_params(
    method: str,
    selector: dict[str, Any],
    *,
    candidate_reports: list[dict[str, Any]] | None = None,
    classification_threshold: float = 0.5,
) -> dict[str, Any]:
    if method == "candidate_agreement":
        model_thresholds: dict[str, float] = {}
        if candidate_reports:
            for report in candidate_reports:
                name = report.get("model_name") or report.get("model", "")
                t = report.get("threshold") or report.get("classification_threshold")
                if name and t is not None:
                    model_thresholds[name] = float(t)
        return {
            "agreement_threshold": float(selector.get("agreement_threshold", 0.6)),
            "margin_threshold": float(selector.get("margin_threshold", 0.26)),
            "side_match_required": bool(selector.get("side_match_required", True)),
            "models": list(selector.get("models", [])),
            "model_thresholds": model_thresholds,
            "best_model_threshold": classification_threshold,
        }
    if method == "regime_probability_gate":
        return {
            "feature": str(selector.get("feature", "")),
            "feature_side": str(selector.get("feature_side", "low")),
            "feature_quantile": float(selector.get("feature_quantile", 0.15)),
            "feature_threshold_standardized": float(selector.get("feature_threshold_standardized", 0.0)),
            "probability_side": str(selector.get("probability_side", "long")),
            "probability_margin": float(selector.get("probability_margin", 0.09)),
            "classification_threshold": classification_threshold,
        }
    return dict(selector)


def hash_selected_features(features: list[str]) -> str:
    joined = "\n".join(sorted(features))
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def hash_selector_config(params: dict[str, Any]) -> str:
    canonical = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
