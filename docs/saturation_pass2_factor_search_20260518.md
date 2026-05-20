# Saturation Pass 2 Factor Search 2026-05-18

Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.

## Search Surface

- Local raw pool: remaining no-match/ready candidates, especially limit-board, theme, minute-HF, LHB reason, Guba/Baidu, and convertible clauses.
- Social/TGB/Xueqiu/Bilibili/Douyin surfaces: weak-to-strong, auction expectation, follower confirmation, theme reflow, leader/board ceiling rules.
- Broker/research surfaces: high-frequency minute price-volume templates, text sentiment, convertible clauses and premium behavior.
- Data feasibility: no true L2/tick/orderbook factors were registered; these remain blocked until data exists.

## Result

- Added candidates: 25 (C426 to C450)
- Priority counts: {'P1': 18, 'P2': 7}
- Family counts: {'limit_premium': 1, 'limit_board': 3, 'subnew_board': 1, 'convertible_bond': 3, 'theme_intraday': 1, 'limit_theme': 1, 'minute_amount_shape': 2, 'minute_volume_shape': 1, 'minute_volume_peak': 1, 'minute_volatility_shape': 2, 'minute_reversal': 1, 'minute_price_bucket': 1, 'minute_volume_bucket': 1, 'lhb_reason': 2, 'social_attention': 1, 'search_attention': 1, 'retail_behavior': 2}

## Added Candidates

| ID | Name | Priority | Family | Frequency | Data Need | Asof / Caveat |
|---|---|---:|---|---|---|---|
| C426 | yesterday_limit_open_premium | P1 | limit_premium | daily_open | limit_pool yesterday basket and daily open/prev close | At 09:25/09:30 use open/auction final only for T; do not use T close. |
| C427 | board_height_ceiling_proximity | P1 | limit_board | daily_or_cutoff | limit_pool board_count history | Use only board counts known by cutoff; daily full session version is T+1. |
| C428 | subnew_limit_board_heat | P2 | subnew_board | daily | listing date, limit_pool, daily returns | Use listing age and limit events available by cutoff; full-day result is T+1. |
| C429 | seal_time_distribution_entropy | P1 | limit_board | daily_or_cutoff | limit_pool first seal time and market calendar | For same-day use include only boards sealed by cutoff; full-day entropy is T+1. |
| C430 | reversal_board_quality_score | P1 | limit_board | daily_or_1min | daily OHLCV, 1min bars, limit_pool seal/open-board fields | Use only 1min/limit events up to cutoff for live replay; after-close fields are T+1. |
| C431 | cb_stock_limit_up_premium_spread | P2 | convertible_bond | daily | cb_daily, cb_basic stock mapping, conversion premium, underlying limit_pool | Convertible daily data is normally after-close; use for T+1 unless intraday CB quote timestamps exist. |
| C432 | has_convertible_bond_leader_drag | P2 | convertible_bond | daily | active convertible-stock mapping and theme/leader score | Convertible mapping is known before trade; theme/leader score must be cutoff-bounded. |
| C433 | intraday_theme_reflow_score | P1 | theme_intraday | 1min | theme membership, 1min bars, leader identity or board_count | Use only minute bars <= cutoff and theme labels known by cutoff. |
| C434 | follower_position_confirmation | P1 | limit_theme | daily_or_1min | theme membership, leader/follower tag, intraday/daily returns, limit_pool | Use cutoff-bounded returns and limit events for same-day replay; full-day version is T+1. |
| C435 | tail20_amount_concentration | P1 | minute_amount_shape | 1min | 1min bars amount | Use only bars <= cutoff; at 14:57 use observed tail window within available bars, not post-cutoff bars. |
| C436 | minute_volume_path_roughness | P1 | minute_volume_shape | 1min | 1min bars volume | Use only bars <= cutoff. |
| C437 | volume_peak_count_factor | P1 | minute_volume_peak | 1min | 1min bars volume | Use only peaks observable by cutoff; do not use future bars to confirm a peak in live mode. |
| C438 | realized_volatility_peak_cluster_count | P1 | minute_volatility_shape | 1min | 1min close/returns | Use only returns up to cutoff. |
| C439 | local_reversal_by_volume_bucket | P1 | minute_reversal | 1min | 1min returns and volume bucket labels | Use only minute observations <= cutoff. |
| C440 | micro_partition_volatility_spread | P1 | minute_volatility_shape | 1min | 1min returns and volume partition labels | Use only bars <= cutoff; partitions must be defined using observed bars only. |
| C441 | high_low_price_bucket_momentum | P1 | minute_price_bucket | 1min | 1min close/returns | Use only observed intraday high/low percentiles up to cutoff. |
| C442 | high_low_volume_bucket_reversal | P1 | minute_volume_bucket | 1min | 1min close/returns and volume | Use only bars <= cutoff. |
| C443 | amount_distribution_asymmetry | P1 | minute_amount_shape | 1min | 1min amount | Use only bars <= cutoff and normalize by expected intraday curve. |
| C444 | dragon_list_reason_type_score | P1 | lhb_reason | after_close_daily | top_list/LHB reason text, parsed reason categories, stock-date event | LHB reason is after-close; use for next trading day only. |
| C445 | dragon_list_historical_reason_premium | P1 | lhb_reason | after_close_daily | top_list/LHB reason type, historical forward returns, market regime labels | Use only historical events strictly before the current event date; current LHB reason is T+1. |
| C446 | guba_attention_surge_score | P2 | social_attention | event_or_daily | timestamped Guba/Eastmoney post count by stock | For same-day use include only posts before cutoff; otherwise T+1. |
| C447 | baidu_search_attention_surge | P2 | search_attention | daily | Baidu search index by stock name/code and timestamp/date | If search index timestamp is daily after close, use T+1; same-day use requires timestamped intraday search data. |
| C448 | retail_fomo_moneyflow_limit_interaction | P1 | retail_behavior | daily_or_cutoff | moneyflow small-order fields, turnover, daily/limit_pool state | Use only moneyflow/limit fields available by cutoff; after-close moneyflow is T+1. |
| C449 | disposition_effect_pressure_proxy | P2 | retail_behavior | daily | daily returns, chip/cost proxy or turnover-cost model, small-order moneyflow sell pressure | Use T close/cost/moneyflow for next-day prediction unless intraday small-order flow is timestamped. |
| C450 | convertible_clause_game_score | P2 | convertible_bond | daily | cb_basic clause fields, conversion price history, stock close, issuer status | Use clause data known by date; do not use future issuer decisions or future conversion-price revisions. |

## Explicit Non-Adds

- L2/orderbook factors such as bid-ask depth imbalance, cancellation pressure, hidden order detection, and true OFI remain blocked.
- Pure trading slogans and discretionary exit/position rules were not registered.
- Direct aliases of existing features, generic moving-average formulas, and raw `current_price = close` patterns were rejected.
- Untimestamped short-video/social heat was not promoted to same-day trainable factors.

## Ten Checks

1. C001-C425 duplicate name screen
2. C001-C425 duplicate formula screen
3. local raw pool ready/no-match review
4. TGB/Xueqiu weak-to-strong and auction rule review
5. Bilibili/Douyin social-surface review with timestamp gate
6. broker high-frequency minute template review
7. Guba/Baidu/news attention source review
8. convertible-bond clause and premium source review
9. asof/leakage classification: cutoff vs T close vs T+1
10. post-write registry integrity validation

## Validation

- Total candidates after write: 450
- Missing IDs: []
- Duplicate IDs: []
- Unsafe status count: 0
