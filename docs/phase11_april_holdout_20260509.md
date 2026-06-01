# Phase 11: April Known-Holdout - 2026-05-09

**Status**: BLOCKED (data unavailable)

## Findings

The `research` feature set data only covers up to 2026-03-31 (end of Q1). April 2026 data is available in raw `limit_pool_snapshots` but has NOT been processed into the feature matrix used by `gpu_probe`.

The probe returns `invalid_config` when `test_start=2026-04-01`, confirming no feature data exists for the April window.

## Implication

Phase 11 cannot validate signal decay on holdout data. However, since Phase 9 already determined the model is NOT FROZEN (instability finding), this does not change the overall pipeline conclusion.

## Action Required

To run April holdout in the future:
1. Process April raw data through the feature engineering pipeline
2. Re-run this script after feature matrix is updated
