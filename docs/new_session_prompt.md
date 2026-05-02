你的任务是为 A 股短线 T+1 预测系统拉取 Tushare 历史数据并构造新因子。

## 第一步：读取上下文（必须全部读完再动手，不要跳过任何一个）

1. `C:\Users\zzzzzzl\Desktop\subagent\docs\tushare_data_handoff.md` — **最重要的文件**，包含 Tushare 连接信息、全部 API 可用性测试结果、每个 API 的返回字段、因子-API 映射、数据存储规范、运行环境、已有数据盘点、API 调用注意事项、因子接入管线位置。这个文件是上一个会话花了大量时间验证和编写的，所有技术细节以这个文件为准。
2. `C:\Users\zzzzzzl\Desktop\股票预测模型（1）.md` — 执行计划，定义了预测目标、验收标准、核心原则。
3. `C:\Users\zzzzzzl\Desktop\subagent\docs\frozen_forward_config.json` — 冻结配置，**不能修改其中任何参数**。
4. `C:\Users\zzzzzzl\Desktop\subagent\docs\prediction_experiment_log.md` — 实验台账，了解已完成的实验和当前状态。

读完这四个文件后，先用 check-key 检查 Tushare Key 是否仍然有效（方法见 handoff 文档 §16）。如果 Key 已过期，告诉我，不要继续。

## 第二步：拉取数据

按 handoff 文档 §4 的优先级顺序拉取：P0（moneyflow、limit_list_d、top_list + top_inst）→ P1（hk_hold、margin_detail、ths_hot + ths_daily + ths_member）→ P2（daily_basic、cyq_perf）→ P3。

要求：
- `scripts/pull_tushare_moneyflow.py` 已写好，可以直接运行 moneyflow 的拉取。其他 API 参考 handoff §7 的模板编写脚本。
- 数据存到 `E:\ashare_similarity_runtime\data\cache\prediction\tushare\` 下对应子目录，目录已建好。
- 很多 API 已经完成或正在运行，开拉前必须先检查对应目录的 `_pull_log.json`、parquet 数量和当前 Python 进程，避免重复启动同类任务。
- 每个 API 拉完后立刻验证数据：读取几个 parquet 检查行数、列名、日期范围是否正确。
- 拉取间隔 >= 0.55 秒，连续 5 次错误停止。
- **不要用 Tushare 拉日线（daily）**，项目中已有 5327 只日线 parquet。

## 第三步：构造因子

数据拉完后，按 handoff §4 中列出的"可构造因子"逐个实现：
- 所有因子名以 `tushare_` 为前缀。
- 因子代码写入 `src/ashare_similarity/prediction/free_data_factors.py`。
- 每个因子必须报告覆盖率（非 NaN 占比），覆盖率 <30% 只能标记为 smoke。
- 只进 `research` 因子集，不进 `expanded`。
- 注意 handoff §14 中的单位换算（moneyflow 万元 vs daily 千元，比值 10 倍）和格式解析（first_time HHMMSS、up_stat "2/3"）。

## 第四步：跑消融实验

因子接入后，用 `--feature-set research` 跑 `gpu-prediction-probe`，对比有无 Tushare 因子的差异。结果记录到 `docs/prediction_experiment_log.md`。

## 绝对不能做的事

1. 不能修改 `docs/frozen_forward_config.json` 中的任何参数
2. 不能把新因子加入 `expanded` 因子集
3. 不能用 2026-01~04 数据得出 `passed` 结论
4. 不能自动 git commit / push（需要我确认）
5. 不能删除任何已有数据或备份
6. 不能拉取 15min/30min/60min 分钟线；`stk_mins` 的 1min/5min 已复测可用但仍需等拉取、merge、verify 完成后才能用于正式消融
7. 不能用 Tushare 重拉已有的日线数据

补充口径（2026-05-02 二次审计）：`stk_auction_o` / `stk_auction_c` 竞价接口已可用且已有历史 parquet；相关因子只能进入 `research`，不能影响冻结 forward 配置。

## 工作目录

核心仓库：`C:\Users\zzzzzzl\Desktop\subagent\`
运行数据：`E:\ashare_similarity_runtime\`

先读完上面四个文件，然后告诉我你的理解和执行计划，等我确认后再开始拉数据。
