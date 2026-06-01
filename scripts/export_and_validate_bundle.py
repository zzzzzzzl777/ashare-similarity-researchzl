"""Export G model bundle + validate against original test_predictions.

Captures the exact ensemble_average_top3 from Run G by re-running the
deterministic pipeline (same data + seed = same model).

Saves a .pt bundle with all components needed for standalone inference:
  - mean/std (normalization from training)
  - selected_indices (feature selection)
  - member models (state_dict for torch, pickle for tree)
  - per-member calibration (scale/bias)
  - isotonic model (if used)
  - threshold, confidence_band

Then validates by predicting on the feature cache and comparing with
the original test_predictions.parquet.
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
import pandas as pd
import torch

import ashare_similarity.prediction.gpu_probe as gp
from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import (
    GPU_PROBE_STABLE_FEATURES,
    GpuProbeConfig,
    run_gpu_next_day_probe,
)

# ---------------------------------------------------------------------------
# Config (exact same as Run G)
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

RUN_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260504T033857Z_074fe9ea")
FEATURE_CACHE_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_383b5a3c0e707ae9.parquet")
BUNDLE_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\realtime_model_bundles")


def main():
    print("=" * 70)
    print("EXPORT G MODEL BUNDLE + VALIDATION")
    print("=" * 70)

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

    # --- Patch feature names (same two-phase as G run) ---
    original_fn = gp._feature_names_for_config
    call_state = {"count": 0}
    def _two_phase(cfg):
        call_state["count"] += 1
        return original_fn(cfg) if call_state["count"] == 1 else custom_features
    gp._feature_names_for_config = _two_phase

    # --- Force feature cache hit on the original G run's cache ---
    # The source_code_hash changed since the G run, so the fingerprint won't match.
    # We force the descriptor to return the known-good cache file.
    original_cache_descriptor = gp._feature_cache_descriptor

    def _forced_cache_descriptor(store_arg, config_arg, *, symbols, context_symbols=None):
        descriptor = original_cache_descriptor(store_arg, config_arg, symbols=symbols, context_symbols=context_symbols)
        # Override with the original G run's cache
        forced_path = str(FEATURE_CACHE_PATH)
        forced_meta = str(FEATURE_CACHE_PATH.with_suffix(".json"))
        descriptor["hit"] = True
        descriptor["path"] = forced_path
        descriptor["metadata_path"] = forced_meta
        descriptor["fingerprint"] = "383b5a3c0e707ae9"
        # Load metadata
        import json as _json
        try:
            meta = _json.loads(Path(forced_meta).read_text(encoding="utf-8"))
            descriptor["rows"] = meta.get("rows")
            descriptor["symbol_frames_kept"] = meta.get("symbol_frames_kept")
            descriptor["created_at"] = meta.get("created_at")
            descriptor["factor_reports"] = meta.get("factor_reports") or []
        except Exception:
            pass
        print(f"  [FORCED CACHE HIT] Using: {forced_path}", file=sys.stderr)
        return descriptor

    gp._feature_cache_descriptor = _forced_cache_descriptor

    # --- Capture all model internals from _train_and_score ---
    captured = {}
    original_train_and_score = gp._train_and_score

    def _capturing_train_and_score(train_df, test_df, **kwargs):
        device = kwargs["device"]
        feature_names = kwargs["feature_names"]
        seed = kwargs["seed"]

        # We need mean/std and selected_indices from inside.
        # Replicate the pre-processing to capture them.
        fit_frame, valid_frame, split_info = gp._purged_train_validation_split(
            train_df,
            validation_fraction=kwargs.get("validation_fraction", 0.15),
            embargo_label_days=kwargs.get("embargo_label_days", 5),
            max_fit_rows=kwargs.get("max_fit_rows", 300_000),
            seed=seed,
        )
        x_train_raw = torch.as_tensor(
            fit_frame.loc[:, feature_names].to_numpy(dtype=np.float32), device=device
        )
        mean = x_train_raw.mean(dim=0, keepdim=True)
        std = torch.clamp(x_train_raw.std(dim=0, keepdim=True), min=1e-6)

        captured["mean"] = mean.cpu()
        captured["std"] = std.cpu()
        captured["full_feature_names"] = feature_names
        captured["fit_rows"] = len(fit_frame)
        captured["valid_rows"] = len(valid_frame)

        # Run original _train_and_score
        result = original_train_and_score(train_df, test_df, **kwargs)

        # Extract feature selection info
        fs = result.get("feature_selection", {})
        selected_features = fs.get("selected_features", list(feature_names))
        captured["selected_feature_names"] = tuple(selected_features)

        # Compute selected_indices
        name_to_idx = {name: i for i, name in enumerate(feature_names)}
        captured["selected_indices"] = [name_to_idx[n] for n in selected_features if n in name_to_idx]

        # The result dict contains the best candidate, but we need the ensemble members
        # We'll capture them via another hook on _build_average_ensemble_candidate
        return result

    gp._train_and_score = _capturing_train_and_score

    # --- Capture ensemble members ---
    original_build_ensemble = gp._build_average_ensemble_candidate

    def _capturing_build_ensemble(candidates, valid_y, **kwargs):
        result = original_build_ensemble(candidates, valid_y, **kwargs)
        if result:
            captured["ensemble_members"] = result.get("members", [])
            captured["ensemble_threshold"] = result.get("threshold", 0.5)
            captured["ensemble_confidence_band"] = result.get("confidence_band", {})
            captured["ensemble_score"] = result.get("selection_score", 0.0)
            captured["member_names"] = result.get("member_models", [])
            captured["all_candidates"] = candidates
        return result
    gp._build_average_ensemble_candidate = _capturing_build_ensemble

    # --- Capture isotonic calibration ---
    original_fit_isotonic = gp._fit_isotonic_calibration
    iso_fits = []

    def _capturing_fit_isotonic(prob, y):
        iso = original_fit_isotonic(prob, y)
        iso_fits.append(iso)
        return iso
    gp._fit_isotonic_calibration = _capturing_fit_isotonic

    # --- Capture the brier comparison that determines calibration_used ---
    original_brier = gp._brier
    brier_calls = []

    def _tracking_brier(prob, y):
        result = original_brier(prob, y)
        brier_calls.append(float(result))
        return result
    gp._brier = _tracking_brier

    # --- Run the pipeline ---
    print("\nRunning pipeline to capture model (same config/seed as G run)...")
    t0 = time.perf_counter()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.perf_counter() - t0
    print(f"Pipeline completed in {elapsed:.1f}s, status={result.get('status')}")

    # Restore patches
    gp._feature_names_for_config = original_fn
    gp._feature_cache_descriptor = original_cache_descriptor
    gp._train_and_score = original_train_and_score
    gp._build_average_ensemble_candidate = original_build_ensemble
    gp._fit_isotonic_calibration = original_fit_isotonic
    gp._brier = original_brier

    if result.get("status") != "completed":
        print(f"ERROR: Pipeline did not complete: {result.get('status')}")
        return 1

    # --- Determine calibration_used ---
    # The pipeline fits isotonic on ensemble valid_prob, then checks if brier improves.
    # From the brier calls, the last comparison before test prediction decides this.
    # The iso model is the LAST one fit (for the ensemble).
    iso_model = iso_fits[-1] if iso_fits else None
    # Check if isotonic was used by looking at the result
    calibration_used = result.get("result", {}).get("calibration", "platt")
    post_cal = result.get("result", {}).get("post_calibration", {})
    if post_cal.get("method") == "isotonic":
        calibration_used = "isotonic"
    elif post_cal.get("improved") is True:
        calibration_used = "isotonic"
    print(f"\nCalibration used: {calibration_used}")
    print(f"Isotonic models fit: {len(iso_fits)}")
    print(f"Brier calls: {len(brier_calls)}")

    # --- Verify we got the ensemble ---
    members = captured.get("ensemble_members", [])
    print(f"\nEnsemble members captured: {len(members)}")
    for m in members:
        print(f"  - {m.get('model_name')}: kind={m.get('model_kind')}, "
              f"score={m.get('selection_score', 0):.4f}, "
              f"cal={m.get('calibration', {})}")

    if len(members) < 2:
        print("ERROR: Failed to capture ensemble members!")
        return 1

    # --- Build and save bundle ---
    print("\nBuilding model bundle...")

    run_id = result.get("run_id", "unknown")
    bundle_id = f"bundle_G_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    # Serialize member models
    members_serialized = []
    for member in members:
        model_kind = member.get("model_kind", "torch")
        model_obj = member.get("model")
        m_info = {
            "model_name": member.get("model_name", ""),
            "model_kind": model_kind,
            "calibration": member.get("calibration", {"scale": 1.0, "bias": 0.0}),
            "threshold": member.get("threshold", 0.5),
            "selection_score": member.get("selection_score", 0.0),
        }
        if model_kind == "torch" and model_obj is not None:
            buf = io.BytesIO()
            torch.save(model_obj.state_dict(), buf)
            m_info["state_dict_bytes"] = buf.getvalue()
            m_info["model_class"] = type(model_obj).__name__
            # Get input dimension from first layer
            sd = model_obj.state_dict()
            first_key = next(iter(sd))
            m_info["input_dim"] = int(sd[first_key].shape[1]) if len(sd[first_key].shape) > 1 else int(sd[first_key].shape[0])
            m_info["architecture"] = str(model_obj)
        elif model_kind in ("xgboost", "lightgbm", "catboost") and model_obj is not None:
            buf = io.BytesIO()
            pickle.dump(model_obj, buf)
            m_info["model_bytes"] = buf.getvalue()
        members_serialized.append(m_info)

    # Serialize isotonic model
    iso_bytes = None
    if iso_model is not None:
        buf = io.BytesIO()
        pickle.dump(iso_model, buf)
        iso_bytes = buf.getvalue()

    # Build metadata
    selected_indices_tensor = torch.tensor(captured.get("selected_indices", []), dtype=torch.long)

    bundle = {
        "bundle_id": bundle_id,
        "source_run_id": run_id,
        "original_run_id": "gpu_probe_20260504T033857Z_074fe9ea",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_name": "stacking_average_top3",
        "model_kind": "ensemble_average",
        "member_count": len(members_serialized),
        "member_names": [m["model_name"] for m in members_serialized],
        "selected_feature_names": list(captured.get("selected_feature_names", [])),
        "selected_feature_count": len(captured.get("selected_feature_names", [])),
        "full_feature_names": list(captured.get("full_feature_names", [])),
        "threshold": captured.get("ensemble_threshold", 0.5),
        "confidence_band": captured.get("ensemble_confidence_band", {}),
        "calibration_used": calibration_used,
        "config": {
            "train_end": "2025-12-31",
            "test_start": "2026-01-01",
            "end": "2026-04-30",
            "seed": 42,
            "feature_set": "research",
            "label_target": "next_high_from_close",
            "target_high_return_pct": 1.0,
            "max_selected_features": 260,
            "feature_selection_method": "stable_tail",
            "min_phase_days_3": 1,
            "exclude_event_limit_up": True,
            "candidate_family": "all",
            "used_factor_ids": ["C009", "C004"],
            "extra_features": list(TIER1_PLUS_C009_C004),
        },
    }

    # Save bundle
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    bundle_path = BUNDLE_DIR / f"{bundle_id}.pt"

    save_payload = {
        "metadata": bundle,
        "mean": captured["mean"],
        "std": captured["std"],
        "selected_indices": selected_indices_tensor,
        "members": members_serialized,
        "iso_model_bytes": iso_bytes,
        "calibration_used": calibration_used,
    }

    torch.save(save_payload, str(bundle_path))
    bundle_size_mb = bundle_path.stat().st_size / 1024 / 1024

    # Save metadata JSON
    meta_path = BUNDLE_DIR / f"{bundle_id}_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"BUNDLE SAVED")
    print(f"{'='*70}")
    print(f"  Bundle ID: {bundle_id}")
    print(f"  Source run: {run_id}")
    print(f"  Original G run: gpu_probe_20260504T033857Z_074fe9ea")
    print(f"  Path: {bundle_path}")
    print(f"  Size: {bundle_size_mb:.1f} MB")
    print(f"  Members: {bundle['member_names']}")
    print(f"  Selected features: {bundle['selected_feature_count']}")
    print(f"  Threshold: {bundle['threshold']:.4f}")
    print(f"  Calibration: {calibration_used}")
    print(f"  Meta JSON: {meta_path}")

    # =====================================================================
    # VALIDATION: Reproduce test_predictions from bundle
    # =====================================================================
    print(f"\n{'='*70}")
    print("VALIDATION: Reproducing test_predictions from bundle")
    print(f"{'='*70}")

    # Load the original test predictions
    orig_preds = pd.read_parquet(RUN_DIR / "test_predictions.parquet")
    orig_preds["date"] = pd.to_datetime(orig_preds["date"])
    print(f"  Original predictions: {len(orig_preds)} rows")

    # Load feature cache
    print("  Loading feature cache...")
    feature_cache = pd.read_parquet(FEATURE_CACHE_PATH)
    feature_cache["date"] = pd.to_datetime(feature_cache["date"])

    # Filter to test period
    test_data = feature_cache[feature_cache["date"] >= pd.Timestamp("2026-01-01")].copy()
    print(f"  Feature cache test rows: {len(test_data)}")

    # Prepare features
    full_feature_names = list(captured["full_feature_names"])
    selected_feature_names = list(captured["selected_feature_names"])
    selected_idx = captured["selected_indices"]

    # Get raw feature matrix for test data
    X_raw = test_data[full_feature_names].to_numpy(dtype=np.float32)
    X_raw = np.nan_to_num(X_raw, nan=0.0)

    # Normalize
    mean_np = captured["mean"].numpy().flatten()
    std_np = captured["std"].numpy().flatten()
    X_norm = (X_raw - mean_np) / std_np

    # Select features
    X_selected = X_norm[:, selected_idx]

    # Predict with each member
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x_tensor = torch.as_tensor(X_selected, dtype=torch.float32, device=device)

    member_probs = []
    for m_info in members_serialized:
        model_kind = m_info["model_kind"]
        if model_kind == "torch":
            # Reconstruct model
            model_class = m_info["model_class"]
            input_dim = m_info["input_dim"]
            # Create model instance
            if model_class == "_TorchLogistic":
                model_obj = gp._TorchLogistic(input_dim).to(device)
            elif model_class == "_TorchMlp":
                # Parse architecture from string to get hidden dims
                arch = m_info.get("architecture", "")
                sd = torch.load(io.BytesIO(m_info["state_dict_bytes"]), weights_only=True)
                # Infer hidden sizes from state dict
                hidden_sizes = []
                layer_idx = 0
                while f"layers.{layer_idx}.weight" in sd:
                    hidden_sizes.append(sd[f"layers.{layer_idx}.weight"].shape[0])
                    layer_idx += 1
                # Last layer is output (1), hidden = all except last
                if hidden_sizes:
                    hidden_sizes = hidden_sizes[:-1]
                model_obj = gp._TorchMlp(input_dim, hidden=tuple(hidden_sizes)).to(device)
            elif model_class == "_TorchResidualMlp":
                sd = torch.load(io.BytesIO(m_info["state_dict_bytes"]), weights_only=True)
                # Infer hidden size from first layer
                hidden = sd["layers.0.weight"].shape[0]
                model_obj = gp._TorchResidualMlp(input_dim, hidden=hidden).to(device)
            else:
                raise ValueError(f"Unknown model class: {model_class}")

            # Load state dict
            sd = torch.load(io.BytesIO(m_info["state_dict_bytes"]), weights_only=True)
            model_obj.load_state_dict(sd)
            model_obj.eval()

            # Predict
            with torch.no_grad():
                logits = model_obj(x_tensor).flatten()
                cal = m_info["calibration"]
                prob = torch.sigmoid(logits * cal["scale"] + cal["bias"])
            member_probs.append(prob)

        elif model_kind in ("xgboost", "lightgbm", "catboost"):
            model_obj = pickle.loads(m_info["model_bytes"])
            prob_np = model_obj.predict_proba(X_selected)[:, 1]
            prob = torch.as_tensor(prob_np, dtype=torch.float32, device=device)
            member_probs.append(prob)

    # Average ensemble
    ensemble_prob = torch.stack(member_probs, dim=0).mean(dim=0)

    # Apply isotonic if used
    if calibration_used == "isotonic" and iso_bytes is not None:
        iso = pickle.loads(iso_bytes)
        prob_np = ensemble_prob.cpu().numpy().astype(float).ravel()
        calibrated = iso.predict(prob_np)
        final_prob = torch.as_tensor(calibrated, dtype=torch.float32)
    else:
        final_prob = ensemble_prob.cpu()

    # Build prediction dataframe
    bundle_preds = pd.DataFrame({
        "symbol": test_data["symbol"].values,
        "date": test_data["date"].values,
        "prob_bundle": final_prob.numpy(),
    })

    # Merge with original predictions
    comparison = orig_preds.merge(bundle_preds, on=["symbol", "date"], how="inner")
    print(f"\n  Matched rows: {len(comparison)}/{len(orig_preds)}")

    if len(comparison) == 0:
        print("  ERROR: No matched rows! Check date/symbol alignment.")
        return 1

    # Compute metrics
    diff = comparison["prob_bundle"] - comparison["probability"]
    abs_diff = diff.abs()

    print(f"\n  --- Probability Comparison ---")
    print(f"  mean_abs_diff:   {abs_diff.mean():.8f}")
    print(f"  max_abs_diff:    {abs_diff.max():.8f}")
    print(f"  median_abs_diff: {abs_diff.median():.8f}")
    print(f"  P95_abs_diff:    {abs_diff.quantile(0.95):.8f}")
    print(f"  P99_abs_diff:    {abs_diff.quantile(0.99):.8f}")
    print(f"  Pearson corr:    {comparison['probability'].corr(comparison['prob_bundle']):.8f}")
    print(f"  Spearman corr:   {comparison['probability'].corr(comparison['prob_bundle'], method='spearman'):.8f}")

    # Top-N overlap
    print(f"\n  --- Top-N Overlap ---")
    for n in [30, 50, 100]:
        top_orig = set(comparison.nlargest(n, "probability").index)
        top_bundle = set(comparison.nlargest(n, "prob_bundle").index)
        overlap = len(top_orig & top_bundle) / n
        print(f"  Top{n}: {overlap*100:.1f}%")

    # Threshold overlap
    print(f"\n  --- Threshold Overlap ---")
    for thresh in [0.70, 0.75, 0.80]:
        orig_set = set(comparison[comparison["probability"] >= thresh].index)
        bundle_set = set(comparison[comparison["prob_bundle"] >= thresh].index)
        if orig_set:
            recall = len(orig_set & bundle_set) / len(orig_set)
            jaccard = len(orig_set & bundle_set) / len(orig_set | bundle_set) if (orig_set | bundle_set) else 0
            print(f"  T>={thresh}: orig={len(orig_set)}, bundle={len(bundle_set)}, "
                  f"recall={recall*100:.1f}%, jaccard={jaccard*100:.1f}%")

    # Diagnose if not matching
    if abs_diff.max() > 0.01:
        print(f"\n  --- WARNING: max_abs_diff > 0.01, diagnosing ---")
        comparison["abs_diff"] = abs_diff
        worst = comparison.nlargest(10, "abs_diff")
        print(worst[["symbol", "date", "probability", "prob_bundle", "abs_diff"]].to_string())

    # Verdict
    print(f"\n{'='*70}")
    if abs_diff.max() < 1e-4:
        print("VERDICT: EXACT MATCH (max diff < 0.0001)")
    elif abs_diff.max() < 0.001:
        print("VERDICT: NEAR-EXACT MATCH (max diff < 0.001)")
    elif abs_diff.max() < 0.01:
        print("VERDICT: CLOSE MATCH (max diff < 0.01) - acceptable for inference")
    else:
        print(f"VERDICT: MISMATCH (max diff = {abs_diff.max():.6f}) - INVESTIGATE")
    print(f"{'='*70}")

    # Save validation report data
    validation = {
        "bundle_id": bundle_id,
        "bundle_path": str(bundle_path),
        "original_run": "gpu_probe_20260504T033857Z_074fe9ea",
        "matched_rows": len(comparison),
        "total_original_rows": len(orig_preds),
        "mean_abs_diff": float(abs_diff.mean()),
        "max_abs_diff": float(abs_diff.max()),
        "median_abs_diff": float(abs_diff.median()),
        "p95_abs_diff": float(abs_diff.quantile(0.95)),
        "p99_abs_diff": float(abs_diff.quantile(0.99)),
        "pearson_corr": float(comparison["probability"].corr(comparison["prob_bundle"])),
        "spearman_corr": float(comparison["probability"].corr(comparison["prob_bundle"], method="spearman")),
        "members": bundle["member_names"],
        "calibration_used": calibration_used,
        "threshold": bundle["threshold"],
    }

    val_path = BUNDLE_DIR / f"{bundle_id}_validation.json"
    with open(val_path, "w") as f:
        json.dump(validation, f, indent=2)
    print(f"\n  Validation saved: {val_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
