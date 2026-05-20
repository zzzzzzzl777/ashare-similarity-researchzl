# All-Factor Variant Manifest — 2026-05-07

**Status**: LOCKED (no modifications allowed after training starts)  
**Round**: 5  
**Total Variants**: 10  

---

## Standard Config (all variants)

```
start = 2023-05-01
train_end = 2025-12-31
test_start = 2026-01-01
test_end = 2026-03-31
feature_set = research
label_target = next_high_from_close
target_high_return_pct = 1.0
feature_selection_method = stable_tail
max_selected_features = 260
min_phase_days_3 = 1
exclude_event_limit_up = True
exclude_feature_prefix = ("cross_",)
seed = 42
lockbox_role = seen_research
final_acceptance_eligible = False
```

---

## Variant List

| # | Variant | Family | New Factors | Purpose |
|---|---------|--------|-------------|---------|
| V00 | baseline_control | control | None | Dedup-fixed baseline, no new factors |
| V01 | daily_ohlcv_all | smoke | C154-C162 (all 7) | Smoke: all new daily OHLCV together |
| V10 | single_C154 | single_factor | C154 only | price_vs_cost_20d |
| V11 | single_C156 | single_factor | C156 only | abnormal_3d_deviation |
| V12 | single_C157 | single_factor | C157 only | VOL_GAIN_20d |
| V13 | single_C158 | single_factor | C158 only | INV_t_20d |
| V14 | single_C159 | single_factor | C159 only | ASR_60d |
| V15 | single_C161 | single_factor | C161 only | ILLIQ_classic_20d |
| V16 | single_C162 | single_factor | C162 only | ATO_120d |
| V20 | daily_plus_minute_best | combo | C154-C162 + C133+C136+C138 | Max combo |

---

## Modification Policy

- Manifest is FROZEN at creation time
- No additions/deletions of variants after any training run starts
- If manifest has errors, STOP all training and rewrite manifest
- Results-driven additions are strictly forbidden (P1 violation)

---

## April Declaration

No variant has `is_april_allowed = True`. April known_holdout will only be used AFTER freeze decision on a separate frozen candidate bundle.

---

## Expected Training Runs

| Phase | Runs |
|-------|:----:|
| Phase 5 (Smoke) | 10 |
| Phase 6 (Pairwise, if top candidates emerge) | ~21 |
| Phase 7 (Seed stability, top 3) | 15 |
| Phase 7 (Budget stability, top 2) | 8 |
| Total maximum | ~54 |

---

*Manifest locked. Training may begin.*
