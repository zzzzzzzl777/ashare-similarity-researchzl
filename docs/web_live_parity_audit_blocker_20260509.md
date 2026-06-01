# Web/Live Parity Audit — BLOCKER Report

**Date**: 2026-05-09  
**Auditor**: Automated (Claude Code)  
**Overall Verdict**: **FAIL — BLOCKER**  
**Blocker**: U95 bundle is incompatible with the live-strict execution gate

---

## Executive Summary

The validated U95 bundle (`gpu_probe_20260505T113406Z_bb25159b`) **cannot be deployed** in the 14:57 live scoring path because it selects 11 THS sector features that require post-close data (published after 15:00). The live script's `STRICT_FORBIDDEN_SELECTED_FEATURES` gate correctly detects this and would abort with FATAL error.

The currently deployed bundle (`gpu_probe_20260508T061653Z_d2a985a5`) was intentionally designed to avoid sector features and passes the live-strict gate — this is why it was deployed in the first place.

**The original audit recommendation ("swap to U95") was incorrect.** Swapping would break the live system.

---

## Root Cause Analysis

| Fact | Detail |
|------|--------|
| U95 bundle name | "U95_chip_t1_no_ths_live_strict" |
| Expected meaning | No THS sector features in selected set |
| Actual state | 11 THS sector-derived features in selected set |
| Why "no_ths" is misleading | Bundle was validated offline; "no_ths" may refer to a training-time exclusion that was relaxed or a naming error |

### THS Sector Features — Data Dependency

These features are computed by `build_ths_sector_factors()` from:
- `ths_daily/*.parquet` — THS concept sector daily pct_change (published AFTER 15:00)
- `ths_member/all_members.parquet` — stock-to-concept mapping
- `limit_list_d/*.parquet` — daily limit events

**Metadata**: `asof_time="after_close"`, `lag_rule="T day THS concept data; use for T+1 prediction only"`

At 14:57, T-day THS data does not exist yet. The live script correctly uses `empty_ths_live_factor()` which returns zero-filled values. A model that selects these features would score on zeros instead of real values — hence the strict gate.

---

## Forbidden Features in U95 Selected Set

| Feature | Meaning |
|---------|---------|
| `sector_divergence` | Concept sector divergence from broad market |
| `sector_divergence_available` | Data availability flag |
| `sector_duration_days` | Days since sector trend started |
| `sector_duration_days_available` | Data availability flag |
| `sector_limit_up_count` | Limit-up events in concept sector |
| `sector_limit_up_count_available` | Data availability flag |
| `sector_pct_change_best` | Best concept sector's pct change |
| `sector_pct_change_best_available` | Data availability flag |
| `sector_strength_rank` | Rank of stock's sector strength |
| `sector_strength_rank_available` | Data availability flag |
| `sector_climax_signal_available` | Sector climax signal availability flag |

**Total: 11 features that would be zero-filled at 14:57** (out of 260 selected)

---

## Comparison: U95 vs Current Live Bundle

| Attribute | U95 (bb25159b) | Live (d2a985a5) |
|-----------|----------------|-----------------|
| Members | 3× LightGBM | 1× LGB + 2× CatBoost |
| Full features | 376 | 735 |
| Selected features | 260 | 260 |
| Shared selected | 184 | 184 |
| Sector features in selected | **11** | **0** |
| STRICT_FORBIDDEN gate | **FAIL (abort)** | **PASS** |
| Q1 HC accuracy | 75.42% | 75.42% |
| Q1 Wilson@0.75 | 0.7461 | 0.7461 |
| Lockbox status | N/A | seen_research |
| Live-deployable | **NO** | YES |

---

## What Was Attempted and Reverted

1. **Attempted**: Changed `BUNDLE_PATH` / `DEFAULT_BUNDLE` in all three live scripts to U95
2. **Discovered**: U95 would trigger `STRICT_FORBIDDEN_SELECTED_FEATURES` gate → FATAL abort
3. **Reverted**: All three scripts restored to original live bundle (`d2a985a5`)

Scripts remain in their original state. Backup files (`.bak_20260509_0010`) preserved.

---

## Options to Resolve

### Option A: Build a True "Live-Strict" U95 Variant

Re-run the U95 ensemble pipeline with sector features excluded from the feature pool:
1. Take the same 376 features, remove 12 sector features → 364 features
2. Re-run stable_tail feature selection to get 249-260 selected features
3. Re-train 3× LightGBM ensemble on remaining features
4. Apply isotonic calibration
5. Validate on Q1 + April holdout

**Pros**: Clean solution, verified architecture, no sector dependency  
**Cons**: May lose some accuracy (sector features had predictive value in offline validation)

### Option B: Accept the Current Live Bundle with Formal Validation

The 20260508 bundle achieves identical Q1 metrics and passes the live-strict gate. It needs:
1. Formal Q1 + April holdout evaluation (same protocol as U95)
2. Comparison against U95's offline metrics
3. Lockbox "seen_research" → formal acceptance or new lockbox
4. Decision document recording why a non-U95 bundle is used

**Pros**: No code changes, already running  
**Cons**: Lockbox violation, different architecture (CatBoost members), "seen_research" flag

### Option C: Add T-1 Lagged Sector Feature Support to Live Path

Modify the live script to fetch T-1 (yesterday's) THS sector data instead of zero-filling:
1. Change `empty_ths_live_factor()` to load previous trading day's THS data
2. Remove sector features from `STRICT_FORBIDDEN_SELECTED_FEATURES`
3. Keep the gate for post-close-only features (margin, LHB, etc.)
4. Validate that T-1 lagged sector features have similar predictive power

**Pros**: U95 bundle becomes live-compatible  
**Cons**: Model was trained on T-day sector data, not T-1 — prediction quality may degrade; requires code change + re-validation

### Option D: Create New "Sector-Excluded" Feature Selection for U95 Architecture

Keep the exact same 3× LightGBM models (no retraining) but generate a new `selected_indices` that excludes sector features:
1. Take U95's 260 selected features
2. Remove 11 sector features → 249 features
3. Either: accept 249 features (fewer), or re-run selection to pick 11 replacements from remaining pool

**Pros**: Same models, same weights, just different feature mask  
**Cons**: Removing features changes predictions — 11 features that contributed to 75.42% accuracy would be zero-filled or absent; not validated at 249 features

---

## Recommended Path

**Option A** is the cleanest but requires compute time. **Option B** is the fastest path to production with a validated live bundle.

The critical next step is a **user decision**: which option to pursue.

---

## Audit Gate Status (Final)

| Check | Status | Notes |
|-------|--------|-------|
| Bundle identity match | **BLOCKED** | U95 cannot run in live-strict path |
| Feature parity | **N/A** | Cannot assess until compatible bundle identified |
| P0 strict (live bundle) | PASS | Current live bundle passes strict gate |
| P0 strict (U95 bundle) | **FAIL** | 11 sector features in STRICT_FORBIDDEN |
| Replay numeric | **N/A** | No valid target bundle for live path |
| Web/API output | RUNNING (with unvalidated bundle) | System operational, model unvalidated |
| **OVERALL** | **FAIL — BLOCKER** | No validated live-compatible bundle exists |

---

## Files Modified / Referenced

| File | Action |
|------|--------|
| `scripts/realtime_1457_today_probe.py` | Attempted swap → reverted to original |
| `scripts/serve_1457_picker_web.py` | Attempted swap → reverted to original |
| `scripts/run_1457_live_sim.py` | Attempted swap → reverted to original |
| `*.bak_20260509_0010` | Backups preserved (original state) |
| `runs/gpu_probe_20260505T113406Z_bb25159b/` | U95 bundle (offline-only) |
| `runs/gpu_probe_20260508T061653Z_d2a985a5/` | Current live bundle |
