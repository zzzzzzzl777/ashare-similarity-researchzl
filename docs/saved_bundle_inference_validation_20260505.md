# Saved Bundle Inference Validation Report

**Date**: 2026-05-05  
**Bundle**: `gpu_probe_20260505T113406Z_bb25159b/model_bundle.pt`  
**Script**: `scripts/predict_with_saved_bundle.py`  
**Status**: Bundle 加载/推理正常，**无法严格复现同 run 输出**（缺 raw test feature matrix）

---

## 1. Bundle 加载检查

| 项目 | 值 | 预期 | 结果 |
|------|-----|------|------|
| torch.load 成功 | Yes | Yes | PASS |
| bundle_version | 1 | 1 | PASS |
| model_kind | ensemble_average | ensemble_average | PASS |
| model_name | stacking_average_top3 | stacking_average_top3 | PASS |
| members 数量 | 3 | 3 | PASS |
| member_names | gpu_lightgbm_wide, gpu_lightgbm_compact, gpu_lightgbm | — | PASS |
| calibration_used | isotonic | isotonic | PASS |
| threshold | 0.52 | 0.52 | PASS |
| feature_names 长度 | 376 | 376 | PASS |
| selected_feature_names 长度 | 260 | 260 | PASS |
| mean shape | [1, 376] | [1, 376] | PASS |
| std shape | [1, 376] | [1, 376] | PASS |
| selected_indices shape | [260] | [260] | PASS |
| iso_model 反序列化 | IsotonicRegression | IsotonicRegression | PASS |
| LightGBM 成员反序列化 | 3x LGBMClassifier | — | PASS |
| Bundle 加载耗时 | 0.56s | — | — |

---

## 2. 严格复现状态：不可达

### 原因

同 run 的 artifact **未保存 raw test feature matrix**（57167 行 × 376 列原始特征张量）。

虽然同 run 使用的 feature cache parquet 仍存在于磁盘 (`gpu_probe_features_665406333a7e545d.parquet`, 414MB)，但：

1. **行序不匹配**：pipeline 内部对 test 数据的行序不同于 feature cache 原始行序（经过 shuffle/sampling）
2. **无法按 test_row_id 对齐**：test_predictions.parquet 中的 test_row_id (0..57166) 对应 pipeline 内部 DataFrame 行序，而非 feature cache 行序
3. **(symbol, date) merge 不严格**：test_predictions 存在 336 行 duplicate (symbol, date)，merge 会产生歧义

### 结论

**无法做完整外部复现。只能做 bundle 文件加载检查 + 基于 (symbol, date) 唯一对的近似验证 + 候选导出。**

不允许用近似验证冒充严格复现。

---

## 3. 近似验证结果（非严格复现）

方法：对 (symbol, date) 唯一对子集（56831 行, 覆盖 99.41%）执行 merge 后推理对比。

| 指标 | 值 | 说明 |
|------|-----|------|
| 对比行数 | 56,831 / 57,167 | 排除 336 行 duplicate (symbol, date) |
| 覆盖率 | 99.41% | — |
| 完全匹配行数 | 56,810 (99.96%) | diff == 0.0 |
| max_abs_diff | 2.07e-3 | 来自 merge 歧义 |
| mean_abs_diff | 6.36e-8 | — |
| diff > 1e-6 行数 | 19 | — |
| diff > 1e-4 行数 | 5 | — |
| **严格通过 (max < 1e-6)** | **否** | 因为 merge 歧义导致 19 行错位 |

### 差异分析

19 行差异不是 bundle 推理错误，而是验证方法（merge）的歧义：当 feature cache 中同一 (symbol, date) 存在多行时，merge 可能匹配到不同行的特征值。

证据：
1. 同 run 自验证（positional alignment）max_abs_diff = **0.0**（完全精确）
2. 99.96% 行 diff = 0，说明推理链完全正确
3. 5 个最大差异行均为已知 duplicate-adjacent 区域

**Bundle 推理逻辑验证为正确。差异来源是验证方法的局限性。**

---

## 4. 2026-04-30 候选不可生成

| 事实 | 说明 |
|------|------|
| Feature cache 最后 event date | 2026-04-29 |
| 2026-04-30 行数 | **0** |
| 是否可生成 4/30 entry 候选 | **否** |
| 原因 | feature cache 按 label_date <= 2026-04-30 构建，最后 event date 为 2026-04-29 |
| 正确做法 | 如需 4/30 入场候选，需重新构建 4/30 特征（本次不做） |

---

## 5. VOID 文件

| 文件 | 状态 | 原因 |
|------|------|------|
| `C:\Users\zzzzzzl\Desktop\saved_bundle_candidates_20260430.csv` | **VOID / 错名** | 文件名标注 20260430 但内容是 2026-04-29 entry 候选。不应使用。 |
| `C:\Users\zzzzzzl\Desktop\saved_bundle_candidates_20260429_replay.csv` | **VOID / 旧版** | 旧版脚本生成，缺 name 列。已被新版替代。 |

---

## 6. 正确候选文件

| 项目 | 值 |
|------|-----|
| 文件 | `C:\Users\zzzzzzl\Desktop\saved_bundle_candidates_20260429.csv` |
| event_date (特征日期) | 2026-04-29 |
| entry_date (T日尾盘买入) | 2026-04-29 |
| label_date (T+1验证) | 2026-04-30 |
| 总候选 | 792 |
| 超阈值 (≥0.52) | 493 |
| Top-1 probability | 0.7425 |
| mode | replay (使用完整收盘后缓存) |
| name 列补全率 | **99.9%** (791/792) |
| 数据来源 | 本地 tushare cache (limit_list_d + stk_surv + ccass_hold + hk_hold) |

CSV 列: `rank, symbol, name, date, entry_date, label_date, probability, threshold, close, turnover, limit_up_like, mode`

---

## 7. 推理耗时拆分

### Cold Start（首次加载）

| 步骤 | 耗时 | 占比 |
|------|------|------|
| Bundle 加载 (torch.load + pickle) | 0.019s | 7.9% |
| Feature 读取 (parquet 单日) | 0.203s | 83.9% |
| 过滤 | 0.001s | 0.2% |
| Feature 提取 | 0.001s | 0.2% |
| 归一化 | 0.000s | 0.1% |
| 特征选择 | 0.000s | 0.0% |
| 模型预测 (3x LightGBM) | 0.018s | 7.4% |
| Isotonic 校准 | 0.000s | 0.0% |
| **总计** | **0.242s** | **100%** |

### Warm Cache（bundle 已加载）

| 步骤 | 耗时 | 占比 |
|------|------|------|
| Feature 读取 | 0.188s | 89.5% |
| 模型预测 | 0.020s | 9.5% |
| 其他 | 0.002s | 1.0% |
| **总计** | **0.210s** | **100%** |

### 重要说明

**以上耗时仅代表从已有 parquet 缓存读取特征的速度，不代表真实 14:57 实时数据构建的速度。** 真实 14:57 场景需要从行情 API 实时构建 376 个特征，耗时未知。

---

## 8. 后续要做 14:57 realtime-dry-run 还缺什么

| 缺失项 | 说明 | 优先级 |
|--------|------|--------|
| akshare 实时数据源 | 9 组 tushare 盘后因子（~24 特征）在 15:00 后更新，需 akshare 替代 | P0 |
| 实时 feature 构建管线 | 从分钟线/实时行情实时构建 376 特征的函数 | P0 |
| stk_limit 数据 | 涨跌停信息需收盘后才有 | P1 |
| daily_basic 数据 | free_share 等需盘后更新 | P1 |
| 14:57 可用特征评估 | 评估 24 个不可用特征置零后对预测质量的影响 | P1 |
| 股票名称映射维护 | 当前 99.9% 覆盖，但新股/更名需定期刷新 | P2 |

---

## 9. 脚本防护机制

| 防护 | 实现 |
|------|------|
| target-date 无数据 | 报 FATAL 退出，不生成空/错名文件 |
| output-csv 日期不匹配 | 报 ERROR 退出，需 `--allow-mismatched-output-name` 覆盖 |
| name 列 | 从本地缓存补充，无网络调用 |
| entry_date 语义 | entry_date = target_date = event date（T日尾盘买入） |
| label_date 语义 | 自动从 feature cache 的 label_date 列获取（T+1 验证日期） |

---

## 10. 明确声明

1. **不 claim 严格复现** — 缺少 raw test feature matrix，merge 方法有歧义
2. **不 claim 14:57 实盘可用** — 耗时测试仅基于 parquet cache，非实时构建
3. **Bundle 推理逻辑验证为正确** — 同 run 自验证 max_abs_diff=0.0
4. **2026-04-30 候选不可生成** — feature cache 无 2026-04-30 数据
5. **saved_bundle_candidates_20260430.csv 是错名文件** — 标记 VOID
6. **不 commit / 不 push**

---

## 11. 产出文件

| 文件 | 路径 | 状态 |
|------|------|------|
| 推理脚本 | `scripts/predict_with_saved_bundle.py` | 有效 |
| 本报告 | `docs/saved_bundle_inference_validation_20260505.md` | 有效 |
| 验证 JSON | `E:\...\saved_bundle_inference_validation_20260505.json` | 有效 |
| 正确候选 CSV | `C:\Users\zzzzzzl\Desktop\saved_bundle_candidates_20260429.csv` | **有效** |
| Name 缓存 | `scripts/_symbol_name_cache.json` | 辅助文件 |
| 错名候选 CSV | `C:\Users\zzzzzzl\Desktop\saved_bundle_candidates_20260430.csv` | **VOID** |
| 旧版候选 CSV | `C:\Users\zzzzzzl\Desktop\saved_bundle_candidates_20260429_replay.csv` | **VOID** |
