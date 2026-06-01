# Phase B: P0-Free Deliverable Variants - 2026-05-09

## P0 Counting Method

p0_forbidden_count is computed from **actual selected_features** in each model artifact,
checked against the canonical P0 feature set (18 features).
It is NOT hardcoded.

## Canonical P0 Features

```
sector_climax_signal
sector_climax_signal_available
sector_divergence
sector_divergence_available
sector_duration_days
sector_duration_days_available
sector_limit_up_count
sector_limit_up_count_available
sector_pct_change_best
sector_pct_change_best_available
sector_strength_rank
sector_strength_rank_available
tushare_cost_concentration
tushare_cost_concentration_available
tushare_cost_position
tushare_cost_position_available
tushare_winner_rate
tushare_winner_rate_available
```

## Variant Comparison

| Variant | Role | P0 | Deployable | Model | HC Acc | N | W95 | Brier | Pass 75% |
|---------|------|----|-----------|-------|--------|---|-----|-------|----------|
| B_baseline_s2_best | DIAGNOSTIC | 6 | NO | gpu_catboost_expressive | 0.7747 | 9716 | 0.7663 | 0.1685 | YES |
| B_delete_sector_only | DIAGNOSTIC | 2 | NO | gpu_catboost_expressive | 0.7516 | 11081 | 0.7435 | 0.181 | NO |
| B_delete_cyq_only | DIAGNOSTIC | 4 | NO | stacking_average_top3 | 0.7668 | 9842 | 0.7584 | 0.1732 | YES |
| B_delete_all_p0 | CANDIDATE | 0 | YES | gpu_catboost_expressive | 0.7391 | 12237 | 0.7312 | 0.1895 | NO |
| B_expanded_clean | CANDIDATE | 0 | YES | gpu_catboost_expressive | 0.7488 | 10797 | 0.7406 | 0.1833 | NO |

## Deployable Candidates (P0=0, non-diagnostic)

- **B_delete_all_p0**: W95=0.7312 [BELOW 75%]
- **B_expanded_clean**: W95=0.7406 [BELOW 75%]

## Best P0-Free: B_expanded_clean (W95=0.7406, P0=0)

## Seed Stability
- SKIPPED: Best P0-free candidate does not pass Wilson 75% gate.
- Cannot proceed to Phase C.

## Gate Decision

**BLOCKED** - No P0-free candidate meets Wilson 75% acceptance criterion.
Next step: expand P0-free factor/strategy search (pairwise, triples, beam, new factors).

## Self-Audit Checklist

| Check | Result |
|-------|--------|
| p0_forbidden_count from actual selected_features | PASS |
| No diagnostic variant in best_p0free | PASS |
| train_end = 2025-12-31 | PASS |
| Q1 used as seen_research only | PASS |
| No U95/Phase2 reuse | PASS |
| best_p0free true P0=0 | PASS (verified=0) |