"""
Build comprehensive feature catalog for A-share prediction system.
Classifies all 817 columns from the superset feature cache.
"""
import json
import os
from datetime import datetime
from collections import Counter
import pyarrow.parquet as pq

# === 1. Read schema ===
PARQUET_PATH = r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_50f0a15cc17d25ca.parquet"
pf = pq.ParquetFile(PARQUET_PATH)
schema = pf.schema_arrow
all_cols = [schema.field(i).name for i in range(len(schema))]
print(f"Total columns: {len(all_cols)}")

# === 2. Define classification rules ===

# Factor ID mapping (19 trainable factors)
factor_id_map = {
    "tushare_ff_adjusted_flow": "C004",
    "tushare_main_force_divergence": "C009",
    "tushare_auction_open_vwap_ratio": "C011",
    "tushare_last_30min_return": "C133",
    "tushare_first_15min_volume_ratio": "C134",
    "tushare_intraday_volatility": "C136",
    "tushare_up_volume_ratio": "C137",
    "tushare_high_time_pct": "C138",
    "tushare_prev_top20_chase_mean": "C141",
    "tushare_volume_sufficiency_ratio": "C143",
    "tushare_anti_drop_strength_20d": "C151",
    "tushare_multi_wave_count_60d": "C152",
    "tushare_price_vs_cost_20d": "C154",
    "tushare_abnormal_3d_deviation": "C156",
    "tushare_vol_gain_20d": "C157",
    "tushare_inv_t_20d": "C158",
    "tushare_asr_60d": "C159",
    "tushare_illiq_classic_20d": "C161",
    "tushare_ato_120d": "C162",
}

factor_family_map = {
    "C004": "moneyflow_derivative",
    "C009": "moneyflow_derivative",
    "C011": "stk_auction_tier1b",
    "C133": "intraday_momentum",
    "C134": "intraday_volume_structure",
    "C136": "intraday_risk",
    "C137": "intraday_volume_structure",
    "C138": "intraday_momentum",
    "C141": "market_breadth",
    "C143": "volume_quality",
    "C151": "relative_strength",
    "C152": "technical_pattern",
    "C154": "price_structure",
    "C156": "momentum",
    "C157": "volume_structure",
    "C158": "volume_structure",
    "C159": "price_structure",
    "C161": "liquidity",
    "C162": "volume_structure",
}

# Blocked columns
blocked_map = {
    "tushare_vwap_deviation": "C135_blocked_until_outlier_guard",
    "tushare_vwap_deviation_available": "C135_blocked_until_outlier_guard (available flag)",
    "tushare_close_vs_vwap": "duplicate_of_C135_no_factor_id",
    "tushare_close_vs_vwap_available": "duplicate_of_C135_no_factor_id (available flag)",
    "tushare_mf_flow_intensity": "C139_area_not_engineered",
    "tushare_mf_flow_intensity_available": "C139_area_not_engineered (available flag)",
    "tushare_float_relative_impact": "C_area_not_engineered",
    "tushare_float_relative_impact_available": "C_area_not_engineered (available flag)",
    "tushare_limit_space_compression": "limit_blocked_not_engineered",
    "tushare_limit_space_compression_available": "limit_blocked_not_engineered (available flag)",
    "tushare_limit_approach_velocity": "limit_blocked_not_engineered",
    "tushare_limit_approach_velocity_available": "limit_blocked_not_engineered (available flag)",
    "tushare_seal_strength_proxy": "limit_blocked_not_engineered",
    "tushare_seal_strength_proxy_available": "limit_blocked_not_engineered (available flag)",
}

# Duplicate map
duplicate_map = {
    "tushare_close_vs_vwap": "tushare_vwap_deviation",
    "tushare_close_vs_vwap_available": "tushare_vwap_deviation_available",
}

# Meta / non-feature columns
meta_cols = {
    "actual", "next_close_return_pct", "next_high_return_pct", "next_low_return_pct",
    "next_return_pct", "next_close_up", "hard_to_hold_2pct", "hard_to_hold_3pct",
    "close", "date", "label_date", "symbol",
}

# Emotion/market misc features
emotion_misc = {
    "emotion_phase_code", "emotion_phase_ice", "emotion_phase_trial",
    "emotion_phase_upswing", "emotion_phase_climax", "emotion_phase_divergence",
    "emotion_phase_ebbing", "emotion_climax_next_day_risk", "emotion_ice_rebound_setup",
    "cycle_day_count", "divergence_day_count", "buy_sell_cycle_phase",
    "liquidity_exhaustion_signal", "quant_climax_type", "vol_stagnation_signal",
    "bull_rotation_upgrade", "theme_capacity_score",
    "seal_rate_80_threshold",
    "prev_limit_up_premium", "prev_board_premium",
    "prev_failed_limit_up_count", "prev_failed_limit_up_return",
    "prev_failed_limit_up_red_rate", "prev_failed_limit_up_loss_rate",
    "failed_limit_up_loss_pressure", "prev_top20_chase_return",
    "prev_top20_chase_win_rate", "prev_bottom20_rebound_return",
    "money_effect_spread_20", "collapse_warning_signal",
    "consecutive_ice_days", "consecutive_high_premium_days",
    "volume_is_king_signal", "ground_volume_risk",
    "post_decline_transition", "decline_stabilize_signal", "weak_friday_risk",
    "strong_market_regime", "weak_market_oversold_regime",
    "bull_hotspot_bear_oversold", "bullish_pivot_recognition",
    "limit_premium_failure_signal", "bad_sentiment_no_sweep",
    "high_leader_crash_sentiment_collapse", "no_theme_rotation_mode",
    "money_effect_sector_rotation", "full_position_trigger",
    "late_cycle_position_cap", "bear_position_reduction",
    "market_split_signal",
    "same_height_success_rate_1",
    "same_height_success_rate_2",
    "same_height_success_rate_3plus",
    "same_height_failure_pressure",
}

# Board structure features
board_misc = {
    "board_count", "board_vs_max", "board_height_suppression",
    "is_space_board", "is_first_board", "is_second_board", "is_high_board",
    "prev_board_count", "board_promoted_today", "first_divergence_flag",
    "first_negative_flag", "volume_vs_prev", "volume_health_zone",
    "consecutive_shrink_days", "shrink_after_rotten", "explosive_vol_next_weak",
    "break_node_new_dragon", "dragon_replace_signal", "mid_cap_trap_risk",
    "buy_rise_divergence", "bet_decline_exhaustion", "board_keep_break_signal",
    "one_day_trip_risk_proxy",
}

# Symbol OHLCV misc (complex derived features from daily OHLCV)
symbol_ohlcv_misc = {
    "close_position", "gap_pct", "overnight_return", "intraday_return",
    "overnight_intraday_gap", "overnight_vs_intraday", "reversal_intraday",
    "limit_up_like", "limit_down_like", "failed_limit_up", "limit_down_bounce_pct",
    "limit_up_turnover", "one_word_board_proxy", "t_shape_board_proxy",
    "t_plus_1_selling_pressure", "board_space_height_5", "big_up", "big_down",
    "up_count_3", "up_count_5", "down_count_3", "down_count_5",
    "intraday_reversal_score", "limit_up_streak", "near_limit_close",
    "failed_breakout_10", "failed_breakout_20", "volume_price_divergence_5",
    "money_flow_fire", "hot_exhaustion_score", "limit_touch_fail_proxy",
    "limit_seal_quality_proxy", "gap_fill_ratio", "gap_continue_score",
    "trend_exhaustion_score", "climax_volume_ratio_60", "climax_amount_ratio_60",
    "volume_to_mean_20", "amount_to_mean_20", "daily_amount_300m_gate",
    "amount_300m_turnover_quality", "volume_price_match", "twenty_cm_board_risk",
    "amount_mean_3", "range_mean_3", "atr_mean_3", "short_phase_score_3",
    "short_phase_days_3", "turnover_sum_5", "turnover_sum_10", "turnover_sum_20",
    "turnover_accel_5_20", "limit_up_freq_60", "near_limit_freq_60",
    "failed_limit_freq_60", "active_turnover_freq_60", "stock_personality_score",
    "first_board_entry", "second_board_entry", "new_high_board",
    "new_high_breakout_quality", "weak_to_strong_daily", "low_suck_reversal_proxy",
    "board_failure_repair", "monster_acceleration", "recognizable_backup",
    "highlight_score", "former_leader_memory_120", "former_leader_recall",
    "leader_faith_decay_60", "leader_faith_decay_pressure",
    "quant_oscillation_score_10", "oscillation_breakout_signal",
    "new_high_volume_ratio_20", "consolidation_days_20", "consolidation_breakout_20",
    "reversal_with_volume", "cost_position_20", "cost_position_60",
    "profit_pressure_20", "profit_pressure_60", "risk_long_upper_after_big_up",
    "price_position_20", "price_position_60", "low_position_big_yang",
    "low_position_volume_reversal", "ma5_pullback_entry", "ma5_break_exit",
    "strong_rebound_from_20low", "high_position_climax_risk",
    "trend_pullback_health", "non_limit_open_strength",
    "auction_board_trigger_proxy", "safety_margin_calculation_proxy",
    "seal_grade_confirmation_proxy", "mega_order_absorption_proxy",
    "popularity_positive_feedback_proxy",
    "day_of_week_sin", "day_of_week_cos", "month_start_3", "month_end_3",
    "max_return_1d_20", "max_return_5d_60", "corwin_schultz_spread",
    "realized_skew_20", "limit_up_double_shot",
}


def assign_ohlcv_subfamily(col):
    """Assign sub-family for symbol_ohlcv_misc features."""
    if any(x in col for x in ["return", "ret", "reversal", "rebound", "overnight"]):
        return "symbol_ohlcv_return"
    elif any(x in col for x in ["volume", "amount", "turnover", "climax_volume", "climax_amount"]):
        return "symbol_ohlcv_volume"
    elif any(x in col for x in ["range", "atr", "body", "shadow"]):
        return "symbol_ohlcv_range"
    elif any(x in col for x in ["ma5_", "ma_", "ema_", "bollinger", "mean_reversion"]):
        return "symbol_ohlcv_moving_avg"
    elif any(x in col for x in ["gap_", "phase_", "days_", "consolidation_days", "consolidation_breakout"]):
        return "symbol_ohlcv_pattern"
    elif any(x in col for x in ["position", "dist_", "price_", "cost_", "profit_pressure"]):
        return "symbol_ohlcv_price"
    else:
        return "symbol_ohlcv_pattern"  # default for complex signals


def classify_column(col):
    """Classify a single column into catalog entry."""
    entry = {
        "feature_name": col,
        "family": None,
        "baseline_family": None,
        "factor_id": None,
        "factor_family": None,
        "source_module": None,
        "asof_rule": None,
        "strict_1457_available": None,
        "approximated_1457_available": None,
        "post_close_only": None,
        "blocked_reason": None,
        "duplicate_of": None,
        "is_meta": False,
    }

    # Check if meta
    if col in meta_cols:
        entry["family"] = "meta"
        entry["is_meta"] = True
        entry["asof_rule"] = "N/A (label/identifier)"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = False
        entry["post_close_only"] = False
        return entry

    # Check if blocked
    if col in blocked_map:
        entry["blocked_reason"] = blocked_map[col]
    if col in duplicate_map:
        entry["duplicate_of"] = duplicate_map[col]

    # Check if it's an _available flag
    is_available_flag = col.endswith("_available")
    parent_col = col[:-10] if is_available_flag else None

    if is_available_flag:
        entry["family"] = "available_flag"
        entry["baseline_family"] = "available_flag"
        if parent_col in factor_id_map:
            entry["factor_id"] = factor_id_map[parent_col] + "_available"
            entry["factor_family"] = factor_family_map.get(factor_id_map[parent_col])
        entry["source_module"] = "derived_from_parent"
        entry["asof_rule"] = "same_as_parent"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Check if it's a factor_value column
    if col in factor_id_map:
        fid = factor_id_map[col]
        entry["family"] = "factor_value"
        entry["factor_id"] = fid
        entry["factor_family"] = factor_family_map[fid]
        entry["source_module"] = "tushare_factor_pipeline"
        if fid in ("C004", "C009"):
            entry["asof_rule"] = "post_close_settlement"
            entry["strict_1457_available"] = False
            entry["approximated_1457_available"] = False
            entry["post_close_only"] = True
        elif fid == "C011":
            entry["asof_rule"] = "morning_auction"
            entry["strict_1457_available"] = True
            entry["approximated_1457_available"] = True
            entry["post_close_only"] = False
        elif fid in ("C133", "C134", "C136", "C137", "C138"):
            entry["asof_rule"] = "full_day_minute_data"
            entry["strict_1457_available"] = False
            entry["approximated_1457_available"] = False
            entry["post_close_only"] = True
        else:  # C141-C162
            entry["asof_rule"] = "daily_ohlcv_derived"
            entry["strict_1457_available"] = False
            entry["approximated_1457_available"] = True
            entry["post_close_only"] = False
        return entry

    # --- Baseline family classification by prefix/pattern ---

    # Return-related (including open_to_high_pct, open_to_low_pct)
    if any(col.startswith(p) for p in ["ret_", "overnight_", "reversal_intraday", "open_to_high",
                                        "open_to_low"]):
        entry["family"] = "symbol_ohlcv"
        entry["baseline_family"] = "symbol_ohlcv_return"
        entry["source_module"] = "daily_ohlcv_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Lag features
    if any(col.startswith(p) for p in ["ret_lag_", "range_lag_", "close_pos_lag_",
                                        "volume_z_lag_", "amount_z_lag_"]):
        entry["family"] = "symbol_ohlcv"
        entry["baseline_family"] = "symbol_ohlcv_return"
        entry["source_module"] = "daily_ohlcv_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Volume-related
    if any(col.startswith(p) for p in ["volume_", "amount_", "turnover", "obv_", "mfi_"]):
        entry["family"] = "symbol_ohlcv"
        entry["baseline_family"] = "symbol_ohlcv_volume"
        entry["source_module"] = "daily_ohlcv_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Range-related
    if any(col.startswith(p) for p in ["range_", "atr_", "body_pct", "upper_shadow",
                                        "lower_shadow"]):
        entry["family"] = "symbol_ohlcv"
        entry["baseline_family"] = "symbol_ohlcv_range"
        entry["source_module"] = "daily_ohlcv_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Momentum indicators
    if any(col.startswith(p) for p in ["rsi_", "macd_", "kdj_", "cci_", "williams_r",
                                        "adx_", "willr_"]):
        entry["family"] = "symbol_ohlcv"
        entry["baseline_family"] = "symbol_ohlcv_momentum"
        entry["source_module"] = "daily_ohlcv_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Moving averages
    if any(col.startswith(p) for p in ["ma_", "ema_", "bollinger_", "mean_reversion_distance"]):
        entry["family"] = "symbol_ohlcv"
        entry["baseline_family"] = "symbol_ohlcv_moving_avg"
        entry["source_module"] = "daily_ohlcv_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Pattern/phase/gap/days
    if any(col.startswith(p) for p in ["gap_", "short_phase_"]):
        entry["family"] = "symbol_ohlcv"
        entry["baseline_family"] = "symbol_ohlcv_pattern"
        entry["source_module"] = "daily_ohlcv_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Price position / high / low / close / dist / breakdown
    if any(col.startswith(p) for p in ["close_position", "dist_high", "dist_low",
                                        "price_position", "cost_position", "profit_pressure",
                                        "breakdown_"]):
        entry["family"] = "symbol_ohlcv"
        entry["baseline_family"] = "symbol_ohlcv_price"
        entry["source_module"] = "daily_ohlcv_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Interaction features
    if any(col.startswith(p) for p in ["ret1_x_", "ret5_x_", "range_x_", "turnover_x_",
                                        "amount_z_x_", "upper_shadow_x_", "lower_shadow_x_"]):
        entry["family"] = "symbol_ohlcv"
        entry["baseline_family"] = "symbol_ohlcv_volume"
        entry["source_module"] = "daily_ohlcv_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Cross-section (cs_* and cross_* index features, rel_*)
    if col.startswith("cs_") or col.startswith("cross_") or col.startswith("rel_"):
        entry["family"] = "cross_section"
        entry["baseline_family"] = "cross_section"
        entry["source_module"] = "cross_section_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Cross-section interaction features
    if col in ["volume_z_x_cs_ret_rank", "close_pos_x_cs_range_rank"]:
        entry["family"] = "cross_section"
        entry["baseline_family"] = "cross_section"
        entry["source_module"] = "cross_section_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Market emotion
    if any(col.startswith(p) for p in ["market_", "chase_", "strong_market_", "weak_market_",
                                        "weak_rebound_"]):
        entry["family"] = "market_emotion_board"
        entry["baseline_family"] = "market_emotion"
        entry["source_module"] = "market_emotion_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Board structure (breakout_, second_board_, seal80_, bull_, money_effect_, collapse_, index_panic_)
    if any(col.startswith(p) for p in ["breakout_", "second_board_", "seal80_", "bull_",
                                        "money_effect_", "collapse_", "index_panic_"]):
        entry["family"] = "market_emotion_board"
        entry["baseline_family"] = "board_structure"
        entry["source_module"] = "market_emotion_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # TGB stock features
    if col.startswith("tgb_") and any(col.startswith(p) for p in [
        "tgb_ma_", "tgb_pullback_", "tgb_board_height_", "tgb_board_quality_",
        "tgb_zhaban_", "tgb_volume_buildup_", "tgb_eod_"
    ]):
        entry["family"] = "tgb_factor"
        entry["baseline_family"] = "tgb_stock"
        entry["source_module"] = "tgb_factor_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # TGB market features
    if col.startswith("tgb_") and any(col.startswith(p) for p in [
        "tgb_market_", "tgb_leader_", "tgb_nuclear_", "tgb_mid_",
        "tgb_retreat_", "tgb_new_first_"
    ]):
        entry["family"] = "tgb_factor"
        entry["baseline_family"] = "tgb_market"
        entry["source_module"] = "tgb_factor_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Sector (ths)
    if col.startswith("sector_"):
        entry["family"] = "ths_sector"
        entry["baseline_family"] = "ths_sector"
        entry["source_module"] = "ths_sector_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Minute-bar features
    if col.startswith("minute_"):
        entry["family"] = "minute_intraday"
        entry["baseline_family"] = "minute_intraday"
        entry["source_module"] = "minute_bar_pipeline"
        entry["asof_rule"] = "full_day_minute_data"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = False
        entry["post_close_only"] = True
        return entry

    # Tushare moneyflow baseline
    if any(col.startswith(p) for p in ["tushare_net_mf_", "tushare_lg_", "tushare_elg_",
                                        "tushare_mf_", "tushare_sm_"]):
        entry["family"] = "tushare_baseline"
        entry["baseline_family"] = "tushare_moneyflow"
        entry["source_module"] = "tushare_moneyflow_pipeline"
        entry["asof_rule"] = "post_close_settlement"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = False
        entry["post_close_only"] = True
        return entry

    # Tushare auction
    if any(col.startswith(p) for p in ["tushare_seal_", "tushare_open_times",
                                        "tushare_first_time"]):
        entry["family"] = "tushare_baseline"
        entry["baseline_family"] = "tushare_auction"
        entry["source_module"] = "tushare_auction_pipeline"
        entry["asof_rule"] = "morning_auction"
        entry["strict_1457_available"] = True
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Tushare daily basic
    if col in ["tushare_total_mv", "tushare_circ_mv", "tushare_volume_ratio",
               "tushare_free_share"] or col.startswith("tushare_pe") or col.startswith("tushare_pb"):
        entry["family"] = "tushare_baseline"
        entry["baseline_family"] = "tushare_daily_basic"
        entry["source_module"] = "tushare_daily_basic_pipeline"
        entry["asof_rule"] = "T_minus_1_lag"
        entry["strict_1457_available"] = True
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Tushare margin
    if col.startswith("tushare_margin_") or any(col.startswith(p) for p in [
        "tushare_rzye", "tushare_rzmre", "tushare_rqye"
    ]):
        entry["family"] = "tushare_baseline"
        entry["baseline_family"] = "tushare_margin"
        entry["source_module"] = "tushare_margin_pipeline"
        entry["asof_rule"] = "post_close_T_minus_1"
        entry["strict_1457_available"] = True
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Tushare cyq
    if any(col.startswith(p) for p in ["tushare_winner_", "tushare_cost_concentration",
                                        "tushare_cost_position"]):
        entry["family"] = "tushare_baseline"
        entry["baseline_family"] = "tushare_cyq"
        entry["source_module"] = "tushare_cyq_pipeline"
        entry["asof_rule"] = "post_close_settlement"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = False
        entry["post_close_only"] = True
        return entry

    # Tushare HK
    if col.startswith("tushare_hk_"):
        entry["family"] = "tushare_baseline"
        entry["baseline_family"] = "tushare_hk"
        entry["source_module"] = "tushare_hk_pipeline"
        entry["asof_rule"] = "post_close_T_minus_1"
        entry["strict_1457_available"] = True
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Limit pool (real_*, seal_time_score, seal_money_*, seal_strength, etc.)
    if any(col.startswith(p) for p in ["real_", "seal_time_score", "seal_money_",
                                        "seal_strength", "seal_before_",
                                        "board_height_real", "last_seal_delay"]):
        entry["family"] = "limit_pool"
        entry["baseline_family"] = "limit_pool"
        entry["source_module"] = "limit_pool_pipeline"
        entry["asof_rule"] = "intraday_snapshot"
        entry["strict_1457_available"] = True
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # market_real_* and market_prev_zt_* (limit pool market features)
    if col.startswith("market_real_") or col in [
        "market_prev_zt_count", "market_prev_zt_red_rate",
        "prev_limit_pool_red_rate", "market_prev_zt_mean_pct_change",
        "yesterday_zt_premium", "real_limit_up_count"
    ]:
        entry["family"] = "limit_pool"
        entry["baseline_family"] = "limit_pool"
        entry["source_module"] = "limit_pool_pipeline"
        entry["asof_rule"] = "intraday_snapshot"
        entry["strict_1457_available"] = True
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Remaining tushare columns
    if col.startswith("tushare_"):
        if any(col.startswith(p) for p in ["tushare_up_stat_", "tushare_limit_type",
                                            "tushare_limit_turnover", "tushare_limit_space",
                                            "tushare_limit_approach", "tushare_limit_range",
                                            "tushare_up_limit_distance",
                                            "tushare_down_limit_distance"]):
            entry["family"] = "tushare_baseline"
            entry["baseline_family"] = "tushare_limit_stats"
            entry["source_module"] = "tushare_limit_pipeline"
            entry["asof_rule"] = "post_close_settlement"
            entry["strict_1457_available"] = False
            entry["approximated_1457_available"] = False
            entry["post_close_only"] = True
        elif col.startswith("tushare_lhb_") or col.startswith("tushare_inst_"):
            entry["family"] = "tushare_baseline"
            entry["baseline_family"] = "tushare_lhb"
            entry["source_module"] = "tushare_lhb_pipeline"
            entry["asof_rule"] = "post_close_T_plus_1"
            entry["strict_1457_available"] = False
            entry["approximated_1457_available"] = False
            entry["post_close_only"] = True
        elif col.startswith("tushare_hot_"):
            entry["family"] = "tushare_baseline"
            entry["baseline_family"] = "tushare_hot"
            entry["source_module"] = "tushare_hot_pipeline"
            entry["asof_rule"] = "intraday"
            entry["strict_1457_available"] = True
            entry["approximated_1457_available"] = True
            entry["post_close_only"] = False
        elif col.startswith("tushare_holder_"):
            entry["family"] = "tushare_baseline"
            entry["baseline_family"] = "tushare_holder"
            entry["source_module"] = "tushare_holder_pipeline"
            entry["asof_rule"] = "quarterly_lag"
            entry["strict_1457_available"] = True
            entry["approximated_1457_available"] = True
            entry["post_close_only"] = False
        elif col.startswith("tushare_auction_"):
            entry["family"] = "tushare_baseline"
            entry["baseline_family"] = "tushare_auction"
            entry["source_module"] = "tushare_auction_pipeline"
            entry["asof_rule"] = "morning_auction"
            entry["strict_1457_available"] = True
            entry["approximated_1457_available"] = True
            entry["post_close_only"] = False
        else:
            # Catch-all for remaining tushare
            entry["family"] = "tushare_baseline"
            entry["baseline_family"] = "tushare_misc"
            entry["source_module"] = "tushare_pipeline"
            entry["asof_rule"] = "post_close_settlement"
            entry["strict_1457_available"] = False
            entry["approximated_1457_available"] = False
            entry["post_close_only"] = True
        return entry

    # Emotion misc
    if col in emotion_misc:
        entry["family"] = "market_emotion_board"
        entry["baseline_family"] = "market_emotion"
        entry["source_module"] = "market_emotion_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Board misc
    if col in board_misc:
        entry["family"] = "market_emotion_board"
        entry["baseline_family"] = "board_structure"
        entry["source_module"] = "board_structure_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # Symbol OHLCV misc
    if col in symbol_ohlcv_misc:
        entry["family"] = "symbol_ohlcv"
        entry["baseline_family"] = assign_ohlcv_subfamily(col)
        entry["source_module"] = "daily_ohlcv_pipeline"
        entry["asof_rule"] = "daily_close_approx_1457"
        entry["strict_1457_available"] = False
        entry["approximated_1457_available"] = True
        entry["post_close_only"] = False
        return entry

    # If we got here, it's unmapped
    entry["family"] = "UNMAPPED"
    entry["baseline_family"] = None
    entry["source_module"] = "unknown"
    entry["asof_rule"] = "unknown"
    entry["strict_1457_available"] = None
    entry["approximated_1457_available"] = None
    entry["post_close_only"] = None
    return entry


# === 3. Classify all columns ===
catalog_entries = []
for col in all_cols:
    entry = classify_column(col)
    catalog_entries.append(entry)

# Report unmapped
unmapped = [e for e in catalog_entries if e["family"] == "UNMAPPED"]
print(f"Unmapped columns: {len(unmapped)}")
for e in unmapped:
    print(f"  {e['feature_name']}")

# Family distribution
family_counts = Counter(e["family"] for e in catalog_entries)
baseline_counts = Counter(e["baseline_family"] for e in catalog_entries if e["baseline_family"])
print(f"\nFamily distribution:")
for k, v in sorted(family_counts.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print(f"\nBaseline family distribution:")
for k, v in sorted(baseline_counts.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

# === 4. Build summary statistics ===
summary = {
    "generated_at": datetime.now().isoformat(),
    "parquet_path": PARQUET_PATH,
    "total_columns": len(all_cols),
    "family_counts": dict(family_counts),
    "baseline_family_counts": dict(baseline_counts),
    "factor_count": sum(1 for e in catalog_entries if e["factor_id"] and not e["factor_id"].endswith("_available")),
    "blocked_count": sum(1 for e in catalog_entries if e["blocked_reason"]),
    "duplicate_count": sum(1 for e in catalog_entries if e["duplicate_of"]),
    "meta_count": sum(1 for e in catalog_entries if e["is_meta"]),
    "unmapped_count": len(unmapped),
    "post_close_only_count": sum(1 for e in catalog_entries if e["post_close_only"]),
    "approximated_1457_available_count": sum(1 for e in catalog_entries if e["approximated_1457_available"]),
}

# === 5. Write JSON catalog ===
catalog_json = {
    "summary": summary,
    "columns": catalog_entries,
}

json_path = r"E:\ashare_similarity_runtime\data\reports\prediction\feature_catalog_20260507.json"
os.makedirs(os.path.dirname(json_path), exist_ok=True)
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(catalog_json, f, indent=2, ensure_ascii=False)
print(f"\nWritten: {json_path}")

# === 6. Write markdown summary ===
md_path = r"C:\Users\zzzzzzl\Desktop\subagent\docs\feature_catalog_20260507.md"
lines = []
lines.append("# Feature Catalog - 2026-05-07")
lines.append("")
lines.append(f"Generated: {summary['generated_at']}")
lines.append(f"Source: `{PARQUET_PATH}`")
lines.append(f"Total columns: **{summary['total_columns']}**")
lines.append("")
lines.append("## Summary Statistics")
lines.append("")
lines.append(f"| Metric | Count |")
lines.append(f"|--------|-------|")
lines.append(f"| Total columns | {summary['total_columns']} |")
lines.append(f"| Factor columns (with factor_id) | {summary['factor_count']} |")
lines.append(f"| Blocked columns | {summary['blocked_count']} |")
lines.append(f"| Duplicate columns | {summary['duplicate_count']} |")
lines.append(f"| Meta/label columns | {summary['meta_count']} |")
lines.append(f"| Unmapped columns | {summary['unmapped_count']} |")
lines.append(f"| Post-close only | {summary['post_close_only_count']} |")
lines.append(f"| Approximated 14:57 available | {summary['approximated_1457_available_count']} |")
lines.append("")
lines.append("## Family Distribution")
lines.append("")
lines.append("| Family | Count |")
lines.append("|--------|-------|")
for k, v in sorted(family_counts.items(), key=lambda x: -x[1]):
    lines.append(f"| {k} | {v} |")
lines.append("")
lines.append("## Baseline Family Distribution")
lines.append("")
lines.append("| Baseline Family | Count |")
lines.append("|----------------|-------|")
for k, v in sorted(baseline_counts.items(), key=lambda x: -x[1]):
    lines.append(f"| {k} | {v} |")
lines.append("")
lines.append("## Factor ID Mapping (19 trainable factors)")
lines.append("")
lines.append("| Feature Name | Factor ID | Factor Family | As-Of Rule |")
lines.append("|-------------|-----------|---------------|------------|")
for col, fid in sorted(factor_id_map.items(), key=lambda x: x[1]):
    ff = factor_family_map[fid]
    entry = next(e for e in catalog_entries if e["feature_name"] == col)
    lines.append(f"| {col} | {fid} | {ff} | {entry['asof_rule']} |")
lines.append("")
lines.append("## Blocked Columns (14 total)")
lines.append("")
lines.append("| Feature Name | Blocked Reason | Duplicate Of |")
lines.append("|-------------|----------------|-------------|")
for col, reason in blocked_map.items():
    dup = duplicate_map.get(col, "-")
    lines.append(f"| {col} | {reason} | {dup} |")
lines.append("")
lines.append("## As-Of Availability Rules")
lines.append("")
lines.append("| Rule | Description | Strict 14:57 | Approximated 14:57 |")
lines.append("|------|-------------|-------------|-------------------|")
lines.append("| daily_close_approx_1457 | Daily OHLCV bars, close approx 14:57 price | No | Yes |")
lines.append("| post_close_settlement | Post-market settlement data | No | No |")
lines.append("| morning_auction | Morning auction (9:15-9:25) | Yes | Yes |")
lines.append("| full_day_minute_data | Requires full trading day minute bars | No | No |")
lines.append("| daily_ohlcv_derived | Derived from daily OHLCV with lookback | No | Yes |")
lines.append("| T_minus_1_lag | Previous trading day data | Yes | Yes |")
lines.append("| post_close_T_minus_1 | Previous day post-close | Yes | Yes |")
lines.append("| intraday_snapshot | Intraday snapshot data (AKShare) | Yes | Yes |")
lines.append("| quarterly_lag | Quarterly report lag | Yes | Yes |")
lines.append("| post_close_T_plus_1 | Data available T+1 after close | No | No |")
lines.append("| same_as_parent | Available flag follows parent feature | - | Yes |")
lines.append("")
lines.append("## Unmapped Columns")
lines.append("")
if unmapped:
    for e in unmapped:
        lines.append(f"- `{e['feature_name']}`")
else:
    lines.append("None - all columns successfully mapped.")
lines.append("")

with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Written: {md_path}")

# === 7. Audit selected features from artifacts ===
artifacts = {
    "c0497be3_TRUE_baseline": "E:/ashare_similarity_runtime/data/reports/prediction/runs/gpu_probe_20260507T105820Z_c0497be3/artifact.json",
    "bb25159b_round4": "E:/ashare_similarity_runtime/data/reports/prediction/runs/gpu_probe_20260505T113406Z_bb25159b/artifact.json",
    "960529e8_superset": "E:/ashare_similarity_runtime/data/reports/prediction/runs/gpu_probe_20260507T100546Z_960529e8/artifact.json",
    "240a4b24_superset": "E:/ashare_similarity_runtime/data/reports/prediction/runs/gpu_probe_20260507T105225Z_240a4b24/artifact.json",
}

# Build lookup from catalog
catalog_lookup = {e["feature_name"]: e for e in catalog_entries}

audit_results = {}
for tag, path in artifacts.items():
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    result = d["result"]
    features = result.get("features", [])
    run_id = d.get("run_id", tag)

    # Classify each selected feature
    mapped_to_factor = []
    mapped_to_baseline = []
    unmapped_features = []
    blocked_features = []
    duplicate_features = []

    for feat in features:
        cat = catalog_lookup.get(feat)
        if cat is None:
            # Feature not in superset at all
            unmapped_features.append({"feature": feat, "reason": "not_in_superset_cache"})
            continue
        if cat["blocked_reason"]:
            blocked_features.append({"feature": feat, "reason": cat["blocked_reason"]})
        if cat["duplicate_of"]:
            duplicate_features.append({"feature": feat, "duplicate_of": cat["duplicate_of"]})
        if cat["factor_id"]:
            mapped_to_factor.append(feat)
        elif cat["baseline_family"]:
            mapped_to_baseline.append(feat)
        elif cat["is_meta"]:
            # Meta columns shouldn't be in selected features but not "unmapped"
            pass
        else:
            unmapped_features.append({"feature": feat, "reason": "no_factor_id_and_no_baseline_family"})

    audit_entry = {
        "run_id": run_id,
        "artifact_path": path,
        "total_selected_features": len(features),
        "mapped_to_factor_id": len(mapped_to_factor),
        "mapped_to_baseline_family": len(mapped_to_baseline),
        "unmapped_count": len(unmapped_features),
        "blocked_count": len(blocked_features),
        "duplicate_count": len(duplicate_features),
        "unmapped_features": unmapped_features,
        "blocked_features": blocked_features,
        "duplicate_features": duplicate_features,
        "gate_violations": [],
    }

    # Gate rules
    if len(blocked_features) > 0:
        audit_entry["gate_violations"].append({
            "severity": "P0",
            "rule": "blocked_features_in_selected > 0",
            "count": len(blocked_features),
            "features": [f["feature"] for f in blocked_features],
        })
    if len(unmapped_features) > 0:
        audit_entry["gate_violations"].append({
            "severity": "P1",
            "rule": "selected_features_unmapped > 0",
            "count": len(unmapped_features),
            "features": [f["feature"] for f in unmapped_features],
        })
    if len(duplicate_features) > 0:
        audit_entry["gate_violations"].append({
            "severity": "P1",
            "rule": "duplicate_features_in_selected > 0",
            "count": len(duplicate_features),
            "features": [f["feature"] for f in duplicate_features],
        })

    audit_results[tag] = audit_entry
    print(f"\n=== {tag} ===")
    print(f"  Total selected: {len(features)}")
    print(f"  Mapped to factor_id: {len(mapped_to_factor)}")
    print(f"  Mapped to baseline_family: {len(mapped_to_baseline)}")
    print(f"  Unmapped: {len(unmapped_features)}")
    print(f"  Blocked: {len(blocked_features)}")
    print(f"  Duplicate: {len(duplicate_features)}")
    print(f"  Gate violations: {len(audit_entry['gate_violations'])}")

# Write audit JSON
audit_json_path = r"E:\ashare_similarity_runtime\data\reports\prediction\selected_feature_catalog_audit_20260507.json"
audit_output = {
    "generated_at": datetime.now().isoformat(),
    "audit_results": audit_results,
}
with open(audit_json_path, "w", encoding="utf-8") as f:
    json.dump(audit_output, f, indent=2, ensure_ascii=False)
print(f"\nWritten: {audit_json_path}")

# Write audit markdown
audit_md_path = r"C:\Users\zzzzzzl\Desktop\subagent\docs\selected_feature_catalog_audit_20260507.md"
md_lines = []
md_lines.append("# Selected Feature Catalog Audit - 2026-05-07")
md_lines.append("")
md_lines.append(f"Generated: {datetime.now().isoformat()}")
md_lines.append("")
md_lines.append("## Audit Summary")
md_lines.append("")
md_lines.append("| Run | Total | Factor | Baseline | Unmapped | Blocked | Duplicate | Violations |")
md_lines.append("|-----|-------|--------|----------|----------|---------|-----------|------------|")
for tag, ae in audit_results.items():
    md_lines.append(f"| {tag} | {ae['total_selected_features']} | {ae['mapped_to_factor_id']} | {ae['mapped_to_baseline_family']} | {ae['unmapped_count']} | {ae['blocked_count']} | {ae['duplicate_count']} | {len(ae['gate_violations'])} |")
md_lines.append("")

for tag, ae in audit_results.items():
    md_lines.append(f"## {tag}")
    md_lines.append("")
    md_lines.append(f"- Run ID: `{ae['run_id']}`")
    md_lines.append(f"- Artifact: `{ae['artifact_path']}`")
    md_lines.append(f"- Total selected features: {ae['total_selected_features']}")
    md_lines.append(f"- Mapped to factor_id: {ae['mapped_to_factor_id']}")
    md_lines.append(f"- Mapped to baseline_family: {ae['mapped_to_baseline_family']}")
    md_lines.append(f"- Unmapped: {ae['unmapped_count']}")
    md_lines.append(f"- Blocked: {ae['blocked_count']}")
    md_lines.append(f"- Duplicate: {ae['duplicate_count']}")
    md_lines.append("")

    if ae["gate_violations"]:
        md_lines.append("### Gate Violations")
        md_lines.append("")
        for gv in ae["gate_violations"]:
            md_lines.append(f"- **{gv['severity']}**: {gv['rule']} (count={gv['count']})")
            for feat in gv["features"]:
                md_lines.append(f"  - `{feat}`")
        md_lines.append("")
    else:
        md_lines.append("### Gate Violations: NONE")
        md_lines.append("")

    if ae["unmapped_features"]:
        md_lines.append("### Unmapped Features")
        md_lines.append("")
        for uf in ae["unmapped_features"]:
            md_lines.append(f"- `{uf['feature']}` ({uf['reason']})")
        md_lines.append("")

    if ae["blocked_features"]:
        md_lines.append("### Blocked Features in Selected")
        md_lines.append("")
        for bf in ae["blocked_features"]:
            md_lines.append(f"- `{bf['feature']}` ({bf['reason']})")
        md_lines.append("")

    if ae["duplicate_features"]:
        md_lines.append("### Duplicate Features in Selected")
        md_lines.append("")
        for df in ae["duplicate_features"]:
            md_lines.append(f"- `{df['feature']}` (duplicate of `{df['duplicate_of']}`)")
        md_lines.append("")

with open(audit_md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))
print(f"Written: {audit_md_path}")

print("\n=== DONE ===")
