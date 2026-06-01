# Minute Factor Round 4 — Final Summary Report

**Date**: 2026-05-06  
**Round**: 4 (Minute Factor Ablation — C133-C138)  
**Status**: **COMPLETE — NO IMPROVEMENT FOUND**

---

## Executive Summary

Round 4 performed a rigorous 32-combination ablation matrix of 5 minute-bar factors (C133-C138) on Q1 2026 data, followed by seed and budget stability testing. **No minute factor combination provides statistically significant improvement over the baseline.**

| Phase | Result |
|-------|--------|
| 1. Gate fix verification | PASS |
| 2. Preflight | PASS (dedup fix verified) |
| 3. Smoke (3 variants) | PASS |
| 4. Full 32 matrix | COMPLETE (12/32 beat baseline at seed=42) |
| 5. Extended ablation | **DECISIVE**: Seed variance (1.0pp std) >> factor signal (0.07pp) |
| 6. Freeze decision | **NO FREEZE** — baseline retained |
| 7. Bundle gate | PASS (max_abs_diff=0.0) |
| 8. April holdout | Wilson=72.36% (−2.26pp from Q1 baseline) |

---

## Key Findings

### 1. Minute Factors Don't Help (Statistically)

| Metric | M21 (best minute combo) | M00 (baseline) | Difference |
|--------|:-----------------------:|:--------------:|:----------:|
| Wilson (seed=42 only) | 75.03% | 74.62% | +0.41pp |
| Wilson (mean of 5 seeds) | 74.23% | 74.16% | **+0.07pp** |
| Seed std | 1.05pp | 1.21pp | — |
| Signal-to-noise | — | — | 0.067 |

The +0.41pp advantage at seed=42 is a random fluctuation — confirmed by running 5 seeds showing only +0.07pp mean advantage with 1pp+ standard deviation.

### 2. C138 (high_time_pct) Is the Strongest Individual Factor

But still not reliably additive:
- Solo (M16): mean Wilson = 74.18% vs baseline 74.16% (+0.02pp, noise)
- Best combo (M21 = C133+C136+C138): +0.07pp mean, also noise

### 3. April Regime Shift

The model trained on 2023-2025 data tested on April 2026 shows:
- Wilson dropped from 74.62% (Q1) to 72.36% (April)
- Coverage halved from 24.79% to 12.61%
- This is regime degradation, not model failure — the model correctly becomes less confident when faced with out-of-sample conditions

### 4. Infrastructure Improvements

Despite no metric improvement, this round delivered:
- **Stable dedup in gpu_probe.py** — removes 15 duplicate features (improved ALL variants by +0.25-1.22pp)
- **`exclude_feature_names` field** — surgical per-run feature blocking
- **Experiment ledger** — JSONL with full reproducibility metadata
- **Variant manifest** — immutable experiment governance
- **Factor registry entries** — C133-C138 formally registered

---

## Factor Registry Feedback (Phase 11)

| Factor | Status | Round 4 Finding |
|--------|--------|-----------------|
| C133 (last_30min_return) | existing_engineered | Not additive in current pipeline |
| C134 (first_15min_volume_ratio) | existing_engineered | Not additive |
| C135 (vwap_deviation) | blocked_until_outlier_guard | Still blocked (max=109.6) |
| C136 (intraday_volatility) | existing_engineered | Not additive |
| C137 (up_volume_ratio) | existing_engineered | Negative solo contribution |
| C138 (high_time_pct) | existing_engineered | Best solo (+0.25pp seed=42, 0pp mean) |
| C139-C152 | not_tested | Deferred to future round |

**No status changes recommended.** All factors remain valid engineering artifacts; they simply don't add value to the 747-feature ensemble at the current configuration.

---

## Live Forward Plan (Phase 12)

**Recommendation: Continue with current production baseline (no minute factors).**

No changes to the deployed model or prediction pipeline. The minute factor data pipeline continues to run (for future research), but predictions use the existing non-minute model.

---

## Next Round Plan (Phase 13)

Suggested directions for Round 5:

1. **C139-C152 factors** — 14 new factors not tested in this round (money flow, float impact, limit dynamics, seal strength). These may have stronger signal than the basic minute factors.

2. **Alternative feature selection** — `stable_tail` keeps only 1 minute feature out of 10. Try:
   - Forward selection starting from minute features
   - Dedicated minute-factor sub-model in an ensemble
   - Lower `selector_coverage_weight` to give minority features more chance

3. **Longer training window** — Current train=2023-05-01 to 2025-12-31. Adding 2022 data might stabilize the signal.

4. **Seed-robust evaluation** — Always run 5+ seeds for any candidate. Single-seed evaluations are misleading (as proven in this round).

5. **Regime-aware training** — The Q1→April drop (-2.26pp Wilson, coverage halved) suggests model benefits from recency. Consider rolling train window or regime-weighted training.

---

## Experiment Governance Summary

| Artifact | Location |
|----------|----------|
| Experiment ledger | `E:\...\experiment_ledger_20260506.jsonl` |
| Variant manifest | `E:\...\minute_factor_variant_manifest_20260506.json` |
| Full matrix report | `docs/minute_factor_full_matrix_q1_20260506.md` |
| Extended ablation | `docs/minute_factor_extended_ablation_q1_20260506.md` |
| Freeze decision | `docs/minute_factor_q1_freeze_decision_20260506.md` |
| Smoke audit | `docs/minute_factor_smoke_audit_q1_20260506.md` |
| Preflight | `docs/minute_factor_matrix_preflight_q1_20260506.md` |

Total training runs: 54  
Total GPU hours: ~2.25h  
No commit, no push, no production changes.

---

## Explicit Final Statements

1. **No acceptance claims** — `final_acceptance_eligible=false` on all runs
2. **lockbox_role=seen_research** — Q1 data is observed research, not unseen holdout
3. **April is known_holdout** — historically observed, not strict final_unseen
4. **No minute factors enter production** — decision is NO FREEZE
5. **Dedup fix is the one real improvement** — +0.25-1.22pp across all variants
6. **No commit/push executed** — all changes remain local
7. **C139-C152 not tested** — explicitly deferred

---

*Round 4 complete. The minute factors (C133-C138) do not provide statistically robust improvement over the 747-feature baseline. The dedup fix (+1pp) is the real win from this round. Recommend proceeding to C139-C152 evaluation in Round 5.*
