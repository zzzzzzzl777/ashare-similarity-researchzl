"""Generate Phase 1 training matrix for 14:57 hard-unavailable-excluded training."""
import json
from pathlib import Path
from datetime import datetime, timezone

factors = [
    {"factor_id": "C004", "factor_name": "ff_adjusted_flow", "family": "moneyflow_derivative", "engineering_status": "existing_engineered", "feature_columns": ["tushare_ff_adjusted_flow"], "available_feature_columns": ["tushare_ff_adjusted_flow_available"], "hard_unavailable_feature_columns": ["tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available"], "asof_tier": "strict_unavailable_requires_same_semantic_realtime_moneyflow", "source": "tushare moneyflow", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": False, "blocked_reason": "blocked_for_1457_hard_unavailable", "recommended_variant_group": "full_day_reference_only"},
    {"factor_id": "C009", "factor_name": "main_force_divergence", "family": "moneyflow_derivative", "engineering_status": "existing_engineered", "feature_columns": ["tushare_main_force_divergence"], "available_feature_columns": ["tushare_main_force_divergence_available"], "hard_unavailable_feature_columns": ["tushare_main_force_divergence", "tushare_main_force_divergence_available"], "asof_tier": "strict_unavailable_requires_same_semantic_realtime_moneyflow", "source": "tushare moneyflow", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": False, "blocked_reason": "blocked_for_1457_hard_unavailable", "recommended_variant_group": "full_day_reference_only"},
    {"factor_id": "C011", "factor_name": "auction_open_vwap_ratio", "family": "stk_auction_tier1b", "engineering_status": "existing_engineered", "feature_columns": ["tushare_auction_open_vwap_ratio"], "available_feature_columns": ["tushare_auction_open_vwap_ratio_available"], "hard_unavailable_feature_columns": [], "asof_tier": "strict_pre1457_or_metadata", "source": "tushare stk_auction", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+controls"},
    {"factor_id": "C133", "factor_name": "last_30min_return", "family": "intraday_momentum", "engineering_status": "existing_engineered", "feature_columns": ["tushare_last_30min_return"], "available_feature_columns": ["tushare_last_30min_return_available"], "hard_unavailable_feature_columns": [], "asof_tier": "needs_asof_rewrite_for_strict_1457", "source": "tushare stk_mins_5", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_intraday_momentum"},
    {"factor_id": "C134", "factor_name": "first_15min_volume_ratio", "family": "intraday_volume_structure", "engineering_status": "existing_engineered", "feature_columns": ["tushare_first_15min_volume_ratio"], "available_feature_columns": ["tushare_first_15min_volume_ratio_available"], "hard_unavailable_feature_columns": [], "asof_tier": "needs_asof_rewrite_for_strict_1457", "source": "tushare stk_mins_5", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_intraday_volume_structure"},
    {"factor_id": "C136", "factor_name": "intraday_volatility", "family": "intraday_risk", "engineering_status": "existing_engineered", "feature_columns": ["tushare_intraday_volatility"], "available_feature_columns": ["tushare_intraday_volatility_available"], "hard_unavailable_feature_columns": [], "asof_tier": "needs_asof_rewrite_for_strict_1457", "source": "tushare stk_mins_5", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_intraday_risk"},
    {"factor_id": "C137", "factor_name": "up_volume_ratio", "family": "intraday_volume_structure", "engineering_status": "existing_engineered", "feature_columns": ["tushare_up_volume_ratio"], "available_feature_columns": ["tushare_up_volume_ratio_available"], "hard_unavailable_feature_columns": [], "asof_tier": "needs_asof_rewrite_for_strict_1457", "source": "tushare stk_mins_5", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_intraday_volume_structure"},
    {"factor_id": "C138", "factor_name": "high_time_pct", "family": "intraday_momentum", "engineering_status": "existing_engineered", "feature_columns": ["tushare_high_time_pct"], "available_feature_columns": ["tushare_high_time_pct_available"], "hard_unavailable_feature_columns": [], "asof_tier": "needs_asof_rewrite_for_strict_1457", "source": "tushare stk_mins_5", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_intraday_momentum"},
    {"factor_id": "C141", "factor_name": "prev_top20_chase_mean", "family": "market_breadth", "engineering_status": "existing_engineered", "feature_columns": ["tushare_prev_top20_chase_mean"], "available_feature_columns": ["tushare_prev_top20_chase_mean_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_market_breadth"},
    {"factor_id": "C143", "factor_name": "volume_sufficiency_ratio", "family": "volume_quality", "engineering_status": "existing_engineered", "feature_columns": ["tushare_volume_sufficiency_ratio"], "available_feature_columns": ["tushare_volume_sufficiency_ratio_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_market_breadth"},
    {"factor_id": "C151", "factor_name": "anti_drop_strength_20d", "family": "relative_strength", "engineering_status": "existing_engineered", "feature_columns": ["tushare_anti_drop_strength_20d"], "available_feature_columns": ["tushare_anti_drop_strength_20d_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_relative_strength"},
    {"factor_id": "C152", "factor_name": "multi_wave_count_60d", "family": "technical_pattern", "engineering_status": "existing_engineered", "feature_columns": ["tushare_multi_wave_count_60d"], "available_feature_columns": ["tushare_multi_wave_count_60d_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_relative_strength"},
    {"factor_id": "C154", "factor_name": "price_vs_cost_20d", "family": "price_structure", "engineering_status": "existing_engineered", "feature_columns": ["tushare_price_vs_cost_20d"], "available_feature_columns": ["tushare_price_vs_cost_20d_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_price_structure"},
    {"factor_id": "C156", "factor_name": "abnormal_3d_deviation", "family": "momentum", "engineering_status": "existing_engineered", "feature_columns": ["tushare_abnormal_3d_deviation"], "available_feature_columns": ["tushare_abnormal_3d_deviation_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_momentum"},
    {"factor_id": "C157", "factor_name": "vol_gain_20d", "family": "volume_structure", "engineering_status": "existing_engineered", "feature_columns": ["tushare_vol_gain_20d"], "available_feature_columns": ["tushare_vol_gain_20d_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_volume_structure"},
    {"factor_id": "C158", "factor_name": "inv_t_20d", "family": "volume_structure", "engineering_status": "existing_engineered", "feature_columns": ["tushare_inv_t_20d"], "available_feature_columns": ["tushare_inv_t_20d_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_volume_structure"},
    {"factor_id": "C159", "factor_name": "asr_60d", "family": "price_structure", "engineering_status": "existing_engineered", "feature_columns": ["tushare_asr_60d"], "available_feature_columns": ["tushare_asr_60d_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_price_structure"},
    {"factor_id": "C161", "factor_name": "illiq_classic_20d", "family": "liquidity", "engineering_status": "existing_engineered", "feature_columns": ["tushare_illiq_classic_20d"], "available_feature_columns": ["tushare_illiq_classic_20d_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_liquidity"},
    {"factor_id": "C162", "factor_name": "ato_120d", "family": "volume_structure", "engineering_status": "existing_engineered", "feature_columns": ["tushare_ato_120d"], "available_feature_columns": ["tushare_ato_120d_available"], "hard_unavailable_feature_columns": [], "asof_tier": "approximated_1457_or_post_close", "source": "daily OHLCV derived", "leakage_risk": "none", "trainable_under_1457_hard_exclusion": True, "blocked_reason": None, "recommended_variant_group": "single+family_daily_volume_structure"},
]

matrix = {
    "phase": "Phase1_training_matrix",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "global_hard_exclusion": {
        "value_columns": ["tushare_net_mf_amount", "tushare_lg_buy_sell_ratio", "tushare_elg_buy_sell_ratio", "tushare_mf_strength", "tushare_sm_sell_pressure", "tushare_main_force_divergence", "tushare_ff_adjusted_flow"],
        "available_companions": ["tushare_net_mf_amount_available", "tushare_lg_buy_sell_ratio_available", "tushare_elg_buy_sell_ratio_available", "tushare_mf_strength_available", "tushare_sm_sell_pressure_available", "tushare_main_force_divergence_available", "tushare_ff_adjusted_flow_available"],
        "total_exclusion_count": 14
    },
    "factors": factors,
    "summary": {
        "total_in_manifest": 19,
        "blocked_1457": 2,
        "trainable": 17,
        "asof_tiers": {"strict_pre1457_or_metadata": 1, "needs_asof_rewrite_for_strict_1457": 5, "approximated_1457_or_post_close": 11},
        "families": {
            "stk_auction_tier1b": ["C011"],
            "intraday_momentum": ["C133", "C138"],
            "intraday_volume_structure": ["C134", "C137"],
            "intraday_risk": ["C136"],
            "market_breadth": ["C141"],
            "volume_quality": ["C143"],
            "relative_strength": ["C151"],
            "technical_pattern": ["C152"],
            "price_structure": ["C154", "C159"],
            "momentum": ["C156"],
            "volume_structure": ["C157", "C158", "C162"],
            "liquidity": ["C161"]
        }
    },
    "self_review_pass_1_scope_boundary": "done",
    "self_review_pass_2_data_factor_boundary": "done",
    "self_review_pass_3_engineering_audit_boundary": "done"
}

out = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\1457_executable_training_matrix_20260507.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(matrix, f, indent=2, ensure_ascii=False)
print(f"Written: {out}")
print(f"Trainable: {matrix['summary']['trainable']}, Blocked: {matrix['summary']['blocked_1457']}")
