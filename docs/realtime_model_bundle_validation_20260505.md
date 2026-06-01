# G Model Bundle Export — Validation Report

**Date**: 2026-05-05  
**Status**: **VOID — 当前 bundle 作废，不可使用**  
**Verdict**: 无法通过重跑复现旧 G 模型，必须在训练当场保存模型

---

## 1. 背景

目标：导出 G run (`gpu_probe_20260504T033857Z_074fe9ea`) 的 `ensemble_average_top3` 模型权重，
用于 14:57 实盘推理。要求 bundle 预测结果与 G run 的 `test_predictions.parquet` 一一对齐。

---

## 2. 尝试过程

### 2.1 第一次尝试 (Run 1: gpu_probe_20260505T103107Z_726ed547)

| 项目 | 结果 |
|------|------|
| Feature cache | Forced hit on `383b5a3c0e707ae9` (正确) |
| Pipeline best model | `gpu_lightgbm_wide` (单 LightGBM), score=0.859199 |
| 脚本保存的模型 | ensemble_average (强行从 hook 捕获) |
| 问题 | **Pipeline 选择了单模型，不是 ensemble；脚本保存了错误的东西** |

### 2.2 第二次尝试 (Run 2: gpu_probe_20260505T103527Z_bbfe605e)

| 项目 | 结果 |
|------|------|
| Feature cache | Forced hit on `383b5a3c0e707ae9` (正确) |
| Pipeline best model | `stacking_average_top3` (ensemble_average), score=0.858343 |
| 脚本保存的模型 | ensemble_average 3 members (正确捕获了 pipeline 选择的模型) |
| Members | `['gpu_lightgbm_wide', 'gpu_lightgbm_compact', 'gpu_lightgbm']` |
| 保存 bundle | `bundle_G_20260505T103527Z.pt` (5.3 MB) |
| Bug 1 | `calibration_used` 保存为 "platt"，实际是 "isotonic" |
| Bug 2 | 验证时 symbol/date merge 有重复行 (feature cache 有 707 重复 rows) |
| Bug 3 | 脚本 KeyError crash，未完成 validation report |

### 2.3 修正后的自验证 (Self-validation)

修正 calibration_used → "isotonic" 并去重后：

| 指标 | 值 |
|------|-----|
| matched_rows | 56,999 / 56,999 (100%) |
| mean_abs_diff | **1.36e-8** |
| max_abs_diff | **2.98e-8** |
| Pearson | 1.0000000000 |
| Top30/50/100 overlap | 100% / 100% / 100% |
| T≥0.75 recall / jaccard | 100% / 100% |
| T≥0.80 recall / jaccard | 100% / 100% |

**结论：export/inference pipeline 本身是正确的。Bundle 可以精确复现其 own source run 的预测。**

---

## 3. 与旧 G Run 的对比

Bundle (= Run 2 predictions) vs Original G Run predictions:

| 指标 | 值 |
|------|-----|
| matched_rows | 56,999 / 56,999 |
| mean_abs_diff | 0.00619 (0.62pp) |
| max_abs_diff | 0.143 (14.3pp, 1 row) |
| max_abs_diff (excl. prob=0) | 0.071 (7.1pp) |
| P95_abs_diff | 0.022 (2.2pp) |
| Pearson | 0.9938 |
| Spearman | 0.9943 |
| Top30 overlap | 83.3% |
| Top50 overlap | 80.0% |
| T≥0.75 recall (full period) | 95.4% |
| T≥0.75 jaccard (full period) | 89.8% |
| T≥0.80 recall (full period) | 96.2% |
| April T≥0.75 recall | 95.2% |
| April T≥0.80 recall | 97.4% |

**不满足验证标准：**
- 要求 max_abs_diff < 1e-4，实际 0.071
- 要求 Top30/50 100%，实际 83%/80%
- 要求 T≥0.75 candidates 100% 一致，实际 95.2%

---

## 4. 根因诊断

### 4.1 为什么重跑不能复现旧 G？

| 因素 | 影响 |
|------|------|
| LightGBM GPU 多线程非确定性 | 即使 seed=42，线程调度导致浮点累积不同 |
| 代码版本变化 | source_code_hash 不同 → forced cache workaround |
| 候选评分漂移 | 个别 LGB 候选 selection_score 变化 ±0.001 |
| Best model 选择不稳定 | Run 1 选了单 LightGBM (0.8592)，Run 2 选了 ensemble (0.8583) |
| Isotonic 曲线不同 | 验证集预测略有不同 → isotonic fit 不同 → 高概率区 7pp 偏差 |

### 4.2 关键证据

```
                     Original G       Run 1         Run 2
Best model:          ensemble         lightgbm_wide ensemble
Ensemble score:      0.858590         (not best)    0.858343
Top LGB score:       0.856969         0.859199      0.856290
Feature selection:   260 features     260 features  260 features (100% same)
Train/valid split:   211014/86124     211014/86124  211014/86124 (identical)
Post-calibration:    isotonic         isotonic      isotonic
```

- Feature selection 100% 一致 (260/260)
- 数据 split 完全相同 (211,014 / 86,124)
- XGBoost / CatBoost / Torch candidates 分数完全一致
- **仅 LightGBM candidates 有浮点差异** (GPU 多线程不确定性)
- 差异通过 isotonic 非线性映射被放大

### 4.3 不可修复

这不是 bug，是 LightGBM GPU 训练的 **固有特性**：
- 已知 issue：https://github.com/microsoft/LightGBM/issues/3255
- 多线程直方图构建的浮点求和顺序不同
- `deterministic=True` 选项会大幅降低性能
- 即使用 `deterministic=True`，跨代码版本仍无法保证

---

## 5. 结论

### 5.1 当前 Bundle 状态

| Bundle | 状态 | 原因 |
|--------|------|------|
| `bundle_G_20260505T103107Z.pt` | **作废** | 捕获了错误模型 (ensemble，而非 pipeline 选择的 lightgbm_wide) |
| `bundle_G_20260505T103527Z.pt` | **作废** | 虽然 pipeline 选择了 ensemble 且自验证通过，但不等于旧 G |

### 5.2 核心判定

**无法通过重跑保证复现旧 G 模型。**

- Export/inference pipeline 本身没有 bug（自验证 max_diff=3e-8）
- 但 "重跑 → 捕获" 的方法论有根本缺陷：重跑得到的模型不是旧 G
- LightGBM GPU 非确定性使得任何重跑都会得到一个 **相似但不相同** 的模型
- Isotonic 非线性映射放大了底层微小差异

### 5.3 正确路径

**以后训练必须当场保存模型。** 具体要求：

1. `run_gpu_next_day_probe()` 完成后，立即 export best candidate 的完整权重
2. Bundle 内容：member models + mean/std + selected_indices + isotonic model + threshold + config
3. Bundle 验证：立即对 test_df 做推理，与 pipeline 输出一一对齐（max_diff < 1e-6）
4. Bundle 与 test_predictions.parquet 一起保存在 run 目录下

**当前不要继续尝试 export 旧 G。不要继续 14:57 工程化直到有正确 bundle。**

---

## 6. 下一步建议

| 工作项 | 优先级 | 说明 |
|--------|--------|------|
| 在 pipeline 中添加 bundle auto-save | P0 | 训练完成即 export，不留"事后补导"的窗口 |
| 训练新一轮 G 模型 (with bundle) | P0 | 重跑相同配置，当场保存 bundle |
| 验证新 bundle predictions | P0 | 确保 max_diff < 1e-6 |
| 新 bundle 通过后，继续 14:57 工程化 | P1 | 不再需要 "复现旧 G" |

---

## 7. 附录：文件路径

| 项目 | 路径 |
|------|------|
| Original G run | `E:\...\runs\gpu_probe_20260504T033857Z_074fe9ea` |
| Run 1 (best=lightgbm_wide) | `E:\...\runs\gpu_probe_20260505T103107Z_726ed547` |
| Run 2 (best=ensemble) | `E:\...\runs\gpu_probe_20260505T103527Z_bbfe605e` |
| Bundle 1 (VOID) | `E:\...\realtime_model_bundles\bundle_G_20260505T103107Z.pt` |
| Bundle 2 (VOID) | `E:\...\realtime_model_bundles\bundle_G_20260505T103527Z.pt` |
| Feature cache | `E:\...\feature_cache\gpu_probe_features_383b5a3c0e707ae9.parquet` |
| Export script | `scripts\export_and_validate_bundle.py` |
| Self-validation script | `scripts\validate_bundle_self.py` |

---

*当前 bundle 作废。不 claim passed，不 claim final，不 commit，不 push。*
*下一步：在 pipeline 加入 bundle auto-save → 重训 → 当场验证 → 再启 14:57 工程化。*
