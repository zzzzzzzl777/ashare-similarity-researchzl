# Family Ablation Q1 Audit Report

**Date**: 2026-05-04  
**Plan version**: v1.4 (第四轮训练)  
**Label**: `next_high_from_close` (T+1 日内最高价 >= 收盘价 +1%)  
**Acceptance target**: Wilson 95% lower bound >= 75% on final_unseen  

---

## 1. Audit Checks

### 1.1 Data Split Confirmation

| Segment | Range | Status |
|---------|-------|--------|
| Train | 2023-05-01 ~ 2025-12-31 | PASS |
| Q1 seen_research | 2026-01-05 ~ 2026-03-30 (55 trading days) | PASS |
| April reserved holdout | 2026-04-01 ~ 2026-04-30 | **NOT TOUCHED** |
| Forward final_unseen | TBD | NOT TOUCHED |

### 1.2 min_phase_days_3 Verification

All 4 runs: `result.short_filter.min_phase_days_3 = 1` (from artifact.json).  
Previous 8 runs with inconsistent mpd3 values (baseline=1, others=2) declared **作废**.

**Status**: PASS

### 1.3 C001 / C010 Absence Confirmation

| Factor | Column | Status | In any feature manifest | Reason |
|--------|--------|--------|------------------------|--------|
| C001 | `tushare_mf_flow_intensity` | `implementation_blocked` | **No** | Requires real daily `amount` — tushare `daily` API not in cache |
| C010 | `tushare_float_relative_impact` | `implementation_blocked` | **No** | Requires real daily `volume` — tushare `daily` API not in cache |

**Status**: PASS

### 1.4 C004 Status

| Factor | Column | In features | Selected | Note |
|--------|--------|-------------|----------|------|
| C004 | `tushare_ff_adjusted_flow` | **No** (all 4 runs) | No | Added to `TUSHARE_FACTOR_COLUMNS` but never injected into any variant's monkey-patch feature list |

C004 was computed in `free_data_factors.py` post-merge but never appeared in any run's feature manifest because it was not included in `TUSHARE_TIER1_FEATURES` or any B-group tuple.

---

## 2. Run Summary

| Field | baseline | tier1 | B0 | B1 |
|-------|----------|-------|-----|-----|
| **run_id** | `bf2da25f` | `5e9e07fd` | `c42c8e4f` | `41d4ad1d` |
| **variant** | baseline_expanded_no_cross | tushare_tier1_available | tier1_plus_b0_c011 | tier1_plus_b1_c009_c011 |
| **feature_set** | expanded | research | research | research |
| **used_factor_ids** | [] | [] | [C011] | [C009, C011] |
| **model** | gpu_lightgbm_wide | gpu_lightgbm_wide | gpu_lightgbm_wide | stacking_average_top3 |
| **model_kind** | lightgbm | lightgbm | lightgbm | ensemble_average |
| **features_in_manifest** | 352 | 372 | 374 | 376 |
| **selected_features** | 260 | 260 | 260 | 260 |
| **tushare_selected** | 0 | 9 | 10 | 11 |
| **test_rows** | 42,975 | 43,025 | 43,025 | 43,025 |
| **test_days** | 55 | 55 | 55 | 55 |
| **test_symbols** | 2,523 | 2,523 | 2,523 | 2,523 |
| **train_rows** | 291,180 | 297,711 | 297,711 | 297,711 |
| **overall_accuracy** | 65.50% | 65.72% | 65.79% | 65.07% |
| **hc_accuracy** | 72.55% | 73.58% | 73.89% | 73.06% |
| **hc_count** | 9,242 | 9,697 | 9,544 | 8,489 |
| **feature_hash** | `a97cd5fe` | `7df0edde` | `c5ce36ac` | `d096e087` |
| **data_hash** | `4fc6c454` | `52ca221f` | `6634c7b2` | `6634c7b2` |
| **split_hash** | `3f96b325` | `f877fdd2` | `f877fdd2` | `f877fdd2` |

### 2.1 C-Factor Presence per Run

| Factor | Column | baseline | tier1 | B0 | B1 |
|--------|--------|----------|-------|-----|-----|
| C001 | tushare_mf_flow_intensity | - | - | - | - |
| C004 | tushare_ff_adjusted_flow | - | - | - | - |
| C009 | tushare_main_force_divergence | - | - | - | **in + sel** |
| C010 | tushare_float_relative_impact | - | - | - | - |
| C011 | tushare_auction_open_vwap_ratio | - | - | **in + sel** | **in + sel** |

### 2.2 Selected Tushare Features per Run

| Feature | baseline | tier1 | B0 | B1 |
|---------|----------|-------|-----|-----|
| tushare_net_mf_amount | - | sel | sel | sel |
| tushare_lg_buy_sell_ratio | - | sel | sel | sel |
| tushare_elg_buy_sell_ratio | - | sel | sel | sel |
| tushare_mf_strength | - | sel | sel | sel |
| tushare_sm_sell_pressure | - | sel | sel | sel |
| tushare_volume_ratio | - | sel | sel | sel |
| tushare_up_limit_distance | - | sel | sel | sel |
| tushare_down_limit_distance | - | sel | sel | sel |
| tushare_limit_range | - | sel | sel | sel |
| tushare_free_share | - | unsел | unsel | unsel |
| tushare_auction_open_vwap_ratio (C011) | - | - | **sel** | **sel** |
| tushare_main_force_divergence (C009) | - | - | - | **sel** |

---

## 3. Precision @ Threshold (all runs, Q1 only, 55 total days)

| Run | T | Precision | Wilson LB | Count | Hits | Active Days | Avg/AllDay |
|-----|---|-----------|-----------|-------|------|-------------|------------|
| baseline | 0.70 | 73.77% | 73.01% | 13,240 | 9,767 | 55/55 | 240.7 |
| baseline | 0.75 | **80.12%** | **78.82%** | 3,753 | 3,007 | 47/55 | 68.2 |
| baseline | 0.76 | **84.25%** | **81.46%** | 743 | 626 | 31/55 | 13.5 |
| baseline | 0.80 | 76.92% | 67.28% | 91 | 70 | 14/55 | 1.7 |
| tier1 | 0.70 | 73.35% | 72.62% | 14,414 | 10,573 | 55/55 | 262.1 |
| tier1 | 0.75 | 78.14% | 77.00% | 5,183 | 4,050 | 52/55 | 94.2 |
| tier1 | 0.76 | 81.95% | 77.88% | 399 | 327 | 14/55 | 7.3 |
| tier1 | 0.80 | 81.95%* | 77.88%* | 399* | 327* | 14/55* | 7.3* |
| B0 | 0.70 | 74.16% | 73.40% | 13,089 | 9,707 | 55/55 | 238.0 |
| B0 | 0.75 | 76.65% | 75.57% | 6,014 | 4,610 | 51/55 | 109.4 |
| B0 | 0.76 | 78.69% | 77.30% | 3,477 | 2,736 | 43/55 | 63.2 |
| B0 | 0.80 | 78.38% | 71.90% | 185 | 145 | 8/55 | 3.4 |
| **B1** | 0.70 | 74.81% | 74.07% | 13,214 | 9,886 | 55/55 | 240.3 |
| **B1** | **0.75** | **86.55%** | **84.59%** | 1,294 | 1,120 | 26/55 | 23.5 |
| **B1** | **0.76** | **86.53%** | **84.56%** | 1,292 | 1,118 | 26/55 | 23.5 |
| **B1** | **0.80** | **88.58%** | **86.02%** | 709 | 628 | 17/55 | 12.9 |

\* tier1 T>=0.76 与 T>=0.80 完全相同 (399 samples) — 概率分布在 [0.76, 0.80) 区间无样本。

---

## 4. B1 Daily TopK Cap Analysis

### 4.1 T >= 0.75 — Candidate Distribution

| Stat | Value |
|------|-------|
| Total candidates | 1,294 |
| Active days | 26 / 55 (53% zero-candidate days) |
| Min / Median / Mean / P75 / Max per active day | 1 / 4 / 49.8 / 13 / 518 |
| Top date | 2026-01-13: 518 candidates (40.0%), 455 hits (87.8%) |

| TopK Cap | Precision | Wilson LB | Count | Active Days | Avg/AllDay |
|----------|-----------|-----------|-------|-------------|------------|
| top5 | 77.01% | 67.14% | 87 | 26 | 1.58 |
| top10 | 79.29% | 71.83% | 140 | 26 | 2.55 |
| top20 | 82.86% | 77.18% | 210 | 26 | 3.82 |
| top30 | 84.81% | **80.05%** | 270 | 26 | 4.91 |
| top50 | **86.53%** | **82.76%** | 386 | 26 | 7.02 |

### 4.2 T >= 0.80 — Candidate Distribution

| Stat | Value |
|------|-------|
| Total candidates | 709 |
| Active days | 17 / 55 (69% zero-candidate days) |
| Min / Median / Mean / P75 / Max per active day | 1 / 4 / 41.7 / 25 / 324 |
| Top date | 2026-01-13: 324 candidates (45.7%), 287 hits (88.6%) |

| TopK Cap | Precision | Wilson LB | Count | Active Days | Avg/AllDay |
|----------|-----------|-----------|-------|-------------|------------|
| top5 | 83.05% | 71.54% | 59 | 17 | 1.07 |
| top10 | 86.02% | 77.54% | 93 | 17 | 1.69 |
| top20 | 88.11% | 81.79% | 143 | 17 | 2.60 |
| top30 | 88.83% | **83.53%** | 188 | 17 | 3.42 |
| top50 | **90.00%** | **85.65%** | 250 | 17 | 4.55 |

### 4.3 TopK 特征说明

精度随 cap 增大而**递增** (counterintuitive)。原因：每日 top-ranked 候选来自低精度的稀疏日（少量候选），而大批量候选来自高精度集中日 (如 2026-01-13: 518 candidates, 87.8% hit rate)。TopK cap 的作用不是「只留最好」而是「限制单日风险暴露」。

---

## 5. B1 Candidate Concentration

| Metric | T>=0.75 | T>=0.80 |
|--------|---------|---------|
| Active days / Total days | 26 / 55 | 17 / 55 |
| Zero-candidate days | 53% | 69% |
| Max single-day candidates | 518 (2026-01-13) | 324 (2026-01-13) |
| Top date % of total | 40.0% | 45.7% |
| Top date hit rate | 87.8% (455/518) | 88.6% (287/324) |

---

## 6. Pre-locked April Holdout Rules

以下规则在进入 April holdout 前锁定，不可追溯修改：

### Rule A (主规则)
- **Variant**: B1 (`tier1_plus_b1_c009_c011`)
- **Run ID**: `gpu_probe_20260503T170747Z_41d4ad1d`
- **Threshold**: T >= 0.75
- **Daily cap**: top 50
- **Q1 参考**: precision=86.53%, Wilson=82.76%, N=386, 26 active days, 7.02/day

### Rule B (严格规则)
- **Variant**: B1 (`tier1_plus_b1_c009_c011`)
- **Run ID**: `gpu_probe_20260503T170747Z_41d4ad1d`
- **Threshold**: T >= 0.80
- **Daily cap**: top 50
- **Q1 参考**: precision=90.00%, Wilson=85.65%, N=250, 17 active days, 4.55/day

### Observation (观察组)
- **Variant**: B1 (`tier1_plus_b1_c009_c011`)
- **Threshold**: T >= 0.75
- **Daily cap**: top 30
- **Q1 参考**: precision=84.81%, Wilson=80.05%, N=270, 26 active days, 4.91/day

---

## 7. Blockers & Open Items

| Item | Status | Note |
|------|--------|------|
| C001 implementation | Blocked | 需要 tushare `daily` API 的 `amount` 字段 |
| C010 implementation | Blocked | 需要 tushare `daily` API 的 `volume` 字段 |
| C004 not in any run | Info | 已加入 TUSHARE_FACTOR_COLUMNS 但未加入 monkey-patch feature list，需要决定是否纳入 |
| B2/B3 variants | Blocked | 依赖 C001/C010 |
| April holdout | **待确认** | 需用户授权后方可执行 |
| Forward final_unseen | 未开始 | April 通过后进入 |

---

*Generated from artifact.json + test_predictions.parquet of each run. Not committed. Not pushed. No acceptance claim made.*
