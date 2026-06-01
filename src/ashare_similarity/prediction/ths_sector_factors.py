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


def build_ths_sector_factors(
    tushare_dir: Path | str,
    *,
    symbols: set[str] | None = None,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> FactorFrame:
    tushare_dir = Path(tushare_dir)
    members = _load_members(tushare_dir)
    if symbols:
        symbol_filter = {str(symbol).zfill(6) for symbol in symbols}
        members = members[members["symbol"].isin(symbol_filter)].copy()
    if members.empty:
        return _empty_factor()

    ths_daily = _load_ths_daily(tushare_dir)
    if not ths_daily.empty and (start is not None or end is not None):
        trade_dates = pd.to_datetime(ths_daily["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
        if start is not None:
            ths_daily = ths_daily[trade_dates >= pd.Timestamp(start).normalize()].copy()
            trade_dates = trade_dates.loc[ths_daily.index]
        if end is not None:
            ths_daily = ths_daily[trade_dates <= pd.Timestamp(end).normalize()].copy()
    if ths_daily.empty:
        return _empty_factor()

    limit_events = _load_limit_events(tushare_dir)
    if not limit_events.empty:
        if symbols:
            limit_events = limit_events[limit_events["symbol"].isin(symbol_filter)].copy()
        if start is not None or end is not None:
            limit_dates = pd.to_datetime(limit_events["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
            if start is not None:
                limit_events = limit_events[limit_dates >= pd.Timestamp(start).normalize()].copy()
                limit_dates = limit_dates.loc[limit_events.index]
            if end is not None:
                limit_events = limit_events[limit_dates <= pd.Timestamp(end).normalize()].copy()
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
    concept_daily["concept_code"] = concept_daily["concept_code"].astype(str)
    concept_daily["trade_date"] = concept_daily["trade_date"].astype(str)
    concept_daily["pct_change"] = pd.to_numeric(concept_daily["pct_change"], errors="coerce")
    concept_daily = concept_daily.dropna(subset=["concept_code", "trade_date", "pct_change"])
    if concept_daily.empty:
        return pd.DataFrame(columns=["symbol", "date"] + list(THS_SECTOR_COLUMNS))

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

    lu_q70 = concept_daily["limit_up_count"].quantile(0.7)
    pct_q70 = concept_daily["pct_change"].quantile(0.7)
    concept_daily["climax"] = (
        (concept_daily["limit_up_count"] >= max(lu_q70, 3)) &
        (concept_daily["pct_change"] > pct_q70)
    ).astype(np.float32)

    concept_daily = concept_daily.sort_values(["concept_code", "trade_date"]).reset_index(drop=True)
    concept_frames = {
        str(code): group.drop(columns=["concept_code"]).reset_index(drop=True)
        for code, group in concept_daily.groupby("concept_code", sort=False)
    }
    member_groups = (
        members.assign(
            symbol=members["symbol"].astype(str).str.zfill(6),
            concept_code=members["concept_code"].astype(str),
        )
        .drop_duplicates(["symbol", "concept_code"])
        .groupby("symbol", sort=False)["concept_code"]
        .agg(lambda values: tuple(pd.unique(values)))
    )

    chunks: list[pd.DataFrame] = []
    for symbol, concept_codes in member_groups.items():
        frames = [concept_frames[code] for code in concept_codes if code in concept_frames]
        if not frames:
            continue
        stock_concept = pd.concat(frames, ignore_index=True)
        if stock_concept.empty:
            continue
        best_idx = stock_concept.groupby("trade_date", sort=False)["pct_change"].idxmax().dropna()
        if best_idx.empty:
            continue
        best = stock_concept.loc[best_idx].copy()
        divergence = stock_concept.groupby("trade_date", sort=False)["pct_change"].std()
        best["sector_divergence"] = best["trade_date"].map(divergence).fillna(0.0).astype(np.float32)
        chunks.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "date": pd.to_datetime(best["trade_date"], format="%Y%m%d", errors="coerce"),
                    "sector_pct_change_best": best["pct_change"].to_numpy(dtype=np.float32),
                    "sector_strength_rank": (1.0 - best["rank_pct"].fillna(1.0)).to_numpy(dtype=np.float32),
                    "sector_limit_up_count": best["limit_up_count"].fillna(0.0).to_numpy(dtype=np.float32),
                    "sector_divergence": best["sector_divergence"].to_numpy(dtype=np.float32),
                    "sector_duration_days": best["streak_days"].fillna(0.0).to_numpy(dtype=np.float32),
                    "sector_climax_signal": best["climax"].fillna(0.0).to_numpy(dtype=np.float32),
                }
            )
        )

    if not chunks:
        return pd.DataFrame(columns=["symbol", "date"] + list(THS_SECTOR_COLUMNS))
    return pd.concat(chunks, ignore_index=True).dropna(subset=["date"])
