# 14:57 下一轮训练 Phase 1 证据汇总

生成时间：2026-05-13 10:13:25

## 自审结论

- 输入审计：PASS=7，FAIL=0。
- 固定训练矩阵：36 行；旧 bundle score-only：24 行。
- 合并 leaderboard：30 行。
- 输出 CSV：`E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_stage1_combined_20260513.csv`
- 输出 JSON：`E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_stage1_combined_20260513.json`

| check                          | status   | detail                           |
|:-------------------------------|:---------|:---------------------------------|
| matrix_rows_expected           | PASS     | 36 / 36                          |
| bundle_rows_expected           | PASS     | 24 / 24                          |
| matrix_audit_clean             | PASS     | {"p0": 0, "p1": 0, "wip": 0}     |
| matrix_completed_only          | PASS     | {'completed': 36}                |
| bundle_completed_only          | PASS     | {'completed': 24}                |
| bundle_no_missing_features     | PASS     | missing feature columns are zero |
| no_q1_or_april_in_stage1_outer | PASS     | max outer_valid_end=2025-12-31   |

## 统一 Leaderboard（按 p>=0.75 Wilson 均值排序）

| evidence_source            | candidate_id                   | scheme                    |   folds |   mean_pge075_wilson95 |   min_pge075_wilson95 |   mean_pge075_accuracy |   total_pge075 |
|:---------------------------|:-------------------------------|:--------------------------|--------:|-----------------------:|----------------------:|-----------------------:|---------------:|
| fixed_config_train         | all_A_engineerable             | expanding_from_fair_start |       2 |               0.800317 |              0.776661 |               0.816801 |           4495 |
| fixed_config_train         | pre_new_A_engineerable_control | fixed_start_2018          |       2 |               0.798616 |              0.780175 |               0.815284 |           4438 |
| fixed_config_train         | pre_new_A_engineerable_control | expanding_from_fair_start |       2 |               0.798472 |              0.780341 |               0.815228 |           4397 |
| fixed_config_train         | new_5min_family_only           | expanding_from_fair_start |       2 |               0.798467 |              0.769641 |               0.814302 |           4906 |
| fixed_config_train         | new_5min_family_only           | fixed_start_2018          |       2 |               0.796796 |              0.770368 |               0.812796 |           4835 |
| fixed_config_train         | all_A_engineerable             | fixed_start_2018          |       2 |               0.795435 |              0.778225 |               0.81184  |           4632 |
| score_only_existing_bundle | baseline_s2                    | fixed_recent_60m          |       2 |               0.788478 |              0.768851 |               0.802029 |           7292 |
| score_only_existing_bundle | baseline_s2                    | fixed_recent_36m          |       2 |               0.784186 |              0.760266 |               0.804229 |           3771 |
| score_only_existing_bundle | baseline_s2                    | fixed_start_2020          |       2 |               0.784186 |              0.760266 |               0.804229 |           3771 |
| fixed_config_train         | pre_new_A_engineerable_control | fixed_start_2020          |       2 |               0.78365  |              0.778579 |               0.801964 |           3928 |
| fixed_config_train         | pre_new_A_engineerable_control | fixed_recent_36m          |       2 |               0.781576 |              0.774594 |               0.799975 |           3935 |
| fixed_config_train         | new_5min_family_only           | fixed_recent_36m          |       2 |               0.780712 |              0.77362  |               0.79928  |           3864 |
| fixed_config_train         | new_5min_family_only           | fixed_start_2020          |       2 |               0.780574 |              0.774845 |               0.79894  |           4014 |
| fixed_config_train         | all_A_engineerable             | fixed_recent_36m          |       2 |               0.777604 |              0.776862 |               0.795716 |           4143 |
| score_only_existing_bundle | baseline_s2                    | fixed_recent_24m          |       2 |               0.777455 |              0.746805 |               0.794089 |           4829 |
| fixed_config_train         | all_A_engineerable             | fixed_start_2020          |       2 |               0.777236 |              0.774669 |               0.796295 |           3782 |

## 固定训练矩阵前排

| evidence_source    | candidate_id                   | scheme                    |   folds |   mean_pge075_wilson95 |   min_pge075_wilson95 |   mean_pge075_accuracy |   total_pge075 |
|:-------------------|:-------------------------------|:--------------------------|--------:|-----------------------:|----------------------:|-----------------------:|---------------:|
| fixed_config_train | all_A_engineerable             | expanding_from_fair_start |       2 |               0.800317 |              0.776661 |               0.816801 |           4495 |
| fixed_config_train | pre_new_A_engineerable_control | fixed_start_2018          |       2 |               0.798616 |              0.780175 |               0.815284 |           4438 |
| fixed_config_train | pre_new_A_engineerable_control | expanding_from_fair_start |       2 |               0.798472 |              0.780341 |               0.815228 |           4397 |
| fixed_config_train | new_5min_family_only           | expanding_from_fair_start |       2 |               0.798467 |              0.769641 |               0.814302 |           4906 |
| fixed_config_train | new_5min_family_only           | fixed_start_2018          |       2 |               0.796796 |              0.770368 |               0.812796 |           4835 |
| fixed_config_train | all_A_engineerable             | fixed_start_2018          |       2 |               0.795435 |              0.778225 |               0.81184  |           4632 |
| fixed_config_train | pre_new_A_engineerable_control | fixed_start_2020          |       2 |               0.78365  |              0.778579 |               0.801964 |           3928 |
| fixed_config_train | pre_new_A_engineerable_control | fixed_recent_36m          |       2 |               0.781576 |              0.774594 |               0.799975 |           3935 |
| fixed_config_train | new_5min_family_only           | fixed_recent_36m          |       2 |               0.780712 |              0.77362  |               0.79928  |           3864 |
| fixed_config_train | new_5min_family_only           | fixed_start_2020          |       2 |               0.780574 |              0.774845 |               0.79894  |           4014 |
| fixed_config_train | all_A_engineerable             | fixed_recent_36m          |       2 |               0.777604 |              0.776862 |               0.795716 |           4143 |
| fixed_config_train | all_A_engineerable             | fixed_start_2020          |       2 |               0.777236 |              0.774669 |               0.796295 |           3782 |

## 旧 S2/PhaseC Score-Only 基线

| evidence_source            | candidate_id    | scheme                    |   folds |   mean_pge075_wilson95 |   min_pge075_wilson95 |   mean_pge075_accuracy |   total_pge075 |   mean_daily_top5_wilson95 |   min_daily_top5_wilson95 |   missing_feature_total |
|:---------------------------|:----------------|:--------------------------|--------:|-----------------------:|----------------------:|-----------------------:|---------------:|---------------------------:|--------------------------:|------------------------:|
| score_only_existing_bundle | baseline_s2     | fixed_recent_60m          |       2 |               0.788478 |              0.768851 |               0.802029 |           7292 |                   0.720387 |                  0.714566 |                       0 |
| score_only_existing_bundle | baseline_s2     | fixed_recent_36m          |       2 |               0.784186 |              0.760266 |               0.804229 |           3771 |                   0.729375 |                  0.726209 |                       0 |
| score_only_existing_bundle | baseline_s2     | fixed_start_2020          |       2 |               0.784186 |              0.760266 |               0.804229 |           3771 |                   0.729375 |                  0.726209 |                       0 |
| score_only_existing_bundle | baseline_s2     | fixed_recent_24m          |       2 |               0.777455 |              0.746805 |               0.794089 |           4829 |                   0.703391 |                  0.680573 |                       0 |
| score_only_existing_bundle | baseline_phasec | fixed_recent_36m          |       2 |               0.771358 |              0.741658 |               0.791825 |           3654 |                   0.747287 |                  0.743945 |                       0 |
| score_only_existing_bundle | baseline_phasec | fixed_start_2020          |       2 |               0.771358 |              0.741658 |               0.791825 |           3654 |                   0.747287 |                  0.743945 |                       0 |
| score_only_existing_bundle | baseline_phasec | fixed_recent_60m          |       2 |               0.770471 |              0.739884 |               0.784492 |           7308 |                   0.740047 |                  0.736149 |                       0 |
| score_only_existing_bundle | baseline_s2     | expanding_from_fair_start |       2 |               0.762674 |              0.717243 |               0.774627 |          12395 |                   0.749322 |                  0.726209 |                       0 |
| score_only_existing_bundle | baseline_s2     | fixed_start_2018          |       2 |               0.762674 |              0.717243 |               0.774627 |          12395 |                   0.749322 |                  0.726209 |                       0 |
| score_only_existing_bundle | baseline_phasec | fixed_recent_24m          |       2 |               0.759679 |              0.718301 |               0.777437 |           4471 |                   0.717496 |                  0.691047 |                       0 |
| score_only_existing_bundle | baseline_phasec | expanding_from_fair_start |       2 |               0.755631 |              0.710205 |               0.767956 |          12234 |                   0.745214 |                  0.743945 |                       0 |
| score_only_existing_bundle | baseline_phasec | fixed_start_2018          |       2 |               0.755631 |              0.710205 |               0.767956 |          12234 |                   0.745214 |                  0.743945 |                       0 |

## 时间窗口初判

| scheme                    |   best_mean_wilson |   best_min_wilson |   variants |
|:--------------------------|-------------------:|------------------:|-----------:|
| expanding_from_fair_start |           0.800317 |          0.780341 |          3 |
| fixed_start_2018          |           0.798616 |          0.780175 |          3 |
| fixed_start_2020          |           0.78365  |          0.778579 |          3 |
| fixed_recent_36m          |           0.781576 |          0.776862 |          3 |
| fixed_recent_24m          |           0.7658   |          0.751217 |          3 |
| fixed_recent_60m          |           0.76091  |          0.743212 |          3 |

## 当前判断

- 不能再用 2026-04 单月准确率决定冠军；tier1 的多窗口证据显示窗口选择会显著改变结论。
- `fixed_start_2018` 与 `expanding_from_fair_start` 是第一梯队；`fixed_recent_36m` 和 `fixed_start_2020` 可做稳健性陪跑；`fixed_recent_24m/60m` 暂时落后。
- `all_A_engineerable` 在 expanding 上均值最高，但 `pre_new_A_engineerable_control` 在 2018/expanding 的最差窗口更稳；新 5min 因子单独可用但还不能单独当冠军。
- S2/PhaseC 旧 bundle 在 score-only 下仍有参考价值，尤其可作为风险基线；但它们不是同协议重训模型，不能直接替代下一轮冠军训练。

## 自动进入下一步

- Stage2 扩大 fold：`all_A_engineerable`、`pre_new_A_engineerable_control`、`new_5min_family_only`。
- Stage2 窗口：`expanding_from_fair_start`、`fixed_start_2018`、`fixed_recent_36m`、`fixed_start_2020`。
- 每个方案先取 4 个均匀 fold 复核，继续要求 P0=0、P1=0、WIP=0；通过后再做 HPO/multi-seed/frozen score-only。
