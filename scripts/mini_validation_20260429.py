"""Mini validation: 2026-04-29 -> 2026-04-30 replay.

Runs the all-family executable-only baseline with identical config,
captures per-sample predictions via _PREDICTION_CAPTURE, and outputs
the 4/29 event-day candidates.

This script does NOT change any model config, thresholds, or features.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

os.environ["ASHARE_SIMILARITY_HOME"] = r"E:\ashare_similarity_runtime"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction import gpu_probe
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

capture: dict = {}
gpu_probe._PREDICTION_CAPTURE = capture

app_config = get_default_config()
store = LocalDataStore(app_config)

config = GpuProbeConfig(
    start=date(2023, 5, 1),
    train_end=date(2025, 6, 30),
    test_start=date(2025, 7, 1),
    end=date(2026, 4, 30),
    train_rows=300_000,
    test_rows=120_000,
    feature_set="expanded",
    candidate_family="all",
    selector_coverage_weight=0.02,
    max_selected_features=260,
    feature_selection_method="stable_tail",
    label_target="next_high_from_close",
    target_high_return_pct=1.0,
    lockbox_role="seen_research",
    exclude_event_limit_up=True,
)

print("=== Running all-family baseline replay for mini validation ===")
print(f"Config: expanded260 stable_tail, all-family, executable-only")
result = run_gpu_next_day_probe(store, config)

print(f"\n=== Replay complete: {result.get('status', 'unknown')} ===")
print(f"HC Accuracy: {result.get('confident_accuracy', result.get('result', {}).get('confident_accuracy'))}")
print(f"HC Count: {result.get('confident_count', result.get('result', {}).get('confident_count'))}")

if "test_df" not in capture:
    print("ERROR: _PREDICTION_CAPTURE did not receive data. Cannot produce per-sample output.")
    sys.exit(1)

test_df = capture["test_df"].copy()
prob = capture["prob"].flatten()
confident = capture["confident"].flatten().astype(bool)
actual = capture["actual"].flatten()
threshold = capture["threshold"]

test_df["prob"] = prob
test_df["confident"] = confident
test_df["actual_label"] = actual
test_df["predicted"] = (prob >= threshold).astype(int)

event_date_col = "date"
label_date_col = "label_date"

target_label_date = pd.Timestamp("2026-04-30")
target_event_date = pd.Timestamp("2026-04-29")

mask_by_label = test_df[label_date_col] == target_label_date
mask_by_event = test_df[event_date_col] == target_event_date
mask = mask_by_label & mask_by_event

day_df = test_df[mask].copy()

if day_df.empty:
    mask_label_dates = test_df[label_date_col].unique()
    close_dates = sorted([d for d in mask_label_dates if abs((pd.Timestamp(d) - target_label_date).days) <= 3])
    print(f"No exact match for 4/29 event. Nearby label_dates: {close_dates[:6]}")
    sys.exit(1)

print(f"\n=== 2026-04-29 Event Day Summary ===")
print(f"Total executable samples: {len(day_df)}")
print(f"Positive-predicted (prob >= {threshold:.4f}): {int((day_df['predicted'] == 1).sum())}")
print(f"High-confidence candidates: {int(day_df['confident'].sum())}")
print(f"Actual hits (next_high_from_close=1): {int(day_df['actual_label'].sum())}")

hc = day_df[day_df["confident"] & (day_df["predicted"] == 1)].copy()
hc_sorted = hc.sort_values("prob", ascending=False)

print(f"\n=== High-Confidence Positive Candidates ({len(hc_sorted)}) ===")

output_cols = ["symbol"]
for c in ["name", "stock_name"]:
    if c in hc_sorted.columns:
        output_cols.append(c)
        break
output_cols.extend(["prob", "actual_label"])
for c in ["close", "pct_change", "turnover", "amount", "limit_up_like",
          "next_high_return_pct", "next_close_return_pct"]:
    if c in hc_sorted.columns:
        output_cols.append(c)

available_cols = [c for c in output_cols if c in hc_sorted.columns]

hit_count = int(hc_sorted["actual_label"].sum())
total = len(hc_sorted)
precision = hit_count / total if total > 0 else 0.0

print(f"Hits: {hit_count}/{total} = {precision:.2%}")
print()
print(hc_sorted[available_cols].to_string(index=False, max_rows=80))

top_k_results = {}
for k in [3, 5, 10, 20]:
    topk = hc_sorted.head(k)
    if len(topk) > 0:
        topk_hits = int(topk["actual_label"].sum())
        topk_prec = topk_hits / len(topk)
        top_k_results[f"top{k}"] = {"count": len(topk), "hits": topk_hits, "precision": topk_prec}
        print(f"Top-{k}: {topk_hits}/{len(topk)} = {topk_prec:.2%}")

boyun_mask = day_df["symbol"].astype(str).str.contains("002297")
boyun = day_df[boyun_mask]
print(f"\n=== Case Study: 博云新材 002297 ===")
if boyun.empty:
    full_test_boyun = test_df[test_df["symbol"].astype(str).str.contains("002297")]
    print(f"NOT in 4/29 test samples (may be excluded by sampling or filters)")
    print(f"博云新材 in full test set: {len(full_test_boyun)} rows total")
    if not full_test_boyun.empty:
        recent = full_test_boyun.sort_values(event_date_col).tail(3)
        for _, row in recent.iterrows():
            print(f"  event={row[event_date_col]}, prob={row['prob']:.4f}, conf={row['confident']}, actual={row['actual_label']}")
else:
    for _, row in boyun.iterrows():
        print(f"  symbol={row['symbol']}, prob={row['prob']:.4f}, predicted={row['predicted']}, "
              f"confident={row['confident']}, actual={row['actual_label']}")
        for c in ["close", "limit_up_like", "next_high_return_pct", "next_close_return_pct"]:
            if c in row.index:
                print(f"  {c}={row[c]}")

summary = {
    "event_date": "2026-04-29",
    "label_date": "2026-04-30",
    "total_executable_samples": int(len(day_df)),
    "positive_predicted": int((day_df["predicted"] == 1).sum()),
    "high_conf_candidates": int(day_df["confident"].sum()),
    "high_conf_positive_candidates": int(total),
    "high_conf_hits": int(hit_count),
    "high_conf_precision": round(precision, 6),
    "actual_positives": int(day_df["actual_label"].sum()),
    "natural_hit_rate": round(float(day_df["actual_label"].mean()), 6),
    "threshold": round(threshold, 6),
    "top_k": top_k_results,
    "boyun_002297_in_pool": bool(len(boyun) > 0),
}

out_path = Path("E:/ashare_similarity_runtime/data/reports/prediction/mini_validation_20260429.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
print(f"\nSummary saved to {out_path}")

csv_path = Path("E:/ashare_similarity_runtime/data/reports/prediction/mini_validation_20260429_candidates.csv")
hc_sorted[available_cols].to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"Candidates CSV saved to {csv_path}")

gpu_probe._PREDICTION_CAPTURE = None
