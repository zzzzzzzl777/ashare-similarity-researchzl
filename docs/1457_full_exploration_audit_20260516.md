# 14:57 Full Exploration Audit 20260516

## Scope

This is the executable Phase 0-2 gate for the next all-round search:

- evidence freeze across docs, scripts, reports, feature caches, bundles and recent runs;
- raw cache/source coverage audit, especially `stk_mins_1` and `stk_mins_5`;
- C001-C292 factor asof reclassification for strict 14:57 champion eligibility;
- execution gate before true 14:57-asof cache/training.

## Current Gate

- `allow_true_1457_cache_build`: `False`
- `allow_champion_training`: `False`
- `allow_family_screen_research_only`: `True`

### P0

- Full-market stk_mins_1 cache is incomplete; true 14:57-asof champion training is blocked.
- Latest feature caches look like generic gpu_probe caches; no true 14:57-asof schema was found.
- 36 registry factors are 1min-derived A_pending_data and cannot enter champion training yet.
- 2 factors are currently C/forbidden until rewritten or removed.

### P1

- Known S2/PhaseC/pre_new_A bundles all require asof rebuild/proxy cleanup; keep them as references, not direct champions.
- 25 discovered cache sources are unclassified (adj_factor,cb_daily,ccass_hold,express_vip,forecast_vip,ggt_daily,hk_hold,hsgt_top10); assign asof/source gates before using related factors.
- suspend_d is empty_or_not_backfilled; related factors must stay pending/proxy-only.
- ggt_top10 is empty_or_not_backfilled; related factors must stay pending/proxy-only.
- index_weight is empty_or_not_backfilled; related factors must stay pending/proxy-only.
- ths_member is sparse; related factors must stay pending/proxy-only.
- 95 factors look engineerable but require explicit 14:57-asof rewrite/golden replay before champion use.
- 52 factors have insufficient evidence and are suspended from champion candidates.

## Key Cache Summary

| source         |   file_count |   nested_parquet_count | market_counts            | completeness_status                  | gate_severity   | sampled_has_1457   | note                                                                                               |
|:---------------|-------------:|-----------------------:|:-------------------------|:-------------------------------------|:----------------|:-------------------|:---------------------------------------------------------------------------------------------------|
| stk_mins_1     |          230 |                    230 | {"SZ": 230}              | incomplete_blocks_true_1457_training | P0              | YES                | 1min per-symbol cache is far below full A-share coverage; true 14:57 champion training is blocked. |
| stk_mins_5     |         3195 |                  23344 | {"SH": 1703, "SZ": 1492} | available                            | OK              | NO                 | 5min cache appears broad; exact 14:57 reconstruction still requires 1min for true cutoff.          |
| raw_bars_daily |         5327 |                   5327 | {}                       | available                            | OK              | NO                 | Raw daily bars are available outside tushare cache and should satisfy daily OHLCV needs.           |
| daily_basic    |         2267 |                   2267 | {}                       | available                            | OK              | NO                 | Layout=per_date; sampled 8 files.                                                                  |
| stk_factor_pro |         2234 |                   2234 | {}                       | available                            | OK              | NO                 | Layout=per_date; sampled 8 files.                                                                  |
| cyq_perf       |         3198 |                   3198 | {"SH": 1704, "SZ": 1492} | available                            | OK              | NO                 | Layout=per_symbol; sampled 8 files.                                                                |
| moneyflow      |         2267 |                   2267 | {}                       | available                            | OK              | NO                 | Layout=per_date; sampled 8 files.                                                                  |

## Minute Coverage Sample

| source     |   sampled_symbols | markets   |   min_unique_dates |   max_unique_dates |   symbols_with_1457 |   min_1457_dates |   max_1457_dates |   symbols_with_1455 |   min_1455_dates |   max_1455_dates |
|:-----------|------------------:|:----------|-------------------:|-------------------:|--------------------:|-----------------:|-----------------:|--------------------:|-----------------:|-----------------:|
| stk_mins_1 |                24 | SZ        |               2033 |               2271 |                  24 |             2033 |             2271 |                  24 |             2033 |             2271 |
| stk_mins_5 |                30 | SH,SZ     |               1096 |               2269 |                   0 |                0 |                0 |                  30 |             1096 |             2269 |

## Latest Feature Cache Schema Sample

| name                                        |   rows |   columns | date_min   | date_max   | likely_asof_1457   | schema_note                                    |
|:--------------------------------------------|-------:|----------:|:-----------|:-----------|:-------------------|:-----------------------------------------------|
| gpu_probe_features_10c11fc874db003c.parquet | 405359 |       847 | 2023-02-14 | 2026-05-08 | False              | generic_gpu_probe_cache_probably_not_true_1457 |
| gpu_probe_features_550a77f54882058f.parquet | 877895 |       847 | 2017-02-14 | 2026-04-29 | False              | generic_gpu_probe_cache_probably_not_true_1457 |
| gpu_probe_features_379c33555f8021bf.parquet | 877895 |       847 | 2017-02-14 | 2026-04-29 | False              | generic_gpu_probe_cache_probably_not_true_1457 |
| gpu_probe_features_d64264f1a06e1a7f.parquet |    144 |       847 | 2026-03-17 | 2026-04-29 | False              | generic_gpu_probe_cache_probably_not_true_1457 |
| gpu_probe_features_a4f4a4f77f5c19f3.parquet | 877895 |       847 | 2017-02-14 | 2026-04-29 | False              | generic_gpu_probe_cache_probably_not_true_1457 |
| gpu_probe_features_3b6ec119913aa465.parquet | 323741 |       817 | 2023-06-08 | 2025-12-30 | False              | generic_gpu_probe_cache_probably_not_true_1457 |
| gpu_probe_features_ce423b75344264dd.parquet | 230913 |       817 | 2023-06-08 | 2025-06-27 | False              | generic_gpu_probe_cache_probably_not_true_1457 |
| gpu_probe_features_ff543b0184aac1df.parquet | 161125 |       817 | 2023-06-08 | 2024-12-30 | False              | generic_gpu_probe_cache_probably_not_true_1457 |
| jan_2023_patched.parquet                    |   5133 |       817 | 2023-01-03 | 2023-01-31 | False              | generic_gpu_probe_cache_probably_not_true_1457 |
| pretrain_2023_02_04_patched.parquet         |  20625 |       817 | 2023-02-01 | 2023-04-27 | False              | generic_gpu_probe_cache_probably_not_true_1457 |

## Source Temporal Summary

| source               | layout           |   sample_units | first_month   | last_month   |   months_present |   missing_months_count | has_2017_01   | has_2026_04   | note                                |
|:---------------------|:-----------------|---------------:|:--------------|:-------------|-----------------:|-----------------------:|:--------------|:--------------|:------------------------------------|
| stk_mins_1           | per_symbol       |             24 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | sampled_per_symbol_file_months      |
| stk_mins_5           | per_symbol       |             24 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | sampled_per_symbol_file_months      |
| raw_bars_daily       | per_symbol       |             24 | 1991-01       | 2026-05      |              425 |                      0 | True          | True          | sampled_per_symbol_file_months      |
| daily_basic          | per_date         |           2267 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| stk_factor_pro       | per_date         |           2234 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| cyq_perf             | per_symbol       |             24 | 2018-01       | 2026-05      |              101 |                      0 | False         | True          | sampled_per_symbol_file_months      |
| moneyflow            | per_date         |           2267 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| limit_list_d         | per_date         |           1537 | 2020-01       | 2026-05      |               77 |                      0 | False         | True          | filename_months_from_per_date_files |
| top_list             | per_date         |           2268 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| top_inst             | per_date         |           2268 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| block_trade          | per_date         |           2271 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| pledge_stat_perstock | per_symbol       |             24 | 2014-03       | 2026-05      |              147 |                      0 | True          | True          | sampled_per_symbol_file_months      |
| stk_holdertrade      | per_date         |           2240 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| suspend_d            | empty            |              0 |               |              |                0 |                      0 | False         | False         | not_temporally_sampled              |
| ths_member           | mixed_or_unknown |              0 |               |              |                0 |                      0 | False         | False         | not_temporally_sampled              |
| ggt_top10            | empty            |              0 |               |              |                0 |                      0 | False         | False         | not_temporally_sampled              |
| index_weight         | empty            |              0 |               |              |                0 |                      0 | False         | False         | not_temporally_sampled              |
| adj_factor           | per_date         |           2271 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| cb_daily             | per_date         |           2271 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| ccass_hold           | per_date         |           1287 | 2020-11       | 2026-05      |               67 |                      0 | False         | True          | filename_months_from_per_date_files |
| express_vip          | per_date         |           1030 | 2017-01       | 2026-05      |               75 |                     38 | True          | True          | filename_months_from_per_date_files |
| forecast_vip         | per_date         |           1968 | 2017-01       | 2026-04      |              112 |                      0 | True          | True          | filename_months_from_per_date_files |
| ggt_daily            | per_date         |           2134 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| hk_hold              | per_date         |           2197 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| hsgt_top10           | per_date         |           2169 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| index_dailybasic     | per_date         |           2268 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| index_global         | per_date         |           2268 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| margin               | per_date         |           2267 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| margin_detail        | per_date         |           2267 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |
| moneyflow_hsgt       | per_date         |           2198 | 2017-01       | 2026-05      |              113 |                      0 | True          | True          | filename_months_from_per_date_files |

## Source Asof Policy

| source               |   file_count | source_policy_class     | formal_1457_use                                                                               | cutoff_rule                                                                 | risk                                                         |
|:---------------------|-------------:|:------------------------|:----------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------|:-------------------------------------------------------------|
| stk_surv             |         1083 | A_calendar_filter       | Use as listing/delisting survival filter, not as a raw alpha factor unless justified.         | status known by decision time; no future delist backfill in historical rows | survivorship-bias leakage                                    |
| raw_bars_daily       |         5327 | A_history_Tminus1       | Use for historical lookback, T-1 finalized features and labels; not T-day live close.         | T-day full daily OHLCV forbidden for formal 14:57 features                  | full-day T field would recreate the old close-proxy mistake  |
| stk_mins_1           |          230 | A_pending_data          | Primary T-day 14:57 snapshot source for formal model.                                         | use bars <=14:57 only; never consume later 1min bars                        | partial breadth blocks champion training                     |
| stk_auction_c        |         2268 | A_preopen               | Can enter formal model if auction fields are known after 09:25 and stable by 14:57.           | auction snapshot only; no post-close auction-like aggregates                | vendor field may be revised or aggregated after close        |
| stk_auction_o        |         2267 | A_preopen               | Can enter formal model if auction fields are known after 09:25 and stable by 14:57.           | auction snapshot only; no post-close auction-like aggregates                | vendor field may be revised or aggregated after close        |
| limit_list_d         |         1537 | A_rewrite_required      | Can be valuable only if reconstructed as limit-pool state visible by 14:57.                   | historical full-day limit list must be truncated to events <=14:57          | full-day pool includes late limit events after decision time |
| stk_limit            |         2268 | A_rewrite_required      | Can be valuable only if reconstructed as limit-pool state visible by 14:57.                   | historical full-day limit list must be truncated to events <=14:57          | full-day pool includes late limit events after decision time |
| stk_mins_5           |         3195 | A_rewrite_required      | Use mature 5min history only with safe cutoff; combine with 1min for exact 14:57.             | last fully safe 5min bar is 14:55; never use 15:00 bar                      | 15:00 5min bar leaks 14:56-15:00                             |
| adj_factor           |         2271 | B_Tminus1               | Use latest data available before 14:57, normally T-1.                                         | shift to T-1 unless vendor provides documented intraday asof timestamp      | same-day per-date fields are often settled after close       |
| daily_basic          |         2267 | B_Tminus1               | Use latest data available before 14:57, normally T-1.                                         | shift to T-1 unless vendor provides documented intraday asof timestamp      | same-day per-date fields are often settled after close       |
| share_float          |         2199 | B_Tminus1               | Use as lagged float-share context or to normalize turnover/impact.                            | latest known float share before 14:57; normally T-1 or announcement-asof    | backfilled share changes can leak corporate-action timing    |
| stk_factor_pro       |         2234 | B_Tminus1               | Use latest data available before 14:57, normally T-1.                                         | shift to T-1 unless vendor provides documented intraday asof timestamp      | same-day per-date fields are often settled after close       |
| shibor               |         2267 | B_Tminus1_macro         | Use as lagged macro/liquidity context only.                                                   | T-1 or latest published timestamp before 14:57                              | publication lag and calendar mismatch                        |
| cyq_perf             |         3198 | B_Tminus1_or_proxy      | Use T-1 version or explicitly named live proxy family only.                                   | no same-name overwrite between delayed Tushare fields and live proxy fields | proxy drift and delayed-source leakage                       |
| margin               |         2267 | B_Tminus1_or_proxy      | Use T-1 version or explicitly named live proxy family only.                                   | no same-name overwrite between delayed Tushare fields and live proxy fields | proxy drift and delayed-source leakage                       |
| margin_detail        |         2267 | B_Tminus1_or_proxy      | Use T-1 version or explicitly named live proxy family only.                                   | no same-name overwrite between delayed Tushare fields and live proxy fields | proxy drift and delayed-source leakage                       |
| moneyflow            |         2267 | B_Tminus1_or_proxy      | Use T-1 version or explicitly named live proxy family only.                                   | no same-name overwrite between delayed Tushare fields and live proxy fields | proxy drift and delayed-source leakage                       |
| moneyflow_hsgt       |         2198 | B_Tminus1_or_proxy      | Use T-1 version or explicitly named live proxy family only.                                   | no same-name overwrite between delayed Tushare fields and live proxy fields | proxy drift and delayed-source leakage                       |
| moneyflow_ind_dc     |          643 | B_Tminus1_or_proxy      | Use T-1 version or explicitly named live proxy family only.                                   | no same-name overwrite between delayed Tushare fields and live proxy fields | proxy drift and delayed-source leakage                       |
| moneyflow_ind_ths    |          400 | B_Tminus1_or_proxy      | Use T-1 version or explicitly named live proxy family only.                                   | no same-name overwrite between delayed Tushare fields and live proxy fields | proxy drift and delayed-source leakage                       |
| express_vip          |         1030 | B_announcement_asof     | Use only records announced before the decision timestamp; otherwise T-1/history.              | announcement_time <= 14:57 with trading-day alignment                       | future announcement leakage                                  |
| forecast_vip         |         1968 | B_announcement_asof     | Use only records announced before the decision timestamp; otherwise T-1/history.              | announcement_time <= 14:57 with trading-day alignment                       | future announcement leakage                                  |
| pledge_stat          |           13 | B_announcement_asof     | Use only records announced before the decision timestamp; otherwise T-1/history.              | announcement_time <= 14:57 with trading-day alignment                       | future announcement leakage                                  |
| pledge_stat_perstock |         2805 | B_announcement_asof     | Use only records announced before the decision timestamp; otherwise T-1/history.              | announcement_time <= 14:57 with trading-day alignment                       | future announcement leakage                                  |
| stk_holdernumber     |         2268 | B_announcement_asof     | Use only records announced before the decision timestamp; otherwise T-1/history.              | announcement_time <= 14:57 with trading-day alignment                       | future announcement leakage                                  |
| stk_holdertrade      |         2240 | B_announcement_asof     | Use only records announced before the decision timestamp; otherwise T-1/history.              | announcement_time <= 14:57 with trading-day alignment                       | future announcement leakage                                  |
| ccass_hold           |         1287 | B_delayed_cross_market  | Use as lagged cross-market/holding context, not same-day live signal by default.              | T-1 or documented intraday timestamp only                                   | settlement/publication lag                                   |
| ggt_daily            |         2134 | B_delayed_cross_market  | Use as lagged cross-market/holding context, not same-day live signal by default.              | T-1 or documented intraday timestamp only                                   | settlement/publication lag                                   |
| hk_hold              |         2197 | B_delayed_cross_market  | Use as lagged cross-market/holding context, not same-day live signal by default.              | T-1 or documented intraday timestamp only                                   | settlement/publication lag                                   |
| hsgt_top10           |         2169 | B_delayed_cross_market  | Use as lagged cross-market/holding context, not same-day live signal by default.              | T-1 or documented intraday timestamp only                                   | settlement/publication lag                                   |
| block_trade          |         2271 | B_delayed_event         | Research/T-1 event features only unless announcement timestamp proves pre-14:57 availability. | asof announcement timestamp <=14:57, otherwise T-1                          | after-close publication leakage                              |
| top_inst             |         2268 | B_delayed_event         | Research/T-1 event features only unless announcement timestamp proves pre-14:57 availability. | asof announcement timestamp <=14:57, otherwise T-1                          | after-close publication leakage                              |
| top_list             |         2268 | B_delayed_event         | Research/T-1 event features only unless announcement timestamp proves pre-14:57 availability. | asof announcement timestamp <=14:57, otherwise T-1                          | after-close publication leakage                              |
| index_dailybasic     |         2268 | B_or_A_rewrite_required | Use T-1 official daily values, or rebuild live sector/index state from an intraday source.    | same-day full daily values forbidden unless intraday feed exists            | market/sector context drift between train and live           |
| index_global         |         2268 | B_or_A_rewrite_required | Use T-1 official daily values, or rebuild live sector/index state from an intraday source.    | same-day full daily values forbidden unless intraday feed exists            | market/sector context drift between train and live           |
| ths_daily            |         2268 | B_or_A_rewrite_required | Use T-1 official daily values, or rebuild live sector/index state from an intraday source.    | same-day full daily values forbidden unless intraday feed exists            | market/sector context drift between train and live           |
| ths_hot              |          656 | B_or_A_rewrite_required | Use T-1 official daily values, or rebuild live sector/index state from an intraday source.    | same-day full daily values forbidden unless intraday feed exists            | market/sector context drift between train and live           |
| ths_member           |            1 | B_or_A_rewrite_required | Use T-1 official daily values, or rebuild live sector/index state from an intraday source.    | same-day full daily values forbidden unless intraday feed exists            | market/sector context drift between train and live           |
| ggt_top10            |            0 | D_pending_source        | Do not use in champion factors until backfilled or replaced.                                  | none                                                                        | missing source can create silent sparse/zero-fill artifacts  |
| index_weight         |            0 | D_pending_source        | Do not use in champion factors until backfilled or replaced.                                  | none                                                                        | missing source can create silent sparse/zero-fill artifacts  |
| suspend_d            |            0 | D_pending_source        | Do not use in champion factors until backfilled or replaced.                                  | none                                                                        | missing source can create silent sparse/zero-fill artifacts  |
| cb_daily             |         2271 | D_unclassified          | Do not use in champion route until owner and asof semantics are documented.                   | none                                                                        | unknown timing semantics                                     |

## Factor Asof Class Counts

{
  "A_rewrite_required": 95,
  "B": 77,
  "D": 52,
  "A_pending_data": 36,
  "A": 30,
  "C": 2
}

## Known Bundle Selected Feature Gate

| bundle_id                  |   selected_count |   asof_rewrite_required |   proxy_required |   blocked |   orphan_available_flag |   unknown | champion_eligible_now   | recommended_role                            |
|:---------------------------|-----------------:|------------------------:|-----------------:|----------:|------------------------:|----------:|:------------------------|:--------------------------------------------|
| baseline_s2                |              260 |                     251 |                2 |         0 |                       1 |         0 | False                   | rehabilitation_candidate_retrain_required   |
| baseline_phasec            |              200 |                     194 |                0 |         0 |                       2 |         0 | False                   | legacy_score_only_baseline_rebuild_required |
| pre_new_A_freeze_candidate |              260 |                     248 |                4 |         0 |                       1 |         0 | False                   | research_freeze_candidate_rebuild_required  |

## S2 Increment vs PhaseC

| scope                      |   feature_count |   asof_rewrite_required |   proxy_required |   orphan_available_flag |   strict_ok |   unknown | recommendation                           |
|:---------------------------|----------------:|------------------------:|-----------------:|------------------------:|------------:|----------:|:-----------------------------------------|
| s2_selected_only_vs_phasec |              60 |                      57 |                2 |                       0 |           0 |         0 | split_rewrite_vs_proxy_then_full_rolling |
| phasec_selected_only_vs_s2 |               0 |                       0 |                0 |                       0 |           0 |         0 | empty_by_design                          |

## Bundle Family Gate

| bundle_id                  | family                  |   selected_count |   asof_rewrite_required |   proxy_required |   orphan_available_flag | recommended_action                |
|:---------------------------|:------------------------|-----------------:|------------------------:|-----------------:|------------------------:|:----------------------------------|
| baseline_phasec            | available_flag          |                5 |                       0 |                0 |                       2 | remove_or_pair_available_flags    |
| baseline_phasec            | market_emotion          |               53 |                      53 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | symbol_ohlcv_return     |               31 |                      31 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | cross_section           |               23 |                      23 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | symbol_ohlcv_volume     |               22 |                      22 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | symbol_ohlcv_pattern    |               19 |                      19 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | board_structure         |                8 |                       8 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | symbol_ohlcv_momentum   |                7 |                       7 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | symbol_ohlcv_price      |                7 |                       7 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | symbol_ohlcv_range      |                7 |                       7 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | symbol_ohlcv_moving_avg |                6 |                       6 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | factor_value            |                5 |                       5 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | tushare_auction         |                3 |                       3 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | tushare_misc            |                2 |                       2 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | tushare_limit_stats     |                1 |                       1 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_phasec            | tushare_daily_basic     |                1 |                       0 |                0 |                       0 | strict_or_reference_ok            |
| baseline_s2                | tushare_cyq             |                2 |                       0 |                2 |                       0 | delete_vs_t1_or_new_proxy_retrain |
| baseline_s2                | available_flag          |                6 |                       0 |                0 |                       1 | remove_or_pair_available_flags    |
| baseline_s2                | market_emotion          |               61 |                      61 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | symbol_ohlcv_return     |               42 |                      42 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | symbol_ohlcv_volume     |               29 |                      29 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | cross_section           |               28 |                      28 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | symbol_ohlcv_pattern    |               28 |                      28 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | board_structure         |               12 |                      12 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | symbol_ohlcv_price      |               11 |                      11 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | symbol_ohlcv_momentum   |               10 |                      10 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | symbol_ohlcv_moving_avg |                7 |                       7 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | symbol_ohlcv_range      |                7 |                       7 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | factor_value            |                5 |                       5 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | ths_sector              |                4 |                       4 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | tushare_auction         |                3 |                       3 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | tushare_limit_stats     |                2 |                       2 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | tushare_misc            |                2 |                       2 |                0 |                       0 | rewrite_family_to_true_1457_asof  |
| baseline_s2                | tushare_daily_basic     |                1 |                       0 |                0 |                       0 | strict_or_reference_ok            |
| pre_new_A_freeze_candidate | tushare_moneyflow       |                2 |                       0 |                2 |                       0 | delete_vs_t1_or_new_proxy_retrain |

## Factor Family Priority Summary

| family                     |   total |   a |   a_rewrite_required |   a_pending_data |   b |   c |   d |   first_wave_candidates | recommended_action                    |
|:---------------------------|--------:|----:|---------------------:|-----------------:|----:|----:|----:|------------------------:|:--------------------------------------|
| limit_intraday             |      10 |   0 |                    0 |                9 |   0 |   0 |   1 |                       8 | wait_1min_backfill_then_screen        |
| intraday_microstructure    |       4 |   0 |                    0 |                4 |   0 |   0 |   0 |                       4 | wait_1min_backfill_then_screen        |
| formulaic_alpha            |       4 |   0 |                    0 |                4 |   0 |   0 |   0 |                       2 | wait_1min_backfill_then_screen        |
| intraday_open              |       2 |   0 |                    0 |                2 |   0 |   0 |   0 |                       2 | wait_1min_backfill_then_screen        |
| lhb                        |       4 |   0 |                    0 |                0 |   4 |   0 |   0 |                       2 | delete_vs_t1_or_proxy_pair            |
| limit_theme                |       6 |   0 |                    0 |                2 |   0 |   0 |   4 |                       1 | wait_1min_backfill_then_screen        |
| auction_intraday           |       1 |   0 |                    0 |                1 |   0 |   0 |   0 |                       1 | wait_1min_backfill_then_screen        |
| limit_pool_intraday        |       1 |   0 |                    0 |                1 |   0 |   0 |   0 |                       1 | wait_1min_backfill_then_screen        |
| intraday_cost              |       4 |   0 |                    0 |                4 |   0 |   0 |   0 |                       0 | wait_1min_backfill_then_screen        |
| intraday_liquidity         |       4 |   0 |                    0 |                4 |   0 |   0 |   0 |                       0 | wait_1min_backfill_then_screen        |
| intraday_pattern           |       2 |   0 |                    0 |                2 |   0 |   0 |   0 |                       0 | wait_1min_backfill_then_screen        |
| auction_limit_theme        |       1 |   0 |                    0 |                1 |   0 |   0 |   0 |                       0 | wait_1min_backfill_then_screen        |
| intraday_relative_strength |       1 |   0 |                    0 |                1 |   0 |   0 |   0 |                       0 | wait_1min_backfill_then_screen        |
| intraday_volume            |       1 |   0 |                    0 |                1 |   0 |   0 |   0 |                       0 | wait_1min_backfill_then_screen        |
| intraday_structure         |      21 |   2 |                   17 |                0 |   2 |   0 |   0 |                       0 | rewrite_to_true_1457_asof_then_screen |
| volume_structure           |       8 |   0 |                    8 |                0 |   0 |   0 |   0 |                       0 | rewrite_to_true_1457_asof_then_screen |
| board_structure            |       8 |   0 |                    6 |                0 |   0 |   0 |   2 |                       0 | rewrite_to_true_1457_asof_then_screen |
| limit_list                 |       6 |   0 |                    6 |                0 |   0 |   0 |   0 |                       0 | rewrite_to_true_1457_asof_then_screen |
| intraday_5m                |       7 |   3 |                    4 |                0 |   0 |   0 |   0 |                       0 | rewrite_to_true_1457_asof_then_screen |
| stk_limit_derivative       |       7 |   3 |                    4 |                0 |   0 |   0 |   0 |                       0 | rewrite_to_true_1457_asof_then_screen |
| price_structure            |       5 |   0 |                    4 |                0 |   1 |   0 |   0 |                       0 | rewrite_to_true_1457_asof_then_screen |
| auction                    |       5 |   2 |                    3 |                0 |   0 |   0 |   0 |                       0 | rewrite_to_true_1457_asof_then_screen |
| risk_filter                |       5 |   0 |                    3 |                0 |   1 |   0 |   1 |                       0 | rewrite_to_true_1457_asof_then_screen |
| sentiment                  |       5 |   0 |                    3 |                0 |   0 |   0 |   2 |                       0 | rewrite_to_true_1457_asof_then_screen |
| auction_confirm            |       3 |   0 |                    3 |                0 |   0 |   0 |   0 |                       0 | rewrite_to_true_1457_asof_then_screen |

## Deep Interpretation

- `stk_mins_1` is conceptually usable for true 14:57 training: every sampled 1min symbol has 14:57 bars.
  The blocker is breadth, not timestamp availability. Current root coverage is `230` files
  (7.7% of the broad 3000-file minimum gate), markets=`{"SZ": 230}`.
- `stk_mins_5` is broad at root level, but 5min bars do not contain an exact 14:57 close. The last fully
  safe 5min bar is 14:55; using the 15:00 bar would leak 14:56-15:00 information into a 14:57 model.
- Existing latest feature caches are generic `gpu_probe_features_*` schemas and are not named or audited
  as true 14:57-asof caches. They cannot be used to certify a champion route.
- Daily OHLCV is not missing: it is present under raw bars, outside the tushare cache directory.
- The factor classification is intentionally conservative in two directions:
  hard C is kept tiny to avoid wasting engineerable factors, while `A_rewrite_required` is kept out of
  champion training until its 14:57 rewrite and golden replay are proven.
- S2, PhaseC, and pre_new_A bundles all remain useful references, but their selected features are not
  currently champion-eligible as-is because they rely on old close/proxy schemas and/or delayed-source
  families. Their value is in the feature ideas and baselines, not direct freeze.
- S2's incremental value over PhaseC is not invalidated: the S2-only selected set should be split into
  rewrite candidates versus proxy/orphan cleanup, then rerun as proper 14:57-asof families.

## Optimized Execution Order

1. Finish `stk_mins_1` backfill to broad SH/SZ coverage, then rerun this audit.
2. Build a strict `true_1457_asof` feature cache with explicit `snapshot_time`, `cutoff_policy`,
   source coverage, and train/live feature mapping.
3. Rebuild S2 best-9 and S2-only 60 columns under asof semantics; compare delete vs rewrite vs T-1 proxy.
4. Rebuild C174-C188 5min factors using safe cutoff semantics. If exact 14:57 is required, combine
   5min history with the 1min 14:56/14:57 slice rather than using the 15:00 bar.
5. After 1min is complete, add C189-C193 and C244-C261/C273-C285 as first-wave minute families.
6. Run family screens only as triage, then promote shortlisted families to full 23-fold
   `fixed_recent_36m` rolling. Do not select champion from screen results.
7. Only after full rolling: run window sensitivity, candidate-pool matrix, feature-selection/budget,
   model-family, HPO, calibration, seed, ensemble, strategy and Web/live gates.

## Readiness Scorecard

| gate                                 | status               | severity   | evidence                                                                                                                                                               | required_fix                                                                       | acceptance_check                                                                          |
|:-------------------------------------|:---------------------|:-----------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------|
| full_market_1min_breadth             | BLOCKED              | P0         | stk_mins_1 root files=230, markets={"SZ": 230}                                                                                                                         | finish full-market 1min backfill                                                   | >=3000 symbol files with both SH/SZ and sampled monthly 14:57 coverage                    |
| historical_1457_timestamp            | PASS_SAMPLE          | P1         | 24/24 sampled 1min symbols have 14:57 bars                                                                                                                             | recheck after full backfill                                                        | all sampled SH/SZ symbols across old/new listings contain expected 14:57 dates            |
| 5min_breadth_and_cutoff              | PASS_WITH_LIMITATION | P1         | stk_mins_5 root files=3195; sample has 14:55 but no exact 14:57                                                                                                        | use 14:55-safe cutoff or combine with 1min 14:57 slice                             | no training feature may consume the 15:00 5min bar for formal 14:57                       |
| true_1457_asof_feature_cache         | BLOCKED              | P0         | latest feature caches are generic gpu_probe schemas                                                                                                                    | build true_1457_asof cache with snapshot_time/cutoff_policy/source coverage        | schema/golden replay/train-live mapping all pass                                          |
| factor_registry_champion_eligibility | BLOCKED              | P0/P1      | A_pending_data=36, A_rewrite_required=95                                                                                                                               | complete data and rewrite/proxy catalog before champion training                   | P0=0, P1=0 for selected feature set                                                       |
| known_bundles_direct_freeze          | BLOCKED              | P1         | no known S2/PhaseC/pre_new_A bundle is direct champion-eligible now                                                                                                    | use bundles as references; retrain on true 14:57-asof cache                        | bundle selected features show no rewrite/proxy/orphan issues and score-only replay passes |
| s2_increment_rehabilitation          | READY_AFTER_CACHE    | P1         | S2-only selected=60, rewrite=57, proxy=2                                                                                                                               | split S2-only rewrite vs proxy and rerun full 23-fold fixed_recent_36m             | S2 increments beat/hold stability versus PhaseC/pre_new_A baseline without P0/P1          |
| unclassified_cache_source_asof_rules | NEEDS_CLASSIFICATION | P1         | unclassified_sources=25 sample=adj_factor,cb_daily,ccass_hold,express_vip,forecast_vip,ggt_daily,hk_hold,hsgt_top10,index_dailybasic,index_global,margin,margin_detail | assign each discovered source to A/B/C/D source timing and factor-family ownership | no source used by champion factors remains unclassified                                   |

## Next Task Queue

|   priority | task                                         | can_run_now   | blocked_by                                                                                                                                                             | deliverable                                                                                             | exit_criteria                                                       |
|-----------:|:---------------------------------------------|:--------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------|
|          1 | Complete full-market stk_mins_1 backfill     | False         | external data pull still running / incomplete                                                                                                                          | stk_mins_1 root parquet set covering SH/SZ/BJ if used                                                   | >=3000 symbols, broad SH/SZ, sampled 14:57 dates pass               |
|          2 | Classify discovered unassigned cache sources | False         | unclassified_sources=25 sample=adj_factor,cb_daily,ccass_hold,express_vip,forecast_vip,ggt_daily,hk_hold,hsgt_top10,index_dailybasic,index_global,margin,margin_detail | source timing/asof ownership table for adj_factor, auction, THS, index, margin, hsgt and related caches | no champion-used source remains unclassified_source                 |
|          3 | Build true_1457_asof feature cache           | False         | full-market 1min incomplete                                                                                                                                            | versioned feature cache with snapshot_time, cutoff_policy, source coverage                              | P0=0 for cache, selected feature mapping reproducible               |
|          4 | Rehabilitate S2-only 60 selected features    | False         | true_1457_asof cache missing                                                                                                                                           | S2-only rewrite/proxy manifest and family variants                                                      | 57 rewrite features and 2 proxy features split into proper variants |
|          5 | Run first-wave minute families               | False         | 1min data incomplete                                                                                                                                                   | C189-C193 and C244-C261/C273-C285 family screen results                                                 | 2-4 shortlisted families ready for full rolling                     |
|          6 | Run full 23-fold fixed_recent_36m rolling    | False         | shortlist and true-asof cache missing                                                                                                                                  | leaderboard, worst-window rows, P0/P1 audit                                                             | candidate beats stable baseline on mean/min/std Wilson and coverage |
|          7 | Run non-factor matrices                      | False         | full rolling finalists missing                                                                                                                                         | window, candidate-pool, selection/budget, model-family matrices                                         | top 2-4 finalists selected for HPO/calibration                      |
|          8 | Freeze and Web/live gate                     | False         | finalists missing                                                                                                                                                      | 1-3 frozen bundles plus score-only Q1/April and live replay                                             | Champion/Challenger/NO_FREEZE decision with P0=0/P1=0               |

## Factor Action Queue

|   priority | factor_scope                                    |   factor_count | asof_class                   | action                                                                    | experiment_role                                                 |
|-----------:|:------------------------------------------------|---------------:|:-----------------------------|:--------------------------------------------------------------------------|:----------------------------------------------------------------|
|          1 | C189-C193/C244-C261/C273-C285 minute first-wave |             21 | A_pending_data / mixed       | wait for full-market stk_mins_1, then formula-lock and golden replay      | first-wave family screen only, then full 23-fold if shortlisted |
|          2 | S2 selected-only increment over PhaseC          |             60 | A_rewrite_required + B proxy | rehabilitate, not discard; split rewrite vs T-1/proxy variants            | strong challenger route after asof rebuild                      |
|          3 | All A_rewrite_required factors                  |             95 | A_rewrite_required           | implement/rebuild from shared 14:57 snapshot; no old close-schema reuse   | main clean-factor expansion pool                                |
|          4 | Current strict A factors                        |             30 | A                            | keep as baseline clean pool; still rerun on true_1457_asof cache          | PhaseC/S2/pre_new_A reference rebuild component                 |
|          5 | B proxy/T-1 candidates                          |             77 | B                            | create delete-vs-T1/proxy pairs with explicit new names                   | secondary ablation only, never silent inclusion                 |
|          6 | D unknown evidence factors                      |             52 | D                            | suspend from champion route until source/asof evidence is added           | research backlog                                                |
|          7 | Hard C forbidden factors                        |              2 | C                            | reject from strict champion unless redefined into a new live-safe factor  | reject list / rewrite backlog                                   |
|          8 | Known bundle selected family gates              |            717 | bundle-selected mixed        | resolve family gates before using any known bundle as more than reference | bundle rebuild prerequisite                                     |

## Experiment Decision Protocol

|   stage_order | dimension                     | allowed_now   | dependency                                   | primary_metrics                                                    | promotion_rule                                                           |
|--------------:|:------------------------------|:--------------|:---------------------------------------------|:-------------------------------------------------------------------|:-------------------------------------------------------------------------|
|             1 | data_and_asof_gate            | True          | none                                         | coverage, missing months, sampled 14:57 bars, P0/P1                | P0=0/P1=0, then build cache                                              |
|             2 | true_1457_asof_cache          | False         | full-market 1min breadth and source coverage | schema parity, golden replay, no leak scan, mapping hash           | cache is versioned and replay-equivalent to Web/live feature builder     |
|             3 | factor_family_screen          | False         | true_asof cache                              | 4-fold screen mean/min Wilson, candidate count, P0/P1              | 2-4 families enter full 23-fold fixed_recent_36m                         |
|             4 | full_fixed_recent_36m         | False         | shortlisted families                         | mean_wilson_95, min_wilson_95, std_wilson_95, accuracy, coverage   | candidate beats pre_new_A stable baseline without weakening tail risk    |
|             5 | candidate_pool                | False         | full rolling candidate model                 | daily candidate count, coverage, topK hit, sector concentration    | stable coverage with P0 filters all clean                                |
|             6 | selection_and_budget          | False         | family candidates                            | Wilson stability, feature overlap, drift prune, orphan flag check  | selected set stable across folds and no P0/P1 selected                   |
|             7 | model_family_hpo              | False         | top 2-4 full-rolling candidates              | stability-first Optuna objective, Brier, tie penalty               | multi-fold HPO improves stability without candidate collapse             |
|             8 | calibration_selector          | False         | trained finalists                            | bucket monotonicity, Brier, candidate count, daily topK            | selector improves stable high-confidence hit rate with adequate coverage |
|             9 | seed_ensemble_strategy_regime | False         | finalist configs                             | mean/min/std across seeds, worst windows, drawdown, regime buckets | Champion/Challenger ranking remains consistent under seeds and regimes   |
|            10 | freeze_web_live_gate          | False         | final P0/P1-clean candidate                  | score-only replay, live parity, runtime, missing feature count     | freeze 1-3 bundles or output NO_FREEZE                                   |

## Required Next Actions

- Complete full-market stk_mins_1 backfill and rerun this audit.
- Build strict true 14:57-asof feature cache from minute cutoff; do not train champion on 15:00 full-day proxies.
- Run S2-only rehabilitation with asof rewritten columns, not old hard-delete assumptions.
- After P0/P1 clear, run family screens, then full 23-fold fixed_recent_36m for shortlisted families.

## Training Matrix Gate

| phase      | experiment_group               | status                                | champion_eligible_now   | next_action                                                                          |
|:-----------|:-------------------------------|:--------------------------------------|:------------------------|:-------------------------------------------------------------------------------------|
| Phase 3    | true_1457_asof_cache           | blocked_by_p0                         | False                   | Finish stk_mins_1 backfill, then build schema/parity/golden replay.                  |
| Phase 4    | PhaseC_asof_baseline           | blocked_until_asof_cache              | False                   | Rebuild as score-only baseline after cache exists; do not promote as champion route. |
| Phase 4    | S2_rehabilitation              | partially_blocked_by_rewrite_and_1min | False                   | Map every S2-only factor to A/B/C/D; rewrite A factors on asof snapshot.             |
| Phase 4    | 5min_intraday_family           | research_ready_not_champion           | False                   | Build cutoff version excluding post-14:57 bars; run family screen after parity.      |
| Phase 4    | 1min_microstructure_family     | blocked_by_p0                         | False                   | Wait for 1min backfill; audit 14:57 bar coverage month-by-month.                     |
| Phase 4    | all_A_engineerable             | blocked_until_rewrite                 | False                   | After cache, run 4-fold family screen, then 23-fold full rolling for finalists.      |
| Phase 4    | A_plus_B_proxy                 | pending_proxy_design                  | False                   | Create separate feature names for proxy families and run paired ablations.           |
| Phase 5    | full_fixed_recent_36m_rolling  | blocked_until_shortlist_and_cache     | False                   | Run every shortlisted family through full 23-fold fixed_recent_36m.                  |
| Phase 6    | time_window_matrix             | pending_after_main_protocol           | False                   | Use same factor/model config; compare stability, not Q1/April.                       |
| Phase 6    | candidate_pool_matrix          | pending_after_cache                   | False                   | Run filter matrix and track no-candidate days and sector concentration.              |
| Phase 6    | selection_budget_matrix        | pending_after_family_shortlist        | False                   | Compare mean/min/std Wilson and feature overlap across folds.                        |
| Phase 7    | model_hpo_calibration_selector | pending_after_full_rolling            | False                   | Optimize stability-first objective; never use Q1/April.                              |
| Phase 8    | seed_ensemble_strategy_regime  | pending_after_hpo                     | False                   | Run multi-seed, ensemble, strategy consistency and weak-window analysis.             |
| Phase 9-10 | freeze_and_web_live_gate       | pending_after_no_p0_p1                | False                   | Freeze only if P0/P1=0 and future final_forward can be monitored.                    |

## Output Files

- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_evidence_index_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_cache_audit_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_factor_audit_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_training_matrix_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_minute_symbol_audit_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_feature_cache_audit_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_bundle_summary_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_bundle_feature_audit_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_factor_family_summary_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_s2_increment_summary_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_s2_increment_audit_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_source_temporal_summary_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_source_asof_policy_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_bundle_family_gate_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_readiness_scorecard_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_next_task_queue_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_factor_action_queue_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_experiment_protocol_20260516.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_execution_gate_20260516.json`

## Decision

No champion training should start from this audit state. The project can continue evidence/factor
work and research-only screens, but final strict 14:57 training requires a complete 1min cache and
a verified true 14:57-asof feature cache first.
