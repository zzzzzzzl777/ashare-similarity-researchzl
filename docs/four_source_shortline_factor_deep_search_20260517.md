# Four-Source Shortline Factor Deep Search 2026-05-17

Scope: factor-library research only. No training, no gpu_probe, no model-code changes, no registry writes in this pass.

## Current Baseline

- Formal registry: `E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json`
- Current formal candidates: C001-C292.
- This pass is a deeper source search and de-duplication review for possible C293+ candidates.
- Hard rule: shortline relevance + computable formula + deterministic asof path before formal registration.

## Source Findings

### A. Broker / Sell-Side Reports

Broker reports are the richest next source because they provide both formula families and empirical framing.

Evidence:

- CSC high-frequency factor library describes 213 minute/Level2 based daily factors across capital-flow intent, liquidity, volatility, and buy/sell strength.
- Guosheng 2024 mid-year quant report explicitly names `daily_turn_std`, `minute_turn_std`, `minute_volatility`, `daily_pv_corr`, `minute_pv_corr`, and `minute_price_autocorr`.
- Guosheng high/low-volume event report gives a clear recipe: define high/low price zones and high/low volatility zones using 1min bars over a trailing 20-day window.
- Guosheng abnormal-radar report shifts from simple price anomaly to event clusters: correlation with benchmark minute series, excess direction, multidimensional flow signals, filtering and synthesis.
- CSC bid/ask order liquidity report motivates MCI-style orderbook liquidity factors, but these remain blocked unless true orderbook/depth is available.

High-value candidate families:

| Candidate | Priority | Data need | Formula sketch | Duplicate / gate |
|---|---:|---|---|---|
| minute_turnover_stability_20d | P0 | 1min bars + float/share_float | std(minute_turnover over trailing 20d) or inverse stability, same-clock normalized | New; related to C174/C177 but turnover-specific |
| minute_pv_corr_segmented | P0 | 1min bars | corr(minute_return, minute_volume_or_turnover) by open/mid/close segment | Similar to earlier `intraday_price_volume_corr_segmented`, keep one canonical name |
| minute_price_autocorr_20d | P0 | 1min bars | autocorr(minute_return, lag=1 or lag=5) over trailing 20d, segment-aware | Check against C174-C188 duplicates |
| high_position_volume_event_ratio | P0 | 1min/daily bars | minutes with price in top 20% of trailing window and volume/turnover shock / all active minutes | Strong report-backed candidate |
| low_position_volume_repair_ratio | P1 | 1min/daily bars | low-price-zone volume expansion followed by intraday price repair | Report-backed, needs event-window lock |
| high_vol_price_position_ratio | P0 | 1min bars | mean(close during top-volatility minutes) / mean(close all minutes), trailing 20d | Report-backed |
| low_vol_price_position_ratio | P1 | 1min bars | mean(close during low-volatility minutes) / mean(close all minutes), trailing 20d | Report-backed but weaker in report |
| abnormal_radar_flow_corr | P1 | 1min bars + moneyflow/proxy | negative corr(stock flow minute series, benchmark/sector flow series) with excess-return direction | Needs flow field choice |
| abnormal_radar_event_cluster_score | P1 | 1min bars + flow + benchmark | weighted cluster of price/volume/flow anomaly flags by time segment | More complex, keep after simpler radar factor |
| retail_herding_next_open_proxy | P2 | 1min + small-order/L2 if available | corr(T intraday return, T+1 morning small-order net inflow) | Blocked without small-order classification |

### B. Academic / GitHub / Formula Libraries

The best contribution here is not more generic alphas, but reusable high-frequency-to-daily factor templates.

Evidence:

- DolphinDB high-frequency-to-low-frequency docs describe adapting 100+ public-report/academic factors to minute OHLC, Level2 snapshots, tick-by-tick orders, and trades.
- DolphinDB real-time factor docs show pipeline factors from minute OHLC and recent-window net money-flow ratios.
- WorldQuant 101 / Qlib Alpha158/Alpha360 are useful formula templates, but many overlap existing daily OHLCV features unless rewritten into intraday/asof-safe versions.
- Shenzhen extreme price-change paper supports shock/decay factors around large intraday moves: volume imbalance, bid-ask spread, volatility, and order aggressiveness rise before events and decay after.

Candidate families:

| Candidate | Priority | Data need | Formula sketch | Duplicate / gate |
|---|---:|---|---|---|
| shock_volume_decay_half_life | P0 | 1min bars | after large intraday return shock, fit decay of volume_zscore; shorter/longer half-life as factor | New, minute-only proxy of order-flow shock |
| shock_price_reversal_efficiency | P0 | 1min bars | post-shock opposite-direction return / shock magnitude over N minutes | Related to C183, but event-conditioned |
| intraday_noise_to_trend_ratio | P1 | 1min bars | sum(abs(minute_ret)) / abs(cumulative_ret), segment-normalized | Common HF template, useful as choppiness |
| signed_volume_early_late_ratio | P0 | 1min bars | signed volume in first K bars / signed volume in latest K bars before cutoff | DolphinDB pipeline idea; asof-safe |
| minute_vwap_drift_slope | P1 | 1min bars | slope(close/vwap - 1) over morning and afternoon segments | Check C135/C176 overlap |
| intraday_range_compression_break | P1 | 1min bars | narrow rolling range followed by expansion, normalized by same-clock baseline | Shortline breakout proxy |

### C. Social Media / Forum / Live-Trader Signals

This source has strong conceptual value but is the most pipeline-dependent.

Evidence:

- Eastmoney Guba topic-attention study reports firm-day topic-intensity measures predicting future returns and volatility, stronger among smaller/non-main-board firms and post-2015.
- Guba sentiment/overtrading research uses high-frequency sentiment indices inferred from Guba posts for CSI300/CSI500 constituents from 2018-2022.
- Other Chinese sentiment papers use BERT or post volume/comment/read/like information from Eastmoney Guba to link sentiment, liquidity, volatility, or returns.

Candidate families:

| Candidate | Priority | Data need | Formula sketch | Duplicate / gate |
|---|---:|---|---|---|
| guba_topic_attention_zscore | P1 | timestamped Guba posts + stock/theme mapping | topic_count_to_cutoff / trailing same-clock baseline, z-scored | More precise than C287 |
| guba_attention_turnover_coupling | P1 | Guba attention + 1min turnover | zscore(attention_growth) * zscore(turnover_acceleration) | Similar to C286/C287; formalize only if source-specific |
| guba_sentiment_volatility_asymmetry | P2 | Guba sentiment + 1min bars | sentiment shock * realized_volatility_1min, split positive/negative sentiment | Needs NLP classifier |
| guba_topic_lifecycle_stage | P2 | Guba topic model | topic infancy/growth/climax/decay stage from rolling topic intensity | Needs topic pipeline |
| social_attention_smallcap_sensitivity | P2 | social attention + cap/board | attention shock * smallcap/non-main-board dummy | Paper-supported heterogeneity |
| live_trader_consensus_breadth | P2 | KOL/live/short-video scrape | unique credible authors mentioning same stock/theme before cutoff / baseline | Requires source list and timestamps |

Do not train social factors until:

- Each post/video has a timestamp.
- Mention can be mapped to stock or theme.
- The value is computed only from information available before the prediction cutoff.
- Re-scrape produces stable counts.

### D. Taoguba / Shortline Trading Context

Taoguba is still the best source for A-share-specific shortline structure, but many ideas already exist in C001-C292. The remaining value is to convert phrases into stable market-state variables.

Evidence:

- Taoguba emotion-cycle content emphasizes connected-board height compression, seal-rate collapse, broken-board loss, dragon-head extreme boards, yesterday-limit premium, and retreat acceleration.
- Existing registry already has many board/limit/auction/leader candidates, so new additions should be market-state composites or stricter variants, not duplicate names.

Candidate families:

| Candidate | Priority | Data need | Formula sketch | Duplicate / gate |
|---|---:|---|---|---|
| board_height_compression_speed | P0 | limit_list_d | delta(max_board_height, 1d/3d) with no-4-board streak flag | New; distinct from C230 board height level |
| seal_rate_collapse_3d | P0 | limit_list_d | rolling seal_rate drop from recent peak, plus broken-board next-day loss | Extends C098/C109 but more mechanical |
| broken_board_loss_diffusion | P0 | limit_list_d + next-day returns | mean next-day return of broken-board stocks and count below threshold | Strong risk regime |
| yesterday_limit_premium_peak_risk | P1 | limit_list_d + daily/auction | yesterday-limit average premium high then falling; risk of climax | Related to market emotion, not single-stock |
| dragon_head_extreme_board_warning | P1 | limit_list_d + daily returns | high-board leader extreme board/reversal event multiplied by high-board count | Needs robust leader definition |
| theme_ladder_gap_penalty | P1 | theme mapping + limit_list_d | missing middle echelon penalty inside hot theme ladder | Refines C271 |

## Recommended C293+ Engineering Review Queue

If we ask CC to engineer-review rather than train, the next queue should be:

| Rank | Candidate | Source lane | Priority | Why |
|---:|---|---|---:|---|
| 1 | minute_turnover_stability_20d | broker/minute | P0 | Explicitly report-backed; data now available if 1min + float exists |
| 2 | minute_pv_corr_segmented | broker/minute | P0 | Explicitly report-backed; shortline segment version may add new info |
| 3 | high_position_volume_event_ratio | broker/event | P0 | Strong high/low-volume event logic; easy formula lock |
| 4 | high_vol_price_position_ratio | broker/minute | P0 | Strong empirical framing in report; 1min computable |
| 5 | shock_volume_decay_half_life | paper/HF | P0 | Shortline shock decay; no Level2 needed |
| 6 | shock_price_reversal_efficiency | paper/HF | P0 | Uses intraday reversal after extreme moves; no Level2 needed |
| 7 | signed_volume_early_late_ratio | GitHub/HF template | P0 | Simple asof-safe pipeline factor |
| 8 | board_height_compression_speed | Taoguba | P0 | Very A-share shortline-specific |
| 9 | seal_rate_collapse_3d | Taoguba | P0 | Direct market emotion risk gate |
| 10 | broken_board_loss_diffusion | Taoguba | P0 | Captures loss-effect spread |
| 11 | abnormal_radar_flow_corr | broker/event | P1 | Good but depends on flow field choice |
| 12 | theme_ladder_gap_penalty | Taoguba | P1 | Needs clean theme mapping |
| 13 | guba_topic_attention_zscore | social/forum | P1 | Strong academic support, blocked by scrape pipeline |
| 14 | guba_attention_turnover_coupling | social/forum | P1 | Strong shortline interaction, blocked by scrape pipeline |
| 15 | intraday_noise_to_trend_ratio | formula/HF | P1 | Easy, but must check duplicate with volatility/reversal factors |

## Data Needs Created By This Search

Already likely available or derivable:

- `stk_mins_1`: for all minute candidates.
- `daily`, `daily_basic`, `pro_bar`: for trailing return/turnover/float normalization.
- `limit_list_d`, `stk_limit`: for board height, seal rate, broken-board and yesterday-limit premium.
- `share_float`: for minute turnover.
- benchmark/index minute bars if available; otherwise approximate with full-market minute breadth.

Still uncertain / blocked:

- True small-order / order aggressiveness classification.
- Level2 orderbook/depth snapshots for MCI-style bid/ask liquidity.
- Stable Guba / Bilibili / Douyin / KOL timestamped scrape.
- Reliable theme membership at historical dates.

## Registration Discipline

Do not auto-add all candidates. Next step should be a strict engineering review that:

1. Checks exact duplicates against C001-C292 by formula, not just name.
2. Labels each candidate as `ready_to_register`, `needs_formula_lock`, `needs_data_pipeline`, or `reject_duplicate`.
3. Adds only ready candidates as C293+ with full fields:
   `factor_id`, `name`, `family`, `source_type`, `raw_idea`, `computable_definition`, `data_need`, `asof_rule`, `leakage_risk`, `related_existing_features`, `duplicate_check`, `priority`, `training_status=not_trained`, `lockbox_role=research_candidate`.
4. Leaves P2 social/Level2 candidates in report backlog until data is deterministic.

## Sources

- CSC high-frequency factor library: https://www.sdyanbao.com/detail/374422
- Huatai minute-level explainable factor framework summary: https://www.sohu.com/a/1003727967_122014422
- Guosheng 2024 quant strategy, minute turnover/volatility/price-volume factors: https://aigc.idigital.com.cn/djyanbao/%E3%80%90%E5%9B%BD%E7%9B%9B%E8%AF%81%E5%88%B8%E3%80%912024%E5%B9%B4%E5%BA%A6%E9%87%91%E8%9E%8D%E5%B7%A5%E7%A8%8B%E4%B8%AD%E6%9C%9F%E7%AD%96%E7%95%A5%E5%B1%95%E6%9C%9B-2024-07-14.pdf
- Guosheng high/low-volume event report: https://bigdata-s3.wmcloud.com/researchreport/2023-12/169254d9654de9c32112aaa089cceb44.pdf
- Guosheng abnormal radar event cluster: https://www.fxbaogao.com/detail/5296242
- DolphinDB high-frequency to low-frequency factors: https://docs.dolphindb.com/en/Tutorials/hf_to_lf_factor.html
- DolphinDB real-time high-frequency factors: https://docs.dolphindb.com/en/3.00.5/Tutorials/high_frequency_factors.html
- A-share Guba sentiment and intraday overtrading: https://arxiv.org/abs/2404.12001
- Retail investor forum topic attention: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6062915
- Chinese investor sentiment, liquidity and volatility: https://arxiv.org/abs/2205.05719
- Taoguba emotion-cycle retreat signal example: https://m.tgb.cn/a/2luP37oIbzF
- Order flow dynamics around extreme intraday price changes: https://arxiv.org/abs/1003.0168
