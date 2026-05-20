# Superset Feature Matrix Runner Plan — 2026-05-07

**Goal**: Decouple "feature matrix construction" from "variant training" to eliminate redundant computation and memory contention.

---

## 1. Architecture

```
Phase A: Build Superset (ONE TIME)
  load 3063 symbols × feature_frames → 361k rows
  attach ALL factor features (tushare, TGB, limit_pool, intraday, market_index)
  write superset cache parquet (ALL columns, ~820 cols)
  validate: all 19 trainable factor columns present and non-zero

Phase B: Train Variants (78 times, fast)
  load superset from cache (cache hit, ~5s)
  apply variant-specific exclude_feature_names
  run stable_tail feature selection + LightGBM training
  write result to ledger + run directory
```

---

## 2. Key Design Decisions

### 2.1 Feature Cache Fingerprint Stability

The existing `gpu_probe` fingerprint includes:
- source_code_hash
- feature_names (the FULL set before exclusions)
- start/end dates, symbols, filters

It does NOT include `exclude_feature_names`. Therefore:
- All 78 variants share the SAME fingerprint
- Once the superset cache is built, all variants get cache hits
- No redundant 3063-symbol loads

### 2.2 Superset Validation Gate

Before any variant training, the superset must pass:
1. All 19 trainable factor columns exist in cache
2. All 19 factor columns have non-zero values (not all-zeros fallback)
3. Row count matches expected (361k ± 5%)
4. Date range covers 2023-05-01 to 2026-03-31
5. No blocked/leaked factors in column list
6. `_available` indicator columns present for each factor

### 2.3 Variant Slicing

Each variant defines `exclude_feature_names` — a list of factor columns (and their `_available` counterparts) to exclude. The training pipeline:
1. Loads full superset from cache
2. Applies active_anomaly_filter
3. Applies exclude_feature_names (drops columns before feature selection)
4. Runs stable_tail feature selection on remaining columns
5. Trains LightGBM
6. Evaluates on test set

### 2.4 P1 Stops

The runner MUST abort (not fallback to zeros) if:
- A required factor column is missing from superset
- A factor column is all-zeros (silent failure from prior builds)
- `exclude_feature_names` references a non-existent column
- Feature selection returns 0 features
- Row count mismatch between build and variant run

---

## 3. Implementation Plan

### 3.1 `scripts/run_superset_factor_matrix.py`

CLI modes:
```
python scripts/run_superset_factor_matrix.py build-superset-only
python scripts/run_superset_factor_matrix.py dry-run-variant TRUE_baseline
python scripts/run_superset_factor_matrix.py run-single-variant TRUE_baseline
python scripts/run_superset_factor_matrix.py run-all-variants
```

### 3.2 build-superset-only

1. Instantiate GpuProbeConfig with `exclude_feature_names=()` and `refresh_feature_cache=True`
2. Run data loading + factor attachment (the expensive part)
3. Write superset cache parquet
4. Run superset validation gate
5. Output validation report JSON
6. Exit (no training)

### 3.3 dry-run-variant

1. Load superset from cache (must exist, P1 stop if missing)
2. Apply variant exclusions
3. Report: which columns excluded, which remain, feature count, row count
4. DO NOT train
5. Output dry-run report

### 3.4 run-single-variant / run-all-variants

1. Load superset from cache
2. For each variant (from manifest JSON):
   a. Apply exclusions
   b. Train + evaluate
   c. Write ledger entry
   d. Write run directory
3. Output summary

---

## 4. Fixed Q1 Configuration

```python
GpuProbeConfig(
    start=date(2023, 5, 1),
    train_end=date(2025, 12, 31),
    test_start=date(2026, 1, 1),
    end=date(2026, 3, 31),
    seed=42,
    feature_set="research",
    label_target="next_high_from_close",
    target_high_return_pct=1.0,
    feature_selection_method="stable_tail",
    max_selected_features=260,
    min_phase_days_3=1,
    exclude_event_limit_up=True,
    exclude_feature_prefix=("cross_",),
    exclude_feature_names=(),  # superset: no exclusions
    lockbox_role="seen_research",
    use_feature_cache=True,
    refresh_feature_cache=True,  # only for build-superset-only
)
```

---

## 5. Superset Validation Checklist

| Check | Criterion | P-level |
|-------|-----------|:-------:|
| Factor column existence | All 19 factor columns in cache | P1 |
| Factor column non-zero | mean != 0 for each factor col | P1 |
| Availability columns | 19 `_available` columns present | P1 |
| Row count | 350k-380k rows | P1 |
| Date range | min >= 2023-05-01, max <= 2026-03-31 | P1 |
| No blocked factors | C001/C005/C010/C135 etc not in cols | P1 |
| No leakage columns | No T+1 data columns | P0 |
| Symbol count | >= 2800 unique symbols | P2 |
| Label distribution | positive_rate 55-65% | P2 |

---

## 6. Estimated Runtime

| Phase | Time | Notes |
|-------|------|-------|
| Build superset | ~25 min | One-time: 3063 symbols + factor attach |
| Per variant (cache hit) | ~3-5 min | Load cache + train + evaluate |
| All 78 variants | ~4-6.5 hours | Sequential, no memory contention |
| Total | ~5-7 hours | Build + all variants |

---

## 7. Baseline Equivalence Gate

Before running all variants, must verify:
- Superset baseline (exclude_feature_names=all_tushare) matches Phase 7 baseline
- Expected Wilson ~74.15% (Phase 7 seed=42 baseline = 75.11%)
- Row counts, split, label distribution identical

---

## 8. Self-Audit

| Check | Status |
|-------|:------:|
| Architecture separates build from train | PASS |
| No redundant 3063-symbol loads | PASS |
| Feature cache fingerprint stable across variants | PASS |
| P1 stops on missing/zero columns | PASS |
| Reads manifest from JSON | PASS |
| Writes to experiment_ledger | PASS |
| No freeze/April/passed claims | PASS |

---

**Plan COMPLETE. Proceeding to implementation.**
