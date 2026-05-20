"""Frozen inference validation for S2_fw_step1_try_add_C138 bundle.

Two out-of-sample windows:
  - Pre-training: 2023-02-01 ~ 2023-04-30 (model never saw this)
  - April holdout: 2026-04-01 ~ 2026-04-30 (forward validation)

Uses the saved bundle (CatBoost + isotonic) to score without any retraining.
Reports per-threshold daily coverage, hit rate, ticket count, monthly breakdown.
"""
from __future__ import annotations

import io
import json
import math
import pickle
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

BUNDLE_PATH = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260509T002433Z_a0ec8105\model_bundle.pt"
)
REPORT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
SUMMARY_PATH = REPORT_DIR / "s2_frozen_validation_20260509.json"
TABLE_PATH = REPORT_DIR / "s2_frozen_validation_daily_detail_20260509.csv"


def wilson_lower_95(accuracy: float, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = accuracy
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (center - spread) / denom


def predict_from_bundle(payload: dict, X_raw: np.ndarray) -> np.ndarray:
    """Run full inference pipeline from frozen bundle."""
    mean_np = payload["mean"].numpy().flatten()
    std_np = payload["std"].numpy().flatten()
    selected_idx = payload["selected_indices"].numpy()

    X_norm = (X_raw - mean_np) / std_np
    X_selected = X_norm[:, selected_idx]

    member_probs = []
    for m_info in payload["members"]:
        model_kind = m_info["model_kind"]
        if model_kind in ("xgboost", "lightgbm", "catboost"):
            model_obj = pickle.loads(m_info["model_bytes"])
            prob_np = model_obj.predict_proba(X_selected)[:, 1]
            prob = torch.as_tensor(prob_np, dtype=torch.float32)
            member_probs.append(prob)
        elif model_kind == "torch":
            raise NotImplementedError("Torch member not expected in S2 bundle")

    ensemble_prob = torch.stack(member_probs, dim=0).mean(dim=0)

    iso_bytes = payload.get("iso_model_bytes")
    if payload.get("calibration_used") == "isotonic" and iso_bytes:
        iso = pickle.loads(iso_bytes)
        prob_np = ensemble_prob.numpy().astype(float).ravel()
        calibrated = iso.predict(prob_np)
        return calibrated
    return ensemble_prob.numpy()


def score_window(
    payload: dict,
    feature_df: pd.DataFrame,
    window_start: str,
    window_end: str,
    label: str,
) -> dict:
    """Score a date window with the frozen bundle and report detailed metrics."""
    feature_names = list(payload["feature_names"])

    df = feature_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    if "label_date" in df.columns:
        df["label_date"] = pd.to_datetime(df["label_date"])
        mask = (df["label_date"] >= window_start) & (df["label_date"] <= window_end)
    else:
        mask = (df["date"] >= window_start) & (df["date"] <= window_end)

    window_df = df[mask].copy()
    print(f"\n[{label}] Scoring {len(window_df)} rows in {window_start} ~ {window_end}", flush=True)

    if len(window_df) == 0:
        return {"label": label, "status": "no_data", "rows": 0}

    missing_cols = [c for c in feature_names if c not in window_df.columns]
    if missing_cols:
        print(f"[{label}] WARNING: {len(missing_cols)} missing columns, filling with 0", flush=True)
        for c in missing_cols:
            window_df[c] = 0.0

    X_raw = window_df[feature_names].to_numpy(dtype=np.float32)
    X_raw = np.nan_to_num(X_raw, nan=0.0)

    print(f"[{label}] Running frozen inference...", flush=True)
    probs = predict_from_bundle(payload, X_raw)
    window_df = window_df.copy()
    window_df["probability"] = probs

    has_label = "actual" in window_df.columns
    if not has_label and "next_high_from_close" in window_df.columns:
        window_df["actual"] = window_df["next_high_from_close"].astype(int)
        has_label = True

    if not has_label:
        return {
            "label": label,
            "status": "scored_no_label",
            "rows": len(window_df),
            "mean_probability": float(probs.mean()),
        }

    results = {"label": label, "status": "completed", "rows": len(window_df)}
    thresholds = [
        ("p>=0.70", 0.70, False),
        ("p>0.75", 0.75, True),
        ("p>=0.78", 0.78, False),
        ("p>=0.80", 0.80, False),
    ]

    # --- Overall threshold metrics ---
    for thresh_name, thresh_val, strict in thresholds:
        if strict:
            sel = window_df[window_df["probability"] > thresh_val]
        else:
            sel = window_df[window_df["probability"] >= thresh_val]

        if len(sel) > 0:
            acc = sel["actual"].mean()
            w95 = wilson_lower_95(acc, len(sel))
            results[thresh_name] = {
                "count": int(len(sel)),
                "accuracy": round(float(acc), 6),
                "wilson_95": round(float(w95), 6),
                "coverage": round(float(len(sel)) / len(window_df), 6),
            }
        else:
            results[thresh_name] = {"count": 0, "accuracy": None, "wilson_95": None, "coverage": 0}

    # --- Daily top6 (p>0.75 + top6 with ties) ---
    dates_sorted = sorted(window_df["date"].dt.date.unique())
    daily_groups = []
    for d in dates_sorted:
        day_df = window_df[window_df["date"].dt.date == d]
        day_above = day_df[day_df["probability"] > 0.75].sort_values(
            ["probability", "symbol"], ascending=[False, True]
        )
        if len(day_above) > 0:
            if len(day_above) > 6:
                cutoff = day_above.iloc[5]["probability"]
                day_above = day_above[day_above["probability"] >= cutoff]
            daily_groups.append(day_above)

    if daily_groups:
        top6_df = pd.concat(daily_groups, ignore_index=True)
        top6_acc = top6_df["actual"].mean()
        top6_w95 = wilson_lower_95(top6_acc, len(top6_df))
        results["daily_top6_p>0.75"] = {
            "count": int(len(top6_df)),
            "accuracy": round(float(top6_acc), 6),
            "wilson_95": round(float(top6_w95), 6),
            "coverage_days": int(len(daily_groups)),
            "total_trading_days": int(len(dates_sorted)),
            "avg_per_day": round(len(top6_df) / len(daily_groups), 2),
        }
    else:
        results["daily_top6_p>0.75"] = {
            "count": 0, "accuracy": None, "coverage_days": 0,
            "total_trading_days": int(len(dates_sorted)),
        }

    # --- Per-day detail for each threshold ---
    daily_detail = []
    for d in dates_sorted:
        day_df = window_df[window_df["date"].dt.date == d]
        day_total = len(day_df)
        row = {
            "window": label,
            "date": str(d),
            "total_stocks": day_total,
        }
        for thresh_name, thresh_val, strict in thresholds:
            if strict:
                sel = day_df[day_df["probability"] > thresh_val]
            else:
                sel = day_df[day_df["probability"] >= thresh_val]
            n = len(sel)
            hits = int(sel["actual"].sum()) if n > 0 else 0
            acc = hits / n if n > 0 else None
            row[f"{thresh_name}_count"] = n
            row[f"{thresh_name}_hits"] = hits
            row[f"{thresh_name}_accuracy"] = round(acc, 4) if acc is not None else None

        # top6 with ties for this day
        day_above = day_df[day_df["probability"] > 0.75].sort_values(
            ["probability", "symbol"], ascending=[False, True]
        )
        if len(day_above) > 6:
            cutoff = day_above.iloc[5]["probability"]
            day_above = day_above[day_above["probability"] >= cutoff]
        t6_n = len(day_above)
        t6_hits = int(day_above["actual"].sum()) if t6_n > 0 else 0
        t6_acc = t6_hits / t6_n if t6_n > 0 else None
        row["top6_count"] = t6_n
        row["top6_hits"] = t6_hits
        row["top6_accuracy"] = round(t6_acc, 4) if t6_acc is not None else None
        row["top6_max_prob"] = round(float(day_above["probability"].max()), 4) if t6_n > 0 else None

        daily_detail.append(row)

    results["daily_detail"] = daily_detail

    # --- Monthly breakdown ---
    window_df["month"] = window_df["date"].dt.to_period("M")
    monthly = {}
    for month, group in window_df.groupby("month"):
        m_total = len(group)
        m_dates = group["date"].dt.date.nunique()
        m_entry = {"total_rows": m_total, "trading_days": m_dates}

        for thresh_name, thresh_val, strict in thresholds:
            if strict:
                sel = group[group["probability"] > thresh_val]
            else:
                sel = group[group["probability"] >= thresh_val]
            n = len(sel)
            if n > 0:
                acc = sel["actual"].mean()
                w95 = wilson_lower_95(acc, n)
                days_with_signal = sel["date"].dt.date.nunique()
                m_entry[thresh_name] = {
                    "count": int(n),
                    "accuracy": round(float(acc), 4),
                    "wilson_95": round(float(w95), 4),
                    "signal_days": days_with_signal,
                    "avg_per_signal_day": round(n / days_with_signal, 2) if days_with_signal > 0 else 0,
                }
            else:
                m_entry[thresh_name] = {"count": 0, "accuracy": None, "signal_days": 0}

        monthly[str(month)] = m_entry

    results["monthly"] = monthly

    return results


def main() -> int:
    print("=" * 70)
    print("S2_fw_step1_try_add_C138 Frozen Validation")
    print("=" * 70)
    print(f"Bundle: {BUNDLE_PATH}")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")

    payload = torch.load(str(BUNDLE_PATH), map_location="cpu", weights_only=False)
    feature_names = list(payload["feature_names"])
    selected_names = list(payload["selected_feature_names"])
    print(f"Feature pool: {len(feature_names)}, Selected: {len(selected_names)}")
    print(f"Model: {payload['model_name']}, Calibration: {payload['calibration_used']}")

    store = LocalDataStore(get_default_config())
    all_results = {}
    all_daily_detail = []

    # === Window 1: Pre-training 2023-02 ~ 2023-04 ===
    print("\n" + "=" * 70)
    print("WINDOW 1: Pre-training validation (2023-02-01 ~ 2023-04-30)")
    print("  Model training starts 2023-05 — this window is fully OOS")
    print("=" * 70)

    config_pre = GpuProbeConfig(
        start=date(2022, 11, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2023, 2, 1),
        end=date(2023, 4, 30),
        seed=42,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )
    print("Building pre-training feature matrix...", flush=True)
    t0 = time.time()
    result_pre = run_gpu_next_day_probe(store, config_pre)
    elapsed_pre = time.time() - t0
    print(f"Pre-training probe: {result_pre.get('status')} in {elapsed_pre:.0f}s", flush=True)

    cache_pre = result_pre.get("feature_cache", {})
    cache_pre_path = cache_pre.get("path")

    if cache_pre_path and Path(cache_pre_path).exists():
        feature_pre = pd.read_parquet(cache_pre_path)
        print(f"Pre-training cache: {len(feature_pre)} rows, {len(feature_pre.columns)} cols", flush=True)
        pre_result = score_window(payload, feature_pre, "2023-02-01", "2023-04-30", "pre_training")
        all_results["pre_training_2023_02_04"] = pre_result
        if "daily_detail" in pre_result:
            all_daily_detail.extend(pre_result.pop("daily_detail"))
    else:
        print("WARNING: No feature cache for pre-training window", flush=True)
        all_results["pre_training_2023_02_04"] = {"status": "cache_not_available"}

    # === Window 2: April 2026 holdout ===
    print("\n" + "=" * 70)
    print("WINDOW 2: April 2026 holdout (2026-04-01 ~ 2026-04-30)")
    print("  Training ends 2025-12. Q1 test ends 2026-03. April is forward-only.")
    print("=" * 70)

    config_apr = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2026, 3, 31),
        test_start=date(2026, 4, 1),
        end=date(2026, 4, 30),
        seed=42,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )
    print("Building April feature matrix...", flush=True)
    t0 = time.time()
    result_apr = run_gpu_next_day_probe(store, config_apr)
    elapsed_apr = time.time() - t0
    print(f"April probe: {result_apr.get('status')} in {elapsed_apr:.0f}s", flush=True)

    cache_apr = result_apr.get("feature_cache", {})
    cache_apr_path = cache_apr.get("path")

    if cache_apr_path and Path(cache_apr_path).exists():
        feature_apr = pd.read_parquet(cache_apr_path)
        print(f"April cache: {len(feature_apr)} rows, {len(feature_apr.columns)} cols", flush=True)
        apr_result = score_window(payload, feature_apr, "2026-04-01", "2026-04-30", "april_holdout")
        all_results["april_2026_holdout"] = apr_result
        if "daily_detail" in apr_result:
            all_daily_detail.extend(apr_result.pop("daily_detail"))
    else:
        print("WARNING: No feature cache for April", flush=True)
        all_results["april_2026_holdout"] = {"status": "cache_not_available"}

    # === Print Summary ===
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for window_name, res in all_results.items():
        print(f"\n{'='*50}")
        print(f"  {window_name}")
        print(f"{'='*50}")
        if res.get("status") != "completed":
            print(f"  Status: {res.get('status')}")
            continue
        print(f"  Total rows: {res['rows']}")
        print()
        print(f"  {'Threshold':<12} {'Count':>6} {'Accuracy':>9} {'Wilson95':>9} {'Coverage':>9}")
        print(f"  {'-'*12} {'-'*6} {'-'*9} {'-'*9} {'-'*9}")
        for thresh in ["p>=0.70", "p>0.75", "p>=0.78", "p>=0.80"]:
            t = res.get(thresh, {})
            if t.get("count", 0) > 0:
                print(f"  {thresh:<12} {t['count']:>6} {t['accuracy']:>9.4f} {t['wilson_95']:>9.4f} {t['coverage']:>9.4f}")
            else:
                print(f"  {thresh:<12} {0:>6} {'N/A':>9} {'N/A':>9} {0:>9.4f}")

        top6 = res.get("daily_top6_p>0.75", {})
        if top6.get("count", 0) > 0:
            print(f"\n  Daily top6 (p>0.75 + top6 ties):")
            print(f"    Tickets: {top6['count']}, Accuracy: {top6['accuracy']:.4f}, Wilson: {top6['wilson_95']:.4f}")
            print(f"    Signal days: {top6['coverage_days']}/{top6['total_trading_days']}, Avg/day: {top6['avg_per_day']}")

        monthly = res.get("monthly", {})
        if monthly:
            print(f"\n  Monthly breakdown:")
            print(f"  {'Month':<8} {'Days':>5} | {'p>0.75 n':>8} {'acc':>6} {'W95':>6} {'sig_d':>5} {'avg/d':>5} | {'p>=0.78 n':>9} {'acc':>6} {'W95':>6}")
            print(f"  {'-'*8} {'-'*5}-+-{'-'*8}-{'-'*6}-{'-'*6}-{'-'*5}-{'-'*5}-+-{'-'*9}-{'-'*6}-{'-'*6}")
            for m, v in sorted(monthly.items()):
                p75 = v.get("p>0.75", {})
                p78 = v.get("p>=0.78", {})
                p75_n = p75.get("count", 0)
                p75_acc = f"{p75['accuracy']:.4f}" if p75.get("accuracy") else "N/A"
                p75_w = f"{p75['wilson_95']:.4f}" if p75.get("wilson_95") else "N/A"
                p75_sd = p75.get("signal_days", 0)
                p75_avg = f"{p75.get('avg_per_signal_day', 0):.1f}"
                p78_n = p78.get("count", 0)
                p78_acc = f"{p78['accuracy']:.4f}" if p78.get("accuracy") else "N/A"
                p78_w = f"{p78['wilson_95']:.4f}" if p78.get("wilson_95") else "N/A"
                print(f"  {m:<8} {v['trading_days']:>5} | {p75_n:>8} {p75_acc:>6} {p75_w:>6} {p75_sd:>5} {p75_avg:>5} | {p78_n:>9} {p78_acc:>6} {p78_w:>6}")

    # Save outputs
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle": str(BUNDLE_PATH),
        "bundle_run_id": "gpu_probe_20260509T002433Z_a0ec8105",
        "bundle_variant": "S2_fw_step1_try_add_C138",
        "bundle_model": payload["model_name"],
        "bundle_calibration": payload["calibration_used"],
        "bundle_selected_features": len(selected_names),
        "validation_windows": all_results,
    }

    SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nJSON saved: {SUMMARY_PATH}")

    if all_daily_detail:
        detail_df = pd.DataFrame(all_daily_detail)
        detail_df.to_csv(TABLE_PATH, index=False, encoding="utf-8-sig")
        print(f"Daily detail CSV: {TABLE_PATH} ({len(detail_df)} rows)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
