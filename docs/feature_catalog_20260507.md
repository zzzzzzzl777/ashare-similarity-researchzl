# Feature Catalog - 2026-05-07

Generated: 2026-05-07T22:05:32.268148
Source: `E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_50f0a15cc17d25ca.parquet`
Total columns: **817**

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total columns | 817 |
| Factor columns (with factor_id) | 19 |
| Blocked columns | 8 |
| Duplicate columns | 2 |
| Meta/label columns | 12 |
| Unmapped columns | 0 |
| Post-close only | 59 |
| Approximated 14:57 available | 746 |

## Family Distribution

| Family | Count |
|--------|-------|
| available_flag | 270 |
| symbol_ohlcv | 210 |
| market_emotion_board | 135 |
| cross_section | 47 |
| tushare_baseline | 42 |
| limit_pool | 33 |
| minute_intraday | 29 |
| factor_value | 19 |
| tgb_factor | 14 |
| meta | 12 |
| ths_sector | 6 |

## Baseline Family Distribution

| Baseline Family | Count |
|----------------|-------|
| available_flag | 270 |
| market_emotion | 98 |
| symbol_ohlcv_pattern | 64 |
| symbol_ohlcv_return | 61 |
| cross_section | 47 |
| symbol_ohlcv_volume | 43 |
| board_structure | 37 |
| limit_pool | 33 |
| minute_intraday | 29 |
| symbol_ohlcv_price | 14 |
| symbol_ohlcv_range | 10 |
| symbol_ohlcv_momentum | 10 |
| symbol_ohlcv_moving_avg | 8 |
| tgb_stock | 8 |
| tgb_market | 6 |
| ths_sector | 6 |
| tushare_moneyflow | 6 |
| tushare_auction | 6 |
| tushare_limit_stats | 6 |
| tushare_lhb | 5 |
| tushare_margin | 5 |
| tushare_misc | 3 |
| tushare_cyq | 3 |
| tushare_hk | 2 |
| tushare_hot | 2 |
| tushare_daily_basic | 2 |
| tushare_holder | 2 |

## Factor ID Mapping (19 trainable factors)

| Feature Name | Factor ID | Factor Family | As-Of Rule |
|-------------|-----------|---------------|------------|
| tushare_ff_adjusted_flow | C004 | moneyflow_derivative | post_close_settlement |
| tushare_main_force_divergence | C009 | moneyflow_derivative | post_close_settlement |
| tushare_auction_open_vwap_ratio | C011 | stk_auction_tier1b | morning_auction |
| tushare_last_30min_return | C133 | intraday_momentum | full_day_minute_data |
| tushare_first_15min_volume_ratio | C134 | intraday_volume_structure | full_day_minute_data |
| tushare_intraday_volatility | C136 | intraday_risk | full_day_minute_data |
| tushare_up_volume_ratio | C137 | intraday_volume_structure | full_day_minute_data |
| tushare_high_time_pct | C138 | intraday_momentum | full_day_minute_data |
| tushare_prev_top20_chase_mean | C141 | market_breadth | daily_ohlcv_derived |
| tushare_volume_sufficiency_ratio | C143 | volume_quality | daily_ohlcv_derived |
| tushare_anti_drop_strength_20d | C151 | relative_strength | daily_ohlcv_derived |
| tushare_multi_wave_count_60d | C152 | technical_pattern | daily_ohlcv_derived |
| tushare_price_vs_cost_20d | C154 | price_structure | daily_ohlcv_derived |
| tushare_abnormal_3d_deviation | C156 | momentum | daily_ohlcv_derived |
| tushare_vol_gain_20d | C157 | volume_structure | daily_ohlcv_derived |
| tushare_inv_t_20d | C158 | volume_structure | daily_ohlcv_derived |
| tushare_asr_60d | C159 | price_structure | daily_ohlcv_derived |
| tushare_illiq_classic_20d | C161 | liquidity | daily_ohlcv_derived |
| tushare_ato_120d | C162 | volume_structure | daily_ohlcv_derived |

## Blocked Columns (14 in blocklist, 8 present in parquet)

Note: 6 blocked columns (tushare_limit_space_compression, tushare_limit_approach_velocity,
tushare_seal_strength_proxy + their _available flags) are NOT in the parquet schema.

| Feature Name | Blocked Reason | Duplicate Of | In Parquet |
|-------------|----------------|-------------|:----------:|
| tushare_vwap_deviation | C135_blocked_until_outlier_guard | - | Yes |
| tushare_vwap_deviation_available | C135_blocked_until_outlier_guard (available flag) | - | Yes |
| tushare_close_vs_vwap | duplicate_of_C135_no_factor_id | tushare_vwap_deviation | Yes |
| tushare_close_vs_vwap_available | duplicate_of_C135_no_factor_id (available flag) | tushare_vwap_deviation_available | Yes |
| tushare_mf_flow_intensity | C139_area_not_engineered | - | Yes |
| tushare_mf_flow_intensity_available | C139_area_not_engineered (available flag) | - | Yes |
| tushare_float_relative_impact | C_area_not_engineered | - | Yes |
| tushare_float_relative_impact_available | C_area_not_engineered (available flag) | - | Yes |
| tushare_limit_space_compression | limit_blocked_not_engineered | - | No |
| tushare_limit_space_compression_available | limit_blocked_not_engineered (available flag) | - | No |
| tushare_limit_approach_velocity | limit_blocked_not_engineered | - | No |
| tushare_limit_approach_velocity_available | limit_blocked_not_engineered (available flag) | - | No |
| tushare_seal_strength_proxy | limit_blocked_not_engineered | - | No |
| tushare_seal_strength_proxy_available | limit_blocked_not_engineered (available flag) | - | No |

## As-Of Availability Rules

| Rule | Description | Strict 14:57 | Approximated 14:57 |
|------|-------------|-------------|-------------------|
| daily_close_approx_1457 | Daily OHLCV bars, close approx 14:57 price | No | Yes |
| post_close_settlement | Post-market settlement data | No | No |
| morning_auction | Morning auction (9:15-9:25) | Yes | Yes |
| full_day_minute_data | Requires full trading day minute bars | No | No |
| daily_ohlcv_derived | Derived from daily OHLCV with lookback | No | Yes |
| T_minus_1_lag | Previous trading day data | Yes | Yes |
| post_close_T_minus_1 | Previous day post-close | Yes | Yes |
| intraday_snapshot | Intraday snapshot data (AKShare) | Yes | Yes |
| quarterly_lag | Quarterly report lag | Yes | Yes |
| post_close_T_plus_1 | Data available T+1 after close | No | No |
| same_as_parent | Available flag follows parent feature | - | Yes |

## Unmapped Columns

None - all columns successfully mapped.
