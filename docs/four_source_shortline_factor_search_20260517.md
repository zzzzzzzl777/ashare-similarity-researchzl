# Four-Source Shortline Factor Search 2026-05-17

Scope: short-line A-share factor expansion only. No training, no gpu_probe, no model-code changes.

## Current Registry Baseline

- Machine registry: `E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json`
- Current registered candidates: C001-C292, 292 unique ids.
- Recent high-priority gaps:
  - 1min minute cache enables C189-C193 and many C244-C285 style intraday factors.
  - Social/forum factors C286-C289 still need timestamped scrape and asof rules.
  - Level2/orderbook candidates should stay separate unless data fields are confirmed.

## External Search Evidence

### 1. Taoguba / Shortline Trading Context

Useful new/renewed themes:

- Emotion-cycle breadth: limit-up count, down-limit count, red/green stock breadth, market turnover change, high-board height, broken-board ratio.
- Echelon integrity: 5-4-3-2 style limit-up ladder continuity, missing-echelon penalty, theme leader/follower spread.
- Weak-to-strong confirmation: post-break or post-first-negative-day auction not weak, quick red flip, VWAP reclaim.
- Retreat/ice-point reversal: recent high-board break, middle-board loss effect, down-limit cluster, next-day rebound breadth.

Candidate ideas:

| Candidate name | Priority | Data need | Computable definition sketch | Registry relation |
|---|---:|---|---|---|
| emotion_ladder_integrity | P0 | limit_list_d, daily breadth | count of contiguous board levels / max board height, with missing middle-board penalty | Extension of C230/C271, keep distinct if ladder gap is explicit |
| high_board_break_loss_effect | P0 | limit_list_d, daily returns | recent high-board break count * next-day negative breadth among 3+ board stocks | New risk-state factor |
| theme_leader_follower_spread | P1 | theme mapping, limit list, returns | leader intraday return or board status minus median follower return | Related to C249/C270, but broader theme spread |
| weak_to_strong_open_reclaim | P1 | auction + 1min bars | weak previous day + open not below threshold + first 5/15min VWAP reclaim | Related to C261, but condition-based |
| icepoint_repair_breadth | P1 | limit/down-limit counts, daily breadth | rebound breadth after recent limit-up collapse/down-limit cluster | Market regime factor |

### 2. Social Media / Forum / Live-Trader Content

Useful new/renewed themes:

- Eastmoney Guba sentiment and topic attention have academic support for intraday overtrading and later returns/volatility.
- Topic attention is better than raw mention count: track stock-specific/topic-specific attention lifecycle, not only bullish words.
- Live/short-video sources are usable only if timestamped and mapped to stock/theme before decision time.

Candidate ideas:

| Candidate name | Priority | Data need | Computable definition sketch | Registry relation |
|---|---:|---|---|---|
| guba_topic_attention_shock | P1 | guba posts with timestamp and stock/theme mapping | zscore(topic_count_today_to_cutoff / trailing same-clock baseline) | More specific than C287 |
| guba_negative_lifecycle_reversal | P2 | guba topic model/sentiment | high continuous-drop topic attention followed by intraday stabilization | Inspired by topic attention paper; needs NLP pipeline |
| social_attention_volume_coupling | P2 | social mentions + 1min volume | zscore(attention_growth) * zscore(volume_acceleration_1min) | Similar to C286/C287; only add if source-specific |
| kol_breadth_concentration | P2 | timestamped KOL mentions | unique KOL count / total mentions, with concentration penalty | Extension of C289 |
| short_video_theme_heat_decay | P2 | Bilibili/Douyin scrape | topic/video heat decay half-life for mapped theme | Requires stable scrape |

### 3. GitHub / Academic / Formula Libraries

Useful new/renewed themes:

- DolphinDB high-frequency factor docs support stateless, sliding-window, stateful, and pipeline factors from minute/tick/orderbook data.
- High-frequency-to-low-frequency factor libraries adapt public-report/academic factors to minute OHLC, Level2 snapshots, orders, and trades.
- WorldQuant 101 style formulas remain useful as formula templates, but must be asof-safe and avoid pure daily-close leakage.

Candidate ideas:

| Candidate name | Priority | Data need | Computable definition sketch | Registry relation |
|---|---:|---|---|---|
| intraday_price_volume_corr_segmented | P0 | 1min bars | corr(ret_1min, volume_1min) in morning/midday/late segments | Extends C278/C285, but segment-specific |
| minute_return_autocorr_regime | P0 | 1min or 5min bars | autocorr of minute returns under high/low volume regimes | Existing duplicate watch: C174-C188 may already cover part |
| volume_herding_stateful_decay | P1 | 1min bars | stateful decay of volume concentration after shock minute | Builds on C174/C177, keep if decay definition differs |
| intraday_liquidity_noise_ratio | P1 | 1min bars | microstructure-noise proxy / realized volatility, same-clock normalized | New if not already C285 |
| wq_open_close_range_rank_intraday | P1 | minute/daily OHLCV | rank((close-open)/(high-low)) by intraday segment, not full-day close only | Extension of C280 |

### 4. Broker / Sell-Side Reports

Useful new/renewed themes:

- CSC high-frequency factor library: 213 factors from minute/Level2 data, including capital-flow intent, liquidity, volatility, buy/sell strength.
- CSC bid/ask order liquidity: MCI_B/MCI_A uses orderbook quote volume-weighted trading cost and links to short-term return direction.
- Huatai/Guosheng/Shenwan report lines emphasize minute price-volume correlation, minute turnover stability, liquidity shock, and return repair.

Candidate ideas:

| Candidate name | Priority | Data need | Computable definition sketch | Registry relation |
|---|---:|---|---|---|
| minute_turnover_stability | P0 | 1min bars + float/share_float | std(minute_turnover) or entropy of minute turnover, same-clock normalized | Likely new if float available |
| liquidity_shock_repair_speed | P0 | 1min bars | price impact shock magnitude and time-to-repair after excluding information events | Related to C282/C285, but repair-speed focus |
| mci_bid_liquidity_proxy | P2 | Level2 5-level quotes | bid-side market-cost vs midquote, divided by depth value | Only if orderbook available |
| mci_ask_liquidity_proxy | P2 | Level2 5-level quotes | ask-side market-cost vs midquote, divided by depth value | Only if orderbook available |
| up_down_volume_strength_ratio | P0 | 1min bars | sum(volume on up-return minutes) / sum(volume on down-return minutes), segment-normalized | Check duplicate vs C191/C248 |
| late_day_price_impact_resilience | P1 | 1min bars | late-session return per unit volume after earlier shock; lower impact may indicate resilience | New |

## Most Practical Next Candidates

These look worth engineering review before adding C293+:

1. `emotion_ladder_integrity` - limit-list only, strong shortline logic.
2. `high_board_break_loss_effect` - limit-list + returns, shortline risk regime.
3. `intraday_price_volume_corr_segmented` - 1min bars, report/paper backed.
4. `minute_turnover_stability` - 1min + float/share_float, report backed.
5. `liquidity_shock_repair_speed` - 1min bars, microstructure backed.
6. `up_down_volume_strength_ratio` - 1min bars, simple and asof-safe.
7. `guba_topic_attention_shock` - high potential, requires timestamped Guba pipeline.
8. `theme_leader_follower_spread` - requires reliable theme membership and leader definition.

## Do Not Register Yet

- Pure KOL/short-video factors without stable timestamped scrape.
- True Level2 MCI_B/MCI_A unless 5-level quote/depth data is available and timestamped.
- Any factor using full-day close/volume under a 14:57 live setting unless rewritten as a 14:57 proxy.

## Source Links

- Taoguba emotion-cycle pages: `https://www.tgb.cn/talk/talkSeq/101`, `https://m.tgb.cn/a/2iT0nkym8pD?type=hot`
- A-share Guba sentiment/overtrading paper: `https://arxiv.org/abs/2404.12001`
- Retail forum topic attention SSRN: `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6062915`
- CSC high-frequency factor library: `https://www.sdyanbao.com/detail/374422`
- CSC bid/ask order liquidity report: `https://asset.quant-wiki.com/pdf/%E4%B8%AD%E4%BF%A1%E5%9B%A0%E5%AD%90%E6%B7%B1%E5%BA%A6%E7%A0%94%E7%A9%B6%E7%B3%BB%E5%88%9710%EF%BC%9A%E4%B9%B0%E5%8D%96%E6%8A%A5%E5%8D%95%E6%B5%81%E5%8A%A8%E6%80%A7%E5%9B%A0%E5%AD%90%E6%9E%84%E5%BB%BA.pdf`
- DolphinDB high-frequency factors: `https://docs.dolphindb.com/en/3.00.5/Tutorials/high_frequency_factors.html`
- DolphinDB high-frequency to low-frequency factors: `https://docs.dolphindb.com/en/Tutorials/hf_to_lf_factor.html`
- DolphinDB WorldQuant 101 alphas: `https://docs.dolphindb.com/en/3.00.5/Tutorials/wq101alpha.html`
