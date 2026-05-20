# 14:57 Next-Round Protocol Research

## Executive Summary

- Selected feature cache: `E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_550a77f54882058f.parquet`
- Current selected cache range: 2017-02-15 to 2026-04-30
- 5min raw cache range: 2017-01 to 2026-05
- Factor classes: {"D": 118, "A": 34, "B": 28, "C": 8}
- S2/PhaseC selected overlap: {"shared": 200, "s2_only": 60, "phasec_only": 0, "phasec_is_subset_of_s2": true}
- Self-audit: P0 fails=0, P1 fails=0

## Decision Notes

- April-only accuracy is not accepted as the champion selector; Q1 and April remain seen research windows.
- Extended 2017+ feature cache is ready for true training-window comparison.
- Rebuild helper is available: `python scripts/build_1457_extended_feature_cache.py --start 2017-01-03 --end 2026-04-30`.
- S2-only factors are not deleted by default; class A/B factors are retained for controlled fixed-config comparisons.
- B-class moneyflow/CYQ features require explicit T-1 or proxy columns with distinct names.

## Artifacts

- Factor source discovery: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_factor_source_discovery_20260513.csv`
- Time-window manifest: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_time_window_manifest_20260513.csv`
- Monthly timeline: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_monthly_timeline_20260513.csv`
- Model matrix manifest: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_model_matrix_manifest_20260513.csv`
- Self-audit: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_self_audit_20260513.csv`
- JSON payload: `E:\ashare_similarity_runtime\data\reports\prediction\next_round_1457_protocol_20260513.json`
