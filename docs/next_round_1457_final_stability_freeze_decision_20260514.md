# 14:57 下一轮稳定性冠军冻结决策 20260514

## 2026-05-15 Strict Audit Addendum

This decision is superseded for strict 14:57 champion selection.

The original freeze used an incomplete P0 audit set in
`run_1457_next_round_fixed_matrix.py`. A recomputed strict audit now fails the
Tier-3 and Tier-7 fixed matrix outputs because selected features include
same-name T-day/post-close or implementation-mismatched columns such as
`tushare_net_mf_amount`, `tushare_auction_close_vwap_ratio`,
`tushare_auction_close_vol`, `tushare_lhb_net_rate`,
`tushare_rqye_ratio`, and `tushare_float_relative_impact`.

Therefore `pre_new_A_engineerable_control` and
`family_drop_intraday_volume_structure` must be treated as research evidence
only until rerun with the expanded strict P0 gate and a 14:57-asof feature
cache. They are not valid strict champion candidates under the updated gate.

## Decision

Champion candidate: `pre_new_A_engineerable_control`.

Challenger: `family_drop_intraday_volume_structure`.

`family_drop_intraday_volume_structure` has a slightly higher 3-seed mean Wilson, but it fails the stability-first rule because seed 2026 / 2023Q3 drops to `0.698737`. `pre_new_A_engineerable_control` keeps the better tail floor and remains the frozen champion candidate.

Q1 and April were not used for model selection, feature selection, calibration, or threshold selection. They are only score-only consistency checks.

## Evidence Chain

| Stage | Role | Result |
|---|---|---|
| Tier-3 full 23-fold | baseline comparison | `pre_new_A` had lower mean than `all_A`, but better tail stability. |
| Tier-4 family screen | family screening only | `family_drop_intraday_volume_structure` promoted only to full rolling candidate. |
| Tier-5 full 23-fold | challenger validation seed 42 | challenger improved min slightly but lost mean/accuracy. |
| Tier-6 seed 7 | multi-seed extension | challenger looked better on two seeds. |
| Tier-7 seed 2026 | stress seed | challenger collapsed on fold 19; `pre_new_A` kept better tail. |
| Tier7 3-seed summary | final selection evidence | stability-first leader = `pre_new_A_engineerable_control`. |

## Stability Leaderboard

| Variant | Seeds | Fold Runs | Mean W95 | Min W95 | Std W95 | Mean Accuracy | Candidates | Role |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `pre_new_A_engineerable_control` | 3 | 69 | 0.782220 | 0.713268 | 0.034187 | 0.803175 | 163606 | Champion candidate |
| `family_drop_intraday_volume_structure` | 3 | 69 | 0.783020 | 0.698737 | 0.034483 | 0.803801 | 164699 | Challenger |

Worst risk row: challenger seed 2026, fold 19, `2023-07-01 ~ 2023-09-30`, Wilson `0.698737`.

## Frozen Bundle

| Item | Value |
|---|---|
| Run ID | `gpu_probe_20260514T110633Z_e763ec32` |
| Bundle | `E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260514T110633Z_e763ec32\model_bundle.pt` |
| Feature cache | `E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_10c11fc874db003c.parquet` |
| Train window | `2023-01-01 ~ 2025-12-31` |
| Excluded from training | `2026Q1` and `2026-04` |
| First forward observation | `2026-05-06 ~ 2026-05-11` |
| Model | `stacking_average_top3` |
| Members | `gpu_xgboost_hist_deep`, `catboost_cpu_fallback_compact`, `lightgbm_cpu_stable_wide` |
| Calibration | isotonic |
| Selected features | 260 |
| Full features | 763 |

Freeze self-audit:

| Check | Status |
|---|---|
| run completed | PASS |
| strict GPU backend | PASS |
| `.venv5090` Python | PASS |
| final_unseen window after freeze | PASS |
| Q1/April not in train | PASS |
| P0 selected = 0 | PASS |
| bundle self-validation | PASS, max diff `0.0` |
| bundle exists | PASS |
| forward sample nonempty | PASS |

## Score-Only Checks

These rows were produced by frozen bundle inference only. No training, feature selection, calibration, or threshold update occurred.

| Window | Rows | Missing Features | p>=0.75 Count | p>=0.75 Accuracy | p>=0.75 W95 | Daily Top5 Accuracy | Daily Top5 W95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Q1 seen research | 43621 | 0 / 0 | 5271 | 0.801935 | 0.790958 | 0.800000 | 0.749229 |
| April seen research | 14202 | 0 / 0 | 717 | 0.768480 | 0.736224 | 0.790476 | 0.703084 |
| May partial final_forward | 2654 | 0 / 0 | 40 | 0.800000 | 0.652427 | 0.800000 | 0.548146 |

May partial is not a final pass. It has only 3 label dates and 40 samples at `p>=0.75`, so Wilson is too low. The v4 rerun also reuses the same May lockbox identity after warning cleanup, so it must be treated as an early observation only.

## Engineering Notes

Code changes made during freeze cleanup:

- Added `scripts/run_1457_champion_freeze.py` for protocol-aware champion freezing.
- Fixed safe division in `tgb_daily_factors.py`.
- Removed pandas concat future-warning source in `free_data_factors.py`.
- Centralized tree-model `predict_proba` warning suppression in `gpu_probe.py`.
- Applied the same warning cleanup in `score_1457_existing_bundles.py`.

Verification:

- `py_compile` passed for all touched scripts/modules.
- v4 freeze completed with P0=0, P1=0.
- v4 score-only Q1/April/May completed with missing feature count `0`.
- No matching long-running training/scoring process remains.

## Final Gate

The project now has a frozen champion candidate and a valid bundle. It should not be called final passed until a fresh, post-freeze unseen window accumulates enough samples. The next gate is score-only only:

1. Keep the v4 bundle, selected feature order, calibration, and thresholds fixed.
2. Score new unseen dates after the current May partial window.
3. Require P0=0, missing features=0, and adequate sample size.
4. Apply the stability-first acceptance standard instead of any single-month headline accuracy.
