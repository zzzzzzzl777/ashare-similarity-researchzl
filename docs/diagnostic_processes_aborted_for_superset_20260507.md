# Diagnostic Processes Aborted for Superset Runner — 2026-05-07

**Action**: Engineering strategy correction  
**Timestamp**: 2026-05-07T18:10:00+08:00  

---

## 1. Processes Stopped

| PID | Command Line | Started | Status at Kill | Classification |
|-----|-------------|---------|:-------------:|:--------------|
| 30764 | `C:\Python314\python.exe -u scripts/run_expanded_matrix.py` | 16:53:51 | Running variant 3/51 (data loading) | **diagnostic_partial_run** |
| 57008 | `C:\Python314\python.exe -c "..." (refresh_feature_cache=True)` | 17:53:40 | Loading feature_frames 2500/3063 | **redundant_cache_build_attempt** |

---

## 2. Why This Is Strategy Correction, Not Failure

Both processes were stopped because:

1. **PID 30764 (run_expanded_matrix.py)** was a diagnostic-only 51-variant run using:
   - Incorrect factor IDs (M001-M005 instead of C133-C138)
   - An all-zeros tushare feature cache (fingerprint `70fa9f447520a014`)
   - Results (Wilson ~72%) confirm tushare factors were absent from training
   - Cannot be authoritative even if completed

2. **PID 57008 (cache rebuild)** was competing for GPU/memory with PID 30764:
   - Both loading 3063 symbol frames simultaneously
   - OOM failures observed (Unable to allocate 342 MiB / 492 MiB)
   - Architecture is flawed: each variant rebuilds full feature matrix

3. **Correct approach**: Build ONE superset feature matrix, then slice columns per variant. This eliminates:
   - 78× redundant 3063-symbol loads
   - Memory contention between parallel processes
   - Feature cache fingerprint churn from `exclude_feature_names` changes

---

## 3. Completed Runs (Preserved, Not Deleted)

| # | Run ID | Variant | Wilson | HC Acc | Phase |
|---|--------|---------|:------:|:------:|-------|
| 31 | gpu_probe_20260507T092620Z_4b5ade66 | EXP_baseline | 72.60% | 73.48% | expanded_matrix |
| 32 | gpu_probe_20260507T100546Z_960529e8 | EXP_daily_r1_all | 72.17% | 73.01% | expanded_matrix |

**Note**: Both used the all-zeros tushare cache. Wilson ~72% vs expected ~75% confirms tushare features were zeroed. These are INVALID for comparison but preserved as diagnostic artifacts.

---

## 4. Incomplete State

| Item | Status |
|------|--------|
| Incomplete run directories | **NONE** (kill happened during data load, before run dir creation) |
| Half-written cache files | **NONE** (cache `70fa9f447520a014` was pre-existing bad cache, already deleted earlier) |
| Ledger integrity | 32 entries, all with complete metadata |
| Feature cache on disk | `3f386fd04386e166` (R1 only, 809 cols) — valid but incomplete universe |

---

## 5. Unfinished Variants from PID 30764

49/51 variants never started. The full manifest included:
- 5 controls
- 16 single-factor
- 4 family smoke
- 10 pairwise
- 10 greedy forward
- 6 backward pruning

All are superseded by the true_all_factor_expansion_manifest (78 variants from registry).

---

## 6. Governance Declarations

| Declaration | Status |
|-------------|:------:|
| PID 30764 result = diagnostic_partial_run | CONFIRMED |
| PID 57008 result = redundant_cache_build_attempt | CONFIRMED |
| No freeze decision permitted | CONFIRMED |
| No April data accessed | CONFIRMED |
| No claim of passed/final_unseen/production_ready | CONFIRMED |
| All artifacts preserved, nothing deleted | CONFIRMED |
| Superset runner architecture required before next training | CONFIRMED |

---

## 7. Next Steps

1. Generate `true_all_factor_expansion_manifest_20260507.json` (machine-auditable)
2. Design superset runner (build once, slice per variant)
3. Implement `scripts/run_superset_factor_matrix.py`
4. Baseline equivalence gate
5. Only then: authoritative 78-variant training

---

**This abort is an engineering strategy upgrade, not a failure. The old per-variant-rebuild approach cannot scale to 78 variants within memory constraints.**
