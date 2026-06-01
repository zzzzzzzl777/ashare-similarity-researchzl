# 14:57 Daily TopK Selector Probe

Date: 2026-05-08

Scope: post-model selector probe for `M1457_greedy_top8`. Q1 is used for rule search. April is used only as forward replay. This is not final production tuning.

## Baseline

| Window | Rule | Count | Avg/day | Accuracy | Wilson |
|---|---:|---:|---:|---:|---:|
| Q1 | model high-confidence | 8991 | 163.47 | 78.79% | 77.93% |
| April | model high-confidence | 913 | 45.65 | 76.67% | 73.82% |

The baseline high-confidence pool is much larger than the intended trading use case. The real target should be `precision@daily_candidates`, not high-confidence coverage.

## Q1-Selected Practical Rules

These rules use only prediction-time fields available in the prediction parquet: probability, date, close proxy, and turnover proxy. In live 14:57 execution, `close` and `turnover` must be replaced by latest 14:57 price and cumulative turnover approximations.

| Rule | Q1 Count | Q1 Avg/day | Q1 Accuracy | Q1 Wilson | April Count | April Avg/day | April Accuracy | April Wilson |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `prob>=0.80`, daily top10, close 5-60, turnover 3.5-20 | 166 | 3.02 | 84.34% | 78.04% | 57 | 2.85 | 78.95% | 66.71% |
| `prob>=0.80`, daily top10, close >=3, turnover 3.5-20 | 172 | 3.13 | 83.14% | 76.83% | 71 | 3.55 | 80.28% | 69.58% |
| `prob>=0.80`, daily top10, high-score-day gate `count(prob>=0.80)>=5` | 169 | 3.07 | 82.84% | 76.44% | 74 | 3.70 | 81.08% | 70.71% |
| `prob>=0.80`, daily top10, no extra filters | 195 | 3.55 | 82.05% | 76.06% | 80 | 4.00 | 80.00% | 69.95% |
| high-score-day gate `count(prob>=0.80)>=5`, daily top10 | 200 | 3.64 | 81.50% | 75.54% | 80 | 4.00 | 81.25% | 71.34% |

## User-Preferred Paper-Trading Candidate

The user prefers the simple April-performing rule:

```text
For each trading day:
    keep candidates with probability >= 0.70
    output the top 5 by probability
```

April replay:

| Rule | Count | Avg/day | Accuracy | Wilson |
|---|---:|---:|---:|---:|
| `prob>=0.70`, daily top5 | 96 | 4.80 | 83.33% | 74.63% |

This is attractive for live use because it matches the intended candidate volume and has the best April point accuracy among the simple rules tested. It should be treated as `paper_trading_selector_v1`, not final statistical proof, because it was selected after looking at April.

## Interpretation

1. Reducing coverage helps the trading-facing point accuracy, but daily top5/top6 alone is not stable enough across Q1 and April.
2. The most robust simple family is `prob>=0.80` plus a daily cap. It produces roughly 3-4 names per trading day on Q1/April, not always 5-6. Forcing 5-6 every day lowers discipline.
3. A market-state breadth gate, such as `count(prob>=0.80)>=5`, generalizes better than narrow price/turnover fitting in the April replay.
4. The recommended first engineering candidate is:

```text
If a date has at least 5 candidates with probability >= 0.80:
    output the top 10 candidates by probability for that date
else:
    output no candidates or only the candidates passing a stricter manual review gate
```

This gives:

| Window | Count | Avg/day | Accuracy | Wilson |
|---|---:|---:|---:|---:|
| Q1 | 200 | 3.64 | 81.50% | 75.54% |
| April | 80 | 4.00 | 81.25% | 71.34% |

## Caveats

- This does not make April final-unseen. April has already been observed in research context.
- This does not solve the remaining 14:57 as-of engineering caveat for all selected features.
- Do not select the final rule by April. Use Q1 and pre-April validation logic, then replay April only once per frozen candidate.
- The next useful step is to implement a reusable selector layer that reports `precision@daily_topK`, zero-candidate days, active days, and max single-day concentration.
