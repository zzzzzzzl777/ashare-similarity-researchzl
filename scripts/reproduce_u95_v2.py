"""Reproduce U95_chip_t1_no_ths_live_strict metrics - v2.

Uses the T-1 shifted cache by copying it to the computed fingerprint path.

Expected reference:
  HC accuracy: 75.4243%
  Wilson lower 95%: 74.6116%
  HC count: 11019
  Coverage: 25.6107%
  Brier: 0.219497
  Selected features: 260

Tolerance: < 0.3pp difference from reference.
"""
from __future__ import annotations

import json
import sys
import time
import shutil
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import (
    GpuProbeConfig, run_gpu_next_day_probe, _feature_cache_descriptor
)

REPORT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
CACHE_DIR = REPORT_DIR / "feature_cache"

# U95 exclusion list (58 features)
HARD_MONEYFLOW = [
    "tushare_net_mf_amount", "tushare_net_mf_amount_available",
    "tushare_lg_buy_sell_ratio", "tushare_lg_buy_sell_ratio_available",
    "tushare_elg_buy_sell_ratio", "tushare_elg_buy_sell_ratio_available",
    "tushare_mf_strength", "tushare_mf_strength_available",
    "tushare_sm_sell_pressure", "tushare_sm_sell_pressure_available",
    "tushare_main_force_divergence", "tushare_main_force_divergence_available",
    "tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available",
]

POST_CLOSE_FAMILY_ABDE = [
    "tushare_lhb_net_buy", "tushare_lhb_net_rate", "tushare_inst_buy_count",
    "tushare_lhb_appeared", "tushare_inst_net_buy",
    "tushare_rzye_delta_pct", "tushare_rzye", "tushare_rzmre_ratio",
    "tushare_margin_net", "tushare_rqye_ratio",
    "tushare_auction_close_vwap_ratio", "tushare_auction_close_vol",
    "tushare_float_relative_impact",
]
POST_CLOSE_WITH_AVAIL = []
for col in POST_CLOSE_FAMILY_ABDE:
    POST_CLOSE_WITH_AVAIL.append(col)
    POST_CLOSE_WITH_AVAIL.append(f"{col}_available")

THS_SECTOR_BASE = [
    "sector_pct_change_best", "sector_strength_rank", "sector_limit_up_count",
    "sector_divergence", "sector_duration_days", "sector_climax_signal",
]
THS_WITH_AVAIL = []
for col in THS_SECTOR_BASE:
    THS_WITH_AVAIL.append(col)
    THS_WITH_AVAIL.append(f"{col}_available")
    THS_WITH_AVAIL.append(f"{col}_available_available")

ALL_EXCLUDED = sorted(set(HARD_MONEYFLOW + POST_CLOSE_WITH_AVAIL + THS_WITH_AVAIL))

# Chip features to T-1 shift
CHIP_COLS = [
    "tushare_cost_concentration", "tushare_cost_position", "tushare_winner_rate",
    "tushare_cost_concentration_available", "tushare_cost_position_available",
    "tushare_winner_rate_available",
]

# Reference metrics
REF = {
    "hc_accuracy": 0.754243,
    "wilson_lower_95": 0.746116,
    "hc_count": 11019,
    "hc_coverage": 0.256107,
    "brier": 0.219497,
    "selected_features": 260,
}


def _build_t1_shifted_cache(source_path: Path, dest_path: Path):
    """Apply T-1 shift to chip/cost features."""
    import pandas as pd
    print(f"  Building T-1 shifted cache from {source_path.name}...")
    t0 = time.time()
    df = pd.read_parquet(source_path)
    print(f"  Loaded {len(df)} rows, {len(df.columns)} columns in {time.time()-t0:.1f}s")

    # Sort by symbol+date for correct shift
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Apply T-1 shift: for each symbol, shift chip columns by 1 row
    for col in CHIP_COLS:
        if col in df.columns:
            df[col] = df.groupby("symbol")[col].shift(1)
            # First row per symbol becomes NaN - fill with 0
            df[col] = df[col].fillna(0.0)

    df.to_parquet(dest_path, index=False)
    print(f"  T-1 cache written to {dest_path.name} ({dest_path.stat().st_size/1e6:.1f}MB) in {time.time()-t0:.1f}s")


def main():
    print(f"U95 Reproduction Script v2")
    print(f"Exclusion count: {len(ALL_EXCLUDED)}")
    assert len(ALL_EXCLUDED) == 58, f"Expected 58, got {len(ALL_EXCLUDED)}"
    print(f"Reference: HC={REF['hc_accuracy']:.4%}, Wilson={REF['wilson_lower_95']:.4%}")
    print()

    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 3, 31),
        seed=42,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=tuple(ALL_EXCLUDED),
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )

    cfg = get_default_config()
    store = LocalDataStore(cfg)

    # Step 1: Find what fingerprint the current env computes
    # We need to get symbols first (same way gpu_probe does internally)
    from ashare_similarity.prediction.gpu_probe import _hash_payload

    # The fresh cache we just built has the correct fingerprint for current env
    # Check if it exists
    fresh_cache = CACHE_DIR / "gpu_probe_features_29fad3014f118dc1.parquet"
    if not fresh_cache.exists():
        print(f"ERROR: Fresh cache not found. Need to identify current fingerprint.")
        print("Looking for most recent cache...")
        caches = sorted(CACHE_DIR.glob("gpu_probe_features_*.parquet"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        for c in caches[:3]:
            if '_t1shifted' not in c.stem:
                fresh_cache = c
                print(f"  Using: {c.name}")
                break

    fingerprint = fresh_cache.stem.replace("gpu_probe_features_", "")
    print(f"Current env fingerprint: {fingerprint}")

    # Step 2: Build T-1 shifted version of the fresh cache
    t1_cache = CACHE_DIR / f"gpu_probe_features_{fingerprint}_t1shifted.parquet"
    if not t1_cache.exists():
        _build_t1_shifted_cache(fresh_cache, t1_cache)
    else:
        print(f"  T-1 cache already exists: {t1_cache.name}")

    # Step 3: Swap the T-1 cache into position
    backup_path = fresh_cache.with_suffix(".parquet.repro_bak")
    fresh_meta = fresh_cache.with_suffix(".json")
    backup_meta = fresh_meta.with_suffix(".json.repro_bak") if fresh_meta.exists() else None

    print(f"\nSwapping T-1 cache into position...")
    t0 = time.time()
    try:
        fresh_cache.rename(backup_path)
        if fresh_meta.exists():
            fresh_meta.rename(backup_meta)

        shutil.copy2(t1_cache, fresh_cache)
        # Write minimal metadata
        if backup_meta and backup_meta.exists():
            shutil.copy2(backup_meta, fresh_meta)

        print("  Running gpu_probe with T-1 shifted data...")
        result = run_gpu_next_day_probe(store, config)
    finally:
        # Restore original
        if fresh_cache.exists():
            fresh_cache.unlink()
        if fresh_meta.exists():
            fresh_meta.unlink(missing_ok=True)
        if backup_path.exists():
            backup_path.rename(fresh_cache)
        if backup_meta and backup_meta.exists():
            backup_meta.rename(fresh_meta)
        print("  Restored original cache.")

    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.1f}s")

    # Extract metrics
    hc_acc = result.get("confident_accuracy", 0)
    wilson = result.get("acceptance", {}).get("high_confidence", {}).get("wilson_lower_95", 0)
    if wilson == 0:
        wilson = result.get("wilson_lower_95", 0)
    hc_count = result.get("confident_count", 0)
    coverage = result.get("confident_coverage", 0)
    brier = result.get("brier", 0)
    sel_count = result.get("feature_selection", {}).get("selected_feature_count", 0)
    if sel_count == 0:
        sel_count = result.get("selected_feature_count", 0)

    print(f"\n{'='*60}")
    print(f"REPRODUCTION RESULTS vs REFERENCE")
    print(f"{'='*60}")
    print(f"{'Metric':<25} {'Reproduced':>12} {'Reference':>12} {'Delta':>10}")
    print(f"{'-'*60}")

    metrics = [
        ("HC Accuracy", hc_acc, REF["hc_accuracy"]),
        ("Wilson Lower 95%", wilson, REF["wilson_lower_95"]),
        ("HC Count", hc_count, REF["hc_count"]),
        ("Coverage", coverage, REF["hc_coverage"]),
        ("Brier", brier, REF["brier"]),
        ("Selected Features", sel_count, REF["selected_features"]),
    ]

    all_pass = True
    for name, repro, ref in metrics:
        if isinstance(ref, int):
            delta = repro - ref
            print(f"{name:<25} {repro:>12} {ref:>12} {delta:>+10}")
            if name == "Selected Features" and repro != ref:
                all_pass = False
        else:
            delta_pp = (repro - ref) * 100
            print(f"{name:<25} {repro:>12.6f} {ref:>12.6f} {delta_pp:>+10.4f}pp")
            if name in ("HC Accuracy", "Wilson Lower 95%") and abs(delta_pp) > 0.3:
                all_pass = False

    print(f"\n{'='*60}")
    if all_pass:
        print("PASS: U95 successfully reproduced within tolerance.")
    else:
        print("FAIL: Reproduction exceeds 0.3pp tolerance.")
        print("NOTE: Check if fingerprint/data drift is the cause.")
    print(f"{'='*60}")

    return result


if __name__ == "__main__":
    main()
