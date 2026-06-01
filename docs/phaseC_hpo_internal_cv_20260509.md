# Phase C: Formal HPO (Internal Rolling CV) - 2026-05-09

## Methodology
- Objective: mean Wilson 95% across 3 expanding-window CV folds within 2023-2025
- Fold 1: train→2024-06-30, val 2024-07→2024-12
- Fold 2: train→2024-12-31, val 2025-01→2025-06
- Fold 3: train→2025-06-30, val 2025-07→2025-12
- Q1 (2026-01 to 2026-03) reported ONLY for winner, NOT in objective
- P0 audit: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C

## HPO Grid Results (seed=42)

| Variant | Budget | Selection | Family | Fold1 | Fold2 | Fold3 | Mean CV W95 | Deployable |
|---------|--------|-----------|--------|-------|-------|-------|-------------|------------|
| HPO_budget200 | 200 | stable_tail | all | 0.686853 | 0.917473 | 0.721861 | 0.775396 | YES |
| HPO_family_tree | 180 | stable_tail | tree | 0.686929 | 0.890184 | 0.74585 | 0.774321 | YES |
| HPO_budget220 | 220 | stable_tail | all | 0.695026 | 0.836286 | 0.7432 | 0.758171 | YES |
| HPO_budget140 | 140 | stable_tail | all | 0.682815 | 0.843112 | 0.717735 | 0.747887 | YES |
| HPO_budget120 | 120 | stable_tail | all | 0.697244 | 0.820566 | 0.697965 | 0.738592 | YES |
| HPO_budget160 | 160 | stable_tail | all | 0.695424 | 0.803828 | 0.714065 | 0.737772 | YES |
| HPO_budget180 | 180 | stable_tail | all | 0.68692 | 0.760348 | 0.759502 | 0.73559 | YES |
| HPO_family_all | 180 | stable_tail | all | 0.686246 | 0.760348 | 0.759502 | 0.735365 | YES |
| HPO_sel_stable_tail | 180 | stable_tail | all | 0.686799 | 0.760348 | 0.74585 | 0.730999 | YES |
| HPO_family_catboost | 180 | stable_tail | catboost | 0.0 | 0.0 | 0.0 | 0.0 | YES |
| HPO_sel_mutual_info | 180 | mutual_info | all | 0.0 | 0.0 | 0.0 | 0.0 | YES |

## Multi-Seed Stability (Top 3)

- **HPO_budget200**: [0.7754, 0.7911, 0.7562] overall=0.7743
- **HPO_family_tree**: [0.7743, 0.7711, 0.7616] overall=0.769
- **HPO_budget220**: [0.7582, 0.7719, 0.7842] overall=0.7714

## HPO Winner: HPO_budget200
- Mean CV W95 (across seeds): 0.7743
- Budget: 200
- Selection: stable_tail
- Family: all

## Q1 Seen-Research Report (Winner Only)
- W95: 0.72875
- HC Accuracy: 0.736911
- HC Count: 11403
- P0: 0

## Gate: PROCEED to Phase D