# 14:57 Full-Spectrum Comparison Expansion Notes 2026-05-15

Companion training-dimension expansion: `docs/1457_training_dimensions_deep_dive_20260515.md`.
That note covers non-factor axes such as training windows, universe gates, feature
selection budgets, model families, HPO, calibration/selectors, seed stability,
strategy diagnostics, and Web/live gates.

## Current Hard Gate

The strict 14:57 champion route is still blocked from final retraining until the true
historical 14:57-asof feature cache is ready.

- `stk_mins_5` cache is complete by the current parallel progress file
  (`3196` completed, `0` failed in
  `E:\ashare_similarity_runtime\data\cache\prediction\tushare\stk_mins_5\_backfill_progress_parallel.json`).
- `stk_mins_1` cache is not complete (`62` parquet files at audit time; latest observed write
  `2026-05-15 16:08:49`).
- Sampled 1min files do contain historical `14:57` bars, so true 14:57-asof training is feasible after full-market backfill.
- `new_perdate` is still progressing on `block_trade`.
- Recent 2026-05-13/14 fixed-matrix results are research evidence only: recomputed strict P0 audit fails because selected features include same-name T-day/post-close columns.

Deployable baseline until clean rerun: PhaseC strict live-executable bundle. It remains a baseline, not the final champion.

## Expansion Axes Worth Comparing

### 1. Asof Construction

This is the highest-priority expansion because it changes the training/live semantics.

Compare:

- Current PhaseC-style daily/proxy cache.
- True `14:57` synthetic daily bar cache from historical 1min/5min bars.
- 5min-only strict cache.
- 1min+5min strict cache.
- Postclose cache only as diagnostics, never as formal 14:57 champion data.

Required gates:

- Every selected feature must be computable from data available at or before 14:57.
- No same-name replacement of full-day Tushare moneyflow/LHB/margin/close-auction fields.
- Any proxy feature must use a new explicit name and be trained under that exact proxy name.

### 2. Feature Families

Do not compare only S2 versus PhaseC. Use a staged factor matrix.

Primary strict-A groups after data is ready:

- PhaseC strict feature set.
- S2 rehabilitated asof feature set: do not discard S2 wholesale. Its best 9-factor
  route and 60 selected-only increments need true 14:57-asof rebuild/re-test; see
  `docs/1457_s2_asof_rehabilitation_notes_20260515.md`.
- PhaseC plus true-asof 5min factors.
- PhaseC plus true-asof 1min microstructure factors C189-C193.
- PhaseC plus limit-intraday 1min family C244-C261 and C273-C285 after coverage/formula locks.
- Daily formulaic WQ-style factors C278-C281, computed from 14:57 synthetic bar if T-day values are used.
- Existing pre-new-A/non-new-A features after strict P0 re-audit.

Secondary B/proxy groups:

- Chip/cost T-1 only if trained under T-1 columns.
- LHB/margin/block-trade/share-float/holder-trade only as T-1 or publication-lagged features.
- Sector/theme/limit-pool features only with timestamped point-in-time membership and limit-pool snapshots.

Never include:

- Full-day same-name moneyflow split fields for formal 14:57.
- Post-close LHB/margin/close-auction fields for same-day prediction.
- Social/news/event fields without timestamped asof rules.
- Zero-filled missing live features.

### 3. Training Window and Split

Primary champion validation remains `fixed_recent_36m`, full 23-fold rolling.

Use other windows only for sensitivity:

- Recent windows: 24m, 30m, 48m, 60m, 72m.
- Fixed starts: 2017, 2018, 2019, 2020, 2021, 2022, 2023.
- Expanding from earliest fair date.

Champion rule:

- Full 23-fold `fixed_recent_36m` first.
- Then check sensitivity across other windows.
- Q1 and April remain score-only seen-research checks.

### 4. Universe and Candidate Pool Gates

The active stock pool itself should be ablated, not treated as fixed truth.

Compare:

- `min_turnover`: 2.0, 3.0, 4.0.
- `min_amount`: 100m, 200m, 300m.
- `min_range_pct`: 2.0, 3.0, 4.0.
- `min_phase_days_3`: 1, 2, 3.
- main-board-only versus broader board only as research.
- ST/退市/suspended exclusion as mandatory.
- event-day limit-up exclusion on/off only for diagnostics; production should keep non-executable limit-up rows out.

Report:

- Candidate count by day.
- Active days.
- Concentration by date and sector.
- Whether weak windows improve because the pool is cleaner rather than because probability ranking improved.

### 5. Feature Selection and Budget

Compare feature selection separately from feature families.

Recommended grid:

- Methods: `stable_tail`, `abs_correlation`.
- Budgets: 120, 180, 220, 260, 320, 480.
- Family add/drop and beam-style family search.
- Stability-selected core features: features selected in at least N of 23 folds.
- Drift-pruned set: remove features with unstable sign or unstable nonzero coverage.

Hard rule:

- Feature selection must run inside each fold only.
- No Q1/April feature ranking.

### 6. Model Family and HPO

The existing `gpu_probe` already supports a useful model family matrix:

- Torch logistic.
- Torch MLP 64/32, 128/64, 256/128/64.
- Torch residual MLP 128/256.
- XGBoost baseline/shallow/deep.
- LightGBM baseline/compact/wide.
- CatBoost baseline/compact/expressive.
- `stacking_average_top3` ensemble.

Compare in stages:

- Fixed config for all feature families first.
- HPO only for top 2-4 strict-clean candidates.
- Multi-seed only after full rolling passes.
- Ensembling only if members use identical strict feature mapping and pass bundle replay.

### 7. Calibration and Confidence Selector

The current pipeline has several selector layers. They need explicit comparison.

Compare:

- Platt/logit calibration.
- Isotonic calibration.
- Raw rank/no isotonic for rank stability.
- Probability band selector.
- Candidate-agreement selector.
- Meta-correctness selector.
- Regime probability gate.
- Pair-regime probability gate.

Metrics:

- Brier.
- Probability bucket monotonicity.
- `p>=0.75/0.78/0.80` Wilson.
- Daily top3/top5/top10 Wilson.
- Worst-window selector collapse.

### 8. Label and Trading Objective Diagnostics

Do not change the champion label casually. Use diagnostics to understand robustness.

Diagnostics:

- Current label: `next_high_from_close >= 1.0%`.
- Sensitivity labels: 0.8%, 1.2%, 1.5% as research-only.
- Hard-to-hold labels for risk diagnostics.
- Next-close return as strategy auxiliary, not primary champion objective.

If a model only wins under a changed label, it is a separate research branch.

### 9. Strategy Layer

Strategy should support champion selection but not replace hit-rate/Wilson.

Compare after model scoring:

- `p>=0.75/0.78/0.80`.
- Daily top3/top5/top10.
- Daily cap versus no forced candidates.
- Rank recipes: raw probability, probability minus RSI, volume/amount/range rank blends.
- Exit modes: next open/close, high-touch target, stop-loss/take-profit simulations.

Report:

- Total return.
- Max drawdown.
- Daily win rate.
- Monthly worst return.
- Signal days and tickets.
- Whether strategy strength agrees with probability/Wilson strength.

### 10. Regime and Worst-Window Analysis

Current weak windows repeatedly include 2022Q2 and 2023Q3. Add dedicated diagnostics:

- Bull/bear/sideways regime buckets.
- Low-liquidity versus high-liquidity months.
- High-volatility shock months.
- Market breadth buckets.
- Candidate scarcity days.
- Sector concentration risk.

Champion must improve or at least not worsen the stable baseline on worst-window rows.

### 11. Live Parity and Engineering Gate

Before freeze:

- Bundle hash fixed.
- Selected feature order fixed.
- Train/live mapping fixed.
- Golden replay from saved 14:57 snapshot.
- No missing feature silent fill.
- ST/退市/suspended exclusion verified.
- Formal 14:57, postclose validation, and test mode semantics separated.
- Backend/env/audit pass.

### 12. Negative Controls

Add leak tests before champion declaration:

- Shift labels forward/backward as a sanity check.
- Randomized label smoke check.
- Deliberately include a known post-close feature in a blocked test and confirm strict audit catches it.
- Train on postclose cache and verify it is marked diagnostic-only.
- Compare 14:57-asof versus 15:00 same-day deltas to quantify proxy drift.

## Recommended Next Matrix Order

1. Finish and verify 1min/full new data backfill.
2. Build a true `14:57_asof` feature cache.
3. Run PhaseC feature set on true `14:57_asof` cache as baseline parity.
4. Run strict-clean full 23-fold `fixed_recent_36m` for:
   - PhaseC strict set.
   - PhaseC + 5min strict family.
   - PhaseC + 1min microstructure C189-C193.
   - PhaseC + limit-intraday first-wave C244/C246/C248/C252/C254/C258/C260/C270/C272/C273.
   - PhaseC + daily formulaic C279/C280 and C278/C281 only if VWAP/asof is locked.
5. Only then run family add/drop, budget/method, model-family, calibration, selector, and strategy matrices.
6. Promote only candidates with P0=0, P1=0, full rolling stability, and live replay parity.
