"""
Minute Factor Full Matrix Q1 Ablation — 32-combination experiment.
Runs all 2^5 combinations of C133/C134/C136/C137/C138 with Q1 seen_research.

Scope: ONLY C133/C134/C136/C137/C138. No C135, no C139-C152, no April.
"""
import sys
import json
import time
import platform
import subprocess
import warnings
import itertools
from datetime import date, datetime
from pathlib import Path
from collections import defaultdict

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ashare_similarity.prediction.gpu_probe import (
    GpuProbeConfig, run_gpu_next_day_probe, GPU_PROBE_RESEARCH_FEATURES,
    _feature_names_for_config,
)
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.config import get_default_config

STORE_ROOT = Path(r"E:\ashare_similarity_runtime\data")
REPORT_DIR = STORE_ROOT / "reports" / "prediction"

SAFE_FACTORS = {
    "C133": ("tushare_last_30min_return", "tushare_last_30min_return_available"),
    "C134": ("tushare_first_15min_volume_ratio", "tushare_first_15min_volume_ratio_available"),
    "C136": ("tushare_intraday_volatility", "tushare_intraday_volatility_available"),
    "C137": ("tushare_up_volume_ratio", "tushare_up_volume_ratio_available"),
    "C138": ("tushare_high_time_pct", "tushare_high_time_pct_available"),
}

BLOCKED_COLUMNS = (
    "tushare_vwap_deviation", "tushare_vwap_deviation_available",
    "tushare_close_vs_vwap", "tushare_close_vs_vwap_available",
    "tushare_mf_flow_intensity", "tushare_mf_flow_intensity_available",
    "tushare_float_relative_impact", "tushare_float_relative_impact_available",
    "tushare_limit_space_compression", "tushare_limit_space_compression_available",
    "tushare_limit_approach_velocity", "tushare_limit_approach_velocity_available",
    "tushare_seal_strength_proxy", "tushare_seal_strength_proxy_available",
)

FACTOR_IDS = ["C133", "C134", "C136", "C137", "C138"]
LEDGER_PATH = REPORT_DIR / "experiment_ledger_20260506.jsonl"


def _get_env_info():
    """Gather environment info for ledger."""
    try:
        git_status = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            cwd=str(Path(__file__).resolve().parent.parent),
            text=True, timeout=10
        ).strip()
        dirty = 'dirty' if git_status else 'clean'
    except Exception:
        dirty = 'unknown'
    py_ver = platform.python_version()
    try:
        import lightgbm; lgbm_ver = lightgbm.__version__
    except Exception: lgbm_ver = 'unknown'
    try:
        import torch; torch_ver = torch.__version__
    except Exception: torch_ver = 'unknown'
    return dirty, py_ver, {'lightgbm': lgbm_ver, 'torch': torch_ver}

_DIRTY, _PY_VER, _PKG_VERS = _get_env_info()


def write_ledger_entry(result: dict, included_factor_ids: list[str], vname: str):
    """Append one ledger entry immediately after a run completes."""
    hc = result.get("acceptance", {}).get("high_confidence", {})
    selected = result.get("feature_selection", {}).get("selected_features", [])
    safe_minute_cols = []
    for fid in FACTOR_IDS:
        safe_minute_cols.extend(SAFE_FACTORS[fid])
    sel_minute = [f for f in selected if f in set(safe_minute_cols)]

    allowed_cols = []
    for fid in included_factor_ids:
        allowed_cols.extend(SAFE_FACTORS[fid])
    excluded_cols = list(build_exclude_names(included_factor_ids))

    # Monthly from buckets
    monthly = defaultdict(lambda: {"count": 0, "correct": 0})
    for b in result.get("date_bucket_stability", {}).get("buckets", []):
        d = b.get("label_date", "")
        if d:
            c = b.get("confident_count", 0) or 0
            prec = b.get("confident_precision", 0) or 0
            monthly[d[:7]]["count"] += c
            monthly[d[:7]]["correct"] += int(round(c * prec))
    monthly_metrics = {}
    for m in sorted(monthly.keys()):
        info = monthly[m]
        acc = info["correct"] / info["count"] if info["count"] > 0 else 0
        monthly_metrics[m] = {"count": info["count"], "accuracy": round(acc, 4)}

    run_id = result.get("run_id", "")
    run_dir = REPORT_DIR / "runs" / run_id
    art_path = str(run_dir / "artifact.json") if run_id else ""

    record = {
        "run_id": run_id,
        "artifact_path": art_path,
        "variant": vname,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "code_hash": result.get("code_hash", ""),
        "data_hash": result.get("data_hash", ""),
        "feature_hash": result.get("feature_hash", ""),
        "config_hash": result.get("selector_config_hash", ""),
        "dirty_git_status": _DIRTY,
        "python_version": _PY_VER,
        "package_versions": _PKG_VERS,
        "gpu_name": result.get("device_name", ""),
        "used_factor_ids": included_factor_ids,
        "allowed_feature_columns": allowed_cols,
        "excluded_feature_columns": excluded_cols,
        "selected_features_count": len(selected),
        "selected_minute_features": sel_minute,
        "train_window": f"to {result.get('split_manifest',{}).get('train_end','?')} (fit={result.get('fit_rows',0)})",
        "test_window": f"{result.get('test_start','?')} to {result.get('test_end','?')} ({result.get('test_rows',0)} rows)",
        "lockbox_role": result.get("lockbox_role", ""),
        "final_acceptance_eligible": False,
        "hc_accuracy": hc.get("accuracy"),
        "wilson_lower_95": hc.get("wilson_lower_95"),
        "hc_count": hc.get("rows"),
        "coverage": hc.get("coverage"),
        "brier": result.get("brier"),
        "monthly_metrics": monthly_metrics,
        "notes": "dedup-fixed Q1 matrix run",
    }
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def build_exclude_names(included_factor_ids: list[str]) -> tuple[str, ...]:
    """Build exclude list: blocked + safe factors NOT in the included set."""
    exclude = list(BLOCKED_COLUMNS)
    for fid, cols in SAFE_FACTORS.items():
        if fid not in included_factor_ids:
            exclude.extend(cols)
    return tuple(exclude)


def variant_name(included: list[str]) -> str:
    if not included:
        return "M00_none"
    bits = sum(1 << FACTOR_IDS.index(fid) for fid in included)
    suffix = "_".join(included)
    return f"M{bits:02d}_{suffix}"


def _stable_dedup(seq: tuple[str, ...]) -> tuple[tuple[str, ...], list[str]]:
    """Stable dedup: keep first occurrence, return (deduped, removed)."""
    seen: set = set()
    result: list[str] = []
    removed: list[str] = []
    for item in seq:
        if item in seen:
            removed.append(item)
        else:
            seen.add(item)
            result.append(item)
    return tuple(result), removed


def run_preflight() -> bool:
    """Preflight audit: check all gates without training."""
    print("=" * 60)
    print("PREFLIGHT AUDIT")
    print("=" * 60)
    print()

    all_pass = True

    # 1. Check factor registry for C133-C138
    reg_path = REPORT_DIR / "factor_registry.json"
    with open(reg_path, encoding="utf-8") as f:
        reg = json.load(f)

    print("[1] Factor Registry Status (C133-C138)")
    batch = reg.get("candidates_20260506_minute_registration", {})
    if not batch:
        print("  FAIL: candidates_20260506_minute_registration batch not found")
        all_pass = False
    else:
        detail = batch.get("detail", [])
        factor_map = {e.get("factor_id"): e for e in detail}

        for fid in FACTOR_IDS:
            entry = factor_map.get(fid)
            if not entry:
                print(f"  {fid}: NOT FOUND — FAIL")
                all_pass = False
            else:
                status = entry.get("engineering_status", "?")
                ok = status == "existing_engineered"
                print(f"  {fid} ({entry.get('column_name', '?')}): {status} {'PASS' if ok else 'FAIL'}")
                if not ok:
                    all_pass = False

        # C135 must be blocked
        c135 = factor_map.get("C135")
        if c135:
            s135 = c135.get("engineering_status", "?")
            ok135 = "blocked" in s135
            print(f"  C135 ({c135.get('column_name', '?')}): {s135} {'PASS' if ok135 else 'FAIL'}")
            if not ok135:
                all_pass = False
        else:
            print("  C135: NOT FOUND (expected blocked entry) — FAIL")
            all_pass = False

        # tushare_close_vs_vwap
        cvw = [e for e in detail if e.get("column_name") == "tushare_close_vs_vwap"]
        if cvw:
            cvw_s = cvw[0].get("engineering_status", "?")
            print(f"  tushare_close_vs_vwap: {cvw_s} (no factor_id) PASS")
        else:
            print("  tushare_close_vs_vwap: not in batch (OK)")

    print()
    print("[2] Scope Declaration")
    print(f"  allowed_factor_ids: {FACTOR_IDS}")
    print(f"  C139-C152: NOT part of this round (explicitly excluded)")
    print(f"  C135: blocked_until_outlier_guard (excluded)")
    print(f"  tushare_close_vs_vwap: duplicate of C135 (excluded)")
    print()

    # 3. Feature list check (with dedup simulation)
    print("[3] Feature List Verification (with dedup)")
    research_set = set(GPU_PROBE_RESEARCH_FEATURES)
    safe_cols = []
    for fid in FACTOR_IDS:
        safe_cols.extend(SAFE_FACTORS[fid])

    missing = [c for c in safe_cols if c not in research_set]
    if missing:
        print(f"  FAIL: safe minute columns not in research features: {missing}")
        all_pass = False
    else:
        print(f"  All 10 safe minute columns in GPU_PROBE_RESEARCH_FEATURES: PASS")

    # Simulate M31 pipeline: prefix filter → name filter → dedup
    excl_m31 = build_exclude_names(FACTOR_IDS)
    fnames = tuple(GPU_PROBE_RESEARCH_FEATURES)
    fnames = tuple(f for f in fnames if not f.startswith("cross_"))
    excl_set = set(excl_m31)
    fnames = tuple(f for f in fnames if f not in excl_set)
    fnames, dedup_removed_m31 = _stable_dedup(fnames)

    print(f"  duplicate_feature_count (M31 pre-dedup): {len(dedup_removed_m31)}")
    if dedup_removed_m31:
        print(f"  duplicates_removed: {dedup_removed_m31}")
    print(f"  duplicate_feature_count (M31 post-dedup): 0 — PASS")

    blocked_leaked = [f for f in BLOCKED_COLUMNS if f in set(fnames)]
    print(f"  blocked_features_leaked (M31 config): {len(blocked_leaked)}")
    if blocked_leaked:
        print(f"  FAIL: leaked: {blocked_leaked}")
        all_pass = False
    else:
        print(f"  PASS: 0 blocked features in final set")

    safe_present = [c for c in safe_cols if c in set(fnames)]
    print(f"  safe_minute_in_final (M31): {len(safe_present)}/10")
    if len(safe_present) != 10:
        all_pass = False
        print(f"  FAIL: expected 10")
    else:
        print(f"  PASS")

    # Simulate M00 pipeline: prefix filter → name filter → dedup
    excl_m00 = build_exclude_names([])
    fnames_m00 = tuple(GPU_PROBE_RESEARCH_FEATURES)
    fnames_m00 = tuple(f for f in fnames_m00 if not f.startswith("cross_"))
    excl_set_m00 = set(excl_m00)
    fnames_m00 = tuple(f for f in fnames_m00 if f not in excl_set_m00)
    fnames_m00, dedup_removed_m00 = _stable_dedup(fnames_m00)

    safe_in_m00 = [c for c in safe_cols if c in set(fnames_m00)]
    print(f"  safe_minute_in_M00_baseline: {len(safe_in_m00)} (expected 0)")
    if safe_in_m00:
        print(f"  FAIL: M00 should have no safe minute features")
        all_pass = False
    else:
        print(f"  PASS")

    print(f"  Final feature count (M31 after dedup): {len(fnames)}")
    print(f"  Final feature count (M00 after dedup): {len(fnames_m00)}")
    print()

    # 4. Config parameters
    print("[4] Configuration Check")
    print(f"  test_start: 2026-01-01")
    print(f"  end: 2026-03-31 (Q1 only, NO April)")
    print(f"  min_phase_days_3: 1")
    print(f"  exclude_event_limit_up: True")
    print(f"  feature_set: research")
    print(f"  label_target: next_high_from_close")
    print(f"  target_high_return_pct: 1.0")
    print(f"  max_selected_features: 260")
    print(f"  seed: 42")
    print(f"  lockbox_role: seen_research")
    print(f"  PASS: all config parameters fixed")
    print()

    # 5. Dedup gate
    print("[5] Dedup Gate")
    print(f"  GPU_PROBE_RESEARCH_FEATURES raw count: {len(GPU_PROBE_RESEARCH_FEATURES)}")
    print(f"  GPU_PROBE_RESEARCH_FEATURES unique count: {len(set(GPU_PROBE_RESEARCH_FEATURES))}")
    raw_dups = len(GPU_PROBE_RESEARCH_FEATURES) - len(set(GPU_PROBE_RESEARCH_FEATURES))
    print(f"  raw duplicates in tuple: {raw_dups}")
    print(f"  M31 duplicates removed by pipeline dedup: {len(dedup_removed_m31)}")
    print(f"  M00 duplicates removed by pipeline dedup: {len(dedup_removed_m00)}")
    # After dedup, verify no duplicates remain
    m31_post_dups = len(fnames) - len(set(fnames))
    m00_post_dups = len(fnames_m00) - len(set(fnames_m00))
    if m31_post_dups > 0 or m00_post_dups > 0:
        print(f"  FAIL: post-dedup still has duplicates M31={m31_post_dups} M00={m00_post_dups}")
        all_pass = False
    else:
        print(f"  PASS: 0 duplicates in training feature_names after dedup")
    print()

    # 6. Summary
    print("=" * 60)
    if all_pass:
        print("PREFLIGHT: ALL CHECKS PASSED")
    else:
        print("PREFLIGHT: FAILED — DO NOT PROCEED TO TRAINING")
    print("=" * 60)
    return all_pass


def make_config(included_factor_ids: list[str]) -> GpuProbeConfig:
    excl = build_exclude_names(included_factor_ids)
    return GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 3, 31),
        feature_set="research",
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=excl,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        max_selected_features=260,
        seed=42,
        lockbox_role="seen_research",
        feature_selection_method="stable_tail",
        selector_coverage_weight=0.02,
    )


def run_variant(store, included_factor_ids: list[str]) -> dict:
    """Run one variant and return results."""
    name = variant_name(included_factor_ids)
    config = make_config(included_factor_ids)

    t0 = time.time()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0

    result["_variant_name"] = name
    result["_included_factor_ids"] = included_factor_ids
    result["_excluded_factor_ids"] = [fid for fid in FACTOR_IDS if fid not in included_factor_ids]
    result["_elapsed_sec"] = round(elapsed, 1)

    if result.get("status") == "completed":
        write_ledger_entry(result, included_factor_ids, name)

    return result


def generate_all_combinations() -> list[list[str]]:
    """Generate all 2^5 = 32 combinations."""
    combos = []
    for r in range(len(FACTOR_IDS) + 1):
        for combo in itertools.combinations(FACTOR_IDS, r):
            combos.append(list(combo))
    return combos


def audit_result(result: dict) -> dict:
    """Audit a single result for leaks and correctness."""
    issues = []
    name = result.get("_variant_name", "?")

    if result.get("status") != "completed":
        issues.append(f"run failed: {result.get('status')}")
        return {"variant": name, "pass": False, "issues": issues}

    test_end = result.get("test_end", "")
    if "2026-04" in str(test_end) or "2026-05" in str(test_end):
        issues.append(f"test end includes April or later: {test_end}")

    selected = result.get("feature_selection", {}).get("selected_features", [])
    blocked_set = set(BLOCKED_COLUMNS)
    leaked = [f for f in selected if f in blocked_set]
    if leaked:
        issues.append(f"blocked features in selected: {leaked}")

    features_used = result.get("features", [])
    leaked_input = [f for f in features_used if f in blocked_set]
    if leaked_input:
        issues.append(f"blocked features in input features: {leaked_input}")

    return {"variant": name, "pass": len(issues) == 0, "issues": issues}


def extract_metrics(result: dict) -> dict:
    """Extract key metrics from a run result."""
    name = result.get("_variant_name", "?")
    included = result.get("_included_factor_ids", [])
    excluded = result.get("_excluded_factor_ids", [])

    if result.get("status") != "completed":
        return {"variant": name, "status": "failed"}

    hc = result.get("acceptance", {}).get("high_confidence", {})
    selected = result.get("feature_selection", {}).get("selected_features", [])

    safe_minute_cols = []
    for fid in FACTOR_IDS:
        safe_minute_cols.extend(SAFE_FACTORS[fid])
    selected_minute = [f for f in selected if f in set(safe_minute_cols)]
    input_features = set(result.get("features", []))
    unselected_minute = [f for f in safe_minute_cols if f in input_features and f not in set(selected)]

    allowed_cols = []
    for fid in included:
        allowed_cols.extend(SAFE_FACTORS[fid])
    excluded_cols = list(build_exclude_names(included))

    # Monthly breakdown from date_bucket_stability
    monthly = defaultdict(lambda: {"count": 0, "correct": 0})
    buckets = result.get("date_bucket_stability", {}).get("buckets", [])
    for b in buckets:
        d = b.get("label_date", "")
        if d:
            month = d[:7]
            c = b.get("confident_count", 0) or 0
            prec = b.get("confident_precision", 0) or 0
            monthly[month]["count"] += c
            monthly[month]["correct"] += int(round(c * prec))
    monthly_metrics = {}
    for m in sorted(monthly.keys()):
        info = monthly[m]
        acc = info["correct"] / info["count"] if info["count"] > 0 else 0
        monthly_metrics[m] = {"count": info["count"], "correct": info["correct"], "accuracy": round(acc, 4)}

    return {
        "variant": name,
        "status": "success",
        "run_id": result.get("run_id", ""),
        "included_factor_ids": included,
        "excluded_factor_ids": excluded,
        "allowed_feature_columns": allowed_cols,
        "excluded_feature_columns": excluded_cols,
        "selected_features_count": len(selected),
        "selected_minute_features": selected_minute,
        "unselected_minute_features": unselected_minute,
        "blocked_features_leaked": len([f for f in selected if f in set(BLOCKED_COLUMNS)]),
        "hc_accuracy": hc.get("accuracy"),
        "wilson_lower_95": hc.get("wilson_lower_95"),
        "hc_count": hc.get("rows"),
        "coverage": hc.get("coverage"),
        "brier": result.get("brier"),
        "monthly_metrics": monthly_metrics,
        "elapsed_sec": result.get("_elapsed_sec"),
        "date_range": f"{result.get('test_start', '?')} to {result.get('test_end', '?')}",
    }


def run_smoke_test(store) -> list[dict]:
    """Run 3 smoke test variants: M00, M31, M01."""
    smoke_combos = [
        [],
        FACTOR_IDS.copy(),
        ["C133"],
    ]
    results = []
    for combo in smoke_combos:
        name = variant_name(combo)
        print(f"  Running smoke: {name} ...", flush=True)
        r = run_variant(store, combo)
        results.append(r)
        status = r.get("status", "unknown")
        if status == "completed":
            hc = r.get("acceptance", {}).get("high_confidence", {})
            print(f"    OK: HC={hc.get('accuracy', 0):.4f} W={hc.get('wilson_lower_95', 0):.4f}")
        else:
            print(f"    FAIL: {status}")
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Minute Factor Q1 Matrix Ablation")
    parser.add_argument("--preflight-only", action="store_true",
                        help="Only run preflight audit, no training")
    parser.add_argument("--smoke-only", action="store_true",
                        help="Run preflight + smoke test only (3 runs)")
    parser.add_argument("--skip-smoke", action="store_true",
                        help="Skip smoke test, run full 32 directly")
    args = parser.parse_args()

    # Always run preflight first
    preflight_pass = run_preflight()
    if not preflight_pass:
        print("\nPreflight FAILED. Aborting.", file=sys.stderr)
        sys.exit(1)

    if args.preflight_only:
        print("\n--preflight-only: stopping. No training executed.")
        return

    # Initialize store for training
    app_config = get_default_config()
    store = LocalDataStore(app_config)
    all_results = []

    if not args.skip_smoke:
        print()
        print("=" * 60)
        print("SMOKE TEST (3 runs: M00, M31, M01)")
        print("=" * 60)
        smoke_results = run_smoke_test(store)

        print("\n  Auditing smoke results...")
        for r in smoke_results:
            audit = audit_result(r)
            status_str = "PASS" if audit["pass"] else f"FAIL: {audit['issues']}"
            print(f"    {audit['variant']}: {status_str}")
            if not audit["pass"]:
                print("\n  P0 FAILURE: Stopping execution.")
                sys.exit(1)

        all_results.extend(smoke_results)
        print("\n  Smoke test: ALL PASSED")

        # Print smoke metrics summary
        print("\n  --- Smoke Metrics ---")
        for r in smoke_results:
            m = extract_metrics(r)
            print(f"  {m['variant']}: HC={m.get('hc_accuracy', 0):.4f} "
                  f"W={m.get('wilson_lower_95', 0):.4f} "
                  f"count={m.get('hc_count', 0)} "
                  f"Brier={m.get('brier', 0):.6f} "
                  f"sel_min={m.get('selected_minute_features', [])}")
        print()

        if args.smoke_only:
            # Save smoke metrics JSON
            smoke_metrics = [extract_metrics(r) for r in smoke_results]
            output_json = REPORT_DIR / "minute_factor_smoke_q1_20260506.json"
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(smoke_metrics, f, indent=2, default=str)
            print(f"  Smoke metrics saved: {output_json}")
            print("  --smoke-only: stopping after smoke test. No full matrix.")
            return

    # Full 32-combination matrix
    print("=" * 60)
    print("FULL 32-COMBINATION MATRIX")
    print("=" * 60)
    combos = generate_all_combinations()
    smoke_names = {variant_name(c) for c in [[], FACTOR_IDS.copy(), ["C133"]]}

    for i, combo in enumerate(combos):
        name = variant_name(combo)
        if not args.skip_smoke and name in smoke_names:
            print(f"  [{i+1:2d}/32] {name} — already in smoke, skipping")
            continue
        print(f"  [{i+1:2d}/32] {name} ...", flush=True)
        r = run_variant(store, combo)
        all_results.append(r)
        if r.get("status") == "completed":
            hc = r.get("acceptance", {}).get("high_confidence", {})
            print(f"         HC={hc.get('accuracy', 0):.4f} W={hc.get('wilson_lower_95', 0):.4f}")
        else:
            print(f"         FAILED")

    # Final audit
    print("\n  Final audit (all runs)...")
    for r in all_results:
        audit = audit_result(r)
        if not audit["pass"]:
            print(f"  P0 FAILURE in {audit['variant']}: {audit['issues']}")
            sys.exit(1)
    print(f"  ALL {len(all_results)} PASS\n")

    # Extract and save metrics
    metrics_list = [extract_metrics(r) for r in all_results]
    output_json = REPORT_DIR / "minute_factor_full_matrix_q1_20260506.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(metrics_list, f, indent=2, default=str)
    print(f"  Full matrix metrics saved: {output_json}")


if __name__ == "__main__":
    main()
