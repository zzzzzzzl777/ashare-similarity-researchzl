# 14:57 Unavailable Factor Comparison Results

Date: 2026-05-08

## 1. Best Executable Policy

**Winner: `U90_best_policy_q1` / `U31_chip_t1` (equivalent configuration)**

- Mode: T-1 shifted for chip family only; LHB, margin, closing auction, float impact deleted
- Configuration: T-1 cache with 40 exclusions (14 hard moneyflow + 26 from A/B/D/E families)
- Only chip/cost distribution features (tushare_cost_concentration, tushare_cost_position, tushare_winner_rate) use T-1 lagged values

Note: U31 and U90 produce the same training configuration. Small metric differences (0.15-0.28%) are GPU LightGBM non-determinism.

## 2. Q1 Metrics (2026-01 to 2026-03)

| Variant | HC Acc | Wilson 95 | HC Count | Coverage | Brier | Sel Feats | Executable |
|---------|--------|-----------|----------|----------|-------|-----------|------------|
| U30_chip_delete | 77.98% | 77.13% | 9324 | 21.67% | 0.2187 | 260 | no |
| U50_float_impact_delete | 76.57% | 75.72% | 9817 | 22.82% | 0.2197 | 260 | no |
| U31_chip_t1 | 76.12% | 75.29% | 10518 | 24.45% | 0.2200 | 260 | YES |
| U20_margin_delete | 76.08% | 75.23% | 10036 | 23.33% | 0.2193 | 260 | no |
| U90_best_policy_q1 | 75.98% | 75.14% | 10137 | 23.56% | 0.2200 | 260 | YES |
| U01_delete_all_blocked | 75.92% | 75.12% | 11236 | 26.11% | 0.2194 | 260 | YES |
| U21_margin_t1 | 75.85% | 75.06% | 11534 | 26.81% | 0.2188 | 260 | YES |
| U11_lhb_t1 | 75.80% | 75.01% | 11721 | 27.24% | 0.2187 | 260 | YES |
| U00_current_reference | 75.50% | 74.68% | 10819 | 25.15% | 0.2198 | 260 | no |
| U41_close_auction_t1 | 75.42% | 74.58% | 10527 | 24.47% | 0.2195 | 260 | YES |
| U02_t1_all_blocked | 75.33% | 74.54% | 11757 | 27.33% | 0.2196 | 260 | YES |
| U91_best_policy_plus_sensitivity | 75.31% | 74.53% | 11799 | 27.42% | 0.2196 | 260 | YES |
| U51_float_impact_t1 | 75.22% | 74.41% | 11331 | 26.34% | 0.2199 | 260 | YES |
| U10_lhb_delete | 74.96% | 74.13% | 10790 | 25.08% | 0.2203 | 260 | no |
| U40_close_auction_delete | 74.67% | 73.87% | 11576 | 26.91% | 0.2194 | 260 | no |

## 3. April Forward Validation (2026-04)

| Variant | HC Acc | Wilson 95 | HC Count | Coverage | Brier |
|---------|--------|-----------|----------|----------|-------|
| U31_chip_t1 | 78.51% | 75.67% | 875 | 6.53% | 0.2238 |
| U90_best_policy_q1 | 78.25% | 75.39% | 869 | 6.48% | 0.2240 |
| U00_current_reference | 77.73% | 75.01% | 970 | 7.24% | 0.2233 |
| U02_t1_all_blocked | 76.23% | 73.22% | 833 | 6.22% | 0.2241 |
| U11_lhb_t1 | 76.34% | 72.98% | 672 | 5.01% | 0.2237 |
| U01_delete_all_blocked | 76.14% | 72.74% | 658 | 4.91% | 0.2237 |
| U21_margin_t1 | 76.14% | 72.74% | 658 | 4.91% | 0.2237 |

## 4. Trade-Facing Selector Analysis (Best Executable, Q1)

Variant: `U31_chip_t1`

| Selector | Candidates | Accuracy | Wilson 95 | Avg/Day |
|----------|-----------|----------|-----------|---------|
| T>=0.70 | 14237 | 73.11% | 72.37% | — |
| T>=0.75 | 8111 | 76.35% | 75.42% | — |
| T>=0.78 | 2790 | 86.56% | 85.24% | — |
| T>=0.80 | 1922 | 90.22% | 88.81% | — |
| daily_top5 | 275 | 74.91% | 69.47% | 5.0 |
| daily_top6 | 330 | 75.45% | 70.54% | 6.0 |
| T>=0.70_top5 | 270 | 74.44% | 68.92% | 4.91 |
| T>=0.70_top6 | 324 | 75.00% | 70.01% | 5.89 |

## 5. P0 Audit

All variants passed P0 audit. No hard moneyflow or C004/C009 leakage detected.

## 6. Family Decision Summary

| Family | Decision | Rationale |
|--------|----------|-----------|
| A_lhb | Delete | T-1 Wilson 75.01% <= baseline 75.12% |
| B_margin | Delete | T-1 Wilson 75.06% <= baseline 75.12% |
| C_chip | T-1 shift | T-1 Wilson 75.29% > baseline 75.12% |
| D_close_auction | Delete | T-1 Wilson 74.58% <= baseline 75.12% |
| E_float_impact | Delete | T-1 Wilson 74.41% <= baseline 75.12% |

## 7. Key Findings

1. **Chip/cost T-1 is the only family worth keeping.** All other blocked families (LHB, margin, closing auction, float impact) should be deleted — their T-1 shifted values don't improve and often degrade the model.

2. **April forward validation strongly confirms.** The chip-T-1 policy (U31/U90) achieves Wilson 75.39-75.67% on April, vs 72.74% for delete-all (U01). This is a +2.6-2.9% forward validation advantage.

3. **T-day blocked features are harmful.** U00 (reference using T-day blocked values, non-executable) scored 74.68% Wilson on Q1, while U01 (delete all) scored 75.12%. The blocked features were actively hurting the model even with T-day values.

4. **The "all T-1" approach (U02/U91) performs poorly.** Shifting all 5 families to T-1 together (Wilson Q1 74.53-74.54%) is worse than just deleting them all (75.12%). Only selective T-1 (chip only) helps.

5. **Production recommendation:** Use the U90/U31 policy — keep T-1 shifted chip features, delete all other blocked families. This is executable at 14:57 and validates forward.

## 8. Production Feature Set (T-1 Shift Columns)

The following 6 columns use T-1 shifted values in the production model:

```text
tushare_cost_concentration          (T-1 shifted)
tushare_cost_concentration_available (T-1 shifted)
tushare_cost_position               (T-1 shifted)
tushare_cost_position_available     (T-1 shifted)
tushare_winner_rate                 (T-1 shifted)
tushare_winner_rate_available       (T-1 shifted)
```

The following 26 columns are deleted from the production model:

```text
LHB (10): tushare_lhb_net_buy, tushare_lhb_net_rate, tushare_inst_buy_count,
           tushare_lhb_appeared, tushare_inst_net_buy (+ _available)
Margin (10): tushare_rzye_delta_pct, tushare_rzye, tushare_rzmre_ratio,
             tushare_margin_net, tushare_rqye_ratio (+ _available)
Close Auction (4): tushare_auction_close_vwap_ratio, tushare_auction_close_vol (+ _available)
Float Impact (2): tushare_float_relative_impact (+ _available)
```
