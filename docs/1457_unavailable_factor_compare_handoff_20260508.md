# 14:57 Unavailable Factor Comparison Handoff

Date: 2026-05-08

This handoff is for a new cc session. The task is model comparison only, not live Web engineering.

## Goal

Current `M1457_greedy_top8` is the best 14:57 no-hard-moneyflow research winner so far, but the live hard gate showed that several selected features still come from T-day data that is not available at 14:57.

Run controlled training comparisons to decide, for these unavailable/non-executable feature families, whether the best production model should:

1. delete the features entirely, or
2. replace T-day values with T-1 shifted values.

Do not tune on April. Q1 is the selection window; April is forward-only validation.

## Current Reference

Baseline research winner:

- Variant: `M1457_greedy_top8`
- Bundle: `E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260508T020054Z_fcda6c48\model_bundle.pt`
- Q1 result from `docs/1457_final_summary_20260507.md`: HC Accuracy `78.79%`, Wilson `77.93%`
- April winner result from `docs/1457_april_holdout_report_20260508.md`: HC Accuracy `76.85%`, Wilson `73.88%`
- Trading-facing Q1 selector from `docs/1457_daily_topk_selector_probe_20260508.md`: `prob>=0.70` and daily top5 gives 96 candidates, 83.33% accuracy, 74.63% Wilson

Important nuance: the `M1457_*` manifest excluded C004/C009 and hard moneyflow fields, but it did not exclude every older/base Tushare research feature. That is why the saved winner can still select T-day LHB/margin/chip/closing-auction fields.

## Already Solved / Out Of Scope

Do not spend this comparison cycle on these unless the user explicitly asks:

- Real-time limit-up / failed-board pools are already live-engineered in `scripts/realtime_1457_today_probe.py`.
  - `stock_zt_pool_em`, `stock_zt_pool_zbgc_em`, `stock_zt_pool_dtgc_em`, `stock_zt_pool_strong_em`, `stock_zt_pool_previous_em`
  - `tushare_seal_ratio`, `tushare_open_times`, `tushare_first_time_minutes`, `tushare_up_stat_days`, `tushare_limit_type`, `tushare_limit_turnover`
- Minute/VWAP/daily-derived fields are considered engineering-solvable and should be handled later in the live path:
  - `tushare_last_30min_return`
  - `tushare_vwap_deviation`
  - `tushare_close_vs_vwap`
  - `tushare_price_vs_cost_20d`
  - `tushare_abnormal_3d_deviation`
  - `tushare_asr_60d`

The only exception is `tushare_float_relative_impact`; see the comparison set below.

## Features To Compare

For every value feature below, include its `_available` column in the same treatment.

### A. LHB / Institutional Seats

These are published after close and are not known at 14:57 on T day.

- `tushare_lhb_net_buy`
- `tushare_lhb_net_rate`
- `tushare_inst_buy_count`

Optional audit-only columns from the same family, if they appear in selected/input features:

- `tushare_lhb_appeared`
- `tushare_inst_net_buy`

### B. Margin Financing

At 14:57, the latest safe value is T-1.

- `tushare_rzye_delta_pct`

Optional same-family audit columns:

- `tushare_rzye`
- `tushare_rzmre_ratio`
- `tushare_margin_net`
- `tushare_rqye_ratio`

### C. Chip / Cost Distribution

T-day `cyq_perf` should not be treated as known at 14:57.

- `tushare_cost_concentration`
- `tushare_cost_position`

Optional same-family audit column:

- `tushare_winner_rate`

### D. Closing Auction

Closing auction is after 14:57 and must not be used as T-day live input.

- `tushare_auction_close_vwap_ratio`

Optional same-family audit column:

- `tushare_auction_close_vol`

Do not confuse this with opening auction:

- `tushare_auction_open_vwap_ratio` is allowed.
- `tushare_auction_open_vol` is allowed.

### E. Float Relative Impact

- `tushare_float_relative_impact`

Treat as blocked for this comparison unless you explicitly implement and verify the original executable formula. Existing docs flag implementation mismatch: current code derives it via Tushare moneyflow temporary volume, not the intended daily-volume/free-share formula.

Conservative default for this round: include it in the delete-vs-T-1 comparison set and report it separately.

## Must Never Reintroduce

Always exclude these 14 hard moneyflow fields:

```text
tushare_net_mf_amount
tushare_net_mf_amount_available
tushare_lg_buy_sell_ratio
tushare_lg_buy_sell_ratio_available
tushare_elg_buy_sell_ratio
tushare_elg_buy_sell_ratio_available
tushare_mf_strength
tushare_mf_strength_available
tushare_sm_sell_pressure
tushare_sm_sell_pressure_available
tushare_main_force_divergence
tushare_main_force_divergence_available
tushare_ff_adjusted_flow
tushare_ff_adjusted_flow_available
```

Also keep C004/C009 out of formal training:

- `tushare_ff_adjusted_flow`
- `tushare_main_force_divergence`

If any of these appear in `input_features` or `selected_features`, stop and report P0 failure.

## Experiment Design

Use the same training protocol as `scripts/run_1457_no_hard_moneyflow_matrix.py`:

- `start=2023-05-01`
- Q1 selection/test: `train_end=2025-12-31`, `test_start=2026-01-01`, `end=2026-03-31`
- `feature_set="research"`
- `label_target="next_high_from_close"`
- `target_high_return_pct=1.0`
- `feature_selection_method="stable_tail"`
- `max_selected_features=260`
- `min_phase_days_3=1`
- `exclude_event_limit_up=True`
- `exclude_feature_prefix=("cross_",)`
- `use_feature_cache=True`
- `refresh_feature_cache=False`

Then validate selected winners on April using the same holdout protocol as `scripts/run_1457_april_holdout.py`:

- `train_end=2026-03-31`
- `test_start=2026-04-01`
- `end=2026-04-30`
- no threshold/model/feature selection based on April

## Variants To Run

Use short names, but keep full metadata in the ledger.

1. `U00_current_reference`
   - Diagnostic only. Replicate current M1457-style setup for comparison.
   - Mark as not executable if it still uses T-day unavailable fields.

2. `U01_delete_all_blocked`
   - Exclude all features in A-E and their `_available` columns.
   - This is the clean strict baseline after live-engineerable fields are handled separately.

3. `U02_t1_all_blocked`
   - Replace all A-E feature families with T-1 shifted values.
   - Same column names, but row date T must contain previous trading day's source value.

4. Group-level comparisons:
   - `U10_lhb_delete`
   - `U11_lhb_t1`
   - `U20_margin_delete`
   - `U21_margin_t1`
   - `U30_chip_delete`
   - `U31_chip_t1`
   - `U40_close_auction_delete`
   - `U41_close_auction_t1`
   - `U50_float_impact_delete`
   - `U51_float_impact_t1`

5. Greedy policy variants:
   - Start from `U01_delete_all_blocked`.
   - Add back each family only if its T-1 version improves Q1 Wilson without harming April materially.
   - Candidate names: `U90_best_policy_q1`, `U91_best_policy_plus_sensitivity`.

## Correct T-1 Implementation

Do not use T-day post-close values.

Preferred implementation:

1. Build the full Tushare factor frame with normal `symbol,date` rows.
2. For the selected blocked columns, sort by `symbol,date`.
3. For each symbol, shift the value and availability by one trading row:
   - row T gets previous trading row's value
   - row T gets previous trading row's availability flag
4. Keep all other fields unchanged.

Avoid a calendar-day shift. It will break around weekends and holidays.

Sparse LHB warning:

- Do not shift only the sparse `top_list` rows and then merge directly, because most symbols will not have a row on T.
- Shift after the full factor frame has daily rows, or reindex LHB to the model universe's symbol-date grid before shifting.

Availability warning:

- If shifting from an already materialized feature cache, shift both `feature` and `feature_available`.
- A shifted zero with `_available=0` should remain unavailable, not become a real zero signal.

## Metrics To Report

For Q1 and April, report at minimum:

- HC Accuracy
- Wilson lower 95
- confident count
- confident coverage
- Brier
- selected feature count
- whether any P0 fields entered input/selected features

Also report threshold and trading-facing selector tables:

- `T>=0.70`
- `T>=0.75`
- `T>=0.78`
- `T>=0.80`
- daily top5 without threshold
- daily top6 without threshold
- `T>=0.70` and daily top5
- `T>=0.70` and daily top6

For each selector row include:

- candidate count
- average candidates/day
- accuracy
- Wilson lower 95
- average next-day high return if the predictions parquet has enough price fields

## Expected Outputs

Write all outputs under the existing runtime/report structure:

- Ledger: `E:\ashare_similarity_runtime\data\reports\prediction\experiment_ledger_20260508_unavailable_factor_compare.jsonl`
- Summary JSON: `E:\ashare_similarity_runtime\data\reports\prediction\1457_unavailable_factor_compare_20260508.json`
- Human report: `docs/1457_unavailable_factor_compare_results_20260508.md`
- If a new winner is produced, write its bundle path and exact selected features.

The final report should lead with:

1. best executable policy
2. Q1 metrics
3. April metrics
4. trade-facing top5/top6 selector metrics
5. P0 audit
6. which families were deleted vs T-1 shifted

## Useful Existing Files

- `scripts/run_1457_no_hard_moneyflow_matrix.py`
- `scripts/run_1457_april_holdout.py`
- `scripts/run_1457_live_sim.py`
- `scripts/realtime_1457_today_probe.py`
- `docs/1457_final_summary_20260507.md`
- `docs/1457_april_holdout_report_20260508.md`
- `docs/1457_daily_topk_selector_probe_20260508.md`
- `docs/engineering_gate_report_20260507.md`
- `docs/selected_feature_catalog_audit_20260507.md`
- `src/ashare_similarity/prediction/free_data_factors.py`
- `src/ashare_similarity/prediction/gpu_probe.py`

## Suggested First Prompt For New cc

```text
Read docs/1457_unavailable_factor_compare_handoff_20260508.md first.
Your job is to run delete-vs-T-1 training comparisons for the remaining 14:57-unavailable selected feature families:
LHB/inst, margin, chip, closing auction, and float_relative_impact.
Do not work on live Web engineering or realtime limit pools.
Keep the 14 hard moneyflow fields and C004/C009 excluded.
Use Q1 for selection and April only as forward validation.
Write a ledger, JSON summary, and docs/1457_unavailable_factor_compare_results_20260508.md.
Stop and report if any hard-unavailable moneyflow field enters input_features or selected_features.
```
