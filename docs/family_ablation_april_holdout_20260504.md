# Family Ablation April Reserved Holdout Report

**Date**: 2026-05-04  
**Plan version**: v1.4 (第四轮训练)  
**Label**: `next_high_from_close` (T+1 日内最高价 >= 收盘价 +1%)  
**Acceptance target**: Wilson 95% lower bound >= 75%  
**Rules locked before holdout**: Yes  
**Post-hoc tuning applied**: **None**  

---

## 1. Run Metadata

| Field | Value |
|-------|-------|
| run_id | `gpu_probe_20260503T185913Z_793f0623` |
| variant | tier1_plus_b1_c009_c011 |
| used_factor_ids | [C009, C011] |
| feature_set | research |
| model | stacking_average_top3 (ensemble_average) |
| features_in_manifest | 376 |
| selected_features | 260 |
| tushare_selected | 11 (9 tier1 + C009 + C011) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| lockbox_role | seen_research |
| feature_hash | `d096e087f16ea198` |
| data_hash | `e2ebdf90c171dbe7` |
| split_hash | `0957315f1dc3f7e4` |
| artifact_path | `E:\...\runs\gpu_probe_20260503T185913Z_793f0623\artifact.json` |
| test_predictions_path | `E:\...\runs\gpu_probe_20260503T185913Z_793f0623\test_predictions.parquet` |

### 1.1 Config Match with Q1 B1

| Check | Q1 B1 (`41d4ad1d`) | April B1 (`793f0623`) | Match |
|-------|---------------------|----------------------|-------|
| feature_set | research | research | Yes |
| min_phase_days_3 | 1 | 1 | Yes |
| model | stacking_average_top3 | stacking_average_top3 | Yes |
| exclude_event_limit_up | True | True | Yes |
| feature_hash | d096e087f16ea198 | d096e087f16ea198 | **Yes** |
| selected_count | 260 | 260 | Yes |
| train_rows | 297,711 | 297,711 | Yes |
| test_end | 2026-03-30 | 2026-04-29 | **Diff (expected)** |

### 1.2 Split Manifest

| Field | Value |
|-------|-------|
| protocol | dev_train_dev_valid_test_lockbox_v1 |
| train_end | 2025-12-31 |
| test_start | 2026-01-01 |
| end | 2026-04-30 |
| train_window_rows | 297,711 |
| fit_rows | 211,014 |
| validation_rows | 86,124 |
| test_lockbox_rows | 57,167 |
| test_event_start | 2026-01-05 |
| test_event_end | 2026-04-29 |

### 1.3 C-Factor Status

| Factor | Column | in_features | selected |
|--------|--------|-------------|----------|
| C001 | tushare_mf_flow_intensity | **No** | No |
| C004 | tushare_ff_adjusted_flow | **No** | No |
| C009 | tushare_main_force_divergence | Yes | **Yes** |
| C010 | tushare_float_relative_impact | **No** | No |
| C011 | tushare_auction_open_vwap_ratio | Yes | **Yes** |

### 1.4 Selected Tushare Features (11)

| # | Feature | Source |
|---|---------|--------|
| 1 | tushare_net_mf_amount | tier1 (moneyflow) |
| 2 | tushare_lg_buy_sell_ratio | tier1 (moneyflow) |
| 3 | tushare_elg_buy_sell_ratio | tier1 (moneyflow) |
| 4 | tushare_mf_strength | tier1 (moneyflow) |
| 5 | tushare_sm_sell_pressure | tier1 (moneyflow) |
| 6 | tushare_volume_ratio | tier1 (daily_basic) |
| 7 | tushare_up_limit_distance | tier1 (stk_limit) |
| 8 | tushare_down_limit_distance | tier1 (stk_limit) |
| 9 | tushare_limit_range | tier1 (stk_limit) |
| 10 | tushare_main_force_divergence | **C009** (moneyflow) |
| 11 | tushare_auction_open_vwap_ratio | **C011** (stk_auction_o) |

Unselected: tushare_free_share (rejected by stable_tail)

---

## 2. April Holdout Summary

| Metric | Value |
|--------|-------|
| Date range | 2026-04-01 ~ 2026-04-29 |
| Trading days | 20 |
| Rows | 13,401 |
| Symbols | 1,954 |

---

## 3. Pre-locked Rule Results (April only)

### 3.1 Rule A: B1 + T>=0.75 + daily top50

| Metric | April | Q1 Reference | Delta |
|--------|-------|--------------|-------|
| Precision | **74.60%** | 86.53% | **-11.93pp** |
| Wilson LB | **67.95%** | 82.76% | **-14.81pp** |
| Count | 189 | 386 | -197 |
| Hits | 141 | — | — |
| Active days | 17/20 | 26/55 | — |
| Avg/all day | 9.45 | 7.02 | +2.43 |

Top50 cap 未生效 — April 每日最多 39 候选 (< 50)。

### 3.2 Rule B: B1 + T>=0.80 + daily top50

| Metric | April | Q1 Reference | Delta |
|--------|-------|--------------|-------|
| Precision | **100.00%** | 90.00% | +10.00pp |
| Wilson LB | **64.57%** | 85.65% | **-21.09pp** |
| Count | **7** | 250 | -243 |
| Hits | 7 | — | — |
| Active days | 3/20 | 17/55 | — |
| Avg/all day | 0.35 | 4.55 | -4.20 |

仅 7 个样本，Wilson 在此样本量下无统计意义。

### 3.3 Observation: B1 + T>=0.75 + daily top30

| Metric | April | Q1 Reference | Delta |
|--------|-------|--------------|-------|
| Precision | **75.14%** | 84.81% | **-9.67pp** |
| Wilson LB | **68.29%** | 80.05% | **-11.76pp** |
| Count | 177 | 270 | -93 |
| Hits | 133 | — | — |
| Active days | 17/20 | 26/55 | — |
| Avg/all day | 8.85 | 4.91 | +3.94 |

观察组仅供参考，不用于事后挑选正式规则。

---

## 4. Precision @ Threshold (April full scan)

| T | Precision | Wilson LB | Count | Hits | Active Days | Avg/AllDay |
|---|-----------|-----------|-------|------|-------------|------------|
| 0.70 | 71.30% | 69.69% | 3,119 | 2,224 | 20/20 | 155.95 |
| **0.75** | **74.60%** | **67.95%** | 189 | 141 | 17/20 | 9.45 |
| 0.76 | 77.06% | 70.18% | 170 | 131 | 15/20 | 8.50 |
| 0.80 | 100.00% | 64.57% | 7 | 7 | 3/20 | 0.35 |

---

## 5. B1 TopK Cap Analysis (April)

### 5.1 T >= 0.75

| TopK Cap | Precision | Wilson LB | Count | Active Days | Avg/AllDay |
|----------|-----------|-----------|-------|-------------|------------|
| top5 | 81.13% | 68.64% | 53 | 17 | 2.65 |
| top10 | 73.86% | 63.82% | 88 | 17 | 4.40 |
| top20 | 74.83% | 67.13% | 143 | 17 | 7.15 |
| top30 | 75.14% | 68.29% | 177 | 17 | 8.85 |
| top50 | 74.60% | 67.95% | 189 | 17 | 9.45 |

### 5.2 T >= 0.80

| TopK Cap | Precision | Wilson LB | Count | Active Days | Avg/AllDay |
|----------|-----------|-----------|-------|-------------|------------|
| top5 | 100.00% | 64.57% | 7 | 3 | 0.35 |
| top10 | 100.00% | 64.57% | 7 | 3 | 0.35 |
| top20 | 100.00% | 64.57% | 7 | 3 | 0.35 |
| top30 | 100.00% | 64.57% | 7 | 3 | 0.35 |
| top50 | 100.00% | 64.57% | 7 | 3 | 0.35 |

T>=0.80 在 April 几乎无候选 (仅 7 个)，所有 cap 级别结果相同。

---

## 6. Daily Candidate Concentration

### 6.1 T >= 0.75

| Stat | April | Q1 |
|------|-------|----|
| Total candidates | 189 | 1,294 |
| Active / Total days | 17/20 (85%) | 26/55 (47%) |
| Zero-candidate days | 15% | 53% |
| Min per active day | 1 | 1 |
| Median | 3 | 4 |
| Mean | 11.1 | 49.8 |
| P75 | 19 | 13 |
| Max | 39 | 518 |
| Top date % of total | 20.6% | 40.0% |

April 集中度显著优于 Q1 — 最大单日仅 39 候选 (Q1: 518)，zero-day 比例 15% vs 53%。

### 6.2 Daily Breakdown (T >= 0.75)

| Date | Candidates | Hits | Precision |
|------|-----------|------|-----------|
| 2026-04-02 | 33 | 23 | 69.70% |
| 2026-04-03 | 25 | 24 | **96.00%** |
| 2026-04-07 | 39 | 34 | **87.18%** |
| 2026-04-08 | 11 | 3 | **27.27%** |
| 2026-04-09 | 1 | 1 | 100.00% |
| 2026-04-10 | 5 | 5 | 100.00% |
| 2026-04-13 | 1 | 1 | 100.00% |
| 2026-04-14 | 2 | 1 | 50.00% |
| 2026-04-15 | 2 | 2 | 100.00% |
| 2026-04-16 | 3 | 2 | 66.67% |
| 2026-04-17 | 1 | 1 | 100.00% |
| 2026-04-20 | 1 | 1 | 100.00% |
| 2026-04-21 | 1 | 1 | 100.00% |
| 2026-04-22 | 1 | 1 | 100.00% |
| 2026-04-23 | 29 | 18 | 62.07% |
| 2026-04-27 | 19 | 10 | 52.63% |
| 2026-04-28 | 15 | 13 | **86.67%** |

### 6.3 T >= 0.80 Daily Breakdown

| Date | Candidates | Hits | Precision |
|------|-----------|------|-----------|
| 2026-04-07 | 5 | 5 | 100.00% |
| 2026-04-23 | 1 | 1 | 100.00% |
| 2026-04-28 | 1 | 1 | 100.00% |

---

## 7. Key Observations

1. **Rule A 未通过 75% Wilson 目标**: April precision=74.60%, Wilson=67.95% — 两者均低于 Q1 参考值和 75% 接受线。
2. **Rule B 样本不足**: 仅 7 个候选，Wilson=64.57%，无统计意义。
3. **Q1 → April 精度衰减约 12pp**: Rule A 从 86.53% 降至 74.60%，Q1 高精度可能部分依赖 2026-01-13 单日 518 候选 (88% hit rate) 的集中贡献。
4. **April 集中度健康**: 无单日 > 39 候选，zero-day 仅 15%。但低精度日 (04-08: 27%, 04-27: 53%) 对总精度拖累显著。
5. **2026-04-08 是最差日**: 11 候选仅 3 命中 (27.27%)，贡献了 189 个候选中 8 个 miss (8/48 total misses = 17%)。
6. **不做任何调参决定**: 本报告仅记录 holdout 结果，不修改规则、阈值或因子。

---

*Generated from artifact.json + test_predictions.parquet. Not committed. Not pushed. No acceptance claim. No final_unseen claim. No post-hoc tuning applied.*
