"""Reproduce U95_chip_t1_no_ths_live_strict metrics.

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
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

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

# Reference metrics
REF = {
    "hc_accuracy": 0.754243,
    "wilson_lower_95": 0.746116,
    "hc_count": 11019,
    "hc_coverage": 0.256107,
    "brier": 0.219497,
    "selected_features": 260,
}


def main():
    print(f"U95 Reproduction Script")
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

    # U95 uses T-1 shifted cache for chip features
    # Same swap mechanism as run_1457_unavailable_factor_compare.py
    Q1_CACHE_FP = "50f0a15cc17d25ca"
    T1_SUFFIX = "_t1shifted"
    superset_path = CACHE_DIR / f"gpu_probe_features_{Q1_CACHE_FP}.parquet"
    superset_meta = superset_path.with_suffix(".json")
    t1_path = CACHE_DIR / f"gpu_probe_features_{Q1_CACHE_FP}{T1_SUFFIX}.parquet"
    t1_meta = CACHE_DIR / f"gpu_probe_features_{Q1_CACHE_FP}{T1_SUFFIX}.json"

    if not t1_path.exists():
        print(f"ERROR: T-1 cache not found at {t1_path}")
        print("Run 'python scripts/run_1457_unavailable_factor_compare.py build-t1-cache' first.")
        sys.exit(1)

    print(f"Using T-1 shifted cache: {t1_path.name}")
    print(f"Swapping superset cache temporarily...")

    import shutil
    backup_parquet = superset_path.with_suffix(".parquet.repro_bak")
    backup_meta = superset_meta.with_suffix(".json.repro_bak")

    t0 = time.time()
    try:
        superset_path.rename(backup_parquet)
        if superset_meta.exists():
            superset_meta.rename(backup_meta)

        shutil.copy2(t1_path, superset_path)
        if t1_meta.exists():
            shutil.copy2(t1_meta, superset_meta)
        else:
            orig_meta = {}
            if backup_meta.exists():
                with open(backup_meta, encoding="utf-8") as f:
                    orig_meta = json.load(f)
            meta = {
                "fingerprint": Q1_CACHE_FP,
                "columns": orig_meta.get("columns", []),
                "rows": orig_meta.get("rows", 370430),
                "created_at": "2026-05-08T04:44:59+00:00",
                "symbol_frames_kept": orig_meta.get("symbol_frames_kept", 2937),
            }
            with open(superset_meta, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

        result = run_gpu_next_day_probe(store, config)
    finally:
        if superset_path.exists():
            superset_path.unlink()
        if superset_meta.exists():
            superset_meta.unlink(missing_ok=True)
        if backup_parquet.exists():
            backup_parquet.rename(superset_path)
        if backup_meta.exists():
            backup_meta.rename(superset_meta)
        print("Restored original superset cache.")

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
        print("FAIL: Reproduction exceeds 0.3pp tolerance. HALT.")
    print(f"{'='*60}")

    return result


if __name__ == "__main__":
    main()
