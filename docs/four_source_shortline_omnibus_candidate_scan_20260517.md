# Four-Source Shortline Omnibus Candidate Scan 2026-05-17

Scope: factor-library research only. No training, no `gpu_probe`, no model-code changes, no registry writes in this pass.

This file is a broad sweep of short-line A-share factor ideas after local raw-pool review and external source search. Candidates use temporary `Oxxx` IDs. They are not formal `Cxxx` registry IDs until a separate engineering review confirms formula, data availability, asof safety, and duplicate status.

## Local Baseline

- Formal registry file: `E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json`
- Current formal registry count: C001-C292, from `meta.registry_candidate_count = 292`
- Latest formal batch: `candidates_20260515_shortline_full_expansion`
- Raw pool index: `E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json`
- Raw pool records: 3,075
- Prior deep-search reports:
  - `C:\Users\zzzzzzl\Desktop\subagent\docs\four_source_shortline_factor_search_20260517.md`
  - `C:\Users\zzzzzzl\Desktop\subagent\docs\four_source_shortline_factor_deep_search_20260517.md`

## Decision Rules

- Priority is engineering/data readiness, not factor strength. Final strength must be decided by training/probe later.
- `ready_engineering_review` means the idea has a computable formula path and likely available data.
- `needs_formula_lock` means the idea is promising but requires one deterministic formula choice before registration.
- `needs_data_pipeline` means the formula is plausible but a scrape/API/cache pipeline must be confirmed first.
- `blocked_level2_or_scrape` means it requires data not currently proven stable, usually tick/orderbook/L2 or external social scraping.
- Do not promote `Oxxx` directly into model inputs. Use this file as a candidate queue for possible C293+ formal registry entries.

## Source Evidence Used

- Broker / sell-side reports: high-frequency factor libraries, high/low volume event factors, abnormal radar, limit-board behavior, LHB/seat behavior.
- Academic / GitHub / formula libraries: high-frequency-to-low-frequency factor construction, Qlib/Alpha158/Alpha360/WorldQuant formula templates, sentiment and attention papers.
- Taoguba / short-line domain language: board height, seal strength, broken-board contagion, emotion cycle, theme ladder, weak-to-strong auction language.
- Social media / live-trader sources: Guba topic attention, forum sentiment, short-video or live-room attention and consensus concepts.

Reference URLs are listed at the end.

## Omnibus Candidate Queue

### A. Minute / High-Frequency Price-Volume Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O001 | minute_turnover_stability_20d | P0 | broker_hf | 1min bars + share_float | inverse std of same-clock minute turnover over trailing 20d | ready_engineering_review | C174/C177 volume concentration |
| O002 | minute_pv_corr_segmented | P0 | broker_hf | 1min bars | corr(minute_ret, minute_volume_or_turnover) by open/mid/close segment | ready_engineering_review | prior segmented PV names |
| O003 | minute_price_autocorr_20d | P0 | broker_hf | 1min bars | autocorr(minute_ret, lag=1 or lag=5), trailing 20d, segment aware | ready_engineering_review | C174-C188 minute family |
| O004 | high_position_volume_event_ratio | P0 | broker_hf | 1min bars + trailing price window | active minutes with price in top 20pct and volume shock / active minutes | ready_engineering_review | none |
| O005 | low_position_volume_repair_ratio | P1 | broker_hf | 1min bars | low-price-zone volume expansion followed by intraday repair | needs_formula_lock | event window choice |
| O006 | high_vol_price_position_ratio | P0 | broker_hf | 1min bars | mean price during top-volatility minutes / full-session mean price | ready_engineering_review | C176/C183 overlap check |
| O007 | low_vol_price_position_ratio | P1 | broker_hf | 1min bars | mean price during low-volatility minutes / full-session mean price | ready_engineering_review | weaker pair of O006 |
| O008 | abnormal_radar_flow_corr | P1 | broker_hf | 1min bars + moneyflow proxy | corr(stock minute flow, benchmark/sector flow) with excess return sign | needs_formula_lock | flow proxy choice |
| O009 | abnormal_radar_event_cluster_score | P1 | broker_hf | 1min bars + benchmark + flow proxy | weighted cluster of price/volume/flow anomaly flags | needs_formula_lock | too many weights |
| O010 | intraday_noise_to_trend_ratio | P1 | academic_hf | 1min bars | sum(abs(minute_ret)) / abs(cumulative_ret) by segment | ready_engineering_review | generic choppiness |
| O011 | shock_volume_decay_half_life | P0 | academic_hf | 1min bars | fit post-shock volume_z decay half-life after large minute move | ready_engineering_review | none |
| O012 | shock_price_reversal_efficiency | P0 | academic_hf | 1min bars | post-shock opposite return / shock magnitude over N minutes | ready_engineering_review | C183 but event-conditioned |
| O013 | signed_volume_early_late_ratio | P0 | academic_hf | 1min bars | signed volume first K bars / signed volume latest K bars before cutoff | ready_engineering_review | sign definition |
| O014 | minute_vwap_drift_slope | P1 | academic_hf | 1min bars | slope(close/vwap - 1) in open and close segments | ready_engineering_review | C135/C176 |
| O015 | intraday_range_compression_break | P1 | academic_hf | 1min bars | narrow rolling range followed by range expansion | ready_engineering_review | breakout variants |
| O016 | minute_liquidity_impact_slope | P1 | broker_hf | 1min bars + amount | regression slope abs(ret) on turnover/amount shock | ready_engineering_review | impact family |
| O017 | same_clock_volume_surprise | P0 | broker_hf | 1min bars | current same-clock volume zscore vs trailing 20d same minute | ready_engineering_review | volume_z_20 if existing |
| O018 | same_clock_return_reversal | P1 | broker_hf | 1min bars | current same-clock ret shock followed by next-window reversal tendency | ready_engineering_review | O012 |
| O019 | intraday_volatility_state_switch | P1 | academic_hf | 1min bars | transition from low-vol to high-vol state by same-clock zscore | needs_formula_lock | state thresholds |
| O020 | tail_session_impact_resilience | P1 | broker_hf | 1min bars | late-session price impact recovery after volume shock | ready_engineering_review | close leakage cutoff |
| O021 | morning_volume_exhaustion | P1 | broker_hf | 1min bars | first 30min volume share high but later momentum weak | ready_engineering_review | O013 opposite |
| O022 | afternoon_reacceleration | P1 | broker_hf | 1min bars | afternoon turnover/ret acceleration after calm midday | ready_engineering_review | intraday momentum |
| O023 | close_to_vwap_reclaim_count | P1 | academic_hf | 1min bars | count of reclaim events from below VWAP before cutoff | ready_engineering_review | C135/C176 |
| O024 | intraday_trend_smoothness | P1 | academic_hf | 1min bars | abs(cum_ret) / sum(abs(minute_ret)) | ready_engineering_review | inverse O010 |
| O025 | minute_turnover_entropy | P1 | broker_hf | 1min bars + share_float | entropy of turnover distribution across intraday buckets | ready_engineering_review | C174 HHI |

### B. Limit-Board / Taoguba Structure Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O026 | board_height_compression_speed | P0 | taoguba | limit_list_d + board height | decline speed of market max board height over 3-5d | ready_engineering_review | existing board height |
| O027 | seal_rate_collapse_3d | P0 | taoguba | limit_list_d + intraday seal/break | 3d drop in seal success rate | ready_engineering_review | seal_rate variants |
| O028 | broken_board_loss_diffusion | P0 | taoguba | limit_list_d + returns | mean next-day loss of broken-board stocks and breadth spread | ready_engineering_review | broken-board family |
| O029 | theme_ladder_gap_penalty | P1 | taoguba | theme membership + limits | gap between theme leader board height and follower count | needs_data_pipeline | theme PIT needed |
| O030 | yesterday_limit_premium_peak_risk | P1 | taoguba | limit_list_d + returns | previous-limit basket premium near recent peak | ready_engineering_review | sentiment cycle |
| O031 | dragon_head_extreme_board_warning | P1 | taoguba | limit board chain | leader board height extreme plus follower weakening | needs_formula_lock | subjective leader |
| O032 | high_board_survival_rate_3d | P0 | taoguba | limit_list_d | survival of stocks board>=N over next 3 sessions | ready_engineering_review | board continuation |
| O033 | board_echelon_repair_signal | P1 | taoguba | limit_list_d + theme | low/mid/high board echelon all improving from trough | needs_formula_lock | market state thresholds |
| O034 | first_board_to_second_board_conversion | P0 | taoguba | limit_list_d | first-board stocks converting to second-board next day | ready_engineering_review | first-board rate |
| O035 | limit_pool_crowding_score | P1 | taoguba | limit_list_d + turnover | crowding of limit stocks by amount/turnover concentration | ready_engineering_review | crowding factors |
| O036 | rotten_board_afterglow_risk | P1 | taoguba | limit_list_d + intraday breaks | lagged broken-board rate impact on next 1-3d risk | ready_engineering_review | C062-like |
| O037 | seal_time_rank_change | P1 | taoguba | limit_list_d seal time | change in early seal rank within theme/market | ready_engineering_review | seal_time existing |
| O038 | theme_first_limit_lead_time | P1 | taoguba | theme + limit time | earliest limit time in theme minus market median | needs_data_pipeline | theme PIT |
| O039 | failed_board_recovery_breadth | P1 | taoguba | broken-board list + returns | breadth of failed-board stocks that recover above VWAP/close | ready_engineering_review | O028 |
| O040 | limit_down_cluster_relief | P2 | taoguba | limit down list | drop in limit-down cluster count after high-stress day | ready_engineering_review | market state |

### C. Auction / Opening Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O041 | auction_real_order_pressure_after_0920 | P0 | taoguba | stk_auction or auction proxy | post-09:20 effective order pressure vs float | needs_data_pipeline | auction data availability |
| O042 | auction_volume_vs_same_clock_baseline | P0 | taoguba | auction + 1min | auction volume zscore vs trailing same-stock baseline | needs_data_pipeline | O047 |
| O043 | auction_gap_quality_score | P1 | taoguba | auction/open + prev close | open gap confirmed by auction volume and not overextended | needs_formula_lock | gap factors |
| O044 | auction_open_to_first5_reclaim | P1 | taoguba | auction + 1min | reclaim from weak open within first 5min | ready_engineering_review | 1min first5 |
| O045 | auction_false_strength_risk | P1 | taoguba | auction + 1min | strong auction gap followed by first5 negative reversal | ready_engineering_review | O043 inverse |
| O046 | auction_theme_consensus | P1 | taoguba | auction + theme | breadth of same-theme positive auction confirmation | needs_data_pipeline | theme PIT |
| O047 | auction_amount_to_float_ratio | P0 | taoguba | auction amount + share_float | auction amount / free float market cap | needs_data_pipeline | O042 |
| O048 | preopen_jump_decay_risk | P2 | taoguba | auction snapshots if available | gap fade between preopen snapshots and final open | blocked_level2_or_scrape | needs auction snapshots |
| O049 | weak_to_strong_open_reclaim | P0 | taoguba | 1min + prev board status | low/open weakness then reclaim above open/VWAP with volume | ready_engineering_review | shortline classic |

### D. LHB / Seat / Fund-Flow Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O050 | seat_buy_style_persistence | P1 | broker_lhb | top_list/top_inst | recurring hot-seat buy after similar setup | needs_data_pipeline | seat mapping |
| O051 | institution_vs_hotmoney_lhb_balance | P1 | broker_lhb | top_list/top_inst | institutional net buy minus hot-money net buy scaled by float | needs_data_pipeline | LHB taxonomy |
| O052 | lhb_afterglow_half_life | P1 | broker_lhb | top_list + returns | decay half-life of post-LHB excess return | ready_engineering_review | LHB lag factors |
| O053 | lhb_net_buy_vs_float | P0 | broker_lhb | top_list + share_float | net buy amount / free float market cap | ready_engineering_review | C LHB candidates |
| O054 | famous_seat_rotation_score | P2 | broker_lhb | top_inst seat names | whether active seats rotate into same theme/leader | needs_data_pipeline | seat dictionary |
| O055 | block_trade_followthrough_after_limit | P1 | broker_flow | block_trade + limit_list | block trade premium/discount after limit day and follow-through return | needs_data_pipeline | block_trade availability |
| O056 | big_trade_discount_repair | P1 | broker_flow | block_trade + daily/1min | discount block trade followed by price repair | needs_data_pipeline | event lag |
| O057 | northbound_top10_followthrough | P1 | broker_flow | hsgt_top10 | northbound top10 net buy followed by next-day intraday strength | needs_data_pipeline | sparse coverage |
| O058 | industry_moneyflow_resonance | P1 | broker_flow | moneyflow_ind_dc/ths + stock moneyflow | stock inflow aligned with industry inflow | needs_data_pipeline | industry mapping |
| O059 | stock_industry_flow_disagreement | P1 | broker_flow | moneyflow_ind_dc/ths + stock moneyflow | stock inflow against weak industry flow, or vice versa | needs_data_pipeline | O058 pair |

### E. Social / Forum / Live-Video Attention Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O060 | guba_topic_attention_zscore | P1 | social | timestamped Guba posts | topic count to cutoff / same-clock baseline zscore | needs_data_pipeline | C287 |
| O061 | guba_attention_turnover_coupling | P1 | social | Guba + 1min turnover | z(attention growth) * z(turnover acceleration) | needs_data_pipeline | C286/C287 |
| O062 | guba_sentiment_volatility_asymmetry | P2 | social | Guba NLP + 1min bars | signed sentiment shock * realized volatility split positive/negative | blocked_level2_or_scrape | NLP pipeline |
| O063 | guba_topic_lifecycle_stage | P2 | social | topic model | infancy/growth/climax/decay from rolling topic intensity | blocked_level2_or_scrape | topic pipeline |
| O064 | social_attention_smallcap_sensitivity | P2 | social | Guba + float/mcap | attention shock stronger for small/non-main-board firms | needs_data_pipeline | academic finding |
| O065 | live_trader_consensus_breadth | P2 | social_live | live transcripts | breadth of live-trader bullish/defensive consensus | blocked_level2_or_scrape | transcript source |
| O066 | short_video_theme_heat_decay | P2 | social_video | short-video scrape | theme mention heat half-life after spike | blocked_level2_or_scrape | platform pipeline |
| O067 | forum_negative_attention_reversal | P2 | social | Guba NLP + returns | negative attention spike followed by reversal or continuation | blocked_level2_or_scrape | NLP polarity |
| O068 | guba_post_count_spike_decay | P1 | social | timestamped Guba posts | post count spike decay rate over 1-3d | needs_data_pipeline | O060 |
| O069 | social_leader_disagreement | P2 | social | influencer/source mapping | disagreement between high-attention accounts on same stock/theme | blocked_level2_or_scrape | source identity |
| O070 | xueqiu_attention_price_divergence | P2 | social | Xueqiu scrape/API | attention rising while price momentum weakens | blocked_level2_or_scrape | source availability |
| O071 | news_forum_attention_dislocation | P2 | social_news | news + Guba | news attention vs forum attention gap | blocked_level2_or_scrape | news source |

### F. Academic / GitHub / Formula-Library Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O072 | wq_intraday_rank_decay_combo | P1 | github_formula | 1min + daily | WorldQuant-style rank/decay rewritten on intraday aggregates | needs_formula_lock | generic alpha duplicate |
| O073 | qlib_alpha158_intraday_rewrite | P1 | github_formula | 1min + daily | selected Alpha158 fields using intraday cutoff-safe OHLCV | needs_formula_lock | many daily duplicates |
| O074 | alpha360_shape_moment_intraday | P1 | github_formula | 1min bars | shape moments of recent intraday normalized close/volume sequence | ready_engineering_review | sequence features |
| O075 | rolling_rank_volume_price_residual | P1 | github_formula | daily + 1min | residual of price move after volume/turnover rank | ready_engineering_review | residual alpha |
| O076 | intraday_correlation_regime_switch | P1 | academic_hf | 1min bars | rolling corr pattern changes between price, volume, volatility | ready_engineering_review | O002/O019 |
| O077 | realized_skew_kurtosis_combo | P1 | academic_hf | 1min bars | realized skew/kurtosis combination of minute returns | ready_engineering_review | technical moments |
| O078 | jump_risk_after_liquidity_shock | P1 | academic_hf | 1min bars | jump flag after liquidity/turnover shock | ready_engineering_review | O011/O012 |
| O079 | event_conditioned_reversal_alpha | P1 | academic_hf | 1min + event flags | reversal only after limit/LHB/volume shock events | needs_formula_lock | broad family |
| O080 | volatility_of_liquidity_impact | P1 | academic_hf | 1min bars | rolling volatility of price impact slope | ready_engineering_review | O016 |

### G. Event / Fundamental / Cross-Market Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O081 | pead_intraday_confirmation | P1 | event | forecast_vip + 1min | forecast/earnings event confirmed by intraday demand | needs_data_pipeline | PEAD candidates |
| O082 | forecast_revision_attention_interaction | P2 | event_social | forecast_vip + attention | forecast revision surprise * attention shock | needs_data_pipeline | source timing |
| O083 | research_survey_heat_decay | P2 | event | stk_surv | institutional survey heat half-life and next-day strength | needs_data_pipeline | C survey ideas |
| O084 | unlock_pressure_intraday_amplifier | P1 | event | share_float/unlock + 1min | unlock pressure amplified by intraday weak liquidity | needs_data_pipeline | unlock data |
| O085 | pledge_risk_repair_after_limit | P2 | event | pledge_stat + limit | pledge-risk stock limit-up repair or risk discount | needs_data_pipeline | sparse |
| O086 | global_risk_open_gap_filter | P2 | cross_market | index_global + open gap | global overnight risk filters open-gap quality | needs_data_pipeline | market filter |
| O087 | shibor_liquidity_intraday_gate | P2 | cross_market | shibor + daily/1min | liquidity environment gates intraday continuation | needs_data_pipeline | macro slow |
| O088 | cb_risk_appetite_tailwind | P2 | cross_market | cb_daily | convertible-bond risk appetite for small-cap/shortline tailwind | needs_data_pipeline | proxy validity |
| O089 | hsgt_top10_sparse_attention_flag | P1 | event_flow | hsgt_top10 | sparse northbound appearance as attention/quality flag | needs_data_pipeline | sparse |
| O090 | industry_policy_density_decay | P2 | event_news | policy/news scrape + industry | policy density decay by industry theme | blocked_level2_or_scrape | news/policy scrape |

### H. Level2 / Tick / Orderbook Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O091 | mci_bid_liquidity_proxy | P2 | broker_l2 | orderbook depth | bid-side marginal cost of immediacy | blocked_level2_or_scrape | needs orderbook |
| O092 | mci_ask_liquidity_proxy | P2 | broker_l2 | orderbook depth | ask-side marginal cost of immediacy | blocked_level2_or_scrape | needs orderbook |
| O093 | orderbook_depth_imbalance_5level | P2 | broker_l2 | 5-level depth | bid depth - ask depth scaled by total depth | blocked_level2_or_scrape | L2 |
| O094 | order_cancellation_pressure | P2 | broker_l2 | order events | cancellation volume / submitted volume by side | blocked_level2_or_scrape | tick/order data |
| O095 | aggressive_buy_order_ratio | P2 | broker_l2 | tick trades/orders | aggressive buy amount / total active amount | blocked_level2_or_scrape | tick classification |
| O096 | small_order_herding_proxy | P2 | broker_l2 | tick/order size | synchronized small-order net buy ratio | blocked_level2_or_scrape | small-order data |
| O097 | bid_ask_spread_shock_decay | P2 | broker_l2 | spread/depth | spread shock half-life after liquidity event | blocked_level2_or_scrape | orderbook |
| O098 | orderbook_resilience_after_sweep | P2 | broker_l2 | orderbook/trades | depth recovery after aggressive sweep | blocked_level2_or_scrape | orderbook |

### I. Additional Short-Line Cross-Section Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O099 | minute_market_breadth_thrust | P0 | broker_hf | 1min all-stock bars | market-wide share of stocks with positive same-clock return surge | ready_engineering_review | market breadth |
| O100 | theme_minute_breadth_acceleration | P1 | taoguba | 1min + theme PIT | acceleration of positive-return breadth inside theme | needs_data_pipeline | theme PIT |
| O101 | cross_sectional_minute_momentum_rank | P0 | academic_hf | 1min all-stock bars | rank of cutoff-safe intraday momentum among universe | ready_engineering_review | cs_ret_1_rank |
| O102 | minute_downside_absorption | P1 | academic_hf | 1min bars | high volume on down minutes without price breakdown | ready_engineering_review | absorption concepts |
| O103 | consecutive_red_minute_count | P1 | taoguba | 1min bars | max consecutive positive minute returns by segment | ready_engineering_review | simple streak |
| O104 | consecutive_green_exhaustion | P1 | taoguba | 1min bars | long positive streak plus weakening volume/price slope | needs_formula_lock | O103 pair |
| O105 | first_pullback_hold_ratio | P1 | taoguba | 1min bars | first pullback low holds above VWAP/open after morning high | ready_engineering_review | weak-to-strong |
| O106 | late_breakout_fail_probability | P1 | taoguba | 1min bars | late breakout above range then fail back below range | ready_engineering_review | tail session |
| O107 | minute_opening_range_breakout_quality | P0 | taoguba | 1min bars | opening range breakout confirmed by volume and no quick failure | ready_engineering_review | ORB |
| O108 | same_theme_limit_follow_probability | P1 | taoguba | theme + limit_list | probability stock follows same-theme leader limit-up | needs_data_pipeline | theme PIT |
| O109 | market_rotten_board_infection | P1 | taoguba | limit_list_d + broken boards | broken-board rate infects next-day non-limit high-beta names | ready_engineering_review | O028/O036 |
| O110 | social_heat_vs_lhb_confirmation | P2 | social_lhb | social + top_list | social heat confirmed by LHB net buy or institution participation | needs_data_pipeline | multi-pipeline |

## Status Counts

| status | count | meaning |
|---|---:|---|
| ready_engineering_review | 51 | Good candidates for formula/asof/duplicate engineering review before possible registry promotion |
| needs_formula_lock | 11 | Promising but needs one deterministic formula, threshold, or event-window choice |
| needs_data_pipeline | 30 | Needs API/scrape/cache confirmation before promotion |
| blocked_level2_or_scrape | 18 | Keep as backlog until orderbook/tick/L2/social/news pipeline is available |
| total | 110 | All `Oxxx` candidates in this scan |

## Best Near-Term Engineering Queue

If the next task is to create C293+ candidates, start from these groups:

1. Minute/HF P0s with 1min bars already possible: O001-O004, O006, O011-O013, O017, O099, O101, O107.
2. Limit-board structure with existing daily/limit data: O026-O028, O032, O034-O037, O039, O109.
3. 1min short-line structure: O044, O045, O049, O102, O103, O105, O106.
4. Flow/LHB after API confirmation: O053, O052, O057-O059.
5. Social/forum after scrape confirmation: O060, O061, O068.

## Data Pull Implications

The broadest unlock is still `stk_mins` 1min bars from 2017 onward, because it supports minute price/volume, same-clock normalization, shock decay, trend smoothness, opening range, and cross-sectional minute breadth factors.

Additional useful datasets:

- `share_float` or equivalent free-float fields for turnover and impact normalization.
- `limit_list_d`, `stk_limit`, or equivalent for board, seal, broken-board, and limit-down structure.
- `top_list`, `top_inst`, and LHB tables for seat/fund-flow candidates.
- `moneyflow_hsgt`, `hsgt_top10`, `moneyflow_ind_dc`, `moneyflow_ind_ths` for northbound/industry flow candidates.
- Point-in-time theme/sector membership for theme ladder, theme breadth, and same-theme follow factors.
- Timestamped Guba/forum/social posts only if social candidates are promoted.
- Orderbook/tick/L2 only if O091-O098 are intentionally pursued.

## Avoid / Reject Patterns

- Do not register generic duplicates of existing daily OHLCV, daily momentum, daily turnover, or plain technical indicator fields unless the candidate adds a short-line intraday/event condition.
- Do not register pure language concepts without timestamp, stock mapping, and formula.
- Do not use full-day close/volume fields when the target is a 14:57 or intraday decision; lock cutoff/asof before registry.
- Do not promote L2/orderbook ideas unless the data pipeline is proven.

## Recommended Next Prompt For CC

Ask CC to perform an engineering review only, not training:

```text
You are only doing factor-library engineering review. Do not train, do not run gpu_probe, do not change model/training code.

Input report:
C:\Users\zzzzzzl\Desktop\subagent\docs\four_source_shortline_omnibus_candidate_scan_20260517.md

Task:
1. Read the O001-O110 candidate queue.
2. Compare against the formal registry at E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json and code features to identify duplicates.
3. Select only candidates that are computable, asof-safe, and not duplicates.
4. Produce a review report with promote/reject/defer decisions, exact formula, required columns, asof rule, duplicate check, and data pipeline requirement.
5. Do not write C293+ into the registry until the promote list has been reviewed.
```

## Reference URLs

- DolphinDB high-frequency to low-frequency factor tutorial: https://docs.dolphindb.com/en/Tutorials/hf_to_lf_factor.html
- DolphinDB high-frequency factors tutorial: https://docs.dolphindb.com/en/3.00.5/Tutorials/high_frequency_factors.html
- DolphinDB real-time factor calculation tutorial: https://docs.dolphindb.com/en/3.00.5/Tutorials/real_time_factor_calculation.html
- Guba sentiment and overtrading paper: https://arxiv.org/abs/2404.12001
- Investor topics / attention and Chinese stock market SSRN paper: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6062915
- Chinese stock board discussion / social attention related paper: https://arxiv.org/abs/2205.05719
- CSC high-frequency factor report page: https://www.sdyanbao.com/detail/374422
- Guosheng high/low volume event factor report PDF mirror: https://bigdata-s3.wmcloud.com/researchreport/2023-12/169254d9654de9c32112aaa089cceb44.pdf
- Guosheng abnormal radar report page: https://www.fxbaogao.com/detail/5296242
- Taoguba short-line context example: https://m.tgb.cn/a/2luP37oIbzF
