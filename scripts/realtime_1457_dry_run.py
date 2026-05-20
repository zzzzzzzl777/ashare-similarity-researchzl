#!/usr/bin/env python
"""14:57 Realtime Dry-Run: Independent feature construction + inference validation.

Builds the 376-feature frame INDEPENDENTLY from raw daily bars (not from the
post-close feature cache), applies fallback strategies for features unavailable
at 14:57, runs inference through the saved model bundle, and compares against
the post-close replay reference.

Two modes:
- daily_proxy (default for 2026-04-29): Uses T-day daily bar as proxy for 14:57.
  NOT a true 14:57 validation — daily close includes call auction (14:57-15:00).
- strict_1457 (requires 5-min bars): Uses only T-1 daily + T-day bars through 14:55.
  Only possible for dates with minute bar coverage.

Usage:
    python scripts/realtime_1457_dry_run.py --target-date 2026-04-29
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

SUBAGENT_ROOT = Path("C:/Users/zzzzzzl/Desktop/subagent")
sys.path.insert(0, str(SUBAGENT_ROOT / "src"))

from ashare_similarity.prediction.gpu_probe import (
    GPU_PROBE_ALL_FEATURES,
    GPU_PROBE_CROSS_MARKET_FEATURES,
    GPU_PROBE_INTRADAY_FACTOR_FEATURES,
    GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES,
    GPU_PROBE_MARKET_INDEX_SYMBOLS,
    GPU_PROBE_RESEARCH_FEATURES,
    GPU_PROBE_TGB_FACTOR_FEATURES,
    GPU_PROBE_THS_SECTOR_FEATURES,
    GPU_PROBE_TUSHARE_FACTOR_FEATURES,
    GpuProbeConfig,
    _add_cross_section_features,
    _attach_free_factor_features,
    _attach_tgb_factor_features,
    _daily_context_slice,
    _ensure_feature_columns,
    _symbol_feature_frame,
)
from ashare_similarity.prediction.free_data_factors import (
    build_cross_market_return_factor,
)
from ashare_similarity.prediction.ths_sector_factors import (
    build_ths_sector_factors,
)
from ashare_similarity.prediction.factor_cache_manager import merge_factor_frames
from ashare_similarity.prediction.limit_pool_snapshots import (
    build_limit_pool_snapshot_factors,
    load_snapshot_bundles,
)

RUNTIME_ROOT = Path("E:/ashare_similarity_runtime/data")
DAILY_BARS_DIR = RUNTIME_ROOT / "raw" / "bars" / "daily"
MARKET_INDEX_DIR = RUNTIME_ROOT / "cache" / "market" / "daily"
TUSHARE_DIR = RUNTIME_ROOT / "cache" / "prediction" / "tushare"
LIMIT_POOL_DIR = RUNTIME_ROOT / "cache" / "prediction" / "limit_pool_snapshots"
FEATURE_CACHE_PATH = (
    RUNTIME_ROOT
    / "reports"
    / "prediction"
    / "feature_cache"
    / "gpu_probe_features_665406333a7e545d.parquet"
)
BUNDLE_PATH = (
    RUNTIME_ROOT
    / "reports"
    / "prediction"
    / "runs"
    / "gpu_probe_20260505T113406Z_bb25159b"
    / "model_bundle.pt"
)
OUTPUT_DIR = RUNTIME_ROOT / "reports" / "prediction" / "realtime_1457_tmp"
DESKTOP = Path("C:/Users/zzzzzzl/Desktop")

# Feature status categories (per user specification)
STATUS_STRICT_1457 = "available_strict_1457"
STATUS_PROXY_DAILY = "proxy_daily_bar"
STATUS_T_MINUS_1 = "t_minus_1_lag"
STATUS_POST_CLOSE = "post_close_unavailable"


def load_bundle(path: Path) -> dict[str, Any]:
    import torch
    return torch.load(path, map_location="cpu", weights_only=False)


def load_daily_bars(symbols: list[str], start: date, end: date) -> dict[str, pd.DataFrame]:
    bars: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        path = DAILY_BARS_DIR / f"{sym}.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        if "date" not in df.columns:
            continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
        df = df[mask].reset_index(drop=True)
        if not df.empty:
            bars[sym] = df
    return bars


def discover_symbols() -> list[str]:
    return sorted(
        p.stem for p in DAILY_BARS_DIR.glob("*.parquet")
        if len(p.stem) == 6 and p.stem.isdigit()
    )


def build_config(target_date: date) -> GpuProbeConfig:
    lookback_start = target_date - timedelta(days=400)
    # end must be BEYOND target_date because _symbol_feature_frame
    # excludes the last row (needs T+1 bar for label computation)
    end_date = target_date + timedelta(days=5)
    return GpuProbeConfig(
        start=lookback_start,
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=end_date,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_set="research",
    )


def build_symbol_features(
    all_bars: dict[str, pd.DataFrame],
    config: GpuProbeConfig,
    target_date: date,
) -> tuple[pd.DataFrame, list[pd.DataFrame], dict[str, float]]:
    import torch

    device = torch.device("cpu")
    examples: list[pd.DataFrame] = []
    context_frames: list[pd.DataFrame] = []
    timing: dict[str, float] = {}

    t0 = time.perf_counter()
    total = len(all_bars)
    for idx, (sym, bars) in enumerate(all_bars.items(), 1):
        ctx = _daily_context_slice(bars, symbol=sym, start=config.start, end=config.end)
        if not ctx.empty:
            context_frames.append(ctx)
        frame = _symbol_feature_frame(
            bars,
            symbol=sym,
            start=config.start,
            end=config.end,
            device=device,
            config=config,
        )
        if not frame.empty:
            target_rows = frame[frame["date"].dt.date == target_date]
            if not target_rows.empty:
                examples.append(target_rows)
        if idx == 1 or idx % 100 == 0 or idx == total:
            print(
                f"[1457-dry-run] symbol_features {idx}/{total} "
                f"accepted={len(examples)} elapsed={time.perf_counter()-t0:.1f}s",
                file=sys.stderr, flush=True,
            )
    timing["symbol_features_sec"] = time.perf_counter() - t0

    if not examples:
        return pd.DataFrame(), context_frames, timing

    data = pd.concat(examples, ignore_index=True)
    return data, context_frames, timing


def attach_cross_section(data: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    t0 = time.perf_counter()
    return _add_cross_section_features(data), time.perf_counter() - t0


def attach_free_factors(
    data: pd.DataFrame, context_frames: list[pd.DataFrame]
) -> tuple[pd.DataFrame, float]:
    t0 = time.perf_counter()
    result, _ = _attach_free_factor_features(data, daily_context_frames=context_frames)
    return result, time.perf_counter() - t0


def attach_market_index(data: pd.DataFrame, config: GpuProbeConfig) -> tuple[pd.DataFrame, float]:
    t0 = time.perf_counter()
    index_frames: dict[str, pd.DataFrame] = {}
    for symbol in GPU_PROBE_MARKET_INDEX_SYMBOLS:
        path = MARKET_INDEX_DIR / f"{symbol}.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        if "date" not in df.columns or "close" not in df.columns:
            continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        mask = (df["date"].dt.date >= config.start) & (df["date"].dt.date <= config.end)
        df = df[mask].reset_index(drop=True)
        if not df.empty:
            index_frames[symbol] = df
    if index_frames:
        factor = build_cross_market_return_factor(index_frames)
        data, _ = merge_factor_frames(data, [factor])
    else:
        for col in GPU_PROBE_CROSS_MARKET_FEATURES:
            data[col] = 0.0
            data[f"{col}_available"] = 0.0
    return data, time.perf_counter() - t0


def attach_tgb(
    data: pd.DataFrame, context_frames: list[pd.DataFrame]
) -> tuple[pd.DataFrame, float]:
    t0 = time.perf_counter()
    result, _ = _attach_tgb_factor_features(data, daily_context_frames=context_frames)
    return result, time.perf_counter() - t0


def attach_ths_sector(data: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    t0 = time.perf_counter()
    if TUSHARE_DIR.is_dir():
        try:
            factor = build_ths_sector_factors(TUSHARE_DIR)
            if not factor.frame.empty:
                data, _ = merge_factor_frames(data, [factor])
            else:
                for col in GPU_PROBE_THS_SECTOR_FEATURES:
                    data[col] = 0.0
        except Exception:
            for col in GPU_PROBE_THS_SECTOR_FEATURES:
                data[col] = 0.0
    else:
        for col in GPU_PROBE_THS_SECTOR_FEATURES:
            data[col] = 0.0
    return data, time.perf_counter() - t0


def attach_limit_pool(data: pd.DataFrame) -> tuple[pd.DataFrame, float, str]:
    t0 = time.perf_counter()
    status = "unavailable"
    if LIMIT_POOL_DIR.is_dir():
        try:
            frames = load_snapshot_bundles(LIMIT_POOL_DIR)
            factors = build_limit_pool_snapshot_factors(frames)
            if factors:
                data, _ = merge_factor_frames(data, factors)
                status = "available"
            else:
                for col in GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES:
                    data[col] = 0.0
                status = "no_data"
        except Exception as exc:
            for col in GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES:
                data[col] = 0.0
            status = f"failed: {exc}"
    else:
        for col in GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES:
            data[col] = 0.0
    return data, time.perf_counter() - t0, status


def classify_features(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Classify each feature by its 14:57 availability status.

    Categories (per user specification):
    - available_strict_1457: Can be computed from T-1 daily + T intraday <=14:57
    - proxy_daily_bar: Uses T-day daily bar (includes 14:57-15:00 call auction)
    - t_minus_1_lag: Uses T-1 data (available at 14:57 but lagged)
    - post_close_unavailable: Requires post-close settlement data
    """
    feature_names = bundle["feature_names"]
    selected_indices = bundle["selected_indices"].numpy().tolist()
    selected_set = set(feature_names[i] for i in selected_indices)

    tushare_set = set(GPU_PROBE_TUSHARE_FACTOR_FEATURES)
    intraday_set = set(GPU_PROBE_INTRADAY_FACTOR_FEATURES)
    limit_pool_set = set(GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES)
    cross_market_set = set(GPU_PROBE_CROSS_MARKET_FEATURES) | {
        f"{c}_available" for c in GPU_PROBE_CROSS_MARKET_FEATURES
    }
    tgb_set = set(GPU_PROBE_TGB_FACTOR_FEATURES)
    ths_set = set(GPU_PROBE_THS_SECTOR_FEATURES)

    # Cross-section features that are derived from symbol features
    cs_derived = {
        "rel_ret_1_to_market", "rel_range_to_market",
        "volume_z_x_cs_ret_rank", "close_pos_x_cs_range_rank",
        "market_cycle_failed_pressure", "market_cycle_broken_pressure",
        "market_cycle_seal_pressure", "market_monday_hot_new_high_risk",
        "market_hot_cycle_short_pressure", "chase_market_up_alignment",
        "strong_market_anti_drop", "weak_market_oversold_rebound",
        "breakout_first_board_proxy", "second_board_leader_proxy",
        "seal80_second_board_quality", "bull_hotspot_bear_oversold_signal",
        "money_effect_chase_alignment", "collapse_hot_stock_risk",
        "weak_rebound_money_effect", "index_panic_rebound_setup",
        "index_panic_rebound_leader", "index_panic_low_position_repair",
    }

    classification: dict[str, dict[str, Any]] = {}
    for i, name in enumerate(feature_names):
        is_selected = name in selected_set

        if name in tushare_set:
            category = "tushare"
            status = STATUS_POST_CLOSE
        elif name in intraday_set:
            category = "intraday_minute"
            status = STATUS_POST_CLOSE
        elif name in limit_pool_set:
            # Limit pool snapshots are observable intraday but stored data is EOD
            category = "limit_pool_snapshot"
            status = STATUS_T_MINUS_1
        elif name in cross_market_set:
            # A-share index uses T-day close → proxy
            category = "cross_market_index"
            status = STATUS_PROXY_DAILY
        elif name in tgb_set:
            # TGB derived from T-day daily bars → proxy
            category = "tgb"
            status = STATUS_PROXY_DAILY
        elif name in ths_set:
            # THS sector from tushare cache → T-1 lag
            category = "ths_sector"
            status = STATUS_T_MINUS_1
        elif name.startswith("cs_") or name in cs_derived:
            # Cross-section computed from T-day symbol features → proxy
            category = "cross_section"
            status = STATUS_PROXY_DAILY
        elif name.startswith("market_") or name.startswith("board_"):
            # Market emotion / board structure from T-day daily bars → proxy
            category = "market_emotion_board"
            status = STATUS_PROXY_DAILY
        elif name.endswith("_available"):
            # Availability flags follow their base feature
            base = name[:-10]
            if base in tushare_set or f"{base}" in {n[:-10] for n in tushare_set if n.endswith("_available")}:
                category = "tushare"
                status = STATUS_POST_CLOSE
            elif base in intraday_set:
                category = "intraday_minute"
                status = STATUS_POST_CLOSE
            elif base in limit_pool_set:
                category = "limit_pool_snapshot"
                status = STATUS_T_MINUS_1
            elif base.startswith("cross_"):
                category = "cross_market_index"
                status = STATUS_PROXY_DAILY
            elif base.startswith("tgb_"):
                category = "tgb"
                status = STATUS_PROXY_DAILY
            elif base.startswith("sector_"):
                category = "ths_sector"
                status = STATUS_T_MINUS_1
            else:
                category = "market_emotion_board"
                status = STATUS_PROXY_DAILY
        else:
            # Per-symbol OHLCV-derived features use T-day daily bar → proxy
            category = "symbol_ohlcv"
            status = STATUS_PROXY_DAILY

        classification[name] = {
            "index": i,
            "category": category,
            "status": status,
            "selected": is_selected,
        }
    return classification


def get_unavailable_features(classification: dict[str, dict[str, Any]]) -> list[str]:
    """Features that require post-close data and must use fallback."""
    return [
        name for name, info in classification.items()
        if info["status"] == STATUS_POST_CLOSE
    ]


def apply_fallback_nan(
    data: pd.DataFrame,
    unavailable_cols: list[str],
    feature_names: tuple,
) -> pd.DataFrame:
    """NaN missing: set value to NaN and _available flag to 0."""
    out = data.copy()
    available_flag_map = {name: f"{name}_available" for name in feature_names}
    for col in unavailable_cols:
        if col in out.columns:
            out[col] = np.nan
        # If this feature has a companion _available flag, set it to 0
        avail_col = available_flag_map.get(col)
        if avail_col and avail_col in out.columns:
            out[avail_col] = 0.0
        # If this IS an _available flag for an unavailable feature, set to 0
        if col.endswith("_available") and col in out.columns:
            out[col] = 0.0
    return out


def apply_fallback_mean(
    data: pd.DataFrame,
    unavailable_cols: list[str],
    bundle_mean: np.ndarray,
    feature_names: tuple,
) -> pd.DataFrame:
    """Neutral mean: set value to bundle mean (→0 after normalization), _available flag = 0."""
    out = data.copy()
    mean_dict = {feature_names[i]: float(bundle_mean[0, i]) for i in range(len(feature_names))}
    available_flag_map = {name: f"{name}_available" for name in feature_names}
    for col in unavailable_cols:
        if col in out.columns:
            if col.endswith("_available"):
                out[col] = 0.0
            elif col in mean_dict:
                out[col] = mean_dict[col]
        avail_col = available_flag_map.get(col)
        if avail_col and avail_col in out.columns:
            out[avail_col] = 0.0
    return out


def run_inference(data: pd.DataFrame, bundle: dict[str, Any]) -> np.ndarray:
    feature_names = bundle["feature_names"]
    mean = bundle["mean"].numpy()
    std = bundle["std"].numpy()
    selected_indices = bundle["selected_indices"].numpy()
    iso_model = pickle.loads(bundle["iso_model_bytes"])

    feature_matrix = np.zeros((len(data), len(feature_names)), dtype=np.float32)
    for i, name in enumerate(feature_names):
        if name in data.columns:
            vals = pd.to_numeric(data[name], errors="coerce").values.astype(np.float32)
            feature_matrix[:, i] = vals

    std_safe = std.copy()
    std_safe[std_safe < 1e-8] = 1.0
    normalized = (feature_matrix - mean) / std_safe
    selected = normalized[:, selected_indices]

    probs = np.zeros(len(data), dtype=np.float64)
    for member in bundle["members"]:
        model = pickle.loads(member["model_bytes"])
        pred = model.predict_proba(selected)[:, 1]
        probs += pred
    probs /= len(bundle["members"])

    return iso_model.predict(probs)


def load_replay_candidates(target_date: date) -> pd.DataFrame | None:
    csv_path = DESKTOP / f"saved_bundle_candidates_{target_date.strftime('%Y%m%d')}.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        df["symbol"] = df["symbol"].astype(str).str.zfill(6)
        return df
    return None


def compare_results(
    dryrun_probs: np.ndarray,
    dryrun_symbols: pd.Series,
    replay_candidates: pd.DataFrame | None,
    threshold: float,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    dryrun_df = pd.DataFrame({
        "symbol": dryrun_symbols.astype(str).str.zfill(6).values,
        "probability": dryrun_probs,
    })
    dryrun_above = dryrun_df[dryrun_df["probability"] >= threshold]
    metrics["dryrun_total_stocks"] = len(dryrun_df)
    metrics["dryrun_above_threshold"] = len(dryrun_above)
    metrics["dryrun_top1_prob"] = float(dryrun_df["probability"].max()) if len(dryrun_df) > 0 else 0.0
    metrics["dryrun_mean_prob"] = float(dryrun_df["probability"].mean()) if len(dryrun_df) > 0 else 0.0

    if replay_candidates is None or "symbol" not in replay_candidates.columns:
        return metrics

    # Universe comparison (only on intersection)
    dryrun_universe = set(dryrun_df["symbol"])
    replay_universe = set(replay_candidates["symbol"])
    intersection = dryrun_universe & replay_universe
    metrics["universe_dryrun"] = len(dryrun_universe)
    metrics["universe_replay"] = len(replay_universe)
    metrics["universe_intersection"] = len(intersection)
    metrics["universe_missing_in_dryrun"] = len(replay_universe - dryrun_universe)

    if not intersection:
        return metrics

    # Compare only on intersection
    dryrun_inter = dryrun_df[dryrun_df["symbol"].isin(intersection)]
    replay_inter = replay_candidates[replay_candidates["symbol"].isin(intersection)]
    merged = dryrun_inter.merge(
        replay_inter[["symbol", "probability"]],
        on="symbol",
        suffixes=("_dryrun", "_replay"),
    )
    if merged.empty:
        return metrics

    diff = (merged["probability_dryrun"] - merged["probability_replay"]).abs()
    metrics["matched_rows"] = len(merged)
    metrics["max_abs_diff"] = float(diff.max())
    metrics["mean_abs_diff"] = float(diff.mean())
    metrics["median_abs_diff"] = float(diff.median())

    # Threshold overlap (on intersection only)
    replay_above = set(replay_inter[replay_inter["probability"] >= threshold]["symbol"])
    dryrun_above_set = set(dryrun_inter[dryrun_inter["probability"] >= threshold]["symbol"])
    inter_above = replay_above & dryrun_above_set
    union_above = replay_above | dryrun_above_set
    metrics["threshold_overlap_jaccard"] = len(inter_above) / max(len(union_above), 1)
    metrics["threshold_overlap_recall"] = len(inter_above) / max(len(replay_above), 1)
    metrics["replay_above_threshold_in_intersection"] = len(replay_above)
    metrics["dryrun_above_threshold_in_intersection"] = len(dryrun_above_set)

    # TopK overlap (on intersection)
    for k in (10, 20, 30, 50):
        replay_topk = set(replay_inter.nlargest(k, "probability")["symbol"])
        dryrun_topk = set(dryrun_inter.nlargest(k, "probability")["symbol"])
        metrics[f"top{k}_overlap"] = len(replay_topk & dryrun_topk) / k

    # High-confidence overlap
    for t in (0.75, 0.80):
        replay_t = set(replay_inter[replay_inter["probability"] >= t]["symbol"])
        dryrun_t = set(dryrun_inter[dryrun_inter["probability"] >= t]["symbol"])
        tag = f"t{t:.2f}"
        metrics[f"{tag}_replay_count"] = len(replay_t)
        metrics[f"{tag}_dryrun_count"] = len(dryrun_t)
        inter_t = replay_t & dryrun_t
        metrics[f"{tag}_overlap"] = len(inter_t) / max(len(replay_t), 1)
        metrics[f"{tag}_jaccard"] = len(inter_t) / max(len(replay_t | dryrun_t), 1)

    return metrics


def generate_candidates_csv(
    data: pd.DataFrame,
    probs: np.ndarray,
    threshold: float,
    target_date: date,
    mode: str,
    output_path: Path,
) -> int:
    name_cache_path = SUBAGENT_ROOT / "scripts" / "_symbol_name_cache.json"
    name_map: dict[str, str] = {}
    if name_cache_path.exists():
        name_map = json.loads(name_cache_path.read_text(encoding="utf-8"))

    df = pd.DataFrame({
        "symbol": data["symbol"].astype(str).str.zfill(6).values,
        "probability": probs,
    })
    if "close" in data.columns:
        df["close"] = data["close"].values
    if "turnover" in data.columns:
        df["turnover"] = data["turnover"].values
    if "limit_up_like" in data.columns:
        df["limit_up_like"] = data["limit_up_like"].values

    df = df.sort_values("probability", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    df.insert(2, "name", df["symbol"].map(name_map).fillna(""))
    df["date"] = target_date.isoformat()
    df["entry_date"] = target_date.isoformat()
    label_date = target_date + timedelta(days=1)
    while label_date.weekday() >= 5:
        label_date += timedelta(days=1)
    df["label_date"] = label_date.isoformat()
    df["threshold"] = threshold
    df["mode"] = mode

    cols = ["rank", "symbol", "name", "date", "entry_date", "label_date",
            "probability", "threshold"]
    for extra in ("close", "turnover", "limit_up_like"):
        if extra in df.columns:
            cols.append(extra)
    cols.append("mode")
    df = df[cols]

    above = df[df["probability"] >= threshold]
    above.to_csv(output_path, index=False, float_format="%.6f")
    return len(above)


def minute_bar_coverage_report(target_date: date) -> dict[str, Any]:
    minute_dir = RUNTIME_ROOT / "raw" / "bars" / "5"
    report: dict[str, Any] = {"minute_bar_dir": str(minute_dir)}
    if not minute_dir.is_dir():
        report["status"] = "directory_not_found"
        return report
    files = list(minute_dir.glob("*.parquet"))
    report["total_files"] = len(files)
    has_target = 0
    latest_dates: list[str] = []
    for f in files[:20]:
        try:
            df = pd.read_parquet(f, columns=["date"])
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            max_d = df["date"].max()
            if max_d is not pd.NaT:
                latest_dates.append(str(max_d.date()))
            if (df["date"].dt.date == target_date).any():
                has_target += 1
        except Exception:
            pass
    report["target_date"] = target_date.isoformat()
    report["files_with_target_date"] = has_target
    report["sample_latest_dates"] = sorted(set(latest_dates))[:5]
    report["status"] = "available" if has_target > 0 else "not_available_for_target"
    return report


def main():
    parser = argparse.ArgumentParser(description="14:57 Realtime Dry-Run")
    parser.add_argument("--target-date", type=str, default="2026-04-29")
    parser.add_argument("--bundle-path", type=str, default=str(BUNDLE_PATH))
    args = parser.parse_args()

    target_date = date.fromisoformat(args.target_date)
    bundle_path = Path(args.bundle_path)

    print(f"[1457-dry-run] target_date={target_date} bundle={bundle_path.name}",
          file=sys.stderr, flush=True)

    timings: dict[str, float] = {}

    # --- Step 1: Load bundle ---
    t0 = time.perf_counter()
    bundle = load_bundle(bundle_path)
    timings["bundle_load"] = time.perf_counter() - t0
    feature_names = bundle["feature_names"]
    threshold = float(bundle["threshold"])
    n_selected = len(bundle["selected_indices"])
    print(f"[1457-dry-run] bundle: {len(feature_names)} features, "
          f"{n_selected} selected, threshold={threshold:.4f}",
          file=sys.stderr, flush=True)

    # --- Step 2: Feature classification ---
    classification = classify_features(bundle)
    unavailable_features = get_unavailable_features(classification)
    selected_unavailable = [n for n in unavailable_features if classification[n]["selected"]]

    # Status summary for selected features
    selected_status: dict[str, int] = {}
    for info in classification.values():
        if info["selected"]:
            s = info["status"]
            selected_status[s] = selected_status.get(s, 0) + 1

    print(f"[1457-dry-run] selected feature status: {selected_status}",
          file=sys.stderr, flush=True)
    print(f"[1457-dry-run] post_close (fallback needed): "
          f"{len(unavailable_features)}/{len(feature_names)} total, "
          f"{len(selected_unavailable)}/{n_selected} selected",
          file=sys.stderr, flush=True)

    # --- Step 3: Load bars ---
    t0 = time.perf_counter()
    symbols = discover_symbols()
    config = build_config(target_date)
    all_bars = load_daily_bars(symbols, config.start, config.end)
    timings["load_bars"] = time.perf_counter() - t0
    print(f"[1457-dry-run] loaded {len(all_bars)} stocks ({timings['load_bars']:.1f}s)",
          file=sys.stderr, flush=True)

    # --- Step 4: Build per-symbol features ---
    data, context_frames, sym_timing = build_symbol_features(all_bars, config, target_date)
    timings.update(sym_timing)
    if data.empty:
        print(f"FATAL: no features produced for {target_date}",
              file=sys.stderr, flush=True)
        sys.exit(1)
    print(f"[1457-dry-run] symbol features: {len(data)} stocks "
          f"({timings['symbol_features_sec']:.1f}s)",
          file=sys.stderr, flush=True)

    # --- Step 5: Free factors (market emotion + board structure) ---
    data, t_free = attach_free_factors(data, context_frames)
    timings["free_factors"] = t_free

    # --- Step 6: Market index ---
    data, t_idx = attach_market_index(data, config)
    timings["market_index"] = t_idx

    # --- Step 7: TGB ---
    data, t_tgb = attach_tgb(data, context_frames)
    timings["tgb_factors"] = t_tgb

    # --- Step 8: THS sector ---
    data, t_ths = attach_ths_sector(data)
    timings["ths_sector"] = t_ths

    # --- Step 9: Limit pool ---
    data, t_lp, lp_status = attach_limit_pool(data)
    timings["limit_pool"] = t_lp

    # --- Step 10: Cross-section ---
    data, t_cs = attach_cross_section(data)
    timings["cross_section"] = t_cs

    # --- Step 11: Ensure columns ---
    t0 = time.perf_counter()
    data = _ensure_feature_columns(data)
    timings["ensure_columns"] = time.perf_counter() - t0

    print(f"[1457-dry-run] feature frame: {data.shape[0]} rows x {data.shape[1]} cols "
          f"| limit_pool={lp_status}", file=sys.stderr, flush=True)

    # --- Step 12: Inference ---
    t0 = time.perf_counter()
    data_nan = apply_fallback_nan(data, unavailable_features, feature_names)
    probs_nan = run_inference(data_nan, bundle)
    timings["inference_nan"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    data_mean = apply_fallback_mean(
        data, unavailable_features, bundle["mean"].numpy(), feature_names
    )
    probs_mean = run_inference(data_mean, bundle)
    timings["inference_mean"] = time.perf_counter() - t0

    print(f"[1457-dry-run] inference: nan top1={probs_nan.max():.4f}, "
          f"mean top1={probs_mean.max():.4f}", file=sys.stderr, flush=True)

    # --- Step 13: Compare ---
    replay = load_replay_candidates(target_date)
    metrics_nan = compare_results(probs_nan, data["symbol"], replay, threshold)
    metrics_mean = compare_results(probs_mean, data["symbol"], replay, threshold)

    # --- Step 14: Candidate CSVs ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_nan_path = DESKTOP / f"realtime_1457_candidates_{target_date.strftime('%Y%m%d')}_nan_missing.csv"
    csv_mean_path = DESKTOP / f"realtime_1457_candidates_{target_date.strftime('%Y%m%d')}_neutral_mean.csv"
    n_nan = generate_candidates_csv(data, probs_nan, threshold, target_date, "nan_missing", csv_nan_path)
    n_mean = generate_candidates_csv(data, probs_mean, threshold, target_date, "neutral_mean", csv_mean_path)

    # --- Step 15: Feature parquet ---
    feature_parquet_path = OUTPUT_DIR / f"features_{target_date.strftime('%Y%m%d')}_1457.parquet"
    meta_cols = [c for c in ("symbol", "date", "close", "turnover") if c in data.columns]
    save_cols = [c for c in feature_names if c in data.columns and c not in meta_cols]
    all_save = meta_cols + save_cols
    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for c in all_save:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    data[deduped].to_parquet(feature_parquet_path, index=False)

    # --- Step 16: Minute bar coverage ---
    minute_report = minute_bar_coverage_report(target_date)

    # --- Step 17: Category summary ---
    category_counts: dict[str, dict[str, int]] = {}
    for info in classification.values():
        cat = info["category"]
        if cat not in category_counts:
            category_counts[cat] = {
                "total": 0, "selected": 0,
                STATUS_STRICT_1457: 0, STATUS_PROXY_DAILY: 0,
                STATUS_T_MINUS_1: 0, STATUS_POST_CLOSE: 0,
            }
        category_counts[cat]["total"] += 1
        if info["selected"]:
            category_counts[cat]["selected"] += 1
        category_counts[cat][info["status"]] += 1

    # --- Step 18: Results JSON ---
    total_time = sum(timings.values())
    results = {
        "target_date": target_date.isoformat(),
        "mode": "daily_proxy",
        "mode_explanation": (
            "Uses T-day daily bar as 14:57 proxy. NOT strict 14:57 — "
            "daily close includes call auction (14:57-15:00). "
            "True strict_1457 requires 5-min bars for target date."
        ),
        "bundle": bundle_path.name,
        "total_features": len(feature_names),
        "selected_features": n_selected,
        "threshold": threshold,
        "stocks_processed": len(data),
        "selected_feature_status": selected_status,
        "post_close_unavailable_total": len(unavailable_features),
        "post_close_unavailable_selected": len(selected_unavailable),
        "post_close_feature_names": unavailable_features,
        "limit_pool_status": lp_status,
        "timings": timings,
        "total_time_sec": total_time,
        "metrics_nan_missing": metrics_nan,
        "metrics_neutral_mean": metrics_mean,
        "nan_missing_above_threshold": n_nan,
        "neutral_mean_above_threshold": n_mean,
        "category_summary": category_counts,
        "minute_bar_report": minute_report,
        "strict_1457_possible": False,
        "strict_1457_blocker": "No 5-min bars for 2026-04-29 (latest: 2026-04-28)",
        "output_files": {
            "csv_nan": str(csv_nan_path),
            "csv_mean": str(csv_mean_path),
            "feature_parquet": str(feature_parquet_path),
        },
    }

    json_path = OUTPUT_DIR / f"realtime_1457_dry_run_validation_{datetime.now().strftime('%Y%m%d')}.json"
    json_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    # --- Print summary ---
    print("\n" + "=" * 70, file=sys.stderr, flush=True)
    print("14:57 REALTIME DRY-RUN — DAILY PROXY MODE", file=sys.stderr, flush=True)
    print("=" * 70, file=sys.stderr, flush=True)
    print(f"Target: {target_date} | Stocks: {len(data)} | Time: {total_time:.1f}s",
          file=sys.stderr, flush=True)
    print(f"Features: {len(feature_names)} total, {n_selected} selected",
          file=sys.stderr, flush=True)
    print(f"\nSelected feature availability:", file=sys.stderr, flush=True)
    for s, c in sorted(selected_status.items()):
        print(f"  {s}: {c}", file=sys.stderr, flush=True)
    print(f"\n--- nan_missing ---", file=sys.stderr, flush=True)
    print(f"  Above threshold: {n_nan}", file=sys.stderr, flush=True)
    print(f"  Top-1: {probs_nan.max():.4f}", file=sys.stderr, flush=True)
    if "max_abs_diff" in metrics_nan:
        print(f"  vs replay (intersection): max_diff={metrics_nan['max_abs_diff']:.6f} "
              f"mean_diff={metrics_nan['mean_abs_diff']:.6f}",
              file=sys.stderr, flush=True)
    if "top30_overlap" in metrics_nan:
        print(f"  Top30 overlap: {metrics_nan['top30_overlap']:.1%}",
              file=sys.stderr, flush=True)
    if "threshold_overlap_jaccard" in metrics_nan:
        print(f"  Threshold Jaccard: {metrics_nan['threshold_overlap_jaccard']:.1%}",
              file=sys.stderr, flush=True)
    print(f"\n--- neutral_mean ---", file=sys.stderr, flush=True)
    print(f"  Above threshold: {n_mean}", file=sys.stderr, flush=True)
    print(f"  Top-1: {probs_mean.max():.4f}", file=sys.stderr, flush=True)
    if "max_abs_diff" in metrics_mean:
        print(f"  vs replay (intersection): max_diff={metrics_mean['max_abs_diff']:.6f} "
              f"mean_diff={metrics_mean['mean_abs_diff']:.6f}",
              file=sys.stderr, flush=True)
    if "top30_overlap" in metrics_mean:
        print(f"  Top30 overlap: {metrics_mean['top30_overlap']:.1%}",
              file=sys.stderr, flush=True)
    if "threshold_overlap_jaccard" in metrics_mean:
        print(f"  Threshold Jaccard: {metrics_mean['threshold_overlap_jaccard']:.1%}",
              file=sys.stderr, flush=True)
    if "universe_intersection" in metrics_nan:
        print(f"\n--- Universe ---", file=sys.stderr, flush=True)
        print(f"  Dry-run: {metrics_nan['universe_dryrun']}",
              file=sys.stderr, flush=True)
        print(f"  Replay: {metrics_nan['universe_replay']}",
              file=sys.stderr, flush=True)
        print(f"  Intersection: {metrics_nan['universe_intersection']}",
              file=sys.stderr, flush=True)
        print(f"  Missing from dry-run: {metrics_nan['universe_missing_in_dryrun']}",
              file=sys.stderr, flush=True)
    print(f"\n--- Timing ---", file=sys.stderr, flush=True)
    for k, v in sorted(timings.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v:.2f}s", file=sys.stderr, flush=True)
    print(f"\n--- Strict 14:57 Status ---", file=sys.stderr, flush=True)
    print(f"  Possible: NO", file=sys.stderr, flush=True)
    print(f"  Blocker: No 5-min bars for {target_date}", file=sys.stderr, flush=True)
    print(f"  This run is daily_proxy only (T-day close used as 14:57 approximation)",
          file=sys.stderr, flush=True)
    print(f"\nOutputs:", file=sys.stderr, flush=True)
    print(f"  JSON: {json_path}", file=sys.stderr, flush=True)
    print(f"  CSV (nan): {csv_nan_path}", file=sys.stderr, flush=True)
    print(f"  CSV (mean): {csv_mean_path}", file=sys.stderr, flush=True)
    print(f"  Features: {feature_parquet_path}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
