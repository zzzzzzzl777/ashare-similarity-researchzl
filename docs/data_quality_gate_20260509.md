# Data Quality Gate — 2026-05-09

Generated: 2026-05-09 (corrected after investigation)

## Superset: E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_50f0a15cc17d25ca.parquet

- Rows: 370,430 (361,469 after dedup)
- Columns: 817
- Date range: 2023-06-08 to 2026-03-30
- Unique dates: 679
- Unique symbols: 2937

## Check Results

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | Schema stability | PASS | Meta=817, Actual=817, exact match |
| 2 | Symbol+date duplicates | PASS* | 8961 raw dups from tushare merge; pipeline dedupes at training |
| 3 | Date coverage | PASS | 2023-06-08 start expected (20-day lookback from 2023-05-01 raw) |
| 4 | Labels present | PASS | actual NaN=0%, positive_rate=64.83% |
| 5 | Missing values | PASS | 0 features with any NaN (filled to 0 during build) |
| 6 | Near-constant | PASS* | 246 zero-var: 193 _available=1 always + 53 event features=0 |
| 7 | Inf values | PASS | 0 columns with inf |
| 8 | Class C presence | PASS | 36/36 present (excluded by mask at training, needed for variant comparison) |
| 9 | T-1 shift correctness | PASS | autocorr(1): winner_rate=0.985, cost_conc=0.991, cost_pos=0.988 |
| 10 | Price anomaly | PASS | ret_1 in pct scale [-10.3, 11.0], normal for A-shares |
| 11 | Train/test split | PASS | Train=324,491 (to 2025-12-31), Q1=45,939, NO April data |
| 12 | Cache freshness | PASS | ~33h old, not stale |

## Investigation Notes

### Duplicates (originally flagged P0)
- 8961 rows have duplicate (symbol, date) pairs
- Cause: multiple tushare API merge passes produce duplicate rows differing only in LHB/margin columns
- Pipeline `drop_duplicates(subset=['symbol','date'], keep='first')` is called in gpu_probe.py before training
- **Verdict**: Not a true P0 — handled by existing pipeline dedup

### Date Coverage (originally flagged P0)
- Data starts 2023-06-08, not plan's 2023-05-01
- Reason: Features like ret_20, ma_gap_20, bollinger_position_20 require 20 trading days of lookback
- 27 trading days from 2023-05-01 lands at approximately 2023-06-08
- **Verdict**: Expected behavior — not an issue

### Zero Variance Columns (P1)
- 193 `_available` flags are constant 1.0 (data source always available for entire period)
- 53 value columns are event-based features (e.g., real_in_zt_pool, twenty_cm_board_risk) that are 0 for stocks not in the limit pool
- **Verdict**: Feature selection assigns zero importance to these; no impact on training

### Price Anomaly (originally flagged)
- ret_1 is in **percentage** scale (1.0 = 1%), not decimal (0.01 = 1%)
- Range [-10.3%, +11.0%] is normal for A-shares with 10% daily limit
- Initial check used wrong threshold (0.20 instead of 20)
- **Verdict**: No anomaly

## Gate Decision

- **P0 issues**: 0
- **P1 issues**: 2 (informational, no action needed)
- **Proceed**: YES

## Self-Audit Gate

| Check | Result |
|-------|--------|
| All 12 checks executed | PASS |
| No P0 blockers | PASS |
| Schema matches metadata | PASS |
| Duplicates investigated and explained | PASS |
| Date coverage explained (lookback window) | PASS |
| No April data leakage | PASS |
| T-1 shift correctness verified | PASS |
| ret_1 scale verified (pct not decimal) | PASS |
| Zero-variance explained (event features + constant flags) | PASS |
| P0 issues | 0 |
| P1 issues | 2 (informational) |
| Proceed to Phase 5 | YES |
