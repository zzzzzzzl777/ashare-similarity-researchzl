"""PhaseC production-oriented strategy search.

This script re-scores the PhaseC bundle from feature caches, then searches
fixed daily selection policies. It avoids using prior candidate display files as
the source of truth.
"""

from __future__ import annotations

import json
import math
import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch


BUNDLE_PATH = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt"
)

CACHE_SOURCES = [
    {
        "path": Path(
            r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
            r"\gpu_probe_features_550a77f54882058f.parquet"
        ),
        "name": "broad_cache_until_202603",
        "filters": [("date", ">=", pd.Timestamp("2023-01-01")), ("date", "<", pd.Timestamp("2026-04-01"))],
    },
    {
        "path": Path(
            r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
            r"\gpu_probe_features_10c11fc874db003c.parquet"
        ),
        "name": "latest_cache_202604_202605",
        "filters": [("date", ">=", pd.Timestamp("2026-04-01")), ("date", "<=", pd.Timestamp("2026-05-31"))],
    },
]

OUT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
OUT_JSON = OUT_DIR / "phasec_strategy_search_20260519.json"
OUT_CSV = OUT_DIR / "phasec_strategy_search_top_20260519.csv"


META_COLS = [
    "date",
    "label_date",
    "symbol",
    "name",
    "actual",
    "next_high_return_pct",
    "next_close_return_pct",
    "next_low_return_pct",
]

SAFE_STRATEGY_COLS = [
    "close",
    "turnover",
    "turnover_z_20",
    "turnover_mean_3",
    "turnover_mean_5",
    "volume_z_5",
    "volume_z_10",
    "volume_z_20",
    "amount_z_20",
    "range_pct",
    "body_pct",
    "lower_shadow_pct",
    "upper_shadow_pct",
    "close_position",
    "gap_pct",
    "overnight_return",
    "intraday_return",
    "ret_1",
    "ret_3",
    "ret_5",
    "rsi_6",
    "rsi_14",
    "ma_gap_5",
    "ma_gap_10",
    "ma_gap_20",
    "atr_14_pct",
    "up_count_3",
    "up_count_5",
    "down_count_3",
    "down_count_5",
    "limit_up_like",
    "short_phase_days_3",
]

SECTOR_PROXY_COLS = [
    "sector_strength_rank",
    "sector_limit_up_count",
    "sector_duration_days",
    "sector_pct_change_best",
    "sector_divergence",
    "sector_climax_signal",
]

P0_MONEY_COLS = [
    "tushare_net_mf_amount",
    "tushare_mf_strength",
    "tushare_mf_flow_intensity",
    "tushare_ff_adjusted_flow",
]


@dataclass(frozen=True)
class Recipe:
    name: str
    uses_sector: bool = False


RECIPES = [
    Recipe("prob_desc"),
    Recipe("prob_then_rsi6_low"),
    Recipe("prob_then_turnover_high"),
    Recipe("prob_then_volume_high"),
    Recipe("prob_then_amount_high"),
    Recipe("rsi6_low"),
    Recipe("turnover_high"),
    Recipe("volume_z_high"),
    Recipe("amount_z_high"),
    Recipe("activity_z_high"),
    Recipe("prob_x_activity"),
    Recipe("low_price_prob"),
    Recipe("sector_strength", uses_sector=True),
    Recipe("sector_hot", uses_sector=True),
]


def parquet_columns(path: Path) -> list[str]:
    return list(pq.ParquetFile(path).schema.names)


def read_cache_source(source: dict, feature_names: list[str]) -> pd.DataFrame:
    path = source["path"]
    if not path.exists():
        raise FileNotFoundError(path)
    available = set(parquet_columns(path))
    wanted = []
    for col in META_COLS + SAFE_STRATEGY_COLS + SECTOR_PROXY_COLS + P0_MONEY_COLS + feature_names:
        if col in available and col not in wanted:
            wanted.append(col)
    print(f"Reading {source['name']} from {path.name}: {len(wanted)} cols", flush=True)
    df = pd.read_parquet(path, columns=wanted, filters=source["filters"])
    df["cache_source"] = source["name"]
    return df


def load_bundle(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    bundle = torch.load(path, map_location="cpu", weights_only=False)
    print(
        "Loaded bundle:",
        bundle.get("model_name"),
        bundle.get("model_kind"),
        "features",
        len(bundle.get("feature_names", [])),
        "selected",
        len(bundle.get("selected_feature_names", [])),
        "cal",
        bundle.get("calibration_used"),
        flush=True,
    )
    return bundle


def score_phasec(df: pd.DataFrame, bundle: dict) -> pd.DataFrame:
    feature_names = list(bundle["feature_names"])
    missing = [c for c in feature_names if c not in df.columns]
    if missing:
        print(f"Filling {len(missing)} missing bundle features with 0. First missing: {missing[:8]}", flush=True)
        for col in missing:
            df[col] = 0.0

    print(f"Scoring {len(df):,} rows with PhaseC bundle...", flush=True)
    t0 = time.time()
    x = (
        df[feature_names]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
        .to_numpy(dtype=np.float32, copy=True)
    )
    mean = bundle.get("mean")
    std = bundle.get("std")
    if mean is not None:
        mean_arr = np.asarray(mean, dtype=np.float32)
        std_arr = np.asarray(std, dtype=np.float32)
        x = (x - mean_arr) / np.where(std_arr == 0, 1.0, std_arr)

    selected_indices = bundle.get("selected_indices")
    if selected_indices is not None:
        if hasattr(selected_indices, "detach"):
            selected_indices = selected_indices.detach().cpu().numpy().astype(int)
        x = x[:, selected_indices]

    member = bundle["members"][0]
    model = pickle.loads(member["model_bytes"])
    raw = model.predict_proba(x)[:, 1].astype(np.float64)
    df["raw_prob"] = raw

    iso_bytes = bundle.get("iso_model_bytes")
    if iso_bytes:
        iso_model = pickle.loads(iso_bytes)
        df["iso_prob"] = iso_model.predict(raw).astype(np.float64)
    else:
        df["iso_prob"] = raw

    print(f"Scored in {time.time() - t0:.1f}s", flush=True)
    return df


def prepare_pool(bundle: dict) -> pd.DataFrame:
    feature_names = list(bundle["feature_names"])
    parts = [read_cache_source(source, feature_names) for source in CACHE_SOURCES]
    df = pd.concat(parts, ignore_index=True, sort=False)
    df["date"] = pd.to_datetime(df["date"])
    df["label_date"] = pd.to_datetime(df["label_date"], errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    df = df.sort_values(["date", "symbol", "cache_source"]).drop_duplicates(["date", "symbol"], keep="last")
    df = df[(df["date"] >= pd.Timestamp("2023-01-01")) & (df["date"] <= pd.Timestamp("2026-05-31"))].copy()
    df = score_phasec(df, bundle)

    for col in SAFE_STRATEGY_COLS + SECTOR_PROXY_COLS + P0_MONEY_COLS:
        if col not in df.columns:
            df[col] = np.nan
    for col in [
        "actual",
        "next_high_return_pct",
        "next_close_return_pct",
        "next_low_return_pct",
        "close",
        "turnover",
        "turnover_z_20",
        "volume_z_20",
        "amount_z_20",
        "rsi_6",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["actual", "next_high_return_pct", "next_close_return_pct", "next_low_return_pct"]).copy()
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["date_key"] = df["date"].dt.strftime("%Y-%m-%d")
    df["actual"] = (df["actual"].astype(float) > 0.5).astype(float)
    print(
        f"Prepared pool: {len(df):,}/{before:,} rows, "
        f"{df['date_key'].nunique()} days, {df['date'].min().date()}..{df['date'].max().date()}",
        flush=True,
    )
    return df.reset_index(drop=True)


def finite(values: pd.Series | np.ndarray, fill: float = 0.0) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    arr = np.where(np.isfinite(arr), arr, fill)
    return arr


def z_clip(arr: np.ndarray, lo: float = -3.0, hi: float = 3.0) -> np.ndarray:
    return np.clip(finite(arr), lo, hi)


def build_filters(df: pd.DataFrame) -> list[tuple[str, str, np.ndarray]]:
    n = len(df)
    specs: list[tuple[str, str, np.ndarray]] = [("none", "safe", np.ones(n, dtype=bool))]

    close = finite(df["close"])
    turnover = finite(df["turnover"])
    vz = finite(df["volume_z_20"])
    az = finite(df["amount_z_20"])
    rsi6 = finite(df["rsi_6"], fill=50.0)
    rng = finite(df["range_pct"])
    sec_rank = finite(df["sector_strength_rank"], fill=999.0)
    sec_lu = finite(df["sector_limit_up_count"])
    sec_days = finite(df["sector_duration_days"])

    safe_specs = [
        ("turnover>=3", turnover >= 3),
        ("turnover>=5", turnover >= 5),
        ("turnover>=8", turnover >= 8),
        ("turnover_3_20", (turnover >= 3) & (turnover <= 20)),
        ("turnover_5_20", (turnover >= 5) & (turnover <= 20)),
        ("turnover_5_30", (turnover >= 5) & (turnover <= 30)),
        ("close_3_60", (close >= 3) & (close <= 60)),
        ("close_5_60", (close >= 5) & (close <= 60)),
        ("close_5_100", (close >= 5) & (close <= 100)),
        ("volume_z>=0", vz >= 0),
        ("volume_z>=0.5", vz >= 0.5),
        ("amount_z>=0", az >= 0),
        ("amount_z>=0.5", az >= 0.5),
        ("rsi6<=45", rsi6 <= 45),
        ("rsi6<=55", rsi6 <= 55),
        ("range>=2", rng >= 2),
        ("t5_20_close5_80", (turnover >= 5) & (turnover <= 20) & (close >= 5) & (close <= 80)),
        ("t5_30_vz0", (turnover >= 5) & (turnover <= 30) & (vz >= 0)),
        ("t5_30_az0", (turnover >= 5) & (turnover <= 30) & (az >= 0)),
        ("t5_30_rsi55", (turnover >= 5) & (turnover <= 30) & (rsi6 <= 55)),
    ]
    for name, mask in safe_specs:
        specs.append((name, "safe", mask.astype(bool)))

    sector_specs = [
        ("sector_rank<=50", sec_rank <= 50),
        ("sector_rank<=100", sec_rank <= 100),
        ("sector_lu>=1", sec_lu >= 1),
        ("sector_days>=2", sec_days >= 2),
        ("t5_sector_rank<=100", (turnover >= 5) & (sec_rank <= 100)),
        ("t5_sector_lu>=1", (turnover >= 5) & (sec_lu >= 1)),
    ]
    for name, mask in sector_specs:
        specs.append((name, "sector_proxy", mask.astype(bool)))

    return specs


def recipe_values(df: pd.DataFrame, score_col: str, recipe: Recipe) -> tuple[np.ndarray, np.ndarray | None, bool]:
    score = finite(df[score_col])
    rsi6 = finite(df["rsi_6"], fill=50.0)
    turnover = finite(df["turnover"])
    vz = z_clip(df["volume_z_20"])
    az = z_clip(df["amount_z_20"])
    close = finite(df["close"])
    activity = vz + az
    sec_rank = finite(df["sector_strength_rank"], fill=999.0)
    sec_lu = finite(df["sector_limit_up_count"])

    if recipe.name == "prob_desc":
        return score, None, False
    if recipe.name == "prob_then_rsi6_low":
        return score, rsi6, True
    if recipe.name == "prob_then_turnover_high":
        return score, turnover, False
    if recipe.name == "prob_then_volume_high":
        return score, vz, False
    if recipe.name == "prob_then_amount_high":
        return score, az, False
    if recipe.name == "rsi6_low":
        return -rsi6, score, False
    if recipe.name == "turnover_high":
        return turnover, score, False
    if recipe.name == "volume_z_high":
        return vz, score, False
    if recipe.name == "amount_z_high":
        return az, score, False
    if recipe.name == "activity_z_high":
        return activity, score, False
    if recipe.name == "prob_x_activity":
        return score * (1.0 + 0.12 * activity), score, False
    if recipe.name == "low_price_prob":
        return score, close, True
    if recipe.name == "sector_strength":
        return -sec_rank, score, False
    if recipe.name == "sector_hot":
        return sec_lu, score, False
    raise ValueError(recipe.name)


def compute_exits(df: pd.DataFrame) -> dict[str, np.ndarray]:
    close_ret = finite(df["next_close_return_pct"])
    high_ret = finite(df["next_high_return_pct"])
    low_ret = finite(df["next_low_return_pct"])
    exits = {"close": close_ret}
    for tp in [2, 3, 5, 7, 10]:
        exits[f"tp{tp}"] = np.where(high_ret >= tp, float(tp), close_ret)
    for sl in [1, 2, 3, 5]:
        exits[f"sl{sl}"] = np.where(low_ret <= -sl, -float(sl), close_ret)
    for sl, tp in [(1, 3), (2, 5), (3, 7), (3, 10), (5, 10)]:
        name = f"sl{sl}_tp{tp}_conservative"
        exits[name] = np.where(
            low_ret <= -sl,
            -float(sl),
            np.where(high_ret >= tp, float(tp), close_ret),
        )
    return exits


def pct_prod(arr: Iterable[float]) -> float:
    vals = np.asarray(list(arr), dtype=np.float64)
    if len(vals) == 0:
        return 0.0
    vals = np.clip(vals / 100.0, -0.95, 5.0)
    return float((np.prod(1.0 + vals) - 1.0) * 100.0)


def sharpe_like(arr: np.ndarray) -> float:
    if len(arr) < 3:
        return 0.0
    std = float(np.std(arr, ddof=1))
    if std <= 1e-12:
        return 0.0
    return float(np.mean(arr) / std * math.sqrt(252))


def make_groups(date_codes: np.ndarray) -> list[np.ndarray]:
    groups = []
    for code in np.unique(date_codes):
        groups.append(np.where(date_codes == code)[0])
    return groups


def daily_top_indices(
    groups: list[np.ndarray],
    mask: np.ndarray,
    primary: np.ndarray,
    secondary: np.ndarray | None,
    secondary_ascending: bool,
    max_top: int = 6,
) -> tuple[np.ndarray, np.ndarray]:
    top_idx: list[int] = []
    top_rank: list[int] = []
    for idx in groups:
        valid = idx[mask[idx]]
        if len(valid) == 0:
            continue
        if secondary is None:
            order = np.argsort(-primary[valid], kind="mergesort")
        else:
            sec_key = secondary[valid] if secondary_ascending else -secondary[valid]
            order = np.lexsort((sec_key, -primary[valid]))
        chosen = valid[order[:max_top]]
        top_idx.extend(chosen.tolist())
        top_rank.extend(range(1, len(chosen) + 1))
    return np.asarray(top_idx, dtype=np.int64), np.asarray(top_rank, dtype=np.int16)


def daily_top_matrix(
    groups: list[np.ndarray],
    mask: np.ndarray,
    primary: np.ndarray,
    secondary: np.ndarray | None,
    secondary_ascending: bool,
    max_top: int = 6,
) -> np.ndarray:
    top = np.full((len(groups), max_top), -1, dtype=np.int64)
    for group_index, idx in enumerate(groups):
        valid = idx[mask[idx]]
        if len(valid) == 0:
            continue
        if secondary is None:
            order = np.argsort(-primary[valid], kind="mergesort")
        else:
            sec_key = secondary[valid] if secondary_ascending else -secondary[valid]
            order = np.lexsort((sec_key, -primary[valid]))
        chosen = valid[order[:max_top]]
        top[group_index, : len(chosen)] = chosen
    return top


def period_name(date: pd.Timestamp) -> str:
    if date < pd.Timestamp("2026-01-01"):
        return "search_2023_2025"
    if date < pd.Timestamp("2026-04-01"):
        return "q1_2026"
    if date < pd.Timestamp("2026-05-01"):
        return "apr_2026"
    return "may_2026_partial"


def evaluate_selection(
    selected_idx: np.ndarray,
    exit_values: np.ndarray,
    actual: np.ndarray,
    date_keys: np.ndarray,
    month_keys: np.ndarray,
    period_keys: np.ndarray,
) -> dict | None:
    if len(selected_idx) == 0:
        return None

    sel_dates = date_keys[selected_idx]
    sel_months = month_keys[selected_idx]
    sel_periods = period_keys[selected_idx]
    sel_returns = exit_values[selected_idx]
    sel_actual = actual[selected_idx]

    unique_dates = np.unique(sel_dates)
    if len(unique_dates) < 8:
        return None

    daily_returns = []
    daily_dates = []
    daily_months = []
    daily_periods = []
    for d in unique_dates:
        dm = sel_dates == d
        day_ret = float(np.mean(sel_returns[dm]))
        daily_returns.append(day_ret)
        daily_dates.append(d)
        daily_months.append(sel_months[dm][0])
        daily_periods.append(sel_periods[dm][0])

    daily_returns_np = np.asarray(daily_returns, dtype=np.float64)
    daily_months_np = np.asarray(daily_months)
    daily_periods_np = np.asarray(daily_periods)

    months = []
    for m in sorted(np.unique(daily_months_np)):
        dm = daily_months_np == m
        ticket_mask = sel_months == m
        months.append(
            {
                "month": str(m),
                "signal_days": int(dm.sum()),
                "tickets": int(ticket_mask.sum()),
                "return_pct": pct_prod(daily_returns_np[dm]),
                "avg_daily_return_pct": float(np.mean(daily_returns_np[dm])),
                "daily_win_rate": float(np.mean(daily_returns_np[dm] > 0)),
                "high1_hit_rate": float(np.mean(sel_actual[ticket_mask])) if ticket_mask.any() else 0.0,
            }
        )

    periods = {}
    for p in ["search_2023_2025", "q1_2026", "apr_2026", "may_2026_partial"]:
        pm = daily_periods_np == p
        ticket_mask = sel_periods == p
        if pm.any():
            periods[p] = {
                "signal_days": int(pm.sum()),
                "tickets": int(ticket_mask.sum()),
                "return_pct": pct_prod(daily_returns_np[pm]),
                "avg_daily_return_pct": float(np.mean(daily_returns_np[pm])),
                "daily_win_rate": float(np.mean(daily_returns_np[pm] > 0)),
                "high1_hit_rate": float(np.mean(sel_actual[ticket_mask])) if ticket_mask.any() else 0.0,
            }
        else:
            periods[p] = {
                "signal_days": 0,
                "tickets": 0,
                "return_pct": 0.0,
                "avg_daily_return_pct": 0.0,
                "daily_win_rate": 0.0,
                "high1_hit_rate": 0.0,
            }

    negative_months = sum(1 for row in months if row["return_pct"] < 0)
    return {
        "signal_days": int(len(unique_dates)),
        "tickets": int(len(selected_idx)),
        "total_return_pct": pct_prod(daily_returns_np),
        "avg_daily_return_pct": float(np.mean(daily_returns_np)),
        "daily_win_rate": float(np.mean(daily_returns_np > 0)),
        "ticket_win_rate": float(np.mean(sel_returns > 0)),
        "high1_hit_rate": float(np.mean(sel_actual)),
        "sharpe": sharpe_like(daily_returns_np),
        "max_daily_loss_pct": float(np.min(daily_returns_np)),
        "max_daily_gain_pct": float(np.max(daily_returns_np)),
        "negative_months": int(negative_months),
        "months_positive": int(len(months) - negative_months),
        "months_total": int(len(months)),
        "months": months,
        "periods": periods,
    }


def evaluate_matrix(
    top_matrix: np.ndarray,
    top_n: int,
    exit_values: np.ndarray,
    actual: np.ndarray,
    group_month_keys: np.ndarray,
    group_period_keys: np.ndarray,
) -> dict | None:
    idx_mat = top_matrix[:, :top_n]
    valid = idx_mat >= 0
    day_has = valid.any(axis=1)
    if int(day_has.sum()) < 8:
        return None

    valid_counts = valid.sum(axis=1).astype(np.float64)
    ret_mat = np.zeros(idx_mat.shape, dtype=np.float64)
    act_mat = np.zeros(idx_mat.shape, dtype=np.float64)
    flat_idx = idx_mat[valid]
    ret_mat[valid] = exit_values[flat_idx]
    act_mat[valid] = actual[flat_idx]

    daily_returns_all = np.zeros(len(idx_mat), dtype=np.float64)
    daily_returns_all[day_has] = ret_mat.sum(axis=1)[day_has] / valid_counts[day_has]
    daily_returns = daily_returns_all[day_has]
    daily_months = group_month_keys[day_has]
    daily_periods = group_period_keys[day_has]

    day_index_mat = np.broadcast_to(np.arange(len(idx_mat))[:, None], idx_mat.shape)
    ticket_day_index = day_index_mat[valid]
    ticket_months = group_month_keys[ticket_day_index]
    ticket_periods = group_period_keys[ticket_day_index]
    ticket_returns = ret_mat[valid]
    ticket_actual = act_mat[valid]

    months = []
    for m in sorted(np.unique(daily_months)):
        dm = daily_months == m
        tm = ticket_months == m
        months.append(
            {
                "month": str(m),
                "signal_days": int(dm.sum()),
                "tickets": int(tm.sum()),
                "return_pct": pct_prod(daily_returns[dm]),
                "avg_daily_return_pct": float(np.mean(daily_returns[dm])),
                "daily_win_rate": float(np.mean(daily_returns[dm] > 0)),
                "high1_hit_rate": float(np.mean(ticket_actual[tm])) if tm.any() else 0.0,
            }
        )

    periods = {}
    for p in ["search_2023_2025", "q1_2026", "apr_2026", "may_2026_partial"]:
        pm = daily_periods == p
        tp = ticket_periods == p
        if pm.any():
            periods[p] = {
                "signal_days": int(pm.sum()),
                "tickets": int(tp.sum()),
                "return_pct": pct_prod(daily_returns[pm]),
                "avg_daily_return_pct": float(np.mean(daily_returns[pm])),
                "daily_win_rate": float(np.mean(daily_returns[pm] > 0)),
                "high1_hit_rate": float(np.mean(ticket_actual[tp])) if tp.any() else 0.0,
            }
        else:
            periods[p] = {
                "signal_days": 0,
                "tickets": 0,
                "return_pct": 0.0,
                "avg_daily_return_pct": 0.0,
                "daily_win_rate": 0.0,
                "high1_hit_rate": 0.0,
            }

    negative_months = sum(1 for row in months if row["return_pct"] < 0)
    return {
        "signal_days": int(day_has.sum()),
        "tickets": int(valid.sum()),
        "total_return_pct": pct_prod(daily_returns),
        "avg_daily_return_pct": float(np.mean(daily_returns)),
        "daily_win_rate": float(np.mean(daily_returns > 0)),
        "ticket_win_rate": float(np.mean(ticket_returns > 0)),
        "high1_hit_rate": float(np.mean(ticket_actual)),
        "sharpe": sharpe_like(daily_returns),
        "max_daily_loss_pct": float(np.min(daily_returns)),
        "max_daily_gain_pct": float(np.max(daily_returns)),
        "negative_months": int(negative_months),
        "months_positive": int(len(months) - negative_months),
        "months_total": int(len(months)),
        "months": months,
        "periods": periods,
    }


def objective_scores(result: dict) -> dict:
    periods = result["periods"]
    search = periods["search_2023_2025"]
    q1 = periods["q1_2026"]
    apr = periods["apr_2026"]
    may = periods["may_2026_partial"]
    min_oos = min(q1["return_pct"], apr["return_pct"], may["return_pct"])
    neg_penalty = max(0, result["negative_months"] - 4) * 15.0
    loss_penalty = abs(min(result["max_daily_loss_pct"], 0.0)) * 2.0
    sparse_penalty = 25.0 if result["signal_days"] < 60 else 0.0
    robust = (
        0.22 * search["return_pct"]
        + 90.0 * (search["daily_win_rate"] - 0.50)
        + 0.18 * q1["return_pct"]
        + 0.15 * apr["return_pct"]
        + 0.08 * may["return_pct"]
        + 3.0 * min_oos
        + 2.0 * result["sharpe"]
        - neg_penalty
        - loss_penalty
        - sparse_penalty
    )
    current = (
        0.10 * search["return_pct"]
        + 0.15 * q1["return_pct"]
        + 0.38 * apr["return_pct"]
        + 0.25 * may["return_pct"]
        + 100.0 * (result["daily_win_rate"] - 0.52)
        + 1.5 * result["sharpe"]
        - neg_penalty
        - loss_penalty
        - sparse_penalty
    )
    return {"robust_score": float(robust), "current_score": float(current)}


def sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return sanitize_for_json(obj.tolist())
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    return obj


def run_search(df: pd.DataFrame) -> list[dict]:
    exits = compute_exits(df)
    filters = build_filters(df)
    date_codes = pd.Categorical(df["date_key"]).codes
    groups = make_groups(date_codes)
    group_first_indices = np.asarray([idx[0] for idx in groups], dtype=np.int64)
    month_keys = df["month"].to_numpy()
    period_keys = np.asarray([period_name(ts) for ts in df["date"]])
    group_month_keys = month_keys[group_first_indices]
    group_period_keys = period_keys[group_first_indices]
    actual = finite(df["actual"])

    base_exclude = np.ones(len(df), dtype=bool)
    if "limit_up_like" in df.columns:
        base_exclude &= ~(finite(df["limit_up_like"]) > 0.5)

    score_cols = ["raw_prob", "iso_prob"]
    thresholds = [round(x, 3) for x in np.arange(0.50, 0.851, 0.02)]
    top_ns = [1, 2, 3, 4, 5, 6]
    exit_names = [
        "close",
        "tp2",
        "tp3",
        "tp5",
        "tp7",
        "tp10",
        "sl2_tp5_conservative",
        "sl3_tp7_conservative",
        "sl3_tp10_conservative",
    ]

    results: list[dict] = []
    rank_configs = 0
    t0 = time.time()
    last = t0
    for score_col in score_cols:
        score = finite(df[score_col])
        for filter_name, filter_family, filter_mask in filters:
            for recipe in RECIPES:
                if recipe.uses_sector and filter_family == "safe":
                    continue
                primary, secondary, secondary_ascending = recipe_values(df, score_col, recipe)
                for threshold in thresholds:
                    mask = base_exclude & filter_mask & (score >= threshold)
                    if int(mask.sum()) < 20:
                        continue
                    top_matrix = daily_top_matrix(groups, mask, primary, secondary, secondary_ascending)
                    rank_configs += 1
                    if not (top_matrix >= 0).any():
                        continue
                    for top_n in top_ns:
                        if int((top_matrix[:, :top_n] >= 0).sum()) < 12:
                            continue
                        for exit_name in exit_names:
                            metrics = evaluate_matrix(
                                top_matrix,
                                top_n,
                                exits[exit_name],
                                actual,
                                group_month_keys,
                                group_period_keys,
                            )
                            if metrics is None:
                                continue
                            if metrics["signal_days"] < 10:
                                continue
                            row = {
                                **metrics,
                                **objective_scores(metrics),
                                "score_col": score_col,
                                "threshold": float(threshold),
                                "top_n": int(top_n),
                                "filter_name": filter_name,
                                "filter_family": filter_family,
                                "rank_recipe": recipe.name,
                                "exit_mode": exit_name,
                            }
                            results.append(row)
                if time.time() - last > 30:
                    print(
                        f"Progress: {rank_configs:,} rank configs, {len(results):,} strategy evals kept, "
                        f"elapsed {time.time() - t0:.0f}s",
                        flush=True,
                    )
                    last = time.time()

    print(f"Search complete: {rank_configs:,} rank configs, {len(results):,} results", flush=True)
    return results


def summarize(results: list[dict], df: pd.DataFrame) -> dict:
    safe = [r for r in results if r["filter_family"] == "safe" and not str(r["rank_recipe"]).startswith("sector")]
    sector = [r for r in results if r["filter_family"] == "sector_proxy" or str(r["rank_recipe"]).startswith("sector")]

    def sorted_top(rows: list[dict], key: str, limit: int = 20) -> list[dict]:
        return sorted(rows, key=lambda r: r[key], reverse=True)[:limit]

    summary = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "bundle_path": str(BUNDLE_PATH),
        "cache_sources": [str(s["path"]) for s in CACHE_SOURCES],
        "pool": {
            "rows": int(len(df)),
            "days": int(df["date_key"].nunique()),
            "date_min": str(df["date"].min().date()),
            "date_max": str(df["date"].max().date()),
            "months": sorted(df["month"].unique().tolist()),
        },
        "notes": [
            "Main recommendation should prefer safe rows. sector_proxy rows require the same 14:57 sector proxy in web.",
            "P0/hard-moneyflow fields are loaded for audit only and not used in filters or rankings.",
            "Stop-loss/take-profit combo exits use conservative same-day ordering: stop-loss wins if high and low both touch.",
        ],
        "best_safe_current": sorted_top(safe, "current_score", 20),
        "best_safe_robust": sorted_top(safe, "robust_score", 20),
        "best_safe_return": sorted_top(safe, "total_return_pct", 20),
        "best_sector_current": sorted_top(sector, "current_score", 10),
        "best_sector_return": sorted_top(sector, "total_return_pct", 10),
    }
    return summary


def flatten_for_csv(rows: list[dict]) -> pd.DataFrame:
    flat = []
    for r in rows:
        periods = r.get("periods", {})
        row = {
            "score_col": r["score_col"],
            "threshold": r["threshold"],
            "top_n": r["top_n"],
            "filter_name": r["filter_name"],
            "filter_family": r["filter_family"],
            "rank_recipe": r["rank_recipe"],
            "exit_mode": r["exit_mode"],
            "signal_days": r["signal_days"],
            "tickets": r["tickets"],
            "total_return_pct": r["total_return_pct"],
            "daily_win_rate": r["daily_win_rate"],
            "high1_hit_rate": r["high1_hit_rate"],
            "sharpe": r["sharpe"],
            "max_daily_loss_pct": r["max_daily_loss_pct"],
            "negative_months": r["negative_months"],
            "robust_score": r["robust_score"],
            "current_score": r["current_score"],
        }
        for p in ["search_2023_2025", "q1_2026", "apr_2026", "may_2026_partial"]:
            row[f"{p}_return_pct"] = periods.get(p, {}).get("return_pct", 0.0)
            row[f"{p}_days"] = periods.get(p, {}).get("signal_days", 0)
        flat.append(row)
    return pd.DataFrame(flat)


def print_strategy(title: str, row: dict | None) -> None:
    if not row:
        print(f"\n{title}: NONE")
        return
    print(f"\n{title}")
    print(
        f"  {row['score_col']} >= {row['threshold']:.3f} | {row['filter_name']} | "
        f"{row['rank_recipe']} | top{row['top_n']} | {row['exit_mode']}"
    )
    print(
        f"  total={row['total_return_pct']:.2f}% days={row['signal_days']} tickets={row['tickets']} "
        f"daily_win={row['daily_win_rate']*100:.1f}% high1={row['high1_hit_rate']*100:.1f}% "
        f"sharpe={row['sharpe']:.2f} max_loss={row['max_daily_loss_pct']:.2f}%"
    )
    for p, v in row["periods"].items():
        print(f"  {p}: {v['return_pct']:.2f}% / {v['signal_days']} days / h1 {v['high1_hit_rate']*100:.1f}%")
    print("  monthly:")
    for m in row["months"]:
        print(
            f"    {m['month']}: {m['return_pct']:+.2f}% "
            f"days={m['signal_days']} win={m['daily_win_rate']*100:.1f}% h1={m['high1_hit_rate']*100:.1f}%"
        )


def main() -> None:
    t0 = time.time()
    bundle = load_bundle(BUNDLE_PATH)
    df = prepare_pool(bundle)
    results = run_search(df)
    if not results:
        raise RuntimeError("No strategy results produced")
    summary = summarize(results, df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(sanitize_for_json(summary), ensure_ascii=False, indent=2), encoding="utf-8")

    top_rows = []
    for key in ["best_safe_current", "best_safe_robust", "best_safe_return", "best_sector_current", "best_sector_return"]:
        top_rows.extend(summary.get(key, []))
    flat = flatten_for_csv(top_rows)
    flat.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    print_strategy("BEST SAFE CURRENT-MARKET STRATEGY", summary["best_safe_current"][0])
    print_strategy("BEST SAFE ROBUST STRATEGY", summary["best_safe_robust"][0])
    if summary["best_sector_current"]:
        print_strategy("BEST SECTOR-PROXY CURRENT STRATEGY", summary["best_sector_current"][0])

    print(f"\nWrote {OUT_JSON}")
    print(f"Wrote {OUT_CSV}")
    print(f"Total elapsed {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
