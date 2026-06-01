# Factor Registry Audit 2026-05-15

Scope: C223-C292 from batch `candidates_20260515_shortline_full_expansion`.

## Result

- Registry structure is valid: C001-C292 are contiguous, unique, and no normalized factor names are duplicated.
- No C223-C292 entries claim `is_passed`, `is_final_unseen`, or `is_frozen_modified`.
- C223-C292 are all still `training_status=not_trained` and `lockbox_role=research_candidate`.
- This audit does not train, does not run `gpu_probe`, and does not change model code.

## Audit Flags

| Flag | Count | Meaning |
|---|---:|---|
| window_lock_required | 10 | Lookback, half-life, or rank universe must be frozen before training. |
| formula_lock_required | 17 | Formula is not yet atomic enough; split or freeze the exact deterministic formula. |
| external_pipeline_required | 32 | Needs a source pipeline/cache before training. |
| overlap_watch | 13 | Similar to an older candidate; keep only if the new definition is materially different. |

## First Wave After Data Cache

These are the safest short-line candidates to hand to engineering/training after the matching data cache exists:

- P0: C229, C236, C244, C246, C248, C252, C254, C258, C260, C270, C272, C279
- P1: C247, C259, C273, C280
- P2: none

Do not hand off the whole C223-C292 batch as a single experiment. Use small ablation groups, keep `factor_id` lineage, and record selected/unselected features back into the registry after training.

## Formula Corrections Applied

- C278: locked to a WQ-style rolling correlation/decay definition; no post-hoc sign selection by validation.
- C279: locked to `sign(delta(volume, 1)) * (-(close / close.shift(1) - 1))`.
- C280: locked to `(close - open) / max(high - low, eps)`; optional neutralization must be a separate feature.

## High-Overlap Watchlist

| Candidate | Watch Against |
|---|---|
| C224 | C059 limit_theme_breadth |
| C227 | C085 pullback_support_ratio |
| C229 | C205 holdertrade_net_buy_ratio |
| C246 | C008 seal_strength_proxy |
| C248 | C191 attack_volume_real_1min |
| C253 | C166 late_seal_ratio |
| C255 | C192 dynamic_volume_acceleration_1min |
| C258 | C190 first_5min_strength_1min |
| C259 | C190 first_5min_strength_1min |
| C261 | C029 weak_to_strong_signal |
| C263 | C040 intraday_break_count |
| C277 | C181 trapped_volume |
| C278 | C118 volume_price_divergence_5, C125 volume_price_spread |

## Data/Formula Gates

- JSON audit file: `E:\ashare_similarity_runtime\data\reports\prediction\factor_registry_audit_20260515.json`
- Registry JSON updated: `E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json`
- Human registry index updated: `C:\Users\zzzzzzl\Desktop\subagent\docs\factor_registry.md`

## Raw Pool Residual Check

`raw_factor_pool_index.json` remains a source-material pool, not a ready training catalog. Exact-name matching is intentionally conservative; many unmatched raw entries are aliases, duplicates, trading rules, vague concepts, or require formula/data gates before promotion.

- Raw records parsed: 3075
- Unique raw names: 2421
- Exact raw-name matches to registry names: 54
- Exact raw-name unmatched: 2367
- Short-line unmatched keyword counts: {'minute': 9, '5min': 7, 'auction': 64, 'limit': 72, 'seal': 48, 'board': 109, 'lhb': 9, 'dragon': 8, 'top': 20, 'hot': 11, 'theme': 32, 'sector': 44, 'announcement': 8, 'float': 5}

