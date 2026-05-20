# 14:57 Live Engineering Test — 2026-05-07

Generated: 2026-05-07 22:20:42

## Output Grade

**approximated_1457**

- NOT claimed as: strict_1457 / production_ready / tradeable
- This output is: **diagnostic_only**
- Reason: 6 moneyflow breakdown features use T-1 tushare (push2 cannot provide buy/sell split); net_mf_amount overridden with realtime; turnover computed from realtime volume/free_share

## Status

| Item | Value |
|------|-------|
| Pipeline status | ok |
| Output grade | approximated_1457 |
| Asof time | 2026-05-07 22:20:02 |
| Within 180s | YES |
| Universe | 727 stocks |
| Scored | 477 |
| Above threshold (0.5200) | 463 |
| Candidates (tradable+threshold) | 454 |
| Top probability | 0.7503 |

## Feature Availability (260 selected features)

| Category | Count | Description |
|----------|-------|-------------|
| exact | 249 | Computed from realtime data, same semantics as training |
| proxy_realtime | 8 | Approximated from realtime source (e.g. push2 f62 for net_mf) |
| T-1_tushare | 8 | Using previous day's tushare cache (ratios, breakdown) |
| missing | 0 | No data source available |

### Moneyflow breakdown features (CANNOT compute at 14:57)

These 5+1 selected features require buy/sell order-size split that push2 batch endpoints
do NOT provide reliably. Values come from T-1 tushare moneyflow cache:

- tushare_lg_buy_sell_ratio (T-1 proxy)
- tushare_elg_buy_sell_ratio (T-1 proxy)
- tushare_mf_strength (T-1 proxy)
- tushare_sm_sell_pressure (T-1 proxy)
- tushare_main_force_divergence (T-1 proxy)
- tushare_mf_flow_intensity (T-1 proxy if net_mf unavailable)

### What IS realtime at 14:57

- Snapshot prices (Sina hq.sinajs.cn): OHLCV, prev_close, pct_change
- push2 f62: net main force inflow → tushare_net_mf_amount (proxy)
- Turnover: volume / free_share (computed, free_share from T-1 cache)
- Volume ratio: today_volume / avg_5d_volume (computed)
- All price-derived features (MA, returns, etc.): exact from snapshot bar

## Config Alignment

| Parameter | Training | Probe | Match |
|-----------|----------|-------|-------|
| min_phase_days_3 | 1 | 1 | YES |
| short_only | True | True | YES |
| exclude_event_limit_up | True | False (post-hoc filter) | DECLARED |
| feature_set | research | research | YES |
| label_target | next_high_from_close | N/A (inference only) | N/A |

**Note on exclude_event_limit_up**: Training excludes limit-up stocks during feature
construction. Probe does NOT exclude during construction (needs all stocks scored)
but applies strict post-hoc filter: ST, suspended, limit-up, limit-down all excluded
from candidate output.

## Tradability Gates Applied

- ST / 退市: excluded
- 涨停 (>= 99.5% of board limit): excluded
- 跌停 (<= 100.5% of down limit): excluded
- Suspended (price=0 or NaN): excluded

## Timing

### Warmup (pre-14:57)

| Step | Time (s) |
|------|----------|
| Bundle load | 0.000 |
| Universe | 0.00 |
| Daily bars | 0.0 |
| THS sector | 0.0 |
| **Warmup total** | **0.0** |

### Live (at 14:57)

| Step | Time (s) |
|------|----------|
| Snapshot | 0.2 |
| Net MF fetch | 5.8 |
| Turnover | 0.3 |
| Inject bar | 0.49 |
| Symbol features | 27.4 |
| Factors attach | 5.9 |
| Tushare T-1 | 0.0 |
| Realtime override | 0.49 |
| Feature alignment | 0.00 |
| Inference | 0.02 |
| **Live total** | **40.8** |

## Model

- Bundle: gpu_probe_20260505T113406Z_bb25159b
- Model: stacking_average_top3
- Members: ['gpu_lightgbm_wide', 'gpu_lightgbm_compact', 'gpu_lightgbm']
- Selected features: 260 / 376 total
- Calibration: isotonic
- Threshold: 0.5200

## Data Sources

| Source | Used for | Availability |
|--------|----------|--------------|
| Sina hq.sinajs.cn | Snapshot OHLCV | Realtime |
| push2.eastmoney.com f62 | net_mf_amount | Realtime (unstable, 502s) |
| push2 f135-f142 | buy/sell breakdown | **NOT USABLE** (batch returns garbage) |
| tushare moneyflow parquet | lg/elg/sm ratios | T-1 cache |
| tushare daily_basic | free_share, turnover_rate | T-1 cache |
| tushare stk_limit | up/down limit prices | T-1 cache |
| Daily bars parquet | Historical OHLCV | Disk cache |

## Conclusion

Output grade: **approximated_1457**
Cannot claim strict_1457 because moneyflow breakdown features (5/260) use T-1 proxy.
Diagnostic CSV saved for review. NOT production candidates.
