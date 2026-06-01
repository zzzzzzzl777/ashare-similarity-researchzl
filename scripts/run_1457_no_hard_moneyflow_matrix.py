"""14:57 Hard-Unavailable-Excluded Runner — Wraps superset runner for this round.

Reads 1457_no_hard_moneyflow_variant_manifest_20260507.json.
Uses existing superset cache (fingerprint 50f0a15cc17d25ca).
All variants globally exclude 14 hard-unavailable columns.
C004/C009 never enter formal training.

CLI:
  python scripts/run_1457_no_hard_moneyflow_matrix.py dry-run-variant M1457_control_no_hard_moneyflow
  python scripts/run_1457_no_hard_moneyflow_matrix.py run-single-variant M1457_control_no_hard_moneyflow
  python scripts/run_1457_no_hard_moneyflow_matrix.py run-smoke
  python scripts/run_1457_no_hard_moneyflow_matrix.py run-all-variants
  python scripts/run_1457_no_hard_moneyflow_matrix.py run-category <category>
  python scripts/run_1457_no_hard_moneyflow_matrix.py summarize
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

MANIFEST_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\1457_no_hard_moneyflow_variant_manifest_20260507.json")
LEDGER_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\experiment_ledger_20260507.jsonl")
CACHE_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache")

HARD_UNAVAILABLE_FEATURES = [
    "tushare_net_mf_amount", "tushare_net_mf_amount_available",
    "tushare_lg_buy_sell_ratio", "tushare_lg_buy_sell_ratio_available",
    "tushare_elg_buy_sell_ratio", "tushare_elg_buy_sell_ratio_available",
    "tushare_mf_strength", "tushare_mf_strength_available",
    "tushare_sm_sell_pressure", "tushare_sm_sell_pressure_available",
    "tushare_main_force_divergence", "tushare_main_force_divergence_available",
    "tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available",
]

SMOKE_VARIANTS = [
    "M1457_control_no_hard_moneyflow",
    "M1457_C011_only",
    "M1457_existing_engineered_all_without_C004_C009",
]


def _find_superset_cache() -> Path | None:
    """Find valid superset cache with all required columns."""
    all_required = [
        "tushare_auction_open_vwap_ratio",
        "tushare_last_30min_return",
        "tushare_first_15min_volume_ratio",
        "tushare_intraday_volatility",
        "tushare_up_volume_ratio",
        "tushare_high_time_pct",
        "tushare_prev_top20_chase_mean",
        "tushare_volume_sufficiency_ratio",
        "tushare_anti_drop_strength_20d",
        "tushare_multi_wave_count_60d",
        "tushare_price_vs_cost_20d",
        "tushare_abnormal_3d_deviation",
        "tushare_vol_gain_20d",
        "tushare_inv_t_20d",
        "tushare_asr_60d",
        "tushare_illiq_classic_20d",
        "tushare_ato_120d",
    ]
    import os
    candidates = []
    for f in CACHE_DIR.glob("gpu_probe_features_*.json"):
        try:
            with open(f, encoding="utf-8") as fh:
                meta = json.load(fh)
            cols = set(meta.get("columns", []))
            if all(c in cols for c in all_required):
                parquet = f.with_suffix(".parquet")
                if parquet.exists():
                    candidates.append((parquet, os.path.getmtime(parquet)))
        except Exception:
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def _load_manifest() -> dict:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def _base_config(*, exclude_names: tuple, seed: int = 42, max_selected: int = 260) -> GpuProbeConfig:
    return GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 3, 31),
        seed=seed,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=max_selected,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=exclude_names,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )


def _p0_check(variant: dict, result: dict) -> list[str]:
    """Check P0 stop conditions after a run."""
    issues = []
    selected = result.get("selected_features", [])
    input_features = result.get("input_features", [])

    for feat in HARD_UNAVAILABLE_FEATURES:
        if feat in selected:
            issues.append(f"P0: hard_unavailable '{feat}' in selected_features")
        if feat in input_features:
            issues.append(f"P0: hard_unavailable '{feat}' in input_features")

    c004_c009_cols = ["tushare_ff_adjusted_flow", "tushare_main_force_divergence",
                      "tushare_ff_adjusted_flow_available", "tushare_main_force_divergence_available"]
    for feat in c004_c009_cols:
        if feat in selected:
            issues.append(f"P0: C004/C009 feature '{feat}' in selected_features")

    return issues


def _run_variant(variant: dict, *, seed: int = 42, max_selected: int = 260) -> dict:
    """Execute a single variant."""
    name = variant["variant_name"]
    exclude = tuple(variant["excluded_feature_names"])
    included_fids = variant.get("included_factor_ids", [])

    cfg = get_default_config()
    store = LocalDataStore(cfg)
    config = _base_config(exclude_names=exclude, seed=seed, max_selected=max_selected)

    print(f"{'=' * 60}")
    print(f"Running: {name} (seed={seed}, max_sel={max_selected})")
    print(f"  Included factors: {included_fids}")
    print(f"  Excluded features: {len(exclude)}")
    print(f"{'=' * 60}")

    t0 = time.time()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0

    if result.get("status") == "insufficient_samples":
        print(f"  RESULT: insufficient_samples (skipping)")
        return result

    metrics = result.get("metrics", result)
    hc_acc = metrics.get("confident_accuracy", 0)
    acceptance = metrics.get("acceptance", {})
    hc_info = acceptance.get("high_confidence", {})
    wilson = hc_info.get("wilson_lower_95", 0)
    hc_count = metrics.get("confident_count", 0)
    coverage = metrics.get("confident_coverage", 0)
    brier = metrics.get("brier", 0)

    print(f"  HC acc={hc_acc:.4f} Wilson={wilson:.4f} count={hc_count} cov={coverage:.4f} brier={brier:.4f} ({elapsed:.0f}s)")

    # P0 check
    p0_issues = _p0_check(variant, result)
    if p0_issues:
        print(f"\n  *** P0 STOP ***")
        for issue in p0_issues:
            print(f"  {issue}")
        sys.exit(1)

    # Write ledger
    selected_features = result.get("selected_features", [])
    _append_ledger({
        "run_id": result.get("run_id", "unknown"),
        "artifact_path": result.get("artifact_path", ""),
        "variant": name,
        "category": variant.get("category", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_hash": result.get("code_hash", ""),
        "data_hash": result.get("data_hash", ""),
        "feature_hash": result.get("feature_hash", ""),
        "config_hash": result.get("config_hash", ""),
        "dirty_git_status": "recorded_not_blocking",
        "seed": seed,
        "max_selected_features": max_selected,
        "used_factor_ids": included_fids,
        "included_factor_ids": included_fids,
        "excluded_factor_ids": variant.get("excluded_factor_ids", []),
        "hard_excluded_feature_names": HARD_UNAVAILABLE_FEATURES,
        "excluded_feature_count": len(exclude),
        "selected_features_count": len(selected_features),
        "selected_features": selected_features,
        "hc_accuracy": hc_acc,
        "wilson_lower_95": wilson,
        "hc_count": hc_count,
        "coverage": coverage,
        "brier": brier,
        "elapsed_seconds": elapsed,
        "lockbox_role": "seen_research",
        "final_acceptance_eligible": False,
        "note": variant.get("note", ""),
    })

    return result


def _append_ledger(entry: dict) -> None:
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def dry_run_variant(variant_name: str):
    """Show what a variant would do without executing."""
    manifest = _load_manifest()
    target = None
    for v in manifest["variants"]:
        if v["variant_name"] == variant_name:
            target = v
            break
    if target is None:
        print(f"ERROR: '{variant_name}' not in manifest.")
        available = [v["variant_name"] for v in manifest["variants"][:20]]
        print(f"Available (first 20): {available}")
        sys.exit(1)

    cache_path = _find_superset_cache()
    if cache_path is None:
        print("P1: No superset cache found.")
        sys.exit(1)

    meta_path = cache_path.with_suffix(".json")
    with open(meta_path) as f:
        meta = json.load(f)
    all_cols = set(meta["columns"])
    exclude = set(target["excluded_feature_names"])
    available = [c for c in meta["columns"] if c not in exclude]

    # Verify hard exclusion
    hard_in_available = [c for c in HARD_UNAVAILABLE_FEATURES if c in set(available)]

    print(f"DRY-RUN: {variant_name}")
    print(f"  Category: {target['category']}")
    print(f"  Included factors: {target['included_factor_ids']}")
    print(f"  Excluded factors: {target['excluded_factor_ids']}")
    print(f"  Total cache cols: {len(all_cols)}")
    print(f"  Excluded cols: {len(exclude)}")
    print(f"  Available for training: {len(available)}")
    print(f"  Hard unavailable in available: {len(hard_in_available)}")
    if hard_in_available:
        print(f"  *** P0: hard unavailable features would enter training! ***")
        for f in hard_in_available:
            print(f"    {f}")
        sys.exit(1)
    print(f"  Status: READY (no P0/P1)")


def run_smoke():
    """Run only the 3 smoke variants."""
    manifest = _load_manifest()
    smoke = [v for v in manifest["variants"] if v["variant_name"] in SMOKE_VARIANTS]
    if len(smoke) != 3:
        print(f"ERROR: Expected 3 smoke variants, found {len(smoke)}")
        sys.exit(1)
    print(f"SMOKE: Running {len(smoke)} variants")
    for v in smoke:
        _run_variant(v)
    print("\nSMOKE COMPLETE — all 3 variants passed")


def run_category(category: str):
    """Run all variants in a specific category."""
    manifest = _load_manifest()
    targets = [v for v in manifest["variants"] if v["category"] == category]
    if not targets:
        cats = set(v["category"] for v in manifest["variants"])
        print(f"ERROR: category '{category}' not found. Available: {sorted(cats)}")
        sys.exit(1)
    print(f"Running {len(targets)} variants in category '{category}'")
    for i, v in enumerate(targets):
        print(f"\n[{i+1}/{len(targets)}]")
        if category == "budget_stability":
            budget = int(v["variant_name"].split("_")[2])
            _run_variant(v, max_selected=budget)
        elif category == "seed_stability":
            seed = int(v["variant_name"].split("_")[1].replace("seed", ""))
            _run_variant(v, seed=seed)
        else:
            _run_variant(v)
    print(f"\nCategory '{category}' COMPLETE ({len(targets)} variants)")


def run_all_variants():
    """Run all 143 variants sequentially."""
    manifest = _load_manifest()
    variants = manifest["variants"]
    print(f"Running ALL {len(variants)} variants")
    for i, v in enumerate(variants):
        print(f"\n[{i+1}/{len(variants)}]")
        cat = v["category"]
        if cat == "budget_stability":
            budget = int(v["variant_name"].split("_")[2])
            _run_variant(v, max_selected=budget)
        elif cat == "seed_stability":
            seed = int(v["variant_name"].split("_")[1].replace("seed", ""))
            _run_variant(v, seed=seed)
        else:
            _run_variant(v)
    print(f"\nALL {len(variants)} VARIANTS COMPLETE")


def summarize():
    """Print summary from ledger."""
    if not LEDGER_PATH.exists():
        print("No ledger found.")
        return
    entries = []
    with open(LEDGER_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    print(f"Total ledger entries: {len(entries)}")
    print(f"\n{'Variant':<55} {'HC Acc':>7} {'Wilson':>7} {'Count':>6} {'Cov':>6}")
    print("-" * 85)
    for e in sorted(entries, key=lambda x: x.get("wilson_lower_95", 0), reverse=True)[:30]:
        print(f"{e['variant']:<55} {e.get('hc_accuracy',0):>7.4f} {e.get('wilson_lower_95',0):>7.4f} {e.get('hc_count',0):>6} {e.get('coverage',0):>6.4f}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/run_1457_no_hard_moneyflow_matrix.py dry-run-variant <name>")
        print("  python scripts/run_1457_no_hard_moneyflow_matrix.py run-single-variant <name>")
        print("  python scripts/run_1457_no_hard_moneyflow_matrix.py run-smoke")
        print("  python scripts/run_1457_no_hard_moneyflow_matrix.py run-category <category>")
        print("  python scripts/run_1457_no_hard_moneyflow_matrix.py run-all-variants")
        print("  python scripts/run_1457_no_hard_moneyflow_matrix.py summarize")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "dry-run-variant":
        dry_run_variant(sys.argv[2])
    elif cmd == "run-single-variant":
        run_single_variant(sys.argv[2])
    elif cmd == "run-smoke":
        run_smoke()
    elif cmd == "run-category":
        run_category(sys.argv[2])
    elif cmd == "run-all-variants":
        run_all_variants()
    elif cmd == "summarize":
        summarize()
    else:
        print(f"Unknown: {cmd}")
        sys.exit(1)


def run_single_variant(variant_name: str):
    manifest = _load_manifest()
    target = None
    for v in manifest["variants"]:
        if v["variant_name"] == variant_name:
            target = v
            break
    if target is None:
        print(f"ERROR: '{variant_name}' not found in manifest.")
        sys.exit(1)
    cat = target["category"]
    if cat == "budget_stability":
        budget = int(target["variant_name"].split("_")[2])
        _run_variant(target, max_selected=budget)
    elif cat == "seed_stability":
        seed = int(target["variant_name"].split("_")[1].replace("seed", ""))
        _run_variant(target, seed=seed)
    else:
        _run_variant(target)


if __name__ == "__main__":
    main()
