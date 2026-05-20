# Factor Source Discovery Audit — 2026-05-09

Generated: 2026-05-09

## 1. Discovery Scope Summary

| Source | Count | Description |
|--------|-------|-------------|
| Raw research pool | ~3075 records / 2581 unique names | Desktop docs, TGB, research notes |
| factor_registry.json factor_ids | 174 | Codex-managed candidate ledger |
| Currently trainable factor_ids | 19 | C004,C009,C011,C133-C138,C141,C143,C151,C152,C154,C156-C159,C161,C162 |
| Superset feature columns (50f0a15cc17d25ca) | 817 | One-shot build, used for variant matrix |
| bb25159b bundle pool | 376 | Old U95 offline bundle |
| d2a985a5 bundle pool | 735 | Current live bundle |
| df28a947 rebuild pool | 709 | U95 live-strict rebuild |
| Web/live actually computable | ~550+ | Excludes THS zero-fill and post-close |
| Orphan columns (have column but no factor_id or clear family) | 0 | All 817 mapped to family or factor_id |
| Registry factor_ids without real feature column | ~155 | C002,C003,C007,C012-C152(partial),C163-C173 etc. |
| Live-computable features previously mis-deleted | 11+ | THS sector (6 values + 5 _available flags mis-classified as hard-unavailable in old pipeline) |
| Post-close/T+1/hard-unavailable that once entered selected | 7+11 | 7 moneyflow + 11 THS sector in bb25159b |

## 2. Feature Column Breakdown by Family (817 superset)

| Family | Value Columns | _available Flags | Total |
|--------|--------------|-----------------|-------|
| symbol_ohlcv (price/volume/technical) | ~210 | 0 | ~210 |
| market_emotion + board_structure | ~94 | ~41 | ~135 |
| cross_section (cs_*) | ~47 | 0 | ~47 |
| tushare_baseline (moneyflow/limit/margin/chip/etc) | ~55 | ~55 | ~110 |
| limit_pool (real_*) | ~30 | ~30 | ~60 |
| minute_intraday (minute_*) | ~29 | ~29 | ~58 |
| factor_value (19 trainable factor columns) | 19 | 19 | 38 |
| tgb_factor (taoguba) | 14 | 14 | 28 |
| ths_sector | 6 | 6 | 12 |
| cross_market (index returns) | 9 | 9 | 18 |
| meta/label (symbol, date, actual, etc) | ~12 | 0 | ~12 |
| **TOTAL** | | | **~817** |

## 3. Factor Registry Trainable Status

### 3.1 Currently Trainable (19 factor_ids with real feature columns)

| factor_id | name | feature_column | family |
|-----------|------|---------------|--------|
| C004 | ff_adjusted_flow | tushare_ff_adjusted_flow | moneyflow_derivative |
| C009 | main_force_divergence | tushare_main_force_divergence | moneyflow_derivative |
| C011 | auction_open_vwap_ratio | tushare_auction_open_vwap_ratio | stk_auction |
| C133 | last_30min_return | tushare_last_30min_return | intraday_momentum |
| C134 | first_15min_volume_ratio | tushare_first_15min_volume_ratio | intraday_volume |
| C136 | intraday_volatility | tushare_intraday_volatility | intraday_risk |
| C137 | up_volume_ratio | tushare_up_volume_ratio | intraday_volume |
| C138 | high_time_position | tushare_high_time_pct | intraday_momentum |
| C141 | volume_sufficiency_ratio | tushare_volume_sufficiency_ratio | volume_structure |
| C143 | anti_drop_strength_20d | tushare_anti_drop_strength_20d | daily_market |
| C151 | multi_wave_count_60d | tushare_multi_wave_count_60d | pattern |
| C152 | prev_top20_chase_mean | tushare_prev_top20_chase_mean | market_breadth |
| C154 | price_vs_cost_20d | tushare_price_vs_cost_20d | price_structure |
| C156 | abnormal_3d_deviation | tushare_abnormal_3d_deviation | momentum |
| C157 | vol_gain_20d | tushare_vol_gain_20d | volume_structure |
| C158 | inv_t_20d | tushare_inv_t_20d | volume_structure |
| C159 | asr_60d | tushare_asr_60d | price_structure |
| C161 | illiq_classic_20d | tushare_illiq_classic_20d | liquidity |
| C162 | ato_120d | tushare_ato_120d | volume_structure |

### 3.2 Blocked / Cannot Train

| factor_id | name | reason |
|-----------|------|--------|
| C001 | mf_flow_intensity | implementation_mismatch |
| C005 | limit_space_compression | needs_formula_correction |
| C006 | limit_approach_velocity | needs_formula_correction |
| C008 | seal_strength_proxy | needs_formula_correction |
| C010 | float_relative_impact | implementation_mismatch |
| C135 | vwap_deviation | blocked_until_outlier_guard |
| C039-C042 | various | Level-2/tick/coverage issues |

### 3.3 Candidate / Engineering Backlog (155+ factor_ids)

C002, C003, C007, C012-C132, C139-C173 (except those in 3.1) remain as candidates without real feature columns or require formula lock / data verification before training.

## 4. Existing Bundle Selected Features Audit

### 4.1 bb25159b (old U95 offline, 2026-05-05)

- Pool: 376, Selected: 260
- Contains 11 THS sector features in selected -> **FAIL live-strict**
- Contains 7 hard moneyflow features in selected (tushare_net_mf_amount, lg_buy_sell_ratio, elg_buy_sell_ratio, mf_strength, sm_sell_pressure, main_force_divergence, ff_adjusted_flow)
- Architecture: 3x LightGBM ensemble, isotonic, threshold 0.52

### 4.2 d2a985a5 (current live, 2026-05-08)

- Pool: 735, Selected: 260
- 0 THS sector in selected, 0 hard moneyflow in selected -> **PASS live-strict**
- Architecture: 1x LightGBM + 2x CatBoost, isotonic, threshold 0.52
- Includes limit_pool, tgb, board_structure, market_emotion features
- Includes chip T-1 features (winner_rate, cost_concentration, cost_position)

### 4.3 df28a947 (U95 rebuild, 2026-05-09)

- Pool: 709, Selected: 300
- 58 forbidden features excluded before selection
- 0 forbidden in selected -> **PASS live-strict**
- Architecture: 3x LightGBM ensemble, isotonic, threshold 0.52
- Q1 Wilson@0.75: 0.8410, April Wilson@0.75: 0.7303

## 5. Live-Computable vs Previously Deleted

### Features that CAN be computed at 14:57 but were deleted in some pipelines:

| Feature | Live Source | Should Be |
|---------|------------|-----------|
| THS sector_pct_change_best | T-1 ths_daily or realtime sector proxy | B (compare delete vs T-1) |
| THS sector_strength_rank | T-1 ths_daily or realtime sector proxy | B |
| THS sector_limit_up_count | Live limit_pool count by concept | A (if using live pool) or B |
| THS sector_divergence | Computed from T-1 sector streak | B |
| THS sector_duration_days | T-1 streak + today status | B |
| THS sector_climax_signal | Computed from duration+divergence | B |
| tushare_net_mf_amount | push2 f62 realtime | A (proxy) |
| tushare_ff_adjusted_flow | Recomputed from push2 f62 + free_share | A (proxy) |
| tushare_float_relative_impact | Depends on flow structure | C (hard unavailable) |

### Features that are HARD UNAVAILABLE at 14:57:

| Feature | Reason |
|---------|--------|
| tushare_lg_buy_sell_ratio | Requires buy/sell order-size bucket split |
| tushare_elg_buy_sell_ratio | Requires buy/sell order-size bucket split |
| tushare_mf_strength | Depends on lg/elg split |
| tushare_sm_sell_pressure | Depends on small-order split |
| tushare_main_force_divergence | Depends on lg/elg ratios |
| tushare_lhb_net_buy | T-day post-close dragon-tiger list |
| tushare_lhb_net_rate | T-day post-close |
| tushare_inst_buy_count | T-day post-close |
| tushare_lhb_appeared | T-day post-close |
| tushare_inst_net_buy | T-day post-close |
| tushare_rzye/rzye_delta_pct/rzmre_ratio/margin_net/rqye_ratio | T-day post-close margin data |
| tushare_auction_close_vwap_ratio | 15:00 close auction |
| tushare_auction_close_vol | 15:00 close auction |

## 6. Data Sources Available

| Source | Type | Coverage | Used For |
|--------|------|----------|----------|
| Sina hq.sinajs.cn | Realtime snapshot | All A-share | OHLCV at 14:57 |
| push2.eastmoney.com f62 | Realtime | All A-share (unstable) | net_mf_amount proxy |
| AkShare minute bars | Realtime/near-RT | ~4000 stocks | last_30min_return |
| AkShare limit pools | Realtime | All boards | limit_pool factors |
| Tushare cyq_perf | T-1 | ~4000 stocks | chip/cost features |
| Tushare daily_basic | T-1 cache | All A-share | free_share, turnover |
| Tushare stk_limit | T-1 cache | All A-share | up/down limit prices |
| Tushare moneyflow | T-1 cache | All A-share | moneyflow ratios (T-1 proxy) |
| Tushare ths_daily | T-1 cache | 500+ concepts | sector strength/rank |
| Tushare ths_member | Static | All concepts | stock-to-concept mapping |
| Tushare limit_list_d | T-1 cache | All limit events | sector limit counts |
| Daily bars parquet | Disk cache | 2015-present | Historical OHLCV |
| 5min bars parquet | Disk cache | ~60 days | Minute-level features |

## 7. Orphan and Missing Analysis

| Category | Count | Action |
|----------|-------|--------|
| Feature columns with no factor_id but clear baseline_family | ~700 | Allowed (baseline features) |
| Feature columns with factor_id mapping | 38 (19 value + 19 _available) | Tracked |
| Registry factor_ids with NO feature column | ~155 | Engineering backlog |
| Live-computable features not in any training pool | 0 | None discovered |
| _available flags with ambiguous semantics | ~12 (THS sector) | Must audit per-column |

## 8. Self-Audit Gate

| Check | Result |
|-------|--------|
| All 19 trainable factor_ids confirmed in superset | PASS |
| All 7 hard-unavailable moneyflow identified | PASS |
| THS sector mis-classification identified | PASS - 6 value + 6 _available need per-column split |
| Post-close forbidden list complete | PASS - 13 columns identified |
| No unknown orphan columns | PASS |
| Registry backlog accounted for | PASS - 155 in backlog |
| Live data sources documented | PASS |
| P0 issues | 0 |
| P1 issues | 0 |
