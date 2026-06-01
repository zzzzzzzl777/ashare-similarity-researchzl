"""Phase 7: Seed stability for top smoke candidates.

Tests C154, C158, C154+C158 pair, and baseline across 5 seeds.
Combined with seed=42 from Phase 5, gives 6 data points per variant.
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

LEDGER_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\experiment_ledger_20260507.jsonl")

ALL_DAILY_OHLCV_COLS = (
    "tushare_price_vs_cost_20d",
    "tushare_abnormal_3d_deviation",
    "tushare_vol_gain_20d",
    "tushare_inv_t_20d",
    "tushare_asr_60d",
    "tushare_illiq_classic_20d",
    "tushare_ato_120d",
)
ALL_MINUTE_COLS = (
    "tushare_last_30min_return",
    "tushare_first_15min_volume_ratio",
    "tushare_intraday_volatility",
    "tushare_up_volume_ratio",
    "tushare_high_time_pct",
)

def _make_exclude(include_daily=(), include_minute=()):
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


STABILITY_VARIANTS = [
    ("SEED_baseline", _make_exclude(), ["C004", "C009", "C011"]),
    ("SEED_C154", _make_exclude(include_daily=("tushare_price_vs_cost_20d",)), ["C004", "C009", "C011", "C154"]),
    ("SEED_C158", _make_exclude(include_daily=("tushare_inv_t_20d",)), ["C004", "C009", "C011", "C158"]),
    ("SEED_C154_C158", _make_exclude(include_daily=("tushare_price_vs_cost_20d", "tushare_inv_t_20d")), ["C004", "C009", "C011", "C154", "C158"]),
]

SEEDS = [1, 2, 3, 4, 5]


def _append_ledger(entry: dict) -> None:
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def run_variant(variant_name: str, exclude_features: tuple[str, ...], used_factor_ids: list[str], seed: int) -> dict:
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

    full_name = f"{variant_name}_s{seed}"
    print(f"\n{'='*60}")
    print(f"Running: {full_name}")
    print(f"{'='*60}")

    t0 = time.time()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0

    metrics = result.get("metrics", result)
    hc_acc = metrics.get("confident_accuracy", 0)
    wilson = metrics.get("acceptance", {}).get("high_confidence", {}).get("wilson_lower_95", 0)
    hc_count = metrics.get("confident_count", 0)
    coverage = metrics.get("confident_coverage", 0)
    brier = metrics.get("brier", 0)

    print(f"  HC acc={hc_acc:.4f} Wilson={wilson:.4f} count={hc_count} cov={coverage:.4f} brier={brier:.5f} ({elapsed:.0f}s)")

    _append_ledger({
        "run_id": result.get("run_id", "unknown"),
        "variant": full_name,
        "phase": "seed_stability",
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
    })
    return result


def main():
    print("Phase 7 — Seed Stability Testing")
    print(f"Variants: {len(STABILITY_VARIANTS)}")
    print(f"Seeds: {SEEDS}")
    print(f"Total runs: {len(STABILITY_VARIANTS) * len(SEEDS)}")
    print()

    for variant_name, exclude_features, factor_ids in STABILITY_VARIANTS:
        for seed in SEEDS:
            run_variant(variant_name, exclude_features, factor_ids, seed)

    print("\n" + "="*60)
    print("SEED STABILITY COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
