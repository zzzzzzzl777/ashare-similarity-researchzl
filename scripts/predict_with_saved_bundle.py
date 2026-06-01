"""
Independent inference script for saved model bundle.

Modes:
  --mode replay        : Offline reproduction using post-close feature cache.
                         Compares against test_predictions.parquet where possible.
  --mode realtime-dry-run : Simulates 14:57 inference. Only uses data available
                         before market close. Tushare moneyflow/daily_basic/stk_limit
                         factors are zeroed (not available at 14:57).

Outputs:
  - Validation JSON (metrics)
  - Candidates CSV (with entry_date and label_date)
  - Timing breakdown

Date semantics:
  --target-date : event date in feature cache (= entry_date = T日尾盘买入日期)
  label_date    : derived from feature cache (= T+1 验证日期, next trading day)
"""
import argparse
import json
import pickle
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BUNDLE_PATH = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260505T113406Z_bb25159b\model_bundle.pt"
)
TEST_PREDICTIONS_PATH = BUNDLE_PATH.parent / "test_predictions.parquet"
FEATURE_CACHE_PATH = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_665406333a7e545d.parquet"
)
META_PATH = BUNDLE_PATH.parent / "model_bundle_meta.json"

OUTPUT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
REPORT_DIR = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs")
CSV_DIR = Path(r"C:\Users\zzzzzzl\Desktop")
SCRIPT_DIR = Path(__file__).resolve().parent
NAME_CACHE_PATH = SCRIPT_DIR / "_symbol_name_cache.json"

# Tushare factors not available at 14:57 (require 15:30+ settlement)
TUSHARE_POST_CLOSE_PREFIXES = (
    "tushare_net_mf_amount", "tushare_lg_buy_sell_ratio",
    "tushare_elg_buy_sell_ratio", "tushare_mf_strength",
    "tushare_sm_sell_pressure", "tushare_volume_ratio",
    "tushare_free_share", "tushare_main_force_divergence",
    "tushare_ff_adjusted_flow",
)

META_COLS = frozenset([
    "symbol", "date", "label_date", "close", "actual",
    "next_close_return_pct", "next_high_return_pct", "next_low_return_pct",
    "next_return_pct", "next_close_up", "hard_to_hold_2pct", "hard_to_hold_3pct",
    "limit_up_like", "short_phase_days_3", "turnover",
])


# ---------------------------------------------------------------------------
# Symbol name mapping (from local cache only, no network calls)
# ---------------------------------------------------------------------------
def load_name_map() -> dict[str, str]:
    """Load symbol -> name mapping from local cache file."""
    if NAME_CACHE_PATH.exists():
        with open(NAME_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# Bundle loader
# ---------------------------------------------------------------------------
def load_bundle(path: Path, device: str = "cpu"):
    """Load and unpack model bundle."""
    bundle = torch.load(path, map_location=device, weights_only=False)
    members = []
    for m in bundle["members"]:
        model = pickle.loads(m["model_bytes"])
        members.append({"model": model, "model_name": m["model_name"],
                        "model_kind": m["model_kind"]})
    iso_model = pickle.loads(bundle["iso_model_bytes"]) if bundle.get("iso_model_bytes") else None
    return {
        "model_kind": bundle["model_kind"],
        "model_name": bundle["model_name"],
        "member_names": bundle["member_names"],
        "members": members,
        "mean": bundle["mean"],
        "std": bundle["std"],
        "selected_indices": bundle["selected_indices"],
        "feature_names": bundle["feature_names"],
        "selected_feature_names": bundle["selected_feature_names"],
        "iso_model": iso_model,
        "calibration_used": bundle["calibration_used"],
        "threshold": bundle["threshold"],
        "confidence_band": bundle.get("confidence_band"),
    }


# ---------------------------------------------------------------------------
# Inference functions (standalone, mirrors gpu_probe.py logic)
# ---------------------------------------------------------------------------
def normalize_features(raw: torch.Tensor, mean: torch.Tensor, std: torch.Tensor) -> torch.Tensor:
    std_safe = std.clone()
    std_safe[std_safe == 0] = 1.0
    return (raw - mean) / std_safe


def select_features(x: torch.Tensor, indices: torch.Tensor) -> torch.Tensor:
    return x[:, indices]


def predict_member(model, x_np: np.ndarray) -> np.ndarray:
    return model.predict_proba(x_np)[:, 1].astype(np.float32)


def predict_ensemble_average(members: list, x_np: np.ndarray) -> np.ndarray:
    probs = np.stack([predict_member(m["model"], x_np) for m in members], axis=0)
    return probs.mean(axis=0)


def apply_isotonic(prob: np.ndarray, iso_model) -> np.ndarray:
    if iso_model is None:
        return prob
    return iso_model.predict(prob.astype(np.float64)).astype(np.float32)


def run_inference(bundle: dict, raw_features: np.ndarray, device: str = "cpu") -> np.ndarray:
    x = torch.as_tensor(raw_features, dtype=torch.float32, device=device)
    x = normalize_features(x, bundle["mean"].to(device), bundle["std"].to(device))
    if bundle["selected_indices"] is not None:
        x = select_features(x, bundle["selected_indices"].to(device))
    x_np = x.detach().cpu().numpy()
    prob = predict_ensemble_average(bundle["members"], x_np)
    if bundle["calibration_used"] == "isotonic":
        prob = apply_isotonic(prob, bundle["iso_model"])
    return prob


# ---------------------------------------------------------------------------
# Feature loading
# ---------------------------------------------------------------------------
def load_features_from_cache(feature_names: tuple, target_date: str = None,
                             mode: str = "replay") -> pd.DataFrame:
    import pyarrow.parquet as pq
    cols_to_load = list(META_COLS | set(feature_names))
    available_cols = set(pq.read_schema(FEATURE_CACHE_PATH).names)
    cols_to_load = [c for c in cols_to_load if c in available_cols]

    data = pd.read_parquet(FEATURE_CACHE_PATH, columns=cols_to_load)

    if target_date:
        data = data[data["date"] == pd.Timestamp(target_date)]

    if mode == "realtime-dry-run":
        for col in data.columns:
            if any(col.startswith(p) for p in TUSHARE_POST_CLOSE_PREFIXES):
                data[col] = 0.0

    return data


def check_date_available(target_date: str) -> tuple[bool, int]:
    """Check if target_date has rows in feature cache. Returns (available, row_count)."""
    import pyarrow.parquet as pq
    df = pd.read_parquet(FEATURE_CACHE_PATH, columns=["date"])
    count = int((df["date"] == pd.Timestamp(target_date)).sum())
    return count > 0, count


# ---------------------------------------------------------------------------
# Phase 1: Offline reproduction test
# ---------------------------------------------------------------------------
def phase1_replay_validation(bundle: dict, device: str = "cpu") -> dict:
    """
    Attempt offline reproduction against test_predictions.parquet.

    LIMITATION: Raw test feature matrix NOT saved. Cannot do strict positional
    reproduction. Uses (symbol, date) merge on unique-pair subset as approximate check.
    """
    report = {
        "phase": "replay_validation",
        "strict_reproduction": False,
        "limitation": (
            "Raw test feature matrix not saved in run artifacts. "
            "Feature cache row order differs from test set (pipeline shuffles). "
            "Validation uses (symbol, date) merge on unique-pair subset (99.4% coverage). "
            "This is approximate verification, NOT strict positional reproduction."
        ),
    }

    timings = {}
    t0 = time.perf_counter()
    tp = pd.read_parquet(TEST_PREDICTIONS_PATH)
    timings["load_test_predictions_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    feature_names = bundle["feature_names"]
    required_meta = ["symbol", "date", "label_date", "limit_up_like"]
    cols = list(set(required_meta) | set(feature_names))
    import pyarrow.parquet as pq
    available = set(pq.read_schema(FEATURE_CACHE_PATH).names)
    cols = [c for c in cols if c in available]
    fc = pd.read_parquet(FEATURE_CACHE_PATH, columns=cols)
    timings["load_feature_cache_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    test_fc = fc[
        (fc["date"] >= "2026-01-05") &
        (fc["label_date"] <= "2026-04-30") &
        (fc["limit_up_like"] != 1)
    ].copy()
    timings["filter_s"] = time.perf_counter() - t0

    report["feature_cache_test_rows"] = len(test_fc)
    report["test_predictions_rows"] = len(tp)
    report["row_count_match"] = len(test_fc) == len(tp)

    t0 = time.perf_counter()
    test_fc["_fc_idx"] = np.arange(len(test_fc))
    tp_unique = tp.drop_duplicates(subset=["symbol", "date"], keep=False).copy()
    fc_unique = test_fc.drop_duplicates(subset=["symbol", "date"], keep=False).copy()
    merged = tp_unique.merge(fc_unique[["symbol", "date", "_fc_idx"]],
                             on=["symbol", "date"], how="inner")
    timings["merge_s"] = time.perf_counter() - t0

    report["unique_pair_rows"] = len(merged)
    report["duplicate_pair_rows_excluded"] = len(tp) - len(tp_unique)
    report["coverage_pct"] = round(len(merged) / len(tp) * 100, 2)

    t0 = time.perf_counter()
    fc_indices = merged["_fc_idx"].values
    missing_features = [f for f in feature_names if f not in test_fc.columns]
    if missing_features:
        report["missing_features"] = missing_features
    raw_features = test_fc.iloc[fc_indices][list(feature_names)].to_numpy(dtype=np.float32)
    timings["feature_extract_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    pred_prob = run_inference(bundle, raw_features, device=device)
    timings["inference_s"] = time.perf_counter() - t0

    expected_prob = merged["probability"].values.astype(np.float32)
    diff = np.abs(pred_prob - expected_prob)

    report["max_abs_diff"] = float(diff.max())
    report["mean_abs_diff"] = float(diff.mean())
    report["median_abs_diff"] = float(np.median(diff))
    report["p99_abs_diff"] = float(np.percentile(diff, 99))
    report["exact_match_rows"] = int((diff == 0).sum())
    report["exact_match_pct"] = round(int((diff == 0).sum()) / len(diff) * 100, 2)

    report["max_abs_diff_lt_1e6"] = bool(diff.max() < 1e-6)
    report["max_abs_diff_lt_1e4"] = bool(diff.max() < 1e-4)

    for topk in [30, 50, 100]:
        if len(pred_prob) >= topk:
            pred_top = set(np.argsort(-pred_prob)[:topk])
            expected_top = set(np.argsort(-expected_prob)[:topk])
            overlap = len(pred_top & expected_top) / topk
            report[f"top{topk}_overlap"] = round(overlap, 4)

    for thr in [0.75, 0.80]:
        pred_above = set(np.where(pred_prob >= thr)[0])
        expected_above = set(np.where(expected_prob >= thr)[0])
        if len(expected_above) > 0:
            recall = len(pred_above & expected_above) / len(expected_above)
            union = len(pred_above | expected_above)
            jaccard = len(pred_above & expected_above) / union if union > 0 else 1.0
        else:
            recall = 1.0
            jaccard = 1.0
        thr_key = f"t{thr:.2f}"
        report[f"{thr_key}_recall"] = round(recall, 4)
        report[f"{thr_key}_jaccard"] = round(jaccard, 4)
        report[f"{thr_key}_expected_count"] = len(expected_above)
        report[f"{thr_key}_pred_count"] = len(pred_above)

    report["passed"] = report["max_abs_diff_lt_1e6"]
    report["timings"] = timings
    return report


# ---------------------------------------------------------------------------
# Phase 2: Speed benchmark
# ---------------------------------------------------------------------------
def phase2_speed_benchmark(bundle: dict, target_date: str, mode: str,
                           device: str = "cpu") -> dict:
    results = {"target_date": target_date, "mode": mode, "device": device}

    for run_type in ["cold_start", "warm_cache"]:
        timings = {}

        if run_type == "cold_start":
            t0 = time.perf_counter()
            b = load_bundle(BUNDLE_PATH, device=device)
            timings["bundle_load_s"] = time.perf_counter() - t0
        else:
            b = bundle
            timings["bundle_load_s"] = 0.0

        t0 = time.perf_counter()
        data = load_features_from_cache(b["feature_names"], target_date=target_date, mode=mode)
        timings["feature_load_s"] = time.perf_counter() - t0

        if len(data) == 0:
            results[run_type] = {"error": f"No data for date {target_date}", "timings": timings}
            continue

        t0 = time.perf_counter()
        if "limit_up_like" in data.columns:
            data = data[data["limit_up_like"] != 1].copy()
        timings["filter_s"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        feature_cols = list(b["feature_names"])
        missing = [f for f in feature_cols if f not in data.columns]
        for f in missing:
            data[f] = 0.0
        raw_features = data[feature_cols].to_numpy(dtype=np.float32)
        timings["feature_extract_s"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        x = torch.as_tensor(raw_features, dtype=torch.float32, device=device)
        x = normalize_features(x, b["mean"].to(device), b["std"].to(device))
        timings["normalize_s"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        if b["selected_indices"] is not None:
            x = select_features(x, b["selected_indices"].to(device))
        timings["feature_select_s"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        x_np = x.detach().cpu().numpy()
        prob = predict_ensemble_average(b["members"], x_np)
        timings["predict_s"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        if b["calibration_used"] == "isotonic":
            prob = apply_isotonic(prob, b["iso_model"])
        timings["isotonic_s"] = time.perf_counter() - t0

        timings["total_s"] = sum(timings.values())
        timings["rows"] = len(data)
        timings["features_full"] = len(b["feature_names"])
        timings["features_selected"] = len(b["selected_feature_names"])
        results[run_type] = timings

    warm = results.get("warm_cache", {})
    if isinstance(warm, dict) and "total_s" in warm:
        results["warm_total_s"] = warm["total_s"]
        results["within_3min"] = warm["total_s"] < 180.0
        results["feasibility_note"] = (
            "Warm cache timing is from pre-built parquet, NOT real-time feature construction. "
            "Does NOT represent true 14:57 latency (which requires building 376 features live)."
        )

    return results


# ---------------------------------------------------------------------------
# Generate candidates CSV
# ---------------------------------------------------------------------------
def generate_candidates_csv(bundle: dict, target_date: str, mode: str,
                            name_map: dict = None,
                            device: str = "cpu") -> tuple[pd.DataFrame, str]:
    """
    Generate candidate CSV for a target date.

    target_date = event date = entry_date (T日尾盘买入)
    label_date is derived from feature cache (next trading day)
    """
    data = load_features_from_cache(bundle["feature_names"], target_date=target_date, mode=mode)

    if len(data) == 0:
        return pd.DataFrame(), "no_data"

    # Preserve metadata before filtering
    symbols = data["symbol"].values.copy()
    limit_up_col = data["limit_up_like"].values.copy() if "limit_up_like" in data.columns else np.zeros(len(data))
    close_col = data["close"].values.copy() if "close" in data.columns else np.full(len(data), np.nan)
    turnover_col = data["turnover"].values.copy() if "turnover" in data.columns else np.full(len(data), np.nan)
    cache_label_date = data["label_date"].values.copy() if "label_date" in data.columns else None

    # Apply exclude_event_limit_up
    if "limit_up_like" in data.columns:
        mask = (data["limit_up_like"] != 1).values
        data = data[mask].copy()
        symbols = symbols[mask]
        limit_up_col = limit_up_col[mask]
        close_col = close_col[mask]
        turnover_col = turnover_col[mask]
        if cache_label_date is not None:
            cache_label_date = cache_label_date[mask]

    if len(data) == 0:
        return pd.DataFrame(), "no_data_after_filter"

    feature_cols = list(bundle["feature_names"])
    missing = [f for f in feature_cols if f not in data.columns]
    for f in missing:
        data[f] = 0.0
    raw_features = data[feature_cols].to_numpy(dtype=np.float32)

    prob = run_inference(bundle, raw_features, device=device)

    threshold = bundle["threshold"]
    label_date_val = str(cache_label_date[0])[:10] if cache_label_date is not None else None

    # Build name column
    names = []
    if name_map:
        names = [name_map.get(s, "") for s in symbols]
    else:
        names = [""] * len(symbols)

    candidates = pd.DataFrame({
        "symbol": symbols,
        "name": names,
        "date": pd.Timestamp(target_date),
        "entry_date": pd.Timestamp(target_date),
        "label_date": pd.Timestamp(label_date_val) if label_date_val else pd.NaT,
        "probability": prob,
        "threshold": threshold,
        "close": close_col,
        "turnover": turnover_col,
        "limit_up_like": limit_up_col,
        "mode": mode,
    })

    candidates = candidates.sort_values("probability", ascending=False).reset_index(drop=True)
    candidates.insert(0, "rank", np.arange(1, len(candidates) + 1))

    return candidates, "ok"


# ---------------------------------------------------------------------------
# Output filename validation
# ---------------------------------------------------------------------------
def validate_output_csv_name(csv_path: Path, target_date: str, allow_mismatch: bool) -> bool:
    """
    Check that output CSV filename date matches target_date.
    Returns True if OK, raises SystemExit if mismatch and not allowed.
    """
    fname = csv_path.stem
    date_pattern = re.search(r"(\d{8})", fname)
    if not date_pattern:
        return True
    fname_date = date_pattern.group(1)
    target_compact = target_date.replace("-", "")
    if fname_date != target_compact:
        msg = (
            f"ERROR: Output filename date '{fname_date}' does not match "
            f"target-date '{target_compact}' (target_date={target_date}).\n"
            f"  File: {csv_path}\n"
            f"  This would create a misleading file where the name implies a different date "
            f"than the actual content.\n"
            f"  Use --allow-mismatched-output-name to override, or fix --target-date / --output-csv."
        )
        if allow_mismatch:
            print(f"WARNING: {msg}")
            return True
        else:
            print(msg, file=sys.stderr)
            sys.exit(1)
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Inference with saved model bundle")
    parser.add_argument("--mode", choices=["replay", "realtime-dry-run"], default="replay",
                        help="replay: post-close features allowed. realtime-dry-run: simulates 14:57")
    parser.add_argument("--target-date", default="2026-04-29",
                        help="Event date in feature cache (= entry_date = T日尾盘买入)")
    parser.add_argument("--device", default="cpu", help="torch device (cpu/cuda)")
    parser.add_argument("--skip-phase1", action="store_true", help="Skip reproduction validation")
    parser.add_argument("--skip-phase2", action="store_true", help="Skip speed benchmark")
    parser.add_argument("--output-csv", default=None, help="Override output CSV path")
    parser.add_argument("--allow-mismatched-output-name", action="store_true",
                        help="Allow output CSV filename date to differ from target-date")
    args = parser.parse_args()

    print(f"=== Bundle Inference Script ===")
    print(f"Mode: {args.mode}")
    print(f"Target date (= entry_date): {args.target_date}")
    print(f"Device: {args.device}")
    print(f"Bundle: {BUNDLE_PATH}")
    print()

    # --- Check target date availability ---
    avail, row_count = check_date_available(args.target_date)
    if not avail:
        msg = (
            f"FATAL: Feature cache has 0 rows for target_date={args.target_date}.\n"
            f"  Cache: {FEATURE_CACHE_PATH}\n"
            f"  Cannot generate candidates without feature data.\n"
            f"  Available date range: check feature cache metadata.\n"
            f"  Do NOT fabricate candidates from a different date and label them as {args.target_date}."
        )
        print(msg, file=sys.stderr)
        # Write a no_data result JSON
        no_data_result = {
            "generated_at": datetime.now().astimezone().isoformat(),
            "status": "no_data",
            "target_date": args.target_date,
            "feature_cache_rows_for_date": 0,
            "error": f"Feature cache has no rows for {args.target_date}. Cannot generate candidates.",
        }
        json_path = OUTPUT_DIR / "saved_bundle_inference_validation_20260505.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(no_data_result, f, indent=2, default=str)
        sys.exit(1)

    print(f"Feature cache rows for {args.target_date}: {row_count}")
    print()

    # --- Validate output CSV name ---
    if args.output_csv:
        csv_path = Path(args.output_csv)
        validate_output_csv_name(csv_path, args.target_date, args.allow_mismatched_output_name)
    else:
        target_compact = args.target_date.replace("-", "")
        csv_path = CSV_DIR / f"saved_bundle_candidates_{target_compact}.csv"

    # --- Load bundle ---
    t0 = time.perf_counter()
    bundle = load_bundle(BUNDLE_PATH, device=args.device)
    bundle_load_time = time.perf_counter() - t0
    print(f"Bundle loaded in {bundle_load_time:.3f}s")
    print(f"  Model: {bundle['model_name']} ({bundle['model_kind']})")
    print(f"  Members: {bundle['member_names']}")
    print(f"  Features: {len(bundle['feature_names'])} full, {len(bundle['selected_feature_names'])} selected")
    print(f"  Calibration: {bundle['calibration_used']}")
    print(f"  Threshold: {bundle['threshold']:.4f}")
    print()

    # --- Load name mapping ---
    name_map = load_name_map()
    print(f"Name mapping loaded: {len(name_map)} entries")
    print()

    all_results = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "bundle_path": str(BUNDLE_PATH),
        "mode": args.mode,
        "target_date": args.target_date,
        "entry_date": args.target_date,
        "device": args.device,
        "bundle_load_s": bundle_load_time,
    }

    # --- Phase 1: Replay validation ---
    if not args.skip_phase1 and args.mode == "replay":
        print("--- Phase 1: Offline Reproduction Test ---")
        print("NOTE: Raw test feature matrix NOT saved in run artifacts.")
        print("      Using (symbol, date) merge on unique pairs (99.4% coverage).")
        print("      This is APPROXIMATE verification, not strict positional reproduction.")
        print("      Cannot claim strict reproduction of same-run output.")
        print()
        phase1 = phase1_replay_validation(bundle, device=args.device)
        all_results["phase1"] = phase1

        print(f"  Rows compared: {phase1.get('unique_pair_rows', 0)} / {phase1.get('test_predictions_rows', 0)}")
        print(f"  Coverage: {phase1.get('coverage_pct', 0)}%")
        print(f"  Exact match: {phase1.get('exact_match_pct', 0)}% ({phase1.get('exact_match_rows', 0)} rows)")
        print(f"  max_abs_diff: {phase1.get('max_abs_diff', -1):.2e}")
        print(f"  mean_abs_diff: {phase1.get('mean_abs_diff', -1):.2e}")
        status = "PASSED (strict)" if phase1.get("passed") else "NOT PASSED (approximate only)"
        print(f"  Status: {status}")
        print()
    elif args.mode == "realtime-dry-run":
        print("--- Phase 1: Skipped (realtime-dry-run cannot reproduce original) ---")
        all_results["phase1"] = {"skipped": True, "reason": "realtime-dry-run zeros post-close features"}
        print()

    # --- Phase 2: Speed benchmark ---
    if not args.skip_phase2:
        print(f"--- Phase 2: Speed Benchmark (date={args.target_date}, mode={args.mode}) ---")
        phase2 = phase2_speed_benchmark(bundle, args.target_date, args.mode, device=args.device)
        all_results["phase2"] = phase2

        for run_type in ["cold_start", "warm_cache"]:
            t = phase2.get(run_type, {})
            if isinstance(t, dict) and "total_s" in t:
                print(f"  [{run_type}] total={t['total_s']:.3f}s  "
                      f"(load={t.get('bundle_load_s',0):.3f} + "
                      f"feat={t.get('feature_load_s',0):.3f} + "
                      f"infer={t.get('predict_s',0):.3f} + "
                      f"iso={t.get('isotonic_s',0):.3f})")
            elif isinstance(t, dict) and "error" in t:
                print(f"  [{run_type}] ERROR: {t['error']}")

        if phase2.get("within_3min") is not None:
            feasible = "YES" if phase2["within_3min"] else "NO"
            print(f"  Within 3-min window (warm): {feasible} ({phase2.get('warm_total_s', -1):.3f}s)")
        print(f"  NOTE: This is parquet cache read speed, NOT real-time feature construction speed.")
        print()

    # --- Generate candidates ---
    print(f"--- Generating Candidates (date={args.target_date}, mode={args.mode}) ---")
    candidates, gen_status = generate_candidates_csv(
        bundle, args.target_date, args.mode, name_map=name_map, device=args.device,
    )

    if gen_status == "ok" and len(candidates) > 0:
        ed = candidates["entry_date"].iloc[0]
        ld = candidates["label_date"].iloc[0]
        print(f"  entry_date = {str(ed)[:10]} (T日尾盘买入)")
        print(f"  label_date = {str(ld)[:10]} (T+1验证日期)")

        above_threshold = int((candidates["probability"] >= bundle["threshold"]).sum())
        name_filled = int((candidates["name"] != "").sum())
        name_pct = round(name_filled / len(candidates) * 100, 1)
        print(f"  Total rows: {len(candidates)}")
        print(f"  Above threshold ({bundle['threshold']:.2f}): {above_threshold}")
        print(f"  Name coverage: {name_filled}/{len(candidates)} ({name_pct}%)")

        candidates.to_csv(csv_path, index=False)
        print(f"  Saved to: {csv_path}")

        all_results["candidates_csv"] = str(csv_path)
        all_results["candidates_total"] = len(candidates)
        all_results["candidates_above_threshold"] = above_threshold
        all_results["name_coverage_pct"] = name_pct
    else:
        print(f"  No candidates generated (status: {gen_status})")
        all_results["candidates_csv"] = None
    print()

    # --- Save JSON ---
    json_path = OUTPUT_DIR / "saved_bundle_inference_validation_20260505.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"Results JSON: {json_path}")

    # --- Summary ---
    print("\n=== Summary ===")
    if all_results.get("phase1", {}).get("passed"):
        print("Phase 1: PASSED strict (max_abs_diff < 1e-6)")
    elif all_results.get("phase1", {}).get("strict_reproduction") is False:
        pct = all_results["phase1"].get("exact_match_pct", 0)
        print(f"Phase 1: Approximate only — {pct}% exact match, NOT strict reproduction")
    elif all_results.get("phase1", {}).get("skipped"):
        print("Phase 1: SKIPPED")
    else:
        print("Phase 1: NOT RUN")

    if phase2_data := all_results.get("phase2"):
        warm = phase2_data.get("warm_cache", {})
        if isinstance(warm, dict) and "total_s" in warm:
            print(f"Phase 2: warm={warm['total_s']:.3f}s (parquet cache, not real-time)")

    print(f"Bundle: {bundle['model_name']}")
    print(f"NOT claimed as 14:57 real-time ready")
    print(f"NOT committed, NOT pushed")

    return all_results


if __name__ == "__main__":
    main()
