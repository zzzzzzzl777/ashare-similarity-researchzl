"""THS concept-sector factors for short-term T+1 prediction.

Uses cached Tushare THS data:
- ths_member: stock -> concept mapping (all_members.parquet)
- ths_daily: concept-level daily stats (per-date parquet)
- limit_list_d: daily limit-up/down events (per-date parquet)

Produces a single FactorFrame with join_keys=("symbol", "date").
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ashare_similarity.prediction.factor_cache_manager import FactorFrame

THS_SECTOR_COLUMNS: tuple[str, ...] = (
    "sector_pct_change_best",
    "sector_strength_rank",
    "sector_limit_up_count",
    "sector_divergence",
    "sector_duration_days",
    "sector_climax_signal",
)


def build_ths_sector_factors(tushare_dir: Path | str) -> FactorFrame:
    tushare_dir = Path(tushare_dir)
    members = _load_members(tushare_dir)
    if members.empty:
        return _empty_factor()

    ths_daily = _load_ths_daily(tushare_dir)
    if ths_daily.empty:
        return _empty_factor()

    limit_events = _load_limit_events(tushare_dir)
    result = _compute_sector_factors(members, ths_daily, limit_events)
    if result.empty:
        return _empty_factor()

    for col in THS_SECTOR_COLUMNS:
        if col not in result.columns:
            result[col] = 0.0
        result[col] = result[col].fillna(0.0).astype(np.float32)

    return FactorFrame(
        name="ths_sector_daily",
        frame=result[["symbol", "date", *THS_SECTOR_COLUMNS]],
        columns=THS_SECTOR_COLUMNS,
        source="tushare_ths_cached",
        asof_time="after_close",
        lag_rule="T day THS concept data; use for T+1 prediction only",
        join_keys=("symbol", "date"),
    )


def _empty_factor() -> FactorFrame:
    return FactorFrame(
        name="ths_sector_daily",
        frame=pd.DataFrame(columns=["symbol", "date", *THS_SECTOR_COLUMNS]),
        columns=THS_SECTOR_COLUMNS,
        source="tushare_ths_cached",
        asof_time="after_close",
        lag_rule="T day THS concept data; use for T+1 prediction only",
        join_keys=("symbol", "date"),
    )


def _load_members(tushare_dir: Path) -> pd.DataFrame:
    path = tushare_dir / "ths_member" / "all_members.parquet"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    df = df.rename(columns={"ts_code": "concept_code", "con_code": "ts_code"})
    df["symbol"] = df["ts_code"].str.replace(r"\.\w+$", "", regex=True).str.zfill(6)
    return df[["symbol", "concept_code"]].drop_duplicates()


def _load_ths_daily(tushare_dir: Path) -> pd.DataFrame:
    daily_dir = tushare_dir / "ths_daily"
    if not daily_dir.exists():
        return pd.DataFrame()
    frames = []
    for f in sorted(daily_dir.iterdir()):
        if not f.name.endswith(".parquet") or f.name.startswith("_"):
            continue
        try:
            df = pd.read_parquet(f, columns=["ts_code", "trade_date", "pct_change"])
            if not df.empty:
                frames.append(df)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    result["trade_date"] = result["trade_date"].astype(str)
    result = result.rename(columns={"ts_code": "concept_code"})
    return result


def _load_limit_events(tushare_dir: Path) -> pd.DataFrame:
    limit_dir = tushare_dir / "limit_list_d"
    if not limit_dir.exists():
        return pd.DataFrame()
    frames = []
    for f in sorted(limit_dir.iterdir()):
        if not f.name.endswith(".parquet") or f.name.startswith("_"):
            continue
        try:
            df = pd.read_parquet(f, columns=["trade_date", "ts_code", "limit"])
            lu = df[df["limit"] == "U"][["trade_date", "ts_code"]].copy()
            if not lu.empty:
                frames.append(lu)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    result["trade_date"] = result["trade_date"].astype(str)
    result["symbol"] = result["ts_code"].str.replace(r"\.\w+$", "", regex=True).str.zfill(6)
    return result[["trade_date", "symbol"]]


def _compute_concept_streak(concept_daily: pd.DataFrame) -> pd.DataFrame:
    """Vectorized consecutive-up-day streak per concept."""
    df = concept_daily[["concept_code", "trade_date", "pct_change"]].copy()
    df = df.sort_values(["concept_code", "trade_date"]).reset_index(drop=True)
    is_up = (df["pct_change"] > 0).astype(int).values
    concept_ids = df["concept_code"].values

    streak = np.zeros(len(df), dtype=np.float32)
    for i in range(len(df)):
        if i == 0 or concept_ids[i] != concept_ids[i - 1]:
            streak[i] = float(is_up[i])
        elif is_up[i]:
            streak[i] = streak[i - 1] + 1.0
        else:
            streak[i] = 0.0

    df["streak_days"] = streak
    return df[["concept_code", "trade_date", "streak_days"]]


def _compute_sector_factors(
    members: pd.DataFrame,
    ths_daily: pd.DataFrame,
    limit_events: pd.DataFrame,
) -> pd.DataFrame:
    concept_daily = ths_daily.copy()

    n_per_date = concept_daily.groupby("trade_date")["concept_code"].transform("count")
    concept_daily["rank"] = concept_daily.groupby("trade_date")["pct_change"].rank(
        ascending=False, method="min", na_option="bottom"
    )
    concept_daily["rank_pct"] = concept_daily["rank"] / n_per_date

    streak_df = _compute_concept_streak(ths_daily)
    concept_daily = concept_daily.merge(
        streak_df, on=["concept_code", "trade_date"], how="left"
    )

    if not limit_events.empty:
        lu_concept = (
            limit_events
            .merge(members, on="symbol", how="inner")
            .groupby(["trade_date", "concept_code"])
            .size()
            .reset_index(name="limit_up_count")
        )
        concept_daily = concept_daily.merge(
            lu_concept, on=["trade_date", "concept_code"], how="left"
        )
    if "limit_up_count" not in concept_daily.columns:
        concept_daily["limit_up_count"] = 0.0
    concept_daily["limit_up_count"] = concept_daily["limit_up_count"].fillna(0)

    stock_concept = members.merge(concept_daily, on="concept_code", how="inner")

    stock_concept = stock_concept.dropna(subset=["pct_change"])
    if stock_concept.empty:
        return pd.DataFrame(columns=["symbol", "date"] + list(THS_SECTOR_COLUMNS))
    best_idx = stock_concept.groupby(["symbol", "trade_date"])["pct_change"].idxmax()
    best_idx = best_idx.dropna()
    if best_idx.empty:
        return pd.DataFrame(columns=["symbol", "date"] + list(THS_SECTOR_COLUMNS))
    best = stock_concept.loc[best_idx].copy()

    divergence = (
        stock_concept
        .groupby(["symbol", "trade_date"])["pct_change"]
        .std()
        .reset_index(name="divergence")
    )
    best = best.merge(divergence, on=["symbol", "trade_date"], how="left")
    best["divergence"] = best["divergence"].fillna(0)

    lu_q70 = best["limit_up_count"].quantile(0.7)
    pct_q70 = best["pct_change"].quantile(0.7)
    best["climax"] = (
        (best["limit_up_count"] >= max(lu_q70, 3)) &
        (best["pct_change"] > pct_q70)
    ).astype(np.float32)

    result = pd.DataFrame({
        "symbol": best["symbol"].values,
        "date": pd.to_datetime(best["trade_date"], format="%Y%m%d"),
        "sector_pct_change_best": best["pct_change"].values.astype(np.float32),
        "sector_strength_rank": (1.0 - best["rank_pct"].values).astype(np.float32),
        "sector_limit_up_count": best["limit_up_count"].values.astype(np.float32),
        "sector_divergence": best["divergence"].values.astype(np.float32),
        "sector_duration_days": best["streak_days"].fillna(0).values.astype(np.float32),
        "sector_climax_signal": best["climax"].values.astype(np.float32),
    })

    return result
