# PhaseC Pre-Train 2023-02/03/04 Frozen Validation

- Generated: 2026-05-09T20:15:46.270070
- Bundle: `E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt`
- Cache: `E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\pretrain_2023_02_04_patched.parquet`
- Method: frozen score-only, no retraining, signal-date Feb/Mar/Apr 2023.
- Missing feature columns: 0

## Overall Feb-Apr 2023

Rows: 19549, trading days: 61

| Selector | N | Acc | Wilson95 | Coverage | Signal days | Avg/day |
|---|---:|---:|---:|---:|---:|---:|
| p>=0.70 | 1936 | 0.7433 | 0.7234 | 0.0990 | 55 | 35.2 |
| p>0.75 | 781 | 0.7593 | 0.7281 | 0.0400 | 36 | 21.69 |
| p>=0.78 | 699 | 0.7568 | 0.7236 | 0.0358 | 32 | 21.84 |
| p>=0.80 | 350 | 0.7600 | 0.7126 | 0.0179 | 12 | 29.17 |
| p>=0.85 | 123 | 0.8130 | 0.7350 | 0.0063 | 3 | 41.0 |
| daily_top6_p>0.75_ties | 217 | 0.8387 | 0.7840 |  | 36/61 | 6.03 |

## 2023-02

Rows: 6850, trading days: 20

| Selector | N | Acc | Wilson95 | Coverage | Signal days | Avg/day |
|---|---:|---:|---:|---:|---:|---:|
| p>=0.70 | 450 | 0.7311 | 0.6883 | 0.0657 | 17 | 26.47 |
| p>0.75 | 148 | 0.7838 | 0.7107 | 0.0216 | 9 | 16.44 |
| p>=0.78 | 127 | 0.7874 | 0.7084 | 0.0185 | 6 | 21.17 |
| p>=0.80 | 36 | 0.8611 | 0.7134 | 0.0053 | 1 | 36.0 |
| p>=0.85 | 0 |  |  | 0.0000 | 0 | 0 |
| daily_top6_p>0.75_ties | 43 | 0.8140 | 0.6738 |  | 9/20 | 4.78 |

## 2023-03

Rows: 6606, trading days: 23

| Selector | N | Acc | Wilson95 | Coverage | Signal days | Avg/day |
|---|---:|---:|---:|---:|---:|---:|
| p>=0.70 | 388 | 0.7990 | 0.7562 | 0.0587 | 21 | 18.48 |
| p>0.75 | 64 | 0.8594 | 0.7538 | 0.0097 | 14 | 4.57 |
| p>=0.78 | 41 | 0.8537 | 0.7156 | 0.0062 | 13 | 3.15 |
| p>=0.80 | 4 | 1.0000 | 0.5101 | 0.0006 | 4 | 1.0 |
| p>=0.85 | 0 |  |  | 0.0000 | 0 | 0 |
| daily_top6_p>0.75_ties | 55 | 0.8364 | 0.7174 |  | 14/23 | 3.93 |

## 2023-04

Rows: 6093, trading days: 18

| Selector | N | Acc | Wilson95 | Coverage | Signal days | Avg/day |
|---|---:|---:|---:|---:|---:|---:|
| p>=0.70 | 1098 | 0.7286 | 0.7015 | 0.1802 | 17 | 64.59 |
| p>0.75 | 569 | 0.7417 | 0.7041 | 0.0934 | 13 | 43.77 |
| p>=0.78 | 531 | 0.7420 | 0.7031 | 0.0871 | 13 | 40.85 |
| p>=0.80 | 310 | 0.7452 | 0.6939 | 0.0509 | 7 | 44.29 |
| p>=0.85 | 123 | 0.8130 | 0.7350 | 0.0202 | 3 | 41.0 |
| daily_top6_p>0.75_ties | 119 | 0.8487 | 0.7735 |  | 13/18 | 9.15 |

## Files
- JSON: `E:\ashare_similarity_runtime\data\reports\prediction\phaseC_pretrain_2023_02_04_validation_20260509.json`
- Daily CSV: `E:\ashare_similarity_runtime\data\reports\prediction\phaseC_pretrain_2023_02_04_daily_detail_20260509.csv`