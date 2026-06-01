# 14:57 As-Of Replay Check — Run G (C009+C004)

**Date**: 2026-05-05  
**Run**: gpu_probe_20260504T033857Z_074fe9ea  
**Purpose**: 验证 G 模型在"14:55 可见特征"下的预测稳定性  
**Verdict**: 证据不足，不能 claim 可以实盘使用

---

## 1. 数据源

| 数据源 | 内容 | 覆盖 |
|--------|------|------|
| stk_mins_5 (tushare 5min bars) | 679 symbols × April 2026 | 23.4% of test rows |
| Feature cache (383b5a3c0e707ae9) | 385,622 rows, 795 cols | 100% |
| G run test_predictions.parquet | 13,401 April rows, 1,954 symbols | 100% |

**关键覆盖缺口**: 5-min bar 数据仅覆盖 679 个标的，而 G 模型 April 测试集包含 1,954 个标的。T≥0.75 候选票中仅 30% (37/125) 有 5-min 数据。

---

## 2. Raw OHLCV 差异 (14:55 vs 15:00 收盘)

基于 13,137 个 symbol-date 快照 (628 symbols × 21 days):

| 指标 | Close | Volume | Amount |
|------|-------|--------|--------|
| Mean | -0.030% | -2.82% | -2.82% |
| |Mean| | 0.130% | 2.82% | 2.82% |
| Median | 0.000% | -2.60% | -2.61% |
| P95 (abs) | 0.398% | 5.03% | 5.03% |
| Max (abs) | 3.279% | 84.2% | 84.2% |

- Close 在 14:55 与收盘的偏差中位数为 0（多数时候 14:55 最新价 = 收盘价）
- Volume 和 Amount 在 14:55 时约为最终值的 97%（最后 5 分钟含集合竞价贡献约 3%）
- Max close diff 3.28% 来自极端集合竞价波动（极少数情况）

---

## 3. 特征扰动方法

### 3.1 使用的模型

**不是 G 模型本身。** 由于 G 模型权重未保存，使用 LightGBM 单模型作为代理：
- 相同训练集 (300K rows, train_end=2025-12-31)
- 相同 260 selected features
- 相同 normalization (mean/std from train)
- **NOT** the ensemble_average_top3 architecture

代理模型的预测分布与 G 模型不同，precision 数字不可直接对比。但**排序稳定性**和**相对变化**是有参考价值的。

### 3.2 扰动覆盖

| 类别 | 特征数 | 说明 |
|------|--------|------|
| 已扰动 (close-dependent) | 43 | ret_1, close_position, RSI, MACD, etc. |
| 已扰动 (volume-dependent) | 16 | volume_z, volume_chg, etc. |
| 已扰动 (amount-dependent) | 8 | amount_z, amount_chg, etc. |
| 已扰动 (turnover-dependent) | 10 | turnover, turnover_z, etc. |
| **已扰动合计** | **77** | 有重叠 (ret1_x_volume_z5 同时在 close 和 volume 列表) |
| 应扰动但未扰动 | 24 | ret_std_5, range_pct, body_pct, atr_14_pct, etc. |
| 不需要扰动 (Category A) | 60 | lag features, calendar, gap, overnight_return |
| 市场/板块/截面 (正确) | 74 | market_*, cs_*, sector_*, prev_* |
| **Moneyflow (不可用)** | **7** | tushare_net_mf_amount 等 (无日内历史) |
| tushare_volume_ratio | 1 | 可从 pytdx 计算但此处未做 |

**扰动不完整**: 77/260 已扰动，另有 24 个 close/volume 依赖特征未扰动。实际影响被低估。

### 3.3 扰动方法的局限性

- Close-dependent: 使用 additive shift `feature += (close_1455/close_final - 1)`
- Volume-dependent: 使用 multiplicative `feature *= (vol_1455/vol_final)`
- 这是**一阶近似**，对非线性特征 (RSI, Bollinger, etc.) 不精确
- 正确做法是从修改后的 OHLCV 重新计算所有特征，但需要完整 pipeline 运行 (~20min)

---

## 4. 预测对比结果 (仅在有 5-min 数据的 3,376 行上)

### 4.1 Probability 差异

| 指标 | 值 |
|------|-----|
| mean_abs_diff | 0.0063 (0.63pp) |
| median_abs_diff | 0.0036 (0.36pp) |
| P95_abs_diff | 0.0222 (2.22pp) |
| P99_abs_diff | 0.0364 (3.64pp) |
| max_abs_diff | 0.0649 (6.49pp) |
| Pearson correlation | 0.9964 |
| Spearman correlation | 0.9959 |

### 4.2 Top-N 排名重合度

| 指标 | 值 |
|------|-----|
| Top30 overlap (global) | 100% |
| Top50 overlap (global) | 100% |
| Top100 overlap (global) | 97% |
| Daily top-10 overlap (mean) | 95.0% |
| Daily top-10 overlap (min) | 80% (2026-04-10) |

### 4.3 阈值候选重合度

| 阈值 | 原始候选数 | as-of 候选数 | Recall | Jaccard |
|------|-----------|-------------|--------|---------|
| ≥0.60 | 2253 | 2257 | 98.4% | 96.8% |
| ≥0.65 | 1761 | 1744 | 97.6% | 96.1% |
| ≥0.70 | 1195 | 1197 | 97.3% | 94.6% |
| ≥0.75 | 688 | 692 | 97.2% | 94.1% |
| ≥0.80 | 320 | 320 | 96.2% | 92.8% |

### 4.4 Precision 对比 (LGB 代理模型, 非 G 模型 precision)

| 阈值 | Original precision | As-of precision | 差异 |
|------|-------------------|-----------------|------|
| ≥0.60 | 68.0% | 67.7% | -0.3pp |
| ≥0.65 | 69.6% | 69.2% | -0.4pp |
| ≥0.70 | 73.2% | 73.1% | -0.1pp |
| ≥0.75 | 77.9% | 77.5% | -0.4pp |

### 4.5 最大排名变化 (prob_orig ≥ 0.60 的股票)

| Symbol | Date | prob_orig | prob_asof | Δ |
|--------|------|-----------|-----------|------|
| 002429 | 04-23 | 0.738 | 0.673 | -0.065 |
| 002442 | 04-09 | 0.669 | 0.616 | -0.053 |
| 002160 | 04-08 | 0.613 | 0.665 | +0.051 |
| 000880 | 04-27 | 0.704 | 0.755 | +0.051 |
| 002213 | 04-22 | 0.639 | 0.597 | -0.042 |

最大单票偏移 6.5pp，可能导致：
- 002429 (04-23): 从 T≥0.70 区域跌出 (0.738 → 0.673)
- 000880 (04-27): 从 T<0.75 升入 T≥0.75 (0.704 → 0.755)

---

## 5. 无法重构的特征 (明确列出)

### 5.1 Moneyflow — 完全不可用 (7 个)

| 特征 | 数据源 | 14:55 状态 |
|------|--------|-----------|
| tushare_net_mf_amount | tushare moneyflow (盘后 16:00+) | 无日内历史数据可供回测 |
| tushare_lg_buy_sell_ratio | 同上 | 同上 |
| tushare_elg_buy_sell_ratio | 同上 | 同上 |
| tushare_mf_strength | 同上 | 同上 |
| tushare_sm_sell_pressure | 同上 | 同上 |
| tushare_main_force_divergence | 同上 | 同上 |
| tushare_ff_adjusted_flow | 同上 | 同上 |

**这 7 个特征在本次回放中保持了原始值 (= 盘后 tushare 值)。**  
在实际 14:57 场景中，计划用 akshare 东财实时数据替代。  
但 **没有 akshare 历史日内数据** 来验证替代效果。

### 5.2 Cross-sectional features — 需全市场快照 (29 个)

cs_ret_1_rank, cs_turnover_rank, cs_amount_z_rank, cs_volume_z_rank, cs_range_rank,
cs_volatility_rank, cs_market_positive_rate, cs_market_mean_ret_1, cs_market_mean_range,
cs_short_pool_size_log, cs_hot_concentration_rank, cs_limit_up_rate, cs_limit_down_rate,
cs_big_up_rate, cs_big_down_rate, cs_failed_limit_up_rate, cs_near_limit_rate,
cs_hot_mean, cs_hot_top_decile_mean, cs_emotion_score, rel_ret_1_to_market,
rel_range_to_market, volume_z_x_cs_ret_rank, close_pos_x_cs_range_rank,
cs_price_rank, cs_low_price_advantage, cs_weak_market_focus,
cs_stock_leads_index_rebound, cs_reversal_day_leader_quality

**状态**: 需要全市场 14:55 价格来计算截面排名。在实盘中用 pytdx 全市场快照可计算，但此处未测试其偏差。本次回放中保持了用 15:00 收盘价计算的原始值。

### 5.3 Sector features — 需板块收益数据 (11 个)

sector_pct_change_best, sector_strength_rank, sector_limit_up_count, sector_divergence, sector_duration_days + 6 个 _available 标记

**状态**: 需要 THS 概念板块日内收益。本次回放未修改。

### 5.4 其他应扰动但未扰动的特征 (24 个)

ret_std_5, ret_std_10, ret_std_20, range_pct, body_pct, upper_shadow_pct, lower_shadow_pct,
bollinger_width_20, limit_down_like, failed_limit_up, limit_down_bounce_pct, big_down,
up_count_3, up_count_5, down_count_3, down_count_5, atr_14_pct, adx_14,
intraday_reversal_score, near_limit_close, failed_breakout_10, failed_breakout_20,
hot_exhaustion_score, limit_touch_fail_proxy

**状态**: 这些特征依赖今日 close/OHLC，应该被扰动但在本次分析中遗漏。影响被低估。

---

## 6. 方法论限制 (诚实声明)

| 限制 | 影响 |
|------|------|
| **5-min 数据覆盖仅 23.4%** | 仅 628/1954 个测试标的有 14:55 数据 |
| **代理模型 ≠ G 模型** | LGB 单模型 vs ensemble_average_top3，precision/recall 数字不可直接迁移 |
| **77/260 特征扰动** (应 ~101) | 预测影响被系统性低估 |
| **扰动方法为一阶近似** | 非线性特征 (RSI, Bollinger) 的精确值需从修改后 OHLCV 重新计算 |
| **Moneyflow 7 特征保持原值** | 相当于假设 akshare = tushare，未验证 |
| **14:55 而非 14:57** | 5-min bar 最细粒度为 5 分钟，14:57 落在最后一个 bar 内 |
| **Cross-sectional 29 特征未修改** | 全市场排名在 14:55 vs 15:00 可能不同 |

---

## 7. G 模型 April 实际表现 (参考)

| 指标 | 值 |
|------|-----|
| April T≥0.75 candidates | 125 |
| April T≥0.75 precision | 80.0% |
| April T≥0.80 candidates | 39 |
| April T≥0.80 precision | 82.1% |
| 有 5-min 数据的 T≥0.75 candidates | 37/125 (30%) |
| 这 37 票的 precision | 78.4% |

---

## 8. 结论

### 8.1 可以说什么

1. **Raw OHLCV 差异确实很小**: close 14:55 vs 15:00 偏差 |mean| = 0.13%, volume 偏差约 -3%
2. **在已测试的 77 个特征和 23.4% 行覆盖下**: 预测差异小 (mean 0.63pp, P95 2.2pp)
3. **排名相对稳定**: daily top-10 overlap mean 95%
4. **阈值候选重合度高**: T≥0.75 recall = 97.2%
5. **Precision 下降不显著**: 在 LGB 代理模型上 <0.5pp

### 8.2 不能说什么

1. **不能 claim "G 模型可以用于 14:57 实盘"** — 没有用 G 模型本身做对比
2. **不能 claim "akshare 替代 tushare moneyflow 无影响"** — 没有 akshare 历史日内数据
3. **不能 claim "全市场 14:57 快照特征与收盘特征一致"** — 仅测试了 23.4% 的样本
4. **不能 claim "截面特征 (cs_*) 不变"** — 未测试全市场 14:55 排名变化
5. **不能 claim "24 个遗漏特征影响为 0"** — 它们确实依赖今日 close

### 8.3 判定

**证据不足，不 claim 可以实盘使用。**

初步信号是正面的（偏差小、重合度高），但验证不完整：
- 覆盖率太低 (23.4%)
- 扰动不完整 (77/260)
- 模型不对 (LGB proxy ≠ G ensemble)
- 核心因子 (moneyflow 7) 完全未测试

---

## 9. 若要得出可靠结论，需要

| 工作项 | 优先级 | 预计耗时 |
|--------|--------|---------|
| 1. 导出 G 模型权重 (export_realtime_model_bundle.py) | P0 | 20 min |
| 2. 用导出的 G 模型做全量 April 预测对比 | P0 | 5 min |
| 3. 收集 akshare 东财日内 moneyflow vs tushare 盘后数据 (至少 5 个交易日) | P0 | 5 天等待 |
| 4. 从修改后 OHLCV 重新计算所有特征 (非近似) | P1 | 20 min |
| 5. 扩展 5-min 数据覆盖 (补充缺失标的的分钟线) | P2 | 取决于 tushare quota |
| 6. 全市场 14:55 截面特征重算 | P1 | 需 pytdx + 全市场 5-min |

**最关键的是第 3 项**: 没有 akshare 历史数据，就无法验证 moneyflow 替代。这需要至少 5 个交易日的数据采集。

---

## 10. 数据来源与脚本

- 分析脚本: `scripts/replay_1457_focused.py`
- 详细指标: `docs/replay_1457_detailed_metrics.json`
- OHLCV 统计: `docs/replay_1457_ohlcv_stats.json`
- 5-min bar: `E:\ashare_similarity_runtime\data\cache\prediction\tushare\stk_mins_5\`
- Feature cache: `gpu_probe_features_383b5a3c0e707ae9.parquet` (created 2026-05-04T03:36:48Z)
- G run: `gpu_probe_20260504T033857Z_074fe9ea`

---

*不 claim passed，不 claim final，不 commit，不 push。*
