# Canonical Factor Candidate Registry Audit 2026-05-17

Scope: factor-library closed-loop audit only. No training, no `gpu_probe`, no model-code changes, no formal registry writes.

## Inputs

- Formal registry: `E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json`
- Raw pool: `E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json`
- O reports:
  - `C:\Users\zzzzzzl\Desktop\subagent\docs\four_source_shortline_omnibus_candidate_scan_20260517.md`
  - `C:\Users\zzzzzzl\Desktop\subagent\docs\four_source_shortline_omnibus_candidate_addendum_20260517.md`
  - `C:\Users\zzzzzzl\Desktop\subagent\docs\four_source_shortline_omnibus_candidate_addendum2_20260517.md`
  - `C:\Users\zzzzzzl\Desktop\subagent\docs\four_source_shortline_omnibus_candidate_addendum3_20260517.md`

## Summary

| metric | value |
|---|---:|
| formal C candidates parsed | 292 |
| temporary O candidates parsed | 450 |
| raw pool records parsed | 3075 |
| total input rows | 3817 |
| canonical groups after merge | 3292 |
| raw-only groups still needing review | 995 |

## Decision Counts

| decision | canonical groups |
|---|---:|
| raw_only_low_priority_or_duplicate | 1502 |
| raw_only_possible_candidate | 519 |
| raw_only_needs_review | 476 |
| already_formal_registry | 291 |
| needs_data_pipeline | 158 |
| engineering_review_first | 153 |
| needs_formula_lock | 80 |
| blocked_or_data_missing | 60 |
| blocked_level2_or_scrape | 53 |

## Family Counts

| family | canonical groups |
|---|---:|
| misc_review | 1394 |
| limit_board | 538 |
| minute_hf | 312 |
| theme_leader | 239 |
| daily_technical | 216 |
| flow_lhb | 184 |
| auction_open | 144 |
| level2_tick | 90 |
| event_fundamental | 86 |
| social_attention | 63 |
| cross_market | 26 |

## What This Means

- The O001-O450 queue is not 450 independent finished factors. It is a wide search queue.
- The canonical groups are the deduplicated working units for CC engineering review.
- `already_formal_registry` groups are already represented by C001-C292 or previous formal batches.
- `engineering_review_first` groups are the cleanest next candidates for possible C293+ promotion.
- `needs_formula_lock` and `needs_data_pipeline` should not be added until the formula or data path is locked.
- `raw_only_*` groups are not covered well by the O queue; they are the true residual candidates from raw pool.

## Priority Engineering Review Queue

| rank | canonical | family | decision | status | pri | members | example ids | data needs |
|---:|---|---|---|---|---|---:|---|---|
| 1 | market_limit_up_count_clean | limit_board | engineering_review_first | ready_engineering_review | P0 | 11 | O120, RAW000027, RAW000744, RAW001018, RAW001241, RAW001525 | ["daily_ohlcv", "limit_pool"]; ["limit_pool", "hot_rank"]; +3 more |
| 2 | seal_time_canonical | limit_board | engineering_review_first | ready_engineering_review | P0 | 4 | O112, RAW000259, RAW000573, RAW000574 | ["limit_pool"]; limit_pool |
| 3 | volume_vs_prev_recheck | daily_technical | engineering_review_first | ready_engineering_review | P0 | 3 | O211, RAW000010, RAW000260 | ["daily_ohlcv", "limit_pool"]; ["daily_ohlcv"]; +1 more |
| 4 | market_open_board_rate_canonical | limit_board | engineering_review_first | ready_engineering_review | P0 | 3 | O111, O332, RAW001097 | ["limit_pool"]; limit_pool |
| 5 | prev_limit_up_premium_recheck | limit_board | engineering_review_first | ready_engineering_review | P0 | 3 | O119, RAW000037, RAW000255 | ["daily_ohlcv", "limit_pool"]; ["limit_pool"]; +1 more |
| 6 | shortest_path_illiquidity_intraday | auction_open | engineering_review_first | ready_engineering_review | P0 | 1 | O176 | 1min bars |
| 7 | first15_volume_acceleration | daily_technical | engineering_review_first | ready_engineering_review | P0 | 1 | O162 | 1min bars |
| 8 | high_vol_price_position_ratio | daily_technical | engineering_review_first | ready_engineering_review | P0 | 1 | O006 | 1min bars |
| 9 | signed_volume_early_late_ratio | daily_technical | engineering_review_first | ready_engineering_review | P0 | 1 | O013 | 1min bars |
| 10 | lhb_net_buy_vs_float | flow_lhb | engineering_review_first | ready_engineering_review | P0 | 1 | O053 | top_list + share_float |
| 11 | board_count_canonical | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O118 | limit_pool |
| 12 | board_height_compression_speed | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O026 | limit_list_d + board height |
| 13 | broken_board_loss_diffusion | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O028 | limit_list_d + returns |
| 14 | first_board_to_second_board_conversion | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O034 | limit_list_d |
| 15 | high_board_survival_rate_3d | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O032 | limit_list_d |
| 16 | last_seal_delay | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O117 | limit_pool |
| 17 | market_limit_attempt_count | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O331 | limit_pool |
| 18 | seal_money_to_amount | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O115 | limit_pool + daily amount |
| 19 | seal_money_to_float_mv | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O114 | limit_pool + share_float |
| 20 | seal_rate_collapse_3d | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O027 | limit_list_d + intraday seal/break |
| 21 | weak_to_strong_open_reclaim | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O049 | 1min + prev board status |
| 22 | zt_total_nonst_nononeword | limit_board | engineering_review_first | ready_engineering_review | P0 | 1 | O338 | limit_pool |
| 23 | apl20_tail_amount_ratio | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O391 | 1min bars |
| 24 | cross_sectional_minute_momentum_rank | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O101 | 1min all-stock bars |
| 25 | first5_vwap_hold_ratio | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O161 | 1min bars |
| 26 | high_position_volume_event_ratio | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O004 | 1min bars + trailing price window |
| 27 | minute_market_breadth_thrust | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O099 | 1min all-stock bars |
| 28 | minute_opening_range_breakout_quality | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O107 | 1min bars |
| 29 | minute_price_autocorr_20d | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O003 | 1min bars |
| 30 | minute_pv_corr_segmented | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O002 | 1min bars |
| 31 | minute_turnover_stability_20d | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O001 | 1min bars + share_float |
| 32 | morning30_volume_factor | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O179 | 1min bars |
| 33 | same_clock_volume_surprise | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O017 | 1min bars |
| 34 | shock_price_reversal_efficiency | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O012 | 1min bars |
| 35 | shock_volume_decay_half_life | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O011 | 1min bars |
| 36 | volume_surge_moment_bright_return | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O312 | 1min bars |
| 37 | volume_surge_moment_bright_volatility | minute_hf | engineering_review_first | ready_engineering_review | P0 | 1 | O311 | 1min bars |
| 38 | reversal_with_volume | daily_technical | engineering_review_first | ready_engineering_review | P1 | 2 | O382, RAW003063 | ["daily_ohlcv"]; daily_ohlcv |
| 39 | volume_peak_count_factor | daily_technical | engineering_review_first | ready_engineering_review | P1 | 2 | O318, O406 | 1min bars |
| 40 | open_board_day_amplitude | limit_board | engineering_review_first | ready_engineering_review | P1 | 2 | O125, RAW001258 | ["limit_pool"]; limit_pool + daily_ohlcv |
| 41 | open_board_day_turnover | limit_board | engineering_review_first | ready_engineering_review | P1 | 2 | O124, RAW001257 | ["daily_ohlcv", "limit_pool"]; limit_pool + daily_ohlcv |
| 42 | open_gap_clean | limit_board | engineering_review_first | ready_engineering_review | P1 | 2 | O225, RAW001135 | ["daily_ohlcv"]; daily_ohlcv |
| 43 | opening_seal_speed | limit_board | engineering_review_first | ready_engineering_review | P1 | 2 | O122, RAW000312 | ["limit_pool"]; limit_pool + 1min |
| 44 | second_seal_opportunity | limit_board | engineering_review_first | ready_engineering_review | P1 | 2 | O340, RAW000918 | ["limit_pool"]; limit_pool + 1min |
| 45 | auction_false_strength_risk | auction_open | engineering_review_first | ready_engineering_review | P1 | 1 | O045 | auction + 1min |
| 46 | auction_open_to_first5_reclaim | auction_open | engineering_review_first | ready_engineering_review | P1 | 1 | O044 | auction + 1min |
| 47 | afternoon30_volume_factor | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O180 | 1min bars |
| 48 | afternoon_reacceleration | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O022 | 1min bars |
| 49 | alpha360_shape_moment_intraday | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O074 | 1min bars |
| 50 | breakout_amount_quality | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O221 | daily_ohlcv |
| 51 | breakout_factor_volume_confirm | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O381 | daily_ohlcv |
| 52 | high_low_vol_bucket_reversal | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O412 | 1min bars |
| 53 | intraday_correlation_regime_switch | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O076 | 1min bars |
| 54 | last30_volume_ridge | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O165 | 1min bars |
| 55 | late_breakout_fail_probability | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O106 | 1min bars |
| 56 | local_reversal_by_volume_bucket | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O409 | 1min bars |
| 57 | low_vol_price_position_ratio | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O007 | 1min bars |
| 58 | rolling_rank_volume_price_residual | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O075 | daily + 1min |
| 59 | volume_peak_isolation | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O166 | 1min bars |
| 60 | volume_ridge_count_factor | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O319 | 1min bars |
| 61 | volume_ridge_retail_participation | daily_technical | engineering_review_first | ready_engineering_review | P1 | 1 | O186 | 1min bars |
| 62 | lhb_afterglow_half_life | flow_lhb | engineering_review_first | ready_engineering_review | P1 | 1 | O052 | top_list + returns |
| 63 | micro_partition_volatility_spread | level2_tick | engineering_review_first | ready_engineering_review | P1 | 1 | O410 | 1min bars |
| 64 | board_break_frequency_3d | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O133 | limit_pool |
| 65 | emotion_score_raw | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O257 | limit_pool |
| 66 | failed_board_recovery_breadth | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O039 | broken-board list + returns |
| 67 | ice_point_new_cycle_trial | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O259 | limit_pool |
| 68 | limit_pool_crowding_score | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O035 | limit_list_d + turnover |
| 69 | limit_pool_internal_dispersion | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O135 | limit_pool + returns |
| 70 | limit_touch_without_followthrough | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O132 | limit_pool + returns |
| 71 | market_rotten_board_infection | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O109 | limit_list_d + broken boards |
| 72 | max_board_height_ceiling | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O336 | limit_pool |
| 73 | noon_seal_stability | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O130 | limit_pool |
| 74 | reseal_speed_real | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O341 | 1min + limit_pool |
| 75 | rotten_board_afterglow_risk | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O036 | limit_list_d + intraday breaks |
| 76 | seal_fail_repair_same_day | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O129 | limit_pool + 1min |
| 77 | seal_money_decay_3d | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O134 | limit_pool |
| 78 | seal_time_distribution_entropy | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O342 | limit_pool |
| 79 | seal_time_rank_change | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O037 | limit_list_d seal time |
| 80 | shrink_accelerate_board_quality | limit_board | engineering_review_first | ready_engineering_review | P1 | 1 | O215 | daily_ohlcv + limit_pool |

## Raw-Only Residual Review Queue

These groups are not formal C candidates and do not appear in the O001-O450 queue by exact canonical key. They are the remaining raw-pool ideas worth manual review, mostly due to aliasing, formula looseness, or missing data.

| rank | canonical | family | decision | status | pri | members | example ids | data needs |
|---:|---|---|---|---|---|---:|---|---|
| 1 | a50_night_return | misc_review | raw_only_needs_review | needs_asof_check | P0 | 2 | RAW002901, RAW002963 | ["cross_market"] |
| 2 | closing_auction_volume | auction_open | raw_only_needs_review | needs_engineering_review | P0 | 2 | RAW002938, RAW002961 | ["daily_ohlcv", "auction"] |
| 3 | consensus_sell_auction | auction_open | raw_only_needs_review | needs_engineering_review | P0 | 2 | RAW000269, RAW000390 | ["auction"] |
| 4 | last_30min_return | minute_hf | raw_only_needs_review | needs_engineering_review | P0 | 2 | RAW002935, RAW002959 | ["minute"] |
| 5 | last_30min_volume_ratio | minute_hf | raw_only_needs_review | needs_engineering_review | P0 | 1 | RAW002960 | ["daily_ohlcv", "minute"] |
| 6 | one_word_board_real | limit_board | raw_only_needs_review | needs_engineering_review | P0 | 1 | RAW001766 | ["auction", "limit_pool"] |
| 7 | turnover_board_real | limit_board | raw_only_needs_review | needs_engineering_review | P0 | 1 | RAW001767 | ["daily_ohlcv", "auction", "limit_pool"] |
| 8 | if_basis_pct | misc_review | raw_only_needs_review | needs_asof_check | P1 | 2 | RAW002903, RAW002970 | ["cross_market"] |
| 9 | turnover_board_30min | limit_board | raw_only_needs_review | needs_engineering_review | P1 | 2 | RAW000196, RAW000289 | ["daily_ohlcv", "minute"] |
| 10 | vix_change | misc_review | raw_only_needs_review | needs_asof_check | P1 | 2 | RAW002902, RAW002971 | ["cross_market"] |
| 11 | vwap_deviation_eod | minute_hf | raw_only_needs_review | needs_engineering_review | P1 | 2 | RAW002948, RAW002976 | ["daily_ohlcv", "minute"]; ["minute"] |
| 12 | attack_volume_confirm | minute_hf | raw_only_needs_review | needs_engineering_review | P1 | 1 | RAW001777 | ["daily_ohlcv", "minute"] |
| 13 | auction_925_amount_ratio | auction_open | raw_only_needs_review | needs_engineering_review | P1 | 1 | RAW001773 | ["daily_ohlcv", "auction"] |
| 14 | core_auction_premium_gap | auction_open | raw_only_needs_review | needs_engineering_review | P1 | 1 | RAW000279 | ["auction", "daily_ohlcv"] |
| 15 | hot_rank_jump | misc_review | raw_only_needs_review | needs_engineering_review | P1 | 1 | RAW001783 | ["hot_rank"] |
| 16 | intraday_trend_strength | minute_hf | raw_only_needs_review | needs_engineering_review | P1 | 1 | RAW002977 | ["minute"] |
| 17 | keyword_theme_heat | theme_leader | raw_only_needs_review | needs_engineering_review | P1 | 1 | RAW001784 | ["hot_rank", "sector_theme"] |
| 18 | open_5m_confirm_strength | minute_hf | raw_only_needs_review | needs_engineering_review | P1 | 1 | RAW001776 | ["daily_ohlcv", "minute"] |
| 19 | reseal_speed_real | limit_board | raw_only_needs_review | needs_engineering_review | P1 | 1 | RAW001778 | ["minute", "limit_pool"] |
| 20 | sector_change_intensity | limit_board | raw_only_needs_review | needs_engineering_review | P1 | 1 | RAW001779 | ["sector_theme", "announcement"] |
| 21 | theme_leader_pull | theme_leader | raw_only_needs_review | needs_engineering_review | P1 | 1 | RAW001782 | ["minute", "sector_theme"] |
| 22 | auction_volume_ratio | auction_open | raw_only_needs_review | needs_engineering_review | P2 | 5 | RAW000048, RAW000297, RAW001038, RAW001368, RAW001369 | ["auction", "daily_ohlcv"]; ["daily_ohlcv", "auction"] |
| 23 | baidu_search_surge | misc_review | raw_only_needs_review | needs_engineering_review | P2 | 2 | RAW002917, RAW002980 | ["hot_rank"]; ["unknown"] |
| 24 | dragon_tiger_net_buy_ratio | theme_leader | raw_only_needs_review | needs_engineering_review | P2 | 2 | RAW002895, RAW002981 | ["lhb"] |
| 25 | famous_seat_buy | flow_lhb | raw_only_needs_review | needs_engineering_review | P2 | 2 | RAW000045, RAW000298 | ["lhb"] |
| 26 | famous_trader_buy | flow_lhb | raw_only_needs_review | needs_engineering_review | P2 | 2 | RAW002893, RAW002982 | ["lhb"] |
| 27 | guba_post_count | social_attention | raw_only_needs_review | needs_engineering_review | P2 | 2 | RAW002914, RAW002979 | ["hot_rank"] |
| 28 | institutional_clearing_day | flow_lhb | raw_only_needs_review | needs_engineering_review | P2 | 2 | RAW000147, RAW000314 | ["lhb"] |
| 29 | quant_vs_youzi_dominance | flow_lhb | raw_only_needs_review | needs_engineering_review | P2 | 2 | RAW000115, RAW000310 | ["lhb"] |
| 30 | famous_seat_premium_score | flow_lhb | raw_only_needs_review | needs_engineering_review | P2 | 1 | RAW001786 | ["lhb"] |
| 31 | has_convertible_bond | misc_review | raw_only_needs_review | needs_asof_check | P2 | 1 | RAW000309 | ["cross_market"] |
| 32 | institution_vs_youzi_conflict | flow_lhb | raw_only_needs_review | needs_engineering_review | P2 | 1 | RAW001787 | ["lhb"] |
| 33 | lhb_net_buy_to_amount | flow_lhb | raw_only_needs_review | needs_engineering_review | P2 | 1 | RAW001785 | ["daily_ohlcv", "lhb"] |
| 34 | regulatory_days | event_fundamental | raw_only_needs_review | needs_engineering_review | P2 | 1 | RAW000301 | ["announcement"] |
| 35 | seat_repeat_decay | flow_lhb | raw_only_needs_review | needs_engineering_review | P2 | 1 | RAW001788 | ["lhb"] |
| 36 | OFI | misc_review | raw_only_needs_review | needs_data_check | P3 | 3 | RAW002058, RAW002860, RAW002988 | ["level2"]; ["unknown"] |
| 37 | auction_922_conviction | limit_board | raw_only_needs_review | needs_engineering_review | P3 | 2 | RAW000153, RAW000342 | ["auction", "level2", "limit_pool"]; ["auction"] |
| 38 | famous_seat_repeat_decay | flow_lhb | raw_only_needs_review | needs_engineering_review | P3 | 2 | RAW000146, RAW000340 | ["lhb"] |
| 39 | ofi_last_30min | minute_hf | raw_only_needs_review | needs_engineering_review | P3 | 2 | RAW002861, RAW002989 | ["level2", "minute"]; ["minute"] |
| 40 | institution_net_buy | flow_lhb | raw_only_needs_review | needs_engineering_review | unknown | 4 | RAW000046, RAW001739, RAW001816, RAW002894 | ["daily_ohlcv", "lhb"]; ["lhb"] |
| 41 | VWAP | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 3 | RAW000949, RAW000950, RAW002075 | ["daily_ohlcv", "minute"]; ["minute"] |
| 42 | auction_gap | auction_open | raw_only_needs_review | needs_engineering_review | unknown | 3 | RAW000051, RAW001373, RAW001374 | ["auction"]; ["daily_ohlcv", "auction"] |
| 43 | seal_order_ratio | limit_board | raw_only_needs_review | needs_engineering_review | unknown | 3 | RAW001700, RAW001701, RAW001702 | ["limit_pool", "hot_rank"] |
| 44 | seal_order_ratio_real | limit_board | raw_only_needs_review | needs_engineering_review | unknown | 3 | RAW001705, RAW001706, RAW001707 | ["daily_ohlcv", "limit_pool"] |
| 45 | theme_strength | limit_board | raw_only_needs_review | needs_engineering_review | unknown | 3 | RAW001729, RAW001730, RAW001732 | ["daily_ohlcv", "sector_theme"] |
| 46 | vol_ratio | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 3 | RAW000719, RAW000727, RAW000736 | ["daily_ohlcv", "minute"]; ["minute"] |
| 47 | vol_ratio | auction_open | raw_only_needs_review | needs_engineering_review | unknown | 3 | RAW001040, RAW001371, RAW002775 | ["auction", "daily_ohlcv"]; ["auction"] |
| 48 | auction_gap_classification | auction_open | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001372, RAW002777 | ["auction"] |
| 49 | auction_gap_real | auction_open | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001754, RAW001756 | ["daily_ohlcv", "auction"] |
| 50 | auction_last_minute_stability | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001143, RAW002681 | ["minute", "auction"] |
| 51 | auction_open_pct | auction_open | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW000810, RAW000815 | ["daily_ohlcv", "auction"] |
| 52 | auction_weak_to_strong | auction_open | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW000085, RAW001810 | ["auction"] |
| 53 | daily_avg_30min | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW000718, RAW000741 | ["daily_ohlcv", "minute"] |
| 54 | discipline_score_realtime | misc_review | raw_only_needs_review | needs_data_check | unknown | 2 | RAW001516, RAW002823 | ["unknown"] |
| 55 | institution_buy_signal | flow_lhb | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW000568, RAW001740 | ["lhb"] |
| 56 | institution_sell_pressure | flow_lhb | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001741, RAW001817 | ["daily_ohlcv", "lhb"]; ["lhb"] |
| 57 | institutional_vs_hotmoney_ratio | flow_lhb | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001279, RAW002743 | ["lhb"] |
| 58 | intraday_consolidation_break | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001496, RAW002817 | ["minute"] |
| 59 | intraday_correlation_penalty | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001426, RAW002794 | ["minute"] |
| 60 | intraday_flow_reversal | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001550, RAW002838 | ["minute"] |
| 61 | intraday_n_shape_breakout | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001487, RAW002815 | ["minute"] |
| 62 | intraday_volume_price_divergence | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW000520, RAW000700 | ["minute", "daily_ohlcv"] |
| 63 | known_seat_historical_win_rate | flow_lhb | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001287, RAW002746 | ["lhb"] |
| 64 | last_30min_vol | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW000716, RAW002937 | ["daily_ohlcv", "minute"]; ["minute", "daily_ohlcv"] |
| 65 | market_impact | misc_review | raw_only_needs_review | needs_data_check | unknown | 2 | RAW000896, RAW000898 | ["unknown"] |
| 66 | portfolio_heat_score | misc_review | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001441, RAW002799 | ["hot_rank"] |
| 67 | r_last30 | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW002437, RAW002447 | ["minute", "daily_ohlcv"] |
| 68 | regulatory_window_escape_days | event_fundamental | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001243, RAW002729 | ["announcement"] |
| 69 | seal_time | limit_board | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW000002, RAW001111 | ["minute", "level2", "limit_pool"]; ["minute", "limit_pool"] |
| 70 | seat_buy_amount_ratio | flow_lhb | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW000499, RAW000500 | ["daily_ohlcv", "lhb"]; ["lhb", "daily_ohlcv"] |
| 71 | seat_premium_score | flow_lhb | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW001742, RAW001744 | ["lhb"] |
| 72 | vwap | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 2 | RAW000517, RAW001888 | ["minute", "daily_ohlcv"] |
| 73 | ABNORMAL_MOVE_BUDGET_UTILIZATION | event_fundamental | raw_only_needs_review | needs_engineering_review | unknown | 1 | RAW002727 | ["announcement"] |
| 74 | ASVI | misc_review | raw_only_needs_review | needs_engineering_review | unknown | 1 | RAW002262 | ["hot_rank"] |
| 75 | AUCTION_PRICE_DISCOVERY_QUALITY | auction_open | raw_only_needs_review | needs_engineering_review | unknown | 1 | RAW002778 | ["auction"] |
| 76 | Alpha360 | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 1 | RAW001856 | ["minute", "daily_ohlcv"] |
| 77 | BAIDU_ATTENTION | social_attention | raw_only_needs_review | needs_engineering_review | unknown | 1 | RAW002428 | ["hot_rank"] |
| 78 | CGO_A | minute_hf | raw_only_needs_review | needs_engineering_review | unknown | 1 | RAW002013 | ["minute", "daily_ohlcv"] |
| 79 | CNN_Factor_t | misc_review | raw_only_needs_review | needs_data_check | unknown | 1 | RAW002114 | ["unknown"] |
| 80 | COOLING_PERIOD_REENTRY_SIGNAL | event_fundamental | raw_only_needs_review | needs_engineering_review | unknown | 1 | RAW002732 | ["announcement"] |

## Recommended CC Prompt

```text
You are only doing factor-library engineering review. Do not train, do not run gpu_probe, do not change model/training code, and do not write the formal factor_registry until the promote list is reviewed.

Inputs:
1. C:\Users\zzzzzzl\Desktop\subagent\docs\canonical_factor_candidate_registry_20260517.md
2. E:\ashare_similarity_runtime\data\reports\prediction\canonical_factor_candidate_registry_20260517.json

Task:
1. Use priority_review_queue as the primary input, not the raw O001-O450 list.
2. For each candidate, decide promote/reject/defer.
3. For promote, provide exact formula, required columns, asof rule, duplicate check against C001-C292, and implementation site.
4. For defer, state exactly which data or formula decision is missing.
5. For reject, state whether it is duplicate, not a stock-day factor, not asof-safe, or not computable.
```

## Output JSON

- Machine-readable canonical registry: `E:\ashare_similarity_runtime\data\reports\prediction\canonical_factor_candidate_registry_20260517.json`
