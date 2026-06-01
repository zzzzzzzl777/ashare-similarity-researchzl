# 第四轮训练阶段复盘

**Date**: 2026-05-04  
**Plan version**: v1.4  
**Label**: `next_high_from_close` (T+1 日内最高价 >= 收盘价 +1%)  
**Acceptance target**: Wilson 95% lower bound >= 75% on final_unseen  

---

## 1. 结论：第四轮不通过

- **不通过 final acceptance。**
- **不 claim passed。**
- **不 claim final_unseen。**
- B1 在 Q1 高阈值表现很强 (Wilson 82.76%~85.65%)，但 April reserved holdout 没有验证出足够稳定性。

---

## 2. Q1 vs April 对照

### Rule A: B1 + T>=0.75 + daily top50

| Metric | Q1 | April | Delta |
|--------|-----|-------|-------|
| Precision | 86.53% | 74.60% | **-11.93pp** |
| Wilson LB | 82.76% | 67.95% | **-14.81pp** |
| Count | 386 | 189 | -197 |
| Active days | 26/55 | 17/20 | — |
| Avg/all day | 7.02 | 9.45 | — |

**April Wilson 67.95% < 75% 目标，且明显低于 Q1。Rule A 不通过。**

### Rule B: B1 + T>=0.80 + daily top50

| Metric | Q1 | April | Delta |
|--------|-----|-------|-------|
| Precision | 90.00% | 100.00% | +10.00pp |
| Wilson LB | 85.65% | 64.57% | **-21.08pp** |
| Count | 250 | 7 | -243 |
| Active days | 17/55 | 3/20 | — |

**April 仅 7 个样本，Wilson 不可靠。Rule B 因样本量不足，无法验证有效性。**

### Observation: B1 + T>=0.75 + daily top30

| Metric | Q1 | April | Delta |
|--------|-----|-------|-------|
| Precision | 84.81% | 75.14% | **-9.67pp** |
| Wilson LB | 80.05% | 68.29% | **-11.76pp** |
| Count | 270 | 177 | -93 |

**观察组仅用于参考，不能事后选为正式规则。同样未达 75% Wilson 目标。**

---

## 3. April 逐日拆解

| Date | Count | Hits | Precision | Note |
|------|-------|------|-----------|------|
| 2026-04-02 | 33 | 23 | 69.70% | |
| 2026-04-03 | 25 | 24 | 96.00% | |
| 2026-04-07 | 39 | 34 | 87.18% | 当月最大候选日 |
| **2026-04-08** | **11** | **3** | **27.27%** | **最差日，严重拖累** |
| 2026-04-09 | 1 | 1 | 100% | |
| 2026-04-10 | 5 | 5 | 100% | |
| 2026-04-13 | 1 | 1 | 100% | |
| 2026-04-14 | 2 | 1 | 50.00% | |
| 2026-04-15 | 2 | 2 | 100% | |
| 2026-04-16 | 3 | 2 | 66.67% | |
| 2026-04-17 | 1 | 1 | 100% | |
| 2026-04-20 | 1 | 1 | 100% | |
| 2026-04-21 | 1 | 1 | 100% | |
| 2026-04-22 | 1 | 1 | 100% | |
| **2026-04-23** | **29** | **18** | **62.07%** | **拖累日** |
| **2026-04-27** | **19** | **10** | **52.63%** | **拖累日** |
| 2026-04-28 | 15 | 13 | 86.67% | |
| (3 days) | 0 | 0 | — | 无候选 |

**三个拖累日 (04-08, 04-23, 04-27) 合计**: 59 candidates, 31 hits, precision=52.54%  
**去除三个拖累日后**: 130 candidates, 110 hits, precision=**84.62%** — 接近 Q1 水平。

衰减集中在少数「批量出错」日，不是全面性失效。但 holdout 规则不允许事后剔除，这一观察仅供后续研究 regime gate 时参考。

---

## 4. 保留价值

第四轮不是失败无价值：

1. **流程验证**：已验证 executable-only 样本过滤 (`min_phase_days_3=1`)、涨停不可买过滤 (`exclude_event_limit_up=True`)、Q1/April 分层 holdout 流程正确执行。
2. **因子方向有信号**：C009 (`main_force_divergence`) 和 C011 (`auction_open_vwap_ratio`) 在 Q1 被 stable_tail 选中 (11/260 selected features 中 2 个来自 B-group)，说明这些因子维度对预测有贡献。
3. **Q1 高阈值表现强劲**：B1 在 Q1 T>=0.75 时 Wilson 84.59% (uncapped) / 82.76% (top50 cap)，远超 75% 目标。如果 Q1 是最终验证窗口，就能通过。
4. **April 集中度更健康**：April 最大单日 39 candidates (占比 20.6%)，Q1 是 518 candidates (40%)。Daily cap 的风险控制在 April 实际不需要触发 (max=39 < top50)。
5. **衰减模式清晰**：不是全面性失效，而是 3 个特定日期的批量错误，可能与 regime 相关 (例如大盘急跌后的反弹预判失误)。这为第五轮 regime gate 研究提供了明确方向。

---

## 5. 因子库回写建议

以下为建议内容，不执行回写：

| Factor | 建议状态 | 理由 |
|--------|---------|------|
| C009 (`main_force_divergence`) | `selected_in_q1_b1, april_holdout_not_confirmed` | Q1 被选中且 B1 高阈值表现好，但 April holdout 整体 Wilson 未达标 |
| C011 (`auction_open_vwap_ratio`) | `selected_in_q1_b0_b1, april_holdout_not_confirmed` | Q1 在 B0 和 B1 均被选中，但 April holdout 整体 Wilson 未达标 |
| C001 (`mf_flow_intensity`) | `implementation_blocked` | 需要 tushare daily API 的 `amount` 字段，缓存中不存在 |
| C010 (`float_relative_impact`) | `implementation_blocked` | 需要 tushare daily API 的 `volume` 字段，缓存中不存在 |
| C004 (`ff_adjusted_flow`) | `engineered_but_untested` | 已可计算但本轮没有进入任何 feature manifest，不能声称已测试 |

**不要把 C009/C011 标记为 final accepted。**

---

## 6. 后续建议

以下只是建议，不执行：

1. **April 已被看过**：如果要继续，就是第五轮研究。April 数据已经被观察，应标记为 `seen_research`，不能再当最终验证窗口。

2. **Regime gate 研究方向**：第五轮可以研究 April 低精度日的 regime gate。04-08、04-23、04-27 三天合计拖累 -32.08pp (从 84.62% 降至 74.60%)。如果能识别这类 regime 并在预测时过滤，B1 的泛化性可能改善。但 regime gate 必须在另一个未见窗口验证。

3. **降低覆盖目标**：也可以考虑把 Rule B (T>=0.80) 当极低频观察信号——但不能凭 7 个样本上线。如果 T>=0.80 在更长窗口积累到足够样本 (比如 200+)，可以重新评估。

4. **新的最终验证窗口**：下一次 final acceptance 应等新的 forward 数据 (如 2026-05 及以后)，或重新定义一个未见窗口。在此之前，所有已看过的数据 (Q1 + April) 均为 seen_research。

5. **C001/C010 解锁**：如果获取到 tushare daily API 缓存 (含 `amount`/`volume`)，可以解锁 C001/C010，为 B2/B3 variants 提供更多因子维度。

---

## 7. 关键数据索引

| Item | Path |
|------|------|
| Q1 audit MD | `docs/family_ablation_q1_audit_20260504.md` |
| Q1 audit JSON | `E:\...\prediction\family_ablation_q1_audit_20260504.json` |
| April holdout MD | `docs/family_ablation_april_holdout_20260504.md` |
| April holdout JSON | `E:\...\prediction\family_ablation_april_holdout_20260504.json` |
| Q1 B1 artifact | `runs/gpu_probe_20260503T170747Z_41d4ad1d/artifact.json` |
| April B1 artifact | `runs/gpu_probe_20260503T185913Z_793f0623/artifact.json` |
| This postmortem MD | `docs/fourth_round_postmortem_20260504.md` |
| This postmortem JSON | `E:\...\prediction\fourth_round_postmortem_20260504.json` |

---

*第四轮训练阶段复盘。不通过 final acceptance。不 claim passed。不 claim final_unseen。不 commit，不 push。*
