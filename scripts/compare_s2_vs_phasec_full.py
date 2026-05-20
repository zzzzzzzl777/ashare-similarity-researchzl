"""
S2 vs Phase C: Comprehensive Multi-Window Comparison.

Three time windows on frozen bundles, identical inference pipeline:
  1. 2023 Feb-Apr (pre-training OOS) — cache 64ba73ab
  2. 2026 Q1 (Jan-Mar, seen_research)  — cache 31ffa036
  3. 2026 April (seen_research)         — cache 31ffa036

Metrics: AUC-ROC, Average Precision, Brier, calibrated/raw thresholds, TopK, daily.
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
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

sys.path.insert(0, str(Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")))

S2_BUNDLE = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260509T002433Z_a0ec8105\model_bundle.pt"
)
PHASEC_BUNDLE = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt"
)
CACHE_MAIN = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_31ffa0367a4d893f.parquet"
)
CACHE_2023 = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_64ba73ab6db5f833.parquet"
)
OUTPUT_JSON = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction"
    r"\s2_vs_phasec_full_comparison.json"
)

META_COLS = ["symbol", "date", "close", "actual", "limit_up_like", "short_phase_days_3"]


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


def run_inference(bundle, df):
    feature_names = bundle["feature_names"]
    raw = np.zeros((len(df), len(feature_names)), dtype=np.float32)
    for i, fname in enumerate(feature_names):
        if fname in df.columns:
            raw[:, i] = df[fname].fillna(0).values.astype(np.float32)

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


def threshold_independent_metrics(raw_prob, cal_prob, actual):
    metrics = {}
    try:
        metrics["auc_roc_raw"] = round(float(roc_auc_score(actual, raw_prob)), 6)
    except ValueError:
        metrics["auc_roc_raw"] = None
    try:
        metrics["auc_roc_cal"] = round(float(roc_auc_score(actual, cal_prob)), 6)
    except ValueError:
        metrics["auc_roc_cal"] = None
    try:
        metrics["avg_precision_raw"] = round(float(average_precision_score(actual, raw_prob)), 6)
    except ValueError:
        metrics["avg_precision_raw"] = None
    try:
        metrics["avg_precision_cal"] = round(float(average_precision_score(actual, cal_prob)), 6)
    except ValueError:
        metrics["avg_precision_cal"] = None
    metrics["brier_raw"] = round(float(brier_score_loss(actual, raw_prob)), 6)
    metrics["brier_cal"] = round(float(brier_score_loss(actual, cal_prob)), 6)
    metrics["mean_raw_prob"] = round(float(raw_prob.mean()), 6)
    metrics["mean_cal_prob"] = round(float(cal_prob.mean()), 6)
    return metrics


def load_window(cache_path, date_start, date_end, all_features):
    schema_cols = set(pq.read_schema(str(cache_path)).names)
    cols_to_load = [c for c in all_features if c in schema_cols]
    data = pd.read_parquet(str(cache_path), columns=cols_to_load)
    window = data[(data["date"] >= date_start) & (data["date"] <= date_end)].copy()
    window = window[window["limit_up_like"] != 1]
    window = window[window["short_phase_days_3"] >= 1]
    return window


def evaluate_window(name, df, s2, phasec, thresholds, topk_list):
    print(f"\n{'#' * 80}")
    print(f"# WINDOW: {name}")
    print(f"# Rows: {len(df):,}  |  Dates: {df['date'].nunique()}  |  Pos rate: {df['actual'].mean():.4f}")
    print(f"{'#' * 80}")

    actual = df["actual"].values
    dates = df["date"].values

    t0 = time.time()
    s2_raw, s2_cal = run_inference(s2, df)
    t1 = time.time()
    pc_raw, pc_cal = run_inference(phasec, df)
    t2 = time.time()
    print(f"  Inference: S2 {t1-t0:.2f}s, PhaseC {t2-t1:.2f}s")

    # Threshold-independent
    s2_ti = threshold_independent_metrics(s2_raw, s2_cal, actual)
    pc_ti = threshold_independent_metrics(pc_raw, pc_cal, actual)

    print(f"\n  {'Metric':<22} {'S2':>10} {'PhaseC':>10} {'Delta':>10} {'Winner':>8}")
    print(f"  {'-'*62}")
    ti_names = [
        ("AUC-ROC (raw)", "auc_roc_raw"),
        ("AUC-ROC (cal)", "auc_roc_cal"),
        ("Avg Precision (raw)", "avg_precision_raw"),
        ("Avg Precision (cal)", "avg_precision_cal"),
        ("Brier (raw)", "brier_raw"),
        ("Brier (cal)", "brier_cal"),
    ]
    for label, key in ti_names:
        sv = s2_ti[key]
        pv = pc_ti[key]
        if sv is None or pv is None:
            print(f"  {label:<22} {'N/A':>10} {'N/A':>10}")
            continue
        delta = sv - pv
        if "brier" in key.lower():
            winner = "S2" if delta < 0 else "PhaseC"
        else:
            winner = "S2" if delta > 0 else "PhaseC"
        print(f"  {label:<22} {sv:>10.4f} {pv:>10.4f} {delta:>+10.4f} {winner:>8}")

    # Calibrated thresholds
    print(f"\n  CALIBRATED PROBABILITY")
    print(f"  {'Thresh':<8} {'S2_N':>6} {'S2_Acc':>7} {'S2_W95':>7} {'S2_Cov':>7}  "
          f"{'PC_N':>6} {'PC_Acc':>7} {'PC_W95':>7} {'PC_Cov':>7}  {'Win':>5}")
    print(f"  {'-'*82}")

    s2_cal_res = []
    pc_cal_res = []
    for t in thresholds:
        s2_r = evaluate_at_threshold(s2_cal, actual, t)
        pc_r = evaluate_at_threshold(pc_cal, actual, t)
        s2_cal_res.append(s2_r)
        pc_cal_res.append(pc_r)
        w = "S2" if s2_r["wilson_95"] > pc_r["wilson_95"] else "PC"
        print(f"  p>={t:<5.2f} {s2_r['count']:>6} {s2_r['accuracy']:>7.4f} {s2_r['wilson_95']:>7.4f} "
              f"{s2_r['coverage']:>7.4f}  {pc_r['count']:>6} {pc_r['accuracy']:>7.4f} "
              f"{pc_r['wilson_95']:>7.4f} {pc_r['coverage']:>7.4f}  {w:>5}")

    # Raw thresholds
    print(f"\n  RAW PROBABILITY")
    print(f"  {'Thresh':<8} {'S2_N':>6} {'S2_Acc':>7} {'S2_W95':>7} {'S2_Cov':>7}  "
          f"{'PC_N':>6} {'PC_Acc':>7} {'PC_W95':>7} {'PC_Cov':>7}  {'Win':>5}")
    print(f"  {'-'*82}")

    s2_raw_res = []
    pc_raw_res = []
    for t in thresholds:
        s2_r = evaluate_at_threshold(s2_raw, actual, t)
        pc_r = evaluate_at_threshold(pc_raw, actual, t)
        s2_raw_res.append(s2_r)
        pc_raw_res.append(pc_r)
        w = "S2" if s2_r["wilson_95"] > pc_r["wilson_95"] else "PC"
        print(f"  p>={t:<5.2f} {s2_r['count']:>6} {s2_r['accuracy']:>7.4f} {s2_r['wilson_95']:>7.4f} "
              f"{s2_r['coverage']:>7.4f}  {pc_r['count']:>6} {pc_r['accuracy']:>7.4f} "
              f"{pc_r['wilson_95']:>7.4f} {pc_r['coverage']:>7.4f}  {w:>5}")

    # TopK
    print(f"\n  TOPK (calibrated)")
    print(f"  {'K':<6} {'S2_N':>6} {'S2_Acc':>7} {'S2_W95':>7}  {'PC_N':>6} {'PC_Acc':>7} {'PC_W95':>7}  {'Win':>5}")
    print(f"  {'-'*60}")

    s2_topk = []
    pc_topk = []
    for k in topk_list:
        s2_tk = evaluate_topk(s2_cal, actual, dates, k)
        pc_tk = evaluate_topk(pc_cal, actual, dates, k)
        s2_topk.append(s2_tk)
        pc_topk.append(pc_tk)
        w = "S2" if s2_tk["wilson_95"] > pc_tk["wilson_95"] else "PC"
        print(f"  top{k:<4} {s2_tk['count']:>6} {s2_tk['accuracy']:>7.4f} {s2_tk['wilson_95']:>7.4f}  "
              f"{pc_tk['count']:>6} {pc_tk['accuracy']:>7.4f} {pc_tk['wilson_95']:>7.4f}  {w:>5}")

    return {
        "window": name,
        "rows": len(df),
        "dates": int(df["date"].nunique()),
        "positive_rate": round(float(actual.mean()), 4),
        "threshold_independent": {"s2": s2_ti, "phasec": pc_ti},
        "calibrated_threshold": {"s2": s2_cal_res, "phasec": pc_cal_res},
        "raw_threshold": {"s2": s2_raw_res, "phasec": pc_raw_res},
        "topk": {"s2": s2_topk, "phasec": pc_topk},
    }


def main():
    print("=" * 80)
    print("S2 vs Phase C: COMPREHENSIVE MULTI-WINDOW COMPARISON")
    print(f"Generated: {datetime.now().isoformat()}")
    print("=" * 80)

    # Load bundles
    print("\n--- Loading bundles ---")
    t0 = time.time()
    s2 = load_bundle(S2_BUNDLE)
    phasec = load_bundle(PHASEC_BUNDLE)
    print(f"  S2:     {s2['model_name']}, {len(s2['feature_names'])} pool / "
          f"{len(s2['selected_feature_names'])} selected, threshold={s2['threshold']}, cal={s2['calibration_used']}")
    print(f"  PhaseC: {phasec['model_name']}, {len(phasec['feature_names'])} pool / "
          f"{len(phasec['selected_feature_names'])} selected, threshold={phasec['threshold']}, cal={phasec['calibration_used']}")

    # Feature overlap
    s2_sel = set(s2["selected_feature_names"])
    pc_sel = set(phasec["selected_feature_names"])
    overlap = s2_sel & pc_sel
    s2_only = s2_sel - pc_sel
    pc_only = pc_sel - s2_sel
    print(f"\n  Feature overlap: {len(overlap)} shared, {len(s2_only)} S2-only, {len(pc_only)} PC-only")
    print(f"  PhaseC subset of S2: {pc_sel.issubset(s2_sel)} ({len(overlap)}/{len(pc_sel)})")
    print(f"  Load time: {time.time()-t0:.1f}s")

    all_features = set(s2["feature_names"]) | set(phasec["feature_names"]) | set(META_COLS)
    thresholds = [0.50, 0.53, 0.55, 0.60, 0.65, 0.70, 0.75, 0.78, 0.80, 0.85]
    topk_list = [3, 5, 6, 10, 15, 20]

    results = {}

    # Window 1: 2023 Feb-Apr (pre-training OOS)
    print("\n--- Loading 2023 Feb-Apr data ---")
    w1 = load_window(CACHE_2023, "2023-02-01", "2023-04-30", all_features)
    print(f"  Loaded {len(w1):,} rows")
    results["2023_feb_apr"] = evaluate_window("2023 Feb-Apr (Pre-Training OOS)", w1, s2, phasec, thresholds, topk_list)

    # Window 2: 2026 Q1
    print("\n--- Loading 2026 Q1 data ---")
    w2 = load_window(CACHE_MAIN, "2026-01-01", "2026-03-31", all_features)
    print(f"  Loaded {len(w2):,} rows")
    results["2026_q1"] = evaluate_window("2026 Q1 (Jan-Mar)", w2, s2, phasec, thresholds, topk_list)

    # Window 3: 2026 April
    print("\n--- Loading 2026 April data ---")
    w3 = load_window(CACHE_MAIN, "2026-04-01", "2026-04-30", all_features)
    print(f"  Loaded {len(w3):,} rows")
    results["2026_april"] = evaluate_window("2026 April", w3, s2, phasec, thresholds, topk_list)

    # Cross-window summary
    print(f"\n{'=' * 80}")
    print("CROSS-WINDOW SUMMARY")
    print(f"{'=' * 80}")

    print(f"\n  {'Window':<28} {'Pos%':>6} {'Metric':<18} {'S2':>8} {'PC':>8} {'Winner':>8}")
    print(f"  {'-'*78}")

    for wname, wkey in [("2023 Feb-Apr", "2023_feb_apr"), ("2026 Q1", "2026_q1"), ("2026 April", "2026_april")]:
        r = results[wkey]
        s2_ti = r["threshold_independent"]["s2"]
        pc_ti = r["threshold_independent"]["phasec"]
        pos = r["positive_rate"]

        auc_s = s2_ti["auc_roc_cal"] or 0
        auc_p = pc_ti["auc_roc_cal"] or 0
        auc_w = "S2" if auc_s > auc_p else "PhaseC"
        print(f"  {wname:<28} {pos:>5.1%} {'AUC-ROC (cal)':<18} {auc_s:>8.4f} {auc_p:>8.4f} {auc_w:>8}")

        brier_s = s2_ti["brier_cal"]
        brier_p = pc_ti["brier_cal"]
        brier_w = "S2" if brier_s < brier_p else "PhaseC"
        print(f"  {'':28} {'':>6} {'Brier (cal)':<18} {brier_s:>8.4f} {brier_p:>8.4f} {brier_w:>8}")

        # Find p>=0.75 results
        s2_75 = next((x for x in r["calibrated_threshold"]["s2"] if x["threshold"] == 0.75), None)
        pc_75 = next((x for x in r["calibrated_threshold"]["phasec"] if x["threshold"] == 0.75), None)
        if s2_75 and pc_75:
            w75 = "S2" if s2_75["wilson_95"] > pc_75["wilson_95"] else "PhaseC"
            print(f"  {'':28} {'':>6} {'W95 @p>=0.75':<18} {s2_75['wilson_95']:>8.4f} {pc_75['wilson_95']:>8.4f} {w75:>8}")
            print(f"  {'':28} {'':>6} {'N @p>=0.75':<18} {s2_75['count']:>8} {pc_75['count']:>8}")
            print(f"  {'':28} {'':>6} {'Acc @p>=0.75':<18} {s2_75['accuracy']:>8.4f} {pc_75['accuracy']:>8.4f}")

        # TopK 5
        s2_t5 = next((x for x in r["topk"]["s2"] if x["k"] == 5), None)
        pc_t5 = next((x for x in r["topk"]["phasec"] if x["k"] == 5), None)
        if s2_t5 and pc_t5:
            t5w = "S2" if s2_t5["wilson_95"] > pc_t5["wilson_95"] else "PhaseC"
            print(f"  {'':28} {'':>6} {'Top5 W95':<18} {s2_t5['wilson_95']:>8.4f} {pc_t5['wilson_95']:>8.4f} {t5w:>8}")

        print()

    # Verdict
    print(f"{'=' * 80}")
    print("VERDICT")
    print(f"{'=' * 80}")

    s2_wins = 0
    pc_wins = 0
    for wkey in ["2023_feb_apr", "2026_q1", "2026_april"]:
        r = results[wkey]
        s2_auc = r["threshold_independent"]["s2"]["auc_roc_cal"] or 0
        pc_auc = r["threshold_independent"]["phasec"]["auc_roc_cal"] or 0
        if s2_auc > pc_auc:
            s2_wins += 1
        else:
            pc_wins += 1

    print(f"\n  AUC-ROC wins: S2={s2_wins}, PhaseC={pc_wins}")

    s2_w_wins = 0
    pc_w_wins = 0
    for wkey in ["2023_feb_apr", "2026_q1", "2026_april"]:
        r = results[wkey]
        s2_75 = next((x for x in r["calibrated_threshold"]["s2"] if x["threshold"] == 0.75), None)
        pc_75 = next((x for x in r["calibrated_threshold"]["phasec"] if x["threshold"] == 0.75), None)
        if s2_75 and pc_75:
            if s2_75["wilson_95"] > pc_75["wilson_95"]:
                s2_w_wins += 1
            else:
                pc_w_wins += 1

    print(f"  W95 @p>=0.75 wins: S2={s2_w_wins}, PhaseC={pc_w_wins}")

    # Regime analysis
    rates = {}
    for wkey in ["2023_feb_apr", "2026_q1", "2026_april"]:
        rates[wkey] = results[wkey]["positive_rate"]

    print(f"\n  Regime sensitivity:")
    print(f"    2023 Feb-Apr pos_rate={rates['2023_feb_apr']:.1%} — {'S2 favored (more features)' if s2_wins >= 2 else 'PhaseC favored'}")
    print(f"    2026 Q1      pos_rate={rates['2026_q1']:.1%}")
    print(f"    2026 April   pos_rate={rates['2026_april']:.1%} — strong bull market")

    s2_total_75 = sum(
        next((x for x in results[w]["calibrated_threshold"]["s2"] if x["threshold"] == 0.75), {"count": 0})["count"]
        for w in ["2023_feb_apr", "2026_q1", "2026_april"]
    )
    pc_total_75 = sum(
        next((x for x in results[w]["calibrated_threshold"]["phasec"] if x["threshold"] == 0.75), {"count": 0})["count"]
        for w in ["2023_feb_apr", "2026_q1", "2026_april"]
    )
    print(f"\n  Total high-conf signals @p>=0.75: S2={s2_total_75:,}, PhaseC={pc_total_75:,}")

    # Save JSON
    output = {
        "generated_at": datetime.now().isoformat(),
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
        "feature_overlap": {
            "shared": len(overlap),
            "s2_only": len(s2_only),
            "phasec_only": len(pc_only),
            "phasec_is_subset_of_s2": pc_sel.issubset(s2_sel),
        },
        "windows": results,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(str(OUTPUT_JSON), "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Full results saved: {OUTPUT_JSON}")
    print("\nDone.")


if __name__ == "__main__":
    main()
