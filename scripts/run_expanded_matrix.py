"""Expanded Variant Manifest — Full training matrix.

Categories:
  1. Controls: baseline, daily_ohlcv_all_r1, daily_ohlcv_all_r1r2, minute_all, daily+minute
  2. Single-factor: each of 11 daily OHLCV + 5 minute factors individually
  3. Family smoke: each family as a group
  4. Pairwise top candidates: C154 paired with each other factor
  5. Greedy forward: start from C154, add one factor at a time by rank
  6. Backward pruning: start from all, remove one at a time
  7. Seed stability: top 3-5 variants from smoke (deferred to after initial run)
  8. Budget stability: top 3-5 with reduced max_features (deferred)

All runs: lockbox_role=seen_research, final_acceptance_eligible=False, Q1 2026 only.
"""
from __future__ import annotations

import json
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

ALL_DAILY_R1 = (
    "tushare_price_vs_cost_20d",
    "tushare_abnormal_3d_deviation",
    "tushare_vol_gain_20d",
    "tushare_inv_t_20d",
    "tushare_asr_60d",
    "tushare_illiq_classic_20d",
    "tushare_ato_120d",
)
ALL_DAILY_R2 = (
    "tushare_prev_top20_chase_mean",
    "tushare_volume_sufficiency_ratio",
    "tushare_anti_drop_strength_20d",
    "tushare_multi_wave_count_60d",
)
ALL_DAILY = ALL_DAILY_R1 + ALL_DAILY_R2

ALL_MINUTE = (
    "tushare_last_30min_return",
    "tushare_first_15min_volume_ratio",
    "tushare_intraday_volatility",
    "tushare_up_volume_ratio",
    "tushare_high_time_pct",
)

FACTOR_META = {
    "tushare_price_vs_cost_20d": ("C154", "price_momentum"),
    "tushare_abnormal_3d_deviation": ("C156", "price_momentum"),
    "tushare_vol_gain_20d": ("C157", "volume_quality"),
    "tushare_inv_t_20d": ("C158", "volume_quality"),
    "tushare_asr_60d": ("C159", "relative_strength"),
    "tushare_illiq_classic_20d": ("C161", "liquidity"),
    "tushare_ato_120d": ("C162", "volume_quality"),
    "tushare_prev_top20_chase_mean": ("C141", "market_breadth"),
    "tushare_volume_sufficiency_ratio": ("C143", "volume_quality"),
    "tushare_anti_drop_strength_20d": ("C151", "relative_strength"),
    "tushare_multi_wave_count_60d": ("C152", "technical_pattern"),
    "tushare_last_30min_return": ("M001", "intraday_momentum"),
    "tushare_first_15min_volume_ratio": ("M002", "intraday_volume"),
    "tushare_intraday_volatility": ("M003", "intraday_volatility"),
    "tushare_up_volume_ratio": ("M004", "intraday_volume"),
    "tushare_high_time_pct": ("M005", "intraday_timing"),
}

FAMILIES = {
    "price_momentum": ["tushare_price_vs_cost_20d", "tushare_abnormal_3d_deviation"],
    "volume_quality": ["tushare_vol_gain_20d", "tushare_inv_t_20d", "tushare_ato_120d", "tushare_volume_sufficiency_ratio"],
    "relative_strength": ["tushare_asr_60d", "tushare_anti_drop_strength_20d"],
    "liquidity": ["tushare_illiq_classic_20d"],
    "market_breadth": ["tushare_prev_top20_chase_mean"],
    "technical_pattern": ["tushare_multi_wave_count_60d"],
    "intraday_momentum": ["tushare_last_30min_return"],
    "intraday_volume": ["tushare_first_15min_volume_ratio", "tushare_up_volume_ratio"],
    "intraday_volatility": ["tushare_intraday_volatility"],
    "intraday_timing": ["tushare_high_time_pct"],
}


def _make_exclude(include_daily=(), include_minute=()):
    exclude = []
    for col in ALL_DAILY:
        if col not in include_daily:
            exclude.append(col)
            exclude.append(f"{col}_available")
    for col in ALL_MINUTE:
        if col not in include_minute:
            exclude.append(col)
            exclude.append(f"{col}_available")
    return tuple(exclude)


def build_manifest():
    variants = []
    seen_excludes = set()

    def _add(name, exclude, fids):
        key = (tuple(sorted(exclude)), tuple(sorted(fids)))
        if key in seen_excludes:
            return
        seen_excludes.add(key)
        variants.append((name, exclude, fids))

    # --- Category 1: Controls ---
    _add("EXP_baseline", _make_exclude(), ["C004", "C009", "C011"])
    _add("EXP_daily_r1_all", _make_exclude(include_daily=ALL_DAILY_R1), ["C004", "C009", "C011"] + [FACTOR_META[c][0] for c in ALL_DAILY_R1])
    _add("EXP_daily_r1r2_all", _make_exclude(include_daily=ALL_DAILY), ["C004", "C009", "C011"] + [FACTOR_META[c][0] for c in ALL_DAILY])
    _add("EXP_minute_all", _make_exclude(include_minute=ALL_MINUTE), ["C004", "C009", "C011"] + [FACTOR_META[c][0] for c in ALL_MINUTE])
    _add("EXP_daily_r1r2_plus_minute", _make_exclude(include_daily=ALL_DAILY, include_minute=ALL_MINUTE), ["C004", "C009", "C011"] + [FACTOR_META[c][0] for c in ALL_DAILY] + [FACTOR_META[c][0] for c in ALL_MINUTE])

    # --- Category 2: Single-factor (daily) ---
    for col in ALL_DAILY:
        fid, fam = FACTOR_META[col]
        _add(f"EXP_single_{fid}", _make_exclude(include_daily=(col,)), ["C004", "C009", "C011", fid])

    # --- Category 2b: Single-factor (minute) ---
    for col in ALL_MINUTE:
        fid, fam = FACTOR_META[col]
        _add(f"EXP_single_{fid}", _make_exclude(include_minute=(col,)), ["C004", "C009", "C011", fid])

    # --- Category 3: Family smoke (skip single-member families, they're duplicates) ---
    for fam_name, fam_cols in FAMILIES.items():
        if len(fam_cols) < 2:
            continue
        daily_in = tuple(c for c in fam_cols if c in ALL_DAILY)
        minute_in = tuple(c for c in fam_cols if c in ALL_MINUTE)
        if not daily_in and not minute_in:
            continue
        fids = [FACTOR_META[c][0] for c in fam_cols]
        _add(f"EXP_family_{fam_name}", _make_exclude(include_daily=daily_in, include_minute=minute_in), ["C004", "C009", "C011"] + fids)

    # --- Category 4: Pairwise (C154 + each other daily factor) ---
    c154_col = "tushare_price_vs_cost_20d"
    for col in ALL_DAILY:
        if col == c154_col:
            continue
        fid = FACTOR_META[col][0]
        _add(f"EXP_pair_C154_{fid}", _make_exclude(include_daily=(c154_col, col)), ["C004", "C009", "C011", "C154", fid])

    # --- Category 5: Greedy forward (start from C154, add by Round5 rank order) ---
    greedy_order = [
        "tushare_price_vs_cost_20d",   # C154 (best)
        "tushare_inv_t_20d",           # C158 (2nd)
        "tushare_illiq_classic_20d",   # C161 (3rd)
        "tushare_asr_60d",            # C159 (4th)
        "tushare_abnormal_3d_deviation",  # C156 (5th)
        "tushare_ato_120d",           # C162 (6th)
        "tushare_vol_gain_20d",       # C157 (7th/harmful)
        # Round 2 added at end (untested in original smoke)
        "tushare_prev_top20_chase_mean",
        "tushare_volume_sufficiency_ratio",
        "tushare_anti_drop_strength_20d",
        "tushare_multi_wave_count_60d",
    ]
    for i in range(2, len(greedy_order) + 1):
        included = tuple(greedy_order[:i])
        fids = [FACTOR_META[c][0] for c in included]
        _add(f"EXP_greedy_top{i}", _make_exclude(include_daily=included), ["C004", "C009", "C011"] + fids)

    # --- Category 6: Backward pruning (start from all daily, remove one at a time) ---
    for col in ALL_DAILY:
        fid = FACTOR_META[col][0]
        included = tuple(c for c in ALL_DAILY if c != col)
        fids = [FACTOR_META[c][0] for c in included]
        _add(f"EXP_prune_no_{fid}", _make_exclude(include_daily=included), ["C004", "C009", "C011"] + fids)

    return variants


def _append_ledger(entry: dict) -> None:
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def run_variant(variant_name: str, exclude_features: tuple[str, ...], used_factor_ids: list[str]) -> dict:
    cfg = get_default_config()
    store = LocalDataStore(cfg)

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
        exclude_feature_names=exclude_features,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )

    print(f"\n{'='*60}")
    print(f"Running: {variant_name}")
    print(f"  Excluded: {len(exclude_features)} features")
    print(f"  Factor IDs: {used_factor_ids}")
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
        "variant": variant_name,
        "phase": "expanded_matrix",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": 42,
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
    variants = build_manifest()
    print(f"Expanded Variant Manifest: {len(variants)} variants")
    print()

    # Save manifest JSON
    manifest_json = []
    for name, exclude, fids in variants:
        manifest_json.append({
            "variant_name": name,
            "used_factor_ids": fids,
            "excluded_feature_count": len(exclude),
        })
    manifest_path = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\expanded_variant_manifest_20260507.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"total_variants": len(variants), "variants": manifest_json}, f, indent=2, ensure_ascii=False)
    print(f"Manifest saved to: {manifest_path}")
    print()

    for i, (name, exclude, fids) in enumerate(variants):
        print(f"\n[{i+1}/{len(variants)}]")
        run_variant(name, exclude, fids)

    print("\n" + "="*60)
    print("EXPANDED MATRIX COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
