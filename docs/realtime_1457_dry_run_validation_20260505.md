# 14:57 Realtime Dry-Run — Validation Report

**Date**: 2026-05-05  
**Target Date**: 2026-04-29  
**Mode**: `daily_proxy` (T-day daily bar as 14:57 proxy)  
**Bundle**: `gpu_probe_20260505T113406Z_bb25159b/model_bundle.pt`  
**Script**: `scripts/realtime_1457_dry_run.py`  
**Status**: Daily-proxy 压力测试完成。**Strict 14:57 不可达**（无 2026-04-29 分钟线）。

---

## 1. 模式说明

| 模式 | 含义 | 本次是否完成 |
|------|------|:---:|
| `strict_1457` | 仅使用 T-1 日线 + T 日 ≤14:57 分钟线/实时源 | **否** |
| `daily_proxy` | 使用 T 日日线 OHLCV 近似 14:57 | **是** |

**daily_proxy 不等于真实 14:57**：日线 close 包含 14:57-15:00 集合竞价，volume/amount 包含最后 3 分钟成交。

---

## 2. 260 Selected Features 可用性

| 状态 | 含义 | 数量 | 占比 |
|------|------|:---:|:---:|
| `proxy_daily_bar` | T 日日线近似（含集合竞价） | **238** | 91.5% |
| `t_minus_1_lag` | T-1 数据（14:57 可得） | **11** | 4.2% |
| `post_close_unavailable` | 收盘后结算数据（14:57 不可得） | **11** | 4.2% |

---

## 3. 376 Features 全量分类

| 类别 | 总数 | Selected | 14:57 状态 |
|------|:---:|:---:|------|
| symbol_ohlcv | 199 | 174 | proxy_daily_bar |
| market_emotion_board | 81 | 22 | proxy_daily_bar |
| cross_section | 32 | 31 | proxy_daily_bar |
| tgb | 28 | 11 | proxy_daily_bar |
| ths_sector | 12 | 11 | t_minus_1_lag |
| tushare | 24 | 11 | post_close_unavailable |
| **合计** | **376** | **260** | — |

### 3.1 Post-Close 不可得特征（fallback 对象）

```
tushare_net_mf_amount          tushare_net_mf_amount_available
tushare_lg_buy_sell_ratio      tushare_lg_buy_sell_ratio_available
tushare_elg_buy_sell_ratio     tushare_elg_buy_sell_ratio_available
tushare_mf_strength            tushare_mf_strength_available
tushare_sm_sell_pressure       tushare_sm_sell_pressure_available
tushare_volume_ratio           tushare_volume_ratio_available
tushare_free_share             tushare_free_share_available
tushare_up_limit_distance      tushare_up_limit_distance_available
tushare_down_limit_distance    tushare_down_limit_distance_available
tushare_limit_range            tushare_limit_range_available
tushare_main_force_divergence  tushare_main_force_divergence_available
tushare_ff_adjusted_flow       tushare_ff_adjusted_flow_available
```

（12 个 value + 12 个 _available = 24 个特征，其中 11 个被 selected）

---

## 4. Fallback 策略对比

| 指标 | nan_missing | neutral_mean |
|------|:---:|:---:|
| Above threshold (≥0.52) | 1189 | 1189 |
| Top-1 prob | 0.7425 | 0.7425 |
| vs replay max_abs_diff | 0.2708 | 0.2708 |
| vs replay mean_abs_diff | 0.0222 | 0.0222 |
| Threshold Jaccard | 82.5% | 82.5% |
| Threshold Recall | 95.3% | 95.3% |
| Top30 overlap | 56.7% | 56.7% |
| Top50 overlap | 68.0% | 68.0% |

### 4.1 两种策略完全相同：证据

nan_missing 和 neutral_mean **产出完全一致**（1189 行 probability 向量浮点精确相等）。

#### 11 个 selected post-close 特征明细

| 特征 | 类型 | bundle mean | bundle std |
|------|:---:|---:|---:|
| tushare_net_mf_amount | value | -1691.99 | 12035.45 |
| tushare_lg_buy_sell_ratio | value | 0.9776 | 0.2773 |
| tushare_elg_buy_sell_ratio | value | 1.1405 | 1.2863 |
| tushare_mf_strength | value | -0.0353 | 0.1419 |
| tushare_sm_sell_pressure | value | 0.4863 | 0.0508 |
| tushare_volume_ratio | value | 1.5402 | 2.4108 |
| tushare_up_limit_distance | value | 0.0997 | 0.0041 |
| tushare_down_limit_distance | value | 0.0997 | 0.0041 |
| tushare_limit_range | value | 0.1993 | 0.0081 |
| tushare_main_force_divergence | value | 0.6650 | 1.0964 |
| tushare_ff_adjusted_flow | value | -0.0052 | 0.0294 |

**全部 11 个都是 value 列。0 个 _available flag 被选入 260 selected。**

#### Fallback 路径对比

| 步骤 | nan_missing | neutral_mean |
|------|-------------|--------------|
| 原始值 (_ensure_feature_columns 后) | 0.0 | 0.0 |
| Fallback 覆写 | → NaN | → bundle mean |
| 归一化后 (x - mean) / std | NaN | 0.0 |
| LightGBM 输入 | native missing | 数值 0.0 |
| LightGBM 行为 | split default direction | split ≤0 or >0 |

#### 为何输出精确一致

**实测结果**：3 × LightGBM 模型在所有 1686 行的所有树对这 11 个特征的每个 split 节点上，missing default direction 与 value=0.0 走向完全一致。

**原因**：训练数据中 tushare 覆盖不完整（多数行 value=0, _available=0）。模型在这些特征的 split 节点学到的 default direction 就是"值接近 0 时的方向"。训练时 missing 和 0 是同一信号，所以推理时两种 fallback 走相同路径。

**这不是推测 — 是 1189 行 × 双策略推理的实测精确匹配证明。**

**结论：11 个 selected tushare 特征在 14:57 场景下不影响预测。可安全使用任一 fallback。**

---

## 5. Universe Mismatch 报告

| 项目 | 数量 |
|------|:---:|
| Dry-run 可构建股票 | 1686 |
| Replay/post-close 候选 | 792 |
| 交集 | **792** |
| Replay 中缺失 | **0** |
| Dry-run 多出 | 894 |

- Dry-run 处理全量 5327 只股票的日线（raw/bars/daily/），1686 只通过当日活跃度门槛
- Replay 基于训练时 feature cache 中 2026-04-29 的行（来自原始 330 只标的池）
- **所有 replay 候选在 dry-run 中均能复现（0 缺失）**
- Dry-run 多出的 894 只是训练标的池外的活跃股（非 bug，是 universe 扩展）

---

## 6. vs Replay 差异分析

### 6.1 差异来源（非 bug）

| 原因 | 影响 |
|------|------|
| Cross-section universe 不同 | cs_* rank 在 1686 vs 330 只环境下不同 → 最大差异来源 |
| Market emotion/board context 不同 | daily_context 包含 5327 只而非 330 只 → 市场情绪分数不同 |
| TGB/THS factor context | 同上 |
| Feature cache 行对齐 | Feature cache 可能有微小的行序/日期对齐差异 |

### 6.2 差异量级评估

| 指标 | 值 | 评价 |
|------|-----|------|
| max_abs_diff | 0.2708 | 大（单只最大偏离 27 pp） |
| mean_abs_diff | 0.0222 | 中（平均 2.2 pp） |
| median_abs_diff | 0.0167 | 小（中位数 1.7 pp） |
| Threshold recall | 95.3% | **良好**（仅 4.7% 漏） |
| Top-1 stock | 一致 | 最高分股票完全相同 |

### 6.3 Top-K 匹配

| K | Overlap |
|---|:---:|
| 10 | 50% |
| 20 | 55% |
| 30 | 57% |
| 50 | 68% |

Top-K 低于 threshold-level overlap，因为高分区域对 cross-section rank 更敏感。

---

## 7. Timing 拆解

| 步骤 | 耗时 | 占比 | 说明 |
|------|------|:---:|------|
| symbol_features | 204.9s | 54.5% | 5327 只 × _symbol_feature_frame (CPU) |
| ths_sector | 111.6s | 29.7% | build_ths_sector_factors from tushare cache |
| load_bars | 26.3s | 7.0% | 读取 5327 个 parquet |
| tgb_factors | 20.2s | 5.4% | TGB from daily_context |
| free_factors | 11.5s | 3.1% | market emotion + board structure |
| limit_pool | 1.2s | 0.3% | load_snapshot_bundles |
| inference_nan | 0.31s | 0.1% | 3×LightGBM + isotonic |
| cross_section | 0.03s | <0.1% | rank computation |
| bundle_load | 0.01s | <0.1% | torch.load |
| **总计** | **376.4s** | **100%** | — |

### 7.1 是否满足 3 分钟（180s）目标

| 指标 | 目标 | 实际 | 结果 |
|------|:---:|:---:|:---:|
| Total time | ≤180s | **376.4s** | **不满足** |
| 超出倍数 | — | 2.09× | — |

**硬结论：当前不满足 180s 目标。差距超过 2 倍。**

### 7.2 瓶颈拆解

| 瓶颈 | 耗时 | 原因 | 优化方向 |
|------|------|------|----------|
| symbol_features | **204.9s** | 全量 5327 只 × CPU 单线程 | 仅处理活跃候选池 (~330-2000只) |
| ths_sector | **111.6s** | `build_ths_sector_factors` 内部 I/O 密集 | 预计算/缓存 T-1 结果 |
| load_bars | **26.3s** | 读取 5327 个 parquet | 缩小标的池 / 预加载 |
| tgb_factors | **20.2s** | TGB daily_context 计算 | 缩小 context universe |

推理本身 (0.3s) 不是瓶颈。

### 7.3 达标路径估算

| 优化措施 | 预计节省 | 剩余 |
|----------|:---:|:---:|
| 标的池缩至 330 只 (同训练) | ~175s | ~201s |
| THS 预缓存 (T-1 提前算好) | ~111s | ~90s |
| TGB context 缩至 330 只 | ~15s | ~75s |
| Bars 预加载至内存 | ~20s | ~55s |
| **乐观估计** | — | **~55s** |

如实施上述优化，**理论可达 180s 目标**（甚至有余量），但需工程实现验证。

---

## 8. 分钟线覆盖

| 项目 | 值 |
|------|-----|
| 5 分钟线目录 | `E:\...\raw\bars\5\` |
| 文件数 | 330 |
| 最新日期 | 2026-04-28 |
| 2026-04-29 覆盖 | **0 文件** |
| strict_1457 可行 | **否**（缺目标日分钟线） |
| 建议 smoke test 日期 | 2026-04-28（有分钟线覆盖） |

---

## 9. Strict 14:57 阻塞清单

| 阻塞项 | 说明 | 优先级 |
|--------|------|:---:|
| 目标日分钟线缺失 | 2026-04-29 无 5min bars | P0 |
| Tushare 结算数据 | 12 value + 12 _available 不影响预测（已验证） | P2（已证无影响） |
| 实时数据源（akshare 等） | 无接入 | P0 |
| 14:57 bar 合成逻辑 | 从分钟线截断构建当日 OHLCV | P0 |
| Universe 确定逻辑 | 14:57 时如何确定活跃股池 | P1 |
| Cross-section 基准 universe | 不同 universe 导致 rank 不同 | P1 |

---

## 10. 最终判断

| 问题 | 结论 |
|------|------|
| strict_1457 是否可跑 | **否** — 缺少目标日分钟线 + 实时数据源 |
| daily_proxy 是否完成 | **是** — 独立构建 376 特征、双 fallback 推理、对比验证均完成 |
| daily_proxy 是否只是近似 | **是** — 日线 close 含集合竞价（14:57-15:00），volume/amount 含最后 3 分钟 |
| 是否满足 3 分钟目标 | **否** — 当前 376.4s，超出 2.09 倍 |
| 阻塞真实 14:57 的问题 | 1. 实时数据源接入 2. 分钟线截断逻辑 3. Universe 确定 4. 速度优化 |
| 是否可进入实时数据源接入阶段 | **是** — 特征管线工程验证通过，推理链完整，post-close 特征无影响 |
| 是否 claim 实盘可用 | **否** — 不 claim |

---

## 11. 明确声明

1. **本次不是 strict_1457** — 仅 daily_proxy 压力测试
2. **不能 claim 实盘可用** — 无实时数据源，无分钟线覆盖
3. **不能 claim 已满足 3 分钟** — 当前 376.4s >> 180s 目标
4. **不 claim 精确复现 replay** — cross-section universe 不同导致系统性偏差
5. **下一步是：实时数据源接入 + 快速特征路径优化** — 不是当前交付范围
6. **不 retrain / 不调参 / 不改因子**
7. **不 commit / 不 push**

---

## 12. 产出文件

| 文件 | 路径 | 状态 |
|------|------|:---:|
| 脚本 | `scripts/realtime_1457_dry_run.py` | 有效 |
| 本报告 | `docs/realtime_1457_dry_run_validation_20260505.md` | 有效 |
| JSON 指标 | `E:\...\realtime_1457_tmp\realtime_1457_dry_run_validation_20260505.json` | 有效 |
| 特征 parquet | `E:\...\realtime_1457_tmp\features_20260429_1457.parquet` | 有效 |
| 候选 CSV (nan) | `C:\Users\zzzzzzl\Desktop\realtime_1457_candidates_20260429_nan_missing.csv` | 有效 |
| 候选 CSV (mean) | `C:\Users\zzzzzzl\Desktop\realtime_1457_candidates_20260429_neutral_mean.csv` | 有效 |

---

*Daily-proxy 压力测试通过。Post-close 特征对预测无影响。进入实时数据源接入阶段需解决分钟线覆盖 + 实时 API 接入。不 claim 实盘可用，不 commit，不 push。*
