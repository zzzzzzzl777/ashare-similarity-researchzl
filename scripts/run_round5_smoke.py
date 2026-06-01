"""Round 5: All-factor layered comparison — smoke phase.

Runs 10 pre-defined variants from the locked manifest:
  V00: baseline control (no new factors)
  V01: all daily OHLCV (7 factors)
  V10-V16: single factor ablation (1 new factor each)
  V20: daily OHLCV + best minute combo

All runs use lockbox_role=seen_research, final_acceptance_eligible=False.
No April data is touched. Q1 2026 only.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

LEDGER_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\experiment_ledger_20260507.jsonl")
MANIFEST_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\all_factor_variant_manifest_20260507.json")

ALL_DAILY_OHLCV_COLS = (
    "tushare_price_vs_cost_20d",
    "tushare_abnormal_3d_deviation",
    "tushare_vol_gain_20d",
    "tushare_inv_t_20d",
    "tushare_asr_60d",
    "tushare_illiq_classic_20d",
    "tushare_ato_120d",
)
ALL_DAILY_OHLCV_AVAIL = tuple(f"{c}_available" for c in ALL_DAILY_OHLCV_COLS)

ALL_MINUTE_COLS = (
    "tushare_last_30min_return",
    "tushare_first_15min_volume_ratio",
    "tushare_intraday_volatility",
    "tushare_up_volume_ratio",
    "tushare_high_time_pct",
)
ALL_MINUTE_AVAIL = tuple(f"{c}_available" for c in ALL_MINUTE_COLS)

MINUTE_BEST_COLS = (
    "tushare_last_30min_return",
    "tushare_intraday_volatility",
    "tushare_high_time_pct",
)
MINUTE_BEST_AVAIL = tuple(f"{c}_available" for c in MINUTE_BEST_COLS)


def _make_exclude(include_daily: tuple[str, ...] = (), include_minute: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Build exclude list: everything NOT in include sets gets excluded."""
    exclude = []
    for col in ALL_DAILY_OHLCV_COLS:
        if col not in include_daily:
            exclude.append(col)
            exclude.append(f"{col}_available")
    for col in ALL_MINUTE_COLS:
        if col not in include_minute:
            exclude.append(col)
            exclude.append(f"{col}_available")
    return tuple(exclude)


VARIANTS = [
    ("V00_baseline_control", _make_exclude(include_daily=(), include_minute=()), ["C004", "C009", "C011"]),
    ("V01_daily_ohlcv_all", _make_exclude(include_daily=ALL_DAILY_OHLCV_COLS, include_minute=()), ["C004", "C009", "C011", "C154", "C156", "C157", "C158", "C159", "C161", "C162"]),
    ("V10_single_C154", _make_exclude(include_daily=("tushare_price_vs_cost_20d",), include_minute=()), ["C004", "C009", "C011", "C154"]),
    ("V11_single_C156", _make_exclude(include_daily=("tushare_abnormal_3d_deviation",), include_minute=()), ["C004", "C009", "C011", "C156"]),
    ("V12_single_C157", _make_exclude(include_daily=("tushare_vol_gain_20d",), include_minute=()), ["C004", "C009", "C011", "C157"]),
    ("V13_single_C158", _make_exclude(include_daily=("tushare_inv_t_20d",), include_minute=()), ["C004", "C009", "C011", "C158"]),
    ("V14_single_C159", _make_exclude(include_daily=("tushare_asr_60d",), include_minute=()), ["C004", "C009", "C011", "C159"]),
    ("V15_single_C161", _make_exclude(include_daily=("tushare_illiq_classic_20d",), include_minute=()), ["C004", "C009", "C011", "C161"]),
    ("V16_single_C162", _make_exclude(include_daily=("tushare_ato_120d",), include_minute=()), ["C004", "C009", "C011", "C162"]),
    ("V20_daily_plus_minute_best", _make_exclude(include_daily=ALL_DAILY_OHLCV_COLS, include_minute=MINUTE_BEST_COLS), ["C004", "C009", "C011", "C154", "C156", "C157", "C158", "C159", "C161", "C162", "C133", "C136", "C138"]),
]


def _append_ledger(entry: dict) -> None:
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def run_variant(variant_name: str, exclude_features: tuple[str, ...], used_factor_ids: list[str], seed: int = 42) -> dict:
    cfg = get_default_config()
    store = LocalDataStore(cfg)

    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 3, 31),
        seed=seed,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=exclude_features,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )

    print(f"\n{'='*60}")
    print(f"Running: {variant_name} (seed={seed})")
    print(f"Excluded features: {len(exclude_features)}")
    print(f"Used factor IDs: {used_factor_ids}")
    print(f"{'='*60}")

    t0 = time.time()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0

    run_id = result.get("run_id", "unknown")
    metrics = result.get("metrics", result)

    hc_acc = metrics.get("confident_accuracy", 0)
    wilson = metrics.get("acceptance", {}).get("high_confidence", {}).get("wilson_lower_95", 0)
    hc_count = metrics.get("confident_count", 0)
    coverage = metrics.get("confident_coverage", 0)
    brier = metrics.get("brier", 0)

    print(f"\n  Result: run_id={run_id}")
    print(f"  HC accuracy: {hc_acc:.4f}")
    print(f"  Wilson 95%:  {wilson:.4f}")
    print(f"  HC count:    {hc_count}")
    print(f"  Coverage:    {coverage:.4f}")
    print(f"  Brier:       {brier:.5f}")
    print(f"  Time:        {elapsed:.1f}s")

    ledger_entry = {
        "run_id": run_id,
        "variant": variant_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "used_factor_ids": used_factor_ids,
        "excluded_feature_count": len(exclude_features),
        "hc_accuracy": hc_acc,
        "wilson_lower_95": wilson,
        "hc_count": hc_count,
        "coverage": coverage,
        "brier": brier,
        "elapsed_seconds": elapsed,
        "lockbox_role": "seen_research",
        "final_acceptance_eligible": False,
        "artifact_path": result.get("artifact_path", ""),
    }
    _append_ledger(ledger_entry)

    return result


def main():
    print("Round 5 — All-Factor Smoke Training")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Ledger: {LEDGER_PATH}")
    print(f"Variants: {len(VARIANTS)}")
    print()

    # First run needs cache refresh to include new daily OHLCV factors
    first_run = True
    results = {}

    for variant_name, exclude_features, factor_ids in VARIANTS:
        result = run_variant(variant_name, exclude_features, factor_ids)
        results[variant_name] = result
        if first_run:
            first_run = False

    print("\n" + "="*60)
    print("ALL VARIANTS COMPLETE")
    print("="*60)
    print(f"\nLedger entries written to: {LEDGER_PATH}")


if __name__ == "__main__":
    main()
