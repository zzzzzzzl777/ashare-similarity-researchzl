# Phase 7 Layer 4: S4 Model HPO - 2026-05-09

## Results

| Variant | Family | Budget | Model | HC Acc | N | W95 | Brier | Pass |
|---------|--------|--------|-------|--------|---|-----|-------|------|
| S4_family_all_budget260 | all | 260 | gpu_catboost_expressive | 0.7667 | 9636 | 0.7582 | 0.1717 | YES |
| S4_family_tree_budget260 | tree | 260 | gpu_catboost_expressive | 0.7723 | 9579 | 0.7638 | 0.1693 | YES |
| S4_seed43_tree | tree | 260 | gpu_catboost | 0.752 | 10358 | 0.7436 | 0.1864 | NO |
| S4_seed44_tree | tree | 260 | stacking_average_top3 | 0.7592 | 10628 | 0.751 | 0.1786 | YES |
| S4_seed45_tree | tree | 260 | stacking_average_top3 | 0.7444 | 11480 | 0.7364 | 0.1874 | NO |
| S4_seed46_tree | tree | 260 | stacking_average_top3 | 0.746 | 10826 | 0.7377 | 0.1857 | NO |

## Best: S4_family_tree_budget260 W95=0.7638