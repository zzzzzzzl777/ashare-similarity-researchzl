# 14:57 S2 Asof Rehabilitation Notes 2026-05-15

## Purpose

This note corrects an important interpretation risk: S2 should not be treated as a
dead branch just because some older audits used "full-day / post-close" labels.
The useful part of S2 is mostly made of factors that can be rebuilt from a
14:57-asof snapshot or minute bars. The right action is not deletion; it is
semantic rehabilitation and full rolling validation after the true asof cache is ready.

S2 is still not a champion by itself. Its 2026-05-09 stability run failed the
freeze gate, and Q1/April are seen-research only. But S2 is a high-value
candidate family that must be re-tested under true 14:57 semantics.

## Evidence Snapshot

- Best S2 variant: `S2_fw_step1_try_add_C138`.
- Best single-seed Wilson 95: `0.773095`.
- Best factor ids:
  `C154, C156, C134, C011, C138, C133, C161, C159, C158`.
- Stability result: not frozen; mean W95 around `0.7456`, only `2/5` seeds passed.
- Feature overlap versus PhaseC:
  - S2 selected features: `260`.
  - PhaseC selected features: `200`.
  - Shared selected features: `200`.
  - PhaseC-only selected features: `0`.
  - S2-only selected features: `60`.

Interpretation: PhaseC is effectively a strict subset of S2 at the selected-feature
level. The next comparison should focus on the 60 S2-only incremental columns and
the 9-factor S2 logical family under true asof semantics.

## S2 Best 9 Factor Asof Status

| Factor | Column | Correct 14:57 treatment |
|---|---|---|
| C011 | `tushare_auction_open_vwap_ratio` | Strict pre-14:57. Available after the morning auction. |
| C133 | `tushare_last_30min_return` | Recompute from bars ending no later than 14:57. The formal model must not train on 15:00 last-30-minute semantics. |
| C134 | `tushare_first_15min_volume_ratio` | Strictly available from morning minute bars; denominator must match the training asof denominator. |
| C138 | `tushare_high_time_pct` | Recompute high-time position using only the session span up to 14:57. |
| C154 | `tushare_price_vs_cost_20d` | Recompute from historical bars plus a 14:57 synthetic T-day bar. |
| C156 | `tushare_abnormal_3d_deviation` | Use T-day pct change from 14:57 latest price versus previous close. |
| C158 | `tushare_inv_t_20d` | Use asof sign/volume for T day; prior days are final historical bars. |
| C159 | `tushare_asr_60d` | Include T-day asof close in the rolling 60-day structure. |
| C161 | `tushare_illiq_classic_20d` | Use asof pct change and asof amount for T day. |

These factors are not "hard unavailable"; they are `needs_asof_rewrite`.
The training cache and live/Web builder must use the same 14:57 definition.

## S2-Only 60 Selected Columns

The `s2_phasec_feature_diff_20260511.json` artifact shows 60 S2-only selected
columns. Classification by the 2026-05-07 feature catalog:

| Group | Count | Treatment |
|---|---:|---|
| symbol OHLCV derived | 35 | Rebuild from 14:57 synthetic daily bar. |
| market emotion / board structure | 12 | Rebuild from 14:57 whole-market snapshot and limit context. |
| cross-section | 5 | Rebuild from the same 14:57 universe and filters. |
| THS sector | 4 | Rebuild from timestamped sector membership plus 14:57 member returns. |
| Tushare chip/cost | 2 | B-class T-1/proxy only: `tushare_cost_concentration`, `tushare_winner_rate`. |
| Tushare limit type | 1 | Should be re-audited; older catalog marked post-close, newer availability notes treat limit-pool compatibility as live Class A if live limit-pool snapshot has the field. |
| available flag only | 1 | `tushare_seal_ratio_available`; do not keep as an orphan unless parent family parity is proven. |

This means 57/60 are not inherently unusable. Most were only "not strict" because
they were generated from 15:00 full-day bars in the old cache. With true 14:57
asof construction, they become legitimate comparison candidates.

## Misclassification Pattern To Avoid

Do not merge these categories:

1. **Hard unavailable**
   Same-day Tushare moneyflow split, LHB, margin, close auction, and post-close
   settlement fields that cannot be replicated or proxied with the same semantics.

2. **Asof rewrite required**
   Price, volume, amount, K-line, cross-section, minute, and market context
   features that were historically computed at 15:00 but can be rebuilt at 14:57.

3. **Proxy policy**
   Chip/cost or similar delayed data that may be useful as T-1, but must be
   trained under explicit T-1 names/policy and compared against delete.

S2 mainly belongs to category 2, with a small category 3 tail. It should not be
thrown away with category 1.

## Required S2 Re-Test Matrix After Data Completes

Run only after a true `14:57_asof` feature cache exists.

1. `PhaseC_strict_asof_baseline`
2. `S2_best9_asof_rewrite`
3. `PhaseC_plus_S2_only_symbol_ohlcv`
4. `PhaseC_plus_S2_only_market_emotion`
5. `PhaseC_plus_S2_only_cross_section`
6. `PhaseC_plus_S2_only_sector`
7. `PhaseC_plus_S2_chip_T1_policy`
8. `PhaseC_plus_S2_limit_pool_fields`
9. `PhaseC_plus_all_clean_S2_only`
10. `S2_best9_plus_new_1min_first_wave`

All variants must go through full 23-fold `fixed_recent_36m` rolling validation
before any champion decision. Tier screens can rank families, but cannot promote
directly.

## Mandatory Gates

- No selected feature from same-day post-close moneyflow/LHB/margin/close auction.
- No same-name replacement of 15:00 full-day columns with 14:57 live values unless
  the training cache was rebuilt with the same 14:57 semantics.
- No orphan `_available` flag unless the parent feature family is explicitly in scope.
- Chip/cost must be delete-vs-T-1 compared and named as T-1/proxy policy.
- `tushare_limit_type` must be source-audited against live limit pool before inclusion.
- Q1 and April remain score-only seen-research consistency checks.
- Champion must be chosen by full rolling stability, not S2's 2023-02/04 strategy
  strength or PhaseC's April strength.

## Bottom Line

S2 is a rehabilitation candidate, not a rejected route and not an automatic champion.
Once the minute data is complete, the correct next step is to rebuild S2's useful
features under exact 14:57-asof semantics and compare the S2-only increments
against PhaseC across the full fixed_recent_36m rolling protocol.
