# Dual-Model Strategy Search: S2 vs PhaseC — 2026-05-10

## Methodology
- Score-only inference with frozen bundles (NO retraining)
- Strategy selection: 2023-02/03/04 only (pretrain OOS)
- 2026-04: frozen holdout validation (NOT used for selection)
- Exit resolution: 5-min bars when both SL and TP trigger same day
- Both models use identical search grid

## Search Space
- Score: raw_prob, iso_prob
- Threshold: 0.50–0.90 (step 0.01, 41 values)
- Daily TopN: 1–6
- Rank recipes: 11
- Exit modes: 19
- Filters: 21

## S2 (a0ec8105)
- Combos: 2,159,388, Kept: 1,333,002, Time: 704s

### Best Return (Selection)
- iso_prob >= 0.59 | top1 | amount_z_high | exit=close | filter=turnover_5_30
- Return: **216.5%** | Sharpe: 7.82
- DayWin: 73.8% | TickWin: 73.8% | High+1: 90.2% (W95=80.2%)
- MaxLoss: -8.6% | Days: 61 | Tickets: 61
- Months+: 3/3
- Neighborhood: STABLE (worst=70.8%)

| Month | Days | Tickets | Return | DayWin | TickWin | High+1 |
|-------|------|---------|--------|--------|---------|--------|
| 2023-02 | 20 | 20 | 69.4% | 80% | 80% | 85% |
| 2023-03 | 23 | 23 | 30.5% | 78% | 78% | 96% |
| 2023-04 | 18 | 18 | 43.1% | 61% | 61% | 89% |

### Best Robust (Selection)
- iso_prob >= 0.59 | top1 | amount_z_high | exit=close | filter=turnover_5_30
- Return: **216.5%** | Sharpe: 7.82
- DayWin: 73.8% | TickWin: 73.8% | High+1: 90.2% (W95=80.2%)
- MaxLoss: -8.6% | Days: 61 | Tickets: 61
- Months+: 3/3
- Neighborhood: STABLE (worst=70.8%)

| Month | Days | Tickets | Return | DayWin | TickWin | High+1 |
|-------|------|---------|--------|--------|---------|--------|
| 2023-02 | 20 | 20 | 69.4% | 80% | 80% | 85% |
| 2023-03 | 23 | 23 | 30.5% | 78% | 78% | 96% |
| 2023-04 | 18 | 18 | 43.1% | 61% | 61% | 89% |

### April 2026 Holdout (NOT used for selection)
#### Best Return → Holdout
- Return: **5.1%** | DayWin: 57.1% | High+1: 61.9% (W95=40.9%)
- MaxLoss: -10.1% | Days: 21 | Tickets: 21
- **OVERFIT RISK: holdout << selection**

| Month | Days | Tickets | Return | DayWin | TickWin | High+1 |
|-------|------|---------|--------|--------|---------|--------|
| 2026-04 | 21 | 21 | 5.1% | 57% | 57% | 62% |

#### Best Robust → Holdout
- Return: **5.1%** | DayWin: 57.1% | High+1: 61.9% (W95=40.9%)
- MaxLoss: -10.1% | Days: 21 | Tickets: 21
- **OVERFIT RISK: holdout << selection**

| Month | Days | Tickets | Return | DayWin | TickWin | High+1 |
|-------|------|---------|--------|--------|---------|--------|
| 2026-04 | 21 | 21 | 5.1% | 57% | 57% | 62% |


## PhaseC (12605e2b)
- Combos: 2,159,388, Kept: 1,386,924, Time: 695s

### Best Return (Selection)
- iso_prob >= 0.58 | top1 | activity_z_high | exit=tp10 | filter=close_5_60
- Return: **183.7%** | Sharpe: 6.55
- DayWin: 60.7% | TickWin: 60.7% | High+1: 83.6% (W95=72.4%)
- MaxLoss: -7.9% | Days: 61 | Tickets: 61
- Months+: 3/3
- Neighborhood: UNSTABLE (worst=29.5%)

| Month | Days | Tickets | Return | DayWin | TickWin | High+1 |
|-------|------|---------|--------|--------|---------|--------|
| 2023-02 | 20 | 20 | 48.1% | 70% | 70% | 85% |
| 2023-03 | 23 | 23 | 14.2% | 48% | 48% | 78% |
| 2023-04 | 18 | 18 | 67.8% | 67% | 67% | 89% |

### Best Robust (Selection)
- iso_prob >= 0.58 | top1 | activity_z_high | exit=tp10 | filter=close_5_60
- Return: **183.7%** | Sharpe: 6.55
- DayWin: 60.7% | TickWin: 60.7% | High+1: 83.6% (W95=72.4%)
- MaxLoss: -7.9% | Days: 61 | Tickets: 61
- Months+: 3/3
- Neighborhood: UNSTABLE (worst=29.5%)

| Month | Days | Tickets | Return | DayWin | TickWin | High+1 |
|-------|------|---------|--------|--------|---------|--------|
| 2023-02 | 20 | 20 | 48.1% | 70% | 70% | 85% |
| 2023-03 | 23 | 23 | 14.2% | 48% | 48% | 78% |
| 2023-04 | 18 | 18 | 67.8% | 67% | 67% | 89% |

### April 2026 Holdout (NOT used for selection)
#### Best Return → Holdout
- Return: **22.8%** | DayWin: 52.4% | High+1: 81.0% (W95=60.0%)
- MaxLoss: -7.6% | Days: 21 | Tickets: 21
- **OVERFIT RISK: holdout << selection**

| Month | Days | Tickets | Return | DayWin | TickWin | High+1 |
|-------|------|---------|--------|--------|---------|--------|
| 2026-04 | 21 | 21 | 22.8% | 52% | 52% | 81% |

#### Best Robust → Holdout
- Return: **22.8%** | DayWin: 52.4% | High+1: 81.0% (W95=60.0%)
- MaxLoss: -7.6% | Days: 21 | Tickets: 21
- **OVERFIT RISK: holdout << selection**

| Month | Days | Tickets | Return | DayWin | TickWin | High+1 |
|-------|------|---------|--------|--------|---------|--------|
| 2026-04 | 21 | 21 | 22.8% | 52% | 52% | 81% |


## Head-to-Head Comparison

### Best Return (Selection Window)
| Metric | S2 | PhaseC | Winner |
|--------|-----|--------|--------|
| Return % | 216.5 | 183.7 | S2 |
| Sharpe | 7.82 | 6.55 | S2 |
| Daily Win | 73.8% | 60.7% | S2 |
| Ticket Win | 73.8% | 60.7% | S2 |
| High+1 | 90.2% | 83.6% | S2 |
| H1 W95 | 80.2% | 72.4% | S2 |
| MaxLoss | -8.6 | -7.9 | S2 |

### Best Return (April Holdout)
| Metric | S2 | PhaseC | Winner |
|--------|-----|--------|--------|
| Return % | 5.1 | 22.8 | PhaseC |
| Daily Win | 57.1% | 52.4% | S2 |
| High+1 | 61.9% | 81.0% | PhaseC |
| H1 W95 | 40.9% | 60.0% | PhaseC |
| MaxLoss | -10.1 | -7.6 | S2 |

### Best Robust (Selection Window)
| Metric | S2 | PhaseC | Winner |
|--------|-----|--------|--------|
| Return % | 216.5 | 183.7 | S2 |
| Sharpe | 7.82 | 6.55 | S2 |
| Daily Win | 73.8% | 60.7% | S2 |
| Ticket Win | 73.8% | 60.7% | S2 |
| High+1 | 90.2% | 83.6% | S2 |
| H1 W95 | 80.2% | 72.4% | S2 |
| MaxLoss | -8.6 | -7.9 | S2 |

### Best Robust (April Holdout)
| Metric | S2 | PhaseC | Winner |
|--------|-----|--------|--------|
| Return % | 5.1 | 22.8 | PhaseC |
| Daily Win | 57.1% | 52.4% | S2 |
| High+1 | 61.9% | 81.0% | PhaseC |
| H1 W95 | 40.9% | 60.0% | PhaseC |
| MaxLoss | -10.1 | -7.6 | S2 |

## Recommendations

*(auto-generated based on results above)*

## Self-Audit Checklist

- [x] Selection uses ONLY 2023-02/03/04
- [x] 2026-04 holdout NOT used for strategy selection
- [x] No model retraining — frozen bundle score-only
- [x] S2 P0 audit: 9 factors all Class A (14:57 computable)
- [x] PhaseC P0 audit: 200 features all web-safe, P0=0
- [x] Both models use identical search grid
- [x] SL/TP order resolved via 5-min bars when both trigger same day
- [x] Monthly consistency checked, single-month risk flagged
- [x] Neighborhood stability checked
- [x] Overfit risk flagged when holdout << selection
