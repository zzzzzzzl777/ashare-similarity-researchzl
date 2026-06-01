# Next Factor Candidates -- 2026-05-03

> Round: post-tushare-tier1 ablation
> Goal: derivative factors from 8 validated tushare features + stk_auction Tier1b
> Constraint: no training, no gpu_probe.py changes, no frozen_forward_config changes
> Existing duplicates checked against: GPU_PROBE_STABLE_FEATURES (370), GPU_PROBE_EXPANDED_FEATURES, TUSHARE_FACTOR_COLUMNS (46)

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 12 | Data exists, T-day computable, directly from tushare tier1 or OHLCV, not redundant |
| P1 | 19 | Strong logic but needs cross-sectional rank, multi-day window, or minor new engineering |
| P2 | 7 | Inspirational but formula unclear, may overlap, or sparse coverage |
| blocked | 4 | Future function, Level-2, or unrecoverable coverage issue |
| **Total** | **42** | |

## Existing Features Checked (Duplicates Removed)

The following proposed ideas were **dropped** because equivalent columns already exist in expanded:
- CLV / close_location_value -- same as `close_position`
- Abnormal volume z-score 20d -- same as `volume_z_20`
- Intraday vs overnight reversal -- same as `overnight_vs_intraday`
- Corwin-Schultz spread -- already `corwin_schultz_spread`
- Turnover acceleration 5d -- similar to `turnover_chg_5`
- 5d volume-price divergence -- similar to `volume_price_divergence_5`

---

## P0 Candidates (12)

### C001: mf_flow_intensity

| Field | Value |
|-------|-------|
| name | Money Flow Intensity |
| source_type | taoguba |
| source_ref | "Capital Support Intensity" -- net flow as fraction of total turnover |
| raw_idea | Large-order net inflow as fraction of total turnover, measures main force absorption depth |
| computable_definition | `net_mf_amount / amount` where amount = daily turnover value |
| data_need | tushare moneyflow (net_mf_amount) + daily amount |
| asof_rule | T-day close, all fields known |
| leakage_risk | none |
| coverage_estimate | same as moneyflow (~99% of trading days for active stocks) |
| related_existing_features | tushare_net_mf_amount (raw level, not normalized) |
| family | moneyflow_derivative |
| priority | P0 |
| engineering_status | candidate |
| reason | Normalizes the strongest signal by turnover; flow of 1M means different things for 10M vs 1B daily turnover |

### C002: mf_momentum_5d

| Field | Value |
|-------|-------|
| name | Money Flow Momentum 5-Day |
| source_type | github_paper |
| source_ref | Chaikin Money Flow momentum; WorldQuant Alpha101 concept |
| raw_idea | Net flow acceleration vs trailing 5-day mean |
| computable_definition | `(net_mf_amount[T] - mean(net_mf_amount[T-5:T-1])) / (std(net_mf_amount[T-5:T-1]) + eps)` |
| data_need | tushare moneyflow, 5-day rolling window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% (needs 5 consecutive trading days) |
| related_existing_features | tushare_net_mf_amount (level only, no momentum) |
| family | moneyflow_derivative |
| priority | P0 |
| engineering_status | candidate |
| reason | net_mf_amount is a level; z-score captures whether today's flow is unusually strong vs recent history |

### C003: mf_persistence_5d

| Field | Value |
|-------|-------|
| name | Money Flow Persistence 5-Day |
| source_type | github_paper |
| source_ref | Jegadeesh-Titman momentum persistence applied to flow data |
| raw_idea | Fraction of recent days with positive net main force flow |
| computable_definition | `sum(net_mf_amount > 0, window=5) / 5` |
| data_need | tushare moneyflow, 5-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_net_mf_amount (single-day, no streak) |
| family | moneyflow_derivative |
| priority | P0 |
| engineering_status | candidate |
| reason | Sustained buying (5/5 positive) is qualitatively different from one spike; binary transform removes magnitude noise |

### C004: ff_adjusted_flow

| Field | Value |
|-------|-------|
| name | Free-Float-Adjusted Flow |
| source_type | taoguba |
| source_ref | "Float Capacity Constraint" -- flow per unit of free float market cap |
| raw_idea | Same 100M net inflow means entirely different things for 3B vs 30B market cap stocks |
| computable_definition | `net_mf_amount / (free_share * close)` |
| data_need | tushare moneyflow + daily_basic (free_share) + close |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_net_mf_amount (raw), tushare_free_share (raw); this is their interaction |
| family | moneyflow_derivative |
| priority | P0 |
| engineering_status | candidate |
| reason | Combines 2 of the 8 validated features into a capacity-normalized flow metric; confirmed by both taoguba and academic sources |

### C005: limit_space_compression

| Field | Value |
|-------|-------|
| name | Limit-Up Space Compression |
| source_type | taoguba |
| source_ref | "Limit-Up Space Compression" -- fraction of upside range consumed |
| raw_idea | Closer to limit-up relative to total range, higher probability of next-day spike |
| computable_definition | `1 - up_limit_distance / limit_range` (values near 1 = very close to up-limit) |
| data_need | tushare stk_limit (up_limit_distance, limit_range) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_up_limit_distance (absolute), tushare_limit_range (absolute); this is their ratio |
| family | stk_limit_derivative |
| priority | P0 |
| engineering_status | candidate |
| reason | up_limit_distance alone doesn't distinguish 10%-limit vs 20%-limit boards; this normalizes by regime |

### C006: limit_approach_velocity

| Field | Value |
|-------|-------|
| name | Limit Approach Velocity |
| source_type | github_paper |
| source_ref | A-share microstructure; "Limit Approach Speed" concept |
| raw_idea | Price momentum toward limit-up measured by day-over-day change in distance |
| computable_definition | `up_limit_distance[T-1] - up_limit_distance[T]` (positive = getting closer) |
| data_need | tushare stk_limit, 1-day lag |
| asof_rule | T-day close (uses T-1 for delta, no leakage) |
| leakage_risk | none |
| coverage_estimate | ~99% (needs 2 consecutive days) |
| related_existing_features | tushare_up_limit_distance (level, no velocity) |
| family | stk_limit_derivative |
| priority | P0 |
| engineering_status | candidate |
| reason | First derivative of validated feature; stocks accelerating toward limit have different next-day profile than static positions |

### C007: limit_range_utilization

| Field | Value |
|-------|-------|
| name | Limit Range Utilization |
| source_type | github_paper |
| source_ref | Intraday volatility relative to constraints; A-share specific |
| raw_idea | How much of the allowed price range was actually used intraday |
| computable_definition | `(high - low) / (limit_range * prev_close)` where limit_range is proportional range |
| data_need | daily OHLCV + tushare stk_limit |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | range_pct (= (high-low)/prev_close, not limit-normalized), tushare_limit_range |
| family | stk_limit_derivative |
| priority | P0 |
| engineering_status | candidate |
| reason | range_pct exists but normalizes by price, not by constraint; utilization near 1.0 means stock used full allowed range |

### C008: seal_strength_proxy

| Field | Value |
|-------|-------|
| name | Seal Strength Proxy |
| source_type | taoguba |
| source_ref | "Seal Strength Proxy" -- ELG buying near limit implies seal intent |
| raw_idea | Higher ELG buy/sell ratio + closer to limit = higher seal probability |
| computable_definition | `elg_buy_sell_ratio * (1 - up_limit_distance / limit_range)` |
| data_need | tushare moneyflow (elg_buy_sell_ratio) + stk_limit (up_limit_distance, limit_range) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_elg_buy_sell_ratio, tushare_up_limit_distance, tushare_limit_range (all individual) |
| family | interaction |
| priority | P0 |
| engineering_status | candidate |
| reason | Product of 3 validated features capturing a specific trading narrative (seal-board); not representable as any single existing feature |

### C009: main_force_divergence

| Field | Value |
|-------|-------|
| name | Main Force Divergence |
| source_type | taoguba |
| source_ref | "Main Force Divergence" -- disagreement between large and extra-large orders |
| raw_idea | Large vs extra-large orders disagreeing means institutional-level divergence |
| computable_definition | `abs(lg_buy_sell_ratio - elg_buy_sell_ratio)` |
| data_need | tushare moneyflow |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_lg_buy_sell_ratio, tushare_elg_buy_sell_ratio (correlated but divergence not captured) |
| family | moneyflow_derivative |
| priority | P0 |
| engineering_status | candidate |
| reason | Both ratios are validated individually; their difference captures a dimension (institutional disagreement) that neither alone measures |

### C010: float_relative_impact

| Field | Value |
|-------|-------|
| name | Float-Relative Volume Impact |
| source_type | taoguba |
| source_ref | "Float-Relative Volume Impact" -- turnover stress on free float at elevated volume |
| raw_idea | Elevated volume ratio while turnover-to-float ratio is high means extreme pressure |
| computable_definition | `volume_ratio * volume / free_share` |
| data_need | tushare daily_basic (volume_ratio, free_share) + daily volume |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_volume_ratio (no float normalization), tushare_free_share (no volume interaction) |
| family | capacity_derivative |
| priority | P0 |
| engineering_status | candidate |
| reason | Combines volume ratio with float scarcity; small float under high relative volume = extreme pressure, neither component alone captures this |

### C011: auction_open_vwap_ratio (Tier1b)

| Field | Value |
|-------|-------|
| name | Auction Open VWAP Ratio |
| source_type | taoguba |
| source_ref | "Auction Strength" -- opening auction price relative to previous close |
| raw_idea | Auction VWAP / prev close, measures opening auction intensity |
| computable_definition | `tushare_auction_open_vwap_ratio` (already computed in free_data_factors.py) |
| data_need | tushare stk_auction_o (804 parquets cached) |
| asof_rule | T-day 9:25 (auction completes before market open) |
| leakage_risk | none |
| coverage_estimate | ~95%+ (804 days cached, high coverage) |
| related_existing_features | gap_pct (= (open-prev_close)/prev_close); this uses auction VWAP not opening price |
| family | stk_auction_tier1b |
| priority | P0 |
| engineering_status | candidate |
| reason | Already coded as TUSHARE_FACTOR_COLUMNS column but NOT in expanded; 804 days cached. Promote candidate for Tier1b ablation. VWAP != open price: captures whether auction volume was front- or back-loaded |

### C012: auction_gap_normalized

| Field | Value |
|-------|-------|
| name | Auction Gap Normalized by Limit Range |
| source_type | taoguba |
| source_ref | "Auction Strength Ratio" -- gap-up relative to allowed range |
| raw_idea | Gap-up magnitude / total limit range, eliminates 10%/20% board-type differences |
| computable_definition | `(open - prev_close) / (limit_range * prev_close)` |
| data_need | daily OHLCV + tushare stk_limit (limit_range) |
| asof_rule | T-day open (known at 9:25) |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | gap_pct (normalized by prev_close, not by limit range) |
| family | stk_limit_derivative |
| priority | P0 |
| engineering_status | candidate |
| reason | gap_pct exists but 2% gap on a 10%-limit stock (20% of range) is very different from 2% on a 20%-limit stock (10% of range); limit_range normalization separates these |

---

## P1 Candidates (19)

### C013: smart_money_divergence

| Field | Value |
|-------|-------|
| name | Smart Money Divergence |
| source_type | github_paper |
| source_ref | Smart money literature; institutional vs retail flow decomposition |
| computable_definition | `rank(elg_buy_sell_ratio) - rank(sm_buy_sell_ratio)` (cross-sectional) |
| data_need | tushare moneyflow full breakdown (need small-order ratio, not currently extracted) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_elg_buy_sell_ratio; needs new sm_buy_sell_ratio column |
| family | moneyflow_derivative |
| priority | P1 |
| engineering_status | needs_data_check |
| reason | Strong concept but needs sm (small order) ratio extracted from moneyflow raw data; requires minor code addition |

### C014: mf_volume_decoupling

| Field | Value |
|-------|-------|
| name | Money Flow vs Volume Decoupling |
| source_type | github_paper |
| source_ref | Volume-flow divergence; stealth accumulation detection |
| computable_definition | `rank(net_mf_amount / amount) - rank(volume_ratio)` (cross-sectional) |
| data_need | tushare moneyflow + daily OHLCV |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_net_mf_amount, tushare_volume_ratio; divergence not captured |
| family | moneyflow_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Needs cross-sectional rank computation; logic is strong (stealth accumulation = high flow, low volume) |

### C015: mf_concentration

| Field | Value |
|-------|-------|
| name | Money Flow Concentration Ratio |
| source_type | github_paper |
| source_ref | Herfindahl-style order flow concentration; JoinQuant factor library |
| computable_definition | `(elg_net + lg_net) / (abs(net_mf_amount) + eps)` -- fraction of net flow from large+extra-large |
| data_need | tushare moneyflow (needs elg/lg net breakdowns, not currently separate columns) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_lg_buy_sell_ratio, tushare_elg_buy_sell_ratio (ratio, not absolute breakdown) |
| family | moneyflow_derivative |
| priority | P1 |
| engineering_status | needs_data_check |
| reason | Needs elg/lg net amounts as separate columns; currently only ratios and total net are extracted |

### C016: elg_momentum_divergence

| Field | Value |
|-------|-------|
| name | ELG Flow vs Price Momentum Divergence |
| source_type | github_paper |
| source_ref | Institutional herding research; flow-price divergence |
| computable_definition | `rank(mean(elg_buy_sell_ratio, 5)) - rank(ret_5d)` |
| data_need | tushare moneyflow + daily OHLCV |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_elg_buy_sell_ratio (single-day); this adds multi-day + price context |
| family | moneyflow_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Captures stealth accumulation (ELG buying but price hasn't moved); needs 5-day window + cross-sectional rank |

### C017: volume_confirmation_score

| Field | Value |
|-------|-------|
| name | Volume Confirmation Score |
| source_type | taoguba |
| source_ref | "Volume Confirmation" -- directional move validated by proportional volume |
| computable_definition | `((close - open) / (high - low + eps)) * volume_ratio` |
| data_need | daily OHLCV + tushare daily_basic (volume_ratio) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | ret1_x_volume_z5 (uses ret1 and volume z-score, not body direction and volume_ratio) |
| family | volume_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Close to existing interactions but uses body direction (not return) and volume_ratio (not z-score); slightly different signal |

### C018: volume_divergence_doji

| Field | Value |
|-------|-------|
| name | Volume Divergence Doji Indicator |
| source_type | taoguba |
| source_ref | "Volume Divergence" -- heavy trading with no directional consensus |
| computable_definition | `volume_ratio * (1 - abs(close - open) / (high - low + eps))` |
| data_need | daily OHLCV + tushare daily_basic (volume_ratio) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | body_pct captures body size; this is body_proportion * volume_ratio interaction |
| family | volume_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | High-volume indecision (doji on big volume) is a distinct pattern; partially captured by existing features but interaction is novel |

### C019: volume_asymmetry_10d

| Field | Value |
|-------|-------|
| name | Volume Asymmetry (Up vs Down Bar Volume) |
| source_type | github_paper |
| source_ref | Granville OBV extended; Alpha101 variants |
| computable_definition | `(sum(vol * (close>open), 10) - sum(vol * (close<=open), 10)) / (sum(vol, 10) + eps)` |
| data_need | daily OHLCV, 10-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | obv_trend_5 (different formula, 5d); this is 10d directional volume ratio |
| family | volume_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Directional decomposition of volume over 10 days; different from OBV trend which is cumulative price-weighted |

### C020: vp_correlation_10d

| Field | Value |
|-------|-------|
| name | Volume-Price Correlation 10-Day |
| source_type | github_paper |
| source_ref | Lo & Wang (2000); Alpha101 #44 |
| computable_definition | `pearson_corr(close, volume, window=10)` |
| data_need | daily OHLCV, 10-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | volume_price_divergence_5 (5-day, different calculation method) |
| family | volume_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Different window (10d) and method (Pearson correlation) vs existing 5d divergence metric |

### C021: cumulative_turnover_5d

| Field | Value |
|-------|-------|
| name | Cumulative Turnover to Float 5-Day |
| source_type | social_media |
| source_ref | "Free-Float Turnover Exhaustion" -- total chip turnover in recent days |
| computable_definition | `sum(volume[T-4:T]) / free_share` |
| data_need | daily volume + tushare daily_basic (free_share) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | turnover_sum_5 (uses turnover_rate, not volume/free_share ratio) |
| family | capacity_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | turnover_sum_5 exists but uses rate not absolute; this computes fraction of float that changed hands |

### C022: float_cap_tier

| Field | Value |
|-------|-------|
| name | Float Market Cap Tier |
| source_type | taoguba |
| source_ref | "Small/Mid/Large Cap Capacity" -- capacity stratification |
| computable_definition | `log10(free_share * close)` |
| data_need | tushare daily_basic (free_share) + close |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_free_share (share count, not market cap log) |
| family | capacity_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Simple transform but captures capacity tier effect; low engineering cost |

### C023: amihud_illiquidity_20d

| Field | Value |
|-------|-------|
| name | Amihud Illiquidity 20-Day |
| source_type | github_paper |
| source_ref | Amihud (2002) "Illiquidity and Stock Returns", Journal of Financial Markets |
| computable_definition | `mean(abs(ret_1) / (volume * close), window=20)` |
| data_need | daily OHLCV, 20-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_free_share (static proxy); Amihud is dynamic daily liquidity measure |
| family | capacity_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Canonical liquidity factor from finance literature; price impact per dollar volume. Complements static free_share |

### C024: limit_distance_compression_5d

| Field | Value |
|-------|-------|
| name | Limit Distance Compression 5-Day |
| source_type | github_paper |
| source_ref | Limit squeeze indicator; A-share specific |
| computable_definition | `up_limit_distance[T] / (up_limit_distance[T-5] + eps)` (ratio < 1 = squeezing) |
| data_need | tushare stk_limit, 5-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_up_limit_distance (level); C006 limit_approach_velocity (1-day delta); this is 5-day ratio |
| family | stk_limit_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Multi-day squeeze toward limit; captures sustained momentum not visible in 1-day delta |

### C025: upper_shadow_limit_ratio

| Field | Value |
|-------|-------|
| name | Upper Shadow Limit Ratio |
| source_type | github_paper |
| source_ref | Candlestick patterns in limit-price context; failed limit attempt |
| computable_definition | `(high - close) / (up_limit_price - close + eps)` where up_limit_price = close * (1 + limit_range/2) |
| data_need | daily OHLCV + tushare stk_limit |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | upper_shadow_pct (normalized by price); failed_limit_up (binary); this is continuous ratio |
| family | stk_limit_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Continuous measure of "how far did the high penetrate toward limit relative to remaining distance"; more granular than binary failed_limit_up |

### C026: updown_asymmetry

| Field | Value |
|-------|-------|
| name | Upside/Downside Space Asymmetry |
| source_type | taoguba |
| source_ref | "Upside/Downside Asymmetry" |
| computable_definition | `up_limit_distance / (down_limit_distance + eps)` |
| data_need | tushare stk_limit |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_up_limit_distance, tushare_down_limit_distance (individual) |
| family | stk_limit_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Ratio captures position within the limit band; partially correlated with daily return but adds constraint-awareness |

### C027: capital_efficiency

| Field | Value |
|-------|-------|
| name | Capital Efficiency |
| source_type | taoguba |
| source_ref | "Capital Efficiency" -- price movement per unit of net inflow |
| computable_definition | `(close - open) / (abs(net_mf_amount) + eps)` |
| data_need | daily OHLCV + tushare moneyflow |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_net_mf_amount (flow without price-movement context) |
| family | moneyflow_derivative |
| priority | P1 |
| engineering_status | candidate |
| reason | Inverse perspective: how much price moves per unit of flow. Low resistance stocks react more to the same flow |

### C028: flow_density_in_limit_space

| Field | Value |
|-------|-------|
| name | Flow Density in Remaining Limit Space |
| source_type | taoguba |
| source_ref | "Flow Density in Limit Space" |
| computable_definition | `net_mf_amount / (up_limit_distance * close + eps)` |
| data_need | tushare moneyflow + stk_limit + close |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | tushare_net_mf_amount, tushare_up_limit_distance (not combined) |
| family | interaction |
| priority | P1 |
| engineering_status | candidate |
| reason | Heavy buying compressed into narrow remaining band implies imminent limit-up; product of two validated features in a meaningful way |

### C029: weak_to_strong_signal

| Field | Value |
|-------|-------|
| name | Weak-to-Strong Reversal Signal |
| source_type | taoguba |
| source_ref | "Weak-to-Strong" -- low open but strong close with volume |
| computable_definition | `((close - open) / (limit_range * prev_close + eps)) * volume_ratio` |
| data_need | daily OHLCV + tushare daily_basic + stk_limit |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | intraday_return (raw); this normalizes by limit range and weights by volume |
| family | interaction |
| priority | P1 |
| engineering_status | candidate |
| reason | Classic short-term reversal pattern; existing intraday_return doesn't normalize by regime or weight by volume |

### C030: auction_open_vol_normalized (Tier1b)

| Field | Value |
|-------|-------|
| name | Normalized Auction Open Volume |
| source_type | taoguba |
| source_ref | "Auction Volume" -- auction volume relative to daily average |
| computable_definition | `tushare_auction_open_vol / mean(volume, 5)` |
| data_need | tushare stk_auction_o + daily volume |
| asof_rule | T-day 9:25 |
| leakage_risk | none |
| coverage_estimate | ~95%+ (stk_auction_o has 804 days cached) |
| related_existing_features | tushare_auction_open_vol (raw, not normalized) |
| family | stk_auction_tier1b |
| priority | P1 |
| engineering_status | candidate |
| reason | Raw auction volume is meaningless without scale; normalizing by recent daily volume gives auction participation intensity |

### C031: auction_vol_imbalance (Tier1b)

| Field | Value |
|-------|-------|
| name | Auction Volume Imbalance (Open vs Close) |
| source_type | taoguba |
| source_ref | "Auction Bidding/Withdrawal" -- open auction volume vs close auction volume |
| computable_definition | `log(auction_open_vol / (auction_close_vol + eps))` |
| data_need | tushare stk_auction_o + stk_auction_c |
| asof_rule | T-day close (close auction at T, open auction at T) |
| leakage_risk | none -- both auctions are within T-day |
| coverage_estimate | ~95%+ |
| related_existing_features | tushare_auction_open_vol, tushare_auction_close_vol (not compared) |
| family | stk_auction_tier1b |
| priority | P1 |
| engineering_status | candidate |
| reason | Open auction volume >> close auction volume implies morning urgency; ratio captures asymmetry |

---

## P2 Candidates (7)

### C032: volume_surge_with_support

| Field | Value |
|-------|-------|
| name | Volume Surge with Support Composite |
| source_type | social_media |
| source_ref | "Volume Surge with Support" |
| computable_definition | `volume_ratio * close_position * (1 if net_mf_amount > 0 else 0)` |
| data_need | daily OHLCV + tushare moneyflow + daily_basic |
| priority | P2 |
| engineering_status | candidate |
| reason | 3-way interaction; close_position and volume_ratio interactions already exist in various forms; may not add incremental signal |

### C033: mf_vs_price_imbalance

| Field | Value |
|-------|-------|
| name | Money Flow vs Price Imbalance |
| source_type | social_media |
| source_ref | "Main force net inflow but price did not rise" -- hidden accumulation |
| computable_definition | `net_mf_amount / amount - (close - prev_close) / prev_close * 10` (scaled divergence) |
| data_need | tushare moneyflow + daily OHLCV |
| priority | P2 |
| engineering_status | candidate |
| reason | Scaling factor (10) is arbitrary; concept is strong but formula needs tuning |

### C034: amplitude_x_mf_direction

| Field | Value |
|-------|-------|
| name | Amplitude x Moneyflow Direction |
| source_type | social_media |
| source_ref | "Amplitude vs Moneyflow Direction" |
| computable_definition | `range_pct * sign(net_mf_amount)` |
| data_need | daily OHLCV + tushare moneyflow |
| priority | P2 |
| engineering_status | candidate |
| reason | Very close to existing range_x_volume_z5 style interactions; may not add unique signal |

### C035: relative_volume_strength

| Field | Value |
|-------|-------|
| name | Signed Relative Volume |
| source_type | github_paper |
| source_ref | Qlib Alpha158 VSTD variants |
| computable_definition | `volume / mean(volume, 20) * sign(close - open)` |
| data_need | daily OHLCV |
| priority | P2 |
| engineering_status | candidate |
| reason | Close to existing volume_z_20 * sign(ret_1); likely redundant |

### C036: small_cap_flow_saturation

| Field | Value |
|-------|-------|
| name | Small-Cap Main Force Saturation |
| source_type | taoguba |
| source_ref | "Small-Cap Flow Saturation" |
| computable_definition | `lg_buy_sell_ratio * elg_buy_sell_ratio / log(free_share + eps)` |
| data_need | tushare moneyflow + daily_basic |
| priority | P2 |
| engineering_status | candidate |
| reason | 3-way multiplicative interaction; formula may be unstable with extreme values |

### C037: consecutive_limit_momentum

| Field | Value |
|-------|-------|
| name | Consecutive Limit-Up Volume Profile |
| source_type | social_media |
| source_ref | "Consecutive Limit-Up Volume Pattern" -- shrinking volume across limit-up streak |
| computable_definition | `limit_up_streak * (1 / (volume / volume_at_first_limit + 0.5))` |
| data_need | daily OHLCV + limit_up_streak (already exists as feature) |
| priority | P2 |
| engineering_status | candidate |
| reason | Very sparse -- only stocks with 2+ consecutive limit-up days; sample size may be too small in quiet markets |

### C038: close_position_x_volume_rank

| Field | Value |
|-------|-------|
| name | Close Position x Volume Rank |
| source_type | social_media |
| source_ref | "Close Position x Volume Rank Interaction" |
| computable_definition | `close_position * rank(volume / mean(volume, 20))` |
| data_need | daily OHLCV |
| priority | P2 |
| engineering_status | candidate |
| reason | Conceptually similar to existing ret1_x_volume_z5 and ret1_x_close_position |

---

## Blocked Candidates (4)

### C039: seal_order_volume

| Field | Value |
|-------|-------|
| name | Limit-Up Seal Order Volume |
| source_type | social_media |
| source_ref | "Seal Order Volume" -- order book seal volume |
| computable_definition | `seal_order_amount / (free_share * close)` |
| priority | blocked |
| engineering_status | blocked |
| reason | Requires Level-2 order book data; cannot reconstruct from daily OHLCV |

### C040: intraday_break_count

| Field | Value |
|-------|-------|
| name | Intraday Limit-Up Break Count |
| source_type | social_media |
| source_ref | "Limit-Break" -- number of times limit-up was broken/resealed intraday |
| computable_definition | `count(price crosses limit_up_price intraday)` |
| priority | blocked |
| engineering_status | blocked |
| reason | Requires tick or minute-bar data at limit price; daily OHLCV only tells "touched limit" or not |

### C041: auction_micro_bidding

| Field | Value |
|-------|-------|
| name | Auction Micro-Bidding Dynamics |
| source_type | social_media |
| source_ref | "Auction Bidding/Withdrawal" -- bid/cancel dynamics in call auction |
| computable_definition | `(bid_increase_rate - cancel_rate) in last 3 min of auction` |
| priority | blocked |
| engineering_status | blocked |
| reason | Requires pre-market Level-2 order flow snapshots; not available from any cached Tushare API |

### C042: hot_money_seat_concentration

| Field | Value |
|-------|-------|
| name | Dragon-Tiger Seat Concentration |
| source_type | social_media |
| source_ref | "Hot Money Concentration" -- single seat dominance on top-list |
| computable_definition | `max(buy_amount[seat_1..5]) / amount` |
| priority | blocked |
| engineering_status | blocked |
| reason | Dragon-tiger (top_list) data only triggers for ~50-100 stocks/day (~1-2% coverage); published T+1; tushare_lhb_* factors already exist but coverage too sparse for universal feature |

---

## Engineering Priority: Top 8 Recommended for Implementation

These 8 candidates are recommended for immediate engineering (code + data pipeline, no training):

| Rank | ID | Name | Family | Data Source | Why Top |
|------|-----|------|--------|-------------|---------|
| 1 | C004 | ff_adjusted_flow | moneyflow | moneyflow + daily_basic | Combines 2 strongest validated features; highest expected marginal signal |
| 2 | C001 | mf_flow_intensity | moneyflow | moneyflow + daily | Simplest normalization of the strongest single feature |
| 3 | C005 | limit_space_compression | stk_limit | stk_limit | Regime-aware normalization of validated limit distance |
| 4 | C006 | limit_approach_velocity | stk_limit | stk_limit | First derivative of validated feature; captures momentum |
| 5 | C009 | main_force_divergence | moneyflow | moneyflow | New dimension (institutional disagreement) from 2 validated features |
| 6 | C008 | seal_strength_proxy | interaction | moneyflow + stk_limit | 3-feature interaction with clear trading narrative |
| 7 | C011 | auction_open_vwap_ratio | stk_auction | stk_auction_o | Already coded, just not promoted; Tier1b gating candidate |
| 8 | C010 | float_relative_impact | capacity | daily_basic + daily | Captures turnover stress vs float; none of the 3 inputs alone does this |

**Implementation note:** C011 (auction_open_vwap_ratio) is already computed -- it only needs promotion to the feature pool. The other 7 need new column computation in free_data_factors.py or a new derivative builder. None require new data download or API calls.

---

## Data Availability Summary

| Data Source | Status | Candidates Using It |
|-------------|--------|---------------------|
| tushare moneyflow | 804 days cached, in Tier1 | C001-C004, C008-C009, C013-C016, C027-C028, C032-C034, C036 |
| tushare daily_basic | 804 days cached, in Tier1 | C004, C010, C021-C022, C030 |
| tushare stk_limit | 804 days cached, in Tier1 | C005-C007, C012, C024-C026, C029 |
| tushare stk_auction_o | 804 days cached, NOT in expanded | C011, C030, C031 |
| tushare stk_auction_c | 804 days cached, NOT in expanded | C031 |
| daily OHLCV | always available | All candidates |
| Level-2 order book | not available | C039-C041 (blocked) |
| Dragon-Tiger top_list | sparse ~1-2% | C042 (blocked) |
