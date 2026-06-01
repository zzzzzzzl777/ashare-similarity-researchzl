# Phase 7 Layer 1: S1 Policy Grid Results - 2026-05-09

## Results (sorted by Wilson 95%)

| # | Variant | chip | hot | tgb | ths | HC Acc | N | Wilson 95% | Pass |
|---|---------|------|-----|-----|-----|--------|---|------------|------|
| 1 | S1_14_chip=T1_proxy_hot=delete_tgb=delete_ths=live_pool_proxy | T1_proxy | delete | delete | live_pool_proxy | 0.7729 | 10321 | 0.7647 | YES |
| 2 | S1_12_chip=T1_proxy_hot=delete_tgb=delete_ths=delete | T1_proxy | delete | delete | delete | 0.7660 | 9735 | 0.7575 | YES |
| 3 | S1_09_chip=delete_hot=T1_proxy_tgb=T1_cached_ths=delete | delete | T1_proxy | T1_cached | delete | 0.7656 | 10270 | 0.7573 | YES |
| 4 | S1_16_chip=T1_proxy_hot=delete_tgb=T1_cached_ths=T1_proxy | T1_proxy | delete | T1_cached | T1_proxy | 0.7642 | 10762 | 0.7561 | YES |
| 5 | S1_13_chip=T1_proxy_hot=delete_tgb=delete_ths=T1_proxy | T1_proxy | delete | delete | T1_proxy | 0.7638 | 11087 | 0.7558 | YES |
| 6 | S1_23_chip=T1_proxy_hot=T1_proxy_tgb=T1_cached_ths=live_pool_proxy | T1_proxy | T1_proxy | T1_cached | live_pool_proxy | 0.7611 | 10518 | 0.7528 | YES |
| 7 | S1_04_chip=delete_hot=delete_tgb=T1_cached_ths=T1_proxy | delete | delete | T1_cached | T1_proxy | 0.7606 | 11084 | 0.7526 | YES |
| 8 | S1_22_chip=T1_proxy_hot=T1_proxy_tgb=T1_cached_ths=T1_proxy | T1_proxy | T1_proxy | T1_cached | T1_proxy | 0.7604 | 10962 | 0.7524 | YES |
| 9 | S1_10_chip=delete_hot=T1_proxy_tgb=T1_cached_ths=T1_proxy | delete | T1_proxy | T1_cached | T1_proxy | 0.7596 | 11141 | 0.7516 | YES |
| 10 | S1_20_chip=T1_proxy_hot=T1_proxy_tgb=delete_ths=live_pool_proxy | T1_proxy | T1_proxy | delete | live_pool_proxy | 0.7593 | 11117 | 0.7513 | YES |
| 11 | S1_03_chip=delete_hot=delete_tgb=T1_cached_ths=delete | delete | delete | T1_cached | delete | 0.7589 | 10943 | 0.7508 | YES |
| 12 | S1_05_chip=delete_hot=delete_tgb=T1_cached_ths=live_pool_proxy | delete | delete | T1_cached | live_pool_proxy | 0.7576 | 11636 | 0.7498 | NO |
| 13 | S1_17_chip=T1_proxy_hot=delete_tgb=T1_cached_ths=live_pool_proxy | T1_proxy | delete | T1_cached | live_pool_proxy | 0.7566 | 11429 | 0.7486 | NO |
| 14 | S1_11_chip=delete_hot=T1_proxy_tgb=T1_cached_ths=live_pool_proxy | delete | T1_proxy | T1_cached | live_pool_proxy | 0.7563 | 11653 | 0.7484 | NO |
| 15 | S1_21_chip=T1_proxy_hot=T1_proxy_tgb=T1_cached_ths=delete | T1_proxy | T1_proxy | T1_cached | delete | 0.7555 | 11532 | 0.7475 | NO |
| 16 | S1_19_chip=T1_proxy_hot=T1_proxy_tgb=delete_ths=T1_proxy | T1_proxy | T1_proxy | delete | T1_proxy | 0.7549 | 11460 | 0.7469 | NO |
| 17 | S1_07_chip=delete_hot=T1_proxy_tgb=delete_ths=T1_proxy | delete | T1_proxy | delete | T1_proxy | 0.7547 | 10596 | 0.7464 | NO |
| 18 | S1_02_chip=delete_hot=delete_tgb=delete_ths=live_pool_proxy | delete | delete | delete | live_pool_proxy | 0.7544 | 10944 | 0.7462 | NO |
| 19 | S1_15_chip=T1_proxy_hot=delete_tgb=T1_cached_ths=delete | T1_proxy | delete | T1_cached | delete | 0.7535 | 11138 | 0.7454 | NO |
| 20 | S1_08_chip=delete_hot=T1_proxy_tgb=delete_ths=live_pool_proxy | delete | T1_proxy | delete | live_pool_proxy | 0.7530 | 10684 | 0.7447 | NO |
| 21 | S1_01_chip=delete_hot=delete_tgb=delete_ths=T1_proxy | delete | delete | delete | T1_proxy | 0.7529 | 10409 | 0.7445 | NO |
| 22 | S1_06_chip=delete_hot=T1_proxy_tgb=delete_ths=delete | delete | T1_proxy | delete | delete | 0.7517 | 11653 | 0.7438 | NO |
| 23 | S1_00_chip=delete_hot=delete_tgb=delete_ths=delete | delete | delete | delete | delete | 0.7514 | 11291 | 0.7433 | NO |
| 24 | S1_18_chip=T1_proxy_hot=T1_proxy_tgb=delete_ths=delete | T1_proxy | T1_proxy | delete | delete | 0.7499 | 11041 | 0.7418 | NO |

## Marginal Family Effects

| Family | Avg W95 (include) | Avg W95 (delete) | Delta | Verdict |
|--------|-------------------|------------------|-------|---------|
| chip_cost | 0.7517 | 0.7483 | +0.0034 | Include helps |
| hot_holder_hk | 0.7487 | 0.7513 | -0.0025 | Delete helps |
| tgb | 0.7511 | 0.7489 | +0.0022 | Include helps (weak) |
| ths_sector | 0.7508 | 0.7484 | +0.0024 | Include helps (weak) |

## Key Findings

1. **Best variant**: S1_14 (chip=T1_proxy, hot=delete, tgb=delete, ths=live_pool_proxy) W95=0.7647
2. **+1.11pp over Phase 6 baseline** (0.7536 -> 0.7647) from policy optimization alone
3. **hot_holder_hk has negative marginal effect** — deleting it consistently helps
4. **chip_cost is the strongest positive B-class family** (+0.34pp marginal)
5. **Interaction effects matter**: best variant deletes tgb despite positive marginal effect
6. **11/24 variants pass Wilson >= 75%**, all above 74%
7. **Model selection varies**: stacking_average_top3 wins for several top variants

## Self-Audit Gate

| Check | Result |
|-------|--------|
| All 24 variants completed | PASS |
| 0 errors | PASS |
| train_end = 2025-12-31 (enforced by config) | PASS |
| No April leakage (test_end = 2026-03-30) | PASS |
| HC count > 1000 for all (min 9735) | PASS |
| Coverage > 10% for all (min 22.6%) | PASS |
| Best W95 > 0.75 (0.7647) | PASS |
| Marginal analysis computed | PASS |
| JSON + MD written | PASS |
| P0 issues | 0 |
| P1 issues | 0 |
| Proceed to S2 | YES |