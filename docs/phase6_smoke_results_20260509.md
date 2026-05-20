# Phase 6: Smoke Run Results - 2026-05-09

Generated: 2026-05-09

## Variants Run

| Variant | Model | Pool | Selected | HC Acc | HC Count | Coverage | Wilson 95% | Time | Pass |
|---------|-------|------|----------|--------|----------|----------|------------|------|------|
| CTRL_current_baseline_reproduced | gpu_catboost_expressive | 751 | 260 | 0.7618 | 10582 | 24.6% | 0.7536 | 146s | YES |
| CTRL_delete_all_BC_uncertain | gpu_catboost_expressive | 693 | 260 | 0.7519 | 10745 | 25.0% | 0.7436 | 197s | NO (W<75%) |
| CTRL_A_plus_chip_t1 | gpu_catboost_expressive | 699 | 260 | 0.7599 | 10533 | 24.5% | 0.7516 | 128s | YES |

## Key Findings

1. **Infrastructure confirmed**: All 3 variants train and evaluate successfully on GPU (RTX 5090)
2. **train_end = 2025-12-31**: Enforced by config, test covers only Q1 2026 (Jan 5 - Mar 30)
3. **No April leakage**: Test end is 2026-03-30
4. **B-class features matter**: Deleting ALL B-class drops Wilson from 0.7536 to 0.7436 (~1pp)
5. **Chip T-1 features specifically**: A+chip_t1 (0.7516) vs delete_all_BC (0.7436) = +0.8pp
6. **All variants above 75% HC accuracy** with count > 10,000 and coverage > 10%
7. **Cache hit confirmed**: All variants use superset parquet (fingerprint 29fad3014f118dc1)
8. **Each run takes 2-3 minutes** (cache hit, GPU training only)

## Implications for Phase 7

- B-class families provide measurable value (~1pp Wilson)
- chip/cost T-1 is the most valuable B-class family (U31 comparison confirmed)
- Need to test TGB, THS sector, hot/holder/hk individually to quantify each family's contribution
- Phase 7 S1 policy grid (24 variants) is computationally feasible: ~24 * 3min = ~72 minutes

## Validation

- All train_end = 2025-12-31: True
- No April leakage: True
- P0 issues: 0
- P1 issues: 0
- Proceed to Phase 7: YES

## Self-Audit Gate

| Check | Result |
|-------|--------|
| All 3 smoke variants completed | PASS |
| train_end confirmed 2025-12-31 | PASS |
| No April data in test window | PASS |
| HC accuracy reasonable (>70%) | PASS |
| HC count > 1000 | PASS (>10000) |
| Feature cache hit confirmed | PASS |
| B-class deletion impact measured | PASS |
| P0 issues | 0 |
| P1 issues | 0 |
| Proceed to Phase 7 | YES |
