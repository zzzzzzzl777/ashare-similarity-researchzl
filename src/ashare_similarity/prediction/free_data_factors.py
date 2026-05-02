from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from ashare_similarity.prediction.factor_cache_manager import FactorFrame


def _limit_threshold_for_symbol(symbol: str) -> float:
    """Daily price-limit percentage by exchange board (same logic as factor_builder._limit_threshold_pct)."""
    s = str(symbol).strip().zfill(6)
    if s.startswith(("300", "301", "688")):
        return 20.0
    if s.startswith(("8", "4", "920")):
        return 30.0
    return 10.0


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
    "market_high_leader_crash_count",
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
    "same_height_success_rate_1",
    "same_height_success_rate_2",
    "same_height_success_rate_3plus",
    "same_height_failure_pressure",
    "prev_limit_up_premium",
    "prev_board_premium",
    "prev_failed_limit_up_count",
    "prev_failed_limit_up_return",
    "prev_failed_limit_up_red_rate",
    "prev_failed_limit_up_loss_rate",
    "failed_limit_up_loss_pressure",
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
    "bullish_pivot_recognition",
    "limit_premium_failure_signal",
    "bad_sentiment_no_sweep",
    "high_leader_crash_sentiment_collapse",
    "no_theme_rotation_mode",
    "money_effect_sector_rotation",
    "full_position_trigger",
    "late_cycle_position_cap",
    "bear_position_reduction",
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
    _limit_pct = frame["symbol"].map(_limit_threshold_for_symbol)
    _limit_thresh = _limit_pct - 0.5
    frame["limit_up_like"] = frame["ret_pct"] >= _limit_thresh
    frame["limit_down_like"] = frame["ret_pct"] <= -_limit_thresh
    frame["touched_limit_up"] = (frame["high"] / frame["prev_close"] - 1.0) * 100.0 >= _limit_thresh
    frame["sealed_limit_up"] = frame["limit_up_like"] & (frame["close_position"].fillna(0.0) >= 0.95)
    frame["one_word_board_like"] = frame["limit_up_like"] & (((frame["low"] / frame["prev_close"] - 1.0) * 100.0) >= (_limit_pct - 1.0))
    frame["failed_limit_up"] = frame["touched_limit_up"] & ~frame["sealed_limit_up"]
    frame["new_high_20"] = frame["close"] >= frame["high_20"]
    frame["new_low_20"] = frame["close"] <= frame["low_20"]
    frame["board_count"] = frame.groupby("symbol", sort=False)["limit_up_like"].transform(_consecutive_true_count)
    frame["prev_board_count"] = frame.groupby("symbol", sort=False)["board_count"].shift(1).fillna(0.0)
    frame["board_promoted_today"] = (frame["board_count"] == frame["prev_board_count"] + 1.0) & (frame["board_count"] > 1.0)
    frame["high_leader_crash"] = (frame["prev_board_count"] >= 3.0) & (frame["ret_pct"] <= -7.0)
    frame["prev_limit_up_flag"] = frame.groupby("symbol", sort=False)["limit_up_like"].shift(1).eq(True)
    frame["prev_board_flag"] = frame.groupby("symbol", sort=False)["board_count"].shift(1).fillna(0.0) >= 2.0
    frame["prev_failed_limit_up_flag"] = frame.groupby("symbol", sort=False)["failed_limit_up"].shift(1).eq(True)
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
    prev_failed_count = grouped["prev_failed_limit_up_flag"].sum().astype(float)
    prev_failed_return = _group_apply(grouped, lambda values: _flagged_mean(values, "prev_failed_limit_up_flag", "ret_pct"))
    prev_failed_red_rate = _group_apply(grouped, lambda values: _flagged_positive_rate(values, "prev_failed_limit_up_flag", "ret_pct"))
    prev_failed_loss_rate = _group_apply(
        grouped,
        lambda values: _flagged_rate(values, "prev_failed_limit_up_flag", "ret_pct", threshold=0.0, op="<"),
    )
    same_height_1 = _group_apply(grouped, lambda values: _promotion_rate(values, start_level=1)).astype(float)
    same_height_2 = _group_apply(grouped, lambda values: _promotion_rate(values, start_level=2)).astype(float)
    same_height_3plus = _group_apply(grouped, lambda values: _promotion_rate(values, min_start_level=3)).astype(float)
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
            "market_high_leader_crash_count": grouped["high_leader_crash"].sum().astype(float).to_numpy(),
            "market_emotion_score": emotion_score.to_numpy(),
            "market_advance_decline_ratio": grouped["ret_pct"].apply(_advance_decline_ratio).astype(float).to_numpy(),
            "market_new_high_20_count": grouped["new_high_20"].sum().astype(float).to_numpy(),
            "market_new_low_20_count": grouped["new_low_20"].sum().astype(float).to_numpy(),
            "market_active_turnover_mean": grouped["turnover"].mean().fillna(0.0).astype(float).to_numpy(),
            "market_active_amount_sum": grouped["amount"].sum().fillna(0.0).astype(float).to_numpy(),
            "market_max_board_height": max_board_height.to_numpy(),
            "market_echelon_completeness": _group_apply(grouped, _echelon_completeness).astype(float).to_numpy(),
            "market_board_promotion_rate": _group_apply(grouped, _promotion_rate).astype(float).to_numpy(),
            "market_board_promotion_rate_1to2": same_height_1.to_numpy(),
            "market_board_promotion_rate_2to3": same_height_2.to_numpy(),
            "market_board_promotion_rate_high": same_height_3plus.to_numpy(),
            "same_height_success_rate_1": same_height_1.to_numpy(),
            "same_height_success_rate_2": same_height_2.to_numpy(),
            "same_height_success_rate_3plus": same_height_3plus.to_numpy(),
            "same_height_failure_pressure": (
                (1.0 - (same_height_1.fillna(0.0) + same_height_2.fillna(0.0) + same_height_3plus.fillna(0.0)) / 3.0)
                * np.log1p(touched_count.fillna(0.0))
            ).astype(float).to_numpy(),
            "prev_limit_up_premium": premium.fillna(0.0).astype(float).to_numpy(),
            "prev_board_premium": board_premium.fillna(0.0).astype(float).to_numpy(),
            "prev_failed_limit_up_count": prev_failed_count.to_numpy(),
            "prev_failed_limit_up_return": prev_failed_return.fillna(0.0).astype(float).to_numpy(),
            "prev_failed_limit_up_red_rate": prev_failed_red_rate.fillna(0.0).astype(float).to_numpy(),
            "prev_failed_limit_up_loss_rate": prev_failed_loss_rate.fillna(0.0).astype(float).to_numpy(),
            "failed_limit_up_loss_pressure": (
                prev_failed_loss_rate.fillna(0.0).astype(float)
                * np.log1p(prev_failed_count.fillna(0.0).astype(float))
                * np.maximum(-prev_failed_return.fillna(0.0).astype(float), 0.0)
            ).to_numpy(),
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
    _foreign_keywords = ("us", "sp500", "spx", "nasdaq", "vix", "cnh", "usd", "hsi", "hang_seng", "a50", "ftse", "nikkei", "dax")
    for name, raw in index_frames.items():
        if raw.empty or "date" not in raw.columns or "close" not in raw.columns:
            continue
        safe = _safe_name(name)
        frame = raw[["date", "close"]].copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.dropna(subset=["date", "close"]).sort_values("date")
        default_lag = 1 if any(kw in name.lower() for kw in _foreign_keywords) else 0
        lag = max(int(lag_days.get(name, default_lag)), 0)
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
    _limit_pct = frame["symbol"].map(_limit_threshold_for_symbol)
    _limit_thresh = _limit_pct - 0.5
    frame["limit_up_like"] = frame["ret_pct"] >= _limit_thresh
    frame["limit_down_like"] = frame["ret_pct"] <= -_limit_thresh
    frame["touched_limit_up"] = (frame["high"] / frame["prev_close"] - 1.0) * 100.0 >= _limit_thresh
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


def _flagged_rate(
    values: pd.DataFrame,
    flag_column: str,
    value_column: str,
    *,
    threshold: float,
    op: str,
) -> float:
    if flag_column not in values.columns or value_column not in values.columns:
        return 0.0
    mask = values[flag_column].fillna(False).astype(bool)
    if not mask.any():
        return 0.0
    selected = pd.to_numeric(values.loc[mask, value_column], errors="coerce").dropna()
    if selected.empty:
        return 0.0
    if op == "<":
        return float((selected < float(threshold)).mean())
    if op == ">":
        return float((selected > float(threshold)).mean())
    raise ValueError("op must be '<' or '>'")


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
            "emotion_phase_ice": (code == 0.0).astype(float),
            "emotion_phase_trial": (code == 1.0).astype(float),
            "emotion_phase_upswing": (code == 2.0).astype(float),
            "emotion_phase_climax": (code == 3.0).astype(float),
            "emotion_phase_divergence": (code == 4.0).astype(float),
            "emotion_phase_ebbing": (code == 5.0).astype(float),
        },
        index=frame.index,
    )


def _market_structure_frame(frame: pd.DataFrame) -> pd.DataFrame:
    limit_up = pd.to_numeric(frame["market_limit_up_count"], errors="coerce").fillna(0.0)
    limit_down = pd.to_numeric(frame["market_limit_down_count"], errors="coerce").fillna(0.0)
    limit_down_rate = pd.to_numeric(frame["market_limit_down_rate"], errors="coerce").fillna(0.0)
    broken_rate = pd.to_numeric(frame["market_broken_board_rate"], errors="coerce").fillna(0.0)
    leader_crash = pd.to_numeric(frame["market_high_leader_crash_count"], errors="coerce").fillna(0.0)
    emotion_score = pd.to_numeric(frame["market_emotion_score"], errors="coerce").fillna(0.0)
    premium = pd.to_numeric(frame["prev_limit_up_premium"], errors="coerce").fillna(0.0)
    amount = pd.to_numeric(frame["market_active_amount_sum"], errors="coerce").fillna(0.0)
    seal_success = pd.to_numeric(frame["market_limit_seal_success_rate"], errors="coerce").fillna(0.0)
    top20_chase_return = pd.to_numeric(frame["prev_top20_chase_return"], errors="coerce").fillna(0.0)
    top20_chase_win_rate = pd.to_numeric(frame["prev_top20_chase_win_rate"], errors="coerce").fillna(0.0)
    bottom20_rebound_return = pd.to_numeric(frame["prev_bottom20_rebound_return"], errors="coerce").fillna(0.0)
    money_effect_spread_20 = pd.to_numeric(frame["money_effect_spread_20"], errors="coerce").fillna(0.0)
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
    bullish_pivot_recognition = (
        prior_decline
        & (amount_pressure >= 1.0)
        & (advance_decline >= 1.10)
        & limit_up_recovering
        & new_low_contracting
        & (max_board >= 2.0)
        & (broken_rate <= 0.50)
    )
    limit_premium_failure_signal = (
        (advance_decline >= 1.05)
        & (limit_up >= 10.0)
        & (premium <= 0.0)
        & ((top20_chase_return <= 0.0) | (top20_chase_win_rate <= 0.45))
    )
    bad_sentiment_no_sweep = (
        ((frame["emotion_phase_ebbing"].astype(float) > 0.0) | (broken_rate >= 0.50) | (premium < -2.0))
        & (limit_up < 40.0)
        & (advance_decline < 1.20)
    )
    high_leader_crash_sentiment_collapse = (leader_crash > 0.0) & (
        (broken_rate >= 0.35) | (premium < 0.0) | (advance_decline < 1.0)
    )
    no_theme_rotation_mode = (
        (limit_up >= 8.0)
        & (limit_up <= 35.0)
        & (broken_rate < 0.55)
        & (advance_decline >= 0.80)
        & (advance_decline <= 1.50)
        & (max_board <= 3.0)
    )
    money_effect_sector_rotation = (
        no_theme_rotation_mode
        & (money_effect_spread_20 > 0.0)
        & (top20_chase_win_rate >= 0.50)
        & (amount_pressure >= 0.80)
    )
    full_position_trigger = (
        (advance_decline >= 1.50)
        & (limit_up >= 40.0)
        & (broken_rate <= 0.35)
        & (amount_pressure >= 1.05)
        & (max_board >= 2.0)
        & (premium >= 0.0)
    )
    late_cycle_position_cap = (
        ((max_board >= 4.0) & (premium >= 3.0))
        | (frame["emotion_climax_next_day_risk"].astype(float) > 0.0)
        | ((amount_percentile_60 >= 0.80) & (broken_rate >= 0.45))
    )
    bear_position_reduction = weak_market_oversold_regime | liquidity_exhaustion | high_leader_crash_sentiment_collapse
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
            "bullish_pivot_recognition": bullish_pivot_recognition.astype(float),
            "limit_premium_failure_signal": limit_premium_failure_signal.astype(float),
            "bad_sentiment_no_sweep": bad_sentiment_no_sweep.astype(float),
            "high_leader_crash_sentiment_collapse": high_leader_crash_sentiment_collapse.astype(float),
            "no_theme_rotation_mode": no_theme_rotation_mode.astype(float),
            "money_effect_sector_rotation": money_effect_sector_rotation.astype(float),
            "full_position_trigger": full_position_trigger.astype(float),
            "late_cycle_position_cap": late_cycle_position_cap.astype(float),
            "bear_position_reduction": bear_position_reduction.astype(float),
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


# ---------------------------------------------------------------------------
# Tushare factors (research-only)
# ---------------------------------------------------------------------------

import os
from pathlib import Path

TUSHARE_FACTOR_COLUMNS: tuple[str, ...] = (
    # moneyflow
    "tushare_net_mf_amount",
    "tushare_lg_buy_sell_ratio",
    "tushare_elg_buy_sell_ratio",
    "tushare_mf_strength",
    "tushare_sm_sell_pressure",
    # limit_list_d (sparse: ~2% coverage)
    "tushare_seal_ratio",
    "tushare_open_times",
    "tushare_first_time_minutes",
    "tushare_up_stat_days",
    "tushare_limit_type",
    "tushare_limit_turnover",
    # top_list + top_inst (sparse: ~2% coverage)
    "tushare_lhb_net_buy",
    "tushare_lhb_net_rate",
    "tushare_lhb_appeared",
    "tushare_inst_buy_count",
    "tushare_inst_net_buy",
    # hk_hold (~17% coverage)
    "tushare_hk_ratio",
    "tushare_hk_ratio_delta_1d",
    # margin_detail (~36% coverage)
    "tushare_rzye",
    "tushare_rzye_delta_pct",
    "tushare_rzmre_ratio",
    "tushare_margin_net",
    "tushare_rqye_ratio",
    # ths_hot (~25% coverage)
    "tushare_hot_rank",
    "tushare_hot_value",
    # daily_basic (high coverage)
    "tushare_volume_ratio",
    "tushare_free_share",
    # cyq_perf (~55% coverage)
    "tushare_winner_rate",
    "tushare_cost_concentration",
    "tushare_cost_position",
    # stk_auction_o + stk_auction_c (high coverage)
    "tushare_auction_open_vwap_ratio",
    "tushare_auction_open_vol",
    "tushare_auction_close_vwap_ratio",
    "tushare_auction_close_vol",
    # stk_holdernumber (quarterly, ~high coverage)
    "tushare_holder_num",
    "tushare_holder_num_delta_pct",
    # stk_limit (high coverage)
    "tushare_up_limit_distance",
    "tushare_down_limit_distance",
    "tushare_limit_range",
    # stk_mins_5 (5min bars, coverage depends on pull progress)
    "tushare_last_30min_return",
    "tushare_first_15min_volume_ratio",
    "tushare_vwap_deviation",
    "tushare_intraday_volatility",
    "tushare_up_volume_ratio",
    "tushare_high_time_pct",
    "tushare_close_vs_vwap",
)


def _load_tushare_daily_parquets(
    api_dir: str | Path,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    api_dir = Path(api_dir)
    if not api_dir.is_dir():
        return pd.DataFrame()
    files = sorted(api_dir.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    dfs = [pd.read_parquet(f, columns=columns) for f in files]
    return pd.concat(dfs, ignore_index=True)


def _load_tushare_stock_parquets(
    api_dir: str | Path,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    api_dir = Path(api_dir)
    if not api_dir.is_dir():
        return pd.DataFrame()
    files = sorted(api_dir.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    dfs = [pd.read_parquet(f) for f in files]
    return pd.concat(dfs, ignore_index=True)


def _ts_code_to_symbol(ts_code: pd.Series) -> pd.Series:
    return ts_code.astype(str).str.split(".").str[0].str.zfill(6)


def _trade_date_to_date(trade_date: pd.Series) -> pd.Series:
    return pd.to_datetime(trade_date.astype(str), format="%Y%m%d", errors="coerce")


def _parse_first_time_minutes(series: pd.Series) -> pd.Series:
    def _parse(t):
        if pd.isna(t) or t is None or str(t).strip() in ("", "None", "nan"):
            return float("nan")
        s = str(t).strip().zfill(6)
        try:
            return int(s[:2]) * 60 + int(s[2:4]) + int(s[4:6]) / 60.0
        except (ValueError, IndexError):
            return float("nan")
    return series.map(_parse)


def _parse_up_stat_days(series: pd.Series) -> pd.Series:
    def _parse(s):
        if pd.isna(s):
            return 0.0
        s = str(s).strip()
        if "/" not in s:
            return 0.0
        try:
            return float(s.split("/")[0])
        except (ValueError, IndexError):
            return 0.0
    return series.map(_parse)


def _build_moneyflow_factors(tushare_dir: Path) -> pd.DataFrame:
    df = _load_tushare_daily_parquets(tushare_dir / "moneyflow")
    if df.empty:
        return pd.DataFrame()
    df["symbol"] = _ts_code_to_symbol(df["ts_code"])
    df["date"] = _trade_date_to_date(df["trade_date"])
    for col in ("net_mf_amount", "buy_lg_amount", "sell_lg_amount",
                "buy_elg_amount", "sell_elg_amount", "buy_sm_amount", "sell_sm_amount"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0.0)
    big_buy = df["buy_lg_amount"] + df["buy_elg_amount"]
    big_sell = df["sell_lg_amount"] + df["sell_elg_amount"]
    out = pd.DataFrame({
        "symbol": df["symbol"],
        "date": df["date"],
        "tushare_net_mf_amount": df["net_mf_amount"],
        "tushare_lg_buy_sell_ratio": (df["buy_lg_amount"] / np.maximum(df["sell_lg_amount"], 100.0)).clip(upper=50.0),
        "tushare_elg_buy_sell_ratio": (df["buy_elg_amount"] / np.maximum(df["sell_elg_amount"], 100.0)).clip(upper=50.0),
        "tushare_mf_strength": (big_buy - big_sell) / np.maximum(big_buy + big_sell, 1.0),
        "tushare_sm_sell_pressure": df["sell_sm_amount"] / np.maximum(df["buy_sm_amount"] + df["sell_sm_amount"], 1.0),
    })
    return out.dropna(subset=["date"])


def _build_limit_factors(tushare_dir: Path) -> pd.DataFrame:
    df = _load_tushare_daily_parquets(tushare_dir / "limit_list_d")
    if df.empty:
        return pd.DataFrame()
    df["symbol"] = _ts_code_to_symbol(df["ts_code"])
    df["date"] = _trade_date_to_date(df["trade_date"])
    for col in ("fd_amount", "float_mv", "amount", "open_times"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    limit_enc = df.get("limit", pd.Series(dtype=str)).map({"U": 1.0, "D": -1.0, "Z": 0.0}).fillna(0.0)
    out = pd.DataFrame({
        "symbol": df["symbol"],
        "date": df["date"],
        "tushare_seal_ratio": df["fd_amount"] / np.maximum(df["float_mv"], 1.0),
        "tushare_open_times": df["open_times"].fillna(0.0),
        "tushare_first_time_minutes": _parse_first_time_minutes(df.get("first_time", pd.Series(dtype=str))),
        "tushare_up_stat_days": _parse_up_stat_days(df.get("up_stat", pd.Series(dtype=str))),
        "tushare_limit_type": limit_enc,
        "tushare_limit_turnover": df["amount"] / np.maximum(df["float_mv"], 1.0),
    })
    return out.dropna(subset=["date"])


def _build_lhb_factors(tushare_dir: Path) -> pd.DataFrame:
    top = _load_tushare_daily_parquets(tushare_dir / "top_list")
    inst = _load_tushare_daily_parquets(tushare_dir / "top_inst")
    if top.empty:
        return pd.DataFrame()
    top["symbol"] = _ts_code_to_symbol(top["ts_code"])
    top["date"] = _trade_date_to_date(top["trade_date"])
    for col in ("l_buy", "l_sell", "net_rate"):
        top[col] = pd.to_numeric(top.get(col), errors="coerce").fillna(0.0)
    out = pd.DataFrame({
        "symbol": top["symbol"],
        "date": top["date"],
        "tushare_lhb_net_buy": top["l_buy"] - top["l_sell"],
        "tushare_lhb_net_rate": top.get("net_rate", 0.0),
        "tushare_lhb_appeared": 1.0,
    })
    if not inst.empty:
        inst["symbol"] = _ts_code_to_symbol(inst["ts_code"])
        inst["date"] = _trade_date_to_date(inst["trade_date"])
        inst["net_buy"] = pd.to_numeric(inst.get("net_buy"), errors="coerce").fillna(0.0)
        inst["side"] = pd.to_numeric(inst.get("side"), errors="coerce").fillna(0.0)
        buy_side = inst[inst["side"] == 0.0]
        if not buy_side.empty:
            agg = buy_side.groupby(["symbol", "date"], sort=False).agg(
                tushare_inst_buy_count=("net_buy", "count"),
                tushare_inst_net_buy=("net_buy", "sum"),
            ).reset_index()
            out = out.merge(agg, on=["symbol", "date"], how="left")
    if "tushare_inst_buy_count" not in out.columns:
        out["tushare_inst_buy_count"] = 0.0
    if "tushare_inst_net_buy" not in out.columns:
        out["tushare_inst_net_buy"] = 0.0
    return out.dropna(subset=["date"])


def _build_hk_hold_factors(tushare_dir: Path) -> pd.DataFrame:
    df = _load_tushare_daily_parquets(tushare_dir / "hk_hold")
    if df.empty:
        return pd.DataFrame()
    df["symbol"] = _ts_code_to_symbol(df["ts_code"])
    df["date"] = _trade_date_to_date(df["trade_date"])
    df["ratio"] = pd.to_numeric(df.get("ratio"), errors="coerce")
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    df["tushare_hk_ratio_delta_1d"] = df.groupby("symbol", sort=False)["ratio"].diff()
    out = pd.DataFrame({
        "symbol": df["symbol"],
        "date": df["date"],
        "tushare_hk_ratio": df["ratio"],
        "tushare_hk_ratio_delta_1d": df["tushare_hk_ratio_delta_1d"],
    })
    return out.dropna(subset=["date"])


def _build_margin_factors(tushare_dir: Path) -> pd.DataFrame:
    df = _load_tushare_daily_parquets(tushare_dir / "margin_detail")
    if df.empty:
        return pd.DataFrame()
    df["symbol"] = _ts_code_to_symbol(df["ts_code"])
    df["date"] = _trade_date_to_date(df["trade_date"])
    for col in ("rzye", "rzmre", "rzche", "rqye", "rzrqye"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0.0)
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    prev_rzye = df.groupby("symbol", sort=False)["rzye"].shift(1)
    out = pd.DataFrame({
        "symbol": df["symbol"],
        "date": df["date"],
        "tushare_rzye": df["rzye"],
        "tushare_rzye_delta_pct": ((df["rzye"] - prev_rzye) / np.maximum(prev_rzye.abs(), 1.0)) * 100.0,
        "tushare_rzmre_ratio": df["rzmre"] / np.maximum(df["rzye"], 1.0),
        "tushare_margin_net": df["rzmre"] - df["rzche"],
        "tushare_rqye_ratio": df["rqye"] / np.maximum(df["rzrqye"], 1.0),
    })
    return out.dropna(subset=["date"])


def _build_ths_hot_factors(tushare_dir: Path) -> pd.DataFrame:
    df = _load_tushare_daily_parquets(tushare_dir / "ths_hot")
    if df.empty:
        return pd.DataFrame()
    df["symbol"] = _ts_code_to_symbol(df["ts_code"])
    df["date"] = _trade_date_to_date(df["trade_date"])
    df["rank"] = pd.to_numeric(df.get("rank"), errors="coerce")
    df["hot"] = pd.to_numeric(df.get("hot"), errors="coerce")
    out = df.groupby(["symbol", "date"], sort=False).agg(
        tushare_hot_rank=("rank", "min"),
        tushare_hot_value=("hot", "max"),
    ).reset_index()
    return out.dropna(subset=["date"])


def _build_daily_basic_factors(tushare_dir: Path) -> pd.DataFrame:
    df = _load_tushare_daily_parquets(tushare_dir / "daily_basic")
    if df.empty:
        return pd.DataFrame()
    df["symbol"] = _ts_code_to_symbol(df["ts_code"])
    df["date"] = _trade_date_to_date(df["trade_date"])
    out = pd.DataFrame({
        "symbol": df["symbol"],
        "date": df["date"],
        "tushare_volume_ratio": pd.to_numeric(df.get("volume_ratio"), errors="coerce"),
        "tushare_free_share": pd.to_numeric(df.get("free_share"), errors="coerce"),
    })
    return out.dropna(subset=["date"])


def _build_cyq_factors(tushare_dir: Path) -> pd.DataFrame:
    df = _load_tushare_stock_parquets(tushare_dir / "cyq_perf")
    if df.empty:
        return pd.DataFrame()
    df["symbol"] = _ts_code_to_symbol(df["ts_code"])
    df["date"] = _trade_date_to_date(df["trade_date"])
    for col in ("winner_rate", "cost_85pct", "cost_15pct", "cost_50pct"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    close = pd.to_numeric(df.get("weight_avg"), errors="coerce")
    out = pd.DataFrame({
        "symbol": df["symbol"],
        "date": df["date"],
        "tushare_winner_rate": df["winner_rate"],
        "tushare_cost_concentration": df["cost_85pct"] / np.maximum(df["cost_15pct"], 0.01),
        "tushare_cost_position": (close - df["cost_50pct"]) / np.maximum(df["cost_50pct"].abs(), 0.01),
    })
    return out.dropna(subset=["date"])


def _build_auction_factors(tushare_dir: Path) -> pd.DataFrame:
    ao = _load_tushare_daily_parquets(
        tushare_dir / "stk_auction_o",
        columns=["ts_code", "trade_date", "vwap", "vol", "close"],
    )
    ac = _load_tushare_daily_parquets(
        tushare_dir / "stk_auction_c",
        columns=["ts_code", "trade_date", "vwap", "vol", "close"],
    )
    pieces = []
    if not ao.empty:
        ao["symbol"] = _ts_code_to_symbol(ao["ts_code"])
        ao["date"] = _trade_date_to_date(ao["trade_date"])
        ao["vwap"] = pd.to_numeric(ao["vwap"], errors="coerce")
        ao["vol"] = pd.to_numeric(ao["vol"], errors="coerce")
        ao["close"] = pd.to_numeric(ao["close"], errors="coerce")
        pieces.append(pd.DataFrame({
            "symbol": ao["symbol"],
            "date": ao["date"],
            "tushare_auction_open_vwap_ratio": ao["vwap"] / ao["close"].clip(lower=0.01),
            "tushare_auction_open_vol": ao["vol"],
        }))
    if not ac.empty:
        ac["symbol"] = _ts_code_to_symbol(ac["ts_code"])
        ac["date"] = _trade_date_to_date(ac["trade_date"])
        ac["vwap"] = pd.to_numeric(ac["vwap"], errors="coerce")
        ac["vol"] = pd.to_numeric(ac["vol"], errors="coerce")
        ac["close"] = pd.to_numeric(ac["close"], errors="coerce")
        pieces.append(pd.DataFrame({
            "symbol": ac["symbol"],
            "date": ac["date"],
            "tushare_auction_close_vwap_ratio": ac["vwap"] / ac["close"].clip(lower=0.01),
            "tushare_auction_close_vol": ac["vol"],
        }))
    if not pieces:
        return pd.DataFrame()
    merged = pieces[0]
    for p in pieces[1:]:
        merged = merged.merge(p, on=["symbol", "date"], how="outer")
    return merged.dropna(subset=["date"])


def _build_holdernumber_factors(tushare_dir: Path) -> pd.DataFrame:
    df = _load_tushare_daily_parquets(
        tushare_dir / "stk_holdernumber",
        columns=["ts_code", "end_date", "holder_num"],
    )
    if df.empty:
        return pd.DataFrame()
    # stk_holdernumber: same end_date appears across multiple trade_date parquets
    df = df.drop_duplicates(subset=["ts_code", "end_date"], keep="last")
    df["symbol"] = _ts_code_to_symbol(df["ts_code"])
    df["date"] = _trade_date_to_date(df["end_date"])
    df["holder_num"] = pd.to_numeric(df["holder_num"], errors="coerce")
    df = df.sort_values(["symbol", "date"])
    df["prev_holder_num"] = df.groupby("symbol")["holder_num"].shift(1)
    out = pd.DataFrame({
        "symbol": df["symbol"],
        "date": df["date"],
        "tushare_holder_num": df["holder_num"],
        "tushare_holder_num_delta_pct": (
            (df["holder_num"] - df["prev_holder_num"])
            / df["prev_holder_num"].clip(lower=1)
        ),
    })
    return out.dropna(subset=["date"])


def _build_stk_limit_factors(tushare_dir: Path) -> pd.DataFrame:
    df = _load_tushare_daily_parquets(
        tushare_dir / "stk_limit",
        columns=["ts_code", "trade_date", "up_limit", "down_limit"],
    )
    if df.empty:
        return pd.DataFrame()
    df["symbol"] = _ts_code_to_symbol(df["ts_code"])
    df["date"] = _trade_date_to_date(df["trade_date"])
    df["up_limit"] = pd.to_numeric(df["up_limit"], errors="coerce")
    df["down_limit"] = pd.to_numeric(df["down_limit"], errors="coerce")
    implied_close = (df["up_limit"] + df["down_limit"]) / 2
    out = pd.DataFrame({
        "symbol": df["symbol"],
        "date": df["date"],
        "tushare_up_limit_distance": (df["up_limit"] - implied_close) / implied_close.clip(lower=0.01),
        "tushare_down_limit_distance": (implied_close - df["down_limit"]) / implied_close.clip(lower=0.01),
        "tushare_limit_range": (df["up_limit"] - df["down_limit"]) / implied_close.clip(lower=0.01),
    })
    return out.dropna(subset=["date"])


def _build_stk_mins_factors(tushare_dir: Path) -> pd.DataFrame:
    import datetime as _dt
    mins_dir = tushare_dir / "stk_mins_5"
    if not mins_dir.is_dir():
        return pd.DataFrame()
    files = sorted(mins_dir.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    chunks: list[pd.DataFrame] = []
    for f in files:
        try:
            chunk = pd.read_parquet(f)
        except Exception:
            continue
        if chunk.empty:
            continue
        chunks.append(chunk)
    if not chunks:
        return pd.DataFrame()
    bars = pd.concat(chunks, ignore_index=True)
    bars["trade_time"] = pd.to_datetime(bars["trade_time"], errors="coerce")
    for col in ("close", "open", "high", "low", "vol", "amount"):
        bars[col] = pd.to_numeric(bars.get(col), errors="coerce")
    bars["symbol"] = bars["ts_code"].astype(str).str.split(".").str[0].str.zfill(6)
    bars["trade_date"] = bars["trade_time"].dt.date
    bars["time"] = bars["trade_time"].dt.time
    bars = bars.dropna(subset=["trade_date", "close"]).sort_values(["symbol", "trade_date", "trade_time"])

    t_1430 = _dt.time(14, 30)
    t_0945 = _dt.time(9, 45)

    gk = ["symbol", "trade_date"]
    grouped = bars.groupby(gk, sort=False)
    day_stats = grouped.agg(
        bar_count=("close", "size"),
        day_vol=("vol", "sum"),
        day_amount=("amount", "sum"),
        eod_close=("close", "last"),
    ).reset_index()
    day_stats = day_stats[(day_stats["bar_count"] >= 5) & (day_stats["day_vol"] > 0)].copy()
    day_stats["vwap"] = day_stats["day_amount"] / day_stats["day_vol"]

    last30 = bars[bars["time"] >= t_1430].groupby(gk, sort=False).agg(
        l30_open=("open", "first"),
        l30_close=("close", "last"),
        l30_count=("close", "size"),
    ).reset_index()
    last30["tushare_last_30min_return"] = np.where(
        last30["l30_count"] >= 2, last30["l30_close"] / last30["l30_open"] - 1, np.nan
    )

    first15 = bars[bars["time"] <= t_0945].groupby(gk, sort=False).agg(
        f15_vol=("vol", "sum"),
    ).reset_index()

    up_bars = bars[bars["close"] > bars["open"]].groupby(gk, sort=False).agg(
        up_vol=("vol", "sum"),
    ).reset_index()

    bars["_bar_pos"] = grouped.cumcount()
    high_rows = bars.loc[bars.groupby(gk, sort=False)["high"].idxmax(), gk + ["_bar_pos"]].copy()
    high_rows.rename(columns={"_bar_pos": "high_pos"}, inplace=True)

    bars["_ret"] = grouped["close"].pct_change()
    vol_stats = bars.groupby(gk, sort=False)["_ret"].std().reset_index()
    vol_stats.rename(columns={"_ret": "tushare_intraday_volatility"}, inplace=True)

    result = day_stats.merge(last30[gk + ["tushare_last_30min_return"]], on=gk, how="left")
    result = result.merge(first15, on=gk, how="left")
    result["tushare_first_15min_volume_ratio"] = result["f15_vol"] / result["day_vol"]
    result = result.merge(up_bars, on=gk, how="left")
    result["tushare_up_volume_ratio"] = result["up_vol"].fillna(0) / result["day_vol"]
    result = result.merge(high_rows, on=gk, how="left")
    result["tushare_high_time_pct"] = result["high_pos"] / np.maximum(result["bar_count"] - 1, 1)
    result = result.merge(vol_stats, on=gk, how="left")
    result["tushare_vwap_deviation"] = (result["eod_close"] - result["vwap"]) / np.maximum(np.abs(result["vwap"]), 0.01)
    result["tushare_close_vs_vwap"] = (result["eod_close"] / np.maximum(result["vwap"], 0.01)) - 1.0
    result["date"] = pd.to_datetime(result["trade_date"])
    out_cols = [
        "symbol", "date",
        "tushare_last_30min_return", "tushare_first_15min_volume_ratio",
        "tushare_vwap_deviation", "tushare_intraday_volatility",
        "tushare_up_volume_ratio", "tushare_high_time_pct", "tushare_close_vs_vwap",
    ]
    return result[out_cols].copy()


def build_tushare_factors(tushare_dir: str | Path) -> FactorFrame:
    """Build all Tushare-derived factors from cached parquets.

    Data directory: E:\\ashare_similarity_runtime\\data\\cache\\prediction\\tushare\\
    """
    tushare_dir = Path(tushare_dir)
    builders = [
        _build_moneyflow_factors,
        _build_limit_factors,
        _build_lhb_factors,
        _build_auction_factors,
        _build_holdernumber_factors,
        _build_stk_limit_factors,
        _build_hk_hold_factors,
        _build_margin_factors,
        _build_ths_hot_factors,
        _build_daily_basic_factors,
        _build_cyq_factors,
        _build_stk_mins_factors,
    ]
    pieces: list[pd.DataFrame] = []
    for builder in builders:
        try:
            piece = builder(tushare_dir)
            if not piece.empty:
                pieces.append(piece)
        except Exception:
            continue
    if not pieces:
        empty = pd.DataFrame(columns=["symbol", "date", *TUSHARE_FACTOR_COLUMNS])
        return FactorFrame(
            name="tushare_factors",
            frame=empty,
            columns=TUSHARE_FACTOR_COLUMNS,
            source="tushare_parquet",
            asof_time="after_close",
            lag_rule="T day Tushare data; use for T+1 prediction only",
            join_keys=("symbol", "date"),
        )
    merged = pieces[0]
    for piece in pieces[1:]:
        factor_cols = [c for c in piece.columns if c not in ("symbol", "date")]
        merged = merged.merge(piece[["symbol", "date", *factor_cols]], on=["symbol", "date"], how="outer")
    for col in TUSHARE_FACTOR_COLUMNS:
        if col not in merged.columns:
            merged[col] = np.nan
    return FactorFrame(
        name="tushare_factors",
        frame=merged[["symbol", "date", *TUSHARE_FACTOR_COLUMNS]].copy(),
        columns=TUSHARE_FACTOR_COLUMNS,
        source="tushare_parquet",
        asof_time="after_close",
        lag_rule="T day Tushare data; use for T+1 prediction only",
        join_keys=("symbol", "date"),
    )
