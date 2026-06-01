# Phase A: P0 Fix Report - 2026-05-09

## Audit Scope

Audited the current best S2 candidate (`S2_fw_step1_try_add_C138`, Wilson 95% = 0.7731) for:
1. Factor availability catalog accuracy
2. Selected features P0 compliance  
3. Web/live script consistency
4. Asof rule compliance (training vs live)

## P0 Findings (6 total)

### 1. CYQ/Chip Asof Mismatch (2 features)

| Feature | Training Asof | Live Asof | Mismatch |
|---------|--------------|-----------|----------|
| `tushare_winner_rate` | T-day post_close_settlement | T-1 cyq_perf | YES - P0 |
| `tushare_cost_concentration` | T-day post_close_settlement | T-1 cyq_perf | YES - P0 |

**Root cause:** Training feature builder uses T-day EOD cyq_perf data (available after market close). Live scripts (`realtime_1457_today_probe.py`) fetch T-1 data from cyq_perf API. The model was trained seeing "today's chip distribution" but live can only provide "yesterday's chip distribution".

**Note:** `tushare_cost_position` is also in the feature pool but was NOT selected by stable_tail for this variant.

### 2. THS Sector Web-FORBIDDEN (4 features)

| Feature | In selected_features | In web FORBIDDEN list | Result |
|---------|---------------------|----------------------|--------|
| `sector_pct_change_best` | YES | YES | P0 |
| `sector_strength_rank` | YES | YES | P0 |
| `sector_limit_up_count` | YES | YES | P0 |
| `sector_duration_days` | YES | YES | P0 |

**Root cause:** The S1_14 policy grid treated THS as `live_pool_proxy=include`, meaning sector features were allowed into the pool. But the web deployment scripts (`serve_1457_picker_web.py`, `run_1457_live_sim.py`) classify ALL THS sector features as FORBIDDEN because no realtime proxy has been implemented.

### 3. Catalog v1 Inconsistency (Fixed in v2)

| Feature | Catalog v1 | Web Script | Correct |
|---------|-----------|------------|---------|
| `tushare_net_mf_amount` | Class A | HARD_MONEYFLOW (forbidden) | B (not same semantics as push2 f62) |
| `tushare_ff_adjusted_flow` | Class A | HARD_MONEYFLOW (forbidden) | B (depends on net_mf_amount) |

**Note:** These two features are NOT in the current selected_features (net_mf_amount was not picked by stable_tail, ff_adjusted_flow was excluded via C004 factor exclusion). So this is a catalog accuracy issue, not a deployment P0 for the current candidate.

## What IS Clean

- All Class C moneyflow breakdown features correctly excluded
- All post-close features correctly excluded  
- No `tushare_net_mf_amount` or `tushare_ff_adjusted_flow` in selected features
- No `cross_` prefix features (correctly excluded)
- Training window is correct (2023-05 to 2025-12-31)
- Test window is correct (Q1 2026 seen_research)

## Remediation for Phase B

The current best candidate CANNOT be deployed. For Phase B, we will construct **P0-free variants** by:

1. **Variant DELETE-ALL**: Add all 6 P0 features + their `_available` columns to exclusion, retrain
2. **Variant DELETE-SECTOR-ONLY**: Add 4 THS sector features to exclusion, keep chip with T-1 lag
3. **Variant EXPANDED-EXCLUSION**: Add all P0 features + `tushare_net_mf_amount` + `tushare_ff_adjusted_flow` to exclusion (belt-and-suspenders)

Each variant must be re-run through the probe with the updated exclusion list and measured against the same Q1 seen_research window.

## Catalog v2 Status

Created: `E:\ashare_similarity_runtime\data\reports\prediction\factor_availability_catalog_v2_20260509.json`

Key changes:
- `tushare_net_mf_amount`: A → B
- `tushare_ff_adjusted_flow`: A → B  
- CYQ features: B with P0_asof_mismatch flag
- THS sector: split into individual columns with per-column classification
- New EM push2 f62 proxies: D_backlog (no training data)

## Phase A Self-Audit

| Check | Result |
|-------|--------|
| Catalog v2 produced | PASS |
| Selected feature audit produced | PASS |
| P0 findings documented | PASS (6 P0s) |
| Remediation plan defined | PASS |
| Web/live consistency documented | PASS |
| No changes to training or scripts (audit only) | PASS |

**Phase A verdict: COMPLETE. Proceeding to Phase B.**
