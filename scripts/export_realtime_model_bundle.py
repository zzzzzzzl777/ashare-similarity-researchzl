"""Export a real model bundle for Run G (tier1_plus_c009_c004).

Captures all components needed for standalone prediction:
- Ensemble member models (torch state_dicts + sklearn tree models)
- Feature normalization (mean/std)
- Feature selection (selected_indices, selected_feature_names)
- Calibration (per-member platt + ensemble-level isotonic)
- Threshold + confidence band
- Config metadata

Does NOT modify gpu_probe.py source. Uses monkey-patch capture.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import pickle
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import numpy as np
import torch
import pandas as pd

import ashare_similarity.prediction.gpu_probe as gp
from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import (
    GPU_PROBE_STABLE_FEATURES,
    GpuProbeConfig,
    run_gpu_next_day_probe,
)

# ---------------------------------------------------------------------------
# Feature definitions (same as Run G)
# ---------------------------------------------------------------------------
TUSHARE_TIER1_BASE = (
    "tushare_net_mf_amount", "tushare_lg_buy_sell_ratio", "tushare_elg_buy_sell_ratio",
    "tushare_mf_strength", "tushare_sm_sell_pressure", "tushare_volume_ratio",
    "tushare_free_share", "tushare_up_limit_distance", "tushare_down_limit_distance",
    "tushare_limit_range",
)
TUSHARE_TIER1_FEATURES = (*TUSHARE_TIER1_BASE, *(f"{c}_available" for c in TUSHARE_TIER1_BASE))
C009_FEATURES = ("tushare_main_force_divergence", "tushare_main_force_divergence_available")
C004_FEATURES = ("tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available")
TIER1_PLUS_C009_C004 = (*TUSHARE_TIER1_FEATURES, *C009_FEATURES, *C004_FEATURES)

BUNDLE_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\realtime_model_bundles")


def main():
    print("=" * 60, file=sys.stderr)
    print("EXPORT REALTIME MODEL BUNDLE (Run G: C009+C004)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    app_config = get_default_config()
    store = LocalDataStore(app_config)

    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 4, 30),
        train_rows=300_000,
        test_rows=120_000,
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        min_phase_days_3=1,
        selector_coverage_weight=0.02,
        candidate_family="all",
        lockbox_role="seen_research",
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        seed=42,
        feature_set="research",
        use_feature_cache=True,
    )

    custom_features = tuple(dict.fromkeys((*GPU_PROBE_STABLE_FEATURES, *TIER1_PLUS_C009_C004)))

    # --- Patch feature names (same two-phase as ablation) ---
    original_fn = gp._feature_names_for_config
    call_state = {"count": 0}
    def _two_phase(cfg):
        call_state["count"] += 1
        return original_fn(cfg) if call_state["count"] == 1 else custom_features
    gp._feature_names_for_config = _two_phase

    # --- Capture hook: intercept _train_and_score to save model internals ---
    captured = {}
    original_train_and_score = gp._train_and_score

    def _capturing_train_and_score(train_df, test_df, **kwargs):
        device = kwargs["device"]
        feature_names = kwargs["feature_names"]

        # Replicate pre-processing to capture mean/std/indices
        fit_frame, valid_frame, split_info = gp._purged_train_validation_split(
            train_df,
            validation_fraction=kwargs.get("validation_fraction", 0.15),
            embargo_label_days=kwargs.get("embargo_label_days", 5),
            max_fit_rows=kwargs.get("max_fit_rows", 300_000),
            seed=kwargs["seed"],
        )
        x_train = torch.as_tensor(
            fit_frame.loc[:, feature_names].to_numpy(dtype=np.float32), device=device
        )
        mean = x_train.mean(dim=0, keepdim=True)
        std = torch.clamp(x_train.std(dim=0, keepdim=True), min=1e-6)

        captured["mean"] = mean.cpu()
        captured["std"] = std.cpu()
        captured["full_feature_names"] = feature_names

        # Run original training
        result = original_train_and_score(train_df, test_df, **kwargs)

        # Capture feature selection info from result
        fs = result.get("feature_selection", {})
        selected_features = fs.get("selected_features", list(feature_names))
        captured["selected_feature_names"] = tuple(selected_features)
        captured["selected_feature_count"] = fs.get("selected_feature_count", len(feature_names))

        # Compute selected_indices
        name_to_idx = {name: i for i, name in enumerate(feature_names)}
        captured["selected_indices"] = [name_to_idx[n] for n in selected_features if n in name_to_idx]

        return result

    gp._train_and_score = _capturing_train_and_score

    # --- Capture ensemble members and isotonic ---
    original_build_ensemble = gp._build_average_ensemble_candidate
    def _capturing_build_ensemble(candidates, valid_y, **kwargs):
        result = original_build_ensemble(candidates, valid_y, **kwargs)
        if result:
            captured["ensemble_members"] = result.get("members", [])
            captured["ensemble_threshold"] = result.get("threshold", 0.5)
            captured["ensemble_confidence_band"] = result.get("confidence_band", {})
            captured["member_models_names"] = result.get("member_models", [])
        return result
    gp._build_average_ensemble_candidate = _capturing_build_ensemble

    original_fit_isotonic = gp._fit_isotonic_calibration
    def _capturing_fit_isotonic(prob, y):
        iso = original_fit_isotonic(prob, y)
        captured["iso_model"] = iso
        return iso
    gp._fit_isotonic_calibration = _capturing_fit_isotonic

    # Track which calibration is used
    original_brier = gp._brier
    brier_calls = []
    def _tracking_brier(prob, y):
        result = original_brier(prob, y)
        brier_calls.append(float(result))
        return result
    gp._brier = _tracking_brier

    # --- Run the pipeline ---
    print("\nRunning pipeline to capture model...", file=sys.stderr)
    t0 = time.perf_counter()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.perf_counter() - t0
    print(f"Pipeline completed in {elapsed:.1f}s, status={result.get('status')}", file=sys.stderr)

    # Restore patches
    gp._feature_names_for_config = original_fn
    gp._train_and_score = original_train_and_score
    gp._build_average_ensemble_candidate = original_build_ensemble
    gp._fit_isotonic_calibration = original_fit_isotonic
    gp._brier = original_brier

    if result.get("status") != "completed":
        print(f"ERROR: Pipeline did not complete: {result.get('status')}", file=sys.stderr)
        return 1

    # --- Build and save bundle ---
    print("\nBuilding model bundle...", file=sys.stderr)

    run_id = result.get("run_id", "unknown")
    bundle_id = f"bundle_G_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    # Serialize ensemble members
    members_serialized = []
    ensemble_members = captured.get("ensemble_members", [])
    for member in ensemble_members:
        model_kind = member.get("model_kind", "torch")
        model_obj = member.get("model")
        m_info = {
            "model_name": member.get("model_name", ""),
            "model_kind": model_kind,
            "calibration": member.get("calibration", {"scale": 1.0, "bias": 0.0}),
            "threshold": member.get("threshold", 0.5),
            "selection_score": member.get("selection_score", 0.0),
            "validation_accuracy": member.get("validation_accuracy", 0.0),
            "validation_brier": member.get("validation_brier", 1.0),
        }
        if model_kind == "torch" and model_obj is not None:
            buf = io.BytesIO()
            torch.save({
                "state_dict": model_obj.state_dict(),
                "class_name": type(model_obj).__name__,
                "input_dim": model_obj.state_dict()[list(model_obj.state_dict().keys())[0]].shape[1]
                    if len(model_obj.state_dict()) > 0 else 260,
            }, buf)
            m_info["model_bytes"] = buf.getvalue()
        elif model_kind in ("xgboost", "lightgbm", "catboost") and model_obj is not None:
            buf = io.BytesIO()
            pickle.dump(model_obj, buf)
            m_info["model_bytes"] = buf.getvalue()
        members_serialized.append(m_info)

    # Determine calibration_used
    # isotonic is used if iso_model is not None and improved brier
    iso_model = captured.get("iso_model")
    calibration_used = "isotonic" if iso_model is not None else "platt"
    # The pipeline checks if isotonic brier < pre-isotonic brier
    # We'll save both and let the predict script decide based on the flag

    # Serialize isotonic model
    iso_bytes = None
    if iso_model is not None:
        buf = io.BytesIO()
        pickle.dump(iso_model, buf)
        iso_bytes = buf.getvalue()

    bundle = {
        "bundle_id": bundle_id,
        "source_run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_version": "gpu_probe_v22",
        "model_name": "stacking_average_top3",
        "model_kind": "ensemble_average",
        "member_count": len(members_serialized),
        "member_names": [m["model_name"] for m in members_serialized],
        "selected_feature_names": list(captured.get("selected_feature_names", [])),
        "selected_feature_count": captured.get("selected_feature_count", 0),
        "full_feature_names": list(captured.get("full_feature_names", [])),
        "selected_indices": captured.get("selected_indices", []),
        "classification_threshold": captured.get("ensemble_threshold", 0.5),
        "confidence_band": captured.get("ensemble_confidence_band", {}),
        "calibration_used": calibration_used,
        "config": {
            "train_end": str(config.train_end),
            "test_start": str(config.test_start),
            "end": str(config.end),
            "seed": config.seed,
            "feature_set": config.feature_set,
            "label_target": config.label_target,
            "target_high_return_pct": config.target_high_return_pct,
            "max_selected_features": config.max_selected_features,
            "feature_selection_method": config.feature_selection_method,
            "min_phase_days_3": config.min_phase_days_3,
            "exclude_event_limit_up": config.exclude_event_limit_up,
            "candidate_family": config.candidate_family,
            "extra_features": list(TIER1_PLUS_C009_C004),
            "factor_ids": ["C009", "C004"],
        },
    }

    # Compute config hash
    config_str = json.dumps(bundle["config"], sort_keys=True)
    bundle["config_hash"] = hashlib.sha256(config_str.encode()).hexdigest()[:16]

    # Save bundle
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    bundle_path = BUNDLE_DIR / f"{bundle_id}.pt"

    save_payload = {
        "metadata": {k: v for k, v in bundle.items() if k not in ("_tensors",)},
        "mean": captured.get("mean"),
        "std": captured.get("std"),
        "selected_indices": torch.tensor(captured.get("selected_indices", []), dtype=torch.long),
        "members": members_serialized,
        "iso_model_bytes": iso_bytes,
        "calibration_used": calibration_used,
    }

    torch.save(save_payload, str(bundle_path))
    bundle_size_mb = bundle_path.stat().st_size / 1024 / 1024

    # Also save metadata JSON (human-readable, no model weights)
    meta_path = BUNDLE_DIR / f"{bundle_id}_meta.json"
    meta_json = {k: v for k, v in bundle.items()}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_json, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"BUNDLE SAVED", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"  Bundle ID: {bundle_id}", file=sys.stderr)
    print(f"  Source run: {run_id}", file=sys.stderr)
    print(f"  Path: {bundle_path}", file=sys.stderr)
    print(f"  Size: {bundle_size_mb:.1f} MB", file=sys.stderr)
    print(f"  Model: {bundle['model_name']} ({bundle['model_kind']})", file=sys.stderr)
    print(f"  Members: {bundle['member_names']}", file=sys.stderr)
    print(f"  Selected features: {bundle['selected_feature_count']}", file=sys.stderr)
    print(f"  Threshold: {bundle['classification_threshold']:.4f}", file=sys.stderr)
    print(f"  Calibration: {calibration_used}", file=sys.stderr)
    print(f"  Config hash: {bundle['config_hash']}", file=sys.stderr)
    print(f"  Meta JSON: {meta_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
