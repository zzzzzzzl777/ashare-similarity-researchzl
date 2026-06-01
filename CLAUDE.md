# CLAUDE.md — A-Share Short-Term T+1 Prediction System

## Project Overview

Predicts whether a stock's next-day intraday high will reach +1% above today's close,
targeting a 75% high-confidence subset accuracy with >= 10% coverage.

## Key Paths

- Code: `C:\Users\zzzzzzl\Desktop\subagent\`
- Runtime data: `E:\ashare_similarity_runtime\`
- Daily bars: `E:\ashare_similarity_runtime\data\raw\bars\daily\`
- Feature cache: `E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\`
- Run reports: `E:\ashare_similarity_runtime\data\reports\prediction\runs\`
- Tushare cache: `E:\ashare_similarity_runtime\data\cache\prediction\tushare\`
- 5min bars (pulling): `E:\ashare_similarity_runtime\data\cache\prediction\tushare\stk_mins_5\`

## Label Convention

- Primary label: `next_high_from_close` — `actual = 1 if high[t+1] >= close[t] * 1.01`
- `--label-target next_high_from_close --target-high-return-pct 1.0`
- Auxiliary: `next_close_up` (close-over-close), `hard_to_hold_2pct/3pct` (post-hoc only)
- Natural hit rate: full ~58%, active ~64%

## Data Split (Four-Layer)

| Layer | Date Range | Purpose |
|-------|-----------|---------|
| dev_train | 2023-05 ~ 2025-06 | Training |
| dev_valid | 2025-07 ~ 2025-12 | Threshold/calibration/walk-forward |
| seen_research | 2026-01 ~ 2026-04 | Evaluate only, no tuning |
| final_unseen | Forward from config freeze | Lockbox — one-shot acceptance |

No random splits. Same-day samples never split across partitions.

## Acceptance Criteria (all AND)

- high_conf_accuracy >= 75%
- wilson_95_lower >= 75%
- brier < class-prior baseline (use NEW label baseline, not old)
- high_conf_count >= 10,000
- high_conf_coverage >= 10%
- No data leakage
- Lockbox unpolluted

## Limit-Up Thresholds

- Main board (00/60): 10% (detect at 9.5%)
- ChiNext/STAR (300/301/688): 20% (detect at 19.5%)
- BSE (8/4): 30% (detect at 29.5%)

## Anti-Leakage Rules

- T+1 high/low/close NEVER as T-day features
- cross_market US/VIX/CNH: lag >= 1 day
- hard_to_hold: post-hoc reporting only, never features
- seen_research window: cannot tune thresholds
- Active sample pct_change must be T-day, not T+1

## GPU Policy

- Training, tensor standardization, batch scoring: GPU (RTX 5090)
- Data download, Parquet I/O, DuckDB, AKShare: CPU
- Single-card serial training, no multi-process GPU contention

## Git Policy

- Never auto-push; all git operations require user confirmation
- Never skip hooks (--no-verify)

## Run Commands

```
python -c "from ashare_similarity.cli import main; import sys; sys.argv = ['ashare-similarity', 'gpu-prediction-probe', ...]; main()"
```

## Testing

```
python -m pytest tests/ -x
```
