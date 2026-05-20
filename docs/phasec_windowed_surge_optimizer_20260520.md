# Windowed PhaseC Live-Safe Surge Optimizer - phasec_windowed_surge_optimizer_20260520

## Guardrails

- PhaseC bundle is frozen; no PhaseC retrain here.
- Surge scorer features are live-safe only.
- Window policies compared: expanding, recent5, recent3.
- Strategy selection uses 2021-2025 rolling OOF metrics; Q1/April/May 2026 are validation reports.
- Stop/take-profit modes are high/low idealized and require minute replay before deployment.

## Best By Window

### expanding

- mask: `raw>=0.78|t5_30_rsi55`
- rank: `raw_prob`
- top_n: `2`
- exit: `tp5`
- strict_score: `956.813`
- current_confirm_score: `1042.137`

- stress_oof_2021_2022: return=16.05%, days=131, daily_win=0.5344, high5=0.2816, limit10=0.0735, max_loss=-8.29%
- dev_oof_2023_2025: return=3416.53%, days=180, daily_win=0.85, high5=0.3689, limit10=0.125, max_loss=-5.62%
- q1_2026_forward: return=-3.24%, days=18, daily_win=0.5, high5=0.2727, limit10=0.0303, max_loss=-8.27%
- apr_2026_forward: return=15.65%, days=4, daily_win=1.0, high5=0.4286, limit10=0.1429, max_loss=0.79%
- may_2026_partial: return=-1.44%, days=1, daily_win=0.0, high5=0.0, limit10=0.0, max_loss=-1.44%

### recent5

- mask: `raw>=0.78|t5_30_rsi55`
- rank: `raw_prob`
- top_n: `2`
- exit: `tp5`
- strict_score: `956.813`
- current_confirm_score: `1042.137`

- stress_oof_2021_2022: return=16.05%, days=131, daily_win=0.5344, high5=0.2816, limit10=0.0735, max_loss=-8.29%
- dev_oof_2023_2025: return=3416.53%, days=180, daily_win=0.85, high5=0.3689, limit10=0.125, max_loss=-5.62%
- q1_2026_forward: return=-3.24%, days=18, daily_win=0.5, high5=0.2727, limit10=0.0303, max_loss=-8.27%
- apr_2026_forward: return=15.65%, days=4, daily_win=1.0, high5=0.4286, limit10=0.1429, max_loss=0.79%
- may_2026_partial: return=-1.44%, days=1, daily_win=0.0, high5=0.0, limit10=0.0, max_loss=-1.44%

### recent3

- mask: `raw>=0.78|t5_30_rsi55`
- rank: `raw_prob`
- top_n: `2`
- exit: `tp5`
- strict_score: `956.813`
- current_confirm_score: `1042.137`

- stress_oof_2021_2022: return=16.05%, days=131, daily_win=0.5344, high5=0.2816, limit10=0.0735, max_loss=-8.29%
- dev_oof_2023_2025: return=3416.53%, days=180, daily_win=0.85, high5=0.3689, limit10=0.125, max_loss=-5.62%
- q1_2026_forward: return=-3.24%, days=18, daily_win=0.5, high5=0.2727, limit10=0.0303, max_loss=-8.27%
- apr_2026_forward: return=15.65%, days=4, daily_win=1.0, high5=0.4286, limit10=0.1429, max_loss=0.79%
- may_2026_partial: return=-1.44%, days=1, daily_win=0.0, high5=0.0, limit10=0.0, max_loss=-1.44%

## Files

- JSON: `E:\ashare_similarity_runtime\data\reports\prediction\phasec_windowed_surge_optimizer_20260520.json`
- Rules CSV: `E:\ashare_similarity_runtime\data\reports\prediction\phasec_windowed_surge_optimizer_20260520_top_rules.csv`