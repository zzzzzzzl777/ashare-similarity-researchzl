# Next Factor Candidates -- 2026-05-05 Round 5

> Round: fifth batch, saturation-aware gap fill
> Goal: Only genuinely new dimensions not captured by C001-C117
> Constraint: no training, no gpu_probe.py changes, no frozen_forward_config changes
> Data-first filter: only candidates using verified cached data
> Existing duplicates checked against: C001-C117 + GPU_PROBE_STABLE_FEATURES + TUSHARE_FACTOR_COLUMNS

## Search Saturation Note

**After 117 candidates across 30 families, search is approaching saturation.** This round found only 10 candidates with genuinely new dimensions. The majority of remaining ideas (>70%) mapped to slight variations of existing formulas (different window lengths, minor parameter tweaks, or combinations of concepts already captured). Remaining whitespace is:
- Tick/Level-2 data (not cached → blocked)
- NLP/text-based factors (requires pipeline → out of scope)
- Cross-asset signals (bonds/commodities/USD → not in tushare cache)
- Factor timing/regime-switching (meta-level, requires existing factor outputs as inputs)

**Recommendation**: Stop searching after this round. Shift effort to engineering and ablation testing of the best P0 candidates from rounds 1-5.

---

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 6 | Data cached, formula clear, genuinely new dimension not in C001-C117 |
| P1 | 3 | Strong logic but moderate overlap concern or engineering complexity |
| P2 | 1 | Sparse or conditional |
| blocked | 0 | — |
| **Total** | **10** | (intentionally lean — saturation reached) |

## Duplicates Checked and Removed (>15 ideas rejected)

- 放量回踩承接 → close to C085 pullback_support_ratio
- 连续涨停后缩量 → close to C103 volume_shrink_streak + C094 consecutive board
- 主力资金加速度 → close to C002 mf_momentum_5d (same z-score logic)
- 北向持股集中度 → close to C070 hk_hold_acceleration (similar information)
- 融资/主力对比 → C095 margin_flow_alignment already covers
- 涨停溢价率 → prev_limit_up_premium already in expanded features
- 全天量能分布均匀度 → close to C065 last_hour_volume (inverse perspective)
- 板块热度衰减 → close to C082 ths_daily_concept_heat (level captures recent)
- 低位放量 → close to C104 volume_expansion_breakout (includes price position)
- 尾盘杀跌幅度 → C113 tail_session_escape_pressure already covers
- 周五效应 dummy → day_of_week_sin/cos already in expanded (linear combination)
- 赚钱效应 z-score → C109 losing_money_effect_regime is the same signal (just inverted)
- 北向 vs 融资 → C111 margin_vs_northbound_divergence already covers
- 热度与筹码背离 → close to C092 winner_rate_flow_divergence logic
- 波动收敛后方向 → C112 consecutive_narrow_range captures compression

---

## P0 Candidates (6)

### C118: volume_price_stagnation

| Field | Value |
|-------|-------|
| factor_id | C118 |
| name | Volume-Price Stagnation |
| family | volume_structure |
| source_type | taoguba |
| source_ref | 量价背离 "放量滞涨 = 上方抛压重，主力对倒出货" |
| raw_idea | Volume expanding significantly but price barely moving = selling pressure absorbing buying volume at current level |
| computable_definition | `max(volume / mean(volume, 5) - 1, 0) * (1 - abs(ret_1d) / (range_pct + eps))` (high volume surplus × low directional efficiency) |
| data_need | daily OHLCV, 5-day volume mean |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | C104 (volume expansion × price HIGH — bullish breakout); volume_ratio; range_pct |
| duplicate_check | C104 is volume × price-at-high (bullish). This is volume × price-NOT-moving (bearish stagnation). Opposite signal — volume expanding but NO directional progress. Not captured anywhere. |
| engineering_status | candidate_ready |
| priority | P0 |

### C119: losing_effect_persistence_3d

| Field | Value |
|-------|-------|
| factor_id | C119 |
| name | Losing Effect Persistence 3-Day |
| family | risk_filter |
| source_type | taoguba |
| source_ref | 打板节奏 "亏钱效应连续3天 = 冰点，第4天可能反转" |
| raw_idea | How many of last 3 days had negative board premium (losing-money effect) — persistence means hostile regime deepening |
| computable_definition | `sum(prev_day_limit_pool_avg_return[T-i] < 0 for i in 0..2) / 3` broadcast (fraction of last 3 days with losing effect) |
| data_need | limit_list_d (T-1..T-3 pools) + daily OHLCV (returns for pool stocks) |
| asof_rule | T-day close |
| leakage_risk | none — all use realized returns of past pools |
| coverage_estimate | 100% (market broadcast) |
| related_existing_features | C109 (single-day losing effect level) |
| duplicate_check | C109 is TODAY's losing effect (single-day level). This is PERSISTENCE over 3 days — whether hostile regime is sustained or one-off. Different: regime duration vs single reading. |
| engineering_status | candidate_ready |
| priority | P0 |

### C120: sector_leadership_decay

| Field | Value |
|-------|-------|
| factor_id | C120 |
| name | Sector Leadership Decay |
| family | market_regime |
| source_type | github_paper |
| source_ref | Sector rotation speed; leadership half-life in A-shares |
| raw_idea | How much the leading sector's excess return has decayed from its 5-day peak — measures rotation speed |
| computable_definition | `(best_sector_ret_5d - best_sector_ret_1d) / (abs(best_sector_ret_5d) + eps)` broadcast; positive = sector fading |
| data_need | ths_daily (sector/concept board returns) or moneyflow_ind_dc |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | 100% (market broadcast using sector data) |
| related_existing_features | C082 (max concept return today), sector_pct_change_best (single-day best sector) |
| duplicate_check | C082/sector_pct_change are TODAY's best sector. This measures decay of LEADERSHIP over time — how fast the top sector is losing its edge. Temporal dynamics, not snapshot. |
| engineering_status | candidate_ready |
| priority | P0 |

### C121: overnight_gap_risk_proxy

| Field | Value |
|-------|-------|
| factor_id | C121 |
| name | Overnight Gap-Down Risk Proxy |
| family | risk_filter |
| source_type | taoguba |
| source_ref | 打板风控 "连板高位+尾盘放量+板块退潮 = 明日核按钮" |
| raw_idea | Stocks at high board count in fading sector environment have elevated gap-down risk next day |
| computable_definition | `prev_board_count * max(-sector_pct_change_best, 0) * (volume / mean(volume, 5))` (board height × sector weakness × volume abnormality) |
| data_need | limit_list_d (prev_board_count) + sector features + daily OHLCV (volume) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~5-10% (only applies to stocks with recent limit-up history) |
| related_existing_features | C109 (market-level losing effect), C087 (pool relative strength), prev_board_count (raw) |
| duplicate_check | C109 is market-level. C087 is relative rank. prev_board_count is raw height. This is HEIGHT × SECTOR_RETREAT × VOLUME interaction — specific nuclear-button risk composite. Three-way interaction not captured. |
| engineering_status | candidate_ready |
| priority | P0 |

### C122: flow_consensus_convergence

| Field | Value |
|-------|-------|
| factor_id | C122 |
| name | Flow Consensus Convergence |
| family | moneyflow_derivative |
| source_type | taoguba |
| source_ref | 分歧转一致 "大单/超大单从分歧到一致 = 即将启动" |
| raw_idea | C009 (main_force_divergence) decreasing over multiple days means lg/elg converging from disagreement to consensus — precedes directional move |
| computable_definition | `main_force_divergence[T-3] - main_force_divergence[T]` (positive = divergence shrinking = convergence) |
| data_need | tushare moneyflow (pre-computed C009 or lg/elg ratios), 3-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | C009 (main_force_divergence level — the signal this is derived from) |
| duplicate_check | C009 is divergence LEVEL (snapshot). This is divergence CHANGE — are institutions converging or diverging over time? First derivative of a validated factor. Directly analogous to how C002 is first derivative of net_mf. |
| engineering_status | candidate_ready |
| priority | P0 |

### C123: support_failure_signal

| Field | Value |
|-------|-------|
| factor_id | C123 |
| name | Support Failure Signal |
| family | intraday_structure |
| source_type | social_live |
| source_ref | 游资实盘 "回踩均线不守住 → 跌破 VWAP = 承接失败，出局" |
| raw_idea | After intraday pullback, if close ends below VWAP despite earlier recovery attempt — support has failed |
| computable_definition | `(close_vs_vwap < 0) * max(intraday_high_vs_vwap, 0)` where intraday_high_vs_vwap = (high - vwap) / vwap; product captures "was above VWAP but failed to hold" |
| data_need | stk_mins_5 (vwap, high) + daily close |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~95% |
| related_existing_features | C085 (pullback_support_ratio — measures support success); C048 (vwap reclaim — bullish) |
| duplicate_check | C085 measures how WELL support held (higher = stronger). C048 is bullish VWAP position. This is the FAILURE case — was above VWAP but fell below. Bearish complement to C085. Mirror signal. |
| engineering_status | candidate_ready |
| priority | P0 |

---

## P1 Candidates (3)

### C124: weekday_regime_interaction

| Field | Value |
|-------|-------|
| factor_id | C124 |
| name | Weekday × Market Regime Interaction |
| family | calendar_event |
| source_type | github_paper |
| source_ref | Day-of-week anomaly conditional on market state; A-share Monday/Friday asymmetry |
| raw_idea | Monday effect is stronger in bear markets; Friday effect is stronger in bull markets — interaction, not main effect |
| computable_definition | `day_of_week_sin * market_breadth_5d_avg` where market_breadth = advance/decline ratio average over 5 days |
| data_need | daily OHLCV (all stocks for breadth) + calendar (weekday) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | 100% (market broadcast × deterministic weekday) |
| related_existing_features | day_of_week_sin/cos (main effect only), C089 (breadth level) |
| duplicate_check | day_of_week_sin exists (main effect). C089 is breadth (level). This is their INTERACTION — weekday effect conditional on market state. Neither alone captures this. Moderate concern: tree-based models can learn this interaction from raw features. |
| engineering_status | candidate |
| priority | P1 |

### C125: volume_price_efficiency_trend

| Field | Value |
|-------|-------|
| factor_id | C125 |
| name | Volume-Price Efficiency Trend |
| family | volume_structure |
| source_type | github_paper |
| source_ref | Amihud-style price impact trend; efficiency improving or worsening |
| raw_idea | 5-day trend in price-per-unit-volume — improving efficiency (less volume needed to move price) signals institutional interest |
| computable_definition | `linreg_slope(abs(ret_1d) / (volume / mean(volume, 20) + eps), window=5)` |
| data_need | daily OHLCV, 25-day window |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | C023 amihud_illiquidity_20d (level), C118 (stagnation snapshot) |
| duplicate_check | C023 is amihud LEVEL (average over 20d). C118 is single-day stagnation. This is TREND in efficiency — is the stock becoming easier or harder to move? Different: dynamics of liquidity, not level. |
| engineering_status | candidate |
| priority | P1 |

### C126: earning_effect_spread

| Field | Value |
|-------|-------|
| factor_id | C126 |
| name | Earning-Effect Market Spread |
| family | market_regime |
| source_type | taoguba |
| source_ref | 赚钱效应扩散 "涨停溢价+炸板率+连板高度 综合衡量" |
| raw_idea | Composite of board premium, broken-board rate (inverted), and max board height — holistic earning-effect diffusion score |
| computable_definition | `zscore(prev_limit_pool_avg_return, 20) - zscore(market_broken_board_rate, 20) + zscore(max_board_height, 20)` broadcast, averaged |
| data_need | limit_list_d + market features (already available) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | 100% (market broadcast) |
| related_existing_features | C109 (losing effect level), C098 (broken board fear), C090 (limit density) |
| duplicate_check | C109 is single component (premium). C098 is single component (broken rate). C090 is limit ratio. This combines 3 z-scored components into one composite diffusion score. May be highly correlated with C109 alone — needs ablation to prove incremental value over constituent parts. |
| engineering_status | candidate |
| priority | P1 |

---

## P2 Candidates (1)

### C127: second_attempt_support

| Field | Value |
|-------|-------|
| factor_id | C127 |
| name | Second-Attempt Intraday Support |
| family | intraday_structure |
| source_type | taoguba |
| source_ref | 二次承接 "冲高回落后再拉升能否创新高=二次确认" |
| raw_idea | After pullback from intraday high, does second attempt reach or exceed the prior high? Captures "double-top fail" vs "higher-high confirm" |
| computable_definition | `(second_high - first_high) / (first_high - open + eps)` from 5-min bar structure; requires peak detection |
| data_need | stk_mins_5 (requires algorithmic peak/trough detection in intraday bars) |
| asof_rule | T-day 14:57 |
| leakage_risk | none |
| coverage_estimate | ~80% (requires at least 2 identifiable peaks in intraday structure) |
| related_existing_features | C085 (single pullback support), C086 (max drawdown from high) |
| duplicate_check | C085 is first pullback support. C086 is max drawdown. This is second-attempt structure (double-top/higher-high). Different: requires peak detection algorithm, engineering complexity higher. |
| engineering_status | needs_validation |
| priority | P2 |

---

## Search Saturation Note

**The factor search has reached saturation for the current data universe.**

Evidence:
- Round 1-2 (C043-C082): 40 candidates, nearly all genuinely new
- Round 3 (C083-C102): 20 candidates, some moderate overlap concerns noted
- Round 4 (C103-C117): 15 candidates, intentionally lean
- **Round 5 (C118-C127): 10 candidates, >70% of initial ideas were rejected as duplicates**

Remaining whitespace requires:
1. **Tick/Level-2 data** (order book depth, order flow imbalance, HFT features) — not cached
2. **NLP/text pipeline** (news sentiment, earnings call tone, announcement keywords) — requires separate system
3. **Cross-asset signals** (bond-equity spread, commodity momentum, USD/CNH) — not in tushare cache
4. **Meta-level timing** (factor rotation, regime-switching over factors themselves) — requires trained factors as inputs

**Recommendation**: Close factor search. Begin engineering + ablation pipeline for top candidates from all 5 rounds.

---

## Engineering Readiness Summary

| Status | IDs | Count |
|--------|-----|-------|
| candidate_ready | C118-C123 | 6 |
| candidate (minor engineering) | C124-C126 | 3 |
| needs_validation | C127 | 1 |

## Implementation Priority: Top 6 (fewer than 8 — only listing genuinely high-value)

| Rank | ID | Name | Coverage | Why |
|------|-----|------|----------|-----|
| 1 | C122 | flow_consensus_convergence | ~99% | First derivative of validated C009; "分歧转一致" is core taoguba concept |
| 2 | C118 | volume_price_stagnation | ~99% | 放量滞涨 — bearish complement to C104; classic volume-price divergence |
| 3 | C119 | losing_effect_persistence_3d | 100% | Regime DURATION extends C109's single-day signal; market broadcast |
| 4 | C120 | sector_leadership_decay | 100% | Rotation speed — how fast the top sector is fading |
| 5 | C123 | support_failure_signal | ~95% | Bearish mirror of C085; VWAP break after earlier recovery |
| 6 | C121 | overnight_gap_risk_proxy | ~5-10% | 核按钮风险 — sparse but critical for board-play risk management |

**Note**: Only 6 recommended (not 8) because C124-C127 have overlap concerns or engineering complexity that make them second-tier.

---

## Constraints Confirmation

- [x] No training executed
- [x] No gpu_probe.py changes
- [x] No frozen_forward_config changes
- [x] No passed/final_unseen/final_accepted claims
- [x] All candidates use verified cached data
- [x] Duplicate check against C001-C117
- [x] Search saturation honestly reported (>70% rejection rate)
- [x] Recommendation to close factor search included

---

*Factor search round 5, 2026-05-05. 10 new candidates (C118-C127). Search saturation reached. Recommend closing search and starting engineering/ablation.*
