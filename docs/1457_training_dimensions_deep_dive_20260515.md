# 14:57 Training Dimension Deep Dive 2026-05-15

## Purpose

This document expands the next-round plan beyond factor comparison. The goal is still
one thing: find the highest-accuracy, most stable, strictly 14:57-executable T+1
stock-selection model.

The key correction is that "more factors" is only one axis. A professional search must
also compare data construction, training windows, candidate-pool gates, feature-selection
policy, model family, HPO, calibration, confidence selectors, seed stability, strategy
layer, and live parity.

Current status: do not start final formal training until the true historical 14:57-asof
feature cache is ready and audited. The 5min cache is complete by the latest progress
file, while 1min backfill is still in progress. Existing 2026-05-13/14 full36 evidence is
research evidence only under the newer strict P0/asof interpretation.

## Evidence Read

Important sources re-read for this expansion:

- `C:\Users\zzzzzzl\Desktop\14点57全量可纳入因子重新对比计划书_20260509.md`
- `C:\Users\zzzzzzl\Desktop\14点57项目优化补强执行方案_20260509.md`
- `C:\Users\zzzzzzl\Desktop\14点57可执行约束训练交接文档_20260507.md`
- `C:\Users\zzzzzzl\Desktop\第四轮全因子对比本机交接文档_20260507.md`
- `C:\Users\zzzzzzl\Desktop\PhaseC_S2_factor_catalog_20260511.md`
- `docs/1457_full_spectrum_comparison_expansion_20260515.md`
- `docs/1457_s2_asof_rehabilitation_notes_20260515.md`
- `docs/shortline_factor_expansion_20260515.md`
- `docs/data_unlocked_factor_mapping_20260515.md`
- `docs/next_round_1457_tier-3_full36_rolling_findings_20260513_tier3_full36_gpu_v1.md`
- `docs/next_round_1457_tier7_top2_seed42_seed7_seed2026_stability.md`
- `docs/next_round_1457_final_stability_freeze_decision_20260514.md`

Code surfaces checked:

- `src/ashare_similarity/prediction/gpu_probe.py`
- `scripts/run_1457_next_round_protocol.py`
- `scripts/run_1457_next_round_fixed_matrix.py`
- `scripts/run_u95_optuna_rolling.py`
- `scripts/run_phaseC_hpo.py`
- strategy scanners such as `scripts/ultra_strategy_search.py` and
  `scripts/scan_combined_4month.py`

## Non-Negotiable Gates

1. Strict champion training must use only features available at or before 14:57.
2. Historical training must use the same 14:57-asof semantics as live/Web.
3. Same-name substitution is forbidden: full-day Tushare fields cannot be silently
   replaced by live approximations.
4. Q1 2026 and April 2026 are seen-research consistency checks only.
5. Tier screens rank candidates only; they cannot promote a champion.
6. Champion selection is stability-first: `mean_wilson_95`, `min_wilson_95`,
   `std_wilson_95`, `mean_accuracy`, candidate count/coverage, P0=0, P1=0.
7. If a clean stable candidate does not beat the baseline, return NO_FREEZE rather than
   forcing a winner.

## Dimension 1: Asof Data Construction

This is the most important dimension because it changes the actual training/live meaning.

Compare only after cache audit:

| Variant | Role | Status |
|---|---|---|
| `phasec_old_strict_bundle_score_only` | deployable baseline reference | score-only |
| `daily_proxy_1457_compat` | old approximation diagnostic | research only |
| `5min_asof_1457_cache` | strict formal candidate if schema complete | trainable after audit |
| `1min_asof_1457_cache` | best formal route for minute factors | trainable after backfill |
| `1min_plus_5min_asof_cache` | richest strict route | trainable after parity audit |
| `postclose_1500_cache` | postclose verification only | never formal champion |

Audit requirements:

- For every day, reconstruct T-day OHLCV as of 14:57.
- Keep T-1 and earlier bars final; only T-day row is truncated/asof.
- For cross-section features, use the same 14:57 universe and quote coverage.
- For market/sector features, record snapshot time and coverage.
- For missing live features, fail or exclude; do not silently fill zero.

Decision rule:

- If true 1min-asof cache passes coverage and parity, stop treating 15:00 training as
  the formal route. Postclose remains only a diagnostic comparison.

## Dimension 2: Training Window and Split

The user's current direction is correct: primary champion validation should be
`fixed_recent_36m` full 23-fold rolling. Other windows are sensitivity checks.

Primary:

- `fixed_recent_36m`
- 3-month outer folds
- full 23 folds
- nested inner validation inside each fold
- `label_date` split with embargo

Sensitivity windows:

| Family | Values | Purpose |
|---|---|---|
| recent rolling | 24m, 30m, 36m, 48m, 60m, 72m | test history length |
| fixed start | 2017, 2018, 2019, 2020, 2021, 2022, 2023 | test early-regime inclusion |
| expanding | earliest fair date to validation start | test more-data hypothesis |
| validation length | 1m, 2m, 3m, 6m, 12m | diagnostics, 3m remains main |

What to compare:

- Does 36m still dominate after true 14:57-asof cache?
- Does 48m/60m improve worst-window without reducing mean too much?
- Do older 2017-2020 regimes help or add obsolete market behavior?
- Does fixed_start_2018 still look strong after strict P0/asof rebuild?

Champion rule:

- Fixed_recent_36m decides the main leaderboard.
- Other windows can demote a fragile candidate, but should not override the primary
  protocol by a single lucky window.

## Dimension 3: Candidate-Pool and Universe Gates

The daily stock pool is not a fixed truth. It should be compared because it changes both
training distribution and live executability.

Existing knobs in `GpuProbeConfig`:

- `short_only`
- `main_board_only`
- `min_turnover`
- `min_amount`
- `min_volume_z`
- `min_amount_z`
- `min_range_pct`
- `min_volatility_pct`
- `min_abnormal_flags`
- `min_phase_days_3`
- `min_active_anomaly_rank`
- `exclude_event_limit_up`

Recommended staged grid:

| Gate | Values |
|---|---|
| `min_turnover` | 2.0, 3.0, 4.0 |
| `min_amount` | 100m, 200m, 300m |
| `min_range_pct` | 2.0, 3.0, 4.0 |
| `min_phase_days_3` | 1, 2, 3 |
| `min_active_anomaly_rank` | 0, top 1500, top 1000 |
| board scope | main board primary; broader board research only |
| limit-up event exclusion | on for production; off only diagnostic |

Metrics:

- candidate count by day
- active days
- no-candidate days
- sector concentration
- topK coverage
- worst-window changes

Guardrail:

- ST, suspended, delisting-risk, and non-executable limit-up rows are engineering P0
  if they reach production candidate output.

## Dimension 4: Feature Selection and Feature Budget

Feature-family comparison and feature-selection policy must be separated.

Existing knobs:

- `feature_selection_method`: currently includes `abs_correlation`; existing scripts
  and U95 logic also use `stable_tail`.
- `max_selected_features`: current grids include 120, 160, 200, 220, 260, 300, 320,
  360, 400, 480.

Required comparisons:

| Axis | Values |
|---|---|
| method | `stable_tail`, `abs_correlation`, family-stable selector |
| budget | 120, 160, 200, 220, 260, 300, 320, 360, 400, 480 |
| stability core | selected in >=50%, >=70%, >=85% of rolling folds |
| drift prune | remove features with unstable sign/coverage across folds |
| orphan flags | drop `_available` flags if parent feature not in scope |

Decision rule:

- Do not choose 260 just because S2 used 260 or PhaseC used 200.
- Use budget as an explicit search dimension after clean factor groups are fixed.
- A larger budget must improve stability, not just mean.

## Dimension 5: Model Family

The code already supports a broader model family search than old PhaseC.

`gpu_probe.py` fixed candidates:

- `gpu_logistic`
- `gpu_mlp_64_32`
- `gpu_mlp_128_64`
- `gpu_mlp_256_128_64`
- `gpu_residual_mlp_128`
- `gpu_residual_mlp_256`
- XGBoost baseline/shallow/deep
- LightGBM baseline/compact/wide
- CatBoost baseline/compact/expressive
- average ensemble of top candidates

U95 Optuna candidates:

- LightGBM
- XGBoost
- CatBoost

Recommended model search:

1. Run fixed model-family comparison on top strict-clean feature variants.
2. Keep model-family rows separate from factor-family rows.
3. Promote only 2-4 clean candidates to HPO.
4. HPO winner must return to full 23-fold rolling and multi-seed validation.

Risk notes:

- CatBoost has had worker/runtime fragility in live/postclose contexts; use subprocess or
  CPU fallback if required, but record backend and environment in every artifact.
- Tree models may produce probability tie/compression; track unique top probabilities.
- Neural models can be seed-sensitive; do not trust one seed.

## Dimension 6: Optuna/HPO

HPO should be a late-stage refinement, not a substitute for protocol discipline.

Existing U95 objective already uses a good stable-first shape:

- positive weight on mean `p>=0.75` Wilson
- positive weight on min `p>=0.75` Wilson
- positive weight on high-confidence Wilson
- penalty on Wilson standard deviation
- penalty on poor Brier
- penalty on sparse candidate count
- penalty on probability ties

Recommended HPO protocol:

| Stage | Scope |
|---|---|
| smoke | 3-5 trials to verify ledger/cache/P0 |
| phase1 | 40-60 trials per top candidate |
| phase2 | 80-120 trials for the top 1-2 families |
| multi-seed rerun | seeds 42, 7, 2026, and optionally 43/44 |
| freeze candidate | top 1-3 only, then score-only Q1/April |

Search dimensions:

- model family
- max selected features
- learning rate
- tree depth/leaves
- estimators/iterations
- regularization
- subsampling/feature fraction
- calibration

Guardrail:

- HPO objective cannot include Q1/April.
- Any HPO result with P0 selected features is invalid, no matter how high the score is.

## Dimension 7: Calibration and Confidence Selector

The project goal is high-confidence candidate quality, so calibration and selector logic
are first-class dimensions.

Compare:

- raw probability/rank
- Platt/logit calibration
- isotonic calibration
- probability band selector
- agreement selector
- meta-confidence selector
- regime probability gate
- pair-regime probability gate
- daily topK selector

Metrics:

- Brier
- ECE or bucket reliability
- probability bucket monotonicity
- score compression and unique probabilities
- `p>=0.75`, `p>=0.78`, `p>=0.80`
- daily top3/top5/top10 Wilson
- selector count and coverage
- worst-window selector collapse

Decision rule:

- Calibration is useful only if it improves high-confidence reliability and does not
  destroy candidate coverage.
- Isotonic that over-compresses scores should be rejected even if average Brier improves.

## Dimension 8: Seed Stability and Ensemble

The old S2 evidence shows why this matters: a strong single seed can fail stability.

Required seed matrix:

- seed 42 as baseline
- seed 7 and 2026 as stress seeds
- optional 43/44 for final freeze stress

Metrics:

- mean over all seed-fold rows
- min over all seed-fold rows
- std over all seed-fold rows
- per-seed mean/min
- same worst-window robustness
- selected-feature overlap

Ensemble candidates:

- simple average probability
- rank average
- top-2/top-3 model average
- family-diverse ensemble: LGB + XGB + CatBoost or tree + torch

Guardrail:

- Ensemble members must share strict feature mapping or have separately versioned
  mapping manifests.
- Do not ensemble a P0-clean model with a P0-contaminated model.
- Ensembling cannot be justified by Q1/April alone.

## Dimension 9: Label and Objective Diagnostics

Do not change the champion label casually. Label changes create a separate research
branch.

Primary label remains:

- `next_high_from_close >= 1.0%`

Diagnostics only:

- `next_high_from_close >= 0.8%`
- `next_high_from_close >= 1.2%`
- `next_high_from_close >= 1.5%`
- next-close return
- adverse excursion / drawdown risk
- hard-to-hold flag

Use diagnostics to explain:

- high hit-rate but bad strategy performance
- strong next-high but poor close-to-close
- models that select high-spike but untradable stocks

Champion selection should not mix labels in one leaderboard.

## Dimension 10: Strategy Layer

Strategy is a strong auxiliary check, not the champion objective.

Compare after model scoring:

- thresholds: 0.75, 0.78, 0.80, 0.85
- daily topK: 3, 5, 6, 10
- no forced candidate versus forced topK
- rank recipe: raw probability, probability plus liquidity, probability minus risk,
  probability plus board/theme strength
- execution: next open, next close, high-touch target, stop-loss/take-profit simulation
- daily cap and sector concentration cap

Report:

- return
- max drawdown
- win rate
- average tickets/day
- no-signal days
- worst day/month
- concentration
- agreement with Wilson leaderboard

Decision rule:

- A model with slightly lower Wilson but much better strategy consistency can become a
  challenger, but not champion unless its rolling hit-rate stability is also acceptable.

## Dimension 11: Regime and Worst-Window Diagnostics

Repeated weak windows include 2022Q2 and 2023Q3. These should become explicit stress
rows, not afterthoughts.

Regime buckets:

- market breadth high/low
- turnover high/low
- volatility shock
- strong trend, weak trend, range-bound
- candidate scarcity
- sector concentration
- limit-up ecology strong/weak

Required worst-window output:

- worst 10 fold rows per candidate
- per-regime metrics
- whether new factors improve or worsen the known weak regimes
- whether mean gains are just strong-window overfitting

Champion rule:

- Do not accept a model that wins mean but materially lowers the worst-window floor
  relative to the stable baseline.

## Dimension 12: Backend, Runtime, and Reproducibility

Training quality includes reproducibility.

Every matrix row should record:

- Python executable
- package versions
- GPU/CPU backend
- seed
- code hash
- data hash
- feature cache path/hash
- selected feature hash
- bundle hash
- dirty git status
- run command
- resume status

Runtime comparisons:

- GPU versus CPU only as engineering parity, not as model-selection objective.
- CatBoost subprocess versus in-process if memory/runtime failures appear.
- deterministic settings where supported.

P0/P1 examples:

- incomplete fold rows: P1
- mixed backend without recording: P1
- failed bundle validation: P1/P0 depending severity
- P0 feature selected: P0
- Q1/April used in training/HPO/threshold: P0

## Dimension 13: Web/Live Gate

No offline champion matters if Web/live cannot reproduce it.

Gate checklist:

- model bundle exists
- bundle meta exists
- selected features order fixed
- train/live mapping fixed
- strict P0 selected = 0
- missing live features = 0
- no silent fill for missing live features
- golden replay from saved 14:57 snapshot
- formal, postclose, test, and replay modes have distinct semantics
- ST/suspended/delisting/limit-up executable filters verified
- 14:57 runtime within operational window

Postclose mode:

- useful for "what would a full-data/postclose diagnostic model output?"
- not a substitute for formal 14:57 training
- should report drift versus formal 14:57, not be mixed into champion training.

## Recommended Execution Ladder After Data Completes

### Phase A: Cache and Asof Audit

Inputs:

- completed 1min/5min caches
- daily/T-1 context
- limit pool snapshots
- sector/theme membership

Outputs:

- 14:57-asof feature cache manifest
- monthly coverage table
- schema parity table
- P0/P1 audit

Exit:

- P0=0, P1=0.

### Phase B: Baseline Rebuild

Run:

- PhaseC strict baseline rebuilt under true 14:57-asof semantics
- S2 best9 rebuilt under true 14:57-asof semantics
- S2-only clean increments rebuilt under true 14:57-asof semantics

Use:

- full 23-fold `fixed_recent_36m`
- no Q1/April selection

Exit:

- establish new stable baseline.

### Phase C: Factor Families

Run:

- PhaseC strict feature set
- S2 rehabilitated groups
- C174-C188 5min groups
- C189-C193 1min groups
- first-wave C223-C292 groups after formula/data locks
- A-only full set
- A + explicit B/T-1 policy sets

Exit:

- 2-4 clean factor-family candidates.

### Phase D: Non-Factor Matrix

On the 2-4 clean candidates only:

1. training window sensitivity
2. candidate-pool gate matrix
3. feature-selection method and budget matrix
4. model-family fixed comparison
5. calibration/selector matrix
6. HPO
7. multi-seed
8. ensemble
9. strategy/regime diagnostics

Exit:

- champion candidate + 1-2 challengers, or NO_FREEZE.

### Phase E: Freeze and Score-Only Checks

Run:

- frozen Q1 seen-research score-only
- frozen April seen-research score-only
- future post-freeze final_forward only after enough new samples

Exit:

- deployable only after Web/live gate and future forward evidence.

## Priority Order

1. Finish and audit true 1min/5min 14:57-asof cache.
2. Rebuild PhaseC and S2 under true asof semantics.
3. Run full 23-fold fixed_recent_36m for PhaseC/S2/S2-only/C174-C193 first wave.
4. Run candidate-pool gate matrix on the strongest clean family.
5. Run feature-selection/budget matrix.
6. Run model-family fixed comparison.
7. Run HPO only on top 2-4 candidates.
8. Run multi-seed and ensemble.
9. Run strategy/regime diagnostics.
10. Freeze 1-3 bundles and do score-only checks.

## What Not To Do

- Do not decide champion from PhaseC, Q1, April, or a single strong fold.
- Do not train formal 14:57 champion on postclose 15:00 T-day values.
- Do not discard S2 just because old S2 used daily close semantics; rehabilitate its
  asof-computable columns.
- Do not include all C223-C292 in one large training run before formula/data gates.
- Do not use social/news/event candidates until timestamped asof pipelines exist.
- Do not treat strategy backtest as a replacement for rolling Wilson stability.
- Do not call a model final before future forward evidence exists.

## Self-Audit

| Check | Result | Notes |
|---|---|---|
| Read prior professional plans | PASS | 2026-05-07/09/11/13/15 docs reviewed. |
| Included non-factor dimensions | PASS | Windows, pool gates, selectors, HPO, model family, seed, strategy, regime, Web. |
| Preserved strict 14:57 constraint | PASS | Asof cache is the first gate. |
| Avoided Q1/April contamination | PASS | Kept score-only seen-research role. |
| Avoided S2 misclassification | PASS | S2 is rehabilitated as asof candidate, not discarded. |
| Avoided training before data completion | PASS | This is a protocol document only. |
| P0/P1 workflow included | PASS | Each phase requires audit before progression. |

## Bottom Line

After data completes, the project should not simply run "all factors versus PhaseC".
The correct path is:

1. build a true 14:57-asof cache,
2. rebuild PhaseC/S2/new factors under that exact semantics,
3. use full fixed_recent_36m rolling to select stable factor families,
4. then search candidate pool, feature budget, model family, HPO, calibration, selectors,
   seed, ensemble, and strategy layer on only the clean finalists.

This is the path most likely to find a model that is both accurate and stable without
repeating the earlier 15:00-versus-14:57 semantic mistake.
