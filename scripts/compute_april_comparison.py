"""Compute April-only metrics for 4 runs: C, F, G (new) + B1 (reference).

Outputs JSON to stdout with full precision@T, topK, daily breakdown, and
cross-run comparison — ready for report generation.
"""
import json, math, sys
from pathlib import Path
import pandas as pd
import numpy as np

RUNS = {
    "C_c009_only": "gpu_probe_20260504T031602Z_43170e0b",
    "F_c004_only": "gpu_probe_20260504T033043Z_080a9ce1",
    "G_c009_c004": "gpu_probe_20260504T033857Z_074fe9ea",
    "B1_c009_c011": "gpu_probe_20260503T185913Z_793f0623",
}

RUNS_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs")
THRESHOLDS = [0.70, 0.75, 0.76, 0.78, 0.80]
TOPK_CAPS = [10, 20, 30, 50]
TOPK_THRESHOLDS = [0.75, 0.78, 0.80]

def wilson_lower(p, n, z=1.959963984540054):
    if n <= 0: return 0.0
    z2 = z * z
    sn = float(max(n, 1))
    denom = 1.0 + z2 / sn
    centre = p + z2 / (2.0 * sn)
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * sn)) / sn)
    return max(0.0, min(1.0, (centre - margin) / denom))


def load_run(run_id):
    run_dir = RUNS_DIR / run_id
    artifact_path = run_dir / "artifact.json"
    pred_path = run_dir / "test_predictions.parquet"

    with open(artifact_path, "r", encoding="utf-8") as f:
        artifact = json.load(f)

    df = pd.read_parquet(pred_path)
    return artifact, df


def april_filter(df):
    """Filter to April only (2026-04-01 ~ 2026-04-29)."""
    if "prediction_event_date" in df.columns:
        date_col = pd.to_datetime(df["prediction_event_date"])
    elif "date" in df.columns:
        date_col = pd.to_datetime(df["date"])
    elif "trade_date" in df.columns:
        date_col = pd.to_datetime(df["trade_date"])
    else:
        raise ValueError(f"No date column found. Columns: {list(df.columns)}")

    mask = (date_col >= "2026-04-01") & (date_col <= "2026-04-29")
    out = df[mask].copy()
    out["_date"] = date_col[mask]
    return out


def compute_precision_at_threshold(df, prob_col, label_col, threshold):
    sel = df[df[prob_col] >= threshold]
    n = len(sel)
    if n == 0:
        return {"precision": None, "wilson": None, "count": 0, "hits": 0,
                "active_days": 0, "zero_candidate_days": 0,
                "avg_per_active_day": 0, "avg_per_all_day": 0}

    hits = int(sel[label_col].sum())
    prec = hits / n
    wil = wilson_lower(prec, n)

    daily = sel.groupby(sel["_date"].dt.date).size()
    active_days = len(daily)

    all_dates = sorted(df["_date"].dt.date.unique())
    total_days = len(all_dates)
    zero_days = total_days - active_days

    return {
        "precision": round(prec, 6),
        "wilson": round(wil, 6),
        "count": n,
        "hits": hits,
        "active_days": active_days,
        "total_days": total_days,
        "zero_candidate_days": zero_days,
        "avg_per_active_day": round(n / active_days, 2) if active_days > 0 else 0,
        "avg_per_all_day": round(n / total_days, 2) if total_days > 0 else 0,
    }


def compute_topk(df, prob_col, label_col, threshold, k):
    sel = df[df[prob_col] >= threshold].copy()
    if len(sel) == 0:
        return {"precision": None, "wilson": None, "count": 0, "hits": 0, "active_days": 0}

    sel["_rank"] = sel.groupby(sel["_date"].dt.date)[prob_col].rank(method="first", ascending=False)
    capped = sel[sel["_rank"] <= k]
    n = len(capped)
    if n == 0:
        return {"precision": None, "wilson": None, "count": 0, "hits": 0, "active_days": 0}

    hits = int(capped[label_col].sum())
    prec = hits / n
    wil = wilson_lower(prec, n)
    active = capped.groupby(capped["_date"].dt.date).ngroups

    return {
        "precision": round(prec, 6),
        "wilson": round(wil, 6),
        "count": n,
        "hits": hits,
        "active_days": active,
        "avg_per_all_day": round(n / len(df["_date"].dt.date.unique()), 2),
    }


def compute_daily_breakdown(df, prob_col, label_col, threshold):
    sel = df[df[prob_col] >= threshold].copy()
    all_dates = sorted(df["_date"].dt.date.unique())

    rows = []
    for d in all_dates:
        day_sel = sel[sel["_date"].dt.date == d]
        n = len(day_sel)
        if n == 0:
            rows.append({
                "date": str(d), "candidates": 0, "hits": 0, "precision": None,
                "max_probability": None, "avg_next_high_return": None,
                "avg_next_close_return": None, "note": "zero-candidate"
            })
            continue

        hits = int(day_sel[label_col].sum())
        prec = hits / n
        max_prob = float(day_sel[prob_col].max())

        avg_high_ret = None
        avg_close_ret = None
        for col in ("next_high_return_pct", "next_high_return"):
            if col in day_sel.columns:
                avg_high_ret = round(float(day_sel[col].mean()), 6)
                break
        for col in ("next_close_return_pct", "next_close_return"):
            if col in day_sel.columns:
                avg_close_ret = round(float(day_sel[col].mean()), 6)
                break

        note = ""
        if prec < 0.60:
            note = "drag_day"
        if n > 40:
            note = (note + " concentration" if note else "concentration").strip()

        rows.append({
            "date": str(d), "candidates": n, "hits": hits,
            "precision": round(prec, 4), "max_probability": round(max_prob, 4),
            "avg_next_high_return": avg_high_ret,
            "avg_next_close_return": avg_close_ret,
            "note": note,
        })

    return rows


def verify_artifact(artifact, run_key):
    """Extract key metadata for verification."""
    fs = artifact.get("feature_selection", {})
    split = artifact.get("split_manifest", {})

    selected = set(fs.get("selected_features", []))
    all_feats = set(artifact.get("features", []))

    c009_in = "tushare_main_force_divergence" in all_feats
    c009_sel = "tushare_main_force_divergence" in selected
    c004_in = "tushare_ff_adjusted_flow" in all_feats
    c004_sel = "tushare_ff_adjusted_flow" in selected
    c011_in = "tushare_auction_open_vwap_ratio" in all_feats
    c011_sel = "tushare_auction_open_vwap_ratio" in selected

    return {
        "run_id": artifact.get("run_id", ""),
        "model": artifact.get("model_name", ""),
        "feature_set": artifact.get("feature_set", ""),
        "features_in_manifest": len(all_feats),
        "selected_features": fs.get("selected_feature_count", len(selected)),
        "feature_hash": artifact.get("feature_hash", ""),
        "data_hash": artifact.get("data_hash", ""),
        "split_hash": split.get("split_hash", ""),
        "train_end": split.get("train_end", ""),
        "test_start": split.get("test_start", ""),
        "end": split.get("end", ""),
        "train_rows": split.get("train_window_rows", ""),
        "test_lockbox_rows": split.get("test_lockbox_rows", ""),
        "min_phase_days_3": artifact.get("min_phase_days_3", ""),
        "exclude_event_limit_up": artifact.get("exclude_event_limit_up", ""),
        "c009": {"in_features": c009_in, "selected": c009_sel},
        "c004": {"in_features": c004_in, "selected": c004_sel},
        "c011": {"in_features": c011_in, "selected": c011_sel},
    }


def main():
    results = {}

    for run_key, run_id in RUNS.items():
        print(f"Processing {run_key} ({run_id})...", file=sys.stderr)
        artifact, df = load_run(run_id)

        # Verify
        meta = verify_artifact(artifact, run_key)

        # Filter April
        april = april_filter(df)
        print(f"  April rows: {len(april)}", file=sys.stderr)

        # Detect columns
        prob_col = None
        label_col = None
        for c in df.columns:
            if c == "probability":
                prob_col = c
            elif "prob" in c.lower() and prob_col is None:
                prob_col = c
            if c == "actual":
                label_col = c
            elif c in ("label", "next_high_from_close", "prediction_label", "actual_label") and label_col is None:
                label_col = c

        print(f"  prob_col={prob_col}, label_col={label_col}", file=sys.stderr)
        print(f"  Columns: {list(df.columns[:20])}", file=sys.stderr)

        # Precision@T
        prec_at_t = {}
        for t in THRESHOLDS:
            prec_at_t[f"T{t:.2f}"] = compute_precision_at_threshold(april, prob_col, label_col, t)

        # TopK caps
        topk = {}
        for t in TOPK_THRESHOLDS:
            for k in TOPK_CAPS:
                topk[f"T{t:.2f}_top{k}"] = compute_topk(april, prob_col, label_col, t, k)

        # Daily breakdown at T>=0.75
        daily_075 = compute_daily_breakdown(april, prob_col, label_col, 0.75)

        # Concentration stats at T>=0.75
        sel_075 = april[april[prob_col] >= 0.75]
        if len(sel_075) > 0:
            daily_counts = sel_075.groupby(sel_075["_date"].dt.date).size()
            conc = {
                "total_candidates": int(daily_counts.sum()),
                "active_days": len(daily_counts),
                "total_days": len(april["_date"].dt.date.unique()),
                "max_single_day": int(daily_counts.max()),
                "max_single_day_date": str(daily_counts.idxmax()),
                "top_date_pct": round(int(daily_counts.max()) / int(daily_counts.sum()), 4),
                "median_per_active_day": round(float(daily_counts.median()), 1),
                "p75_per_active_day": round(float(daily_counts.quantile(0.75)), 1),
            }
        else:
            conc = {"total_candidates": 0}

        results[run_key] = {
            "metadata": meta,
            "april_rows": len(april),
            "april_symbols": int(april[sym_col].nunique()) if (sym_col := next((c for c in ("ts_code", "symbol") if c in april.columns), None)) else None,
            "precision_at_threshold": prec_at_t,
            "topk_cap": topk,
            "daily_breakdown_T075": daily_075,
            "concentration_T075": conc,
        }

    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
