# Data-Unlocked Factor Mapping (2026-05-15)

## Summary

- Added candidate batch: `candidates_20260515_data_unlocked`
- Added factor IDs: `C189-C222`
- Added candidates: 34
- Priority split: P0=13, P1=17, P2=4
- Scope: factor-library registration only. No training, no gpu_probe, no model code change.
- All new entries are `training_status=not_trained` and `lockbox_role=research_candidate`.

## Added Candidates

| ID | Name | Priority | Family | Source/Data | Definition | Status |
|----|------|----------|--------|-------------|------------|--------|
| C189 | rv_ratio_1min_vs_5min | P0 | intraday_microstructure | stk_mins / 1min and 5min minute bars | realized_volatility(1min returns) / (realized_volatility(5min returns) + eps) | data_unlocked_needs_1min_backfill |
| C190 | first_5min_strength_1min | P0 | intraday_microstructure | stk_mins / 1min minute bars | (close_09:35 - open_09:30) / open_09:30 | data_unlocked_needs_1min_backfill |
| C191 | attack_volume_real_1min | P0 | intraday_microstructure | stk_mins / 1min minute bars | sum(vol_i * I(ret_i > 0 and close_i near rolling high), early session) / sum(vol_i, early session) | data_unlocked_needs_1min_backfill |
| C192 | dynamic_volume_acceleration_1min | P1 | intraday_microstructure | stk_mins / 1min bars plus same-clock historical baseline | slope(log(volume_1min + 1)) over recent N bars normalized by same-clock historical median | data_unlocked_needs_1min_backfill |
| C193 | reseal_speed_1min | P1 | limit_pool_intraday | stk_mins + stk_limit/limit_list_d / 1min bars plus daily limit price | Minutes between first up-limit touch and successful reseal; missing if no touch. | data_unlocked_needs_1min_backfill |
| C194 | stk_factor_pro_technical_bank | P0 | technical_indicator_bank | stk_factor_pro / vendor-computed technical indicator columns | Curated feature bank from stk_factor_pro technical indicators after removing raw OHLCV/adj duplicates and choosing one adjustment family. | source_verified_needs_full_backfill_and_column_catalog |
| C195 | technical_momentum_confirmation | P1 | technical_indicator_bank | stk_factor_pro / MACD/KDJ/RSI style fields after catalog | zscore(MACD histogram/diff) + zscore(KDJ J-D) + zscore(RSI short-long) | needs_stk_factor_pro_column_catalog |
| C196 | technical_squeeze_breakout | P1 | technical_indicator_bank | stk_factor_pro / BOLL/ATR style fields after catalog | BOLL bandwidth compression plus close position over middle/upper band, normalized by ATR. | needs_stk_factor_pro_column_catalog |
| C197 | volume_moneyflow_technical_divergence | P1 | technical_moneyflow_cross | stk_factor_pro + moneyflow / technical volume indicator columns plus moneyflow | standardized technical volume pressure minus standardized net moneyflow amount rate | needs_stk_factor_pro_column_catalog |
| C198 | block_trade_discount_intensity | P0 | block_trade | block_trade + daily / block trade price/amount plus daily close | amount_weighted_mean(block_trade.price / daily.close - 1) | source_verified_cache_empty_needs_backfill |
| C199 | block_trade_amount_ratio | P0 | block_trade | block_trade + daily / block trade amount plus daily amount | sum(block_trade.amount) / (daily.amount + eps) | source_verified_cache_empty_needs_backfill |
| C200 | block_trade_buyer_concentration | P1 | block_trade | block_trade / block trade buyer/amount fields | HHI of buyer-side amount shares by buyer name for each stock/date. | source_verified_cache_empty_needs_backfill |
| C201 | block_trade_institutional_net_bias | P1 | block_trade | block_trade / block trade buyer/seller text plus amount | (institution_like_buy_amount - institution_like_sell_amount) / total_block_amount | candidate_needs_text_rule_lock |
| C202 | unlock_pressure_30d | P0 | share_float_unlock | share_float + daily_basic / restricted share unlock schedule plus share base | sum(float_share with float_date in (T, T+30]) / current free_float_or_total_share | source_verified_needs_backfill |
| C203 | unlock_holder_concentration | P1 | share_float_unlock | share_float / restricted share unlock holder/float_share fields | HHI of upcoming 30-day unlock float_share by holder_name. | source_verified_needs_backfill |
| C204 | pledge_pressure_delta | P1 | pledge_risk | pledge_stat / pledge ratio/stat fields | pledge_ratio_T - previous_report_pledge_ratio | source_verified_needs_backfill_and_asof_lock |
| C205 | holdertrade_net_buy_ratio | P0 | holder_trade | stk_holdertrade + daily_basic / holder increase/decrease records plus share base | signed_sum(change_vol over last 20 trading days) / total_share_or_float_share | source_verified_cache_empty_needs_backfill |
| C206 | institution_research_heat_20d | P0 | institution_survey | stk_surv / institution survey/event records | rolling 20-day sum(log1p(fund_visitors)) or event_count. | source_verified_cache_exists_needs_coverage_check |
| C207 | research_org_diversity_20d | P1 | institution_survey | stk_surv / institution survey organization fields | nunique(rece_org or org_type) in trailing 20 calendar/trading days. | source_verified_cache_exists_needs_coverage_check |
| C208 | forecast_profit_revision_intensity | P0 | forecast_event | forecast_vip or forecast / profit forecast announcement fields | current midpoint(p_change_min,p_change_max) minus previous forecast midpoint for the same stock. | source_verified_partial_cache_needs_range_backfill |
| C209 | express_growth_acceleration | P1 | financial_event | express + sector membership / earnings express fields plus sector mapping | net_profit_yoy minus sector median net_profit_yoy, optionally first difference vs previous report. | source_verified_needs_backfill_and_asof_lock |
| C210 | hsgt_top10_net_buy_intensity | P0 | northbound_flow | hsgt_top10 + daily / northbound top10 stock flow plus daily amount | hsgt_top10.net_amount / (daily.amount + eps), sparse with availability flag. | source_verified_cache_exists_needs_coverage_check |
| C211 | ccass_hold_change_5d | P0 | foreign_holding | ccass_hold + daily_basic / CCASS shareholding and share base | (ccass_hold_share_T - ccass_hold_share_T-5) / total_share_or_float_share | source_verified_cache_exists_needs_coverage_check |
| C212 | hk_hold_ratio_change_5d | P1 | foreign_holding | hk_hold / HK hold ratio/share fields | hk_hold_ratio_T - hk_hold_ratio_T-5. | source_verified_cache_exists_needs_coverage_check |
| C213 | northbound_market_flow_regime | P1 | market_regime | moneyflow_hsgt / northbound/southbound aggregate flow | rolling zscore(north_money) plus 3-day acceleration, broadcast to all stocks. | source_verified_cache_exists_needs_coverage_check |
| C214 | industry_moneyflow_strength | P0 | industry_flow | moneyflow_ind_dc or moneyflow_ind_ths + membership / industry flow plus sector membership | industry net_amount_rate cross-sectional zscore mapped back to member stocks. | source_verified_partial_cache_needs_membership_join |
| C215 | stock_vs_industry_flow_divergence | P1 | industry_flow | moneyflow + moneyflow_ind_dc/ths + membership / stock moneyflow plus mapped industry moneyflow | stock net_mf zscore minus mapped industry net_amount_rate zscore. | source_verified_partial_cache_needs_membership_join |
| C216 | ths_hot_rank_change_3d | P1 | theme_heat | ths_hot / THS hot rank/value history | -delta(rank, 3d) plus hot value change. | source_verified_cache_exists_needs_duplicate_ablation |
| C217 | global_index_risk_dispersion | P1 | macro_cross_asset | index_global / global index daily returns | cross-sectional dispersion/std of prior-close returns across US/EU/Asia indices. | source_verified_cache_exists_needs_calendar_alignment |
| C218 | shibor_liquidity_slope | P1 | macro_liquidity | shibor / SHIBOR term structure | 1M Shibor minus overnight Shibor, plus 5-day delta. | source_verified_cache_exists_needs_release_time_lock |
| C219 | convertible_bond_risk_appetite | P2 | macro_cross_asset | cb_daily / convertible bond daily market data | market-wide average cb_daily pct_chg plus amount/volume zscore. | source_verified_needs_backfill |
| C220 | ggt_southbound_flow_regime | P2 | southbound_flow | ggt_daily / southbound daily buy/sell amount | (buy_amount - sell_amount) / (buy_amount + sell_amount + eps), rolling zscore. | source_verified_needs_backfill |
| C221 | limit_pool_block_trade_followthrough | P2 | cross_family_interaction | block_trade + limit_list_d / block-trade amount/discount plus limit-up history | I(recent limit-up) * block_trade_amount_ratio or block_trade_discount_intensity. | depends_on_block_trade_backfill |
| C222 | survey_to_forecast_confirmation | P2 | cross_event_interaction | stk_surv + forecast_vip / survey heat plus forecast revision | institution_research_heat_20d * positive forecast revision indicator. | depends_on_survey_and_forecast_backfill |

## Data Still Needed

| API | Priority | Needed By | Current Cache | Fetch Note |
|-----|----------|-----------|---------------|------------|
| stk_mins | P0 | C189, C190, C191, C192, C193 | missing: E:/.../tushare/stk_mins_1 | Pull all tradable A-shares in segmented batches, then verify per-stock bar coverage and bar_time alignment. |
| stk_factor_pro | P0 | C194, C195, C196, C197 | missing | Backfill and build a column catalog; remove raw OHLCV/adj duplicates and choose one adjusted family before training. |
| block_trade | P0 | C198, C199, C200, C201, C221 | directory exists but parquet count is 0 | Pull by trade_date; retain price, amount, buyer, seller, and join daily close/amount. |
| share_float | P0 | C202, C203 | missing | Retain ann_date, float_date, holder_name, float_share; enforce ann_date <= prediction date. |
| stk_holdertrade | P0 | C205 | directory exists but parquet count is 0 | Retain ann_date, in_de, holder_name, change_vol; compute signed holder trade flow. |
| pledge_stat | P1 | C204 | missing | Backfill and lock publication/asof rule before training. |
| express | P1 | C209 | missing | Retain ann_date and end_date; lag if same-day timestamp is unavailable. |
| forecast_vip/forecast | P1 | C208, C222 | partial | Range pull works; backfill by date range and keep forecast revision lineage per stock. |
| moneyflow_ind_dc/moneyflow_ind_ths | P1 | C214, C215 | partial | Backfill industry flow and verify membership mapping via dc_member/ths_member. |
| ggt_daily | P2 | C220 | missing | Secondary cross-market flow; pull after P0/P1 sources. |
| cb_daily | P2 | C219 | missing | Secondary cross-asset risk appetite; pull after P0/P1 sources. |

## First Fetch Priority

1. `stk_mins` 1min: unlocks C189-C193 and fills the true 1min gap.
2. `stk_factor_pro`: unlocks the technical indicator bank C194-C197 after a strict column catalog.
3. `block_trade`, `share_float`, `stk_holdertrade`: high-priority non-minute sources with direct P0 candidates.
4. `forecast_vip/forecast`, `express`, `pledge_stat`, industry moneyflow membership joins: P1 event/flow expansion.
5. `ggt_daily`, `cb_daily`: lower-priority cross-market/cross-asset expansion.

## Guardrails

- Do not mark any new factor as passed/final/frozen before training.
- Do not feed C194-C197 directly until `stk_factor_pro` columns are cataloged and raw OHLCV/adjustment duplicates are removed.
- Do not feed C204/C208/C209 without conservative `ann_date`/publication-time asof handling.
- Do not feed C221/C222 before their dependency factors are engineered.
