# 14:57 Live Engineering Test — 2026-05-06

Generated: 2026-05-06 17:55:54

## Status

**This is a LIVE ENGINEERING TEST, not a production run.**
- NOT claimed as passed
- NOT claimed as final_unseen
- NOT recommended for direct trading
- NOT committed / NOT pushed

## Summary

| Item | Value |
|------|-------|
| Status | ok |
| Asof time | 2026-05-06 17:54:59 |
| Real 14:57 snapshot | NO — rescue run at 2026-05-06 17:54:59 |
| Within 180s | YES |
| Universe | feature_cache_active (727 stocks) |
| Candidates output | 501 |
| Above threshold | 501 |
| Top probability | 0.8750 |
| Threshold | 0.5200 |

## Timing Breakdown

### Warmup (pre-14:57)

| Step | Time (s) |
|------|----------|
| Bundle load | 0.135 |
| Universe determination | 0.07 |
| Daily bars load | 3.5 |
| THS sector pre-compute | 86.0 |
| Snapshot connectivity test | 0.03 |
| **Warmup total** | **89.7** |

### Live (at 14:57)

| Step | Time (s) |
|------|----------|
| Snapshot fetch | 0.1 |
| Inject today's bar | 0.47 |
| Symbol features | 22.3 |
| Cross-section | 0.02 |
| Free factors | 2.04 |
| Cross-market | 0.08 |
| TGB factors | 2.2 |
| THS sector (pre-computed join) | 24.74 |
| Limit pool | 1.01 |
| Feature alignment | 0.00 |
| Inference | 0.02 |
| **Live total** | **55.0** |

## Feature Gap Report

| Category | Count |
|----------|-------|
| Unavailable (post-close) | 0 |
| Approximated (snapshot-based) | 376 |
| Fallback (zeroed) | 0 |
| Feature mode | post_1457_rescue (not strict_1457_live) |

## Model Info

- Bundle: gpu_probe_20260505T113406Z_bb25159b
- Model: stacking_average_top3
- Kind: ensemble_average
- Members: ['gpu_lightgbm_wide', 'gpu_lightgbm_compact', 'gpu_lightgbm']
- Total features: 376
- Selected features: 260
- Calibration: isotonic
- train_end: 2025-12-31

## Data Source

- Real-time: Sina finance API (hq.sinajs.cn) via HTTP proxy (127.0.0.1:7897)
- push2.eastmoney.com: returned 502 during this session, not used
- Historical bars: E:\ashare_similarity_runtime\data\raw\bars\daily\
- THS sector: pre-computed from tushare cache (T-1 lag)
- Post-close Tushare features: zeroed (unavailable at 14:57)
- Turnover: NOT available from Sina realtime, using last historical bar as proxy

## Run Context

- First attempt at real 14:57 triggered correctly but failed (symbol_feature_frame
  excluded target_date row because it was the last bar in series)
- Fix: appended dummy T+1 bar so target_date is not the last row
- Turnover estimated from last historical bar (Sina does not provide realtime turnover)
- short_only=True (original training condition preserved)
- Feature mode: post_1457_rescue

## Failure Notes

None — rescue run completed successfully.
