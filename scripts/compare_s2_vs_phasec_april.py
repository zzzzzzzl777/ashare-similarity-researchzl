"""
S2 vs Phase C: Fair April Holdout Comparison.

Both models scored on the EXACT same April 2026 rows from the same feature cache.
No retraining. Frozen inference only.

S2 (a0ec8105): 693 pool / 260 selected, CatBoost expressive, threshold=0.55
Phase C (12605e2b): 673 pool / 200 selected, CatBoost expressive, threshold=0.53
"""
import json
import math
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch

sys.path.insert(0, str(Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")))

S2_BUNDLE = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260509T002433Z_a0ec8105\model_bundle.pt"
)
PHASEC_BUNDLE = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt"
)
FEATURE_CACHE = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_31ffa0367a4d893f.parquet"
)
OUTPUT_JSON = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction"
    r"\s2_vs_phasec_april_comparison.json"
)
OUTPUT_CSV = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction"
    r"\s2_vs_phasec_april_predictions.csv"
)

META_COLS = [
    "symbol", "date", "close", "actual",
    "limit_up_like", "short_phase_days_3",
]


def wilson(n, p):
    if n == 0 or p == 0:
        return 0.0
    z = 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin) / denom


def load_bundle(path):
    bundle = torch.load(str(path), map_location="cpu", weights_only=False)
    members = [pickle.loads(m["model_bytes"]) for m in bundle["members"]]
    iso_model = pickle.loads(bundle["iso_model_bytes"]) if bundle.get("iso_model_bytes") else None
    return {
        "members": members,
        "mean": bundle["mean"],
        "std": bundle["std"],
        "selected_indices": bundle["selected_indices"],
        "feature_names": list(bundle["feature_names"]),
        "selected_feature_names": list(bundle.get("selected_feature_names", ())),
        "iso_model": iso_model,
        "calibration_used": bundle["calibration_used"],
        "threshold": float(bundle["threshold"]),
        "model_name": bundle.get("model_name", "unknown"),
    }


def run_inference(bundle, april_df):
    feature_names = bundle["feature_names"]
    raw = np.zeros((len(april_df), len(feature_names)), dtype=np.float32)
    for i, fname in enumerate(feature_names):
        if fname in april_df.columns:
            raw[:, i] = april_df[fname].fillna(0).values.astype(np.float32)

    x = torch.as_tensor(raw, dtype=torch.float32)
    std = bundle["std"].clone()
    std[std == 0] = 1.0
    x = (x - bundle["mean"]) / std
    if bundle["selected_indices"] is not None:
        x = x[:, bundle["selected_indices"]]
    x_np = x.numpy()

    probs = np.stack(
        [m.predict_proba(x_np)[:, 1].astype(np.float32) for m in bundle["members"]],
        axis=0,
    )
    raw_prob = probs.mean(axis=0)

    if bundle["calibration_used"] == "isotonic" and bundle["iso_model"] is not None:
        cal_prob = bundle["iso_model"].predict(raw_prob.astype(np.float64)).astype(np.float32)
    else:
        cal_prob = raw_prob.copy()

    return raw_prob, cal_prob


def evaluate_at_threshold(prob, actual, threshold):
    mask = prob >= threshold
    n = int(mask.sum())
    if n == 0:
        return {"threshold": threshold, "count": 0, "accuracy": 0.0, "wilson_95": 0.0, "coverage": 0.0}
    acc = float(actual[mask].mean())
    w95 = wilson(n, acc)
    return {
        "threshold": threshold,
        "count": n,
        "accuracy": round(acc, 6),
        "wilson_95": round(w95, 6),
        "coverage": round(n / len(actual), 6),
    }


def evaluate_topk(prob, actual, dates, k):
    df_tmp = pd.DataFrame({"prob": prob, "actual": actual, "date": dates})
    selected = df_tmp.groupby("date").apply(
        lambda g: g.nlargest(k, "prob"), include_groups=False
    ).reset_index(drop=True)
    if len(selected) == 0:
        return {"k": k, "count": 0, "accuracy": 0.0, "wilson_95": 0.0}
    acc = float(selected["actual"].mean())
    n = len(selected)
    w95 = wilson(n, acc)
    return {"k": k, "count": n, "accuracy": round(acc, 6), "wilson_95": round(w95, 6)}


def main():
    print("=" * 70)
    print("S2 vs Phase C: FAIR APRIL COMPARISON (Frozen Inference)")
    print("=" * 70)

    # Load bundles
    print("\n--- Loading bundles ---")
    t0 = time.time()
    s2 = load_bundle(S2_BUNDLE)
    phasec = load_bundle(PHASEC_BUNDLE)
    print(f"  S2:     {s2['model_name']}, {len(s2['feature_names'])} pool, "
          f"{len(s2['selected_feature_names'])} selected, threshold={s2['threshold']}")
    print(f"  PhaseC: {phasec['model_name']}, {len(phasec['feature_names'])} pool, "
          f"{len(phasec['selected_feature_names'])} selected, threshold={phasec['threshold']}")
    print(f"  Load time: {time.time()-t0:.1f}s")

    # Load April data
    print("\n--- Loading April feature data ---")
    all_features = set(s2["feature_names"]) | set(phasec["feature_names"]) | set(META_COLS)
    schema_cols = set(pq.read_schema(str(FEATURE_CACHE)).names)
    cols_to_load = [c for c in all_features if c in schema_cols]
    missing_s2 = [f for f in s2["feature_names"] if f not in schema_cols]
    missing_pc = [f for f in phasec["feature_names"] if f not in schema_cols]
    if missing_s2:
        print(f"  WARNING: {len(missing_s2)} S2 features missing from cache")
    if missing_pc:
        print(f"  WARNING: {len(missing_pc)} PhaseC features missing from cache")

    data = pd.read_parquet(str(FEATURE_CACHE), columns=cols_to_load)
    april = data[(data["date"] >= "2026-04-01") & (data["date"] <= "2026-04-30")].copy()
    april = april[april["limit_up_like"] != 1]
    april = april[april["short_phase_days_3"] >= 1]
    print(f"  April rows: {len(april)}")
    print(f"  Unique dates: {april['date'].nunique()}")
    print(f"  Positive rate: {april['actual'].mean():.4f}")

    # Run inference
    print("\n--- Running frozen inference ---")
    t0 = time.time()
    s2_raw, s2_cal = run_inference(s2, april)
    t1 = time.time()
    pc_raw, pc_cal = run_inference(phasec, april)
    t2 = time.time()
    print(f"  S2 inference: {t1-t0:.2f}s")
    print(f"  PhaseC inference: {t2-t1:.2f}s")

    actual = april["actual"].values
    dates = april["date"].values

    # Evaluate at multiple thresholds
    print("\n" + "=" * 70)
    print("RESULTS: CALIBRATED PROBABILITY (isotonic)")
    print("=" * 70)
    thresholds = [0.50, 0.53, 0.55, 0.70, 0.75, 0.78, 0.80, 0.85]

    print(f"\n{'Threshold':<12}{'--- S2 ---':<35}{'--- PhaseC ---':<35}")
    print(f"{'':12}{'N':>6} {'Acc':>7} {'W95':>7} {'Cov':>7}   {'N':>6} {'Acc':>7} {'W95':>7} {'Cov':>7}")
    print("-" * 82)

    s2_results = []
    pc_results = []
    for t in thresholds:
        s2_r = evaluate_at_threshold(s2_cal, actual, t)
        pc_r = evaluate_at_threshold(pc_cal, actual, t)
        s2_results.append(s2_r)
        pc_results.append(pc_r)
        s2_mark = " *" if s2_r["wilson_95"] >= 0.75 else ""
        pc_mark = " *" if pc_r["wilson_95"] >= 0.75 else ""
        print(f"  p>={t:<5.2f} {s2_r['count']:>6} {s2_r['accuracy']:>7.4f} {s2_r['wilson_95']:>7.4f} "
              f"{s2_r['coverage']:>7.4f}{s2_mark}  {pc_r['count']:>6} {pc_r['accuracy']:>7.4f} "
              f"{pc_r['wilson_95']:>7.4f} {pc_r['coverage']:>7.4f}{pc_mark}")

    # TopK comparison
    print(f"\n{'TopK':<12}{'--- S2 ---':<35}{'--- PhaseC ---':<35}")
    print(f"{'':12}{'N':>6} {'Acc':>7} {'W95':>7}           {'N':>6} {'Acc':>7} {'W95':>7}")
    print("-" * 72)

    s2_topk = []
    pc_topk = []
    for k in [3, 5, 6, 10, 15, 20]:
        s2_tk = evaluate_topk(s2_cal, actual, dates, k)
        pc_tk = evaluate_topk(pc_cal, actual, dates, k)
        s2_topk.append(s2_tk)
        pc_topk.append(pc_tk)
        print(f"  top{k:<6} {s2_tk['count']:>6} {s2_tk['accuracy']:>7.4f} {s2_tk['wilson_95']:>7.4f}"
              f"           {pc_tk['count']:>6} {pc_tk['accuracy']:>7.4f} {pc_tk['wilson_95']:>7.4f}")

    # Raw probability comparison
    print(f"\n{'='*70}")
    print("RESULTS: RAW PROBABILITY (no isotonic)")
    print("=" * 70)
    print(f"\n{'Threshold':<12}{'--- S2 ---':<35}{'--- PhaseC ---':<35}")
    print(f"{'':12}{'N':>6} {'Acc':>7} {'W95':>7} {'Cov':>7}   {'N':>6} {'Acc':>7} {'W95':>7} {'Cov':>7}")
    print("-" * 82)

    s2_raw_results = []
    pc_raw_results = []
    for t in thresholds:
        s2_r = evaluate_at_threshold(s2_raw, actual, t)
        pc_r = evaluate_at_threshold(pc_raw, actual, t)
        s2_raw_results.append(s2_r)
        pc_raw_results.append(pc_r)
        print(f"  p>={t:<5.2f} {s2_r['count']:>6} {s2_r['accuracy']:>7.4f} {s2_r['wilson_95']:>7.4f} "
              f"{s2_r['coverage']:>7.4f}   {pc_r['count']:>6} {pc_r['accuracy']:>7.4f} "
              f"{pc_r['wilson_95']:>7.4f} {pc_r['coverage']:>7.4f}")

    # Daily breakdown at p>=0.75 (calibrated)
    print(f"\n{'='*70}")
    print("DAILY BREAKDOWN (calibrated p>=0.75)")
    print("=" * 70)
    print(f"\n{'Date':<12} {'S2_N':>5} {'S2_Acc':>7} {'PC_N':>5} {'PC_Acc':>7} {'S2>PC':>6}")
    print("-" * 55)

    df_daily = pd.DataFrame({
        "date": dates, "actual": actual, "s2_prob": s2_cal, "pc_prob": pc_cal
    })
    daily_stats = []
    for d, grp in df_daily.groupby("date"):
        s2_hc = grp[grp["s2_prob"] >= 0.75]
        pc_hc = grp[grp["pc_prob"] >= 0.75]
        s2_n = len(s2_hc)
        pc_n = len(pc_hc)
        s2_acc = s2_hc["actual"].mean() if s2_n > 0 else float("nan")
        pc_acc = pc_hc["actual"].mean() if pc_n > 0 else float("nan")
        winner = "S2" if s2_acc > pc_acc else ("PC" if pc_acc > s2_acc else "tie")
        daily_stats.append({"date": str(d), "s2_n": s2_n, "s2_acc": s2_acc, "pc_n": pc_n, "pc_acc": pc_acc})
        print(f"  {str(d)[:10]:<12}{s2_n:>5} {s2_acc:>7.3f}  {pc_n:>5} {pc_acc:>7.3f}  {winner:>6}")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print("=" * 70)
    s2_75 = evaluate_at_threshold(s2_cal, actual, 0.75)
    pc_75 = evaluate_at_threshold(pc_cal, actual, 0.75)
    print(f"\n  At p>=0.75 (calibrated):")
    print(f"    S2:     N={s2_75['count']:>5}, Acc={s2_75['accuracy']:.4f}, W95={s2_75['wilson_95']:.4f}, Cov={s2_75['coverage']:.4f}")
    print(f"    PhaseC: N={pc_75['count']:>5}, Acc={pc_75['accuracy']:.4f}, W95={pc_75['wilson_95']:.4f}, Cov={pc_75['coverage']:.4f}")
    diff_acc = s2_75["accuracy"] - pc_75["accuracy"]
    diff_w95 = s2_75["wilson_95"] - pc_75["wilson_95"]
    print(f"    Delta:  Acc {diff_acc:+.4f}, W95 {diff_w95:+.4f} ({'S2 wins' if diff_w95 > 0 else 'PhaseC wins'})")

    # Save predictions CSV
    pred_df = pd.DataFrame({
        "symbol": april["symbol"].values,
        "date": april["date"].values,
        "close": april["close"].values if "close" in april.columns else np.nan,
        "actual": actual,
        "s2_raw_prob": s2_raw,
        "s2_cal_prob": s2_cal,
        "phasec_raw_prob": pc_raw,
        "phasec_cal_prob": pc_cal,
    })
    pred_df.to_csv(str(OUTPUT_CSV), index=False)
    print(f"\n  Predictions CSV: {OUTPUT_CSV}")

    # Save JSON
    output = {
        "generated_at": datetime.now().isoformat(),
        "methodology": "frozen bundle inference, same April rows, same feature cache",
        "feature_cache": str(FEATURE_CACHE),
        "april_rows": len(april),
        "april_dates": int(april["date"].nunique()),
        "april_positive_rate": round(float(actual.mean()), 4),
        "bundles": {
            "s2": {
                "path": str(S2_BUNDLE),
                "model": s2["model_name"],
                "pool_features": len(s2["feature_names"]),
                "selected_features": len(s2["selected_feature_names"]),
                "threshold": s2["threshold"],
                "calibration": s2["calibration_used"],
            },
            "phasec": {
                "path": str(PHASEC_BUNDLE),
                "model": phasec["model_name"],
                "pool_features": len(phasec["feature_names"]),
                "selected_features": len(phasec["selected_feature_names"]),
                "threshold": phasec["threshold"],
                "calibration": phasec["calibration_used"],
            },
        },
        "calibrated_threshold_results": {"s2": s2_results, "phasec": pc_results},
        "raw_threshold_results": {"s2": s2_raw_results, "phasec": pc_raw_results},
        "topk_results": {"s2": s2_topk, "phasec": pc_topk},
        "daily_breakdown_p075": daily_stats,
    }
    with open(str(OUTPUT_JSON), "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"  JSON: {OUTPUT_JSON}")
    print("\nDone.")


if __name__ == "__main__":
    main()
