"""Mini validation: 2026-04-29 -> 2026-04-30 replay from test_predictions.parquet.

Reads the per-sample predictions artifact from the latest all-family
executable-only baseline and filters to event_date = 2026-04-29.
No model retraining — pure parquet read + filter.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def find_latest_run_dir(base: Path) -> Path | None:
    runs_dir = base / "prediction" / "runs"
    if not runs_dir.exists():
        return None
    candidates = sorted(runs_dir.iterdir(), reverse=True)
    for d in candidates:
        if (d / "test_predictions.parquet").exists():
            return d
    return None


def main(run_dir_override: str | None = None) -> None:
    base = Path("E:/ashare_similarity_runtime/data/reports")

    if run_dir_override:
        run_dir = Path(run_dir_override)
    else:
        run_dir = find_latest_run_dir(base)

    if run_dir is None or not (run_dir / "test_predictions.parquet").exists():
        print("ERROR: No test_predictions.parquet found. Run baseline first.")
        sys.exit(1)

    print(f"Reading from: {run_dir}")
    pred_path = run_dir / "test_predictions.parquet"
    df = pd.read_parquet(pred_path)
    print(f"Total test predictions: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    metrics_path = run_dir / "metrics.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        print(f"Run ID: {metrics.get('run_id')}")
        print(f"Model: {metrics.get('model')}")
        print(f"HC accuracy: {metrics.get('confident_accuracy')}")
        print(f"HC count: {metrics.get('confident_count')}")

    df["date"] = pd.to_datetime(df["date"])
    df["label_date"] = pd.to_datetime(df["label_date"])

    target_event = pd.Timestamp("2026-04-29")
    target_label = pd.Timestamp("2026-04-30")

    day_df = df[(df["date"] == target_event) & (df["label_date"] == target_label)].copy()
    if day_df.empty:
        all_dates = sorted(df["date"].unique())
        close_dates = [d for d in all_dates if abs((pd.Timestamp(d) - target_event).days) <= 3]
        print(f"\nNo 4/29 event samples. Nearby event dates: {close_dates[-6:]}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"2026-04-29 -> 2026-04-30 Mini Validation")
    print(f"{'='*60}")
    print(f"Total executable samples on 4/29: {len(day_df)}")

    threshold = day_df["threshold"].iloc[0] if "threshold" in day_df.columns else 0.5
    positive_predicted = day_df[day_df["predicted_label"] == 1]
    high_conf = day_df[day_df["confident"] == 1]
    hc_positive = day_df[(day_df["confident"] == 1) & (day_df["predicted_label"] == 1)]

    print(f"Classification threshold: {threshold:.4f}")
    print(f"Positive-predicted (prob >= threshold): {len(positive_predicted)}")
    print(f"High-confidence total: {len(high_conf)}")
    print(f"High-confidence positive (buy candidates): {len(hc_positive)}")
    print(f"Actual positives (next_high_from_close=1): {int(day_df['actual'].sum())}")
    natural_rate = day_df["actual"].mean()
    print(f"Natural hit rate on 4/29: {natural_rate:.4f} ({natural_rate:.2%})")

    if len(hc_positive) > 0:
        hc_sorted = hc_positive.sort_values("probability", ascending=False)
        hits = int(hc_sorted["actual"].sum())
        total = len(hc_sorted)
        precision = hits / total if total else 0.0

        print(f"\n--- High-Confidence Positive Candidates: {hits}/{total} = {precision:.2%} ---")

        display_cols = ["symbol"]
        for c in ["name", "stock_name"]:
            if c in hc_sorted.columns:
                display_cols.append(c)
                break
        display_cols.append("probability")
        display_cols.append("actual")
        for c in ["close", "pct_change", "limit_up_like", "next_high_return_pct", "next_close_return_pct",
                   "turnover", "amount"]:
            if c in hc_sorted.columns:
                display_cols.append(c)
        available = [c for c in display_cols if c in hc_sorted.columns]
        print(hc_sorted[available].to_string(index=False, max_rows=100))

        print(f"\n--- Top-K Precision ---")
        for k in [3, 5, 10, 20, 50]:
            topk = hc_sorted.head(k)
            if len(topk) > 0:
                tk_hits = int(topk["actual"].sum())
                tk_prec = tk_hits / len(topk) if len(topk) else 0
                print(f"  Top-{k}: {tk_hits}/{len(topk)} = {tk_prec:.2%}")
    else:
        print("\nNo high-confidence positive candidates on 4/29.")

    print(f"\n--- Case Study: 博云新材 002297 ---")
    boyun_mask = day_df["symbol"].astype(str).str.contains("002297")
    boyun = day_df[boyun_mask]
    if boyun.empty:
        print("NOT in 4/29 executable test samples.")
        full_boyun = df[df["symbol"].astype(str).str.contains("002297")]
        if full_boyun.empty:
            print("Not in full test set at all (excluded by filters or sampling).")
        else:
            print(f"Present in full test set: {len(full_boyun)} rows")
            recent = full_boyun.sort_values("date").tail(5)
            for _, row in recent.iterrows():
                conf_str = "HC" if row.get("confident", 0) == 1 else "--"
                print(f"  {row['date'].date()} prob={row['probability']:.4f} [{conf_str}] actual={int(row['actual'])}")
    else:
        for _, row in boyun.iterrows():
            conf_str = "HIGH-CONF" if row.get("confident", 0) == 1 else "low-conf"
            pred_str = "BUY" if row.get("predicted_label", 0) == 1 else "no-buy"
            hit_str = "HIT" if row.get("actual", 0) == 1 else "MISS"
            print(f"  symbol={row['symbol']}  prob={row['probability']:.4f}  [{conf_str}]  [{pred_str}]  [{hit_str}]")
            for c in ["close", "limit_up_like", "next_high_return_pct", "next_close_return_pct"]:
                if c in row.index and pd.notna(row[c]):
                    print(f"    {c} = {row[c]}")

    summary = {
        "event_date": "2026-04-29",
        "label_date": "2026-04-30",
        "run_dir": str(run_dir),
        "total_executable_samples": int(len(day_df)),
        "positive_predicted": int(len(positive_predicted)),
        "high_conf_total": int(len(high_conf)),
        "high_conf_positive": int(len(hc_positive)),
        "high_conf_hits": int(hc_positive["actual"].sum()) if len(hc_positive) else 0,
        "high_conf_precision": round(int(hc_positive["actual"].sum()) / len(hc_positive), 6) if len(hc_positive) else None,
        "actual_positives": int(day_df["actual"].sum()),
        "natural_hit_rate": round(float(natural_rate), 6),
        "threshold": float(threshold),
        "boyun_002297_in_pool": bool(len(boyun) > 0),
    }
    out_path = Path("E:/ashare_similarity_runtime/data/reports/prediction/mini_validation_20260429.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSummary saved to {out_path}")


if __name__ == "__main__":
    run_dir_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(run_dir_arg)
