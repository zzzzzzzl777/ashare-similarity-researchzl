# Web Saturation Short-Line Factor Search 2026-05-18

Scope: factor-library only. No training, no gpu_probe, no model or frozen config changes.

## Expanded Search Surface

- Broker high-frequency volume peak/ridge/valley and volume-distribution reports
- Fangzheng smart-money minute-bar research and Benford/leading-digit idea
- Minute price-volume correlation slice family (HCVP/LCVP style)
- Realized jump / bipower variation and bar-level VPIN proxy literature
- Tushare/API feasibility pass for HSGT, CCASS, industry flow, stk_factor_pro
- Local raw pool cross-check against 3,075 prior raw candidates

## Source Evidence

- `kaiyuan_volume_peak_ridge_valley`: https://www.fhyanbao.com/rpview/1679996
- `fangzheng_smart_money`: https://bigquant.com/wiki/doc/4OvIDMRuTH
- `xingye_volume_distribution_alpha`: https://bigquant.com/wiki/doc/8bghnLBtpA
- `kaiyuan_single_trade_amount`: https://bigquant.com/square/paper/74353d24-a9cf-4d17-a9fb-c431ece0a52e
- `chinese_hf_liquidity_ssrn`: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4191675
- `china_limit_order_book_volatility`: https://www.sciencedirect.com/science/article/pii/S0927538X14000183
- `price_limit_prehit_dynamics`: https://arxiv.org/abs/1503.03548
- `tushare_stk_factor`: https://www.tushare.pro/document/2?doc_id=296

## Added To Registry

- Batch: `candidates_20260518_web_saturation2`
- Count: 22
- ID range: `C371-C392`
- Priority counts: {'P0': 6, 'P1': 14, 'P2': 2}
- Family counts: {'minute_hf': 3, 'minute_smart_money': 2, 'minute_volume_shape': 1, 'minute_volume_peak': 4, 'minute_price_jump': 3, 'minute_amount_shape': 2, 'minute_realized_jump': 1, 'minute_orderflow_proxy': 1, 'northbound_flow': 2, 'industry_crowding': 1, 'technical_indicator_bank': 2}

| ID | Name | Priority | Family | Data Need | Engineering | Asof |
|---|---|---|---|---|---|---|
| C371 | hcvp_price_volume_corr | P0 | minute_hf | 1min bars: close, volume/amount; optional trailing N-day smoothing | engineerable_after_1min_cache | For 14:57 live use only bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C372 | lcvp_price_volume_corr | P1 | minute_hf | 1min bars: close, volume/amount; optional trailing N-day smoothing | engineerable_after_1min_cache | For 14:57 live use only bars with bar_time <= 14:57; for post-close research use T+1 full-day bars. |
| C373 | hcvp_lcvp_corr_spread | P0 | minute_hf | Derived from C371/C372 once 1min bars are available | engineerable_after_1min_cache | Same cutoff rule as C371/C372. |
| C374 | intraday_smart_money_q_return | P0 | minute_smart_money | 1min bars: close, amount or volume | engineerable_after_1min_cache | For 14:57 live compute only from minutes <= 14:57; post-close full-day version must be separate. |
| C375 | intraday_smart_money_q_volume_share | P1 | minute_smart_money | 1min bars: close, amount or volume | engineerable_after_1min_cache | For 14:57 live compute only from minutes <= 14:57. |
| C376 | minute_volume_benford_deviation | P1 | minute_volume_shape | 1min bars: volume | engineerable_after_1min_cache | For 14:57 live use only minute bars <= 14:57; full-day post-close is a separate feature. |
| C377 | volume_peak_return_contribution | P0 | minute_volume_peak | 1min bars: close, volume/amount | engineerable_after_1min_cache | Local peaks must be identified only with already observed neighbor bars; for live 14:57 do not use future bars. |
| C378 | volume_ridge_persistence_share | P1 | minute_volume_peak | 1min bars: volume/amount | engineerable_after_1min_cache | For 14:57 live use only bars <= 14:57. |
| C379 | volume_valley_reversal_strength | P1 | minute_volume_peak | 1min bars: close, volume/amount | engineerable_after_1min_cache | At 14:57 only compute future-after-valley returns when the future bars are already observed. |
| C380 | volume_peak_valley_price_spread | P1 | minute_volume_peak | 1min bars: close or vwap, volume/amount | engineerable_after_1min_cache | For 14:57 live use only peak/valley minutes observed by cutoff. |
| C381 | price_jump_peak_density | P0 | minute_price_jump | 1min bars: close | engineerable_after_1min_cache | For 14:57 live use only returns whose end time <= 14:57. |
| C382 | price_jump_ridge_followthrough | P1 | minute_price_jump | 1min bars: close | engineerable_after_1min_cache | For 14:57 live use only minute returns observed by cutoff. |
| C383 | price_jump_valley_reversal | P1 | minute_price_jump | 1min bars: close | engineerable_after_1min_cache | At 14:57 only compute next_5min_return if all bars are already observed. |
| C384 | minute_amount_autocorr_1 | P1 | minute_amount_shape | 1min bars: amount | engineerable_after_1min_cache | For 14:57 live use only amount bars <= 14:57. |
| C385 | minute_amount_tail_kurtosis | P1 | minute_amount_shape | 1min bars: amount | engineerable_after_1min_cache | For 14:57 live use only amount bars <= 14:57. |
| C386 | minute_bipower_jump_ratio | P0 | minute_realized_jump | 1min bars: close | engineerable_after_1min_cache | For 14:57 live use only returns whose end time <= 14:57. |
| C387 | bar_vpin_proxy_1min | P1 | minute_orderflow_proxy | 1min bars: close, volume; true L2 buy/sell labels optional but not required for this proxy | engineerable_after_1min_cache | For 14:57 live use only bars <= 14:57 and past buckets. |
| C388 | hsgt_top10_member_churn | P1 | northbound_flow | hsgt_top10 historical stock list | engineerable_after_hsgt_top10_backfill | Use T-1 published top10 list for live 14:57 unless same-day timestamp proves availability before cutoff. |
| C389 | ccass_holder_concentration_delta | P1 | northbound_flow | ccass_hold participant-level holdings if available; otherwise stock-level ccass only is insufficient | engineerable_if_ccass_participant_fields_available | Use latest record with publication date <= T-1 for 14:57 live. |
| C390 | industry_turnover_crowding_score | P1 | industry_crowding | industry constituents, daily turnover/amount, moneyflow_ind_ths or comparable industry flow | engineerable_after_industry_flow_backfill | For live 14:57 use T-1 industry flow/turnover unless same-day source timestamp is proven before cutoff. |
| C391 | technical_signal_consensus_261 | P2 | technical_indicator_bank | stk_factor_pro indicator bank plus curated column orientation map | engineerable_after_stk_factor_pro_catalog | Use T-1 vendor indicators for live unless same-day indicators are locally recomputed before 14:57. |
| C392 | technical_signal_disagreement_entropy | P2 | technical_indicator_bank | stk_factor_pro indicator bank plus curated orientation map | engineerable_after_stk_factor_pro_catalog | Use T-1 vendor indicators for live unless same-day indicators are locally recomputed before 14:57. |

## Deferred / Not Registered

- `true L2 limit-order-book slope/depth/cancel factors`: Not registered unless stable L2/tick/orderbook fields exist. Minute-bar proxy VPIN is registered separately as proxy only.
- `single-trade amount QUA/MTS/MTE/SR exact factors`: Exact construction needs per-trade count/size series; only minute-bar amount proxies are registered here.
- `bulk Alpha101/Alpha191 libraries`: Need formula-by-formula translation, dedup and asof review; not bulk-imported.
- `pure social-media text rules`: Not registered unless converted to timestamped stock-level numeric series.

## Ten Validation Checks

1. JSON loads: PASS
2. C IDs are continuous: PASS
3. No duplicate factor_id: PASS
4. No duplicate factor name: PASS
5. meta registry count matches actual C objects: PASS
6. New batch exists and count matches detail length: PASS
7. All new entries have required fields: PASS
8. All new entries are training_status=not_trained: PASS
9. All new entries are lockbox_role=research_candidate: PASS
10. No new entry claims is_passed/is_final_unseen/is_frozen_modified: PASS
