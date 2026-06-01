# PhaseC Surge Analysis - phasec_surge_analysis_20260520

## Guardrails

- PhaseC remains first-stage model; this run does not retrain PhaseC.
- Primary surge scorer excludes hard moneyflow/post-close/minute full-day features.
- 2026 windows are reported separately; the result is not marked production-ready without web/live parity.

## Data

- Candidate rows: 645,133
- Candidate days: 2,238
- Feature count used by surge model: 77

## Top Surge Features

- cs_market_mean_range: total=2621, surge5=1002, limit10=350
- raw_prob: total=1896, surge5=768, limit10=499
- ma_gap_20: total=1087, surge5=400, limit10=295
- close: total=1031, surge5=402, limit10=274
- atr_14_pct: total=1016, surge5=459, limit10=234
- gap_pct: total=822, surge5=331, limit10=218
- range_lag_1: total=791, surge5=312, limit10=205
- range_lag_4: total=744, surge5=281, limit10=214
- range_mean_3: total=739, surge5=254, limit10=189
- range_lag_3: total=727, surge5=235, limit10=213
- ma_gap_5: total=705, surge5=334, limit10=150
- rsi_14: total=691, surge5=270, limit10=168
- ret_3: total=688, surge5=246, limit10=213
- ret_5: total=676, surge5=254, limit10=156
- ma_gap_10: total=674, surge5=235, limit10=229

## Best Robust Rule

- mask: `iso>=0.75|amount_z>=0`
- rank_col: `raw_prob`
- top_n: `5`
- exit_mode: `tp10`
- robust_score: `174.3235`

- stress_2017_2022: return=591.53%, days=941, daily_win=0.5494, high5=0.3163, limit10=0.098, max_loss=-10.04%
- dev_2023_2025: return=12089.37%, days=431, daily_win=0.6636, high5=0.3769, limit10=0.1307, max_loss=-10.03%
- q1_2026: return=7.75%, days=51, daily_win=0.5098, high5=0.3498, limit10=0.1358, max_loss=-7.5%
- apr_2026: return=16.34%, days=16, daily_win=0.6875, high5=0.3429, limit10=0.1857, max_loss=-2.52%
- may_2026_partial: return=10.11%, days=2, daily_win=1.0, high5=0.6, limit10=0.3, max_loss=4.51%

## Output Files

- JSON: `E:\ashare_similarity_runtime\data\reports\prediction\phasec_surge_analysis_20260520.json`
- Top rules CSV: `E:\ashare_similarity_runtime\data\reports\prediction\phasec_surge_analysis_20260520_top_rules.csv`
- Feature lift CSV: `E:\ashare_similarity_runtime\data\reports\prediction\phasec_surge_analysis_20260520_feature_lift.csv`
- Threshold CSV: `E:\ashare_similarity_runtime\data\reports\prediction\phasec_surge_analysis_20260520_thresholds.csv`
- Scored candidates: `E:\ashare_similarity_runtime\data\reports\prediction\phasec_surge_analysis_20260520_scored_candidates.parquet`