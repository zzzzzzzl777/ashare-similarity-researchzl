# Next Factor Candidates -- 2026-05-05 Round 2

> Round: post-C062, second batch same day
> Goal: 20 new candidates (C063-C082) from three search paths
> Constraint: no training, no gpu_probe.py changes, no frozen_forward_config changes
> Data-first filter: only candidates using already cached data (verified parquet counts below)
> Existing duplicates checked against: C001-C062 + GPU_PROBE_STABLE_FEATURES (370) + TUSHARE_FACTOR_COLUMNS (46)

## Verified Data Cache (parquet counts)

| Source | Files | Ready |
|--------|------:|:-----:|
| moneyflow | 804 | YES |
| stk_limit | 804 | YES |
| stk_auction_o | 804 | YES |
| stk_auction_c | 804 | YES |
| stk_mins_5 | 14,291 | YES |
| limit_list_d | 804 | YES |
| daily_basic | 804 | YES |
| ths_hot | 623 | YES |
| cyq_perf | 3,194 | YES |
| margin_detail | 804 | YES |
| hk_hold | 774 | YES |
| moneyflow_hsgt | 778 | YES |
| moneyflow_ind_dc | 635 | YES |
| top_list | 804 | YES |
| top_inst | 804 | YES |
| stk_holdernumber | 804 | YES |
| ccass_hold | 775 | YES |
| index_dailybasic | 803 | YES |
| shibor | 804 | YES |

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 10 | Data fully cached, formula clear, non-redundant, directly computable |
| P1 | 7 | Strong logic, needs cross-sectional or multi-source join |
| P2 | 3 | Sparse or overlap concern |
| blocked | 0 | — |
| **Total** | **20** | |

## Duplicates Checked and Removed

- 尾盘 close_vs_vwap → C048 already covers vwap reclaim
- 集合竞价高开幅度 → C012 already covers gap normalized by limit
- 封板时间 raw → C046/C047 already cover seal time composites
- 资金流 5 日均值 → close to C003 persistence
- 热度排名 raw delta → C050 already covers hot_rank_momentum
- 龙虎榜出现频率 → similar logic to C062 afterglow

---

## P0 Candidates (10)

### C063: auction_open_volume_surprise

| Field | Value |
|-------|-------|
| factor_id | C063 |
| name | Auction Open Volume Surprise |
| family | auction |
| source_type | taoguba |
| source_ref | 打板选股 "竞价放巨量 = 主力抢筹意愿，但必须看相对值" |
| raw_idea | Opening auction volume relative to recent average — extreme values signal institutional pre-market conviction |
| computable_definition | `auction_open_vol / mean(volume, 5) - 1` (volume surprise ratio, 0 = normal) |
| data_need | stk_auction_o (vol) + daily volume (5-day mean) |
| asof_rule | T-day 9:25 auction complete |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | C043 uses log1p(auction_vol/avg_vol) × price premium; this is pure volume dimension |
| duplicate_check | C043 is price×volume interaction; this is pure volume surprise (no price premium multiplier). Orthogonal axis. |
| engineering_status | candidate_ready |
| priority | P0 |

### C064: intraday_vwap_slope

| Field | Value |
|-------|-------|
| factor_id | C064 |
| name | Intraday VWAP Slope |
| family | intraday_5m |
| source_type | social_live |
| source_ref | 游资实盘 "均价线斜率向上 = 全天资金持续流入，不是脉冲" |
| raw_idea | VWAP trending upward throughout the day means sustained buying, not a single spike |
| computable_definition | `linreg_slope(cumulative_vwap_series, n_bars=48) * 48` normalized to daily return scale from 5-min bars |
| data_need | stk_mins_5 (vwap per 5-min bar, 48 bars/day) |
| asof_rule | T-day 14:57 (all bars available) |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | close_vs_vwap (end-of-day snapshot only), C048 (vwap × volume, no slope) |
| duplicate_check | close_vs_vwap is level; C048 is level×volume; this captures trend/slope over time. Different dimension. |
| engineering_status | candidate_ready |
| priority | P0 |

### C065: last_hour_volume_acceleration

| Field | Value |
|-------|-------|
| factor_id | C065 |
| name | Last-Hour Volume Acceleration |
| family | intraday_5m |
| source_type | taoguba |
| source_ref | 尾盘战法 "最后一小时成交量占全天 > 30% = 尾盘资金涌入" |
| raw_idea | Fraction of daily volume concentrated in last hour signals tail-session institutional activity |
| computable_definition | `sum(volume, last_12_bars) / sum(volume, all_48_bars)` from 5-min bars (last hour = 12 bars) |
| data_need | stk_mins_5 |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | last_30min_return (price only), C049 tail_push_strength (return-based) |
| duplicate_check | C049 uses return × volume_ratio; this is pure volume concentration in last hour. No price dimension. |
| engineering_status | candidate_ready |
| priority | P0 |

### C066: broken_board_recovery_speed

| Field | Value |
|-------|-------|
| factor_id | C066 |
| name | Broken Board Recovery Speed |
| family | limit_list |
| source_type | taoguba |
| source_ref | 打板复盘 "炸板后快速回封 = 强主力，炸板不回封 = 弱势" |
| raw_idea | Stocks that break from limit-up but re-seal quickly have stronger main force than those that stay broken |
| computable_definition | `(open_times > 0) * seal_ratio * exp(-last_open_duration / 60)` where last_open_duration from limit_list_d |
| data_need | limit_list_d (open_times, seal_ratio, open durations) |
| asof_rule | T-day close (published ~16:00) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~1-3% daily (only stocks with open_times > 0 and final seal) |
| related_existing_features | C046 seal_stability (punishes opens); this rewards fast recovery from opens |
| duplicate_check | C046 penalizes any open; C066 specifically rewards recovery after open. Complementary, not redundant. |
| engineering_status | candidate_ready |
| priority | P0 |

### C067: moneyflow_concentration_ratio

| Field | Value |
|-------|-------|
| factor_id | C067 |
| name | Money Flow Concentration Ratio |
| family | moneyflow_derivative |
| source_type | github_paper |
| source_ref | Order flow concentration; institutional herding literature |
| raw_idea | When large+extra-large orders dominate total flow (high concentration), signal is more reliable |
| computable_definition | `(abs(buy_lg - sell_lg) + abs(buy_elg - sell_elg)) / (abs(net_mf_amount) + eps)` |
| data_need | tushare moneyflow (buy/sell by size tier) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | C009 main_force_divergence (lg vs elg direction); tushare_net_mf_amount (aggregate) |
| duplicate_check | C009 measures divergence between lg/elg; this measures how much total flow is driven by lg+elg. Different: direction disagreement vs size concentration. |
| engineering_status | candidate_ready |
| priority | P0 |

### C068: elg_net_persistence_3d

| Field | Value |
|-------|-------|
| factor_id | C068 |
| name | Extra-Large Order Net Persistence 3-Day |
| family | moneyflow_derivative |
| source_type | taoguba |
| source_ref | 短线跟庄 "超大单连续3天净买 = 主力建仓确认" |
| raw_idea | Consecutive days of extra-large order net buying is institutional position-building confirmation |
| computable_definition | `sum(sign(buy_elg - sell_elg) == 1, window=3) / 3` (fraction of last 3 days with positive elg net) |
| data_need | tushare moneyflow (buy_elg_amount, sell_elg_amount), 3-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | C003 mf_persistence_5d (total net_mf, 5-day); tushare_elg_buy_sell_ratio (single-day ratio) |
| duplicate_check | C003 uses total net_mf 5-day; this uses elg-specific 3-day. Different tier, different window. |
| engineering_status | candidate_ready |
| priority | P0 |

### C069: margin_momentum_5d

| Field | Value |
|-------|-------|
| factor_id | C069 |
| name | Margin Balance Momentum 5-Day |
| family | margin |
| source_type | github_paper |
| source_ref | Leveraged buying momentum; A-share margin factor literature |
| raw_idea | 5-day rate of change in margin balance captures leveraged buying acceleration |
| computable_definition | `(rzye[T] - rzye[T-5]) / rzye[T-5]` where rzye = margin financing balance |
| data_need | margin_detail (rzye), 5-day lag |
| asof_rule | T-day close (margin published T+1 morning) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~70% (margin-eligible stocks) |
| related_existing_features | C055 margin_chase_pressure (1-day delta × return); no existing multi-day margin momentum |
| duplicate_check | C055 is 1-day delta × price direction; this is 5-day pure margin momentum. Different temporal scale, no price interaction. |
| engineering_status | candidate_ready |
| priority | P0 |

### C070: hk_hold_acceleration

| Field | Value |
|-------|-------|
| factor_id | C070 |
| name | HK Holding Acceleration |
| family | hk_hold |
| source_type | github_paper |
| source_ref | Northbound smart money; acceleration of foreign holding changes |
| raw_idea | Change in holding change rate (second derivative) — accelerating foreign buying is more bullish than steady buying |
| computable_definition | `hk_ratio_delta[T] - hk_ratio_delta[T-5]` where hk_ratio_delta = day-over-day change in HK holding ratio |
| data_need | hk_hold (ratio), 6-day window |
| asof_rule | T-day close (hk_hold published T+1 morning) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~40-50% (HK-connect stocks only) |
| related_existing_features | C054 northbound_stock_alignment (1-day delta × sign(ret)) |
| duplicate_check | C054 is delta × price direction; this is pure acceleration (second derivative). No price interaction. |
| engineering_status | candidate_ready |
| priority | P0 |

### C071: close_auction_vs_last_trade

| Field | Value |
|-------|-------|
| factor_id | C071 |
| name | Close Auction vs Last Trade Price |
| family | auction |
| source_type | social_live |
| source_ref | 东财实盘 "收盘集合竞价相对14:57价格的偏移方向代表最后博弈" |
| raw_idea | If close auction price > 14:57 last trade price, final institutional consensus is bullish |
| computable_definition | `(close - last_trade_price_1457) / last_trade_price_1457` approx by `(close - last_5min_bar_close) / last_5min_bar_close` |
| data_need | stk_mins_5 (last bar close at 14:55) + daily close |
| asof_rule | T-day 15:00 (uses T-1 for 14:57 prediction) |
| leakage_risk | T-day value not available at 14:57; use T-1 lag |
| coverage_estimate | ~95% |
| related_existing_features | C044 auction_close_pressure (vwap-based, volume-weighted); this is pure price displacement |
| duplicate_check | C044 uses close_auction_vwap × volume; this is simple close-vs-last-trade displacement. Different construction. |
| engineering_status | candidate_ready |
| priority | P0 |

### C072: five_min_momentum_dispersion

| Field | Value |
|-------|-------|
| factor_id | C072 |
| name | 5-Min Return Momentum Dispersion |
| family | intraday_5m |
| source_type | github_paper |
| source_ref | Intraday realized volatility decomposition; directional vs diffusive component |
| raw_idea | Proportion of 5-min bars moving in same direction as daily return — high = trending day, low = choppy |
| computable_definition | `sum(sign(bar_ret) == sign(daily_ret), 48 bars) / 48` |
| data_need | stk_mins_5 (per-bar returns) + daily return |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | intraday_volatility (magnitude), range_pct (high-low); neither captures directional consistency |
| duplicate_check | Existing volatility is magnitude-based; this is directional consistency. New dimension. |
| engineering_status | candidate_ready |
| priority | P0 |

---

## P1 Candidates (7)

### C073: cyq_trapped_ratio_delta

| Field | Value |
|-------|-------|
| factor_id | C073 |
| name | CYQ Trapped Ratio Delta |
| family | cyq |
| source_type | taoguba |
| source_ref | 筹码分析 "解套比例快速增加 = 抛压释放完成" |
| raw_idea | Rapid increase in winner_rate from low base means trapped holders getting released, selling pressure fading |
| computable_definition | `max(winner_rate_delta_5d, 0) * (1 - winner_rate_lag_5)` where winner_rate_lag_5 = starting level |
| data_need | cyq_perf (winner_rate), 5-day lag |
| asof_rule | T-day close (cyq published T+1) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~80% |
| related_existing_features | C057 winner_rate_delta_5d (raw delta); this adds base-level interaction |
| duplicate_check | C057 is raw delta; this weights delta by how low the starting level was. Different: captures release-from-trap specifically. |
| engineering_status | candidate |
| priority | P1 |

### C074: market_moneyflow_regime

| Field | Value |
|-------|-------|
| factor_id | C074 |
| name | Market Moneyflow Regime |
| family | market_flow |
| source_type | github_paper |
| source_ref | Market-wide flow regime; total market net_mf z-score as context |
| raw_idea | Market-level net money flow z-score as a regime gate — strong market flow = all boats rise |
| computable_definition | `zscore(sum(net_mf_amount, all_stocks_today), window=20)` broadcast to all stocks |
| data_need | tushare moneyflow (aggregated across all stocks) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | 100% (market-level broadcast) |
| related_existing_features | C052 northbound_market_tailwind (foreign flow only); market_emotion_score (limit-based) |
| duplicate_check | C052 is northbound-only; market_emotion uses limit counts. This is domestic total flow regime. Different source. |
| engineering_status | candidate |
| priority | P1 |

### C075: holdernumber_concentration_trend

| Field | Value |
|-------|-------|
| factor_id | C075 |
| name | Holder Number Concentration Trend |
| family | capacity |
| source_type | social_live |
| source_ref | 雪球/东财 "股东人数减少 = 筹码集中 = 主力控盘" |
| raw_idea | Decreasing shareholder count over time means chip concentration, institutional control increasing |
| computable_definition | `(holdernumber[T-latest] - holdernumber[T-prev]) / holdernumber[T-prev]` using most recent two disclosure dates |
| data_need | stk_holdernumber (periodic disclosure, ~quarterly but some monthly) |
| asof_rule | Latest available disclosure date (low-frequency, lagged) |
| leakage_risk | none (uses disclosed historical data) |
| coverage_estimate | ~60% (not all stocks disclose frequently) |
| related_existing_features | tushare_free_share (static float, no trend) |
| duplicate_check | free_share is static level; this is holder count change rate. Different concept (concentration vs float). |
| engineering_status | candidate |
| priority | P1 |

### C076: intraday_range_position_last_hour

| Field | Value |
|-------|-------|
| factor_id | C076 |
| name | Intraday Range Position (Last Hour) |
| family | intraday_5m |
| source_type | taoguba |
| source_ref | 尾盘买入法 "收盘价在全天最高最低之间的位置 = 尾盘强弱" |
| raw_idea | Where the close sits within the last-hour range tells whether tail session ended strong or weak |
| computable_definition | `(close - low_last_12bars) / (high_last_12bars - low_last_12bars + eps)` |
| data_need | stk_mins_5 (last 12 bars high/low) + daily close |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | close_position (full-day range position); this is last-hour only |
| duplicate_check | close_position uses full-day high-low; this zooms into last-hour range. Different time granularity. |
| engineering_status | candidate |
| priority | P1 |

### C077: sector_flow_leader

| Field | Value |
|-------|-------|
| factor_id | C077 |
| name | Sector Flow Leadership |
| family | industry_flow |
| source_type | github_paper |
| source_ref | Sector rotation; identifying leading stocks within sector flow |
| raw_idea | Stock's moneyflow rank within its sector — top-ranked flow receivers benefit from sector rotation |
| computable_definition | `rank_within_sector(net_mf_amount)` normalized to [0,1] |
| data_need | tushare moneyflow + sector classification (ths_member or industry mapping) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~90% (depends on sector classification coverage) |
| related_existing_features | C053 industry_flow_alignment (stock vs industry aggregate); sector_strength_rank (price-based) |
| duplicate_check | C053 compares stock to industry total; this ranks within sector. Similar intent but different construction (rank vs difference). Moderate overlap concern. |
| engineering_status | candidate |
| priority | P1 |

### C078: index_relative_strength

| Field | Value |
|-------|-------|
| factor_id | C078 |
| name | Index Relative Strength (Market Context) |
| family | market_flow |
| source_type | github_paper |
| source_ref | Index momentum as market regime; alpha-beta decomposition |
| raw_idea | Market index 5-day z-scored return as context feature — stocks behave differently in up vs down market regimes |
| computable_definition | `zscore(index_close_pct_change, window=20)` broadcast using index_dailybasic (e.g., 000001.SH) |
| data_need | index_dailybasic (803 parquets) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | 100% (market-level broadcast) |
| related_existing_features | market_emotion_score (limit-count based); C074 (moneyflow regime) |
| duplicate_check | market_emotion uses limit counts; C074 uses flow. This uses pure index return momentum. Different signal source. |
| engineering_status | candidate |
| priority | P1 |

### C079: shibor_liquidity_shift

| Field | Value |
|-------|-------|
| factor_id | C079 |
| name | SHIBOR Liquidity Shift |
| family | macro |
| source_type | github_paper |
| source_ref | Interbank rate as liquidity regime proxy; SHIBOR → equity correlation in A-shares |
| raw_idea | Sharp rise in SHIBOR signals tightening liquidity environment — negative for leveraged/small-cap stocks |
| computable_definition | `zscore(shibor_overnight, window=20)` broadcast to all stocks |
| data_need | shibor (804 parquets) |
| asof_rule | T-day (SHIBOR published daily ~11:30) |
| leakage_risk | none |
| coverage_estimate | 100% (macro broadcast) |
| related_existing_features | none — no interest rate feature in current set |
| duplicate_check | No SHIBOR or interbank rate feature exists. New macro dimension. |
| engineering_status | candidate |
| priority | P1 |

---

## P2 Candidates (3)

### C080: ccass_foreign_acceleration

| Field | Value |
|-------|-------|
| factor_id | C080 |
| name | CCASS Foreign Holding Acceleration |
| family | hk_hold |
| source_type | github_paper |
| source_ref | CCASS settlement data for HK holding changes; finer-grained than hk_hold |
| raw_idea | CCASS-based holding change may capture intraday foreign flow not in end-of-day hk_hold snapshot |
| computable_definition | `ccass_ratio_delta[T] - ccass_ratio_delta[T-3]` (acceleration of CCASS-based HK holding) |
| data_need | ccass_hold (775 parquets) |
| asof_rule | T+1 morning (CCASS published next day) |
| leakage_risk | none for T+1 |
| coverage_estimate | ~30-40% (CCASS covers HK-connect stocks but granularity varies) |
| related_existing_features | C054 (hk_hold delta × sign(ret)), C070 (hk_hold acceleration) |
| duplicate_check | C070 uses hk_hold; this uses ccass_hold. Different data source but similar concept. May be highly correlated. |
| engineering_status | needs_validation |
| priority | P2 |

### C081: forecast_consensus_surprise

| Field | Value |
|-------|-------|
| factor_id | C081 |
| name | Forecast Consensus Surprise |
| family | fundamental |
| source_type | github_paper |
| source_ref | Earnings surprise factor; analyst forecast revision |
| raw_idea | Stock outperforming/underperforming relative to analyst consensus creates momentum |
| computable_definition | `(actual_eps - consensus_eps) / abs(consensus_eps + eps)` from forecast_vip |
| data_need | forecast_vip (393 parquets) |
| asof_rule | post-earnings disclosure (very low frequency) |
| leakage_risk | careful: must use only announced results, not forward estimates |
| coverage_estimate | ~30% (only stocks with analyst coverage and recent earnings) |
| related_existing_features | none — no fundamental/analyst factor in current set |
| duplicate_check | No analyst forecast feature exists. New dimension but very sparse/low-freq. |
| engineering_status | needs_validation |
| priority | P2 |

### C082: ths_daily_concept_heat

| Field | Value |
|-------|-------|
| factor_id | C082 |
| name | THS Daily Concept Board Heat |
| family | sentiment |
| source_type | social_live |
| source_ref | 同花顺概念板块涨幅/热度 "所属概念今日最强 = 明日溢价" |
| raw_idea | Stock's strongest concept board daily return as a proxy for thematic momentum |
| computable_definition | `max(concept_board_pct_change) for boards containing this stock` using ths_daily |
| data_need | ths_daily (803 parquets) + ths_member (board membership) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~85% (most stocks belong to at least one concept board) |
| related_existing_features | sector_pct_change_best (industry, not concept); C059 limit_theme_breadth (limit-up only) |
| duplicate_check | sector_pct_change_best uses industry; this uses concept boards. Similar intent, different grouping. Moderate overlap concern with sector features. |
| engineering_status | needs_validation |
| priority | P2 |

---

## Engineering Readiness Summary

| Status | IDs | Count |
|--------|-----|-------|
| candidate_ready | C063-C072 | 10 |
| candidate (needs minor engineering) | C073-C079 | 7 |
| needs_validation | C080-C082 | 3 |

## Implementation Priority: Top 8 (recommended for training framework)

| Rank | ID | Name | Family | Coverage | Why First |
|------|-----|------|--------|----------|-----------|
| 1 | C064 | intraday_vwap_slope | intraday_5m | ~95% | Captures sustained trend vs spike; builds on 780-pool vwap signal |
| 2 | C065 | last_hour_volume_acceleration | intraday_5m | ~95% | Pure volume timing; complements C049 tail_push |
| 3 | C072 | five_min_momentum_dispersion | intraday_5m | ~95% | New dimension (directional consistency); no existing equivalent |
| 4 | C067 | moneyflow_concentration_ratio | moneyflow | ~99% | Quality signal for existing moneyflow; high coverage |
| 5 | C068 | elg_net_persistence_3d | moneyflow | ~99% | Institutional streak detection; complements C009 |
| 6 | C063 | auction_open_volume_surprise | auction | ~95% | Pure volume axis for auction; complements C043 |
| 7 | C066 | broken_board_recovery_speed | limit_list | ~1-3% | High-signal for board play universe; sparse but powerful |
| 8 | C069 | margin_momentum_5d | margin | ~70% | Only multi-day margin factor; unique data source |

---

## Constraints Confirmation

- [x] No training executed
- [x] No gpu_probe.py changes
- [x] No frozen_forward_config changes
- [x] No passed/final_unseen/final_accepted claims
- [x] All candidates use verified cached data (parquet counts confirmed)
- [x] Duplicate check against C001-C062 + all existing features
- [x] All P2 candidates clearly marked with overlap/sparsity concerns

---

*Factor search round 2, 2026-05-05. 20 new candidates (C063-C082). No claims of passed/final_unseen/final_accepted.*
