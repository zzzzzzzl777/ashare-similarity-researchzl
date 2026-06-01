"""Self-validate: load saved bundle and compare against its OWN run's predictions.

This proves the export/inference pipeline is correct by matching the bundle
against gpu_probe_20260505T103527Z_bbfe605e (the run that produced the bundle).
"""
import io
import json
import pickle
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import numpy as np
import pandas as pd
import torch

import ashare_similarity.prediction.gpu_probe as gp

BUNDLE_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\realtime_model_bundles\bundle_G_20260505T103527Z.pt")
FEATURE_CACHE_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_383b5a3c0e707ae9.parquet")
SELF_RUN_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260505T103527Z_bbfe605e")
ORIG_RUN_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260504T033857Z_074fe9ea")


def load_bundle(path):
    payload = torch.load(str(path), weights_only=False)
    return payload


def predict_from_bundle(payload, X_raw):
    """Run full inference pipeline from bundle on raw feature matrix."""
    mean_np = payload["mean"].numpy().flatten()
    std_np = payload["std"].numpy().flatten()
    selected_idx = payload["selected_indices"].numpy()

    X_norm = (X_raw - mean_np) / std_np
    X_selected = X_norm[:, selected_idx]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x_tensor = torch.as_tensor(X_selected, dtype=torch.float32, device=device)

    member_probs = []
    for m_info in payload["members"]:
        model_kind = m_info["model_kind"]
        if model_kind == "torch":
            model_class = m_info["model_class"]
            input_dim = m_info["input_dim"]
            sd = torch.load(io.BytesIO(m_info["state_dict_bytes"]), weights_only=True)

            if model_class == "_TorchLogistic":
                model_obj = gp._TorchLogistic(input_dim).to(device)
            elif model_class == "_TorchMlp":
                hidden_sizes = []
                layer_idx = 0
                while f"layers.{layer_idx}.weight" in sd:
                    hidden_sizes.append(sd[f"layers.{layer_idx}.weight"].shape[0])
                    layer_idx += 1
                if hidden_sizes:
                    hidden_sizes = hidden_sizes[:-1]
                model_obj = gp._TorchMlp(input_dim, hidden=tuple(hidden_sizes)).to(device)
            elif model_class == "_TorchResidualMlp":
                hidden = sd["layers.0.weight"].shape[0]
                model_obj = gp._TorchResidualMlp(input_dim, hidden=hidden).to(device)
            else:
                raise ValueError(f"Unknown model class: {model_class}")

            model_obj.load_state_dict(sd)
            model_obj.eval()

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

    ensemble_prob = torch.stack(member_probs, dim=0).mean(dim=0)

    calibration_used = payload.get("calibration_used", "platt")
    iso_bytes = payload.get("iso_model_bytes")

    if calibration_used == "isotonic" and iso_bytes is not None:
        iso = pickle.loads(iso_bytes)
        prob_np = ensemble_prob.cpu().numpy().astype(float).ravel()
        calibrated = iso.predict(prob_np)
        final_prob = calibrated
    else:
        final_prob = ensemble_prob.cpu().numpy()

    return final_prob


def compare_predictions(bundle_prob, ref_preds, test_data, label=""):
    """Compare bundle predictions against a reference prediction set."""
    bundle_df = pd.DataFrame({
        "symbol": test_data["symbol"].values,
        "date": test_data["date"].values,
        "prob_bundle": bundle_prob,
    })

    comparison = ref_preds.merge(bundle_df, on=["symbol", "date"], how="inner")
    print(f"\n  [{label}] Matched rows: {len(comparison)}/{len(ref_preds)}")

    if len(comparison) == 0:
        print("  ERROR: No matched rows!")
        return None

    diff = comparison["prob_bundle"] - comparison["probability"]
    abs_diff = diff.abs()

    print(f"  mean_abs_diff:   {abs_diff.mean():.10f}")
    print(f"  max_abs_diff:    {abs_diff.max():.10f}")
    print(f"  median_abs_diff: {abs_diff.median():.10f}")
    print(f"  P95_abs_diff:    {abs_diff.quantile(0.95):.10f}")
    print(f"  P99_abs_diff:    {abs_diff.quantile(0.99):.10f}")
    print(f"  Pearson corr:    {comparison['probability'].corr(comparison['prob_bundle']):.10f}")
    print(f"  Spearman corr:   {comparison['probability'].corr(comparison['prob_bundle'], method='spearman'):.10f}")

    # Top-N overlap
    print(f"\n  Top-N Overlap:")
    for n in [30, 50, 100]:
        if len(comparison) >= n:
            top_ref = set(comparison.nlargest(n, "probability").index)
            top_bundle = set(comparison.nlargest(n, "prob_bundle").index)
            overlap = len(top_ref & top_bundle) / n
            print(f"    Top{n}: {overlap*100:.1f}%")

    # Threshold overlap
    print(f"\n  Threshold Overlap:")
    for thresh in [0.70, 0.75, 0.80]:
        ref_set = set(comparison[comparison["probability"] >= thresh].index)
        bundle_set = set(comparison[comparison["prob_bundle"] >= thresh].index)
        if ref_set:
            recall = len(ref_set & bundle_set) / len(ref_set)
            jaccard = len(ref_set & bundle_set) / len(ref_set | bundle_set) if (ref_set | bundle_set) else 0
            print(f"    T>={thresh}: ref={len(ref_set)}, bundle={len(bundle_set)}, "
                  f"recall={recall*100:.1f}%, jaccard={jaccard*100:.1f}%")
        else:
            print(f"    T>={thresh}: 0 candidates in ref")

    # Per-member breakdown if available
    if abs_diff.max() > 0.01:
        print(f"\n  WARNING: max_abs_diff > 0.01")
        comparison["abs_diff"] = abs_diff
        worst = comparison.nlargest(10, "abs_diff")
        print(worst[["symbol", "date", "probability", "prob_bundle", "abs_diff"]].to_string())

    return {
        "matched_rows": len(comparison),
        "total_ref_rows": len(ref_preds),
        "mean_abs_diff": float(abs_diff.mean()),
        "max_abs_diff": float(abs_diff.max()),
        "median_abs_diff": float(abs_diff.median()),
        "p95_abs_diff": float(abs_diff.quantile(0.95)),
        "p99_abs_diff": float(abs_diff.quantile(0.99)),
        "pearson_corr": float(comparison["probability"].corr(comparison["prob_bundle"])),
        "spearman_corr": float(comparison["probability"].corr(comparison["prob_bundle"], method="spearman")),
    }


def main():
    print("=" * 70)
    print("SELF-VALIDATION: Bundle vs Its Own Run's Predictions")
    print("=" * 70)

    # Load bundle
    print("\nLoading bundle...")
    payload = load_bundle(BUNDLE_PATH)
    meta = payload["metadata"]
    print(f"  Bundle ID: {meta['bundle_id']}")
    print(f"  Source run: {meta['source_run_id']}")
    print(f"  Original G run: {meta['original_run_id']}")
    print(f"  Members: {meta['member_names']}")
    print(f"  Calibration: {payload['calibration_used']}")
    print(f"  Selected features: {meta['selected_feature_count']}")

    # Load feature cache
    print("\nLoading feature cache...")
    feature_cache = pd.read_parquet(FEATURE_CACHE_PATH)
    feature_cache["date"] = pd.to_datetime(feature_cache["date"])
    test_data = feature_cache[feature_cache["date"] >= pd.Timestamp("2026-01-01")].copy()
    print(f"  Test rows: {len(test_data)}")

    # Get raw features
    full_feature_names = meta["full_feature_names"]
    X_raw = test_data[full_feature_names].to_numpy(dtype=np.float32)
    X_raw = np.nan_to_num(X_raw, nan=0.0)

    # Run inference from bundle
    print("\nRunning bundle inference...")
    bundle_prob = predict_from_bundle(payload, X_raw)
    print(f"  Predictions: {len(bundle_prob)}")
    print(f"  Prob range: [{bundle_prob.min():.6f}, {bundle_prob.max():.6f}]")
    print(f"  Prob mean: {bundle_prob.mean():.6f}")

    # === SELF-VALIDATION: Compare with the run that produced this bundle ===
    print(f"\n{'='*70}")
    print("COMPARISON 1: Bundle vs Its Own Run (self-validation)")
    print(f"{'='*70}")
    self_preds = pd.read_parquet(SELF_RUN_DIR / "test_predictions.parquet")
    self_preds["date"] = pd.to_datetime(self_preds["date"])
    print(f"  Self-run predictions: {len(self_preds)} rows")
    self_result = compare_predictions(bundle_prob, self_preds, test_data, label="SELF")

    # === ORIGINAL G RUN: Compare for reference ===
    print(f"\n{'='*70}")
    print("COMPARISON 2: Bundle vs Original G Run (cross-version)")
    print(f"{'='*70}")
    orig_preds = pd.read_parquet(ORIG_RUN_DIR / "test_predictions.parquet")
    orig_preds["date"] = pd.to_datetime(orig_preds["date"])
    print(f"  Original G run predictions: {len(orig_preds)} rows")
    orig_result = compare_predictions(bundle_prob, orig_preds, test_data, label="ORIG")

    # === DIRECT COMPARISON: Self-run vs Original G run ===
    print(f"\n{'='*70}")
    print("COMPARISON 3: Self-Run vs Original G Run (run-to-run drift)")
    print(f"{'='*70}")
    run_compare = self_preds.merge(
        orig_preds[["symbol", "date", "probability"]].rename(columns={"probability": "prob_orig"}),
        on=["symbol", "date"], how="inner"
    )
    if len(run_compare) > 0:
        run_diff = (run_compare["probability"] - run_compare["prob_orig"]).abs()
        print(f"  Matched rows: {len(run_compare)}")
        print(f"  mean_abs_diff:   {run_diff.mean():.10f}")
        print(f"  max_abs_diff:    {run_diff.max():.10f}")
        print(f"  median_abs_diff: {run_diff.median():.10f}")
        print(f"  Pearson corr:    {run_compare['probability'].corr(run_compare['prob_orig']):.10f}")
        print(f"  Spearman corr:   {run_compare['probability'].corr(run_compare['prob_orig'], method='spearman'):.10f}")

        # Threshold overlap between runs
        print(f"\n  Threshold overlap (self-run vs original G):")
        for thresh in [0.70, 0.75, 0.80]:
            self_set = set(run_compare[run_compare["probability"] >= thresh].index)
            orig_set = set(run_compare[run_compare["prob_orig"] >= thresh].index)
            if orig_set:
                recall = len(orig_set & self_set) / len(orig_set)
                jaccard = len(orig_set & self_set) / len(orig_set | self_set) if (orig_set | self_set) else 0
                print(f"    T>={thresh}: orig={len(orig_set)}, self={len(self_set)}, "
                      f"recall={recall*100:.1f}%, jaccard={jaccard*100:.1f}%")

    # === Check original G run artifact for calibration info ===
    print(f"\n{'='*70}")
    print("DIAGNOSIS: Why don't the runs match?")
    print(f"{'='*70}")
    with open(ORIG_RUN_DIR / "artifact.json") as f:
        orig_artifact = json.load(f)
    with open(SELF_RUN_DIR / "artifact.json") as f:
        self_artifact = json.load(f)

    orig_post_cal = orig_artifact.get("result", {}).get("post_calibration", {})
    self_post_cal = self_artifact.get("result", {}).get("post_calibration", {})
    print(f"  Original G run post_calibration: {orig_post_cal.get('method', 'none')} "
          f"(improved={orig_post_cal.get('improved')})")
    print(f"  Self-run post_calibration: {self_post_cal.get('method', 'none')} "
          f"(improved={self_post_cal.get('improved')})")

    # Check ensemble info
    orig_best = orig_artifact.get("result", {}).get("best_candidate", {})
    self_best = self_artifact.get("result", {}).get("best_candidate", {})
    print(f"\n  Original G best candidate:")
    print(f"    model_name: {orig_best.get('model_name')}")
    print(f"    threshold: {orig_best.get('threshold')}")
    print(f"    selection_score: {orig_best.get('selection_score')}")

    print(f"\n  Self-run best candidate:")
    print(f"    model_name: {self_best.get('model_name')}")
    print(f"    threshold: {self_best.get('threshold')}")
    print(f"    selection_score: {self_best.get('selection_score')}")

    # Check feature selection
    orig_fs = orig_artifact.get("result", {}).get("feature_selection", {})
    self_fs = self_artifact.get("result", {}).get("feature_selection", {})
    orig_selected = set(orig_fs.get("selected_features", []))
    self_selected = set(self_fs.get("selected_features", []))
    shared = orig_selected & self_selected
    only_orig = orig_selected - self_selected
    only_self = self_selected - orig_selected
    print(f"\n  Feature selection comparison:")
    print(f"    Original: {len(orig_selected)} features")
    print(f"    Self-run: {len(self_selected)} features")
    print(f"    Shared: {len(shared)}")
    print(f"    Only in original: {len(only_orig)}: {sorted(only_orig)[:10]}")
    print(f"    Only in self-run: {len(only_self)}: {sorted(only_self)[:10]}")

    # === VERDICTS ===
    print(f"\n{'='*70}")
    print("VERDICTS")
    print(f"{'='*70}")

    if self_result:
        if self_result["max_abs_diff"] < 1e-4:
            print(f"  SELF-VALIDATION: PASS (exact match, max_diff={self_result['max_abs_diff']:.2e})")
        elif self_result["max_abs_diff"] < 0.001:
            print(f"  SELF-VALIDATION: PASS (near-exact, max_diff={self_result['max_abs_diff']:.2e})")
        elif self_result["max_abs_diff"] < 0.01:
            print(f"  SELF-VALIDATION: PASS (close, max_diff={self_result['max_abs_diff']:.6f})")
        else:
            print(f"  SELF-VALIDATION: FAIL (max_diff={self_result['max_abs_diff']:.6f})")

    if orig_result:
        if orig_result["max_abs_diff"] < 0.01:
            print(f"  ORIG-VALIDATION: PASS (close, max_diff={orig_result['max_abs_diff']:.6f})")
        else:
            print(f"  ORIG-VALIDATION: FAIL (max_diff={orig_result['max_abs_diff']:.6f})")
            print(f"    Root cause: code-version drift (calibration method differs: "
                  f"original={orig_post_cal.get('method')}, self={self_post_cal.get('method')})")

    # Save results
    output = {
        "bundle_id": meta["bundle_id"],
        "bundle_path": str(BUNDLE_PATH),
        "self_validation": self_result,
        "orig_validation": orig_result,
        "diagnosis": {
            "original_calibration": orig_post_cal.get("method", "none"),
            "self_calibration": self_post_cal.get("method", "none"),
            "feature_overlap": len(shared),
            "features_only_in_original": sorted(only_orig),
            "features_only_in_self": sorted(only_self),
        },
    }
    out_path = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\bundle_self_validation_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved: {out_path}")


if __name__ == "__main__":
    main()
