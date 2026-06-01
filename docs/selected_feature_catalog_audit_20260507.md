# Selected Feature Catalog Audit - 2026-05-07

Generated: 2026-05-07T22:05:32.277798

## Audit Summary

| Run | Total | Factor | Baseline | Unmapped | Blocked | Duplicate | Violations |
|-----|-------|--------|----------|----------|---------|-----------|------------|
| c0497be3_TRUE_baseline | 755 | 6 | 749 | 0 | 8 | 2 | 2 |
| bb25159b_round4 | 376 | 4 | 372 | 0 | 0 | 0 | 0 |
| 960529e8_superset | 769 | 20 | 749 | 0 | 8 | 2 | 2 |
| 240a4b24_superset | 787 | 38 | 749 | 0 | 8 | 2 | 2 |

## c0497be3_TRUE_baseline

- Run ID: `gpu_probe_20260507T105820Z_c0497be3`
- Artifact: `E:/ashare_similarity_runtime/data/reports/prediction/runs/gpu_probe_20260507T105820Z_c0497be3/artifact.json`
- Total selected features: 755
- Mapped to factor_id: 6
- Mapped to baseline_family: 749
- Unmapped: 0
- Blocked: 8
- Duplicate: 2

### Gate Violations

- **P0**: blocked_features_in_selected > 0 (count=8)
  - `tushare_mf_flow_intensity`
  - `tushare_float_relative_impact`
  - `tushare_vwap_deviation`
  - `tushare_close_vs_vwap`
  - `tushare_mf_flow_intensity_available`
  - `tushare_float_relative_impact_available`
  - `tushare_vwap_deviation_available`
  - `tushare_close_vs_vwap_available`
- **P1**: duplicate_features_in_selected > 0 (count=2)
  - `tushare_close_vs_vwap`
  - `tushare_close_vs_vwap_available`

### Blocked Features in Selected

- `tushare_mf_flow_intensity` (C139_area_not_engineered)
- `tushare_float_relative_impact` (C_area_not_engineered)
- `tushare_vwap_deviation` (C135_blocked_until_outlier_guard)
- `tushare_close_vs_vwap` (duplicate_of_C135_no_factor_id)
- `tushare_mf_flow_intensity_available` (C139_area_not_engineered (available flag))
- `tushare_float_relative_impact_available` (C_area_not_engineered (available flag))
- `tushare_vwap_deviation_available` (C135_blocked_until_outlier_guard (available flag))
- `tushare_close_vs_vwap_available` (duplicate_of_C135_no_factor_id (available flag))

### Duplicate Features in Selected

- `tushare_close_vs_vwap` (duplicate of `tushare_vwap_deviation`)
- `tushare_close_vs_vwap_available` (duplicate of `tushare_vwap_deviation_available`)

## bb25159b_round4

- Run ID: `gpu_probe_20260505T113406Z_bb25159b`
- Artifact: `E:/ashare_similarity_runtime/data/reports/prediction/runs/gpu_probe_20260505T113406Z_bb25159b/artifact.json`
- Total selected features: 376
- Mapped to factor_id: 4
- Mapped to baseline_family: 372
- Unmapped: 0
- Blocked: 0
- Duplicate: 0

### Gate Violations: NONE

## 960529e8_superset

- Run ID: `gpu_probe_20260507T100546Z_960529e8`
- Artifact: `E:/ashare_similarity_runtime/data/reports/prediction/runs/gpu_probe_20260507T100546Z_960529e8/artifact.json`
- Total selected features: 769
- Mapped to factor_id: 20
- Mapped to baseline_family: 749
- Unmapped: 0
- Blocked: 8
- Duplicate: 2

### Gate Violations

- **P0**: blocked_features_in_selected > 0 (count=8)
  - `tushare_mf_flow_intensity`
  - `tushare_float_relative_impact`
  - `tushare_vwap_deviation`
  - `tushare_close_vs_vwap`
  - `tushare_mf_flow_intensity_available`
  - `tushare_float_relative_impact_available`
  - `tushare_vwap_deviation_available`
  - `tushare_close_vs_vwap_available`
- **P1**: duplicate_features_in_selected > 0 (count=2)
  - `tushare_close_vs_vwap`
  - `tushare_close_vs_vwap_available`

### Blocked Features in Selected

- `tushare_mf_flow_intensity` (C139_area_not_engineered)
- `tushare_float_relative_impact` (C_area_not_engineered)
- `tushare_vwap_deviation` (C135_blocked_until_outlier_guard)
- `tushare_close_vs_vwap` (duplicate_of_C135_no_factor_id)
- `tushare_mf_flow_intensity_available` (C139_area_not_engineered (available flag))
- `tushare_float_relative_impact_available` (C_area_not_engineered (available flag))
- `tushare_vwap_deviation_available` (C135_blocked_until_outlier_guard (available flag))
- `tushare_close_vs_vwap_available` (duplicate_of_C135_no_factor_id (available flag))

### Duplicate Features in Selected

- `tushare_close_vs_vwap` (duplicate of `tushare_vwap_deviation`)
- `tushare_close_vs_vwap_available` (duplicate of `tushare_vwap_deviation_available`)

## 240a4b24_superset

- Run ID: `gpu_probe_20260507T105225Z_240a4b24`
- Artifact: `E:/ashare_similarity_runtime/data/reports/prediction/runs/gpu_probe_20260507T105225Z_240a4b24/artifact.json`
- Total selected features: 787
- Mapped to factor_id: 38
- Mapped to baseline_family: 749
- Unmapped: 0
- Blocked: 8
- Duplicate: 2

### Gate Violations

- **P0**: blocked_features_in_selected > 0 (count=8)
  - `tushare_mf_flow_intensity`
  - `tushare_float_relative_impact`
  - `tushare_vwap_deviation`
  - `tushare_close_vs_vwap`
  - `tushare_mf_flow_intensity_available`
  - `tushare_float_relative_impact_available`
  - `tushare_vwap_deviation_available`
  - `tushare_close_vs_vwap_available`
- **P1**: duplicate_features_in_selected > 0 (count=2)
  - `tushare_close_vs_vwap`
  - `tushare_close_vs_vwap_available`

### Blocked Features in Selected

- `tushare_mf_flow_intensity` (C139_area_not_engineered)
- `tushare_float_relative_impact` (C_area_not_engineered)
- `tushare_vwap_deviation` (C135_blocked_until_outlier_guard)
- `tushare_close_vs_vwap` (duplicate_of_C135_no_factor_id)
- `tushare_mf_flow_intensity_available` (C139_area_not_engineered (available flag))
- `tushare_float_relative_impact_available` (C_area_not_engineered (available flag))
- `tushare_vwap_deviation_available` (C135_blocked_until_outlier_guard (available flag))
- `tushare_close_vs_vwap_available` (duplicate_of_C135_no_factor_id (available flag))

### Duplicate Features in Selected

- `tushare_close_vs_vwap` (duplicate of `tushare_vwap_deviation`)
- `tushare_close_vs_vwap_available` (duplicate of `tushare_vwap_deviation_available`)
