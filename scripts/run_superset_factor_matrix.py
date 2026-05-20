"""Superset Factor Matrix Runner — Build once, train per variant.

Architecture:
  Phase A: build-superset-only
    - Loads 3063 symbols, attaches ALL factor features
    - Writes superset feature cache (all columns)
    - Validates: all 19 factor columns present and non-zero
    - Exits (no training)

  Phase B: run variants (from manifest)
    - Loads superset from cache (fast, ~5s)
    - Applies variant-specific column exclusions
    - Trains + evaluates LightGBM
    - Writes ledger entry + run directory

CLI:
  python scripts/run_superset_factor_matrix.py build-superset-only
  python scripts/run_superset_factor_matrix.py dry-run-variant TRUE_baseline
  python scripts/run_superset_factor_matrix.py run-single-variant TRUE_baseline
  python scripts/run_superset_factor_matrix.py run-all-variants
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
MANIFEST_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\true_all_factor_expansion_manifest_20260507.json")
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
CACHE_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache")

REQUIRED_FACTOR_COLUMNS = [
    "tushare_ff_adjusted_flow",
    "tushare_main_force_divergence",
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


def _base_config(*, refresh: bool = False) -> GpuProbeConfig:
    return GpuProbeConfig(
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
        exclude_feature_names=(),
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=refresh,
    )


def _validate_superset_cache(cache_path: Path) -> dict:
    """Validate the superset cache has all required columns with non-zero data."""
    import pandas as pd

    issues = []
    meta_path = cache_path.with_suffix(".json")
    if not cache_path.exists():
        return {"status": "FAIL", "issues": ["Cache file does not exist"]}
    if not meta_path.exists():
        return {"status": "FAIL", "issues": ["Cache metadata does not exist"]}

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    columns = meta.get("columns", [])
    rows = meta.get("rows", 0)

    # Check row count
    if rows < 350000 or rows > 400000:
        issues.append(f"Row count {rows} outside expected range [350k, 400k]")

    # Check factor columns exist
    missing_cols = [c for c in REQUIRED_FACTOR_COLUMNS if c not in columns]
    if missing_cols:
        issues.append(f"Missing factor columns: {missing_cols}")

    # Check availability columns
    missing_avail = [f"{c}_available" for c in REQUIRED_FACTOR_COLUMNS if f"{c}_available" not in columns]
    if missing_avail:
        issues.append(f"Missing availability columns: {missing_avail[:5]}...")

    # Check non-zero values (sample read)
    if not missing_cols:
        df = pd.read_parquet(cache_path, columns=REQUIRED_FACTOR_COLUMNS)
        zero_cols = []
        for col in REQUIRED_FACTOR_COLUMNS:
            if df[col].abs().sum() == 0:
                zero_cols.append(col)
        if zero_cols:
            issues.append(f"All-zero factor columns (P1 STOP): {zero_cols}")

    # Check date range
    if "date" in columns:
        df_dates = pd.read_parquet(cache_path, columns=["date"])
        date_min = pd.to_datetime(df_dates["date"]).min()
        date_max = pd.to_datetime(df_dates["date"]).max()
        if date_min > pd.Timestamp("2023-07-01"):
            issues.append(f"Date min {date_min} too late (expected <= 2023-07-01)")
        if date_max < pd.Timestamp("2026-03-01"):
            issues.append(f"Date max {date_max} too early (expected >= 2026-03-01)")

    status = "PASS" if not issues else "FAIL"
    return {
        "status": status,
        "cache_path": str(cache_path),
        "fingerprint": meta.get("fingerprint", "unknown"),
        "rows": rows,
        "columns_total": len(columns),
        "factor_columns_found": len(REQUIRED_FACTOR_COLUMNS) - len(missing_cols),
        "factor_columns_required": len(REQUIRED_FACTOR_COLUMNS),
        "issues": issues,
    }


def _find_superset_cache() -> Path | None:
    """Find a valid superset cache: most recent .json that has all required factor columns."""
    import os
    candidates = []
    for f in CACHE_DIR.glob("gpu_probe_features_*.json"):
        try:
            with open(f, encoding="utf-8") as fh:
                meta = json.load(fh)
            cols = set(meta.get("columns", []))
            if all(c in cols for c in REQUIRED_FACTOR_COLUMNS):
                parquet = f.with_suffix(".parquet")
                if parquet.exists():
                    candidates.append((parquet, os.path.getmtime(parquet)))
        except Exception:
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def build_superset_only():
    """Phase A: Build the superset feature cache."""
    print("=" * 60)
    print("SUPERSET BUILDER: Phase A — Build Feature Matrix")
    print("=" * 60)

    cfg = get_default_config()
    store = LocalDataStore(cfg)
    config = _base_config(refresh=True)

    print(f"Config: start={config.start} end={config.end} seed={config.seed}")
    print(f"Feature set: {config.feature_set}")
    print(f"Label: {config.label_target} target_pct={config.target_high_return_pct}")
    print(f"Exclusions: none (superset)")
    print()

    t0 = time.time()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0

    # Check result
    if result.get("status") == "insufficient_samples":
        print(f"FATAL: insufficient samples. Aborting.")
        sys.exit(1)

    metrics = result.get("metrics", result)
    hc_acc = metrics.get("confident_accuracy", 0)
    wilson = metrics.get("acceptance", {}).get("high_confidence", {}).get("wilson_lower_95", 0)
    hc_count = metrics.get("confident_count", 0)
    coverage = metrics.get("confident_coverage", 0)
    print(f"\nSuperset baseline result:")
    print(f"  HC acc={hc_acc:.4f} Wilson={wilson:.4f} count={hc_count} cov={coverage:.4f}")
    print(f"  Elapsed: {elapsed:.0f}s")

    # Validate cache
    cache_path = _find_superset_cache()
    if cache_path is None:
        print("FATAL: Superset cache not found after build!")
        sys.exit(1)

    validation = _validate_superset_cache(cache_path)
    print(f"\nSuperset Validation: {validation['status']}")
    if validation["issues"]:
        for issue in validation["issues"]:
            print(f"  P1: {issue}")
        sys.exit(1)

    print(f"\n  Cache: {cache_path}")
    print(f"  Fingerprint: {validation['fingerprint']}")
    print(f"  Rows: {validation['rows']}")
    print(f"  Columns: {validation['columns_total']}")
    print(f"  Factor columns: {validation['factor_columns_found']}/{validation['factor_columns_required']}")

    # Write validation report
    validation["build_time_seconds"] = elapsed
    validation["baseline_wilson"] = wilson
    validation["baseline_hc_accuracy"] = hc_acc
    validation["baseline_hc_count"] = hc_count
    report_path = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\superset_cache_validation_20260507.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(validation, f, indent=2, ensure_ascii=False)
    print(f"\n  Validation report: {report_path}")
    print("\nPhase A COMPLETE. Superset cache is ready for variant training.")

    # Also write ledger entry for the baseline
    _append_ledger({
        "run_id": result.get("run_id", "unknown"),
        "variant": "SUPERSET_baseline_all_factors",
        "phase": "superset_build",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": 42,
        "used_factor_ids": ["C004", "C009", "C011", "C133", "C134", "C136", "C137", "C138",
                            "C141", "C143", "C151", "C152", "C154", "C156", "C157", "C158",
                            "C159", "C161", "C162"],
        "excluded_feature_count": 0,
        "hc_accuracy": hc_acc,
        "wilson_lower_95": wilson,
        "hc_count": hc_count,
        "coverage": coverage,
        "elapsed_seconds": elapsed,
        "lockbox_role": "seen_research",
        "final_acceptance_eligible": False,
        "note": "superset_build_phase_baseline",
    })


def _load_manifest() -> list[dict]:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)
    return manifest["variants"]


def dry_run_variant(variant_name: str):
    """Show what a variant run would do without training."""
    import pandas as pd

    cache_path = _find_superset_cache()
    if cache_path is None:
        print("P1 STOP: No superset cache found. Run build-superset-only first.")
        sys.exit(1)

    validation = _validate_superset_cache(cache_path)
    if validation["status"] != "PASS":
        print(f"P1 STOP: Superset validation failed: {validation['issues']}")
        sys.exit(1)

    variants = _load_manifest()
    target = None
    for v in variants:
        if v["variant_name"] == variant_name:
            target = v
            break
    if target is None:
        print(f"ERROR: Variant '{variant_name}' not found in manifest.")
        print(f"Available: {[v['variant_name'] for v in variants[:10]]}...")
        sys.exit(1)

    exclude_names = set(target["excluded_feature_names"])
    meta_path = cache_path.with_suffix(".json")
    with open(meta_path) as f:
        meta = json.load(f)
    all_cols = meta["columns"]

    available_for_training = [c for c in all_cols if c not in exclude_names]
    excluded_from_training = [c for c in all_cols if c in exclude_names]

    # Check for missing exclusions (column in exclude list but not in cache)
    missing_exclusions = [c for c in target["excluded_feature_names"] if c not in all_cols]

    print(f"DRY-RUN: {variant_name}")
    print(f"  Factor IDs: {target['used_factor_ids']}")
    print(f"  Total cache columns: {len(all_cols)}")
    print(f"  Excluded columns: {len(excluded_from_training)}")
    print(f"  Available columns: {len(available_for_training)}")
    if missing_exclusions:
        print(f"  WARNING: {len(missing_exclusions)} exclusions not in cache (harmless)")
    print(f"  Status: READY")


def run_single_variant(variant_name: str):
    """Run a single variant from the manifest."""
    cache_path = _find_superset_cache()
    if cache_path is None:
        print("P1 STOP: No superset cache found. Run build-superset-only first.")
        sys.exit(1)

    validation = _validate_superset_cache(cache_path)
    if validation["status"] != "PASS":
        print(f"P1 STOP: Superset validation failed: {validation['issues']}")
        sys.exit(1)

    variants = _load_manifest()
    target = None
    for v in variants:
        if v["variant_name"] == variant_name:
            target = v
            break
    if target is None:
        print(f"ERROR: Variant '{variant_name}' not found in manifest.")
        sys.exit(1)

    _run_variant_from_manifest(target)


def run_all_variants():
    """Run all variants from the manifest sequentially."""
    cache_path = _find_superset_cache()
    if cache_path is None:
        print("P1 STOP: No superset cache found. Run build-superset-only first.")
        sys.exit(1)

    validation = _validate_superset_cache(cache_path)
    if validation["status"] != "PASS":
        print(f"P1 STOP: Superset validation failed: {validation['issues']}")
        sys.exit(1)

    variants = _load_manifest()
    print(f"Running ALL {len(variants)} variants from manifest")
    print(f"Cache: {cache_path}")
    print(f"Validation: {validation['status']}")
    print()

    for i, variant in enumerate(variants):
        print(f"\n[{i+1}/{len(variants)}]")
        _run_variant_from_manifest(variant)

    print("\n" + "=" * 60)
    print("ALL VARIANTS COMPLETE")
    print("=" * 60)


def _run_variant_from_manifest(variant: dict):
    """Execute a single variant using the superset cache."""
    name = variant["variant_name"]
    exclude = tuple(variant["excluded_feature_names"])
    fids = variant["used_factor_ids"]

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
        exclude_feature_names=exclude,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )

    print(f"{'='*60}")
    print(f"Running: {name}")
    print(f"  Factors: {fids}")
    print(f"  Excluded features: {len(exclude)}")
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
        "variant": name,
        "phase": "true_expanded_matrix",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": 42,
        "used_factor_ids": fids,
        "excluded_feature_count": len(exclude),
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


def _append_ledger(entry: dict) -> None:
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/run_superset_factor_matrix.py build-superset-only")
        print("  python scripts/run_superset_factor_matrix.py dry-run-variant <name>")
        print("  python scripts/run_superset_factor_matrix.py run-single-variant <name>")
        print("  python scripts/run_superset_factor_matrix.py run-all-variants")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "build-superset-only":
        build_superset_only()
    elif cmd == "dry-run-variant":
        if len(sys.argv) < 3:
            print("ERROR: specify variant name")
            sys.exit(1)
        dry_run_variant(sys.argv[2])
    elif cmd == "run-single-variant":
        if len(sys.argv) < 3:
            print("ERROR: specify variant name")
            sys.exit(1)
        run_single_variant(sys.argv[2])
    elif cmd == "run-all-variants":
        run_all_variants()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
