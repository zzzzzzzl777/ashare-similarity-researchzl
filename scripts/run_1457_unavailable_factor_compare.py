"""14:57 Unavailable Factor Comparison: Delete vs T-1 Shift.

Compares training outcomes when blocked feature families are either:
  - Deleted entirely (excluded from feature pool)
  - Replaced with T-1 shifted values (previous trading day per symbol)

Blocked families (unavailable at 14:57 on T-day):
  A. LHB / Institutional seats
  B. Margin financing
  C. Chip / cost distribution
  D. Closing auction
  E. Float relative impact

CLI:
  python scripts/run_1457_unavailable_factor_compare.py build-t1-cache
  python scripts/run_1457_unavailable_factor_compare.py run-q1-all
  python scripts/run_1457_unavailable_factor_compare.py run-q1-variant U01_delete_all_blocked
  python scripts/run_1457_unavailable_factor_compare.py run-april-winners
  python scripts/run_1457_unavailable_factor_compare.py run-greedy-policy
  python scripts/run_1457_unavailable_factor_compare.py summarize
  python scripts/run_1457_unavailable_factor_compare.py full-pipeline
"""
from __future__ import annotations

import json
import sys
import time
import numpy as np
import pandas as pd
from datetime import date, datetime, timezone
from pathlib import Path
from dataclasses import dataclass

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

REPORT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
CACHE_DIR = REPORT_DIR / "feature_cache"
LEDGER_PATH = REPORT_DIR / "experiment_ledger_20260508_unavailable_factor_compare.jsonl"
SUMMARY_JSON_PATH = REPORT_DIR / "1457_unavailable_factor_compare_20260508.json"
REPORT_MD_PATH = REPO_ROOT / "docs" / "1457_unavailable_factor_compare_results_20260508.md"

# ─── Hard moneyflow exclusions (always excluded) ───────────────────────────────
HARD_UNAVAILABLE_FEATURES = [
    "tushare_net_mf_amount", "tushare_net_mf_amount_available",
    "tushare_lg_buy_sell_ratio", "tushare_lg_buy_sell_ratio_available",
    "tushare_elg_buy_sell_ratio", "tushare_elg_buy_sell_ratio_available",
    "tushare_mf_strength", "tushare_mf_strength_available",
    "tushare_sm_sell_pressure", "tushare_sm_sell_pressure_available",
    "tushare_main_force_divergence", "tushare_main_force_divergence_available",
    "tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available",
]

# ─── Blocked feature families (unavailable at 14:57 on T-day) ──────────────────
FAMILY_A_LHB = [
    "tushare_lhb_net_buy", "tushare_lhb_net_rate", "tushare_inst_buy_count",
    "tushare_lhb_appeared", "tushare_inst_net_buy",
]
FAMILY_B_MARGIN = [
    "tushare_rzye_delta_pct",
    "tushare_rzye", "tushare_rzmre_ratio", "tushare_margin_net", "tushare_rqye_ratio",
]
FAMILY_C_CHIP = [
    "tushare_cost_concentration", "tushare_cost_position", "tushare_winner_rate",
]
FAMILY_D_CLOSE_AUCTION = [
    "tushare_auction_close_vwap_ratio", "tushare_auction_close_vol",
]
FAMILY_E_FLOAT_IMPACT = [
    "tushare_float_relative_impact",
]

ALL_BLOCKED_FAMILIES = {
    "A_lhb": FAMILY_A_LHB,
    "B_margin": FAMILY_B_MARGIN,
    "C_chip": FAMILY_C_CHIP,
    "D_close_auction": FAMILY_D_CLOSE_AUCTION,
    "E_float_impact": FAMILY_E_FLOAT_IMPACT,
}

ALL_BLOCKED_COLUMNS: list[str] = []
for fam in ALL_BLOCKED_FAMILIES.values():
    ALL_BLOCKED_COLUMNS.extend(fam)

ALL_BLOCKED_WITH_AVAIL: list[str] = []
for col in ALL_BLOCKED_COLUMNS:
    ALL_BLOCKED_WITH_AVAIL.append(col)
    ALL_BLOCKED_WITH_AVAIL.append(f"{col}_available")

THRESHOLDS = [0.70, 0.75, 0.78, 0.80]
TOPK_VALUES = [5, 6]

# ─── Cache management ──────────────────────────────────────────────────────────

Q1_CACHE_FINGERPRINT = "50f0a15cc17d25ca"
APRIL_CACHE_FINGERPRINT = "1d06fd67ca1e1175"
T1_CACHE_SUFFIX = "_t1shifted"


def _find_superset_cache(phase: str = "q1") -> Path:
    """Find the superset cache for a given phase."""
    fp = Q1_CACHE_FINGERPRINT if phase == "q1" else APRIL_CACHE_FINGERPRINT
    path = CACHE_DIR / f"gpu_probe_features_{fp}.parquet"
    if path.exists():
        return path
    # Fallback: search for any cache with blocked family columns
    import os
    candidates = []
    for f in CACHE_DIR.glob("gpu_probe_features_*.json"):
        if T1_CACHE_SUFFIX in f.stem:
            continue
        try:
            with open(f, encoding="utf-8") as fh:
                meta = json.load(fh)
            cols = set(meta.get("columns", []))
            if "tushare_lhb_net_buy" in cols and "tushare_cost_concentration" in cols:
                parquet = f.with_suffix(".parquet")
                if parquet.exists():
                    rows = meta.get("rows", 0)
                    # Q1 cache ~370k rows, April cache ~385k rows
                    if phase == "q1" and 360000 < rows < 380000:
                        candidates.append((parquet, os.path.getmtime(parquet)))
                    elif phase == "april" and rows > 380000:
                        candidates.append((parquet, os.path.getmtime(parquet)))
                    else:
                        candidates.append((parquet, os.path.getmtime(parquet)))
        except Exception:
            continue
    if not candidates:
        print(f"FATAL: No superset cache found for phase={phase}.")
        sys.exit(1)
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def _t1_cache_path(phase: str = "q1") -> Path:
    fp = Q1_CACHE_FINGERPRINT if phase == "q1" else APRIL_CACHE_FINGERPRINT
    return CACHE_DIR / f"gpu_probe_features_{fp}{T1_CACHE_SUFFIX}.parquet"


def _t1_cache_meta_path(phase: str = "q1") -> Path:
    fp = Q1_CACHE_FINGERPRINT if phase == "q1" else APRIL_CACHE_FINGERPRINT
    return CACHE_DIR / f"gpu_probe_features_{fp}{T1_CACHE_SUFFIX}.json"


def build_t1_cache():
    """Build T-1 shifted caches from superset caches (both Q1 and April).

    For each blocked column (value + _available), within each symbol group sorted by date,
    shift values by 1 trading row forward (row T gets row T-1's value).
    """
    for phase in ["q1", "april"]:
        superset_path = _find_superset_cache(phase)
        t1_path = _t1_cache_path(phase)

        if t1_path.exists():
            print(f"[{phase}] T-1 cache already exists: {t1_path.name}")
            continue

        print(f"\n[{phase}] Loading superset cache: {superset_path.name}")
        t0 = time.time()
        df = pd.read_parquet(superset_path)
        print(f"  Loaded {len(df)} rows, {len(df.columns)} cols in {time.time()-t0:.1f}s")

        existing_cols = set(df.columns)
        cols_to_shift = [c for c in ALL_BLOCKED_WITH_AVAIL if c in existing_cols]
        print(f"  Columns to T-1 shift: {len(cols_to_shift)}")

        if not cols_to_shift:
            print("  WARNING: No blocked columns found in cache. Nothing to shift.")
            continue

        print(f"  Applying per-symbol T-1 shift (previous trading row)...")
        t1 = time.time()
        df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

        for col in cols_to_shift:
            df[col] = df.groupby("symbol")[col].shift(1)

        for col in cols_to_shift:
            if col.endswith("_available"):
                df[col] = df[col].fillna(0).astype(np.int8)
            else:
                df[col] = df[col].fillna(0.0)

        elapsed_shift = time.time() - t1
        print(f"  Shift completed in {elapsed_shift:.1f}s")

        print(f"  Writing T-1 cache: {t1_path.name}")
        df.to_parquet(t1_path, index=False, engine="pyarrow")

        meta_path = _t1_cache_meta_path(phase)
        meta = {
            "fingerprint": f"{t1_path.stem.replace('gpu_probe_features_', '')}",
            "source_cache": str(superset_path),
            "columns": list(df.columns),
            "rows": len(df),
            "symbol_frames_kept": df["symbol"].nunique(),
            "shifted_columns": cols_to_shift,
            "shift_method": "per_symbol_trading_row_shift_1",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        print(f"  Done. T-1 cache [{phase}]: {len(df)} rows, {len(df.columns)} cols")
        del df

    print("\nAll T-1 caches built.")
    return _t1_cache_path("q1")


# ─── Variant definitions ───────────────────────────────────────────────────────

def _family_columns_with_avail(family_cols: list[str], existing_cols: set[str]) -> list[str]:
    """Get value + _available columns for a family that exist in cache."""
    result = []
    for col in family_cols:
        if col in existing_cols:
            result.append(col)
        avail = f"{col}_available"
        if avail in existing_cols:
            result.append(avail)
    return result


def _get_existing_blocked_cols() -> set[str]:
    """Read superset cache metadata to get actual column list."""
    meta_path = _find_superset_cache("q1").with_suffix(".json")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    return set(meta.get("columns", []))


def _build_variants() -> list[dict]:
    """Build all variant definitions."""
    existing = _get_existing_blocked_cols()

    all_blocked_with_avail_existing = []
    for col in ALL_BLOCKED_COLUMNS:
        if col in existing:
            all_blocked_with_avail_existing.append(col)
        avail = f"{col}_available"
        if avail in existing:
            all_blocked_with_avail_existing.append(avail)

    family_cols = {}
    for fam_name, fam_list in ALL_BLOCKED_FAMILIES.items():
        family_cols[fam_name] = _family_columns_with_avail(fam_list, existing)

    variants = []

    # U00: current reference (includes blocked cols, marked non-executable)
    variants.append({
        "name": "U00_current_reference",
        "mode": "reference",
        "exclude_blocked": [],
        "use_t1_cache": False,
        "note": "Replicates M1457_greedy_top8 style with all blocked cols present. NOT executable.",
        "executable": False,
    })

    # U01: delete ALL blocked
    variants.append({
        "name": "U01_delete_all_blocked",
        "mode": "delete",
        "exclude_blocked": all_blocked_with_avail_existing,
        "use_t1_cache": False,
        "note": "All A-E families excluded. Clean strict executable baseline.",
        "executable": True,
    })

    # U02: T-1 shift ALL blocked
    variants.append({
        "name": "U02_t1_all_blocked",
        "mode": "t1",
        "exclude_blocked": [],
        "use_t1_cache": True,
        "note": "All A-E families replaced with T-1 shifted values.",
        "executable": True,
    })

    # Per-family delete/t1 variants
    family_variant_map = {
        "A_lhb": ("U10_lhb_delete", "U11_lhb_t1"),
        "B_margin": ("U20_margin_delete", "U21_margin_t1"),
        "C_chip": ("U30_chip_delete", "U31_chip_t1"),
        "D_close_auction": ("U40_close_auction_delete", "U41_close_auction_t1"),
        "E_float_impact": ("U50_float_impact_delete", "U51_float_impact_t1"),
    }

    for fam_name, (del_name, t1_name) in family_variant_map.items():
        fam_excl = family_cols[fam_name]

        # Delete variant: exclude this family, keep others as-is (T-day values)
        # But we still need to exclude ALL other families to isolate the effect
        # Actually per the handoff doc: group-level compares change ONE family vs the U00 baseline
        # So "U10_lhb_delete" = exclude only LHB family from the full pool (other blocked families remain as T-day)
        # This isolates the contribution of each family
        variants.append({
            "name": del_name,
            "mode": "delete",
            "exclude_blocked": fam_excl,
            "use_t1_cache": False,
            "note": f"Only {fam_name} excluded. Other blocked families remain (T-day, non-executable reference).",
            "executable": False,
        })

        # T-1 variant: use T-1 cache but only the target family is shifted; others are also shifted
        # since the T-1 cache shifts ALL blocked families simultaneously.
        # For a clean per-family comparison, the T-1 variant uses the T-1 cache (all shifted)
        # but excludes all OTHER families. This isolates: does T-1 of THIS family help vs delete?
        other_family_cols = []
        for other_name, other_list in family_cols.items():
            if other_name != fam_name:
                other_family_cols.extend(other_list)

        variants.append({
            "name": t1_name,
            "mode": "t1",
            "exclude_blocked": other_family_cols,
            "use_t1_cache": True,
            "note": f"Only {fam_name} uses T-1 values. Other blocked families excluded.",
            "executable": True,
        })

    return variants


# ─── Training execution ────────────────────────────────────────────────────────

def _q1_config(*, exclude_names: tuple, use_t1_cache: bool) -> GpuProbeConfig:
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
        exclude_feature_names=exclude_names,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )


def _april_config(*, exclude_names: tuple, use_t1_cache: bool) -> GpuProbeConfig:
    return GpuProbeConfig(
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
        exclude_feature_names=exclude_names,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
    )


def _p0_check(result: dict) -> list[str]:
    """Verify no hard-unavailable or C004/C009 features leaked into training."""
    issues = []
    selected = result.get("selected_features", [])
    if not selected:
        fs = result.get("feature_selection", {})
        selected = fs.get("selected_features", [])
    input_feats = result.get("input_features", result.get("features", []))

    for feat in HARD_UNAVAILABLE_FEATURES:
        if feat in selected:
            issues.append(f"P0: hard_unavailable '{feat}' in selected_features")
        if feat in input_feats:
            issues.append(f"P0: hard_unavailable '{feat}' in input_features")

    c004_c009 = [
        "tushare_ff_adjusted_flow", "tushare_main_force_divergence",
        "tushare_ff_adjusted_flow_available", "tushare_main_force_divergence_available",
    ]
    for feat in c004_c009:
        if feat in selected:
            issues.append(f"P0: C004/C009 '{feat}' in selected_features")
    return issues


def _selector_analysis(pred_df: pd.DataFrame) -> dict:
    """Compute threshold-based and daily topK selector metrics."""
    if pred_df is None or pred_df.empty:
        return {}

    prob = pred_df["probability"].values
    actual = pred_df["actual"].values

    results = {}

    # Threshold selectors
    for t in THRESHOLDS:
        mask = prob >= t
        n = int(mask.sum())
        if n > 0:
            acc = float(actual[mask].mean())
            z = 1.96
            p_hat = acc
            denom = 1 + z**2 / n
            center = (p_hat + z**2 / (2 * n)) / denom
            margin = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denom
            wilson_lower = center - margin
            results[f"T>={t:.2f}"] = {
                "count": n, "accuracy": round(acc, 6),
                "wilson_lower_95": round(float(wilson_lower), 6),
            }
        else:
            results[f"T>={t:.2f}"] = {"count": 0, "accuracy": None, "wilson_lower_95": None}

    # Daily topK selectors
    date_col = "label_date" if "label_date" in pred_df.columns else "date"
    pred_df = pred_df.copy()
    pred_df["_date"] = pd.to_datetime(pred_df[date_col])

    for k in TOPK_VALUES:
        topk_mask = np.zeros(len(pred_df), dtype=bool)
        for _, grp in pred_df.groupby("_date"):
            if len(grp) >= k:
                top_idx = grp["probability"].nlargest(k).index
                topk_mask[pred_df.index.get_indexer(top_idx)] = True
            else:
                topk_mask[pred_df.index.get_indexer(grp.index)] = True

        n = int(topk_mask.sum())
        if n > 0:
            acc = float(actual[topk_mask].mean())
            z = 1.96
            denom = 1 + z**2 / n
            center = (acc + z**2 / (2*n)) / denom
            margin = z * np.sqrt((acc*(1-acc) + z**2/(4*n)) / n) / denom
            wilson_lower = center - margin
            trading_days = pred_df["_date"].nunique()
            results[f"daily_top{k}"] = {
                "count": n, "accuracy": round(acc, 6),
                "wilson_lower_95": round(float(wilson_lower), 6),
                "avg_candidates_per_day": round(n / max(trading_days, 1), 2),
            }
        else:
            results[f"daily_top{k}"] = {"count": 0, "accuracy": None, "wilson_lower_95": None}

    # Combined: T>=0.70 AND daily topK
    for k in TOPK_VALUES:
        t70_mask = prob >= 0.70
        combined_mask = np.zeros(len(pred_df), dtype=bool)
        for _, grp in pred_df.groupby("_date"):
            grp_t70 = grp[t70_mask[grp.index.values]]
            if len(grp_t70) >= k:
                top_idx = grp_t70["probability"].nlargest(k).index
                combined_mask[pred_df.index.get_indexer(top_idx)] = True
            elif len(grp_t70) > 0:
                combined_mask[pred_df.index.get_indexer(grp_t70.index)] = True

        n = int(combined_mask.sum())
        if n > 0:
            acc = float(actual[combined_mask].mean())
            z = 1.96
            denom = 1 + z**2 / n
            center = (acc + z**2 / (2*n)) / denom
            margin = z * np.sqrt((acc*(1-acc) + z**2/(4*n)) / n) / denom
            wilson_lower = center - margin
            trading_days = pred_df["_date"].nunique()
            results[f"T>=0.70_top{k}"] = {
                "count": n, "accuracy": round(acc, 6),
                "wilson_lower_95": round(float(wilson_lower), 6),
                "avg_candidates_per_day": round(n / max(trading_days, 1), 2),
            }
        else:
            results[f"T>=0.70_top{k}"] = {"count": 0, "accuracy": None, "wilson_lower_95": None}

    return results


def _run_single_variant(variant: dict, *, phase: str = "q1") -> dict:
    """Execute a single variant. phase='q1' or 'april'."""
    name = variant["name"]
    use_t1 = variant["use_t1_cache"]
    exclude_blocked = list(variant["exclude_blocked"])

    # Always exclude hard moneyflow
    all_exclude = sorted(set(HARD_UNAVAILABLE_FEATURES + exclude_blocked))
    exclude_tuple = tuple(all_exclude)

    if phase == "q1":
        config = _q1_config(exclude_names=exclude_tuple, use_t1_cache=use_t1)
    else:
        config = _april_config(exclude_names=exclude_tuple, use_t1_cache=use_t1)

    # If using T-1 cache, we need to swap the cache path
    cfg = get_default_config()
    store = LocalDataStore(cfg)

    phase_label = "Q1 (2026-01~03)" if phase == "q1" else "April (2026-04)"
    print(f"\n{'='*60}")
    print(f"[{phase.upper()}] {name}")
    print(f"  Mode: {'T-1 shifted' if use_t1 else 'delete/reference'}")
    print(f"  Excluded columns: {len(all_exclude)}")
    print(f"  Phase: {phase_label}")
    print(f"{'='*60}")

    t0 = time.time()

    if use_t1:
        # For T-1 variants: load T-1 cache manually, apply exclusions, run training
        t1_path = _t1_cache_path(phase)
        if not t1_path.exists():
            print("  ERROR: T-1 cache not found. Run 'build-t1-cache' first.")
            return {"variant": name, "status": "t1_cache_missing"}
        result = _run_with_custom_cache(store, config, t1_path, phase)
    else:
        result = run_gpu_next_day_probe(store, config)

    elapsed = time.time() - t0

    if result.get("status") == "insufficient_samples":
        print(f"  RESULT: insufficient_samples")
        return {"variant": name, "status": "insufficient_samples", "phase": phase}

    # P0 check
    p0_issues = _p0_check(result)
    if p0_issues:
        print(f"\n  *** P0 STOP ***")
        for issue in p0_issues:
            print(f"  {issue}")
        return {"variant": name, "status": "p0_violation", "issues": p0_issues, "phase": phase}

    # Extract metrics
    metrics = result.get("metrics", result)
    hc_acc = metrics.get("confident_accuracy", 0)
    hc_count = metrics.get("confident_count", 0)
    hc_coverage = metrics.get("confident_coverage", 0)
    brier = metrics.get("brier", 0)
    acceptance = metrics.get("acceptance", {})
    hc_info = acceptance.get("high_confidence", {})
    wilson = hc_info.get("wilson_lower_95", 0)
    if not wilson:
        wilson = acceptance.get("wilson_lower_95", 0)

    fs = result.get("feature_selection", {})
    selected_features = fs.get("selected_features", result.get("selected_features", []))
    selected_count = len(selected_features)

    print(f"  HC acc={hc_acc:.4f} Wilson={wilson:.4f} count={hc_count} "
          f"cov={hc_coverage:.4f} brier={brier:.4f} sel_feats={selected_count} ({elapsed:.0f}s)")

    # Selector analysis
    pred_path = result.get("test_predictions_path")
    pred_df = None
    if pred_path and Path(pred_path).exists():
        pred_df = pd.read_parquet(pred_path)
    else:
        pred_df = result.get("_test_predictions_df")

    selector_results = {}
    if pred_df is not None and not pred_df.empty:
        selector_results = _selector_analysis(pred_df)
        # Print key selectors
        for sel_name in ["T>=0.70", "T>=0.70_top5", "T>=0.70_top6"]:
            if sel_name in selector_results and selector_results[sel_name]["count"] > 0:
                s = selector_results[sel_name]
                print(f"  {sel_name}: n={s['count']} acc={s['accuracy']:.4f} wilson={s['wilson_lower_95']:.4f}")

    output = {
        "variant": name,
        "phase": phase,
        "mode": variant["mode"],
        "use_t1_cache": use_t1,
        "executable": variant.get("executable", True),
        "hc_accuracy": round(hc_acc, 6),
        "wilson_lower_95": round(wilson, 6),
        "hc_count": hc_count,
        "hc_coverage": round(hc_coverage, 6),
        "brier": round(brier, 6),
        "selected_features_count": selected_count,
        "selected_features": selected_features,
        "excluded_count": len(all_exclude),
        "selector_analysis": selector_results,
        "elapsed_seconds": round(elapsed, 1),
        "p0_issues": [],
        "note": variant.get("note", ""),
        "bundle_path": result.get("artifact_path", ""),
        "run_id": result.get("run_id", ""),
    }

    # Write ledger
    _append_ledger(output)
    return output


def _run_with_custom_cache(store, config: GpuProbeConfig, cache_path: Path, phase: str = "q1") -> dict:
    """Run gpu_probe using the T-1 shifted cache.

    Strategy: The superset cache and T-1 cache share the same fingerprint (same config),
    so we temporarily rename the original and place T-1 at the expected path.
    """
    superset_path = _find_superset_cache(phase)
    superset_meta = superset_path.with_suffix(".json")

    backup_parquet = superset_path.with_suffix(".parquet.orig_bak")
    backup_meta = superset_meta.with_suffix(".json.orig_bak")

    # The gpu_probe fingerprint for this config will resolve to the superset path
    # (same source_code_hash, same symbols, same date range).
    # Swap: move original aside, symlink/copy T-1 in its place.
    print(f"  Swapping superset cache with T-1 cache at: {superset_path.name}")
    swapped = False
    try:
        superset_path.rename(backup_parquet)
        if superset_meta.exists():
            superset_meta.rename(backup_meta)
        swapped = True

        import shutil
        shutil.copy2(cache_path, superset_path)
        t1_meta = _t1_cache_meta_path(phase)
        if t1_meta.exists():
            shutil.copy2(t1_meta, superset_meta)
        else:
            # Write minimal metadata so gpu_probe accepts the cache hit
            orig_meta = {}
            if backup_meta.exists():
                with open(backup_meta, encoding="utf-8") as f:
                    orig_meta = json.load(f)
            meta = {
                "fingerprint": orig_meta.get("fingerprint", SUPERSET_CACHE_FINGERPRINT),
                "columns": orig_meta.get("columns", []),
                "rows": orig_meta.get("rows", 370000),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "symbol_frames_kept": orig_meta.get("symbol_frames_kept", 2937),
            }
            with open(superset_meta, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

        result = run_gpu_next_day_probe(store, config)
        return result

    finally:
        # Restore original superset cache
        if swapped:
            if superset_path.exists():
                superset_path.unlink()
            if superset_meta.exists():
                superset_meta.unlink(missing_ok=True)
            if backup_parquet.exists():
                backup_parquet.rename(superset_path)
            if backup_meta.exists():
                backup_meta.rename(superset_meta)
            print(f"  Restored original superset cache.")


# ─── Ledger ────────────────────────────────────────────────────────────────────

def _append_ledger(entry: dict) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: v for k, v in entry.items()
                   if not isinstance(v, (pd.DataFrame, np.ndarray))}
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(serializable, ensure_ascii=False, default=str) + "\n")


# ─── Greedy policy ─────────────────────────────────────────────────────────────

def run_greedy_policy(q1_results: list[dict]) -> list[dict]:
    """Start from U01 (delete all), add back families via T-1 if they improve Wilson."""
    baseline = None
    for r in q1_results:
        if r.get("variant") == "U01_delete_all_blocked":
            baseline = r
            break
    if baseline is None:
        print("ERROR: U01_delete_all_blocked not found in Q1 results. Run Q1 first.")
        return []

    baseline_wilson = baseline["wilson_lower_95"]
    print(f"\nGreedy policy starting from U01: Wilson={baseline_wilson:.4f}")

    # Check each family's T-1 contribution
    family_t1_map = {
        "A_lhb": "U11_lhb_t1",
        "B_margin": "U21_margin_t1",
        "C_chip": "U31_chip_t1",
        "D_close_auction": "U41_close_auction_t1",
        "E_float_impact": "U51_float_impact_t1",
    }

    improvements = []
    for fam_name, variant_name in family_t1_map.items():
        t1_result = None
        for r in q1_results:
            if r.get("variant") == variant_name:
                t1_result = r
                break
        if t1_result is None:
            continue

        delta = t1_result["wilson_lower_95"] - baseline_wilson
        improvements.append({
            "family": fam_name,
            "variant": variant_name,
            "wilson": t1_result["wilson_lower_95"],
            "delta": delta,
        })
        print(f"  {fam_name}: Wilson={t1_result['wilson_lower_95']:.4f} delta={delta:+.4f}")

    # Sort by improvement
    improvements.sort(key=lambda x: x["delta"], reverse=True)

    # Select families that improve Wilson
    selected_families = [imp for imp in improvements if imp["delta"] > 0]
    print(f"\n  Families with positive Wilson improvement: {len(selected_families)}")
    for s in selected_families:
        print(f"    {s['family']}: +{s['delta']:.4f}")

    # Build greedy policy variant
    existing = _get_existing_blocked_cols()
    family_cols_map = {}
    for fam_name, fam_list in ALL_BLOCKED_FAMILIES.items():
        family_cols_map[fam_name] = _family_columns_with_avail(fam_list, existing)

    # U90: best policy — include T-1 for improving families, delete the rest
    excluded_families = [imp["family"] for imp in improvements if imp["delta"] <= 0]
    exclude_cols = []
    for fam_name in excluded_families:
        exclude_cols.extend(family_cols_map[fam_name])

    greedy_variants = []

    u90 = {
        "name": "U90_best_policy_q1",
        "mode": "t1",
        "exclude_blocked": exclude_cols,
        "use_t1_cache": True,
        "executable": True,
        "note": f"Greedy best: T-1 for {[s['family'] for s in selected_families]}, delete {excluded_families}",
    }
    greedy_variants.append(u90)

    # U91: sensitivity — include ALL families as T-1 regardless of Q1 improvement
    u91 = {
        "name": "U91_best_policy_plus_sensitivity",
        "mode": "t1",
        "exclude_blocked": [],
        "use_t1_cache": True,
        "executable": True,
        "note": "All families T-1 shifted (sensitivity check vs U90 greedy)",
    }
    greedy_variants.append(u91)

    results = []
    for v in greedy_variants:
        result = _run_single_variant(v, phase="q1")
        results.append(result)

    return results


# ─── Report generation ─────────────────────────────────────────────────────────

def _generate_report(q1_results: list[dict], april_results: list[dict],
                     greedy_results: list[dict]) -> str:
    """Generate the final markdown report."""
    lines = []
    lines.append("# 14:57 Unavailable Factor Comparison Results")
    lines.append(f"\nDate: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    # Find best executable
    executable_q1 = [r for r in q1_results + greedy_results
                     if r.get("executable", True) and r.get("wilson_lower_95", 0) > 0]
    if executable_q1:
        best = max(executable_q1, key=lambda x: x.get("wilson_lower_95", 0))
    else:
        best = {"variant": "NONE", "wilson_lower_95": 0, "hc_accuracy": 0}

    lines.append("## 1. Best Executable Policy")
    lines.append("")
    lines.append(f"**Winner: `{best.get('variant', 'N/A')}`**")
    lines.append(f"- Mode: {best.get('mode', 'N/A')}")
    lines.append(f"- Note: {best.get('note', '')}")
    lines.append("")

    # Q1 metrics table
    lines.append("## 2. Q1 Metrics (2026-01 to 2026-03)")
    lines.append("")
    lines.append("| Variant | HC Acc | Wilson 95 | HC Count | Coverage | Brier | Sel Feats | Executable |")
    lines.append("|---------|--------|-----------|----------|----------|-------|-----------|------------|")
    for r in sorted(q1_results + greedy_results, key=lambda x: x.get("wilson_lower_95", 0), reverse=True):
        if r.get("status") in ("insufficient_samples", "p0_violation", "t1_cache_missing"):
            lines.append(f"| {r['variant']} | — | — | — | — | — | — | {r.get('status')} |")
            continue
        exe = "YES" if r.get("executable", True) else "no"
        lines.append(
            f"| {r['variant']} | {r.get('hc_accuracy',0)*100:.2f}% | "
            f"{r.get('wilson_lower_95',0)*100:.2f}% | {r.get('hc_count',0)} | "
            f"{r.get('hc_coverage',0)*100:.2f}% | {r.get('brier',0):.4f} | "
            f"{r.get('selected_features_count',0)} | {exe} |"
        )
    lines.append("")

    # April metrics
    if april_results:
        lines.append("## 3. April Forward Validation (2026-04)")
        lines.append("")
        lines.append("| Variant | HC Acc | Wilson 95 | HC Count | Coverage | Brier |")
        lines.append("|---------|--------|-----------|----------|----------|-------|")
        for r in sorted(april_results, key=lambda x: x.get("wilson_lower_95", 0), reverse=True):
            if r.get("status") in ("insufficient_samples", "p0_violation", "t1_cache_missing"):
                lines.append(f"| {r['variant']} | — | — | — | — | {r.get('status')} |")
                continue
            lines.append(
                f"| {r['variant']} | {r.get('hc_accuracy',0)*100:.2f}% | "
                f"{r.get('wilson_lower_95',0)*100:.2f}% | {r.get('hc_count',0)} | "
                f"{r.get('hc_coverage',0)*100:.2f}% | {r.get('brier',0):.4f} |"
            )
        lines.append("")

    # Selector analysis for best
    lines.append("## 4. Trade-Facing Selector Analysis (Best Executable, Q1)")
    lines.append("")
    best_selectors = best.get("selector_analysis", {})
    if best_selectors:
        lines.append(f"Variant: `{best['variant']}`")
        lines.append("")
        lines.append("| Selector | Candidates | Accuracy | Wilson 95 | Avg/Day |")
        lines.append("|----------|-----------|----------|-----------|---------|")
        for sel_name, sel_data in best_selectors.items():
            if sel_data.get("count", 0) > 0:
                avg_day = sel_data.get("avg_candidates_per_day", "—")
                lines.append(
                    f"| {sel_name} | {sel_data['count']} | "
                    f"{sel_data['accuracy']*100:.2f}% | {sel_data['wilson_lower_95']*100:.2f}% | {avg_day} |"
                )
        lines.append("")

    # P0 audit
    lines.append("## 5. P0 Audit")
    lines.append("")
    p0_violations = [r for r in q1_results + april_results + greedy_results
                     if r.get("p0_issues")]
    if p0_violations:
        lines.append("**P0 VIOLATIONS FOUND:**")
        for r in p0_violations:
            lines.append(f"- `{r['variant']}`: {r['p0_issues']}")
    else:
        lines.append("All variants passed P0 audit. No hard moneyflow or C004/C009 leakage detected.")
    lines.append("")

    # Family decision summary
    lines.append("## 6. Family Decision Summary")
    lines.append("")
    lines.append("| Family | Decision | Rationale |")
    lines.append("|--------|----------|-----------|")

    family_decisions = _compute_family_decisions(q1_results)
    for fam, decision in family_decisions.items():
        lines.append(f"| {fam} | {decision['action']} | {decision['rationale']} |")
    lines.append("")

    # Bundle path
    if best.get("bundle_path"):
        lines.append("## 7. Winner Bundle")
        lines.append("")
        lines.append(f"- Path: `{best['bundle_path']}`")
        lines.append(f"- Selected features ({best.get('selected_features_count', 0)}):")
        for f in best.get("selected_features", [])[:20]:
            lines.append(f"  - `{f}`")
        if best.get("selected_features_count", 0) > 20:
            lines.append(f"  - ... ({best['selected_features_count'] - 20} more)")
        lines.append("")

    return "\n".join(lines)


def _compute_family_decisions(q1_results: list[dict]) -> dict:
    """Determine delete vs T-1 decision for each family based on Q1 results."""
    decisions = {}
    ref_result = None
    del_all_result = None

    for r in q1_results:
        if r.get("variant") == "U00_current_reference":
            ref_result = r
        elif r.get("variant") == "U01_delete_all_blocked":
            del_all_result = r

    baseline_wilson = del_all_result["wilson_lower_95"] if del_all_result else 0

    family_pairs = {
        "A_lhb": ("U10_lhb_delete", "U11_lhb_t1"),
        "B_margin": ("U20_margin_delete", "U21_margin_t1"),
        "C_chip": ("U30_chip_delete", "U31_chip_t1"),
        "D_close_auction": ("U40_close_auction_delete", "U41_close_auction_t1"),
        "E_float_impact": ("U50_float_impact_delete", "U51_float_impact_t1"),
    }

    for fam_name, (del_variant, t1_variant) in family_pairs.items():
        del_result = next((r for r in q1_results if r.get("variant") == del_variant), None)
        t1_result = next((r for r in q1_results if r.get("variant") == t1_variant), None)

        if t1_result and t1_result.get("wilson_lower_95", 0) > baseline_wilson:
            decisions[fam_name] = {
                "action": "T-1 shift",
                "rationale": f"T-1 Wilson {t1_result['wilson_lower_95']*100:.2f}% > baseline {baseline_wilson*100:.2f}%",
            }
        else:
            t1_w = t1_result.get("wilson_lower_95", 0) * 100 if t1_result else 0
            decisions[fam_name] = {
                "action": "Delete",
                "rationale": f"T-1 Wilson {t1_w:.2f}% <= baseline {baseline_wilson*100:.2f}%",
            }

    return decisions


# ─── CLI commands ──────────────────────────────────────────────────────────────

def run_q1_all() -> list[dict]:
    """Run all Q1 variants."""
    variants = _build_variants()
    results = []
    print(f"\nRunning {len(variants)} Q1 variants...")
    for i, v in enumerate(variants):
        print(f"\n[{i+1}/{len(variants)}]")
        result = _run_single_variant(v, phase="q1")
        results.append(result)
    return results


def run_q1_variant(name: str) -> dict:
    """Run a single Q1 variant by name."""
    variants = _build_variants()
    target = next((v for v in variants if v["name"] == name), None)
    if target is None:
        available = [v["name"] for v in variants]
        print(f"ERROR: '{name}' not found. Available: {available}")
        sys.exit(1)
    return _run_single_variant(target, phase="q1")


def run_april_winners(q1_results: list[dict] | None = None) -> list[dict]:
    """Run April validation on top Q1 performers."""
    if q1_results is None:
        q1_results = _load_q1_from_ledger()

    # Select variants for April: top Wilson executable variants + U00 reference
    executable = [r for r in q1_results if r.get("executable", True)
                  and r.get("wilson_lower_95", 0) > 0]
    executable.sort(key=lambda x: x.get("wilson_lower_95", 0), reverse=True)

    # Take top 5 + U00 + U01 + U02
    april_candidates = []
    must_include = ["U00_current_reference", "U01_delete_all_blocked", "U02_t1_all_blocked"]
    for name in must_include:
        variant = next((r for r in q1_results if r.get("variant") == name), None)
        if variant:
            april_candidates.append(variant)

    for r in executable[:5]:
        if r["variant"] not in must_include:
            april_candidates.append(r)

    print(f"\nRunning April validation for {len(april_candidates)} variants...")

    # Rebuild variant defs for April runs
    all_variants = _build_variants()
    variant_map = {v["name"]: v for v in all_variants}

    # Reconstruct greedy variants from Q1 ledger data
    # U90: greedy policy — uses T-1 cache, excludes families that didn't improve
    # U91: all T-1 — uses T-1 cache, excludes nothing extra
    existing = _get_existing_blocked_cols()
    family_cols_map = {}
    for fam_name, fam_list in ALL_BLOCKED_FAMILIES.items():
        family_cols_map[fam_name] = _family_columns_with_avail(fam_list, existing)

    greedy_names = ["U90_best_policy_q1", "U91_best_policy_plus_sensitivity"]
    for gn in greedy_names:
        r = next((x for x in q1_results if x.get("variant") == gn), None)
        if r and gn not in variant_map:
            if gn == "U91_best_policy_plus_sensitivity":
                # U91: all families T-1, no extra exclusions
                exclude_blocked = []
            else:
                # U90: reconstruct from the note field or from greedy logic
                # Parse which families were deleted from the note
                note = r.get("note", "")
                exclude_blocked = _reconstruct_u90_exclusions(note, family_cols_map)

            variant_map[gn] = {
                "name": gn,
                "mode": r.get("mode", "t1"),
                "exclude_blocked": exclude_blocked,
                "use_t1_cache": r.get("use_t1_cache", True),
                "executable": True,
                "note": r.get("note", ""),
            }
            excl_total = len(set(HARD_UNAVAILABLE_FEATURES + exclude_blocked))
            print(f"  Reconstructed {gn}: exclude_blocked={len(exclude_blocked)}, total_excl={excl_total}")

    april_results = []
    for r in april_candidates:
        vname = r["variant"]
        v = variant_map.get(vname)
        if v is None:
            print(f"  WARNING: No variant def for {vname}, skipping April run")
            continue
        result = _run_single_variant(v, phase="april")
        april_results.append(result)

    return april_results


def _reconstruct_u90_exclusions(note: str, family_cols_map: dict) -> list[str]:
    """Reconstruct U90 exclude_blocked from its note field.

    Note format: "Greedy best: T-1 for ['C_chip'], delete ['B_margin', 'A_lhb', ...]"
    """
    exclude_blocked = []
    # Parse "delete [...]" from note
    import re
    delete_match = re.search(r"delete \[([^\]]*)\]", note)
    if delete_match:
        families_str = delete_match.group(1)
        # Parse family names like 'B_margin', 'A_lhb', etc.
        deleted_families = re.findall(r"'([^']+)'", families_str)
        for fam_name in deleted_families:
            if fam_name in family_cols_map:
                exclude_blocked.extend(family_cols_map[fam_name])
    else:
        # Fallback: re-run greedy logic from Q1 results
        print("  WARNING: Could not parse U90 note, re-deriving from Q1 results")
        q1_results = _load_q1_from_ledger()
        baseline_wilson = 0
        for r in q1_results:
            if r.get("variant") == "U01_delete_all_blocked":
                baseline_wilson = r.get("wilson_lower_95", 0)
                break

        family_t1_map = {
            "A_lhb": "U11_lhb_t1",
            "B_margin": "U21_margin_t1",
            "C_chip": "U31_chip_t1",
            "D_close_auction": "U41_close_auction_t1",
            "E_float_impact": "U51_float_impact_t1",
        }
        for fam_name, variant_name in family_t1_map.items():
            t1_result = next((r for r in q1_results if r.get("variant") == variant_name), None)
            if t1_result is None or t1_result.get("wilson_lower_95", 0) <= baseline_wilson:
                exclude_blocked.extend(family_cols_map.get(fam_name, []))

    return exclude_blocked


def _load_q1_from_ledger() -> list[dict]:
    """Load Q1 results from ledger file."""
    if not LEDGER_PATH.exists():
        return []
    results = []
    with open(LEDGER_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entry = json.loads(line)
                if entry.get("phase") == "q1":
                    results.append(entry)
    return results


def full_pipeline():
    """Run the complete pipeline: build T-1 cache, Q1 all, greedy, April winners, report."""
    print("=" * 70)
    print("FULL PIPELINE: 14:57 Unavailable Factor Comparison")
    print("=" * 70)

    # Step 1: Build T-1 cache
    print("\n\n" + "=" * 70)
    print("STEP 1: Build T-1 shifted cache")
    print("=" * 70)
    build_t1_cache()

    # Step 2: Run all Q1 variants
    print("\n\n" + "=" * 70)
    print("STEP 2: Run all Q1 variants")
    print("=" * 70)
    q1_results = run_q1_all()

    # Step 3: Greedy policy
    print("\n\n" + "=" * 70)
    print("STEP 3: Greedy policy optimization")
    print("=" * 70)
    greedy_results = run_greedy_policy(q1_results)

    # Step 4: April validation
    print("\n\n" + "=" * 70)
    print("STEP 4: April forward validation")
    print("=" * 70)
    all_q1 = q1_results + greedy_results
    april_results = run_april_winners(all_q1)

    # Step 5: Generate report
    print("\n\n" + "=" * 70)
    print("STEP 5: Generate reports")
    print("=" * 70)
    _write_outputs(q1_results, april_results, greedy_results)

    print("\n\nFULL PIPELINE COMPLETE.")
    print(f"  Ledger: {LEDGER_PATH}")
    print(f"  Summary: {SUMMARY_JSON_PATH}")
    print(f"  Report: {REPORT_MD_PATH}")


def _write_outputs(q1_results: list[dict], april_results: list[dict],
                   greedy_results: list[dict]):
    """Write summary JSON and markdown report."""
    # Summary JSON
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "q1_results": q1_results,
        "greedy_results": greedy_results,
        "april_results": april_results,
        "family_decisions": _compute_family_decisions(q1_results),
    }
    serializable = json.loads(json.dumps(summary, default=str))
    with open(SUMMARY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
    print(f"  Summary JSON: {SUMMARY_JSON_PATH}")

    # Markdown report
    report = _generate_report(q1_results, april_results, greedy_results)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  Report: {REPORT_MD_PATH}")


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

    q1 = [e for e in entries if e.get("phase") == "q1"]
    april = [e for e in entries if e.get("phase") == "april"]

    print(f"Total entries: {len(entries)} (Q1: {len(q1)}, April: {len(april)})")
    print(f"\n{'Variant':<40} {'Phase':<6} {'HC Acc':>7} {'Wilson':>7} {'Count':>6} {'Exe':>4}")
    print("-" * 75)
    for e in sorted(entries, key=lambda x: (x.get("phase", ""), -x.get("wilson_lower_95", 0))):
        exe = "Y" if e.get("executable", True) else "N"
        print(f"{e.get('variant','?'):<40} {e.get('phase','?'):<6} "
              f"{e.get('hc_accuracy',0)*100:>6.2f}% {e.get('wilson_lower_95',0)*100:>6.2f}% "
              f"{e.get('hc_count',0):>6} {exe:>4}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "build-t1-cache":
        build_t1_cache()
    elif cmd == "run-q1-all":
        run_q1_all()
    elif cmd == "run-q1-variant":
        if len(sys.argv) < 3:
            print("ERROR: specify variant name")
            sys.exit(1)
        run_q1_variant(sys.argv[2])
    elif cmd == "run-april-winners":
        run_april_winners()
    elif cmd == "run-greedy-policy":
        q1 = _load_q1_from_ledger()
        if not q1:
            print("ERROR: No Q1 results in ledger. Run Q1 first.")
            sys.exit(1)
        run_greedy_policy(q1)
    elif cmd == "summarize":
        summarize()
    elif cmd == "full-pipeline":
        full_pipeline()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
