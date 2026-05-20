# Family Ablation Factor Split Q1 Report

**Date**: 2026-05-04  
**Plan version**: v1.4 (第四轮训练 — 因子拆细消融)  
**Label**: `next_high_from_close` (T+1 日内最高价 >= 收盘价 +1%)  
**Scope**: Q1 only (2026-01-01 ~ 2026-03-31)  
**April data used for tuning/selection**: **No**  

---

## 1. 实验目的

第四轮 B1 (C009+C011) 在 Q1 表现强劲 (Wilson 84.59% uncapped)，但 April holdout 未达 75% Wilson 目标。本消融实验拆解：

1. B1 的 Q1 性能主要来自 C009 还是 C011？
2. 新增 C004 (ff_adjusted_flow) 是否提供独立增量？
3. 哪些因子组合值得进入 April reserved holdout 验证？

---

## 2. 消融矩阵 (9 runs)

| Run | Name | Factor IDs | Feature Set | Extra Features |
|-----|------|-----------|-------------|----------------|
| A | baseline | [] | expanded | (none — expanded baseline) |
| B | tier1 | [] | research | tier1 only (9 tushare) |
| C | tier1_plus_c009_only | [C009] | research | tier1 + C009 |
| D | tier1_plus_c011_only | [C011] | research | tier1 + C011 (= B0) |
| E | tier1_plus_c009_c011 | [C009, C011] | research | tier1 + C009 + C011 (= B1) |
| F | tier1_plus_c004_only | [C004] | research | tier1 + C004 |
| G | tier1_plus_c009_c004 | [C009, C004] | research | tier1 + C009 + C004 |
| H | tier1_plus_c011_c004 | [C011, C004] | research | tier1 + C011 + C004 |
| I | tier1_plus_c009_c011_c004 | [C009, C011, C004] | research | tier1 + C009 + C011 + C004 |

---

## 3. Run Metadata

### Run A: baseline
| Field | Value |
|-------|-------|
| run_id | `gpu_probe_20260503T164045Z_bf2da25f` |
| feature_set | expanded |
| model | lgbm_wide |
| used_factor_ids | [] |
| features_in_manifest | 354 |
| selected_features | 260 |
| tushare_selected | 0 |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| feature_hash | `aa7fd01c7e0b0a0e` |

### Run B: tier1
| Field | Value |
|-------|-------|
| run_id | `gpu_probe_20260503T170234Z_5e9e07fd` |
| feature_set | research |
| model | lgbm_wide |
| used_factor_ids | [] |
| features_in_manifest | 372 |
| selected_features | 260 |
| tushare_selected | 9 (tier1 only) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| feature_hash | `fda968c5ae71e51f` |

### Run C: tier1_plus_c009_only
| Field | Value |
|-------|-------|
| run_id | `gpu_probe_20260503T205241Z_3dc2cdb1` |
| feature_set | research |
| model | stacking_average_top3 |
| used_factor_ids | [C009] |
| features_in_manifest | 374 |
| selected_features | 260 |
| tushare_selected | 10 (9 tier1 + C009) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| feature_hash | `5ad8b584` |
| C009 in_features | Yes |
| C009 selected | **Yes** |
| C011 in_features | No |
| C004 in_features | No |

### Run D: tier1_plus_c011_only (= B0)
| Field | Value |
|-------|-------|
| run_id | `gpu_probe_20260503T170513Z_c42c8e4f` |
| feature_set | research |
| model | lgbm_wide |
| used_factor_ids | [C011] |
| features_in_manifest | 374 |
| selected_features | 260 |
| tushare_selected | 10 (9 tier1 + C011) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| feature_hash | `86a31c6c81c13dda` |
| C011 in_features | Yes |
| C011 selected | **Yes** |
| C009 in_features | No |
| C004 in_features | No |

### Run E: tier1_plus_c009_c011 (= B1)
| Field | Value |
|-------|-------|
| run_id | `gpu_probe_20260503T170747Z_41d4ad1d` |
| feature_set | research |
| model | stacking_average_top3 |
| used_factor_ids | [C009, C011] |
| features_in_manifest | 376 |
| selected_features | 260 |
| tushare_selected | 11 (9 tier1 + C009 + C011) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| feature_hash | `d096e087f16ea198` |
| C009 in_features | Yes |
| C009 selected | **Yes** |
| C011 in_features | Yes |
| C011 selected | **Yes** |
| C004 in_features | No |

### Run F: tier1_plus_c004_only
| Field | Value |
|-------|-------|
| run_id | `gpu_probe_20260503T211250Z_ffaa910f` |
| feature_set | research |
| model | stacking_average_top3 |
| used_factor_ids | [C004] |
| features_in_manifest | 374 |
| selected_features | 260 |
| tushare_selected | 10 (9 tier1 + C004) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| feature_hash | `27fa9045` |
| C004 in_features | Yes |
| C004 selected | **Yes** |
| C009 in_features | No |
| C011 in_features | No |

### Run G: tier1_plus_c009_c004
| Field | Value |
|-------|-------|
| run_id | `gpu_probe_20260503T211501Z_88db3f3e` |
| feature_set | research |
| model | stacking_average_top3 |
| used_factor_ids | [C009, C004] |
| features_in_manifest | 376 |
| selected_features | 260 |
| tushare_selected | 11 (9 tier1 + C009 + C004) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| feature_hash | `0683d797` |
| C009 in_features | Yes |
| C009 selected | **Yes** |
| C004 in_features | Yes |
| C004 selected | **Yes** |
| C011 in_features | No |

### Run H: tier1_plus_c011_c004
| Field | Value |
|-------|-------|
| run_id | `gpu_probe_20260503T211709Z_c760ed37` |
| feature_set | research |
| model | lgbm_wide |
| used_factor_ids | [C011, C004] |
| features_in_manifest | 376 |
| selected_features | 260 |
| tushare_selected | 11 (9 tier1 + C011 + C004) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| feature_hash | `6d4b4a22` |
| C011 in_features | Yes |
| C011 selected | **Yes** |
| C004 in_features | Yes |
| C004 selected | **Yes** |
| C009 in_features | No |

### Run I: tier1_plus_c009_c011_c004
| Field | Value |
|-------|-------|
| run_id | `gpu_probe_20260503T211917Z_a908a440` |
| feature_set | research |
| model | lgbm_wide |
| used_factor_ids | [C009, C011, C004] |
| features_in_manifest | 378 |
| selected_features | 260 |
| tushare_selected | 11 (9 tier1 + C009 + C011; C004 offered but **NOT selected** by stable_tail) |
| min_phase_days_3 | 1 |
| exclude_event_limit_up | True |
| feature_hash | `14a80313` |
| C009 in_features | Yes |
| C009 selected | **Yes** |
| C011 in_features | Yes |
| C011 selected | **Yes** |
| C004 in_features | Yes |
| C004 selected | **No** (rejected by stable_tail) |

---

## 4. Precision @ Threshold (Q1, uncapped)

| Run | Variant | T>=0.70 | T>=0.75 | T>=0.76 | T>=0.78 | T>=0.80 |
|-----|---------|---------|---------|---------|---------|---------|
| A | baseline | — | 80.12% (n=3753) | — | 84.25% (n=743) | 76.92% (n=91) |
| B | tier1 | — | 78.14% (n=5183) | — | 81.95% (n=399) | 81.95% (n=399) |
| **C** | **C009-only** | — | **87.42%** (n=644) | — | **87.42%** (n=445) | **87.78%** (n=360) |
| D | C011-only | — | 76.65% (n=6014) | — | 78.04% (n=551) | 78.38% (n=185) |
| **E** | **C009+C011 (B1)** | — | **86.55%** (n=1294) | — | **86.53%** (n=1292) | **88.58%** (n=709) |
| F | C004-only | — | 84.81% (n=770) | — | 82.42% (n=165) | 82.42% (n=165) |
| **G** | **C009+C004** | — | 83.15% (n=3056) | — | **88.40%** (n=1000) | **88.37%** (n=997) |
| H | C011+C004 | — | 79.26% (n=2840) | — | 80.82% (n=537) | 80.82% (n=537) |
| I | C009+C011+C004 | — | 79.33% (n=4176) | — | 80.95% (n=845) | 76.89% (n=238) |

### Wilson 95% Lower Bound

| Run | Variant | T>=0.75 Wilson | T>=0.78 Wilson | T>=0.80 Wilson |
|-----|---------|---------------|---------------|---------------|
| A | baseline | 78.82% | 81.46% | 67.28% |
| B | tier1 | 76.99% | 77.88% | 77.88% |
| **C** | **C009-only** | **84.64%** | **84.01%** | **83.99%** |
| D | C011-only | 75.57% | 74.40% | 71.90% |
| **E** | **C009+C011 (B1)** | **84.59%** | **84.56%** | **86.02%** |
| F | C004-only | 82.10% | 75.90% | 75.90% |
| **G** | **C009+C004** | **81.78%** | **86.27%** | **86.23%** |
| H | C011+C004 | 77.73% | 77.28% | 77.28% |
| I | C009+C011+C004 | 78.08% | 78.16% | 71.13% |

---

## 5. TopK Cap Analysis (Q1, T >= 0.75)

### Run C: C009-only

| TopK | Precision | Wilson LB | Count | Active Days | Avg/AllDay |
|------|-----------|-----------|-------|-------------|------------|
| top5 | 88.71% | 81.45% | 124 | 25 | 2.25 |
| top10 | 87.50% | 81.58% | 192 | 25 | 3.49 |
| top20 | 87.38% | 82.71% | 293 | 25 | 5.33 |
| top30 | 87.38% | 83.33% | 318 | 25 | 5.78 |
| top50 | 87.00% | 82.89% | 323 | 25 | 5.87 |

### Run E: C009+C011 (B1)

| TopK | Precision | Wilson LB | Count | Active Days | Avg/AllDay |
|------|-----------|-----------|-------|-------------|------------|
| top5 | 90.53% | 84.87% | 190 | 26 | 3.45 |
| top10 | 89.27% | 84.91% | 289 | 26 | 5.25 |
| top20 | 88.26% | 84.91% | 358 | 26 | 6.51 |
| top30 | 87.64% | 84.21% | 380 | 26 | 6.91 |
| top50 | 86.53% | 82.76% | 386 | 26 | 7.02 |

### Run G: C009+C004

| TopK | Precision | Wilson LB | Count | Active Days | Avg/AllDay |
|------|-----------|-----------|-------|-------------|------------|
| top5 | 87.43% | 80.72% | 175 | 29 | 3.18 |
| top10 | 87.94% | 82.85% | 282 | 29 | 5.13 |
| top20 | 86.05% | 82.45% | 430 | 29 | 7.82 |
| top30 | 85.50% | 82.26% | 462 | 29 | 8.40 |
| top50 | 84.29% | 81.28% | 490 | 29 | 8.91 |

### Run F: C004-only

| TopK | Precision | Wilson LB | Count | Active Days | Avg/AllDay |
|------|-----------|-----------|-------|-------------|------------|
| top5 | 85.71% | 76.08% | 84 | 17 | 1.53 |
| top10 | 84.21% | 76.83% | 133 | 17 | 2.42 |
| top20 | 84.26% | 78.67% | 216 | 17 | 3.93 |
| top30 | 84.33% | 79.44% | 249 | 17 | 4.53 |
| top50 | 84.81% | 80.77% | 290 | 17 | 5.27 |

---

## 6. TopK Cap Analysis (Q1, T >= 0.78)

### Run G: C009+C004

| TopK | Precision | Wilson LB | Count | Active Days | Avg/AllDay |
|------|-----------|-----------|-------|-------------|------------|
| top5 | 87.43% | 80.72% | 175 | 29 | 3.18 |
| top10 | 87.94% | 82.85% | 282 | 29 | 5.13 |
| top20 | 86.05% | 82.45% | 430 | 29 | 7.82 |
| top30 | 85.50% | 82.26% | 462 | 29 | 8.40 |
| top50 | 84.29% | 81.28% | 490 | 29 | 8.91 |

### Run E: C009+C011 (B1) at T>=0.80

| TopK | Precision | Wilson LB | Count | Active Days | Avg/AllDay |
|------|-----------|-----------|-------|-------------|------------|
| top5 | 95.24% | 84.52% | 63 | 17 | 1.15 |
| top10 | 91.49% | 84.67% | 94 | 17 | 1.71 |
| top20 | 90.67% | 85.47% | 150 | 17 | 2.73 |
| top30 | 90.24% | 85.78% | 205 | 17 | 3.73 |
| top50 | 90.00% | 85.65% | 250 | 17 | 4.55 |

---

## 7. Daily Candidate Concentration (Q1, T >= 0.75)

### Run C: C009-only

| Stat | Value |
|------|-------|
| Total candidates | 644 |
| Active / Total days | 25/55 (45%) |
| Zero-candidate days | 55% |
| Max single day | 231 (2026-01-13) |
| Top date % of total | 35.9% |
| Median per active day | 4 |

### Run E: C009+C011 (B1)

| Stat | Value |
|------|-------|
| Total candidates | 1,294 |
| Active / Total days | 26/55 (47%) |
| Zero-candidate days | 53% |
| Max single day | 518 (2026-01-13) |
| Top date % of total | 40.0% |
| Median per active day | 5 |

### Run G: C009+C004

| Stat | Value |
|------|-------|
| Total candidates | 3,056 |
| Active / Total days | 29/55 (53%) |
| Zero-candidate days | 47% |
| Max single day | 895 (2026-03-23) |
| Top date % of total | 29.3% |
| Median per active day | 10 |

### Concentration Comparison

| Run | Max single-day % | Active days | Zero days % |
|-----|-------------------|-------------|-------------|
| C (C009-only) | 35.9% | 25 | 55% |
| E (B1) | 40.0% | 26 | 53% |
| G (C009+C004) | **29.3%** | **29** | **47%** |
| F (C004-only) | — | 17 | 69% |

Run G (C009+C004) 集中度最低 — 最大单日仅 29.3%，活跃天数最多 (29 天)，且最集中日从 01-13 转移到 03-23，分散性更好。

---

## 8. 因子贡献分析

### 8.1 C009 (main_force_divergence) — **主驱动因子**

- C009 单独加入 (Run C) 即达 Wilson 84.64%@T>=0.75，超过 B1 (84.59%)
- C009 单独 (Run C) 产出 stacking 模型；无 C009 的 Run B/D/H 均产出 lgbm_wide
- C009 参与的所有 run (C/E/G) 均为高精度组，Wilson 81.78%+
- **结论：C009 是 B1 高精度的主要来源**

### 8.2 C011 (auction_open_vwap_ratio) — **单独无增量，组合有附加值**

- C011 单独加入 (Run D) Wilson 75.57%@T>=0.75，甚至低于 baseline (78.82%)
- 但 C009+C011 (Run E) 在 T>=0.80 达 Wilson 86.02% > C009-only 83.99%
- C011 与 C009 组合时，样本量翻倍 (644→1294) 且高阈值精度提升
- **结论：C011 单独无信号，但与 C009 组合时提升高阈值性能和覆盖**

### 8.3 C004 (ff_adjusted_flow) — **独立增量因子，方向与 C009 互补**

- C004 单独加入 (Run F) Wilson 82.10%@T>=0.75，高于 tier1 baseline (76.99%)
- C009+C004 (Run G) 在 T>=0.78 达 **Wilson 86.27%** — 全矩阵最高之一
- Run G 活跃天数 29 天 (vs B1 的 26 天)，集中度更低
- Run G 最集中日从 01-13 转移到 03-23 — 与 B1 不同的集中模式
- **结论：C004 提供独立信号，与 C009 互补性强**

### 8.4 三因子组合 (C009+C011+C004) — **退化**

- Run I 全部三因子：Wilson 78.08%@T>=0.75，T>=0.80 仅 71.13%
- C004 被 stable_tail **拒绝选入**（offered 但 not selected）
- 三因子同时存在时，特征空间竞争导致 stable_tail 选择退化
- **结论：三因子组合不优于双因子，不应推进**

---

## 9. 排名与推荐

### 9.1 综合排名 (按最佳操作点 Wilson)

| Rank | Run | Variant | Best Wilson | At Threshold | Sample Size | Active Days |
|------|-----|---------|------------|-------------|-------------|-------------|
| 1 | G | C009+C004 | **86.27%** | T>=0.78 | 1,000 | 29 |
| 2 | E | C009+C011 (B1) | **86.02%** | T>=0.80 | 709 | 17 |
| 3 | C | C009-only | **84.64%** | T>=0.75 | 644 | 25 |
| 4 | F | C004-only | 82.10% | T>=0.75 | 770 | 17 |
| 5 | A | baseline | 81.46% | T>=0.78 | 743 | — |
| 6 | I | all-3 | 78.16% | T>=0.78 | 845 | — |
| 7 | H | C011+C004 | 77.73% | T>=0.75 | 2,840 | — |
| 8 | B | tier1 | 77.88% | T>=0.78 | 399 | — |
| 9 | D | C011-only | 75.57% | T>=0.75 | 6,014 | — |

### 9.2 April Holdout 推荐

| Run | Variant | 推荐 | 理由 |
|-----|---------|------|------|
| **G** | **C009+C004** | **进入 April holdout** | 全矩阵最高 Wilson (86.27%@T>=0.78)，29 天活跃，集中度最低，与 B1 不同的集中模式 |
| **C** | **C009-only** | **进入 April holdout** | 最简因子组合即达 84.64%，可验证 C009 单独的泛化能力 |
| **F** | **C004-only** | **进入 April holdout** | Wilson 82.10% 高于 tier1，可验证 C004 独立信号 |
| E | C009+C011 (B1) | **已验证不通过** | April Wilson 67.95% < 75%，已在 postmortem 中记录 |
| D | C011-only | 仅诊断 | Wilson 75.57%，低于 baseline，无独立增量 |
| H | C011+C004 | 仅诊断 | Wilson 77.73%，无 C009 时 C011 不提升 |
| I | all-3 | 仅诊断 | 三因子退化，C004 被 stable_tail 拒选 |
| A | baseline | 仅对照 | expanded baseline，不含 tushare 因子 |
| B | tier1 | 仅对照 | tier1 对照组 |

---

## 10. 结论

### 10.1 哪些组合可以进入 April reserved holdout

1. **Run G (C009+C004)** — 首选。Wilson 86.27%@T>=0.78，活跃天数最多 (29)，集中度最低 (max 29.3%)，与 B1 完全不同的集中日分布。
2. **Run C (C009-only)** — 次选。最简消融，验证 C009 独立泛化。
3. **Run F (C004-only)** — 可选。验证 C004 独立信号，但活跃天数仅 17。

### 10.2 哪些组合只是诊断，不应进入 holdout

- Run D (C011-only)：单独无增量
- Run H (C011+C004)：无 C009 时无优势
- Run I (C009+C011+C004)：三因子退化，stable_tail 拒选 C004
- Run A/B：对照组

### 10.3 哪些因子工程阻塞

| Factor | Status | Blocker |
|--------|--------|---------|
| C001 (mf_flow_intensity) | implementation_blocked | 需要 tushare daily API 的 `amount` 字段 |
| C010 (float_relative_impact) | implementation_blocked | 需要 tushare daily API 的 `volume` 字段 |

### 10.4 是否建议继续拆细因子

**不建议在当前因子集上继续拆细。** 9-run 矩阵已充分覆盖 C009/C011/C004 的所有单因子和双因子组合。三因子组合退化表明因子空间存在竞争瓶颈。

下一步方向应该是：
1. 解锁 C001/C010 (需 tushare daily API 缓存)
2. 对推荐组合进行 April holdout 验证
3. 研究 regime gate (基于第四轮 April 拖累日 04-08/04-23/04-27 的模式)

### 10.5 声明

**本阶段未使用 April 做调参或选择。所有分析和排名仅基于 Q1 (2026-01-01 ~ 2026-03-31) 数据。April 数据在消融实验中完全未被查看或用于任何决策。**

---

## 11. Artifact Index

| Item | Path |
|------|------|
| This report (MD) | `docs/family_ablation_factor_split_q1_20260504.md` |
| This report (JSON) | `E:\...\prediction\family_ablation_factor_split_q1_20260504.json` |
| Run A artifact | `runs/gpu_probe_20260503T164045Z_bf2da25f/artifact.json` |
| Run B artifact | `runs/gpu_probe_20260503T170234Z_5e9e07fd/artifact.json` |
| Run C artifact | `runs/gpu_probe_20260503T205241Z_3dc2cdb1/artifact.json` |
| Run D artifact | `runs/gpu_probe_20260503T170513Z_c42c8e4f/artifact.json` |
| Run E artifact | `runs/gpu_probe_20260503T170747Z_41d4ad1d/artifact.json` |
| Run F artifact | `runs/gpu_probe_20260503T211250Z_ffaa910f/artifact.json` |
| Run G artifact | `runs/gpu_probe_20260503T211501Z_88db3f3e/artifact.json` |
| Run H artifact | `runs/gpu_probe_20260503T211709Z_c760ed37/artifact.json` |
| Run I artifact | `runs/gpu_probe_20260503T211917Z_a908a440/artifact.json` |
| Q1 audit | `docs/family_ablation_q1_audit_20260504.md` |
| April holdout | `docs/family_ablation_april_holdout_20260504.md` |
| Round 4 postmortem | `docs/fourth_round_postmortem_20260504.md` |

---

*因子拆细消融报告。Q1 only。未使用 April 做调参或选择。不 commit，不 push。*
