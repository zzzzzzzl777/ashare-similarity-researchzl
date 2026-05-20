# 14:57 Full Exploration Audit 20260515

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
- stk_holdertrade is empty_or_not_backfilled; related factors must stay pending/proxy-only.
- suspend_d is empty_or_not_backfilled; related factors must stay pending/proxy-only.
- ggt_top10 is empty_or_not_backfilled; related factors must stay pending/proxy-only.
- index_weight is empty_or_not_backfilled; related factors must stay pending/proxy-only.
- ths_member is sparse; related factors must stay pending/proxy-only.
- 95 factors look engineerable but require explicit 14:57-asof rewrite/golden replay before champion use.
- 52 factors have insufficient evidence and are suspended from champion candidates.

## Key Cache Summary

| source         |   file_count |   nested_parquet_count | market_counts            | completeness_status                  | gate_severity   | sampled_has_1457   | note                                                                                               |
|:---------------|-------------:|-----------------------:|:-------------------------|:-------------------------------------|:----------------|:-------------------|:---------------------------------------------------------------------------------------------------|
| stk_mins_1     |           62 |                     62 | {"SZ": 62}               | incomplete_blocks_true_1457_training | P0              | YES                | 1min per-symbol cache is far below full A-share coverage; true 14:57 champion training is blocked. |
| stk_mins_5     |         3195 |                  23344 | {"SH": 1703, "SZ": 1492} | available                            | OK              | NO                 | 5min cache appears broad; exact 14:57 reconstruction still requires 1min for true cutoff.          |
| raw_bars_daily |         5327 |                   5327 | {}                       | available                            | OK              | NO                 | Raw daily bars are available outside tushare cache and should satisfy daily OHLCV needs.           |
| daily_basic    |         2267 |                   2267 | {}                       | available                            | OK              | NO                 | Layout=per_date; sampled 8 files.                                                                  |
| stk_factor_pro |         1927 |                   1927 | {}                       | available                            | OK              | NO                 | Layout=per_date; sampled 8 files.                                                                  |
| cyq_perf       |         3198 |                   3198 | {"SH": 1704, "SZ": 1492} | available                            | OK              | NO                 | Layout=per_symbol; sampled 8 files.                                                                |
| moneyflow      |         2267 |                   2267 | {}                       | available                            | OK              | NO                 | Layout=per_date; sampled 8 files.                                                                  |

## Minute Coverage Sample

| source     |   sampled_symbols | markets   |   min_unique_dates |   max_unique_dates |   symbols_with_1457 |   min_1457_dates |   max_1457_dates |   symbols_with_1455 |   min_1455_dates |   max_1455_dates |
|:-----------|------------------:|:----------|-------------------:|-------------------:|--------------------:|-----------------:|-----------------:|--------------------:|-----------------:|-----------------:|
| stk_mins_1 |                62 | SZ        |                157 |               1906 |                  62 |              157 |             1905 |                  62 |              157 |             1905 |
| stk_mins_5 |                90 | SH,SZ     |               1096 |               2270 |                   0 |                0 |                0 |                  90 |             1096 |             2270 |

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
  The blocker is breadth, not timestamp availability. Current root coverage is only 62 SZ symbols.
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

- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_evidence_index_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_cache_audit_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_factor_audit_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_training_matrix_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_minute_symbol_audit_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_feature_cache_audit_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_bundle_summary_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_bundle_feature_audit_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_factor_family_summary_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_s2_increment_summary_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_s2_increment_audit_20260515.csv`
- `E:\ashare_similarity_runtime\data\reports\prediction\full_exploration_execution_gate_20260515.json`

## Decision

No champion training should start from this audit state. The project can continue evidence/factor
work and research-only screens, but final strict 14:57 training requires a complete 1min cache and
a verified true 14:57-asof feature cache first.
