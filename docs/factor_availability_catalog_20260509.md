# Factor Availability Catalog — 2026-05-09

Generated: 2026-05-09

## Classification Rules

- **A**: 14:57 可实时计算。训练用 T 日收盘/全日 proxy。不得删除。
- **B**: 可 T-1/history/realtime_proxy。必须做 delete vs proxy 对比。
- **C**: 硬不可用。从 formal training 删除。
- **D**: 待定/需工程审计。先审计后再归类。

---

## 1. Symbol OHLCV Family (~210 columns) — Class A

All price/volume/technical features derived from daily OHLCV bars.

| Sub-family | Examples | Class | Training Proxy | Live 14:57 Source |
|------------|---------|-------|---------------|-------------------|
| Returns (ret_1..ret_20) | ret_1, ret_3, ret_5, ret_10, ret_20 | A | EOD close | 14:57 latest price |
| Volume z-scores | volume_z_5, volume_z_10, volume_z_20 | A | EOD volume | 14:57 cumulative volume |
| Amount z-scores | amount_z_20, amount_chg_1 | A | EOD amount | 14:57 cumulative amount |
| Turnover | turnover, turnover_mean_5, turnover_chg_1 | A | EOD turnover | volume/float_share realtime |
| Range/body/shadow | range_pct, body_pct, upper_shadow_pct | A | EOD bar | 14:57 OHLC bar |
| Moving averages | ma_gap_5, ma_gap_10, ma_gap_20 | A | EOD close | 14:57 latest + history |
| Bollinger | bollinger_position_20, bollinger_width_20 | A | EOD | 14:57 latest |
| RSI/MACD/KDJ/CCI/ADX | rsi_6, macd_hist, kdj_k, cci_20, adx_14 | A | EOD | 14:57 bar + history |
| Lag features | ret_lag_0..ret_lag_9, range_lag_0..4 | A | EOD | 14:57 latest for lag_0, history for rest |
| Interaction terms | ret1_x_volume_z5, etc. | A | EOD | 14:57 |
| Limit-related | limit_up_like, limit_down_like, failed_limit_up | A | EOD | 14:57 price vs limit |
| Calendar | day_of_week_sin, month_start_3 | A | Date | Date |
| Short phase | short_phase_score_3, short_phase_days_3 | A | EOD | 14:57 + history |
| Cost/profit | cost_position_20, profit_pressure_20 | A | EOD | 14:57 latest + history |
| New high/consolidation | new_high_volume_ratio_20, consolidation_days_20 | A | EOD | 14:57 + history |

**Total A-class from this family: ~210 columns**

---

## 2. Cross-Section Family (~47 columns) — Class A

| Feature | Class | Reason |
|---------|-------|--------|
| cs_ret_1_rank, cs_amount_z_rank, cs_volume_z_rank, etc. | A | Computed from universe snapshot at 14:57 |
| cs_market_positive_rate, cs_market_mean_ret_1 | A | Aggregated from 14:57 snapshot |
| cs_emotion_score, cs_active_anomaly_score | A | Aggregated from 14:57 |

**Total A-class: ~47 columns**

---

## 3. Market Emotion + Board Structure Family (~135 columns) — Class A/B mix

### 3.1 Market Emotion (72 value columns + ~41 _available flags)

| Sub-group | Class | Reason |
|-----------|-------|--------|
| market_limit_up_count, market_limit_down_count | A | Computable from live limit pool |
| market_broken_board_count, market_broken_board_rate | A | Computable from live pool (zbgc) |
| market_seal_rate, market_emotion_score | A | Computable from live pool counts |
| emotion_phase_code, emotion_phase_* | A | Computable from history + today's counts |
| prev_limit_up_premium, prev_board_premium | A | Uses T-1 data (previous day stats) |
| prev_failed_limit_up_count/return/red_rate/loss_rate | A | T-1 historical |
| market_advance_decline_ratio | A | Computable from 14:57 snapshot |
| market_max_board_height, market_echelon_completeness | A | From live limit pool heights |
| market_board_promotion_rate* | A | From history + live pool |
| same_height_success_rate_* | A | Historical + today |
| volume_is_king_signal, ground_volume_risk | A | From market volume aggregation |
| full_position_trigger, bear_position_reduction | A | Regime signal from emotion history |

**All 72 value columns: Class A** (all derivable from limit pool + historical data + today's snapshot)

### 3.2 Board Structure (22 value columns)

| Feature | Class | Reason |
|---------|-------|--------|
| board_count, board_vs_max, board_height_suppression | A | From live limit pool |
| is_space_board, is_first_board, is_second_board, is_high_board | A | From live pool + T-1 |
| prev_board_count, board_promoted_today | A | T-1 + today's pool |
| volume_vs_prev, volume_health_zone, consecutive_shrink_days | A | Volume from bars + today |
| first_divergence_flag, first_negative_flag | A | From T-1 stats |

**All 22 value columns: Class A**

### 3.3 _available Flags (~41 for market_emotion + 14 for board_structure)

| Flag semantic | Class | Rule |
|---------------|-------|------|
| Limit pool data availability | A | Same as value — realtime from pools |
| Board structure availability | A | Same as value |

**All _available flags for this family: Class A** (they indicate whether limit_pool data was successfully computed for that date)

---

## 4. Tushare Baseline Family (~55 value + ~55 _available) — Mixed A/B/C

### 4.1 Hard Unavailable — Class C (DELETE)

| Feature | _available | Reason |
|---------|-----------|--------|
| tushare_lg_buy_sell_ratio | tushare_lg_buy_sell_ratio_available | Requires order-size bucket split |
| tushare_elg_buy_sell_ratio | tushare_elg_buy_sell_ratio_available | Requires order-size bucket split |
| tushare_mf_strength | tushare_mf_strength_available | Depends on lg/elg split |
| tushare_sm_sell_pressure | tushare_sm_sell_pressure_available | Depends on small-order split |
| tushare_main_force_divergence | tushare_main_force_divergence_available | Depends on lg/elg ratios |

**5 value + 5 _available = 10 columns: Class C**

### 4.2 Realtime Proxy Available — Class A

| Feature | _available | Live Source | Training Proxy |
|---------|-----------|------------|---------------|
| tushare_net_mf_amount | tushare_net_mf_amount_available | push2 f62 | EOD moneyflow |
| tushare_ff_adjusted_flow | tushare_ff_adjusted_flow_available | Recomputed from f62 + free_share | EOD moneyflow |
| tushare_volume_ratio | tushare_volume_ratio_available | today_vol / 5d_avg | EOD vol |
| tushare_free_share | tushare_free_share_available | T-1 daily_basic cache | T-1 |
| tushare_up_limit_distance | tushare_up_limit_distance_available | T-1 stk_limit | T-1 |
| tushare_down_limit_distance | tushare_down_limit_distance_available | T-1 stk_limit | T-1 |
| tushare_limit_range | tushare_limit_range_available | T-1 stk_limit | T-1 |
| tushare_vwap_deviation | (no explicit _available) | Snapshot amount/vol VWAP | EOD VWAP |
| tushare_close_vs_vwap | (no explicit _available) | Snapshot latest vs VWAP | EOD close vs VWAP |
| tushare_last_30min_return | (no explicit _available) | AkShare 5-min bars 14:30-14:55 | EOD minute bars |
| tushare_first_15min_volume_ratio | (no explicit _available) | AkShare minute bars | EOD minute bars |
| tushare_intraday_volatility | (no explicit _available) | From injected 14:57 bar | EOD full day |
| tushare_up_volume_ratio | (no explicit _available) | From injected bar | EOD full day |
| tushare_high_time_pct | (no explicit _available) | From injected bar | EOD full day |

**14 value columns + their _available: Class A**

### 4.3 Post-Close Forbidden — Class C (DELETE)

| Feature | _available | Reason |
|---------|-----------|--------|
| tushare_lhb_net_buy | tushare_lhb_net_buy_available | Dragon-tiger list T-day post-close |
| tushare_lhb_net_rate | tushare_lhb_net_rate_available | Post-close |
| tushare_inst_buy_count | tushare_inst_buy_count_available | Post-close |
| tushare_lhb_appeared | tushare_lhb_appeared_available | Post-close |
| tushare_inst_net_buy | tushare_inst_net_buy_available | Post-close |
| tushare_rzye | tushare_rzye_available | Margin T-day post-close |
| tushare_rzye_delta_pct | tushare_rzye_delta_pct_available | Post-close |
| tushare_rzmre_ratio | tushare_rzmre_ratio_available | Post-close |
| tushare_margin_net | tushare_margin_net_available | Post-close |
| tushare_rqye_ratio | tushare_rqye_ratio_available | Post-close |
| tushare_auction_close_vwap_ratio | tushare_auction_close_vwap_ratio_available | 15:00 close auction |
| tushare_auction_close_vol | tushare_auction_close_vol_available | 15:00 close auction |
| tushare_float_relative_impact | tushare_float_relative_impact_available | Depends on flow structure |

**13 value + 13 _available = 26 columns: Class C**

### 4.4 T-1 Proxy Possible — Class B (compare delete vs T-1)

| Feature | _available | Live Source | Policy |
|---------|-----------|------------|--------|
| tushare_winner_rate | tushare_winner_rate_available | T-1 cyq_perf | T-1 proxy |
| tushare_cost_concentration | tushare_cost_concentration_available | T-1 cyq_perf | T-1 proxy |
| tushare_cost_position | tushare_cost_position_available | T-1 cyq_perf | T-1 proxy |
| tushare_hot_rank | tushare_hot_rank_available | T-1 ths_hot | compare |
| tushare_hot_value | tushare_hot_value_available | T-1 ths_hot | compare |
| tushare_holder_num | tushare_holder_num_available | T-1 quarterly | compare |
| tushare_holder_num_delta_pct | tushare_holder_num_delta_pct_available | T-1 quarterly | compare |
| tushare_hk_ratio | tushare_hk_ratio_available | T-1 HK hold | compare |
| tushare_hk_ratio_delta_1d | tushare_hk_ratio_delta_1d_available | T-1 HK hold | compare |

**9 value + 9 _available = 18 columns: Class B**

### 4.5 Auction-Open — Class A

| Feature | _available | Live Source |
|---------|-----------|------------|
| tushare_auction_open_vwap_ratio | available | Known by 09:25 |
| tushare_auction_open_vol | available | Known by 09:25 |

**2 value + 2 _available = 4 columns: Class A**

### 4.6 Limit Pool Compatibility — Class A

| Feature | Live Source |
|---------|------------|
| tushare_seal_ratio | Live limit pool |
| tushare_open_times | Live limit pool |
| tushare_first_time_minutes | Live limit pool |
| tushare_up_stat_days | Live limit pool + history |
| tushare_limit_type | Live limit pool |
| tushare_limit_turnover | Live limit pool |

**6 value + 6 _available = 12 columns: Class A**

### 4.7 Daily-Derived (19 trainable factor columns) — Class A

All C141-C162 factor columns are computed from historical daily bars + today's injected bar at 14:57:

| Feature | factor_id | Class |
|---------|-----------|-------|
| tushare_price_vs_cost_20d | C154 | A |
| tushare_abnormal_3d_deviation | C156 | A |
| tushare_vol_gain_20d | C157 | A |
| tushare_inv_t_20d | C158 | A |
| tushare_asr_60d | C159 | A |
| tushare_illiq_classic_20d | C161 | A |
| tushare_ato_120d | C162 | A |
| tushare_volume_sufficiency_ratio | C141 | A |
| tushare_anti_drop_strength_20d | C143 | A |
| tushare_multi_wave_count_60d | C151 | A |
| tushare_prev_top20_chase_mean | C152 | A |

---

## 5. Limit Pool Family (~60 columns) — Class A

All `real_*` columns are fetched from live AkShare limit pool APIs at 14:57.

**60 columns (30 value + 30 _available): All Class A**

---

## 6. Minute Intraday Family (~58 columns) — Class A

All `minute_*` columns are computable from 5-minute bars available at 14:57 (using bars up to 14:55).

**29 value + 29 _available: All Class A**

---

## 7. TGB Factor Family (~28 columns) — Class B

TGB (TaoGuBa) factors use forum post analysis data. Historical values are cached. Live values require T-1 or realtime scraping.

| Feature | Class | Live Source |
|---------|-------|------------|
| tgb_ma_alignment_score | B | T-1 cached TGB score |
| tgb_ma_divergence_5 | B | T-1 |
| tgb_pullback_health | B | T-1 |
| tgb_board_height_vs_max | B | T-1 + live pool |
| tgb_board_quality_trend | B | T-1 |
| tgb_zhaban_recovery_score | B | T-1 |
| tgb_volume_buildup_score | B | T-1 |
| tgb_eod_rush_risk | B | T-1 |
| tgb_market_max_height | B | T-1 + live pool |
| tgb_nuclear_button_count | B | T-1 + live pool |
| tgb_mid_collapse_rate | B | T-1 |
| tgb_retreat_intensity | B | T-1 |
| tgb_new_first_board_count | B | T-1 + live pool |
| tgb_leader_break_signal | B | T-1 |

**14 value + 14 _available = 28 columns: Class B** (must compare delete vs T-1)

---

## 8. THS Sector Family (~12 columns) — Class B (per-column split)

Per plan §4A.1, THS must be split per-column:

| Feature | Class | Reason | Policy Candidates |
|---------|-------|--------|-------------------|
| sector_pct_change_best | B | T-1 ths_daily available; could realtime if compute from member stocks | delete / T-1 / realtime_proxy |
| sector_strength_rank | B | T-1 ths_daily; could rank from member pct_change | delete / T-1 / realtime_proxy |
| sector_limit_up_count | A or B | Live limit_pool can count by concept membership | delete / T-1 / live_pool_proxy |
| sector_divergence | B | Computed from duration streak, T-1 possible | delete / T-1 |
| sector_duration_days | B | T-1 streak + intraday continuation | delete / T-1 |
| sector_climax_signal | B | Derived from duration+divergence | delete / T-1 |

| _available Flag | Class | Rule |
|-----------------|-------|------|
| sector_pct_change_best_available | B | Same as value |
| sector_strength_rank_available | B | Same as value |
| sector_limit_up_count_available | B | Same as value |
| sector_divergence_available | B | Same as value |
| sector_duration_days_available | B | Same as value |
| sector_climax_signal_available | B | Same as value |

**6 value + 6 _available = 12 columns: Class B** (compare delete / T-1 / realtime_proxy)

---

## 9. Cross-Market Family (~18 columns) — Class A (excluded from training)

Cross-market index returns (cross_sh000001_ret_1, etc.) are A-class (realtime from index snapshot) but excluded by `exclude_feature_prefix = ("cross_",)`.

**18 columns: Class A but excluded by prefix rule**

---

## 10. Summary Statistics

| Class | Value Columns | _available Columns | Total | Treatment |
|-------|--------------|-------------------|-------|-----------|
| A | ~430 | ~185 | ~615 | Keep, train with EOD proxy |
| B | ~29 | ~26 | ~55 | Compare delete vs T-1/proxy |
| C | ~18 | ~18 | ~36 | Delete from formal training |
| D | 0 | 0 | 0 | None currently |
| Excluded (cross_) | 9 | 9 | 18 | Excluded by prefix |
| Meta/label | ~12 | 0 | ~12 | Not features |
| **TOTAL** | | | **~817** | |

## 11. THS Sector Per-Column Table (per plan §4A.1)

| feature_name | original_source | eod_training_proxy | live_1457_formula | availability_class | policy_candidates | reason |
|---|---|---|---|---|---|---|
| sector_pct_change_best | ths_daily parquet | T-day concept pct_change top | T-1 value or realtime member avg | B | delete/T-1/realtime_proxy | T-1 ths_daily published ~16:00 |
| sector_strength_rank | ths_daily parquet | T-day concept rank | T-1 rank or realtime rank from members | B | delete/T-1/realtime_proxy | Same source |
| sector_limit_up_count | limit_list_d + ths_member | T-day limit count by concept | Live pool count by concept membership | B→A | delete/T-1/live_pool | Live pool makes this partially A |
| sector_divergence | computed | T-day streak metric | T-1 streak value | B | delete/T-1 | Streak from ths_daily history |
| sector_duration_days | computed | T-day streak days | T-1 value + today's direction | B | delete/T-1 | Streak counter |
| sector_climax_signal | computed | From duration + divergence | T-1 derived | B | delete/T-1 | Composite |

## 12. Self-Audit Gate

| Check | Result |
|-------|--------|
| Every feature family classified | PASS |
| A-class not deleted | PASS (confirmed live scripts compute them) |
| B-class has policy candidates listed | PASS |
| C-class deletion reason documented | PASS |
| THS per-column split done | PASS |
| _available flags classified same as value | PASS |
| No unknown D-class remaining | PASS |
| P0 issues | 0 |
| P1 issues | 0 |
| Proceed to data quality gate | YES |
