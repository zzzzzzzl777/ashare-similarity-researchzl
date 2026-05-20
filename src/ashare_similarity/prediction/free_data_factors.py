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
    "tushare_main_force_divergence",
    "tushare_mf_flow_intensity",
    "tushare_ff_adjusted_flow",
    "tushare_float_relative_impact",
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
    # daily OHLCV derived factors (C154/C156/C157/C158/C159/C161/C162)
    "tushare_price_vs_cost_20d",
    "tushare_abnormal_3d_deviation",
    "tushare_vol_gain_20d",
    "tushare_inv_t_20d",
    "tushare_asr_60d",
    "tushare_illiq_classic_20d",
    "tushare_ato_120d",
    # daily OHLCV derived factors round 2 (C141/C143/C151/C152)
    "tushare_prev_top20_chase_mean",
    "tushare_volume_sufficiency_ratio",
    "tushare_anti_drop_strength_20d",
    "tushare_multi_wave_count_60d",
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
    dfs = []
    for file in files:
        frame = pd.read_parquet(file, columns=columns)
        if frame.empty:
            continue
        dfs.append(frame.dropna(axis=1, how="all"))
    if not dfs:
        return pd.DataFrame(columns=columns or None)
    result = pd.concat(dfs, ignore_index=True)
    if columns:
        for column in columns:
            if column not in result.columns:
                result[column] = pd.NA
        result = result[[column for column in columns if column in result.columns]]
    return result


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
    dfs = []
    for file in files:
        frame = pd.read_parquet(file)
        if frame.empty:
            continue
        dfs.append(frame.dropna(axis=1, how="all"))
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def _ts_code_to_symbol(ts_code: pd.Series) -> pd.Series:
    return ts_code.astype(str).str.split(".").str[0].str.zfill(6)


def _trade_date_to_date(trade_date: pd.Series) -> pd.Series:
    return pd.to_datetime(trade_date.astype(str), format="%Y%m%d", errors="coerce")


def _prepare_tushare_factor_piece(piece: pd.DataFrame) -> pd.DataFrame:
    """Normalize and de-duplicate a Tushare factor piece before outer merges.

    Cached Tushare APIs occasionally contain duplicate symbol/date rows. If a
    piece with duplicate join keys is outer-merged with another duplicate piece,
    pandas performs a many-to-many join and the intermediate frame can explode
    into tens of millions of rows. Keeping every piece key-unique preserves the
    intended one-row-per-stock-day semantics and makes full-history builds safe.
    """
    if piece.empty or not {"symbol", "date"}.issubset(piece.columns):
        return piece
    out = piece.copy()
    out["symbol"] = out["symbol"].astype(str).str.extract(r"(\d{6})", expand=False).fillna(out["symbol"].astype(str)).str.zfill(6)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["symbol", "date"])
    value_cols = [column for column in out.columns if column not in ("symbol", "date")]
    for column in value_cols:
        out[column] = pd.to_numeric(out[column], errors="coerce").astype(np.float32)
    if out.duplicated(["symbol", "date"]).any():
        out = (
            out.sort_values(["symbol", "date"])
            .groupby(["symbol", "date"], sort=False, as_index=False)[value_cols]
            .last()
        )
    return out


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
                "buy_elg_amount", "sell_elg_amount", "buy_sm_amount", "sell_sm_amount",
                "buy_md_amount", "sell_md_amount",
                "buy_sm_vol", "buy_md_vol", "buy_lg_vol", "buy_elg_vol"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0.0)
    big_buy = df["buy_lg_amount"] + df["buy_elg_amount"]
    big_sell = df["sell_lg_amount"] + df["sell_elg_amount"]
    lg_ratio = (df["buy_lg_amount"] / np.maximum(df["sell_lg_amount"], 100.0)).clip(upper=50.0)
    elg_ratio = (df["buy_elg_amount"] / np.maximum(df["sell_elg_amount"], 100.0)).clip(upper=50.0)
    total_buy_amount = df["buy_sm_amount"] + df["buy_md_amount"] + df["buy_lg_amount"] + df["buy_elg_amount"]
    total_buy_vol = df["buy_sm_vol"] + df["buy_md_vol"] + df["buy_lg_vol"] + df["buy_elg_vol"]
    out = pd.DataFrame({
        "symbol": df["symbol"],
        "date": df["date"],
        "tushare_net_mf_amount": df["net_mf_amount"],
        "tushare_lg_buy_sell_ratio": lg_ratio,
        "tushare_elg_buy_sell_ratio": elg_ratio,
        "tushare_mf_strength": (big_buy - big_sell) / np.maximum(big_buy + big_sell, 1.0),
        "tushare_sm_sell_pressure": df["sell_sm_amount"] / np.maximum(df["buy_sm_amount"] + df["sell_sm_amount"], 1.0),
        "tushare_main_force_divergence": (lg_ratio - elg_ratio).abs(),
        "tushare_mf_flow_intensity": df["net_mf_amount"] / np.maximum(total_buy_amount, 1.0),
        "_tmp_total_volume": total_buy_vol,
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
        "_tmp_close": pd.to_numeric(df.get("close"), errors="coerce"),
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
    factor_chunks: list[pd.DataFrame] = []
    t_1430 = _dt.time(14, 30)
    t_0945 = _dt.time(9, 45)
    out_cols = [
        "symbol", "date",
        "tushare_last_30min_return", "tushare_first_15min_volume_ratio",
        "tushare_vwap_deviation", "tushare_intraday_volatility",
        "tushare_up_volume_ratio", "tushare_high_time_pct", "tushare_close_vs_vwap",
    ]

    for f in files:
        try:
            bars = pd.read_parquet(
                f,
                columns=["ts_code", "trade_time", "close", "open", "high", "low", "vol", "amount"],
            )
        except Exception:
            continue
        if bars.empty:
            continue
        bars["trade_time"] = pd.to_datetime(bars["trade_time"], errors="coerce")
        for col in ("close", "open", "high", "low", "vol", "amount"):
            bars[col] = pd.to_numeric(bars.get(col), errors="coerce")
        bars["symbol"] = bars["ts_code"].astype(str).str.split(".").str[0].str.zfill(6)
        bars["date"] = bars["trade_time"].dt.normalize()
        bars["time"] = bars["trade_time"].dt.time
        bars = bars.dropna(subset=["date", "close"]).sort_values(["symbol", "date", "trade_time"])
        if bars.empty:
            continue

        gk = ["symbol", "date"]
        grouped = bars.groupby(gk, sort=False)
        day_stats = grouped.agg(
            bar_count=("close", "size"),
            day_vol=("vol", "sum"),
            day_amount=("amount", "sum"),
            eod_close=("close", "last"),
        ).reset_index()
        day_stats = day_stats[(day_stats["bar_count"] >= 5) & (day_stats["day_vol"] > 0)].copy()
        if day_stats.empty:
            continue
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
        high_idx = bars.groupby(gk, sort=False)["high"].idxmax()
        high_rows = bars.loc[high_idx.dropna(), gk + ["_bar_pos"]].copy()
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
        factor_chunks.append(result[out_cols].copy())

    if not factor_chunks:
        return pd.DataFrame()
    return pd.concat(factor_chunks, ignore_index=True)


def _build_daily_ohlcv_derived_factors(tushare_dir: Path) -> pd.DataFrame:
    """C154/C156/C157/C158/C159/C161/C162 from daily OHLCV bars."""
    from pathlib import Path as _P

    daily_dir = _P(r"E:\ashare_similarity_runtime\data\raw\bars\daily")
    if not daily_dir.is_dir():
        return pd.DataFrame()
    files = sorted(daily_dir.glob("*.parquet"))
    if not files:
        return pd.DataFrame()

    _date_floor = pd.Timestamp("2017-01-01")

    chunks: list[pd.DataFrame] = []
    for fpath in files:
        try:
            df = pd.read_parquet(fpath, columns=["date", "symbol", "close", "volume", "amount", "pct_change", "turnover"])
        except Exception:
            continue
        if df.empty or len(df) < 120:
            continue
        df = df.sort_values("date").reset_index(drop=True)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df["pct_change"] = pd.to_numeric(df["pct_change"], errors="coerce")
        df["turnover"] = pd.to_numeric(df["turnover"], errors="coerce")

        sym = df["symbol"].iloc[0] if "symbol" in df.columns else fpath.stem

        vwap_20 = df["amount"].rolling(20, min_periods=15).sum() / df["volume"].rolling(20, min_periods=15).sum().clip(lower=1)
        c154 = (df["close"] - vwap_20) / vwap_20.clip(lower=0.01)

        c156 = df["pct_change"].rolling(3, min_periods=3).sum()

        up_mask = df["pct_change"] > 0
        down_mask = df["pct_change"] <= 0
        to = df["turnover"]
        up_to_mean = to.where(up_mask).rolling(20, min_periods=5).mean()
        dn_to_mean = to.where(down_mask).rolling(20, min_periods=5).mean()
        c157 = up_to_mean / dn_to_mean.clip(lower=0.001)

        sign_ret = np.sign(df["pct_change"])
        signed_vol = sign_ret * df["volume"]
        c158 = -signed_vol.rolling(20, min_periods=15).sum() / df["volume"].rolling(20, min_periods=15).sum().clip(lower=1)

        p90 = df["close"].rolling(60, min_periods=40).quantile(0.9)
        p10 = df["close"].rolling(60, min_periods=40).quantile(0.1)
        c159 = (p90 - p10) / df["close"].clip(lower=0.01)

        abs_ret_over_amount = (df["pct_change"].abs() / 100.0) / df["amount"].clip(lower=1) * 1e10
        c161 = abs_ret_over_amount.rolling(20, min_periods=15).mean()

        to_20 = to.rolling(20, min_periods=15).mean()
        to_120 = to.rolling(120, min_periods=80).mean()
        to_120_std = to.rolling(120, min_periods=80).std()
        c162 = (to_20 - to_120) / to_120_std.clip(lower=0.001)

        out = pd.DataFrame({
            "symbol": sym,
            "date": df["date"],
            "tushare_price_vs_cost_20d": c154,
            "tushare_abnormal_3d_deviation": c156,
            "tushare_vol_gain_20d": c157,
            "tushare_inv_t_20d": c158,
            "tushare_asr_60d": c159,
            "tushare_illiq_classic_20d": c161,
            "tushare_ato_120d": c162,
        })
        out = out.dropna(subset=["date"])
        out = out[out["date"] >= _date_floor]
        if not out.empty:
            chunks.append(out)

    if not chunks:
        return pd.DataFrame()
    result = pd.concat(chunks, ignore_index=True)
    for col in ["tushare_price_vs_cost_20d", "tushare_vol_gain_20d", "tushare_inv_t_20d",
                "tushare_asr_60d", "tushare_illiq_classic_20d", "tushare_ato_120d"]:
        result[col] = result[col].clip(-50, 50)
    result["tushare_abnormal_3d_deviation"] = result["tushare_abnormal_3d_deviation"].clip(-30, 30)

    result["date"] = pd.to_datetime(result["date"], errors="coerce")

    # --- Round 2: C141/C143/C151/C152 (single second pass over daily bars) ---
    all_daily = []
    for fpath in sorted(daily_dir.glob("*.parquet")):
        try:
            df = pd.read_parquet(fpath, columns=["date", "symbol", "pct_change", "turnover", "close"])
        except Exception:
            continue
        if df.empty or len(df) < 5:
            continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df[df["date"] >= _date_floor]
        if len(df) < 5:
            continue
        df["pct_change"] = pd.to_numeric(df["pct_change"], errors="coerce")
        df["turnover"] = pd.to_numeric(df["turnover"], errors="coerce")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        all_daily.append(df[["date", "symbol", "pct_change", "turnover", "close"]].dropna(subset=["date"]))

    if all_daily:
        big = pd.concat(all_daily, ignore_index=True)
        big = big.sort_values(["date", "symbol"]).reset_index(drop=True)

        market_mean_ret = big.groupby("date")["pct_change"].mean()

        # C141: prev_top20_chase_mean (market-level factor, vectorized)
        big["prev_pct"] = big.groupby("symbol")["pct_change"].shift(1)
        rank_desc = big.groupby("date")["prev_pct"].rank(ascending=False, method="first")
        big["_top20"] = rank_desc <= 20
        top20_sum = big.loc[big["_top20"]].groupby("date")["pct_change"].agg(["sum", "count"])
        top20_sum["mean"] = np.where(top20_sum["count"] >= 20, top20_sum["sum"] / top20_sum["count"], np.nan)
        top20_map = top20_sum["mean"].to_dict()
        big.drop(columns=["_top20"], inplace=True)

        # C143: turnover_T / turnover_T-1 per symbol
        big["prev_turnover"] = big.groupby("symbol")["turnover"].shift(1)
        big["c143"] = big["turnover"] / big["prev_turnover"].clip(lower=0.01)

        # C151: stock_pct / market_pct on down days, rolling 20d mean
        big["market_ret"] = big["date"].map(market_mean_ret)
        big["down_day"] = big["market_ret"] < -0.5
        big["cond_ratio"] = np.where(big["down_day"], big["pct_change"] / big["market_ret"].clip(upper=-0.01), np.nan)
        big["c151"] = big.groupby("symbol")["cond_ratio"].transform(lambda x: x.rolling(20, min_periods=3).mean())

        # C152: multi_wave_count in 60d
        big["rise_flag"] = (big["close"] > big.groupby("symbol")["close"].shift(5)).astype(float)
        big["rise_start"] = big.groupby("symbol")["rise_flag"].transform(
            lambda x: (x.diff() == 1).rolling(60, min_periods=20).sum()
        )
        big["c152"] = big["rise_start"]

        # Map C141 (market-level) to result
        result["tushare_prev_top20_chase_mean"] = result["date"].map(top20_map).astype(float).clip(-20, 20)

        # Merge C143/C151/C152 back to result
        merge_cols = big[["date", "symbol", "c143", "c151", "c152"]].copy()
        merge_cols = merge_cols.rename(columns={
            "c143": "tushare_volume_sufficiency_ratio",
            "c151": "tushare_anti_drop_strength_20d",
            "c152": "tushare_multi_wave_count_60d",
        })
        result = result.merge(merge_cols, on=["date", "symbol"], how="left")
    else:
        result["tushare_prev_top20_chase_mean"] = np.nan
        result["tushare_volume_sufficiency_ratio"] = np.nan
        result["tushare_anti_drop_strength_20d"] = np.nan
        result["tushare_multi_wave_count_60d"] = np.nan

    result["tushare_volume_sufficiency_ratio"] = result["tushare_volume_sufficiency_ratio"].clip(0, 20)
    result["tushare_anti_drop_strength_20d"] = result["tushare_anti_drop_strength_20d"].clip(-10, 10)
    result["tushare_multi_wave_count_60d"] = result["tushare_multi_wave_count_60d"].clip(0, 30)

    return result


def build_tushare_factors(
    tushare_dir: str | Path,
    *,
    symbols: set[str] | None = None,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> FactorFrame:
    """Build all Tushare-derived factors from cached parquets.

    Data directory: E:\\ashare_similarity_runtime\\data\\cache\\prediction\\tushare\\
    """
    tushare_dir = Path(tushare_dir)
    symbol_filter = {str(symbol).zfill(6) for symbol in symbols} if symbols else None
    start_ts = pd.Timestamp(start).normalize() if start is not None else None
    end_ts = pd.Timestamp(end).normalize() if end is not None else None
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
        # Old tushare_* intraday columns are now injected from the shared
        # minute_* intraday factor frame in gpu_probe. Re-scanning stk_mins_5
        # here doubles full-history 5min work and is too slow for 2017+ cache
        # builds.
        _build_daily_ohlcv_derived_factors,
    ]
    pieces: list[pd.DataFrame] = []
    for builder in builders:
        try:
            piece = builder(tushare_dir)
            if not piece.empty:
                piece = _prepare_tushare_factor_piece(piece)
                if symbol_filter is not None:
                    piece = piece[piece["symbol"].isin(symbol_filter)]
                if start_ts is not None:
                    piece = piece[piece["date"] >= start_ts]
                if end_ts is not None:
                    piece = piece[piece["date"] <= end_ts]
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
    merged = _prepare_tushare_factor_piece(pieces[0])
    for piece in pieces[1:]:
        piece = _prepare_tushare_factor_piece(piece)
        factor_cols = [c for c in piece.columns if c not in ("symbol", "date")]
        merged = merged.merge(piece[["symbol", "date", *factor_cols]], on=["symbol", "date"], how="outer")
        merged = _prepare_tushare_factor_piece(merged)
    for col in TUSHARE_FACTOR_COLUMNS:
        if col not in merged.columns:
            merged[col] = np.nan
    if "_tmp_close" in merged.columns and "_tmp_total_volume" in merged.columns:
        denom_c004 = np.maximum(merged["tushare_free_share"].fillna(0) * merged["_tmp_close"].fillna(0), 1.0)
        merged["tushare_ff_adjusted_flow"] = (
            merged["tushare_net_mf_amount"].fillna(0) / denom_c004
        ).clip(-10.0, 10.0)
        denom_c010 = np.maximum(merged["tushare_free_share"].fillna(0), 1.0)
        merged["tushare_float_relative_impact"] = (
            merged["tushare_volume_ratio"].fillna(0) * merged["_tmp_total_volume"].fillna(0) / denom_c010
        ).clip(upper=100.0)
    merged = merged.drop(columns=[c for c in merged.columns if c.startswith("_tmp_")], errors="ignore")
    return FactorFrame(
        name="tushare_factors",
        frame=merged[["symbol", "date", *TUSHARE_FACTOR_COLUMNS]].copy(),
        columns=TUSHARE_FACTOR_COLUMNS,
        source="tushare_parquet",
        asof_time="after_close",
        lag_rule="T day Tushare data; use for T+1 prediction only",
        join_keys=("symbol", "date"),
    )
