# 14:57 实时候选操作台 API 契约

日期：2026-05-11
版本：v1.0

## 端点

### GET /
HTML 主页面。

### GET /api/status
返回三种模式的当前状态。

**响应结构**：
```json
{
  "formal": { ...ModeState },
  "postclose": { ...ModeState },
  "test": { ...ModeState }
}
```

**ModeState 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| run_id | string\|null | 运行 ID（YYYYMMDD_HHMMSS） |
| status | string | idle / running / completed / failed / stopped / skipped / stopping |
| message | string | 状态文案 |
| logs | string[] | 运行日志（最近 500 行） |
| today | string | 目标交易日 YYYY-MM-DD |
| target_time | string | 目标时间 HH:MM |
| no_wait | bool | 是否立即执行 |
| test_mode | bool | 是否测试模式 |
| prob_threshold | float | 概率阈值 |
| topk | int | Top K |
| started_at | string\|null | 开始时间 ISO |
| ended_at | string\|null | 结束时间 ISO |
| returncode | int\|null | 进程退出码 |
| cmd | string\|null | 执行命令 |
| elapsed_sec | float\|null | 运行中时已用秒数 |
| outputs | OutputBundle | 产出数据 |

**OutputBundle 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| paths.full_csv | string\|null | 全量概率 CSV 路径 |
| paths.selector_csv | string\|null | 候选 CSV 路径 |
| paths.timing_json | string\|null | 耗时 JSON 路径 |
| paths.report_md | string\|null | 报告 MD 路径 |
| summary | Summary | 摘要数据 |
| candidates | Row[] | 候选行（最多 200） |
| top_rows | Row[] | 全量概率前列（最多 100，tradable only） |
| timing | object | 原始 timing JSON |

**Summary 字段**：

| 字段 | 类型 | 说明 | 模式 |
|------|------|------|------|
| target_date | string | 目标日期 | all |
| generated_at | string\|null | 生成时间 | all |
| asof_time | string\|null | 快照时间 | all |
| status | string\|null | live 状态 | all |
| warmup_sec | float\|null | 预热秒数 | all |
| live_sec | float\|null | live 阶段秒数 | all |
| within_180s | bool\|null | 是否 180s 内完成 | all |
| top_probability | float\|null | 最高概率 | all |
| total_stocks | int\|null | 总股票数 | all |
| candidates_raw | int\|null | 原始候选数 | all |
| selector_rule | string | 选择规则 | all |
| selector_count | int\|null | 选中数 | all |
| selector_top_probability | float\|null | 选中最高概率 | all |
| run_mode | string\|null | formal/postclose/test | all |
| is_formal_valid | bool\|null | formal 验证通过 | formal |
| formal_valid_reason | string\|null | formal 验证原因 | formal |
| snapshot_time_status | string\|null | 快照时间状态 | formal |
| snapshot_quote_min | string\|null | 快照最早 quote_time | formal |
| snapshot_quote_max | string\|null | 快照最晚 quote_time | formal |
| snapshot_captured_at | string\|null | 快照捕获时间 | formal |
| limit_pool_time_status | string\|null | 涨跌停池状态 | formal |
| output_grade | string\|null | 输出等级 | all |
| universe_counts | object\|null | 宇宙计数 | all |
| market_context_injected | bool\|null | 市场上下文注入 | all |
| saved_snapshot_used | bool\|null | 是否用已存快照 | formal |
| is_postclose_complete | bool\|null | postclose 完整 | postclose |
| postclose_incomplete_reasons | string[]\|null | 不完整原因 | postclose |
| postclose_data_fetch_time | string\|null | 数据获取耗时 | postclose |
| postclose_snapshot_source | string\|null | 快照来源 | postclose |
| postclose_checks | object\|null | postclose 检查项 | postclose |
| hard_moneyflow_selected_count | int | 硬资金流特征数 | all |
| postclose_forbidden_selected_count | int | 盘后禁止特征数 | all |
| ths_selected_count | int | THS 特征数 | all |
| has_c004 | bool | C004 是否选中 | all |
| has_c009 | bool | C009 是否选中 | all |
| selected_feature_count | int | 选中特征总数 | all |

### POST /api/run
启动正式跑。

**请求体**：RunRequest
```json
{
  "today": "2026-05-11",
  "target_time": "14:57",
  "no_wait": true,
  "test_mode": false,
  "prob_threshold": 0.75,
  "topk": 6
}
```

**约束**：
- today 必须是今天
- target_time >= 14:57（除非 test_mode）
- 14:57 前 + no_wait=true + !test_mode → 拒绝
- 已有 formal 进程运行中 → 409

### POST /api/postclose-run
启动收盘验证。

**约束**：
- today 必须是今天
- 当前时间 >= 15:00
- 已有 postclose 进程运行中 → 409

### POST /api/test-run
启动测试跑。

**约束**：
- 已有 test 进程运行中 → 409

### POST /api/stop
停止指定模式的运行。

**请求体**：
```json
{ "mode": "formal" }
```
mode: formal | postclose

### GET /api/latest?today=YYYY-MM-DD
获取指定日期三种模式最新产出。

## Formal 安全门槛

正式候选必须满足所有条件：
- run_mode == "formal"
- status == "ok"
- is_formal_valid == true
- output_grade 不含 "approximated" 或 "test"
- snapshot_time_status == "within_window"
- hard_moneyflow_selected_count == 0
- postclose_forbidden_selected_count == 0
- ths_selected_count == 0
- has_c004 == false
- has_c009 == false

任何一项不满足，UI 不得展示为"正式候选有效"。
