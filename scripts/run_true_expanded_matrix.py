"""True All-Factor Expansion Manifest — Generated from factor_registry.json.

Uses ONLY the authoritative trainable universe (19 factors, correct IDs).
No hardcoded factor lists — everything derived from registry.

Categories:
  1. Controls: baseline, all_daily, all_minute, all_daily+minute, all_factors
  2. Single-factor: each of 19 trainable factors individually
  3. Family smoke: each family group (multi-member families only)
  4. Pairwise: top candidates (C154, C158) paired with each other factor
  5. Greedy forward: add factors one at a time by prior rank
  6. Backward pruning: remove one factor at a time from all-daily
  7. (Seed/budget stability deferred to after initial results)

All runs: lockbox_role=seen_research, final_acceptance_eligible=False, Q1 2026 only.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
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
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")


def load_trainable_universe():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        registry = json.load(f)

    all_factors = []
    def find_factors(obj):
        if isinstance(obj, dict):
            if "factor_id" in obj:
                all_factors.append(obj)
            for v in obj.values():
                find_factors(v)
        elif isinstance(obj, list):
            for item in obj:
                find_factors(item)
    find_factors(registry)

    trainable = {}
    for f in all_factors:
        status = f.get("engineering_status", "")
        col = f.get("column_name", "")
        fid = f.get("factor_id", "")
        family = f.get("family", "")
        if status in ("existing_engineered", "verified_engineerable") and col and fid:
            trainable[fid] = {"column": col, "family": family}
    return trainable


def classify_factors(trainable):
    daily_ohlcv_factors = {}
    minute_factors = {}
    other_factors = {}

    minute_columns = {
        "tushare_last_30min_return", "tushare_first_15min_volume_ratio",
        "tushare_intraday_volatility", "tushare_up_volume_ratio", "tushare_high_time_pct",
    }
    daily_ohlcv_columns = {
        "tushare_price_vs_cost_20d", "tushare_abnormal_3d_deviation", "tushare_vol_gain_20d",
        "tushare_inv_t_20d", "tushare_asr_60d", "tushare_illiq_classic_20d", "tushare_ato_120d",
        "tushare_prev_top20_chase_mean", "tushare_volume_sufficiency_ratio",
        "tushare_anti_drop_strength_20d", "tushare_multi_wave_count_60d",
    }

    for fid, info in trainable.items():
        col = info["column"]
        if col in minute_columns:
            minute_factors[fid] = info
        elif col in daily_ohlcv_columns:
            daily_ohlcv_factors[fid] = info
        else:
            other_factors[fid] = info

    return daily_ohlcv_factors, minute_factors, other_factors


def _make_exclude(trainable, include_ids):
    all_cols = set()
    for fid, info in trainable.items():
        all_cols.add(info["column"])
        all_cols.add(f"{info['column']}_available")

    include_cols = set()
    for fid in include_ids:
        if fid in trainable:
            include_cols.add(trainable[fid]["column"])
            include_cols.add(f"{trainable[fid]['column']}_available")

    return tuple(sorted(all_cols - include_cols))


def build_manifest():
    trainable = load_trainable_universe()
    daily, minute, other = classify_factors(trainable)

    all_fids = sorted(trainable.keys())
    daily_fids = sorted(daily.keys())
    minute_fids = sorted(minute.keys())
    other_fids = sorted(other.keys())

    # Base factor IDs always present (not in exclude logic)
    base_ids = ["C004", "C009", "C011"]

    variants = []
    seen = set()

    def _add(name, include_ids):
        key = tuple(sorted(include_ids))
        if key in seen:
            return
        seen.add(key)
        exclude = _make_exclude(trainable, include_ids)
        variants.append((name, exclude, base_ids + [fid for fid in sorted(include_ids) if fid not in base_ids]))

    # --- Category 1: Controls ---
    _add("TRUE_baseline", base_ids)
    _add("TRUE_daily_ohlcv_all", base_ids + daily_fids)
    _add("TRUE_minute_all", base_ids + minute_fids)
    _add("TRUE_daily_plus_minute", base_ids + daily_fids + minute_fids)
    _add("TRUE_all_19_factors", all_fids)

    # --- Category 2: Single-factor ---
    for fid in all_fids:
        _add(f"TRUE_single_{fid}", base_ids + [fid])

    # --- Category 3: Family smoke (multi-member only) ---
    families = defaultdict(list)
    for fid, info in trainable.items():
        families[info["family"]].append(fid)
    for fam_name, fam_fids in sorted(families.items()):
        if len(fam_fids) >= 2:
            _add(f"TRUE_family_{fam_name}", base_ids + sorted(fam_fids))

    # --- Category 4: Pairwise (C154 + each, C158 + each) ---
    for anchor in ["C154", "C158"]:
        for fid in all_fids:
            if fid == anchor or fid in base_ids:
                continue
            _add(f"TRUE_pair_{anchor}_{fid}", base_ids + [anchor, fid])

    # --- Category 5: Greedy forward (from seed stability rank) ---
    greedy_order = ["C154", "C158", "C161", "C159", "C156", "C162", "C157",
                    "C141", "C143", "C151", "C152", "C133", "C134", "C136", "C137", "C138"]
    for i in range(2, len(greedy_order) + 1):
        included = greedy_order[:i]
        _add(f"TRUE_greedy_top{i}", base_ids + included)

    # --- Category 6: Backward pruning (from all daily, remove one) ---
    for fid in daily_fids:
        remaining = [f for f in daily_fids if f != fid]
        _add(f"TRUE_prune_no_{fid}", base_ids + remaining)

    return variants, trainable


def _append_ledger(entry: dict) -> None:
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def run_variant(variant_name, exclude_features, used_factor_ids):
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
    print(f"  Factors: {used_factor_ids}")
    print(f"  Excluded features: {len(exclude_features)}")
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

    print(f"  HC acc={hc_acc:.4f} Wilson={wilson:.4f} count={hc_count} cov={coverage:.4f} ({elapsed:.0f}s)")

    _append_ledger({
        "run_id": result.get("run_id", "unknown"),
        "variant": variant_name,
        "phase": "true_expanded_matrix",
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
    variants, trainable = build_manifest()
    print(f"True All-Factor Expansion Manifest")
    print(f"Trainable universe: {len(trainable)} factors")
    print(f"Total variants: {len(variants)}")
    print()

    # Save manifest JSON
    manifest_data = {
        "report_date": "2026-05-07",
        "report_type": "true_all_factor_expansion_manifest",
        "trainable_universe": {fid: info for fid, info in sorted(trainable.items())},
        "total_variants": len(variants),
        "variants": [
            {"variant_name": name, "used_factor_ids": fids, "excluded_feature_count": len(exc)}
            for name, exc, fids in variants
        ],
    }
    manifest_path = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\true_all_factor_expansion_manifest_20260507.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)
    print(f"Manifest saved: {manifest_path}")
    print()

    for i, (name, exclude, fids) in enumerate(variants):
        print(f"\n[{i+1}/{len(variants)}]")
        run_variant(name, exclude, fids)

    print("\n" + "=" * 60)
    print("TRUE EXPANDED MATRIX COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
