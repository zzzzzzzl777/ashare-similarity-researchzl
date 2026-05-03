# Top 8 Factor Engineering Review -- 2026-05-03

> Scope: engineering feasibility of P0 candidates C004, C001, C005, C006, C009, C008, C011, C010
> Source code: `src/ashare_similarity/prediction/free_data_factors.py` (read-only)
> Constraint: no training, no gpu_probe.py changes, no frozen_forward_config changes
> Method: verify every input column exists in builder code, confirm T-day availability, classify implementation site
> Revision: 2026-05-03 v2 -- corrected C005/C006/C008 (implied_close != actual close)

---

## Critical Correction: implied_close is NOT actual close

`_build_stk_limit_factors` (line 1184) computes:
```python
implied_close = (up_limit + down_limit) / 2
tushare_up_limit_distance = (up_limit - implied_close) / implied_close
tushare_limit_range = (up_limit - down_limit) / implied_close
```

Since `implied_close` is always the midpoint:
- `up_limit - implied_close = (up_limit - down_limit) / 2`
- Therefore `tushare_up_limit_distance = tushare_limit_range / 2` **for all rows**
- `1 - tushare_up_limit_distance / tushare_limit_range = 0.5` **always**

Any formula using the ratio `up_dist / limit_range` from existing tushare columns is a constant and carries zero information. C005, C006, and C008 as originally specified cannot use existing tushare_up_limit_distance for their intended purpose. They require actual daily `close` from OHLCV bars.

---

## Implementation Groups (Corrected)

| Group | Description | Candidates |
|-------|-------------|------------|
| A | Pure tushare, same builder, 1-2 lines each | C009 |
| C | Needs daily OHLCV columns, post-full-merge | C001, C004, C010 |
| C+ | Needs daily OHLCV + stk_limit raw columns, formula correction required | C005, C006, C008 |
| D | Already exists in codebase | C011 |

---

## Per-Candidate Analysis

### Rank 1 -- C004: ff_adjusted_flow

| Field | Detail |
|-------|--------|
| Formula | `net_mf_amount / (free_share * close)` |
| Actual columns | `tushare_net_mf_amount` (line 950), `tushare_free_share` (daily_basic builder, line 1071+), `close` (daily OHLCV bar) |
| Implementation site | Post-full-merge: computed after `build_tushare_factors` output is joined with daily OHLCV bars |
| Input availability | net_mf_amount: moneyflow API, T-day after close. free_share: daily_basic API, T-day. close: daily bar, T-day |
| Missing value handling | Denominator `free_share * close` can be 0 for suspended stocks; use `.clip(lower=1.0)` or `np.maximum(..., 1.0)` |
| Rolling window | None (single-day point-in-time) |
| Leakage risk | None -- all inputs are T-day close or earlier |
| Coverage | ~99% (moneyflow x daily_basic intersection) |
| Unit | Dimensionless ratio (flow per unit free-float market cap) |
| **Status** | **verified_engineerable** |
| **Group** | C (needs daily OHLCV `close`) |

**Why highest priority**: Combines the 2 strongest validated features (net_mf_amount + free_share). Same 100M net inflow means very different things for a 3B vs 30B free-float stock.

---

### Rank 2 -- C001: mf_flow_intensity

| Field | Detail |
|-------|--------|
| Formula | `net_mf_amount / amount` |
| Actual columns | `tushare_net_mf_amount` (line 950), `amount` (daily OHLCV bar turnover value) |
| Implementation site | Post-full-merge: computed after tushare + daily bars merge |
| Input availability | net_mf_amount: moneyflow API, T-day. amount: daily bar, T-day |
| Missing value handling | Denominator `amount` can be 0 on suspended days; use `np.maximum(amount, 1.0)` |
| Rolling window | None |
| Leakage risk | None |
| Coverage | ~99% |
| Unit | Dimensionless ratio (flow fraction of turnover) |
| **Status** | **verified_engineerable** |
| **Group** | C (needs daily OHLCV `amount`) |

**Note**: `amount` in daily bars is turnover value (in yuan/10000 depending on source), NOT moneyflow `net_mf_amount`. Different semantics, not redundant with raw net_mf_amount.

---

### Rank 3 -- C005: limit_space_compression [CORRECTED]

| Field | Detail |
|-------|--------|
| Original formula | `1 - tushare_up_limit_distance / tushare_limit_range` |
| **Problem** | `implied_close = (up_limit + down_limit) / 2` makes `up_dist / limit_range = 0.5` always. Original formula is a constant -- zero information. |
| **Corrected formula** | `(close - down_limit) / (up_limit - down_limit)` |
| Actual columns needed | `close` (daily OHLCV bar), `up_limit` and `down_limit` (stk_limit raw columns, available in `_build_stk_limit_factors` at lines 1182-1183, but NOT passed through to output) |
| Implementation site | Post-full-merge: requires daily `close` joined with stk_limit raw `up_limit`/`down_limit`. Either (a) pass through raw limit columns from builder, or (b) compute directly from stk_limit parquets + daily OHLCV in a new derivative step |
| Input availability | close: daily bar, T-day. up_limit/down_limit: stk_limit API, T-day (known before open) |
| Missing value handling | `up_limit - down_limit` can be 0 on suspension; clip denominator with `.clip(lower=0.01)` |
| Rolling window | None |
| Leakage risk | None -- close is T-day, limit prices are T-day pre-open |
| Coverage | ~99% |
| Unit | Dimensionless, range [0, 1]. 1.0 = close at upper limit, 0.0 = close at lower limit |
| **Status** | **needs_formula_correction** |
| **Group** | C+ (post-full-merge, needs daily close + stk_limit raw columns) |

**Engineering requirement**: Current `_build_stk_limit_factors` only outputs 3 derived columns; raw `up_limit`/`down_limit` are not passed through. Two options:
1. Add `tushare_up_limit_raw` and `tushare_down_limit_raw` passthrough columns to builder output and `TUSHARE_FACTOR_COLUMNS`, then compute compression post-merge with daily close.
2. Build a separate derivative function that reads stk_limit parquets directly and joins with daily close.

Option 1 is cleaner (reuses existing builder infrastructure).

---

### Rank 4 -- C006: limit_approach_velocity [CORRECTED]

| Field | Detail |
|-------|--------|
| Original formula | `tushare_up_limit_distance[T-1] - tushare_up_limit_distance[T]` (diff of existing column) |
| **Problem** | `tushare_up_limit_distance` uses `implied_close` (midpoint), not actual close. Its diff captures only changes in limit-range width (e.g., board transfer between 10%/20% regime), not actual price movement toward limit. |
| **Corrected formula** | `actual_up_gap[T-1] - actual_up_gap[T]` where `actual_up_gap = (up_limit - close) / close` |
| Actual columns needed | `close` (daily OHLCV), `up_limit` (stk_limit raw) |
| Implementation site | Post-full-merge: compute `actual_up_gap` from daily close + stk_limit raw up_limit, then `.diff()` per symbol |
| Input availability | close: T-day. up_limit: T-day pre-open |
| Missing value handling | First day per symbol produces NaN from `.diff()`; filled to 0.0 by `_ensure_feature_columns` |
| Rolling window | 1-day lag (`.diff()` pattern) |
| Leakage risk | None -- T-1 close and T up_limit both available before T+1 |
| Coverage | ~99% (loses first trading day per symbol) |
| Unit | Percentage points; positive = price approaching limit |
| **Status** | **needs_formula_correction** |
| **Group** | C+ (post-full-merge, needs daily close + stk_limit raw, rolling 1d) |

**Depends on C005 infrastructure**: If C005 passes through `up_limit`/`down_limit` raw columns, C006 can reuse them. Implement C005 first.

---

### Rank 5 -- C009: main_force_divergence

| Field | Detail |
|-------|--------|
| Formula | `abs(tushare_lg_buy_sell_ratio - tushare_elg_buy_sell_ratio)` |
| Actual columns | `tushare_lg_buy_sell_ratio` (line 951), `tushare_elg_buy_sell_ratio` (line 952) |
| Implementation site | `_build_moneyflow_factors` (line 936), append 1 line to `out` dict |
| Input availability | Both from moneyflow API, T-day after close |
| Missing value handling | Both ratios already clipped at 50.0 and floored at 100.0 denominator; abs() of difference always finite |
| Rolling window | None |
| Leakage risk | None |
| Coverage | ~99% |
| Unit | Ratio difference (dimensionless). Range [0, ~50]. High = large/extra-large institutional disagreement |
| **Status** | **verified_engineerable** |
| **Group** | A (pure tushare, same builder, 1 line) |

**Implementation**: Add to `out` dict in `_build_moneyflow_factors`:
```python
"tushare_main_force_divergence": (out["tushare_lg_buy_sell_ratio"] - out["tushare_elg_buy_sell_ratio"]).abs(),
```

**Signal logic**: When lg_ratio >> elg_ratio, large institutions are net buying but extra-large are not (or vice versa). High divergence signals institutional disagreement -- a dimension neither ratio captures alone.

---

### Rank 6 -- C008: seal_strength_proxy [CORRECTED]

| Field | Detail |
|-------|--------|
| Original formula | `elg_ratio * (1 - tushare_up_limit_distance / tushare_limit_range)` |
| **Problem** | `1 - up_dist/limit_range = 0.5` always. Original formula reduces to `elg_ratio * 0.5`, a trivial rescaling of an existing feature. |
| **Corrected formula** | `tushare_elg_buy_sell_ratio * actual_compression` where `actual_compression = (close - down_limit) / (up_limit - down_limit)` (same as corrected C005) |
| Actual columns needed | `tushare_elg_buy_sell_ratio` (moneyflow, line 952), `close` (daily OHLCV), `up_limit`/`down_limit` (stk_limit raw) |
| Implementation site | Post-full-merge: compute after tushare merge + daily OHLCV join. Depends on C005 actual_compression being available |
| Input availability | All T-day |
| Missing value handling | Rows missing any of the 3 source values produce NaN -> 0.0 |
| Rolling window | None |
| Leakage risk | None |
| Coverage | ~99% (moneyflow x stk_limit x daily OHLCV intersection) |
| Unit | Dimensionless product. High = large ELG buying pressure when price is near upper limit |
| **Status** | **needs_formula_correction** |
| **Group** | C+ (post-full-merge, cross-source derivative, depends on C005) |

**Depends on C005**: Uses the same `actual_compression` as C005. Implement C005 first, then C008 is a one-line product.

**Caveat**: Even with correct compression, this remains a 3-feature product. The model may learn this interaction from the component features, reducing marginal value. Worth testing but expect smaller lift than C004/C001.

---

### Rank 7 -- C011: auction_open_vwap_ratio

| Field | Detail |
|-------|--------|
| Formula | `vwap / close` (opening auction VWAP divided by close price) |
| Actual columns | `tushare_auction_open_vwap_ratio` (line 1124) |
| Implementation site | Already computed in `_build_auction_factors` (line 1105) |
| Input availability | stk_auction_o API. T-day 9:25 auction data |
| Missing value handling | Already handled: `close.clip(lower=0.01)` |
| Rolling window | None |
| Leakage risk | None -- auction data available at 9:25, before market open |
| Coverage | ~95%+ (804 days cached, but some stocks may not have auction data) |
| Unit | Ratio. >1 means auction VWAP above prev close |
| **Status** | **existing_engineered** |
| **Group** | D (already exists) |

**What's needed**: Not a code change but a promotion decision. Column `tushare_auction_open_vwap_ratio` exists in `TUSHARE_FACTOR_COLUMNS` and is already computed. To include it in ablation testing, it just needs to be added to the monkey-patch feature list for the next probe run.

**Current gating**: Only accessible via `feature_set="research"` because Tushare features are gated by `_uses_research_external_factors` (gpu_probe.py line 885).

---

### Rank 8 -- C010: float_relative_impact

| Field | Detail |
|-------|--------|
| Formula | `tushare_volume_ratio * volume / tushare_free_share` |
| Actual columns | `tushare_volume_ratio` (daily_basic builder), `tushare_free_share` (daily_basic builder), `volume` (daily OHLCV bar) |
| Implementation site | Post-full-merge: computed after tushare + daily bars merge |
| Input availability | volume_ratio: daily_basic API, T-day. free_share: daily_basic API, T-day. volume: daily bar, T-day |
| Missing value handling | free_share can be 0 for newly listed stocks; use `np.maximum(free_share, 1.0)` |
| Rolling window | None |
| Leakage risk | None |
| Coverage | ~99% |
| Unit | Shares^2 / shares = shares (dimensional but model handles via tree splitting) |
| **Status** | **verified_engineerable** |
| **Group** | C (needs daily OHLCV `volume`) |

**Signal logic**: Measures turnover stress on float. A stock with volume_ratio=3 and 10M daily volume / 50M free_share is under different stress than one with same volume_ratio but 10M / 500M free_share. None of the 3 component features alone captures this.

---

## Implementation Dependency Map (Corrected)

```
Daily OHLCV bars (close, amount, volume) ------+
                                               |
stk_limit raw (up_limit, down_limit) ----+     |
                                         |     |
                                         v     v
                                   [post-full-merge]
                                     C001 (amount)
                                     C004 (close)
                                     C010 (volume)
                                     C005 (close + up/down_limit) [CORRECTED]
                                     C006 (close + up_limit, .diff()) [CORRECTED]
                                     C008 (C005 compression * elg_ratio) [CORRECTED]

build_tushare_factors
  |
  |  _build_moneyflow_factors
  |    C009 (1 line, no correction needed)
  |
  _build_auction_factors
    C011 (already exists, no code change)
```

---

## Column Name Conventions

All new tushare-derived columns MUST follow the `tushare_` prefix convention established by existing columns. Proposed names:

| ID | Column Name | Added To |
|----|------------|----------|
| C004 | `tushare_ff_adjusted_flow` | post-merge derivative |
| C001 | `tushare_mf_flow_intensity` | post-merge derivative |
| C005 | `tushare_limit_space_compression` | post-merge derivative (needs raw up/down_limit) |
| C006 | `tushare_limit_approach_velocity` | post-merge derivative (needs raw up_limit + close) |
| C009 | `tushare_main_force_divergence` | `_build_moneyflow_factors` output |
| C008 | `tushare_seal_strength_proxy` | post-merge derivative (depends on C005) |
| C011 | `tushare_auction_open_vwap_ratio` | already exists |
| C010 | `tushare_float_relative_impact` | post-merge derivative |

---

## TUSHARE_FACTOR_COLUMNS Impact (Corrected)

**Group A (C009 only)** needs 1 new entry in `TUSHARE_FACTOR_COLUMNS` (line 812-871).

**Group C (C001, C004, C010)** are computed AFTER tushare merge, so they do NOT go into `TUSHARE_FACTOR_COLUMNS`. They should be added to the research feature constant.

**Group C+ (C005, C006, C008)** require either:
- Passthrough of raw `up_limit`/`down_limit` from `_build_stk_limit_factors` (add 2 columns to `TUSHARE_FACTOR_COLUMNS`), then compute derivatives post-merge with daily close; OR
- A separate derivative step that re-reads stk_limit parquets and joins with daily close.

**Group D (C011)** is already in `TUSHARE_FACTOR_COLUMNS`.

---

## Risk Assessment (Corrected)

| Risk | Mitigation |
|------|-----------|
| Denominator = 0 (C004: free_share*close, C001: amount, C005: up_limit-down_limit, C010: free_share) | All use `.clip(lower=X)` or `np.maximum(..., X)` pattern per existing code conventions |
| .diff() NaN on first day per symbol (C006) | `_ensure_feature_columns` fills NaN with 0.0; 1 row per symbol negligible |
| Cross-source NaN after outer merge (C005, C006, C008) | Rows where daily OHLCV or stk_limit is missing produce NaN -> 0.0 |
| Dimensional mismatch (C010) | Tree models split on ordinal values, not absolute magnitude; no normalization needed |
| C011 stk_auction_o coverage may be lower than other tushare APIs | 804 parquets cached; coverage adequate but narrower than moneyflow/daily_basic |
| C005/C006/C008 need stk_limit raw columns not currently in tushare output | Minor builder change: passthrough 2 raw columns from `_build_stk_limit_factors` |

---

## Verdict (Corrected)

| ID | Name | Engineering Status | Ready for Testing? | Needs Engineering First? |
|----|------|-------------------|-------------------|------------------------|
| C004 | ff_adjusted_flow | verified_engineerable | YES | Post-merge computation only |
| C001 | mf_flow_intensity | verified_engineerable | YES | Post-merge computation only |
| C005 | limit_space_compression | **needs_formula_correction** | NO | Needs raw up/down_limit passthrough + daily close |
| C006 | limit_approach_velocity | **needs_formula_correction** | NO | Needs raw up_limit passthrough + daily close + diff() |
| C009 | main_force_divergence | verified_engineerable | YES | 1 line in existing builder |
| C008 | seal_strength_proxy | **needs_formula_correction** | NO | Depends on C005 correction |
| C011 | auction_open_vwap_ratio | existing_engineered | YES | Already in code |
| C010 | float_relative_impact | verified_engineerable | YES | Post-merge computation only |

### Summary

- **5/8 ready for next-round testing**: C001, C004, C009, C010, C011
- **3/8 need engineering implementation first**: C005, C006, C008 (all require formula correction to use actual daily close instead of implied_close midpoint)

### Recommended Implementation Order

1. **C009** (Group A): 1 line in `_build_moneyflow_factors`, zero risk, ship immediately
2. **C001, C004, C010** (Group C): post-full-merge derivatives, need implementation site decision but formulas are correct as specified
3. **C011** (Group D): no code change, just include in next ablation feature list
4. **C005 then C006 then C008** (Group C+): requires `_build_stk_limit_factors` to passthrough raw `up_limit`/`down_limit`, then post-merge computation with daily close. C006 depends on C005 infrastructure. C008 depends on C005 output.
