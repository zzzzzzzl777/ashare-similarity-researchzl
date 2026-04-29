from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from ashare_similarity.prediction.factor_cache_manager import FactorFrame


MARKET_EMOTION_COLUMNS: tuple[str, ...] = (
    "market_limit_up_count",
    "market_limit_down_count",
    "market_broken_board_count",
    "market_broken_board_rate",
    "market_broken_board_rate_1st",
    "market_broken_board_rate_1to2",
    "market_failed_limit_up_rate",
    "market_seal_rate",
    "market_limit_seal_success_rate",
    "seal_rate_80_threshold",
    "market_limit_down_rate",
    "market_one_word_board_count",
    "market_emotion_score",
    "emotion_phase_code",
    "emotion_phase_ice",
    "emotion_phase_trial",
    "emotion_phase_upswing",
    "emotion_phase_climax",
    "emotion_phase_divergence",
    "emotion_phase_ebbing",
    "emotion_climax_next_day_risk",
    "emotion_ice_rebound_setup",
    "cycle_day_count",
    "divergence_day_count",
    "buy_sell_cycle_phase",
    "liquidity_exhaustion_signal",
    "market_split_signal",
    "quant_climax_type",
    "vol_stagnation_signal",
    "bull_rotation_upgrade",
    "theme_capacity_score",
    "market_advance_decline_ratio",
    "market_new_high_20_count",
    "market_new_low_20_count",
    "market_active_turnover_mean",
    "market_active_amount_sum",
    "market_max_board_height",
    "market_echelon_completeness",
    "market_board_promotion_rate",
    "market_board_promotion_rate_1to2",
    "market_board_promotion_rate_2to3",
    "market_board_promotion_rate_high",
    "prev_limit_up_premium",
    "prev_board_premium",
    "prev_top20_chase_return",
    "prev_top20_chase_win_rate",
    "prev_bottom20_rebound_return",
    "money_effect_spread_20",
    "collapse_warning_signal",
    "consecutive_ice_days",
    "consecutive_high_premium_days",
    "market_amount_ratio_20",
    "market_amount_percentile_60",
    "volume_is_king_signal",
    "ground_volume_risk",
    "post_decline_transition",
    "decline_stabilize_signal",
    "weak_friday_risk",
    "strong_market_regime",
    "weak_market_oversold_regime",
    "bull_hotspot_bear_oversold",
)

BOARD_STRUCTURE_COLUMNS: tuple[str, ...] = (
    "board_count",
    "board_vs_max",
    "board_height_suppression",
    "is_space_board",
    "is_first_board",
    "is_second_board",
    "is_high_board",
    "prev_board_count",
    "board_promoted_today",
    "first_divergence_flag",
    "first_negative_flag",
    "volume_vs_prev",
    "volume_health_zone",
    "consecutive_shrink_days",
    "shrink_after_rotten",
    "explosive_vol_next_weak",
    "break_node_new_dragon",
    "dragon_replace_signal",
    "mid_cap_trap_risk",
    "buy_rise_divergence",
    "bet_decline_exhaustion",
    "board_keep_break_signal",
    "one_day_trip_risk_proxy",
)


def build_market_emotion_factor(daily_bars: pd.DataFrame) -> FactorFrame:
    """Build date-level market emotion proxies from local free daily cache."""
    required = {"symbol", "date", "high", "low", "close"}
    missing = sorted(required - set(daily_bars.columns))
    if missing:
        raise ValueError(f"market emotion factor missing columns: {missing}")
    frame = daily_bars.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.zfill(6)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).sort_values(["symbol", "date"]).reset_index(drop=True)
    for column in ("open", "high", "low", "close", "volume", "amount", "turnover"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "volume" not in frame.columns:
        frame["volume"] = np.nan
    frame["prev_close"] = frame.groupby("symbol", sort=False)["close"].shift(1)
    frame["ret_pct"] = (frame["close"] / frame["prev_close"] - 1.0) * 100.0
    frame["close_position"] = (frame["close"] - frame["low"]) / (frame["high"] - frame["low"]).replace(0.0, np.nan)
    rolling_close = frame.groupby("symbol", sort=False)["close"]
    frame["high_20"] = rolling_close.transform(lambda values: values.rolling(20, min_periods=5).max())
    frame["low_20"] = rolling_close.transform(lambda values: values.rolling(20, min_periods=5).min())
    frame["limit_up_like"] = frame["ret_pct"] >= 9.5
    frame["limit_down_like"] = frame["ret_pct"] <= -9.5
    frame["touched_limit_up"] = (frame["high"] / frame["prev_close"] - 1.0) * 100.0 >= 9.5
    frame["sealed_limit_up"] = frame["limit_up_like"] & (frame["close_position"].fillna(0.0) >= 0.95)
    frame["one_word_board_like"] = frame["limit_up_like"] & (((frame["low"] / frame["prev_close"] - 1.0) * 100.0) >= 9.0)
    frame["failed_limit_up"] = frame["touched_limit_up"] & ~frame["sealed_limit_up"]
    frame["new_high_20"] = frame["close"] >= frame["high_20"]
    frame["new_low_20"] = frame["close"] <= frame["low_20"]
    frame["board_count"] = frame.groupby("symbol", sort=False)["limit_up_like"].transform(_consecutive_true_count)
    frame["prev_board_count"] = frame.groupby("symbol", sort=False)["board_count"].shift(1).fillna(0.0)
    frame["board_promoted_today"] = (frame["board_count"] == frame["prev_board_count"] + 1.0) & (frame["board_count"] > 1.0)
    frame["prev_limit_up_flag"] = frame.groupby("symbol", sort=False)["limit_up_like"].shift(1).eq(True)
    frame["prev_board_flag"] = frame.groupby("symbol", sort=False)["board_count"].shift(1).fillna(0.0) >= 2.0
    frame["top20_ret_rank"] = frame.groupby("date", sort=False)["ret_pct"].rank(method="first", ascending=False)
    frame["bottom20_ret_rank"] = frame.groupby("date", sort=False)["ret_pct"].rank(method="first", ascending=True)
    frame["prev_top20_ret_flag"] = frame.groupby("symbol", sort=False)["top20_ret_rank"].shift(1).le(20.0)
    frame["prev_bottom20_ret_flag"] = frame.groupby("symbol", sort=False)["bottom20_ret_rank"].shift(1).le(20.0)
    frame["volume_vs_prev"] = frame.groupby("symbol", sort=False)["volume"].transform(lambda values: values / values.shift(1)).replace([np.inf, -np.inf], np.nan)
    if "turnover" not in frame.columns:
        frame["turnover"] = np.nan
    if "amount" not in frame.columns:
        frame["amount"] = np.nan

    grouped = frame.groupby("date", sort=False)
    limit_up_count = grouped["limit_up_like"].sum().astype(float)
    limit_down_count = grouped["limit_down_like"].sum().astype(float)
    broken_count = grouped["failed_limit_up"].sum().astype(float)
    touched_count = grouped["touched_limit_up"].sum().astype(float)
    sealed_count = grouped["sealed_limit_up"].sum().astype(float)
    emotion_score = limit_up_count - broken_count - limit_down_count
    max_board_height = grouped["board_count"].max().fillna(0.0).astype(float)
    premium = _group_apply(
        grouped,
        lambda values: float(values.loc[values["prev_limit_up_flag"], "ret_pct"].mean())
        if values["prev_limit_up_flag"].any()
        else 0.0,
    )
    board_premium = _group_apply(
        grouped,
        lambda values: float(values.loc[values["prev_board_flag"], "ret_pct"].mean())
        if values["prev_board_flag"].any()
        else 0.0,
    )
    top20_chase_return = _group_apply(grouped, lambda values: _flagged_mean(values, "prev_top20_ret_flag", "ret_pct"))
    top20_chase_win_rate = _group_apply(grouped, lambda values: _flagged_positive_rate(values, "prev_top20_ret_flag", "ret_pct"))
    bottom20_rebound_return = _group_apply(grouped, lambda values: _flagged_mean(values, "prev_bottom20_ret_flag", "ret_pct"))
    out = pd.DataFrame(
        {
            "date": grouped.size().index,
            "market_limit_up_count": limit_up_count.to_numpy(),
            "market_limit_down_count": limit_down_count.to_numpy(),
            "market_broken_board_count": broken_count.to_numpy(),
            "market_broken_board_rate": (broken_count / touched_count.replace(0.0, np.nan)).fillna(0.0).to_numpy(),
            "market_broken_board_rate_1st": _group_apply(
                grouped,
                lambda values: _broken_board_rate(values, prev_board_count=0),
            ).astype(float).to_numpy(),
            "market_broken_board_rate_1to2": _group_apply(
                grouped,
                lambda values: _broken_board_rate(values, prev_board_count=1),
            ).astype(float).to_numpy(),
            "market_failed_limit_up_rate": grouped["failed_limit_up"].mean().astype(float).to_numpy(),
            "market_seal_rate": grouped["sealed_limit_up"].mean().astype(float).to_numpy(),
            "market_limit_seal_success_rate": (sealed_count / touched_count.replace(0.0, np.nan)).fillna(0.0).to_numpy(),
            "market_limit_down_rate": (limit_down_count / grouped.size().replace(0.0, np.nan)).fillna(0.0).to_numpy(),
            "market_one_word_board_count": grouped["one_word_board_like"].sum().astype(float).to_numpy(),
            "market_emotion_score": emotion_score.to_numpy(),
            "market_advance_decline_ratio": grouped["ret_pct"].apply(_advance_decline_ratio).astype(float).to_numpy(),
            "market_new_high_20_count": grouped["new_high_20"].sum().astype(float).to_numpy(),
            "market_new_low_20_count": grouped["new_low_20"].sum().astype(float).to_numpy(),
            "market_active_turnover_mean": grouped["turnover"].mean().fillna(0.0).astype(float).to_numpy(),
            "market_active_amount_sum": grouped["amount"].sum().fillna(0.0).astype(float).to_numpy(),
            "market_max_board_height": max_board_height.to_numpy(),
            "market_echelon_completeness": _group_apply(grouped, _echelon_completeness).astype(float).to_numpy(),
            "market_board_promotion_rate": _group_apply(grouped, _promotion_rate).astype(float).to_numpy(),
            "market_board_promotion_rate_1to2": _group_apply(grouped, lambda values: _promotion_rate(values, start_level=1)).astype(float).to_numpy(),
            "market_board_promotion_rate_2to3": _group_apply(grouped, lambda values: _promotion_rate(values, start_level=2)).astype(float).to_numpy(),
            "market_board_promotion_rate_high": _group_apply(grouped, lambda values: _promotion_rate(values, min_start_level=3)).astype(float).to_numpy(),
            "prev_limit_up_premium": premium.fillna(0.0).astype(float).to_numpy(),
            "prev_board_premium": board_premium.fillna(0.0).astype(float).to_numpy(),
            "prev_top20_chase_return": top20_chase_return.fillna(0.0).astype(float).to_numpy(),
            "prev_top20_chase_win_rate": top20_chase_win_rate.fillna(0.0).astype(float).to_numpy(),
            "prev_bottom20_rebound_return": bottom20_rebound_return.fillna(0.0).astype(float).to_numpy(),
            "money_effect_spread_20": (top20_chase_return - bottom20_rebound_return).fillna(0.0).astype(float).to_numpy(),
        }
    )
    phase = _emotion_phase_frame(out)
    out = pd.concat([out, phase], axis=1)
    out["consecutive_ice_days"] = _consecutive_true_count(out["market_emotion_score"] < 0.0).astype(float)
    out["consecutive_high_premium_days"] = _consecutive_true_count(out["prev_limit_up_premium"] > 3.0).astype(float)
    out["emotion_climax_next_day_risk"] = (
        ((out["emotion_phase_climax"] > 0.0) & (out["consecutive_high_premium_days"] >= 2.0))
        | (out["prev_limit_up_premium"] > 5.0)
    ).astype(float)
    out["emotion_ice_rebound_setup"] = (
        ((out["emotion_phase_ice"] > 0.0) & (out["consecutive_ice_days"] >= 2.0))
        | (out["prev_limit_up_premium"] < -3.0)
    ).astype(float)
    structure = _market_structure_frame(out)
    out = pd.concat([out, structure], axis=1)
    return FactorFrame(
        name="market_emotion_daily_proxy",
        frame=out,
        columns=MARKET_EMOTION_COLUMNS,
        source="local_daily_cache",
        asof_time="after_close",
        lag_rule="T day close-derived; use for T+1 prediction only",
        join_keys=("date",),
    )


def build_board_structure_factor(daily_bars: pd.DataFrame) -> FactorFrame:
    frame = _prepare_daily_board_frame(daily_bars)
    grouped_symbol = frame.groupby("symbol", sort=False)
    frame["volume_vs_prev"] = grouped_symbol["volume"].transform(lambda values: values / values.shift(1)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    frame["volume_health_zone"] = np.select(
        [frame["volume_vs_prev"] >= 1.0, frame["volume_vs_prev"] >= 0.7],
        [2.0, 1.0],
        default=0.0,
    )
    grouped_symbol = frame.groupby("symbol", sort=False)
    frame["consecutive_shrink_days"] = grouped_symbol["volume_vs_prev"].transform(lambda values: _consecutive_true_count(values < 1.0)).astype(float)
    frame["prev_failed_limit_up"] = grouped_symbol["failed_limit_up"].shift(1).eq(True)
    frame["shrink_after_rotten"] = (frame["prev_failed_limit_up"] & (frame["volume_vs_prev"] < 0.70)).astype(float)
    prev_volume_max_60 = grouped_symbol["volume"].transform(lambda values: values.rolling(60, min_periods=10).max().shift(1))
    prev_volume = grouped_symbol["volume"].shift(1)
    frame["open_gap_pct"] = (frame["open"] / frame["prev_close"] - 1.0) * 100.0
    frame["explosive_vol_next_weak"] = (
        (prev_volume >= prev_volume_max_60 * 0.95)
        & (frame["open_gap_pct"].fillna(0.0) < 1.0)
    ).astype(float)
    max_board = frame.groupby("date", sort=False)["board_count"].transform("max").fillna(0.0).astype(float)
    prev_market_max = frame.groupby("date", sort=False)["prev_board_count"].transform("max").fillna(0.0).astype(float)
    limit_up_count = frame.groupby("date", sort=False)["limit_up_like"].transform("sum").astype(float)
    limit_down_count = frame.groupby("date", sort=False)["limit_down_like"].transform("sum").astype(float)
    market_count = frame.groupby("date", sort=False)["symbol"].transform("count").astype(float).clip(lower=1.0)
    broken_count = frame.groupby("date", sort=False)["failed_limit_up"].transform("sum").astype(float)
    broken_rate = broken_count / np.maximum(limit_up_count + broken_count, 1.0)
    market_liquidity_exhaustion = (limit_down_count >= 10.0) | ((limit_down_count / market_count) >= 0.02)
    space_break_today = (
        (frame["prev_board_count"] >= 2.0)
        & (frame["prev_board_count"] >= prev_market_max)
        & ((frame["board_count"] <= 0.0) | (frame["ret_pct"] <= -7.0))
    )
    break_node = space_break_today.groupby(frame["date"], sort=False).transform("max").astype(bool)
    frame["board_vs_max"] = frame["board_count"] / np.maximum(max_board, 1.0)
    frame["board_height_suppression"] = np.maximum(max_board - frame["board_count"], 0.0)
    frame["is_space_board"] = ((frame["board_count"] > 0.0) & (frame["board_count"] >= max_board) & (max_board > 0.0)).astype(float)
    frame["is_first_board"] = (frame["board_count"] == 1.0).astype(float)
    frame["is_second_board"] = (frame["board_count"] == 2.0).astype(float)
    frame["is_high_board"] = (frame["board_count"] >= 3.0).astype(float)
    frame["first_divergence_flag"] = (
        (frame["prev_board_count"] >= 2.0)
        & (frame["board_count"] <= frame["prev_board_count"])
        & (frame["volume_vs_prev"] >= 1.0)
    ).astype(float)
    frame["first_negative_flag"] = (
        (grouped_symbol["ret_pct"].shift(1).fillna(0.0) >= 5.0)
        & (frame["ret_pct"] < 0.0)
        & (frame["close"] >= grouped_symbol["close"].transform(lambda values: values.rolling(5, min_periods=1).mean()))
    ).astype(float)
    frame["break_node_new_dragon"] = (break_node & (frame["is_first_board"] > 0.0)).astype(float)
    frame["dragon_replace_signal"] = frame["break_node_new_dragon"]
    frame["mid_cap_trap_risk"] = (
        market_liquidity_exhaustion
        & (prev_market_max >= 3.0)
        & (frame["prev_board_count"] >= 2.0)
        & (frame["prev_board_count"] < prev_market_max)
    ).astype(float)
    frame["buy_rise_divergence"] = (
        (frame["ret_pct"] >= 3.0)
        & (frame["volume_vs_prev"] >= 1.2)
        & (frame["close_position"].fillna(0.5) < 0.70)
    ).astype(float)
    down_streak = grouped_symbol["ret_pct"].transform(lambda values: _consecutive_true_count(values < 0.0)).astype(float)
    frame["bet_decline_exhaustion"] = (
        (down_streak >= 3.0)
        & (frame["volume_vs_prev"] >= 1.0)
        & (frame["close_position"].fillna(0.0) >= 0.45)
    ).astype(float)
    frame["board_keep_break_signal"] = np.select(
        [frame["board_promoted_today"] > 0.0, (frame["prev_board_count"] > 0.0) & (frame["board_count"] <= 0.0)],
        [1.0, -1.0],
        default=0.0,
    )
    frame["one_day_trip_risk_proxy"] = (
        (frame["is_first_board"] > 0.0)
        & ((limit_up_count <= 3.0) | (broken_rate >= 0.50))
    ).astype(float)
    return FactorFrame(
        name="board_structure_daily_proxy",
        frame=frame[["symbol", "date", *BOARD_STRUCTURE_COLUMNS]].copy(),
        columns=BOARD_STRUCTURE_COLUMNS,
        source="local_daily_cache",
        asof_time="after_close",
        lag_rule="T day close-derived board structure; use for T+1 prediction only",
        join_keys=("symbol", "date"),
    )


def build_cross_market_return_factor(
    index_frames: Mapping[str, pd.DataFrame],
    *,
    lag_days: Mapping[str, int] | None = None,
) -> FactorFrame:
    lag_days = dict(lag_days or {})
    pieces: list[pd.DataFrame] = []
    columns: list[str] = []
    for name, raw in index_frames.items():
        if raw.empty or "date" not in raw.columns or "close" not in raw.columns:
            continue
        safe = _safe_name(name)
        frame = raw[["date", "close"]].copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.dropna(subset=["date", "close"]).sort_values("date")
        lag = max(int(lag_days.get(name, 0)), 0)
        shifted_close = frame["close"].shift(lag)
        out = pd.DataFrame({"date": frame["date"]})
        for window in (1, 3, 5):
            column = f"cross_{safe}_ret_{window}"
            out[column] = (shifted_close / shifted_close.shift(window) - 1.0) * 100.0
            columns.append(column)
        pieces.append(out)
    if not pieces:
        return FactorFrame(
            name="cross_market_returns",
            frame=pd.DataFrame(columns=["date"]),
            columns=tuple(),
            source="free_index_cache",
            asof_time="source_close_time",
            lag_rule="per-index lag_days; US/VIX/CNH should be lagged for A-share known time",
            join_keys=("date",),
        )
    merged = pieces[0]
    for piece in pieces[1:]:
        merged = merged.merge(piece, how="outer", on="date")
    return FactorFrame(
        name="cross_market_returns",
        frame=merged.sort_values("date").reset_index(drop=True),
        columns=tuple(dict.fromkeys(columns)),
        source="free_index_cache",
        asof_time="source_close_time",
        lag_rule="per-index lag_days; US/VIX/CNH should be lagged for A-share known time",
        join_keys=("date",),
    )


def _prepare_daily_board_frame(daily_bars: pd.DataFrame) -> pd.DataFrame:
    required = {"symbol", "date", "high", "low", "close", "volume"}
    missing = sorted(required - set(daily_bars.columns))
    if missing:
        raise ValueError(f"board structure factor missing columns: {missing}")
    frame = daily_bars.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.zfill(6)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).sort_values(["symbol", "date"]).reset_index(drop=True)
    for column in ("open", "high", "low", "close", "volume", "amount", "turnover"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "open" not in frame.columns:
        frame["open"] = np.nan
    grouped_symbol = frame.groupby("symbol", sort=False)
    frame["prev_close"] = grouped_symbol["close"].shift(1)
    frame["ret_pct"] = (frame["close"] / frame["prev_close"] - 1.0) * 100.0
    frame["close_position"] = (frame["close"] - frame["low"]) / (frame["high"] - frame["low"]).replace(0.0, np.nan)
    frame["limit_up_like"] = frame["ret_pct"] >= 9.5
    frame["limit_down_like"] = frame["ret_pct"] <= -9.5
    frame["touched_limit_up"] = (frame["high"] / frame["prev_close"] - 1.0) * 100.0 >= 9.5
    frame["sealed_limit_up"] = frame["limit_up_like"] & (frame["close_position"].fillna(0.0) >= 0.95)
    frame["failed_limit_up"] = frame["touched_limit_up"] & ~frame["sealed_limit_up"]
    frame["board_count"] = grouped_symbol["limit_up_like"].transform(_consecutive_true_count).astype(float)
    frame["prev_board_count"] = grouped_symbol["board_count"].shift(1).fillna(0.0).astype(float)
    frame["board_promoted_today"] = ((frame["board_count"] == frame["prev_board_count"] + 1.0) & (frame["board_count"] > 1.0)).astype(float)
    return frame


def _consecutive_true_count(values: pd.Series) -> pd.Series:
    count = 0
    out: list[float] = []
    for value in values.fillna(False).astype(bool).tolist():
        count = count + 1 if value else 0
        out.append(float(count))
    return pd.Series(out, index=values.index, dtype=float)


def _echelon_completeness(values: pd.DataFrame) -> float:
    max_height = int(values["board_count"].max() or 0)
    if max_height <= 0:
        return 0.0
    levels = set(int(level) for level in values.loc[values["board_count"] > 0.0, "board_count"].tolist())
    return len([level for level in range(1, max_height + 1) if level in levels]) / max_height


def _promotion_rate(values: pd.DataFrame, *, start_level: int | None = None, min_start_level: int | None = None) -> float:
    prev = values["prev_board_count"].astype(float)
    if start_level is not None:
        attempts = prev == float(start_level)
    elif min_start_level is not None:
        attempts = prev >= float(min_start_level)
    else:
        attempts = prev > 0.0
    denominator = int(attempts.sum())
    if denominator <= 0:
        return 0.0
    promoted = values.loc[attempts, "board_promoted_today"].astype(bool)
    return float(promoted.mean())


def _broken_board_rate(values: pd.DataFrame, *, prev_board_count: int) -> float:
    attempts = values["touched_limit_up"] & (values["prev_board_count"].astype(float) == float(prev_board_count))
    denominator = int(attempts.sum())
    if denominator <= 0:
        return 0.0
    return float(values.loc[attempts, "failed_limit_up"].mean())


def _advance_decline_ratio(values: pd.Series) -> float:
    up = float((values > 0.0).sum())
    down = float((values < 0.0).sum())
    return up / max(down, 1.0)


def _flagged_mean(values: pd.DataFrame, flag_column: str, value_column: str) -> float:
    if flag_column not in values.columns or value_column not in values.columns:
        return 0.0
    mask = values[flag_column].fillna(False).astype(bool)
    if not mask.any():
        return 0.0
    selected = pd.to_numeric(values.loc[mask, value_column], errors="coerce").dropna()
    if selected.empty:
        return 0.0
    return float(selected.mean())


def _flagged_positive_rate(values: pd.DataFrame, flag_column: str, value_column: str) -> float:
    if flag_column not in values.columns or value_column not in values.columns:
        return 0.0
    mask = values[flag_column].fillna(False).astype(bool)
    if not mask.any():
        return 0.0
    selected = pd.to_numeric(values.loc[mask, value_column], errors="coerce").dropna()
    if selected.empty:
        return 0.0
    return float((selected > 0.0).mean())


def _group_apply(grouped: pd.core.groupby.DataFrameGroupBy, func) -> pd.Series:
    try:
        return grouped.apply(func, include_groups=False)
    except TypeError:
        return grouped.apply(func)


def _emotion_phase_frame(frame: pd.DataFrame) -> pd.DataFrame:
    limit_up = pd.to_numeric(frame["market_limit_up_count"], errors="coerce").fillna(0.0)
    broken = pd.to_numeric(frame["market_broken_board_rate"], errors="coerce").fillna(0.0)
    premium = pd.to_numeric(frame["prev_limit_up_premium"], errors="coerce").fillna(0.0)
    advance_decline = pd.to_numeric(frame["market_advance_decline_ratio"], errors="coerce").fillna(1.0)
    ice = (advance_decline < 0.5) & (limit_up < 20.0) & ((broken > 0.60) | (premium < -3.0))
    trial = (limit_up >= 20.0) & (limit_up <= 40.0) & (broken >= 0.40) & (broken <= 0.60) & (premium >= -1.0) & (premium <= 1.0)
    upswing = (advance_decline > 2.0) & (limit_up >= 40.0) & (limit_up <= 80.0) & (broken < 0.30) & (premium > 3.0)
    climax = (limit_up > 80.0) & (broken < 0.20) & (premium > 5.0)
    divergence = (limit_up >= 30.0) & (limit_up <= 50.0) & (broken >= 0.40) & (broken <= 0.55) & (premium >= 0.0) & (premium <= 2.0)
    ebbing = (advance_decline < 1.0) & (limit_up < 20.0) & ((broken > 0.50) | (premium < -2.0))
    code = np.select(
        [ice, trial, upswing, climax, divergence, ebbing],
        [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        default=6.0,
    )
    return pd.DataFrame(
        {
            "emotion_phase_code": code.astype(float),
            "emotion_phase_ice": ice.astype(float),
            "emotion_phase_trial": trial.astype(float),
            "emotion_phase_upswing": upswing.astype(float),
            "emotion_phase_climax": climax.astype(float),
            "emotion_phase_divergence": divergence.astype(float),
            "emotion_phase_ebbing": ebbing.astype(float),
        },
        index=frame.index,
    )


def _market_structure_frame(frame: pd.DataFrame) -> pd.DataFrame:
    limit_up = pd.to_numeric(frame["market_limit_up_count"], errors="coerce").fillna(0.0)
    limit_down = pd.to_numeric(frame["market_limit_down_count"], errors="coerce").fillna(0.0)
    limit_down_rate = pd.to_numeric(frame["market_limit_down_rate"], errors="coerce").fillna(0.0)
    broken_rate = pd.to_numeric(frame["market_broken_board_rate"], errors="coerce").fillna(0.0)
    emotion_score = pd.to_numeric(frame["market_emotion_score"], errors="coerce").fillna(0.0)
    premium = pd.to_numeric(frame["prev_limit_up_premium"], errors="coerce").fillna(0.0)
    amount = pd.to_numeric(frame["market_active_amount_sum"], errors="coerce").fillna(0.0)
    seal_success = pd.to_numeric(frame["market_limit_seal_success_rate"], errors="coerce").fillna(0.0)
    top20_chase_return = pd.to_numeric(frame["prev_top20_chase_return"], errors="coerce").fillna(0.0)
    top20_chase_win_rate = pd.to_numeric(frame["prev_top20_chase_win_rate"], errors="coerce").fillna(0.0)
    bottom20_rebound_return = pd.to_numeric(frame["prev_bottom20_rebound_return"], errors="coerce").fillna(0.0)
    new_high = pd.to_numeric(frame["market_new_high_20_count"], errors="coerce").fillna(0.0)
    new_low = pd.to_numeric(frame["market_new_low_20_count"], errors="coerce").fillna(0.0)
    advance_decline = pd.to_numeric(frame["market_advance_decline_ratio"], errors="coerce").fillna(1.0)
    max_board = pd.to_numeric(frame["market_max_board_height"], errors="coerce").fillna(0.0)
    amount_mean_20 = amount.rolling(20, min_periods=5).mean()
    amount_max_20 = amount.rolling(20, min_periods=5).max()
    amount_pressure = (amount / amount_mean_20.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    amount_percentile_60 = amount.rolling(60, min_periods=10).apply(_last_percent_rank, raw=False).fillna(0.5)
    near_amount_high = amount >= (amount_max_20.fillna(amount) * 0.90)

    market_healthy = (emotion_score > 0.0) & (limit_up >= 20.0) & (broken_rate < 0.50)
    cycle_day_count = _consecutive_true_count(market_healthy).astype(float)
    divergence = (broken_rate >= 0.40) | (frame["emotion_phase_divergence"].astype(float) > 0.0)
    divergence_day_count = _consecutive_true_count(divergence).astype(float)
    liquidity_exhaustion = (
        (limit_down >= 10.0)
        | (limit_down_rate >= 0.02)
        | ((new_low > new_high * 1.5) & (advance_decline < 0.75))
        | (frame["emotion_phase_ebbing"].astype(float) > 0.0)
    )
    market_split = ((limit_up >= 10.0) & (limit_down >= 5.0)) | ((limit_up >= 20.0) & (broken_rate >= 0.50))
    vol_stagnation = near_amount_high & (advance_decline <= 1.2) & (limit_up < limit_up.rolling(10, min_periods=3).max().fillna(limit_up))
    quant_climax_type = np.select(
        [
            near_amount_high & (limit_up >= 40.0) & (broken_rate < 0.35) & (premium >= 0.0),
            near_amount_high & (market_split | (broken_rate >= 0.45)),
        ],
        [2.0, 1.0],
        default=0.0,
    )
    buy_sell_cycle_phase = np.select(
        [
            liquidity_exhaustion | vol_stagnation | (frame["emotion_climax_next_day_risk"].astype(float) > 0.0),
            (cycle_day_count >= 2.0) & (broken_rate < 0.40) & (premium >= 0.0),
        ],
        [-1.0, 1.0],
        default=0.0,
    )
    bull_rotation_upgrade = (
        (cycle_day_count >= 3.0)
        & (limit_up >= limit_up.rolling(5, min_periods=2).mean().fillna(limit_up))
        & (amount_pressure >= 1.0)
        & (max_board >= 2.0)
    )
    theme_capacity_score = np.clip((amount_pressure / 2.0) + (limit_up / 100.0) + (max_board / 10.0), 0.0, 3.0)
    prior_decline = (
        (emotion_score.shift(1).rolling(3, min_periods=1).sum().fillna(0.0) < 0.0)
        | (advance_decline.shift(1).rolling(3, min_periods=1).mean().fillna(1.0) < 0.80)
    )
    limit_up_recovering = limit_up >= limit_up.shift(1).fillna(limit_up)
    new_low_contracting = new_low <= new_low.shift(1).fillna(new_low)
    volume_is_king = (
        (amount_pressure >= 1.10)
        & (amount_percentile_60 >= 0.60)
        & (limit_up >= 20.0)
        & (broken_rate < 0.50)
        & (advance_decline >= 1.0)
    )
    ground_volume_risk = (amount_percentile_60 <= 0.20) & (limit_up < 20.0) & (advance_decline < 1.0)
    seal_rate_80_threshold = (seal_success >= 0.80) & (limit_up >= 10.0)
    strong_market_regime = (
        (advance_decline >= 1.50)
        & (limit_up >= 30.0)
        & (broken_rate <= 0.35)
        & (amount_pressure >= 1.0)
    )
    weak_market_oversold_regime = (
        (advance_decline <= 0.75)
        & ((limit_down >= 5.0) | (new_low > new_high))
        & ((broken_rate >= 0.45) | (premium <= -2.0) | (amount_percentile_60 <= 0.35))
    )
    collapse_warning_signal = (
        ((top20_chase_return <= -2.0) | (top20_chase_win_rate <= 0.40))
        & (bottom20_rebound_return <= 0.0)
        & ((advance_decline < 1.0) | (limit_down >= 5.0) | (broken_rate >= 0.45))
    )
    bull_hotspot_bear_oversold = strong_market_regime.astype(float) - weak_market_oversold_regime.astype(float)
    post_decline_transition = (
        prior_decline
        & (amount_pressure >= 1.0)
        & (advance_decline >= 1.20)
        & limit_up_recovering
        & (broken_rate <= 0.50)
    )
    decline_stabilize_signal = (
        prior_decline
        & new_low_contracting
        & (limit_down <= limit_down.shift(1).fillna(limit_down))
        & (advance_decline >= 0.80)
        & (premium >= -3.0)
    )
    weekday = pd.to_datetime(frame["date"], errors="coerce").dt.dayofweek if "date" in frame.columns else pd.Series(0, index=frame.index)
    weak_friday_risk = (
        (weekday == 4)
        & (advance_decline < 1.0)
        & (limit_up < 30.0)
        & ((broken_rate >= 0.45) | (premium < 0.0) | ground_volume_risk)
    )
    return pd.DataFrame(
        {
            "cycle_day_count": cycle_day_count.to_numpy(dtype=float),
            "divergence_day_count": divergence_day_count.to_numpy(dtype=float),
            "buy_sell_cycle_phase": buy_sell_cycle_phase.astype(float),
            "liquidity_exhaustion_signal": liquidity_exhaustion.astype(float),
            "market_split_signal": market_split.astype(float),
            "quant_climax_type": quant_climax_type.astype(float),
            "vol_stagnation_signal": vol_stagnation.astype(float),
            "bull_rotation_upgrade": bull_rotation_upgrade.astype(float),
            "theme_capacity_score": theme_capacity_score.astype(float),
            "market_amount_ratio_20": amount_pressure.astype(float),
            "market_amount_percentile_60": amount_percentile_60.astype(float),
            "volume_is_king_signal": volume_is_king.astype(float),
            "ground_volume_risk": ground_volume_risk.astype(float),
            "post_decline_transition": post_decline_transition.astype(float),
            "decline_stabilize_signal": decline_stabilize_signal.astype(float),
            "weak_friday_risk": weak_friday_risk.astype(float),
            "seal_rate_80_threshold": seal_rate_80_threshold.astype(float),
            "strong_market_regime": strong_market_regime.astype(float),
            "weak_market_oversold_regime": weak_market_oversold_regime.astype(float),
            "bull_hotspot_bear_oversold": bull_hotspot_bear_oversold.astype(float),
            "collapse_warning_signal": collapse_warning_signal.astype(float),
        },
        index=frame.index,
    )


def _last_percent_rank(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return 0.5
    return float((clean <= clean.iloc[-1]).mean())


def _safe_name(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_")
