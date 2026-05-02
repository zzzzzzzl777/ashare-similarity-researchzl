"""TGB-derived daily factors for short-term T+1 prediction.

Factors are inspired by TaoGuBa (tgb.cn) trader insights, computed entirely
from daily OHLCV data.  Two FactorFrames are produced:

* ``tgb_stock_daily`` — per-stock signals (join on symbol + date)
* ``tgb_market_regime`` — market-level regime transition signals (join on date)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ashare_similarity.prediction.factor_cache_manager import FactorFrame
from ashare_similarity.prediction.free_data_factors import _limit_threshold_for_symbol

TGB_STOCK_COLUMNS: tuple[str, ...] = (
    "tgb_ma_alignment_score",
    "tgb_ma_divergence_5",
    "tgb_pullback_health",
    "tgb_board_height_vs_max",
    "tgb_board_quality_trend",
    "tgb_zhaban_recovery_score",
    "tgb_volume_buildup_score",
    "tgb_eod_rush_risk",
)

TGB_MARKET_COLUMNS: tuple[str, ...] = (
    "tgb_market_max_height",
    "tgb_leader_break_signal",
    "tgb_nuclear_button_count",
    "tgb_mid_collapse_rate",
    "tgb_retreat_intensity",
    "tgb_new_first_board_count",
)


def _grouped_streak(df: pd.DataFrame, col: str) -> pd.Series:
    """Compute per-symbol consecutive-True streak from a boolean column."""
    out = np.zeros(len(df), dtype=np.float32)
    for _, idx in df.groupby("symbol").groups.items():
        vals = df[col].values[idx]
        s = 0.0
        for j, ix in enumerate(idx):
            s = (s + 1.0) if vals[j] else 0.0
            out[ix] = s
    return pd.Series(out, index=df.index, dtype=np.float32)


def build_tgb_stock_factors(daily: pd.DataFrame) -> FactorFrame:
    """Per-stock TGB-derived factors from daily OHLCV."""
    df = daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    df["prev_close"] = df.groupby("symbol")["close"].shift(1)
    df["ret_pct"] = (df["close"] / df["prev_close"] - 1.0) * 100.0

    _compute_ma_alignment(df)
    _compute_pullback_health(df)
    _compute_board_height_vs_max(df)
    _compute_board_quality_trend(df)
    _compute_zhaban_recovery(df)
    _compute_volume_buildup(df)
    _compute_eod_rush_risk(df)

    out = df[["symbol", "date", *TGB_STOCK_COLUMNS]].copy()
    for col in TGB_STOCK_COLUMNS:
        out[col] = out[col].fillna(0.0).astype(np.float32)

    return FactorFrame(
        name="tgb_stock_daily",
        frame=out,
        columns=TGB_STOCK_COLUMNS,
        source="daily_ohlcv_tgb_derived",
        asof_time="after_close",
        lag_rule="T day close-derived; use for T+1 prediction only",
        join_keys=("symbol", "date"),
    )


def build_tgb_market_regime_factors(daily: pd.DataFrame) -> FactorFrame:
    """Market-level TGB regime transition signals from daily OHLCV."""
    df = daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    df["prev_close"] = df.groupby("symbol")["close"].shift(1)
    df["ret_pct"] = (df["close"] / df["prev_close"] - 1.0) * 100.0

    limit_pct = df["symbol"].map(_limit_threshold_for_symbol)
    df["_lu"] = df["ret_pct"] >= (limit_pct - 0.5)
    df["_consec_limit"] = _grouped_streak(df, "_lu")

    dates = sorted(df["date"].unique())
    records = []
    prev_day_data: pd.DataFrame | None = None

    for d in dates:
        day = df[df["date"] == d]
        rec = _market_regime_for_day(day, prev_day_data)
        rec["date"] = d
        records.append(rec)
        prev_day_data = day

    out = pd.DataFrame(records)
    for col in TGB_MARKET_COLUMNS:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = out[col].fillna(0.0).astype(np.float32)

    return FactorFrame(
        name="tgb_market_regime",
        frame=out[["date", *TGB_MARKET_COLUMNS]],
        columns=TGB_MARKET_COLUMNS,
        source="daily_ohlcv_tgb_derived",
        asof_time="after_close",
        lag_rule="T day close-derived; use for T+1 prediction only",
        join_keys=("date",),
    )


# ---------------------------------------------------------------------------
# Per-stock factor helpers
# ---------------------------------------------------------------------------


def _compute_ma_alignment(df: pd.DataFrame) -> None:
    """Factor 4: MA multi-head arrangement score (0-4)."""
    for window in (5, 10, 20, 60):
        df[f"_ma{window}"] = df.groupby("symbol")["close"].transform(
            lambda s: s.rolling(window, min_periods=window).mean()
        )

    score = np.zeros(len(df), dtype=np.float32)
    c = df["close"].values
    ma5 = df["_ma5"].values
    ma10 = df["_ma10"].values
    ma20 = df["_ma20"].values
    ma60 = df["_ma60"].values

    score += (c > ma5).astype(np.float32)
    score += (ma5 > ma10).astype(np.float32)
    score += (ma10 > ma20).astype(np.float32)
    score += (ma20 > ma60).astype(np.float32)
    df["tgb_ma_alignment_score"] = score

    ma5_slope = df.groupby("symbol")["_ma5"].transform(
        lambda s: s.pct_change(5, fill_method=None)
    )
    ma10_slope = df.groupby("symbol")["_ma10"].transform(
        lambda s: s.pct_change(5, fill_method=None)
    )
    ma20_slope = df.groupby("symbol")["_ma20"].transform(
        lambda s: s.pct_change(5, fill_method=None)
    )
    df["tgb_ma_divergence_5"] = (
        (ma5_slope.fillna(0.0) + ma10_slope.fillna(0.0) + ma20_slope.fillna(0.0)) / 3.0
    ).astype(np.float32)

    df.drop(columns=["_ma5", "_ma10", "_ma20", "_ma60"], inplace=True)


def _compute_pullback_health(df: pd.DataFrame) -> None:
    """Factors 5-6: Pullback quality after a big move — vol shrinkage + holding MA5."""
    df["_ma5_pb"] = df.groupby("symbol")["close"].transform(
        lambda s: s.rolling(5, min_periods=3).mean()
    )
    vol_mean = df.groupby("symbol")["volume"].transform(
        lambda s: s.rolling(5, min_periods=3).mean()
    )
    df["_vol_ratio_1"] = df["volume"] / vol_mean.replace(0, np.nan)
    df["_big_move_recent"] = df.groupby("symbol")["ret_pct"].transform(
        lambda s: (s.rolling(5, min_periods=1).max() >= 5.0).astype(float)
    )

    above_ma5 = (df["close"] >= df["_ma5_pb"]).astype(np.float32)
    vol_shrink = (df["_vol_ratio_1"] < 1.0).astype(np.float32)
    small_body = np.where(
        df["close"] > 0,
        (np.abs(df["close"] - df["open"]) / df["close"] < 0.02).astype(np.float32),
        0.0,
    )

    raw_score = (above_ma5 + vol_shrink + small_body) / 3.0
    df["tgb_pullback_health"] = np.where(
        df["_big_move_recent"] > 0.5, raw_score, 0.0
    ).astype(np.float32)

    df.drop(columns=["_ma5_pb", "_vol_ratio_1", "_big_move_recent"], inplace=True)


def _compute_board_height_vs_max(df: pd.DataFrame) -> None:
    """Factors 15-16: Stock's board height relative to market maximum."""
    limit_pct = df["symbol"].map(_limit_threshold_for_symbol)
    df["_lu"] = df["ret_pct"] >= (limit_pct - 0.5)
    df["_consec"] = _grouped_streak(df, "_lu")

    market_max = df.groupby("date")["_consec"].transform("max")
    df["tgb_board_height_vs_max"] = np.where(
        market_max > 0, df["_consec"] / market_max, 0.0
    ).astype(np.float32)

    df.drop(columns=["_lu", "_consec"], inplace=True)


def _compute_board_quality_trend(df: pd.DataFrame) -> None:
    """Factor 2: How seal quality evolves over consecutive limit-up days."""
    if "open" not in df.columns:
        df["tgb_board_quality_trend"] = np.float32(0.0)
        return

    limit_pct = df["symbol"].map(_limit_threshold_for_symbol)
    is_lu = (df["ret_pct"] >= (limit_pct - 0.5)).values

    high = df["high"].values
    low = df["low"].values
    close_arr = df["close"].values
    close_pos = np.where(
        high > low,
        (close_arr - low) / (high - low),
        0.5,
    )

    result = np.zeros(len(df), dtype=np.float32)
    for _, idx in df.groupby("symbol").groups.items():
        prev_quality = np.nan
        for ix in idx:
            if is_lu[ix]:
                cur_quality = close_pos[ix]
                if not np.isnan(prev_quality):
                    result[ix] = cur_quality - prev_quality
                prev_quality = cur_quality
            else:
                prev_quality = np.nan

    df["tgb_board_quality_trend"] = result


def _compute_zhaban_recovery(df: pd.DataFrame) -> None:
    """Factor 9: Post-broken-board recovery quality."""
    limit_pct = df["symbol"].map(_limit_threshold_for_symbol)
    is_lu = (df["ret_pct"] >= (limit_pct - 0.5)).values

    prev_close = df["prev_close"].values
    high_arr = df["high"].values
    safe_prev = np.where(prev_close > 0, prev_close, 1.0)
    touched_limit = ((high_arr / safe_prev - 1.0) * 100.0) >= (limit_pct.values - 0.5)
    is_zhaban = touched_limit & ~is_lu

    rets = df["ret_pct"].values

    result = np.zeros(len(df), dtype=np.float32)
    for _, idx in df.groupby("symbol").groups.items():
        zhaban_drop: float | None = None
        for ix in idx:
            if is_zhaban[ix]:
                zhaban_drop = rets[ix]
            elif zhaban_drop is not None and zhaban_drop < 0:
                recovery_ratio = -rets[ix] / zhaban_drop if rets[ix] > 0 else 0.0
                result[ix] = min(float(recovery_ratio), 2.0)
                zhaban_drop = None
            else:
                zhaban_drop = None

    df["tgb_zhaban_recovery_score"] = result


def _compute_volume_buildup(df: pd.DataFrame) -> None:
    """Factor 5: Volume accumulation pattern before breakout."""
    vol_ma20 = df.groupby("symbol")["volume"].transform(
        lambda s: s.rolling(20, min_periods=10).mean()
    )
    vol_ma5 = df.groupby("symbol")["volume"].transform(
        lambda s: s.rolling(5, min_periods=3).mean()
    )
    vol_increasing = (vol_ma5 / vol_ma20.replace(0, np.nan)).fillna(1.0)
    price_near_high = df.groupby("symbol")["close"].transform(
        lambda s: s / s.rolling(20, min_periods=10).max()
    ).fillna(0.0)

    df["tgb_volume_buildup_score"] = np.where(
        (vol_increasing > 1.0) & (price_near_high > 0.95),
        np.clip((vol_increasing - 1.0) * price_near_high, 0.0, 2.0),
        0.0,
    ).astype(np.float32)


def _compute_eod_rush_risk(df: pd.DataFrame) -> None:
    """Factor 12: EOD sneak limit risk proxy from daily candle shape.

    Detects late-session rush: big intraday range, close near high, open in
    the lower half of the range suggesting most of the move came late.
    """
    if "open" not in df.columns:
        df["tgb_eod_rush_risk"] = np.float32(0.0)
        return

    high = df["high"].values
    low = df["low"].values
    close_arr = df["close"].values
    open_arr = df["open"].values
    prev_close = df["prev_close"].values

    rng = high - low
    safe_range = np.where(rng > 0, rng, 1.0)

    close_pos = (close_arr - low) / safe_range
    open_pos = (open_arr - low) / safe_range

    safe_prev = np.where(prev_close > 0, prev_close, 1.0)
    day_return = (close_arr / safe_prev) - 1.0

    near_high = close_pos >= 0.90
    open_low = open_pos < 0.50
    big_move = day_return >= 0.05

    df["tgb_eod_rush_risk"] = (
        near_high & open_low & big_move
    ).astype(np.float32)


# ---------------------------------------------------------------------------
# Market regime factor helpers
# ---------------------------------------------------------------------------


def _market_regime_for_day(
    day: pd.DataFrame,
    prev_day: pd.DataFrame | None,
) -> dict[str, float]:
    """Compute market regime signals for a single trading day."""
    max_height = float(day["_consec_limit"].max()) if len(day) > 0 else 0.0

    leader_break = 0.0
    nuclear_count = 0.0
    mid_collapse_rate = 0.0
    new_first_boards = 0.0

    if prev_day is not None and len(prev_day) > 0 and len(day) > 0:
        prev_max = float(prev_day["_consec_limit"].max())
        if prev_max >= 2.0 and max_height < prev_max:
            prev_leaders = set(
                prev_day.loc[prev_day["_consec_limit"] == prev_max, "symbol"]
            )
            today_symbols = set(day["symbol"])
            for sym in prev_leaders:
                if sym in today_symbols:
                    sym_ret = day.loc[day["symbol"] == sym, "ret_pct"]
                    if len(sym_ret) > 0 and float(sym_ret.iloc[0]) < 0:
                        leader_break = 1.0
                        break

        prev_strong = prev_day[prev_day["ret_pct"] >= 5.0]
        if len(prev_strong) > 0:
            for sym in prev_strong["symbol"].values:
                sym_today = day.loc[day["symbol"] == sym, "ret_pct"]
                if len(sym_today) > 0 and float(sym_today.iloc[0]) <= -5.0:
                    nuclear_count += 1.0

        prev_mid = prev_day[prev_day["_consec_limit"] >= 3.0]
        if len(prev_mid) > 0:
            broken = 0
            for sym in prev_mid["symbol"].values:
                sym_today = day.loc[day["symbol"] == sym, "_consec_limit"]
                if len(sym_today) > 0 and float(sym_today.iloc[0]) == 0.0:
                    broken += 1
            mid_collapse_rate = broken / len(prev_mid)

    if len(day) > 0:
        day_lu = day[day["_consec_limit"] == 1.0]
        new_first_boards = float(len(day_lu))

    retreat_intensity = min(
        (leader_break + nuclear_count * 0.2 + mid_collapse_rate) / 2.0, 1.0
    )

    return {
        "tgb_market_max_height": max_height,
        "tgb_leader_break_signal": leader_break,
        "tgb_nuclear_button_count": nuclear_count,
        "tgb_mid_collapse_rate": mid_collapse_rate,
        "tgb_retreat_intensity": retreat_intensity,
        "tgb_new_first_board_count": new_first_boards,
    }
