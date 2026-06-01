# Forward Final-Unseen Runbook

> 本文件定义配置冻结后的每日前向验收流程。不允许反向修改冻结配置。

## 前置条件

- 冻结配置文件：`docs/frozen_forward_config.json`
- 冻结 artifact：`gpu_probe_20260501T155956Z_d64e3464`
- 状态：`strong_research_candidate`（不是 passed）
- 2026-01~04 数据角色：`seen_research`，只能得出 `research_only` 或 `strong_research_candidate`，不能得出 `passed`

## 每日盘后流程

### 1. 数据快照（收盘后）

```
# 确认日线数据已更新到当日
# 确认涨停池/炸板池快照已捕获（如有）
# 确认分钟线缓存已更新（如有）
```

### 2. 冻结配置预测（final_unseen）

> **`--test-start` 必须是冻结配置生成之后的首个 A 股交易日，不能包含 2026-01~04。**
> 该日期不得手写假设，必须由交易日历或实际行情数据确认；2026-01~04 永远只能是 `seen_research`，不能作为 `final_unseen`。

```bash
python -c "from ashare_similarity.cli import main; import sys; sys.argv = [
    'cli', 'gpu-prediction-probe',
    '--start', '2023-05-01',
    '--train-end', '2025-12-31',
    '--test-start', '<FREEZE_NEXT_DATE>',
    '--end', '<TODAY>',
    '--feature-set', 'expanded',
    '--max-selected-features', '260',
    '--feature-selection-method', 'stable_tail',
    '--candidate-family', 'all',
    '--selector-coverage-weight', '0.02',
    '--min-phase-days-3', '1',
    '--main-board-only',
    '--test-rows', '60000',
    '--label-target', 'next_high_from_close',
    '--target-high-return-pct', '1.0',
    '--lockbox-role', 'final_unseen',
    '--exclude-feature-prefix', 'cross_',
]; main()"
```

**占位符说明**：
- `<FREEZE_NEXT_DATE>` = `frozen_forward_config.json` 中 `frozen_at` 日期之后的首个 A 股交易日。**不得写死日期**，必须查询交易日历或检查实际日线数据中冻结日之后最早可用的交易日。若冻结日当天闭市，则取之后的首个开市日。
- `<TODAY>` = 当日日期（每日盘后替换）
- `--lockbox-role final_unseen` — 只能用于冻结后新数据窗口
- 其余参数必须与 `frozen_forward_config.json` 完全一致
- **不要修改任何参数**

### 2b. 历史 seen_research 诊断（仅供回顾，不能 passed）

> 如果需要回顾 2026-01~04 的诊断结果，只能用 `seen_research`：

```bash
# 仅用于诊断目的，结论上限为 strong_research_candidate，不能得出 passed
python -c "from ashare_similarity.cli import main; import sys; sys.argv = [
    'cli', 'gpu-prediction-probe',
    '--start', '2023-05-01',
    '--train-end', '2025-12-31',
    '--test-start', '2026-01-01',
    '--end', '2026-04-29',
    '--feature-set', 'expanded',
    '--max-selected-features', '260',
    '--feature-selection-method', 'stable_tail',
    '--candidate-family', 'all',
    '--selector-coverage-weight', '0.02',
    '--min-phase-days-3', '1',
    '--main-board-only',
    '--test-rows', '60000',
    '--label-target', 'next_high_from_close',
    '--target-high-return-pct', '1.0',
    '--lockbox-role', 'seen_research',
    '--exclude-feature-prefix', 'cross_',
]; main()"
```

**注意**：此命令的 `--lockbox-role` 是 `seen_research`，`--test-start` 是 `2026-01-01`，`--end` 是 `2026-04-29`。产出结论**永远不能是 passed**。

### 3. 次日回填标签

T+1 收盘后，T 日的预测才能获得真实标签（T+1 的 high）。标签自动由管线在下一次运行时回填到 `label_date` 列。

### 4. 累计验收检查

每次运行后检查 artifact 中的 `acceptance` 字段：

```python
import json
artifact = json.load(open(r'E:\ashare_similarity_runtime\data\reports\prediction\gpu_probe_latest.json'))
result = artifact.get('result', artifact)
hc = result.get('acceptance', {}).get('high_confidence', {})
print(f"count: {hc.get('rows')}")
print(f"coverage: {hc.get('coverage')}")
print(f"accuracy: {hc.get('accuracy')}")
print(f"wilson: {hc.get('wilson_lower_95')}")
print(f"brier: {result.get('brier')} vs baseline {result.get('baseline_brier')}")
print(f"passed: {result.get('acceptance', {}).get('passed')}")
```

### 5. 验收通过条件（AND 门）

| 条件 | 要求 |
|------|------|
| high_conf_count | >= 10,000 |
| high_conf_coverage | >= 10% |
| high_conf_accuracy | >= 75% |
| wilson_lower_95 | >= 75% |
| brier | < baseline_brier |
| lockbox_role | `final_unseen` |
| no future label filter | true |
| lockbox not previously seen as research | test-start 必须在冻结日期之后，lockbox_identity_hash 不能与 seen_research 的 `54a55ede258240b2` 相同 |

**所有条件必须同时满足（AND 门）。任何一项不通过则继续累计。**

## 禁止事项

- 不允许用 2026-01~04 数据得出 `passed` 结论
- 不允许反向修改冻结配置中的任何参数
- 不允许自动删除备份目录或历史 artifact
- 不允许读取完整 backup JSONL 文件
- 不允许自动 git commit / push / release
- 不允许修改 `frozen_forward_config.json` 中的 fingerprint
- 不允许在 forward 阶段新增 sweep 或调参实验

## 预期时间线

- 当前 seen_research 每月约 14,000 条测试行（57,391 / 4 个月）
- 需要约 10,000 / (14,000 * 0.15) ≈ 4.8 个月的 forward 数据
- 预计 2026-09 ~ 2026-10 可能累计到 10,000 条高置信样本
- 如果 coverage 提升，可能更早达标

## 降级和中止条件

如果 forward 运行中出现以下情况，应标记为风险并考虑中止：

- 连续 5 个交易日高置信精度 < 50%
- 累计 Wilson 下界持续低于 70% 超过 1 个月
- Brier 持续劣于 baseline 超过 2 周
- 数据源异常（日线缺失、接口变更等）

中止后不能通过修改冻结配置来"修复"，需要重新从 Step 1 开始新一轮实验。

## 文件清单

| 文件 | 用途 |
|------|------|
| `docs/frozen_forward_config.json` | 冻结配置（机器可读） |
| `docs/forward_runbook.md` | 本文件 |
| `docs/prediction_experiment_log.md` | 实验台账 |
| `docs/factor_promotion_registry.md` | 因子晋级登记 |
| `E:\...\lockbox_ledger.jsonl` | lockbox 使用账本 |
| `E:\...\gpu_probe_latest.json` | 最新 run 指针 |
