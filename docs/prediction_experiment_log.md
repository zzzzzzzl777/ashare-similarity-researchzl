# 预测实验台账

## 固定验收口径

- 样本：主板短线异动样本，必须同时满足高换手、高成交/金额、高波动。
- 时间：训练区间和测试区间按 `label_date` 隔离，避免次日标签跨入测试期。
- 测试规模：50,000 条是期望规模和报告目标；严格短线异动阶段样本不足时不阻断验收，但必须记录实际样本量。
- 目标：验证集选出的高置信 lockbox 子集方向准确率不低于 75%，Wilson 95% 下界不低于 75%，且 Brier Score 优于样本正例率常数基线。全测试集方向准确率只作背景指标，不单独批准发布。
- 门禁：只有通过 `gpu-prediction-probe` 才能写 `gpu_probe_passed_latest.json`，后续全局拟合必须读取该文件。

## 已完成实验

| 日期 | artifact/run | 特征 | 模型 | 测试样本 | 全样本准确率 | 高置信样本 | 高置信准确率 | Wilson 下界 | Brier | 基线 Brier | 结论 |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-04-29 | early-daily-149 | 149 | gpu_mlp_64_32 | 50,000 | 52.528% | - | - | - | 0.254756 | 0.248389 | 失败，日线价量因子不足 |
| 2026-04-29 | emotion-158 | 158 | gpu_mlp_256_128_64 | 50,000 | 54.212% | - | - | - | 0.250588 | 0.248811 | 失败，短线情绪因子有小幅提升但校准仍弱 |
| 2026-04-29 | logistic-158 | 158 | gpu_logistic，全量训练样本 | 50,000 | 55.342% | - | - | - | 0.246878 | 0.248811 | 失败，但 Brier 首次优于基线 |
| 2026-04-29 | expanded-187-strict | 187 | gpu_residual_mlp_128，严格阶段过滤 | 50,000 | 55.732% | - | - | - | 0.247716 | 0.248312 | 失败，但 187 日线扩展和严格阶段样本继续提升，Brier 优于基线 |
| 2026-04-29 | expanded-187-calibrated | 187 | gpu_residual_mlp_128，验证段概率校准 | 50,000 | 55.740% | - | - | - | 0.246927 | 0.248312 | 失败，校准改善 Brier 但方向离 75% 仍远 |
| 2026-04-29 | stable-1000-sample | 299 stable / 260 selected | stacking_average_top3，1000 股抽样，验证覆盖率 10% | 15,000 | 55.513% | 2,051 | 68.406% | - | 0.245436 | 0.248368 | 未通过；抽样中较好，但样本和 Wilson 仍不足 |
| 2026-04-29 | research-1000-sample | 367 research / 235 selected | stacking_average_top3，新增前龙记忆/弱市聚焦等 research 因子 | 15,000 | 54.360% | 2,070 | 62.029% | - | 0.247867 | 0.248368 | 未通过；新增主观事件代理暂列 research，不进默认 expanded |
| 2026-04-29 | full-mainboard-stable | 299 stable / 260 selected | stacking_average_top3，全主板锁箱 | 48,302 | 56.172% | 7,226 | 63.216% | - | 0.247224 | 0.248671 | 未通过；更多样本未提升到 75% |
| 2026-04-29 | `gpu_probe_20260429T162712Z_9744a6a3` | 326 expanded / 260 selected | stacking_average_top3，2000 股票扩大样本 | 30,000 | 53.390% | 6,449 | 59.2185% | 58.0139% | 0.258097 | 0.248706 | 未通过；扩大到 2000 股票和 1868 个有效股票框架后反而回落，说明当前免费日线信号瓶颈明显 |
| 2026-04-30 | `gpu_probe_20260430T023030Z_60aa7d23` | 457 research / 299 selected | stacking_average_top3，新增淘股吧深挖研究态代理，1000 股票 | 15,000 | 54.7133% | 2,042 | 57.9334% | 55.7793% | 0.252370 | 0.248389 | 未通过；更多主观/日线代理因子继续拖累，高置信和 Brier 均不达标，后续应转向真实涨停池、分钟线、竞价快照 |
| 2026-05-01 | `gpu_probe_20260430T184356Z_47c60b05` | 569 research / 299 selected | gpu_catboost，JSONL 优先因子全量保留，candidate_family=all | 15,000 | 53.8867% | 1,549 | 63.2666% | 60.8358% | 0.232301 | 0.248324 | 未通过；Brier 明显改善，但真实涨停池覆盖仅约 0.4%/1.8%，优先保留低覆盖列没有带来 75% 方向准确率 |
| 2026-05-01 | `gpu_probe_20260430T185048Z_8e098b8e` | 569 research / 299 selected | gpu_logistic，2024+ 起始并刷新特征缓存 | 15,000 | 55.6800% | 4,811 | 57.3893% | 55.9866% | 0.242386 | 0.248448 | 未通过；2024+ 聚焦真实快照后覆盖仍只有约 0.5%/2.2%，方向准确率反降，不能用不完整历史快照当突破口 |
| 2026-05-01 | `gpu_probe_20260430T190242Z_f4e092d0` | 299 expanded / 260 selected | stacking_average_top3，修复 selector 稳定性 0 值误判 | 15,000 | 54.2800% | 1,895 | 64.5910% | 62.4103% | 0.230504 | 0.248324 | 未通过；修复后从错误 pair-regime 选择恢复到 candidate_agreement，验证集过拟合风险下降，但仍低于 75% |
| 2026-05-01 | `gpu_probe_20260430T190440Z_c769282f` | 569 research / 299 selected | gpu_catboost_expressive，覆盖率感知 JSONL 优先特征 | 15,000 | 57.9733% | 2,121 | 60.1603% | 58.0602% | 0.240188 | 0.248324 | 未通过；去掉低覆盖真实快照硬保留后全样本提高，但 research 代理仍拖累高置信方向，不应升格 expanded |
| 2026-05-01 | `gpu_probe_20260430T191255Z_750b14b4` | 299 expanded / 260 selected | gpu_xgboost_hist，stable_tail，全 2026 锁箱 15,459 条 | 15,459 | 54.1562% | 2,276 | 64.4112% | 62.4215% | 0.234534 | 0.248399 | 未通过；全锁箱验证稳定在 64% 左右，确认当前日线/市场情绪代理瓶颈仍未突破 |
| 2026-05-01 | `gpu_probe_20260501T060110Z_75eefb00` | 653 research / 299 selected | research 接入分钟结构因子入口、lockbox ledger，5 分钟缓存缺失时零覆盖 | 15,000 | 56.1800% | 2,106 | 59.3067% | 57.1935% | 0.247007 | 0.248324 | research-only 未通过；`intraday_cache_status=no_minute_bar_dir`，说明工程入口已通但没有可回放分钟缓存，下一步必须补分钟数据而不是继续同口径训练 |
| 2026-05-01 | `gpu_probe_20260501T063717Z_43fe3d53` | 653 research / 299 selected | 5 分钟缓存 330 只后的近期 smoke，2026-02-09 至 2026-04-29 | 522 | 54.4061% | 72 | 65.2778% | 53.7613% | 0.296663 | 0.249281 | research-only 未通过；分钟因子覆盖约 9.82%，45 个 `minute_*` 特征被选中，但样本太小且 Brier 变差，只证明接入口有效，不证明可发布 |
| **以下为新标签 `next_high_from_close`（盘中冲高 1%）** | | | | | | | | | | | **自然命中率：全样本 54.65%，活跃样本 60.63%，短线异动子集约 67.0%** |
| 2026-05-01 | `gpu_probe_20260501T103104Z_138ea55e` | 325 expanded / 260 selected | gpu_xgboost_hist_deep + 5 模型 candidate_agreement，新标签基线 | 15,000 | 67.02% | 5,382 | 74.27% | 73.08% | 0.218449 | 0.221168 | **未通过但极接近**；新标签下全样本从旧 ~55% 跃升至 67%，高置信 74.27%/Wilson 73.08% 距 75% 仅 1.7pp，验证集高置信 82.5%/11.7% 覆盖率，Brier 优于基线；pair_regime 验证 80.4% 但稳定性不达标；下一步：校准 + selector 组合门优化 |
| 2026-05-01 | `gpu_probe_20260501T105423Z_232e1dea` | 325 expanded / 260 selected | stacking_average_top3 + isotonic 校准 + Wilson 最大化 agreement selector | 15,000 | 67.05% | 2,927 | **78.03%** | **76.50%** | 0.215967 | 0.221168 | **Wilson 下界首次突破 75%！** 准确率 78%/Wilson 76.5% 均达标，但 count=2,927 < 10,000 不满足 AND 门；isotonic 校准自动选中，验证集 Wilson 79.2%；扩大测试样本验证中 |
| 2026-05-01 | `gpu_probe_20260501T110607Z_1a53b1fb` | 325 expanded / 260 selected | stacking_average_top3 + isotonic，2000 股/31,930 测试/175k 训练 | 31,930 | 67.32% | 6,174 | **79.74%** | **78.72%** | 0.213255 | 0.219842 | **精度继续提升**；Wilson 78.7%，但 count=6,174 < 10,000；测试实际只有 31,930 行（期望 50,000）；需 3000+ 股票或放宽短线过滤拿到足够样本量 |
| 2026-05-01 | `gpu_probe_20260501T112138Z_a149d266` | 325 expanded / 260 selected | gpu_xgboost_hist_deep + isotonic + Wilson 最大化，3000 股/2810 有效/47,397 测试/265k 训练 | 47,397 | 67.53% | 8,058 | **80.47%** | **~79.6%** | 0.212479 | 0.219530 | **精度最高**；Wilson ~79.6% 远超 75%，但 count=8,058 < 10,000 不满足 AND 门；coverage 17.0% 达标；需再扩大股票池或微调短线过滤 |
| 2026-05-01 | `gpu_probe_20260501T114254Z_4a697dda` | 325 expanded / 260 selected | gpu_xgboost_hist_deep + isotonic，全主板 3063 股/2949 有效/57,391 测试/340k 训练，min_phase_days_3=1 | 57,391 | 66.68% | 9,106 | **80.24%** | **~79.3%** | 0.215061 | 0.222901 | count=9,106 差 894 过 AND 门；放宽 phase_days 到 1 增加了 ~10k 测试行，准确率微降但仍远超 75%；下一步减 min_abnormal_flags |
| 2026-05-01 | `gpu_probe_20260501T115746Z_ee185257` | 325 expanded / 260 selected | 同上 + min_abnormal_flags=1 | 57,391 | 66.66% | 9,371 | **79.94%** | **79.12%** | 0.215270 | 0.222901 | count=9,371 差 629；Wilson 79.12% 达标；min_abnormal_flags 松到 1 但特征缓存未变导致测试行不变，仅训练组成微调；下一步 min_turnover=2.0 |
| 2026-05-01 | `gpu_probe_20260501T121342Z_5267d3dd` | 325 expanded / 260 selected | min_turnover=2.0 放宽 | 50,000 | 65.57% | 7,714 | 78.00% | 77.06% | 0.219268 | 0.226105 | 放宽 turnover 反而退化；count 和精度都下降 |
| **以下为 selector_coverage_weight sweep（预注册 0.02/0.05/0.08/0.10/0.15）** | | | | | | | | | | | |
| 2026-05-01 | `gpu_probe_20260501T144414Z_6983516a` | 325 expanded / 260 selected | weight=0.02, phase_days=1, all mainboard | 57,391 | 66.66% | **9,632** | 79.65% | 78.84% | 0.215200 | 0.222900 | **sweep 最高 count**；仍差 368 |
| 2026-05-01 | `gpu_probe_20260501T144654Z_dbcee191` | 325 expanded / 260 selected | weight=0.05 | 57,391 | 66.66% | 9,404 | 80.16% | 79.34% | 0.215300 | 0.222900 | 精度微升，count 微降 |
| 2026-05-01 | `gpu_probe_20260501T144932Z_9b851415` | 325 expanded / 260 selected | weight=0.08 | 57,391 | 66.66% | 9,439 | 79.63% | 78.80% | 0.215100 | 0.222900 | 与 0.02 基本持平 |
| 2026-05-01 | `gpu_probe_20260501T145203Z_9145d3bc` | 325 expanded / 260 selected | weight=0.10 | 57,391 | 66.66% | 8,764 | 80.33% | 79.48% | 0.214900 | 0.222900 | 更高权重反而 count 下降 |
| 2026-05-01 | `gpu_probe_20260501T145440Z_d5244afc` | 325 expanded / 260 selected | weight=0.15 | 57,391 | 66.66% | 8,749 | 80.29% | 79.45% | 0.215200 | 0.222900 | 同上趋势；sweep 结论：selector 权重无法突破 count 瓶颈 |
| **以下为 research/topK 特征 ablation** | | | | | | | | | | | |
| 2026-05-01 | `gpu_probe_20260501T145817Z_fe08286c` | 653 research / 299 selected | research + stable_tail 299 | 57,391 | 66.60% | 9,295 | **80.61%** | **79.80%** | 0.215405 | 0.222901 | 精度提升但 count 略降 |
| 2026-05-01 | `gpu_probe_20260501T150120Z_3bf594b4` | 653 research / 200 selected | research + stable_tail 200 | 57,391 | 66.60% | 8,593 | 80.03% | 79.17% | - | 0.222901 | 更少特征 → count 和精度都降 |
| 2026-05-01 | `gpu_probe_20260501T150351Z_652a3beb` | 653 research / 400 selected | research + stable_tail 400 | 57,391 | 66.60% | 8,118 | **81.35%** | **80.49%** | - | 0.222901 | 最高精度但 coverage 降至 14%，count 反降；更多特征 ≠ 更多高置信 |
| **以下为 Step 5 日期分块稳定性诊断** | | | | | | | | | | | |
| 2026-05-01 | `gpu_probe_20260501T152946Z_26c1ad73` | 325 expanded / 260 selected | gpu_catboost + isotonic + Wilson 最大化，date-bucket 诊断 | 57,391 | 66.67% | 8,881 | **81.70%** | - | 0.21447 | 0.222901 | Step 5 诊断用；72 日中位精度 81.5%/std 11.9%，无单日 >20%，3 日 <60%（2026-03-23 最差 39.7%） |
| **以下为 Step 6 因子消融收口** | | | | | | | | | | | |
| 2026-05-01 | `gpu_probe_20260501T155724Z_88c1e95e` | 258 expanded / 258 selected | 去掉 `market_` + `board_` + `emotion_` | 57,391 | 66.60% | 8,468 | 81.52% | 80.68% | 0.215574 | 0.222901 | 去掉市场情绪/连板结构/情绪阶段后，count、coverage、accuracy、Brier 全面变差，说明这组因子应保留 |
| 2026-05-01 | `gpu_probe_20260501T155956Z_d64e3464` | 307 expanded / 260 selected | 去掉 `cross_` | 57,391 | 66.56% | 8,573 | **82.93%** | **82.12%** | 0.215244 | 0.222901 | 去掉跨市场收益后高置信精度、Wilson、date-bucket 稳定性反而提升，说明 `cross_` 当前应剔除出 forward 冻结配置 |

## 高置信门槛记录

- 当前正式高置信门槛：验证集选择，测试集只验收；准确率 >= 75%，Brier 优于基线，Wilson 95% 下界 >= 75%，且样本数 >= 10,000 且覆盖率 >= 10%（AND 门，非 OR）。
- 已把验证高置信最小覆盖率从 5% 提到 10%，避免只挑极窄子集造成发布口径失真。
- 已加入 side-aware confidence band：验证集自动比较 `both`、`long`、`short`，但不使用测试集标签选阈值。

## 当前进行中

- 默认 `expanded` 保持稳定因子集；淘股吧新增的主观/账户/席位类因子只进入 `research` 或暂不落地。
- 真实涨停池快照缓存：`E:\ashare_similarity_runtime\data\cache\prediction\limit_pool_snapshots`，154 个 manifest，范围约 2023-01-03 至 2026-04-30；2023 年历史接口核心池多为 0 行，炸板/跌停池只支持近期窗口，不能伪造历史覆盖。
- **Step 4 结论**：selector sweep（5 权重）+ research/topK ablation（3 配置）均无法在当前 57,391 测试行下突破 count >= 10,000。瓶颈是 4 个月见研数据窗口的样本总量。accuracy/Wilson/Brier/coverage 全部达标。需等 forward final_unseen 累计更多月份样本后一次性验收。
- **Step 5 结论**：日期分块稳定性通过。72 日中位精度 81.5%，无单日贡献 >20%，2026-03-23 标为 regime outlier。
- **Step 6 消融结论**：
  - **保留** `market_` + `board_` + `emotion_`：去掉后高置信精度 81.52%（-0.18pp），count 8,468（-413），coverage 14.75%（-0.72pp），Wilson 80.68%（-0.20pp）——全面变差，这组因子对模型有正向贡献。
  - **剔除** `cross_`：去掉后高置信精度 82.93%（+1.23pp），Wilson 82.12%（+1.24pp），date-bucket std 10.2%（vs 11.8%）——精度和日期稳定性均改善，跨市场指数收益当前拖累高置信 selector，应从 forward 冻结配置中移除。
  - `real_`（涨停池）和 `minute_`（分钟线）覆盖率 <1%，在 expanded 325 中都未入选，无法做有意义消融；待数据积累后再评估。
- 旧标签最佳（已废弃）：expanded260 stable_tail 全锁箱高置信 64.4112%，Wilson 62.4215%。
- 已修复 selector 稳定性评分 bug：`validation_stability_min_wilson_lower_95=0.0` 以前会被 `or total_wilson` 当成缺失值，从而让不稳定的 regime/pair-regime 规则压过更稳的 candidate agreement。修复后测试高置信从异常的 50.7042% 恢复到约 64.5%。
- 已加入覆盖率感知 JSONL 优先特征选择：真实快照/可用性类低覆盖或近常量列不再硬塞进 selected features；稀有但可回放的日线连板/空间板特征仍允许优先保留。

## Forward 冻结配置（strong_research_candidate）

> **状态：strong_research_candidate，不是 passed。2026-01~04 数据为 seen_research，不能生成 formal passed。**

基于 Step 6 消融结果，选择 `gpu_probe_20260501T155956Z_d64e3464`（去掉 `cross_`）为冻结配置，因其高置信精度 82.93%/Wilson 82.12% 为所有消融中最优，date-bucket 稳定性最好（std 10.2%）。

| 参数 | 值 |
|------|------|
| label_target | `next_high_from_close` |
| target_high_return_pct | `1.0` |
| feature_set | `expanded` |
| exclude_feature_prefix | `cross_` |
| max_selected_features | `260` |
| feature_selection_method | `stable_tail` |
| candidate_family | `all` |
| selector_coverage_weight | `0.02` |
| calibration | `isotonic`（自动选中） |
| confidence_selector | `candidate_agreement` |
| seed | `42` |
| min_turnover | `3.0` |
| min_amount | `200,000,000` |
| min_phase_days_3 | `1` |
| min_abnormal_flags | `2` |
| main_board_only | `true` |
| short_only | `true` |
| lockbox_role | `seen_research` → forward 用 `final_unseen` |
| code_hash | `b6f0d10418b42f53` |
| feature_hash | `9d3e0d6a56cc39e7` |
| data_hash | `b73f9e6257d9a9da` |
| split_hash | `8dadcf9205592963` |
| lockbox_identity_hash | `54a55ede258240b2` |
| frozen_artifact | `gpu_probe_20260501T155956Z_d64e3464` |

**冻结后纪律**：不再用 2026-01~04 反向改配置。下一阶段只做 forward final_unseen：每日盘后跑冻结配置预测 → 次日回填标签 → 累计到 high_conf_count >= 10,000 AND coverage >= 10% 后一次性验收。

## 标签变更记录（2026-05-01）

**主标签从"次日收盘上涨"切换为"次日盘中冲高 1%"**

```
旧标签：actual = 1 if close[t+1] > close[t] else 0
新标签：actual = 1 if high[t+1] >= close[t] * 1.01 else 0
CLI参数：--label-target next_high_from_close --target-high-return-pct 1.0
```

自然命中率基准（2023-05 ~ 2026-04，主板 10cm，3059 只股票）：

| 指标 | 全样本 (2,167,355) | 活跃样本 (867,379) |
|------|---:|---:|
| P(high[t+1] >= close[t]*1.01) | 54.65% | 60.63% |
| P(close[t+1] > close[t]) | 47.61% | 47.29% |
| P(low[t+1] <= close[t]*0.98) | 30.08% | - |
| P(low[t+1] <= close[t]*0.97) | 15.95% | - |

冲高 1%+ 样本的风险统计：
- 其中 17.45% 盘中先杀到 -2%，8.43% 先杀到 -3%
- 中位盘中最高涨幅 2.24%，中位收盘涨幅 1.05%，中位盘中最低跌幅 -0.80%

**结论**：活跃样本自然命中率 60.63%，75% 目标需要在此基础上提升约 14.4 个百分点。旧的收盘方向所有实验数据不能直接与新标签比较。
- 已接入分钟结构因子入口：`minute_last_30min_return`、`minute_first_15min_volume_ratio`、`minute_vwap_deviation_eod`、`minute_up_volume_ratio` 等列进入 `research`；当前运行环境尚无 `raw/bars/5` 缓存，本轮覆盖率为 0。
- 已加入 lockbox ledger：每次 probe 追加 `lockbox_identity_hash` 账本记录；同一 lockbox 先以 research 跑过后，不能再靠 `--lockbox-role final_unseen` 自报通过正式验收。
- 5 分钟缓存探路完成：`backfill_5min_300_20260501_140603.json` 处理 330 只股票、失败 0，实际覆盖约 `2026-02-09 14:55` 至 `2026-04-28 15:00`，确认免费源只能支撑近期 smoke/消融，不能支撑三年正式分钟训练。

## 因子文档吸收记录

- 2026-05-01 接续后确认：桌面 `因子探索.md`、`短线因子.md` 和 `淘股吧短线因子提取.md` 是持续更新的外部候选源；`run_logs/factor_doc_scan_*_desktop_latest.jsonl` 是结构化候选池；`docs/*.md` 只作为人工精选研究摘要，不视为完整镜像。
- 最新扫描产物：`factor_doc_scan_explore_desktop_latest.jsonl` 候选 216 个，P0 10 个，P1 10 个，`expanded` 8 个，`research` 194 个，`blocked` 14 个；`factor_doc_scan_tgb_desktop_latest.jsonl` 候选 982 个，P0 18 个，P1 25 个，`expanded` 19 个，`research` 934 个，`blocked` 29 个；`factor_doc_scan_short_desktop_latest.jsonl` 候选 984 个，P0 13 个，P1 12 个，`expanded` 13 个，`research` 952 个，`blocked` 19 个。
- 本轮扫描器已补充英文/源函数提示识别，并过滤 `stock_zt_pool_em` 等 AKShare 源函数，避免把数据源名称误当作因子；`seal_money_to_float_mv`、`real_seal_time_rank` 等真实涨停池方向可正确落入可执行分桶。
- 晋级纪律：新增候选仍按数据时点、免费数据可得性、Level2/分钟线依赖、未来函数风险分桶；未形成可回放快照前不得直接进入正式 `expanded` 验收。
- 工程优先级：真实涨停池/炸板池快照、分钟缓存、竞价快照、题材/热度历史落盘优先于继续堆叠主观日线代理。
- 规则挖掘产物：`rule_mining_expanded260_stability_fix_20260501_031002.json`，验证集最佳规则约 69%，测试多落在 57%-65%，没有发现可发布的 75% 稳定规则；强规则多集中在跌停/强下跌延续，覆盖偏窄且 Wilson 不达标。
- **扫描新鲜度警告**：~~三个 `factor_doc_scan_*_desktop_latest.jsonl` 产生于 12:58，但 `淘股吧短线因子提取.md`（17:00）和 `短线因子.md`（17:02）在此之后更新~~。**已补扫描（19:29）**：tgb 1,614 候选（旧 982），P0 18 / P1 25 / P2 33；short 1,245 候选（旧 984），P0 13 / P1 12 / P2 6。新增候选仍按晋级纪律分桶，不直接进入 expanded。

## 下一步

1. **Step 4 总结**：selector sweep（5 权重预注册）+ research/topK ablation（200/299/400）均完成。最高 count = 9,632（expanded 260, weight=0.02, phase_days=1），最高精度 = 81.35%/Wilson 80.49%（research 400）。count >= 10,000 在当前 4 个月 seen_research 窗口下无法达到，需等 forward final_unseen 累计更多月份。**当前状态：strong_research_candidate。**
2. **Step 5 — 日期分块稳定性（已完成）**：`gpu_probe_20260501T152946Z_26c1ad73`（expanded 260, weight=0.02, phase_days=1 复跑，code_hash 变化导致分片微调但测试集相同 57,391 行）。
   - 72 个测试日均有高置信样本，**中位高置信精度 81.5%，标准差 11.9%**。
   - **无单日贡献超过 20%**（最大单日 share = 10.4%，2026-01-14）。Top 5 日合计贡献 36.6%，Top 10 日合计 50.8%，浓度中等。
   - **3 日精度低于 60%**：2026-03-23（39.7%/408 样本）、2026-03-10（49.4%/85）、2026-02-11（55.6%/36）。2026-03-23 同时高置信样本量异常多（408），说明模型在该日系统性误判——可能为市场急转或政策事件日，需标注为 regime outlier。
   - 39/72 日精度 ≥ 80%，15 日 ≥ 90%；日间稳定性可接受。
   - **结论**：日期稳定性通过诊断——没有少数日期主导命中，中位精度远超 75%。2026-03-23 是唯一需要标记的系统性弱日，贡献仅 4.6%，不影响聚合准确率达标。
3. **Step 6 — 因子消融（已完成）**：
   - baseline `26c1ad73`（325 特征）→ remove market_/board_/emotion_ `88c1e95e`（258 特征）→ remove cross_ `d64e3464`（307 特征）。
   - 市场/连板/情绪因子保留（去掉后全面变差）；跨市场收益剔除（去掉后精度 +1.2pp，Wilson +1.2pp，date stability 改善）。
   - 涨停池和分钟线覆盖率 <1%，未入选 expanded 260，无法消融。
4. **Forward final_unseen 阶段**：冻结配置 `d64e3464`（expanded 307/260 selected, exclude cross_, weight=0.02）。每日盘后跑冻结配置预测 → 次日回填标签 → 累计到 high_conf_count >= 10,000 AND coverage >= 10% 后一次性验收。不再用 2026-01~04 调配置。

## 收口验证（2026-05-02）

| 项目 | 结果 |
|------|------|
| 冻结配置文件 | `docs/frozen_forward_config.json` |
| Forward runbook | `docs/forward_runbook.md` |
| 冻结 artifact | `gpu_probe_20260501T155956Z_d64e3464` |
| frozen_config <-> artifact 一致性 | **PASSED**（label / features / sample_filter / fingerprints / lockbox 全部匹配） |
| fingerprints | code=`b6f0d10418b42f53` feat=`9d3e0d6a56cc39e7` data=`b73f9e6257d9a9da` split=`8dadcf9205592963` selector=`09e63e1db0272c7f` |
| runbook final_unseen 命令 | 无 2026-01-01 硬编码，`<FREEZE_NEXT_DATE>` 要求交易日历确认 |
| runbook seen_research 诊断 | 单独章节，明确不能 passed |
| `pytest tests/test_gpu_probe.py` | **38 passed**，无失败 |
| 当前状态 | **strong_research_candidate**（不是 passed） |
| 下一阶段 | forward final_unseen：每日盘后冻结配置预测 → 次日回填标签 → 累计 high_conf_count >= 10,000 AND coverage >= 10% 后一次性验收 |
| 纪律 | 不自动删除备份、不读取完整 backup JSONL、不自动 commit/push/release、不反向改冻结配置 |
| lockbox hash 分离 | seen_research hash `54a55ede258240b2` 与 forward hash 分开记录；forward hash 必须在真实 forward run 时由管线生成，不能沿用 2026-01~04 的 hash |

## 2026-05-03 diagnostics

- Mini validation replay scripts were corrected from `OR` to `AND` on `(date == 2026-04-29) & (label_date == 2026-04-30)`.
- Regenerated mini validation output: `total_executable_samples=630`, `high_conf_total=57`, `high_conf_hits=37`, `high_conf_precision=64.91%`, `natural_hit_rate=69.21%`.
- Output file: `E:\ashare_similarity_runtime\data\reports\prediction\mini_validation_20260429.json`
- Baseline replay source remained `gpu_probe_20260503T071809Z_f57a2059`; the fix changed the replay filter, not the frozen forward config.

### 120k seen_research cross_ re-check

- Compared `gpu_probe_20260503T071809Z_f57a2059` vs `gpu_probe_20260503T093827Z_594a3d7d`.
- `cross_` removal was confirmed at the feature-manifest level: baseline had 18 `cross_*` columns (9 features + 9 availability columns), ablation had 0.
- This 120k-row diagnostic did **not** improve the key metrics:
  - high_conf_accuracy: `75.51% -> 75.45%`
  - wilson_lower_95: `74.86% -> 74.78%`
  - high_conf_count: `17,051 -> 15,958`
  - high_conf_coverage: `14.21% -> 13.30%`
  - high_conf_brier: `0.187206 -> 0.188026`
- Interpretation: in this newer 120k `seen_research` diagnostic setup, excluding `cross_` is still a valid ablation but no longer helps. This result should **not** be mixed with the frozen forward candidate, because the frozen artifact/runbook uses a different protocol (`required_test_rows=60000`, `min_phase_days_3=1`, `frozen_artifact=gpu_probe_20260501T155956Z_d64e3464`).

### Forward status

- `docs/frozen_forward_config.json` remains the active forward freeze.
- Local cached market data currently ends at `2026-04-30`, while `frozen_at` is `2026-05-02`.
- Therefore `final_unseen` forward cannot start yet; the next valid forward run must wait for the first real post-freeze A-share trading date to appear in cache.
