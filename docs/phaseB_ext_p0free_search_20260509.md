# Phase B Extension: Expanded P0-Free Search - 2026-05-09

## Search Space

- Budget sweep: 180/220/260/320/480
- Factor drop: remove weakest from best 9
- Factor add: add remaining factors from 18-pool
- All 18 factors with multiple budgets
- No factor exclusion (maximum pool)

## Results Table

| Variant | Budget | Factors | Model | HC Acc | N | W95 | P0 | Pass |
|---------|--------|---------|-------|--------|---|-----|-----|------|
| Bext_9f_budget180 | 180 | 9 | gpu_catboost_expressive | 0.7716 | 9069 | 0.7629 | 0 | YES |
| Bext_9f_budget320 | 320 | 9 | gpu_lightgbm | 0.7583 | 10750 | 0.7501 | 0 | YES |
| Bext_nofactor_budget320 | 320 | ALL | gpu_catboost_expressive | 0.7583 | 10336 | 0.75 | 0 | NO |
| Bext_all18_budget320 | 320 | 18 | gpu_catboost_expressive | 0.7562 | 10190 | 0.7478 | 0 | NO |
| Bext_drop_C133 | 260 | 8 | stacking_average_top3 | 0.7557 | 10361 | 0.7474 | 0 | NO |
| Bext_all18_budget260 | 260 | 18 | stacking_average_top3 | 0.7548 | 10698 | 0.7466 | 0 | NO |
| Bext_drop_C159 | 260 | 8 | gpu_catboost | 0.7524 | 11151 | 0.7443 | 0 | NO |
| Bext_nofactor_budget260 | 260 | ALL | gpu_catboost_expressive | 0.7513 | 11517 | 0.7433 | 0 | NO |
| Bext_drop_C138 | 260 | 8 | gpu_catboost_expressive | 0.7514 | 10717 | 0.7432 | 0 | NO |
| Bext_drop_C158 | 260 | 8 | stacking_average_top3 | 0.7512 | 11172 | 0.7431 | 0 | NO |
| Bext_drop_C134 | 260 | 8 | gpu_catboost_expressive | 0.7495 | 10975 | 0.7413 | 0 | NO |
| Bext_nofactor_budget480 | 480 | ALL | stacking_average_top3 | 0.7486 | 10871 | 0.7404 | 0 | NO |
| Bext_drop_C011 | 260 | 8 | gpu_catboost_expressive | 0.7485 | 10970 | 0.7403 | 0 | NO |
| Bext_drop_C156 | 260 | 8 | stacking_average_top3 | 0.7484 | 11103 | 0.7402 | 0 | NO |
| Bext_drop_C161 | 260 | 8 | gpu_catboost_expressive | 0.7482 | 11571 | 0.7402 | 0 | NO |
| Bext_add_C136 | 260 | 10 | gpu_catboost_expressive | 0.747 | 11388 | 0.7389 | 0 | NO |
| Bext_add_C162 | 260 | 10 | gpu_catboost_expressive | 0.7471 | 11078 | 0.7389 | 0 | NO |
| Bext_add_C004 | 260 | 10 | gpu_catboost_expressive | 0.7466 | 11346 | 0.7385 | 0 | NO |
| Bext_9f_budget480 | 480 | 9 | stacking_average_top3 | 0.7455 | 10503 | 0.7371 | 0 | NO |
| Bext_drop_C154 | 260 | 8 | stacking_average_top3 | 0.745 | 11688 | 0.737 | 0 | NO |
| Bext_all18_budget480 | 480 | 18 | stacking_average_top3 | 0.7441 | 11397 | 0.736 | 0 | NO |
| Bext_add_C157 | 260 | 10 | gpu_catboost_expressive | 0.744 | 10839 | 0.7357 | 0 | NO |
| Bext_9f_budget220 | 220 | 9 | gpu_catboost_expressive | 0.7429 | 11207 | 0.7348 | 0 | NO |
| Bext_add_C141 | 260 | 10 | gpu_catboost_expressive | 0.7415 | 11498 | 0.7334 | 0 | NO |
| Bext_add_C152 | 260 | 10 | gpu_catboost_expressive | 0.7415 | 11027 | 0.7333 | 0 | NO |
| Bext_add_C151 | 260 | 10 | gpu_catboost_expressive | 0.741 | 11242 | 0.7328 | 0 | NO |
| Bext_add_C137 | 260 | 10 | gpu_catboost_expressive | 0.7389 | 12346 | 0.731 | 0 | NO |
| Bext_add_C143 | 260 | 10 | gpu_catboost_expressive | 0.7374 | 11715 | 0.7294 | 0 | NO |

## Gate Decision

**PROCEED to Phase C** with Bext_9f_budget180 (W95=0.7629)