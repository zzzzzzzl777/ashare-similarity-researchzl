# Next Factor Candidates -- 2026-05-05 Round 6

> Round: sixth batch, saturation-verification search
> Goal: Only genuinely new data dimensions not captured by C001-C127 or expanded/research features
> Constraint: no training, no gpu_probe.py changes, no frozen_forward_config changes
> Data-first filter: only candidates using verified cached data (804+ parquet files)
> Existing duplicates checked against: C001-C127 + GPU_PROBE_STABLE_FEATURES (370) + GPU_PROBE_RESEARCH_FEATURES (413)

## Saturation Verification Note

**Round 5 recommended closing search. This round is a targeted verification pass focused on COMPLETELY UNUSED DATA SOURCES — not formula variants.**

Methodology: Instead of brainstorming factor ideas and checking for duplicates (round 1-5 approach), this round starts from DATA — scanning all 31 tushare cache directories for columns that are NEVER referenced in any feature constant or candidate formula. Only 5 dimensions passed the filter.

Evidence of saturation:
- 370 stable features + 413 research features = 783 defined features
- 127 candidates across 30 families
- This round found exactly 5 candidates from 3 completely untouched data sources
- All other ideas were variants of already-captured concepts

---

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | 4 | Completely unused data source, clear formula, high coverage |
| P1 | 1 | Clear formula but moderate overlap concern with overnight_return |
| P2 | 0 | — |
| blocked | 0 | — |
| **Total** | **5** | (minimum viable — exactly at threshold) |

## Duplicates Checked and Removed

- 融资余额/总市值比 → rzye used in tushare_rzye; this is just normalization, same signal
- 中单净流入占比 → derivative of net (covered by mf_flow_intensity logic family)
- 涨停封单金额 vs 流通市值 → seal_money_to_float_mv already in research features
- 大盘量能百分位 → market_amount_percentile_60 exists in research
- 个股PE分位数 → requires 5-year history normalization; daily_basic PE is raw level (see C128 for proper usage)
- 全球VIX恐慌指数 → not in index_global cache (only price indices, no VIX)
- 融券卖出量rqmcl → too sparse (many stocks have 0 rqye entirely); coverage < 40%
- 股东人数变化率 → tushare_holder_num_delta_pct already in research features
- 机构净买入 from top_inst → tushare_inst_net_buy already in research features  
- 北向净流入 vs 全球指数 → combination of C052 + proposed C128; not genuinely new

---

## P0 Candidates (4)

### C128: global_risk_sentiment_overnight

| Field | Value |
|-------|-------|
| factor_id | C128 |
| name | Global Risk Sentiment Overnight |
| family | cross_market_regime |
| source_type | github_paper |
| source_ref | Overnight foreign returns as A-share opening predictor; 隔夜全球情绪 |
| raw_idea | Weighted average of key global index prior-day returns (SPX, N225, HSI) as overnight risk sentiment proxy for A-share opening. Not individual index, but aggregate risk-on/risk-off signal. |
| computable_definition | `0.4 * pct_chg(SPX) + 0.3 * pct_chg(N225) + 0.3 * pct_chg(HSI)` broadcast (market-level; indices trade before A-share open) |
| data_need | index_global (804 parquet files, 19 indices including SPX, N225, HSI) |
| asof_rule | T-1 day close of foreign indices (known before A-share T-day open) |
| leakage_risk | none — foreign indices close before A-share opens |
| coverage_estimate | 100% (market broadcast; index_global has 18-20 indices consistently) |
| related_existing_features | overnight_return (A-share's OWN overnight gap); C078 index_relative_strength (A-share INDEX only) |
| duplicate_check | overnight_return is THIS STOCK's own gap. C078 is A-share index. C052 is northbound FLOW. NO existing feature uses FOREIGN INDEX RETURNS. Data source (index_global) is completely unused in all 783 features. Genuinely new cross-market dimension. |
| engineering_status | candidate_ready |
| priority | P0 |

### C129: market_valuation_regime

| Field | Value |
|-------|-------|
| factor_id | C129 |
| name | Market Valuation Regime |
| family | cross_market_regime |
| source_type | github_paper |
| source_ref | Valuation-conditional momentum; PE_TTM percentile as regime filter |
| raw_idea | CSI300 PE_TTM rolling 60-day percentile as market valuation regime. High percentile = crowded/expensive market (risk-on fragile), low percentile = cheap market (mean-reversion setup). |
| computable_definition | `rank(pe_ttm_000300SH, window=60) / 60` broadcast (market-level; value 0-1) |
| data_need | index_dailybasic (804 parquet files, CSI300 PE_TTM daily) |
| asof_rule | T-day close |
| leakage_risk | none — PE_TTM computed from prior-day close prices and latest reported earnings |
| coverage_estimate | 100% (market broadcast from index-level data) |
| related_existing_features | NONE. Zero PE/PB/valuation features exist in stable (370) or research (413) feature lists. |
| duplicate_check | Entirely new data dimension. No valuation features exist anywhere. index_dailybasic has pe, pe_ttm, pb columns at 100% coverage for main indices but is NEVER used in any feature pipeline. |
| engineering_status | candidate_ready |
| priority | P0 |

### C130: medium_order_net_ratio

| Field | Value |
|-------|-------|
| factor_id | C130 |
| name | Medium Order Net Flow Ratio |
| family | moneyflow_derivative |
| source_type | taoguba |
| source_ref | 中单力量 "大单对倒+散户接盘时，中单动向才是真实方向" |
| raw_idea | Net medium-order flow as fraction of total. Medium orders (50-200万) reflect genuine mid-size players — not institutional manipulation (elg/lg) nor retail noise (sm). When lg+elg are battling, md direction reveals who's winning. |
| computable_definition | `(buy_md_amount - sell_md_amount) / (buy_md_amount + sell_md_amount + eps)` |
| data_need | moneyflow (804 parquet files; buy_md_amount, sell_md_amount columns — currently UNUSED) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~99% |
| related_existing_features | C001 mf_flow_intensity (net/total), C009 main_force_divergence (lg vs elg), tushare_sm_sell_pressure (small) |
| duplicate_check | C001 is NET total flow. C009 is lg vs elg divergence. tushare_sm_sell_pressure is small-order. ALL existing moneyflow features use net_mf, lg, elg, or sm. buy_md_amount and sell_md_amount are NEVER referenced in any feature. Medium orders are a completely separate trader class. |
| engineering_status | candidate_ready |
| priority | P0 |

### C131: margin_repayment_intensity

| Field | Value |
|-------|-------|
| factor_id | C131 |
| name | Margin Repayment Intensity |
| family | margin_derivative |
| source_type | taoguba |
| source_ref | 融资强平预警 "余额不变但偿还放大=被动还款=逼近平仓线" |
| raw_idea | Ratio of margin repayment to new margin buying. High repayment relative to new buys means existing margin holders are being squeezed/closing positions, even if balance (rzye) is stable. |
| computable_definition | `rzche / (rzmre + eps)` where rzche=融资偿还额, rzmre=融资买入额 from margin_detail |
| data_need | margin_detail (804 parquet files; rzche and rzmre columns — currently UNUSED) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~36% (only stocks with active margin trading — margin_detail has ~1989 stocks per day out of ~5400) |
| related_existing_features | tushare_rzye (balance level), tushare_rzye_delta_pct (balance change), C069 margin_momentum_5d (balance trend) |
| duplicate_check | All existing margin features use RZYE (融资余额 = balance). This uses RZCHE (偿还额) and RZMRE (买入额) — the FLOW components that make up the balance change. Balance can be stable while underneath there's massive churn (high repayment + high new buying). This captures margin STRESS that balance-based features miss. |
| engineering_status | candidate_ready |
| priority | P0 |

---

## P1 Candidates (1)

### C132: large_order_avg_size_ratio

| Field | Value |
|-------|-------|
| factor_id | C132 |
| name | Large Order Average Size Ratio |
| family | moneyflow_derivative |
| source_type | github_paper |
| source_ref | Order size distribution as institutional footprint; 大单平均单笔金额 |
| raw_idea | Average single-order size for large+extra-large orders (amount/vol). Higher average = fewer but bigger orders = more concentrated institutional action. Changes in average size reveal whether "large flow" is one whale or many mid-institutions. |
| computable_definition | `(buy_elg_amount + buy_lg_amount) / (buy_elg_vol + buy_lg_vol + eps) / ((sell_elg_amount + sell_lg_amount) / (sell_elg_vol + sell_lg_vol + eps) + eps)` (buy-side avg order size / sell-side avg order size) |
| data_need | moneyflow (804 parquet files; buy_elg_vol, sell_elg_vol, buy_lg_vol, sell_lg_vol — currently UNUSED volume columns) |
| asof_rule | T-day close |
| leakage_risk | none |
| coverage_estimate | ~95% (requires non-zero elg+lg vol; very small stocks may have 0) |
| related_existing_features | C001 mf_flow_intensity, tushare_elg_buy_sell_ratio (amount ratio only), mega_order_absorption_proxy (research) |
| duplicate_check | tushare_elg_buy_sell_ratio uses AMOUNT only (buy_elg_amount/sell_elg_amount). mega_order_absorption_proxy is in research. This uses VOLUME (order count) to compute AVERAGE ORDER SIZE — a different information axis (concentration vs magnitude). Moderate overlap concern: tree models might reconstruct from amount/vol separately, hence P1 not P0. |
| engineering_status | candidate_ready |
| priority | P1 |

---

## Data Source Verification

| Source | Files | Coverage | Columns Used | New Columns This Round |
|--------|-------|----------|--------------|------------------------|
| index_global | 804 | 100% (broadcast) | NONE previously | pct_chg (SPX, N225, HSI) |
| index_dailybasic | 804 | 100% (broadcast) | NONE previously | pe_ttm (000300.SH) |
| moneyflow | 804 | ~99% (stock) | net_mf_amount, buy/sell_lg/elg/sm amounts | buy_md_amount, sell_md_amount, buy_elg_vol, sell_elg_vol, buy_lg_vol, sell_lg_vol |
| margin_detail | 804 | ~36% (margin stocks) | rzye only | rzche, rzmre |

---

## Engineering Readiness Summary

| Status | IDs | Count |
|--------|-----|-------|
| candidate_ready | C128-C132 | 5 |

## Implementation Priority

| Rank | ID | Name | Coverage | Why |
|------|-----|------|----------|-----|
| 1 | C128 | global_risk_sentiment_overnight | 100% | Completely unused data source; well-established cross-market factor in literature |
| 2 | C129 | market_valuation_regime | 100% | Zero valuation features exist; adds entirely new information axis |
| 3 | C130 | medium_order_net_ratio | ~99% | Unused moneyflow columns; mid-size trader class never measured |
| 4 | C131 | margin_repayment_intensity | ~36% | Unused margin_detail fields; captures stress vs balance-only signals |
| 5 | C132 | large_order_avg_size_ratio | ~95% | Unused vol columns; moderate overlap concern (P1) |

---

## Search Saturation Final Confirmation

**This round confirms round 5's saturation assessment.** Starting from DATA rather than IDEAS:
- 31 tushare directories scanned
- Only 3 sources had genuinely unused columns (index_global, index_dailybasic, moneyflow vol fields + margin_detail flow fields)
- 10+ ideas were rejected as duplicates of existing features/candidates
- Remaining whitespace after this round: tick data, NLP, cross-asset (bonds/commodities), meta-level timing

**Recommendation remains: close factor search after this round.**

---

## Constraints Confirmation

- [x] No training executed
- [x] No gpu_probe.py changes
- [x] No frozen_forward_config changes
- [x] No passed/final_unseen/final_accepted claims
- [x] All candidates use verified cached data (804 files each)
- [x] Duplicate check against C001-C127 + all 783 defined features
- [x] Minimum threshold met (5 candidates with genuinely new data dimensions)

---

*Factor search round 6, 2026-05-05. 5 new candidates (C128-C132). Data-first verification confirms saturation. Factor search closed.*
