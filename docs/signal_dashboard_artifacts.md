# Signal Dashboard Artifacts

## Frozen Candidates JSON

Located at `{report_dir}/prediction/frozen_candidates_20260503.json`.

Contains an array of candidate configurations with:
- `tag`: candidate identifier (accuracy_priority / coverage_priority)
- `run_id`: source gpu_probe run identifier
- `config`: training configuration parameters
- `metrics`: reference backtest metrics from original run
- Hash fields: feature_hash, data_hash, split_hash, code_hash

## Run Artifact

Located at `{report_dir}/prediction/runs/{run_id}/artifact.json`.

Key fields used by build-signals:
- `result.feature_selection.selected_features` — feature name list (read-only)
- `result.classification_threshold` — decision threshold
- `result.confidence_selector` — selector method and parameters
- `result.candidate_reports` — per-model training results
- `result.feature_cache.fingerprint` — feature cache identifier
- `result.feature_cache.path` — path to feature cache parquet

## Feature Manifest

Located at `{report_dir}/prediction/runs/{run_id}/feature_manifest.json`.

Contains feature cache fingerprint and path for cache validation.

## Signal Cache Parquet

Schema:
| Column | Type | Description |
|--------|------|-------------|
| date | datetime | Trading date |
| symbol | str | 6-digit stock code |
| model_tag | str | accuracy_priority / coverage_priority |
| best_model | str | Winning model name |
| selector_method | str | Confidence selector method |
| probability | float32 | Predicted probability |
| confident | bool | Passed confidence selector |
| actual | float32 | Actual label value |
| split_layer | str | dev_valid / seen_research |

## Manifest JSON

Top-level build metadata with `candidates[]` array.
Each candidate entry includes:
- All hash fields for integrity verification
- Selector parameters (from artifact, not re-fitted)
- `artifact_reference`: original run metrics
- `cache_metrics`: metrics computed on this build's signal cache
