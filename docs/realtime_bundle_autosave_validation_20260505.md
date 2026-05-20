# Bundle Auto-Save Integration — Validation Report

**Date**: 2026-05-05  
**Run ID**: `gpu_probe_20260505T113406Z_bb25159b`  
**Status**: **Self-validation PASSED (max_abs_diff = 0.0)**  
**Purpose**: 在 gpu_probe.py 主训练流程中集成 model bundle 自动保存 + 同 run 自验证

---

## 1. 实现内容

在 `src/ashare_similarity/prediction/gpu_probe.py` 中新增:

| 组件 | 位置 | 功能 |
|------|------|------|
| `_build_model_bundle_payload()` | 新增 helper | 构建 bundle payload (live objects) |
| `_validate_model_bundle()` | 新增 helper | 同 run 自验证，行序对齐 |
| `_serialize_model_bundle_to_disk()` | 新增 helper | 序列化为 .pt + meta.json + validation.json |
| Bundle construction in `_train_and_score` | line ~2275 | try/except 包裹，失败不影响训练 |
| `test_row_id` column | `_pred_df` 新增列 | 0..N-1 稳定行号 |
| Bundle write in `_write_gpu_probe_artifacts` | line ~3499 | pop payload → 写文件 → 记录 status |

---

## 2. 新 Run 结果

| 指标 | 值 |
|------|-----|
| Run ID | `gpu_probe_20260505T113406Z_bb25159b` |
| Best model | `stacking_average_top3` (ensemble_average) |
| Members | `['gpu_lightgbm_wide', 'gpu_lightgbm_compact', 'gpu_lightgbm']` |
| Calibration | isotonic |
| Threshold | 0.52 |
| Selected features | 260 / 376 |
| Test rows | 57,167 |
| Bundle size | 5.3 MB |
| Bundle path | `E:\...\runs\gpu_probe_20260505T113406Z_bb25159b\model_bundle.pt` |

---

## 3. Self-Validation Metrics

| 指标 | 值 | 通过标准 | 结果 |
|------|-----|---------|------|
| matched_rows | 57,167 | == test_predictions rows | **PASS** |
| max_abs_diff | **0.0** | < 1e-6 | **PASS** |
| mean_abs_diff | **0.0** | < 1e-7 | **PASS** |
| Top30 overlap | 100% | 100% | **PASS** |
| Top50 overlap | 100% | 100% | **PASS** |
| Top100 overlap | 100% | 100% |**PASS** |
| T≥0.75 recall | 100% | 100% | **PASS** |
| T≥0.75 jaccard | 100% | 100% | **PASS** |
| T≥0.75 count | 2,315 | — | — |
| T≥0.80 recall | 100% | 100% | **PASS** |
| T≥0.80 jaccard | 100% | 100% | **PASS** |
| T≥0.80 count | 573 | — | — |

**所有指标完全通过。bundle 推理精确复现同 run 的 test_predictions。**

---

## 4. Bundle 内容

`model_bundle.pt` (torch.save 格式) 包含:

| Key | 内容 |
|-----|------|
| `bundle_version` | 1 |
| `model_kind` | "ensemble_average" |
| `model_name` | "stacking_average_top3" |
| `member_names` | ["gpu_lightgbm_wide", "gpu_lightgbm_compact", "gpu_lightgbm"] |
| `calibration_used` | "isotonic" |
| `threshold` | 0.52 |
| `confidence_band` | {...} |
| `mean` | tensor [1, 376] |
| `std` | tensor [1, 376] |
| `selected_indices` | tensor [260] |
| `feature_names` | tuple of 376 names |
| `selected_feature_names` | tuple of 260 names |
| `members` | 3 × {model_kind, model_name, model_bytes (pickle)} |
| `iso_model_bytes` | pickled IsotonicRegression |

`model_bundle_meta.json`:
```json
{
  "bundle_version": 1,
  "model_kind": "ensemble_average",
  "model_name": "stacking_average_top3",
  "member_names": ["gpu_lightgbm_wide", "gpu_lightgbm_compact", "gpu_lightgbm"],
  "calibration_used": "isotonic",
  "threshold": 0.52,
  "selected_feature_count": 260,
  "full_feature_count": 376,
  "has_isotonic": true,
  "run_id": "gpu_probe_20260505T113406Z_bb25159b",
  "train_end": "2025-12-31",
  "test_start": "2026-01-01",
  "end": "2026-04-30",
  "feature_set": "research",
  "min_phase_days_3": 1,
  "exclude_event_limit_up": true,
  "model_bundle_status": "passed"
}
```

---

## 5. 验证方法说明

- **不使用 symbol/date merge**：验证在 `_train_and_score()` 内部，对同一 test tensor 做行序位置对齐
- **不跨 run 对比**：仅验证同一次 run 的 bundle 是否精确复现同一次 run 的 `prob` 输出
- **复用现有预测逻辑**：调用 `_predict_average_ensemble_prob()` → `_predict_candidate_prob()` → `_apply_isotonic_calibration()`
- **端到端验证**：从 raw features → normalization → feature selection → member prediction → average → isotonic，全链路对比
- `test_predictions.parquet` 新增 `test_row_id` 列 (0..57166)，供下游外部验证使用

---

## 6. 旧 Bundle 状态

| 文件 | 状态 |
|------|------|
| `bundle_G_20260505T103107Z.pt` | **VOID** — 捕获了错误模型 |
| `bundle_G_20260505T103527Z.pt` | **VOID** — calibration_used 标志错误 |
| `bundle_G_20260505T103527Z_fixed.pt` | **VOID** — 同上的修复尝试 |
| `bundle_G_20260505T103527Z_validation.json` | **VOID** — 基于错误 bundle |
| `bundle_G_20260505T103527Z_meta.json` | **VOID** — 基于错误 bundle |

**以上旧 bundle 不可使用，不引用为有效验证。**

---

## 7. 旧 G Run 不可精确复活

| 事实 | 说明 |
|------|------|
| 旧 G run | `gpu_probe_20260504T033857Z_074fe9ea` |
| 旧 G bundle | 不存在（未保存权重） |
| 重跑能否复现 | **否** — LightGBM GPU 非确定性 |
| 本次 run 与旧 G 的关系 | 同配置/同因子/同数据，但模型权重不同 |
| 正确做法 | 在训练当场保存 bundle（已实现） |

---

## 8. 明确声明

1. **这不是 passed/final** — 仅验证 bundle auto-save 工程可复现性
2. **不 claim 旧 G 可精确复活** — 旧 G 权重已永久丢失
3. **不 claim 14:57 实盘可用** — 需要后续 akshare 数据源验证
4. **不 commit/push** — 代码改动留在本地
5. **不调参/不改因子** — 使用完全相同的 G 配置

---

## 9. 输出文件

| 文件 | 路径 |
|------|------|
| 本报告 | `docs/realtime_bundle_autosave_validation_20260505.md` |
| Bundle | `E:\...\runs\gpu_probe_20260505T113406Z_bb25159b\model_bundle.pt` |
| Meta | `E:\...\runs\gpu_probe_20260505T113406Z_bb25159b\model_bundle_meta.json` |
| Validation | `E:\...\runs\gpu_probe_20260505T113406Z_bb25159b\model_bundle_validation.json` |
| Predictions | `E:\...\runs\gpu_probe_20260505T113406Z_bb25159b\test_predictions.parquet` |
| Modified code | `src/ashare_similarity/prediction/gpu_probe.py` |
| Test script | `scripts/run_bundle_autosave_test.py` |

---

*Self-validation passed。不 claim passed/final，不 commit，不 push。*
