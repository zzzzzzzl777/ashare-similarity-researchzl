# Raw vs Isotonic Ranking Compare - 2026-05-09

## Method
- Frozen bundle score-only; no retraining.
- raw_prob = average model predict_proba before isotonic.
- iso_prob = raw_prob after bundle isotonic model.
- Ranking metrics: AUC/AP/topK. Threshold metrics: fixed probability cutoffs.

## april_2026
- Rows: 15040, trading days: 21

| Score | AUC | AP | unique scores | top6 acc | top6 W95 | top6 p>0.75 count | top6 p>0.75 acc | p>0.75 count | p>0.75 acc | p>=0.80 count | p>=0.80 acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| raw_prob | 0.574014 | 0.716164 | 14175 | 0.793651 | 0.714814 | 62 | 0.854839 | 467 | 0.824411 | 32 | 0.90625 |
| iso_prob | 0.573819 | 0.712711 | 70 | 0.777778 | 0.697578 | 101 | 0.811881 | 668 | 0.812874 | 194 | 0.876289 |

### Equal-count overall TopN

| N | raw acc | raw W95 | raw days | iso acc | iso W95 | iso days | winner |
|---:|---:|---:|---:|---:|---:|---:|---|
| 20 | 1.0 | 0.83887 | 1 | 0.95 | 0.763864 | 1 | raw_prob |
| 24 | 0.916667 | 0.741508 | 2 | 0.916667 | 0.741508 | 2 | tie |
| 30 | 0.9 | 0.743786 | 2 | 0.933333 | 0.786762 | 2 | iso_prob |
| 32 | 0.90625 | 0.757815 | 2 | 0.9375 | 0.798525 | 2 | iso_prob |
| 50 | 0.92 | 0.811615 | 4 | 0.92 | 0.811615 | 5 | tie |
| 100 | 0.92 | 0.850017 | 8 | 0.91 | 0.837736 | 5 | raw_prob |
| 121 | 0.92562 | 0.864668 | 8 | 0.892562 | 0.824833 | 5 | raw_prob |
| 150 | 0.92 | 0.865377 | 9 | 0.906667 | 0.849435 | 8 | raw_prob |
| 194 | 0.876289 | 0.822524 | 9 | 0.876289 | 0.822524 | 9 | tie |
| 200 | 0.88 | 0.827656 | 9 | 0.875 | 0.821985 | 9 | raw_prob |
| 300 | 0.843333 | 0.797891 | 10 | 0.84 | 0.794255 | 10 | raw_prob |
| 467 | 0.824411 | 0.787296 | 12 | 0.841542 | 0.805653 | 12 | iso_prob |
| 500 | 0.824 | 0.788185 | 12 | 0.824 | 0.788185 | 12 | tie |
| 565 | 0.815929 | 0.781876 | 12 | 0.815929 | 0.781876 | 12 | tie |
| 668 | 0.812874 | 0.781539 | 13 | 0.812874 | 0.781539 | 13 | tie |
| 800 | 0.78375 | 0.753901 | 15 | 0.78375 | 0.753901 | 15 | tie |
| 1000 | 0.769 | 0.741877 | 18 | 0.768 | 0.740842 | 18 | raw_prob |
| 1500 | 0.75 | 0.727467 | 21 | 0.741333 | 0.718576 | 20 | raw_prob |
| 1920 | 0.740625 | 0.720553 | 21 | 0.740625 | 0.720553 | 21 | tie |
| 1930 | 0.740933 | 0.720921 | 21 | 0.740933 | 0.720921 | 21 | tie |
| 2000 | 0.742 | 0.722373 | 21 | 0.735 | 0.715221 | 21 | raw_prob |

## pretrain_2023_02_04
- Rows: 19549, trading days: 61

| Score | AUC | AP | unique scores | top6 acc | top6 W95 | top6 p>0.75 count | top6 p>0.75 acc | p>0.75 count | p>0.75 acc | p>=0.80 count | p>=0.80 acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| raw_prob | 0.608509 | 0.680993 | 19499 | 0.770492 | 0.724732 | 92 | 0.804348 | 605 | 0.752066 | 147 | 0.809524 |
| iso_prob | 0.608462 | 0.676583 | 75 | 0.773224 | 0.727614 | 217 | 0.83871 | 793 | 0.757881 | 350 | 0.76 |

### Equal-count overall TopN

| N | raw acc | raw W95 | raw days | iso acc | iso W95 | iso days | winner |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 1.0 | 0.206543 | 1 | 1.0 | 0.206543 | 1 | tie |
| 20 | 0.95 | 0.763864 | 1 | 0.85 | 0.639577 | 1 | raw_prob |
| 30 | 0.933333 | 0.786762 | 2 | 0.9 | 0.743786 | 1 | raw_prob |
| 50 | 0.9 | 0.786395 | 2 | 0.92 | 0.811615 | 1 | iso_prob |
| 100 | 0.84 | 0.755796 | 2 | 0.84 | 0.755796 | 3 | tie |
| 123 | 0.813008 | 0.735014 | 3 | 0.813008 | 0.735014 | 3 | tie |
| 147 | 0.809524 | 0.738481 | 4 | 0.809524 | 0.738481 | 5 | tie |
| 150 | 0.813333 | 0.743441 | 4 | 0.813333 | 0.743441 | 5 | tie |
| 200 | 0.785 | 0.722976 | 6 | 0.8 | 0.739144 | 5 | iso_prob |
| 292 | 0.760274 | 0.708129 | 8 | 0.75 | 0.697304 | 9 | raw_prob |
| 300 | 0.753333 | 0.701554 | 8 | 0.75 | 0.698047 | 9 | raw_prob |
| 350 | 0.76 | 0.712587 | 12 | 0.76 | 0.712587 | 12 | tie |
| 500 | 0.758 | 0.718583 | 20 | 0.758 | 0.718583 | 20 | tie |
| 605 | 0.752066 | 0.716138 | 28 | 0.758678 | 0.723018 | 28 | iso_prob |
| 699 | 0.756795 | 0.723643 | 32 | 0.756795 | 0.723643 | 32 | tie |
| 793 | 0.757881 | 0.726869 | 39 | 0.757881 | 0.726869 | 39 | tie |
| 800 | 0.7525 | 0.721435 | 39 | 0.75375 | 0.722729 | 40 | iso_prob |
| 1000 | 0.75 | 0.722239 | 43 | 0.75 | 0.722239 | 45 | tie |
| 1500 | 0.742 | 0.719259 | 50 | 0.755333 | 0.732944 | 50 | iso_prob |
| 1932 | 0.743271 | 0.723323 | 55 | 0.742754 | 0.722794 | 55 | raw_prob |
| 1936 | 0.743285 | 0.723358 | 55 | 0.743285 | 0.723358 | 55 | tie |
| 2000 | 0.739 | 0.719307 | 56 | 0.7395 | 0.719818 | 56 | iso_prob |

## Notes
- If AUC/AP/topK are nearly identical, raw and isotonic have the same ranking; choose by threshold behavior and live interpretability.
- If iso unique score count is much lower, isotonic is creating probability plateaus, which can increase same-score ties.
- Daily detail CSV: `E:\ashare_similarity_runtime\data\reports\prediction\raw_vs_isotonic_rank_compare_daily_20260509.csv`
- Fine threshold curve CSV: `E:\ashare_similarity_runtime\data\reports\prediction\raw_vs_isotonic_threshold_curve_20260509.csv`