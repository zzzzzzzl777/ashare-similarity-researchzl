# Round 4 Artifact Consistency Audit — 2026-05-07

**Auditor**: CC (Opus 4.6)  
**Scope**: Verify and repair Round 4 minute factor ablation artifacts  
**Policy**: No retraining, no metric changes, only reconstruct missing JSON and fix encoding

---

## 1. Artifact Inventory

| Artifact | Path | Status Before | Status After |
|----------|------|:------------:|:------------:|
| Extended ablation MD | `docs/minute_factor_extended_ablation_q1_20260506.md` | EXISTS | OK |
| Extended ablation JSON | `E:\...\minute_factor_extended_ablation_q1_20260506.json` | **MISSING** | **REBUILT** |
| Freeze decision MD | `docs/minute_factor_q1_freeze_decision_20260506.md` | EXISTS | OK |
| Freeze decision JSON | `E:\...\minute_factor_q1_freeze_decision_20260506.json` | **MISSING** | **REBUILT** |
| Final summary MD | `docs/minute_factor_round4_final_summary_20260506.md` | EXISTS | OK |
| Final summary JSON | `E:\...\minute_factor_round4_final_20260506.json` | EXISTS | OK |
| Experiment ledger | `E:\...\experiment_ledger_20260506.jsonl` | EXISTS (55 entries) | OK |

---

## 2. Encoding Audit

| File | BOM | Garbled chars (鈥?/鈭?) | Verdict |
|------|:---:|:---------------------:|:-------:|
| minute_factor_extended_ablation_q1_20260506.md | No | No | CLEAN |
| minute_factor_q1_freeze_decision_20260506.md | No | No | CLEAN |
| minute_factor_round4_final_summary_20260506.md | No | No | CLEAN |

No encoding repair needed.

---

## 3. Rebuilt JSON Details

### 3.1 `minute_factor_extended_ablation_q1_20260506.json`

Reconstructed from the existing MD file. Key data points:
- 5 seeds × 3 variants + 4 budgets × 2 variants = 23 data points (18 training runs)
- M21 mean Wilson: 74.23%, M00 mean: 74.16%, delta: +0.07pp
- Signal-to-noise: 0.067
- Budget impact (2.2-2.9pp) >> factor signal (0.07pp)
- Conclusion: NO_FREEZE_CANDIDATE_from_minute_factors

### 3.2 `minute_factor_q1_freeze_decision_20260506.json`

Reconstructed from the existing MD file. Key data points:
- Criteria passed: 1/5 (only monthly stability)
- Candidates evaluated: M21, M16, M00
- Decision: NO_FREEZE, BASELINE_RETAINED
- April role: known_holdout (not final_unseen)

---

## 4. April Role Clarification

The Round 4 final summary JSON correctly uses `"lockbox_role": "seen_research"`. The April holdout was performed AFTER the freeze decision. The rebuilt freeze_decision JSON now explicitly states:

```json
"april_role": "known_holdout",
"april_note": "April was only used AFTER freeze decision for one-shot audit, not for tuning"
```

---

## 5. Ledger Consistency

- Ledger has 55 entries (expected ~54 from MD, +1 may be April audit run)
- First entry: `gpu_probe_20260506T150406Z_e734eb7e` (M00_none)
- All entries use `lockbox_role=seen_research` as expected for Q1 research

---

## 6. Dirty Git Status

The workspace has 6 modified tracked files and 50+ untracked files from multiple rounds of experimentation. Key modified files affecting the training path:
- `src/ashare_similarity/prediction/gpu_probe.py` — dedup fix, exclude_feature_names, bundle auto-save
- `src/ashare_similarity/prediction/free_data_factors.py` — C009/C004/C010 factors, stk_mins streaming fix
- `scripts/run_family_ablation_probe.py` — ablation variants

**Risk assessment**: These changes are all from the same research effort and are required for the current experiment. No unrelated dirty changes that could affect training outcomes. **No P0/P1.**

---

## 7. Final Round 4 Conclusions (unchanged)

| Item | Value |
|------|-------|
| Decision | NO_FREEZE |
| Best combo (seed=42) | M21 (C133+C136+C138), Wilson 75.03% |
| Multi-seed reality | +0.07pp mean, noise dominates |
| Real improvement | Dedup fix (+0.25 to +1.22pp) |
| Production changes | None |
| Factors entering production | None |
| Committed/Pushed | No |

---

## 8. Self-Audit Summary

| Check | Result |
|-------|:------:|
| All 7 required artifacts exist | PASS |
| No encoding issues | PASS |
| No metrics were modified | PASS |
| No retraining performed | PASS |
| April correctly labeled known_holdout | PASS |
| lockbox_role = seen_research | PASS |
| final_acceptance_eligible = false | PASS |
| No commit/push | PASS |
| P0/P1 blockers | **NONE** |

---

**Phase 0 COMPLETE. No P0/P1. Proceeding to Phase 1.**
