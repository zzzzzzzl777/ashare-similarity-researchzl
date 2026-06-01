# Four-Source Shortline Omnibus Candidate Addendum 2026-05-17

Scope: factor-library research only. No training, no `gpu_probe`, no model-code changes, no formal registry writes in this pass.

This is the continuation of `four_source_shortline_omnibus_candidate_scan_20260517.md`. The previous file covered O001-O110. This addendum adds O111-O210 from a deeper sweep of:

- local raw pool records not formally registered,
- sell-side high-frequency and limit-board reports,
- academic and GitHub-style high-frequency factor templates,
- Taoguba short-line terminology,
- social/forum/news attention literature.

These `Oxxx` IDs are only scan candidates. They must not be treated as formal `Cxxx` factor IDs until a later engineering review confirms formula, data, asof, duplicate status, and implementation path.

## Current Baseline Rechecked

- Formal registry: `E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json`
- Current registry count: C001-C292
- Raw pool index: `E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json`
- Raw pool records: 3,075
- Prior O queue: O001-O110
- This addendum queue: O111-O210

## Addendum Candidate Queue

### A. Local Raw-Pool Limit / Seal / Board Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O111 | real_open_board_count | P0 | local_raw_limit | limit_pool | count stocks that touched limit then reopened intraday | ready_engineering_review | open_board_rate |
| O112 | seal_time_canonical | P0 | local_raw_limit | limit_pool | first valid seal timestamp normalized by session | ready_engineering_review | seal_time existing name |
| O113 | seal_rate_80_threshold | P0 | local_raw_limit | limit_pool | pct of touched-limit stocks still sealed at 80pct session checkpoint | needs_formula_lock | threshold choice |
| O114 | seal_money_to_float_mv | P0 | local_raw_limit | limit_pool + share_float | seal money / free float market cap | ready_engineering_review | C004/C009 moneyflow style |
| O115 | seal_money_to_amount | P0 | local_raw_limit | limit_pool + daily amount | seal money / daily amount | ready_engineering_review | seal_money_to_float_mv |
| O116 | seal_grade_confirmation | P0 | local_raw_limit | limit_pool | ordinal seal strength from seal time, breaks, seal money | needs_formula_lock | subjective grade |
| O117 | last_seal_delay | P0 | local_raw_limit | limit_pool | final seal time minus first touch time | ready_engineering_review | seal_time |
| O118 | board_count_canonical | P0 | local_raw_limit | limit_pool | consecutive limit-up count using adjusted limit rules | ready_engineering_review | existing board count |
| O119 | prev_limit_up_premium_recheck | P0 | local_raw_limit | limit_pool + returns | T return premium of yesterday limit-up basket | ready_engineering_review | C prior premium factors |
| O120 | market_limit_up_count_clean | P0 | local_raw_limit | limit_pool | market-wide non-ST limit-up count, excluding one-word if configured | ready_engineering_review | market_emotion columns |
| O121 | seal_before_1030 | P1 | local_raw_limit | limit_pool | indicator or ratio of stocks sealed before 10:30 | ready_engineering_review | seal_time bucket |
| O122 | opening_seal_speed | P1 | local_raw_limit | limit_pool + 1min | slope from first touch to stable seal in opening segment | ready_engineering_review | O112/O117 |
| O123 | open_board_quality | P1 | local_raw_limit | limit_pool + 1min | reopened board that quickly reseals and keeps VWAP strength | needs_formula_lock | open-board variants |
| O124 | open_board_day_turnover | P1 | local_raw_limit | limit_pool + daily_ohlcv | turnover on open-board day relative to trailing turnover | ready_engineering_review | turnover spike |
| O125 | open_board_day_amplitude | P1 | local_raw_limit | limit_pool + daily_ohlcv | high-low amplitude on open-board day | ready_engineering_review | daily amplitude duplicate |
| O126 | one_word_board_real | P0 | local_raw_limit | auction + limit_pool | true one-word board from auction/open/zero intraday open signal | needs_data_pipeline | auction data |
| O127 | ipo_open_board_entry | P2 | local_raw_limit | limit_pool + listing age | first open-board after IPO/new-stock limit streak | needs_formula_lock | sub-new special |
| O128 | hesitant_seal_signal | P2 | local_raw_limit | limit_pool | repeated near-limit touches before final seal | ready_engineering_review | O117/O123 |
| O129 | seal_fail_repair_same_day | P1 | local_raw_limit | limit_pool + 1min | intraday break then close near/at limit with recovery | ready_engineering_review | open_board_quality |
| O130 | noon_seal_stability | P1 | local_raw_limit | limit_pool | board remains sealed across lunch break without weakness | ready_engineering_review | seal_time bucket |
| O131 | late_seal_suspicion | P2 | local_raw_limit | limit_pool + amount | late-day seal with high turnover and weak theme breadth | needs_formula_lock | afternoon risk |
| O132 | limit_touch_without_followthrough | P1 | local_raw_limit | limit_pool + returns | touch limit but close below threshold and next-day weakness | ready_engineering_review | broken-board |
| O133 | board_break_frequency_3d | P1 | local_raw_limit | limit_pool | number of board breaks across recent 3d for stock/theme | ready_engineering_review | broken-board count |
| O134 | seal_money_decay_3d | P1 | local_raw_limit | limit_pool | 3d decay of seal money for same board/theme cohort | ready_engineering_review | O114 |
| O135 | limit_pool_internal_dispersion | P1 | local_raw_limit | limit_pool + returns | dispersion of limit-stock intraday returns or seal strength | ready_engineering_review | market emotion |

### B. Theme / Leader / Echelon Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O136 | is_sector_leader_canonical | P0 | local_raw_theme | sector_theme + returns | rank stock as theme leader by return, board height, amount | needs_formula_lock | subjective leader |
| O137 | cycle_day_count | P0 | local_raw_theme | sector_theme + limit_pool | days since theme/emotion cycle started | needs_formula_lock | cycle definition |
| O138 | sector_limit_up_count_clean | P1 | local_raw_theme | sector_theme + limit_pool | count of limit-up stocks inside PIT sector/theme | needs_data_pipeline | theme PIT |
| O139 | sector_divergence_signal | P1 | local_raw_theme | sector_theme + returns | leader up while followers weaken, or breadth divergence | needs_data_pipeline | O029/O108 |
| O140 | sector_batch_limit_effect | P1 | local_raw_theme | sector_theme + limit_pool | same-theme batch limit-up density within short interval/day | needs_data_pipeline | O038 |
| O141 | bull_hotspot_bear_oversold | P1 | local_raw_theme | sector_theme + market state | interaction of theme heat and market oversold/bull state | needs_formula_lock | state thresholds |
| O142 | theme_leader_gap | P1 | local_raw_theme | sector_theme + limit_pool | board/return gap between leader and second tier | needs_data_pipeline | O029 |
| O143 | theme_echelon_slope | P1 | local_raw_theme | sector_theme + board height | slope of counts by board height inside theme | needs_data_pipeline | echelon |
| O144 | theme_capacity_score | P2 | local_raw_theme | sector_theme + float_mv | theme capacity estimated from float market cap and amount | needs_data_pipeline | O035 |
| O145 | spread_ratio_theme | P1 | local_raw_theme | sector_theme + returns | winner-follower return spread inside theme | needs_data_pipeline | theme return spread |
| O146 | sector_leader_return | P1 | local_raw_theme | sector_theme + returns | return of identified sector leader at cutoff | needs_data_pipeline | leader detection |
| O147 | reflow_leader_confirmation | P1 | local_raw_theme | sector_theme + 1min | capital reflows to leader after follower weakness | needs_data_pipeline | moneyflow proxy |
| O148 | leader_timing_not_size | P1 | local_raw_theme | sector_theme + limit time | leader quality from time priority, not market cap | needs_data_pipeline | leader formula |
| O149 | leader_switch_signal | P2 | local_raw_theme | sector_theme + returns | theme leadership rotation flag | needs_formula_lock | leader subjective |
| O150 | leader_succession_cycle | P2 | local_raw_theme | sector_theme + board chain | old leader fades while successor strengthens | needs_formula_lock | succession rule |
| O151 | leader_recognition_score | P1 | local_raw_theme | sector_theme + hot_rank | leader confirmed by return rank, volume, attention, board height | needs_data_pipeline | social/hot rank |
| O152 | leader_pullback_quality | P1 | local_raw_theme | sector_theme + 1min/daily | leader pullback holds above VWAP/support then resumes | needs_formula_lock | pullback formula |
| O153 | leader_premium_decay | P1 | local_raw_theme | sector_theme + returns | decay of leader excess premium vs theme basket | needs_data_pipeline | O145 |
| O154 | leader_follower_repair_spread | P1 | local_raw_theme | sector_theme + returns | followers repair while leader consolidates | needs_data_pipeline | O139 |
| O155 | theme_attention_spread | P2 | local_raw_theme_social | sector_theme + hot_rank | attention concentration leader vs followers | needs_data_pipeline | social pipeline |

### C. Minute / Auction / Intraday Raw-Pool Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O156 | open_5m_confirm_strength | P1 | local_raw_minute | 1min/5min bars | first 5min return, volume, VWAP confirmation composite | ready_engineering_review | O107 |
| O157 | closing_auction_volume_ratio | P0 | local_raw_auction | closing auction + daily amount | closing auction volume / daily volume or float | needs_data_pipeline | auction data |
| O158 | volume_during_open | P1 | local_raw_minute | 1min bars | first N minute volume share vs same-clock baseline | ready_engineering_review | O021/O042 |
| O159 | close_back_strength | P1 | local_raw_minute | 1min bars | late recovery from intraday drawdown into close/cutoff | ready_engineering_review | close leakage |
| O160 | second_break_quality | P1 | local_raw_minute | 1min bars | second breakout succeeds only if first pullback shallow | needs_formula_lock | breakout formula |
| O161 | first5_vwap_hold_ratio | P0 | minute_new | 1min bars | ratio of first 5min closes above VWAP/open | ready_engineering_review | O156 |
| O162 | first15_volume_acceleration | P0 | minute_new | 1min bars | first 15min cumulative volume vs same-clock 20d baseline | ready_engineering_review | O158 |
| O163 | midday_liquidity_dryup | P1 | minute_new | 1min bars | midday volume compression after morning impulse | ready_engineering_review | volume dry-up |
| O164 | post_lunch_reversal_impulse | P1 | minute_new | 1min bars | post-lunch return reversal after morning overextension | ready_engineering_review | O159 |
| O165 | last30_volume_ridge | P1 | broker_hf | 1min bars | continuous high-volume ridge in last 30min | ready_engineering_review | volume ridge |
| O166 | volume_peak_isolation | P1 | broker_hf | 1min bars | isolated abnormal volume peak not followed by ridge | ready_engineering_review | peak/ridge/valley |
| O167 | volume_valley_absorption | P1 | broker_hf | 1min bars | low-volume valley with price support after shock | ready_engineering_review | absorption |
| O168 | open_to_midday_trend_consistency | P1 | minute_new | 1min bars | sign consistency of open segment and pre-lunch segment | ready_engineering_review | O024 |
| O169 | tail_pullup_without_volume | P2 | minute_new | 1min bars | late price pull-up with weak volume confirmation | ready_engineering_review | manipulation risk |
| O170 | intraday_support_retest_count | P2 | minute_new | 1min bars | repeated retest of VWAP/open support without breakdown | ready_engineering_review | support formula |
| O171 | minute_gap_fill_speed | P1 | minute_new | 1min bars | speed and depth of opening gap fill | ready_engineering_review | gap factors |
| O172 | opening_range_false_break | P1 | minute_new | 1min bars | opening range break then fast return into range | ready_engineering_review | O107 inverse |
| O173 | close_position_same_clock_rank | P1 | minute_new | 1min bars | current price position vs same-clock trailing distribution | ready_engineering_review | close_position |
| O174 | intraday_drawdown_repair_ratio | P1 | minute_new | 1min bars | recovered drawdown / max intraday drawdown before cutoff | ready_engineering_review | C183-like |
| O175 | auction_to_first_minute_slippage | P1 | auction_minute | auction + 1min | open auction implied price vs first-minute VWAP slippage | needs_data_pipeline | auction data |

### D. Broker / Academic High-Frequency Additions

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O176 | shortest_path_illiquidity_intraday | P0 | broker_hf | 1min bars | sum((2*(high-low)-abs(close-open))/volume) | ready_engineering_review | DolphinDB/Everbright |
| O177 | consistent_buy_trading_ratio | P0 | broker_hf | 1min bars | upward volume share when abs(close-open)<=alpha*range | needs_formula_lock | alpha threshold |
| O178 | consistent_sell_trading_ratio | P1 | broker_hf | 1min bars | downward volume share under same consensus-trade condition | needs_formula_lock | O177 pair |
| O179 | morning30_volume_factor | P0 | broker_hf | 1min bars | volume share or volume zscore in first 30min | ready_engineering_review | O158 |
| O180 | afternoon30_volume_factor | P1 | broker_hf | 1min bars | volume share or volume zscore in last 30min before cutoff | ready_engineering_review | O165 |
| O181 | realized_skew_5min_or_1min | P1 | broker_hf | 1min/5min bars | realized skewness of intraday returns | ready_engineering_review | C174-C188 |
| O182 | downside_volatility_share_intraday | P1 | broker_hf | 1min bars | volatility from negative minute returns / total volatility | ready_engineering_review | downside vol |
| O183 | intraday_amount_return_corr | P1 | broker_hf | 1min bars | corr(minute amount, minute return) | ready_engineering_review | minute_pv_corr |
| O184 | early_late_pv_corr_shift | P1 | broker_hf | 1min bars | PV corr late segment minus early segment | ready_engineering_review | O002 |
| O185 | minute_return_std_stability | P1 | broker_hf | 1min bars | std of minute return volatility across days | ready_engineering_review | minute_volatility |
| O186 | volume_ridge_retail_participation | P1 | broker_hf | 1min bars | continuous high-volume ridge share, proxy for retail herding | ready_engineering_review | O165 |
| O187 | price_impact_square_root_proxy | P2 | academic_hf | 1min bars + amount | abs(ret) / sqrt(amount or volume) | ready_engineering_review | impact family |
| O188 | hawkes_like_event_clustering | P2 | academic_hf | 1min bars | self-excitation proxy: recent event count weighted by decay | needs_formula_lock | Hawkes approximation |
| O189 | high_frequency_liquidity_commonality | P2 | academic_hf | 1min all-stock bars | stock liquidity co-movement with market liquidity | ready_engineering_review | market commonality |
| O190 | intraday_transfer_entropy_proxy | P2 | academic_sector | 1min sector/stock returns | lagged sector leader return information-flow proxy | needs_formula_lock | transfer entropy heavy |

### E. Flow / LHB / Large-Trade / Northbound Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O191 | northbound_sector_flow | P1 | local_raw_flow | moneyflow_hsgt + sector | northbound net flow into sector / sector float | needs_data_pipeline | sector PIT |
| O192 | northbound_net_buy_stock | P1 | local_raw_flow | hsgt_top10/moneyflow_hsgt | stock-level northbound net buy scaled by float/amount | needs_data_pipeline | O057 |
| O193 | main_force_net_inflow_ratio | P0 | local_raw_flow | moneyflow fields | main force net inflow / amount | needs_data_pipeline | API field semantics |
| O194 | block_trade_discount_rank | P1 | broker_flow | block_trade | block-trade discount percentile by stock/date | needs_data_pipeline | O056 |
| O195 | block_trade_amount_ratio | P1 | broker_flow | block_trade + daily amount | block trade amount / recent daily amount | needs_data_pipeline | source report |
| O196 | block_trade_price_position | P1 | broker_flow | block_trade + daily price | block trade price location in recent range | needs_data_pipeline | report metric |
| O197 | lhb_net_buy_to_amount | P1 | local_raw_lhb | top_list/top_inst + amount | LHB net buy / daily amount | needs_data_pipeline | O053 |
| O198 | famous_seat_premium_score | P2 | local_raw_lhb | top_inst + seat taxonomy | historical next-day premium of buying seats | needs_data_pipeline | seat dictionary |
| O199 | seat_repeat_decay | P2 | local_raw_lhb | top_inst | decay-weighted repeat appearance of same seat in stock/theme | needs_data_pipeline | O050 |
| O200 | multi_seat_score | P2 | local_raw_lhb | top_inst | consensus among multiple strong seats | needs_data_pipeline | seat taxonomy |

### F. Social / Attention / Announcement Candidates

| oid | candidate_name | pri | source_lane | data_need | formula_sketch | status | duplicate_watch |
|---|---:|---|---|---|---|---|---|
| O201 | guba_reading_abnormal_attention | P1 | social | Guba read/post data | abnormal Guba reading or post count vs baseline | needs_data_pipeline | O060/O068 |
| O202 | sentiment_liquidity_boost | P2 | social | Guba/news sentiment + 1min liquidity | sentiment shock multiplied by liquidity improvement | blocked_level2_or_scrape | NLP pipeline |
| O203 | attention_price_divergence_local | P2 | social | hot_rank/Guba + returns | attention up while price weak, reversal/continuation flag | needs_data_pipeline | O070 |
| O204 | popularity_intraday_slope | P2 | social_minute | hot_rank timestamps + 1min | slope of popularity rank during session | needs_data_pipeline | hot-rank intraday |
| O205 | theme_attention_bind | P2 | social_theme | hot_rank + sector_theme | stock attention bound to theme attention rather than isolated | needs_data_pipeline | theme PIT |
| O206 | news_sentiment_score | P2 | news | news NLP | timestamped news sentiment score before cutoff | blocked_level2_or_scrape | NLP/news pipeline |
| O207 | announcement_risk_filter | P2 | event | announcements | risk announcement count/type before signal date | needs_data_pipeline | announcement parser |
| O208 | regulatory_cooling_score | P2 | event_social | announcements + theme | regulatory pressure around theme or stock | needs_data_pipeline | policy text |
| O209 | research_surge | P2 | event | stk_surv/research | institutional research/survey surge over trailing window | needs_data_pipeline | stk_surv |
| O210 | post_abnormal_announcement_days | P2 | event | announcements + returns | days after abnormal announcement, with decay weighting | needs_data_pipeline | event label |

## Status Counts

| status | count | meaning |
|---|---:|---|
| ready_engineering_review | 47 | Formula/data path is relatively concrete; suitable for engineering review first |
| needs_formula_lock | 16 | Useful concept but requires one deterministic formula or threshold |
| needs_data_pipeline | 35 | Requires confirmed API/cache/scrape path before possible registry write |
| blocked_level2_or_scrape | 2 | Keep outside registry until NLP/social/L2 pipeline is proven |
| total | 100 | All O111-O210 candidates in this addendum |

## Highest-Value Next Engineering Review Queue

If CC is asked to prepare the next candidate-to-registry pass, prioritize these:

1. Limit and seal features from local raw pool: O111-O122, O129-O135.
2. Minute bar features enabled by 1min data: O156, O158-O174, O176-O187, O189.
3. Theme features only after PIT sector/theme mapping is confirmed: O138-O148, O151-O155.
4. Flow/LHB features after Tushare proxy field verification: O191-O200.
5. Social and announcement features only after timestamped scrape/parser exists: O201-O210.

## Data Tasks Implied By This Addendum

- 1min `stk_mins`: needed for O156-O174 and most broker/HF additions.
- `limit_pool` / `limit_list_d` / `stk_limit`: needed for O111-O135 and many theme/leader candidates.
- `share_float`: needed for seal money / float, amount impact, and capacity factors.
- PIT sector/theme mapping: needed for O138-O155, O191, O205.
- Auction data: needed for O126, O157, O175.
- `top_list` / `top_inst`: needed for O197-O200.
- `block_trade`: needed for O194-O196.
- `moneyflow_hsgt`, `hsgt_top10`, `moneyflow_ind_dc` / `moneyflow_ind_ths`: needed for O191-O193.
- Timestamped Guba/hot-rank/news/announcement data: needed for O201-O210.

## Current Interpretation

The raw pool is not "mostly useless"; it is mostly not yet safe to bulk-register. The useful subset splits into:

- already concrete, formula-ready candidates,
- candidates requiring one exact formula,
- candidates blocked only by data pipelines,
- candidates that should stay conceptual until NLP/L2/social pipelines are reliable.

This addendum intentionally does not claim any candidate is strong. Strength belongs to later model training/probe. This document only expands and organizes the factor-library search space.

## Reference URLs

- DolphinDB high-frequency-to-low-frequency factor tutorial: https://docs.dolphindb.com/en/Tutorials/hf_to_lf_factor.html
- DolphinDB high-frequency factors tutorial: https://docs.dolphindb.com/en/3.00.5/Tutorials/high_frequency_factors.html
- DolphinDB factor computation best practices: https://docs.dolphindb.com/en/Tutorials/factor_computation.html
- CSC high-frequency factor library report page: https://www.sdyanbao.com/detail/374422
- BigQuant summary of CSC 213 high-frequency factors: https://bigquant.com/square/paper/f5c833dc-dc24-461e-85dd-51b28cc13425
- Guosheng 2025 strategy summary with minute turnover and PV correlation factors: https://finance.sina.com.cn/stock/stockzmt/2024-12-18/doc-inczwpwu0980479.shtml
- Everbright consistent trading factor summary: https://bigquant.com/wiki/doc/Ro88myai0N
- Everbright shortest-path illiquidity factor summary: https://bigquant.com/wiki/doc/QkcqI2DpGX
- Kaiyuan high-frequency volume peak/ridge/valley report page: https://www.fhyanbao.com/rpview/1679996
- Huatai /涨停板背后 Alpha report page: https://www.fxbaogao.com/detail/5312814
- A-share price limit hit dynamics paper: https://arxiv.org/abs/1503.03548
- Order flow dynamics around extreme price changes: https://arxiv.org/abs/1003.0168
- Guba topic attention paper: https://papers.ssrn.com/sol3/Delivery.cfm/6062915.pdf?abstractid=6062915&mirid=1
- Guba sentiment and intraday overtrading paper: https://arxiv.org/abs/2404.12001
- High-frequency liquidity in Chinese stock market: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4191675
