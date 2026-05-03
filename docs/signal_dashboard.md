# Signal Dashboard Architecture

## Overview

The Historical Backtest Signal Dashboard provides a web interface for reviewing
backtest results of frozen research candidates for the A-share T+1 prediction system.

**Status: research_only** — No candidates have passed final_unseen acceptance.

## Architecture

```
Offline Phase (CLI: build-signals)
  Feature Cache Parquet
    -> artifacts.py  (read frozen_candidates, run artifacts, selected_features)
    -> selectors.py  (replicate candidate_agreement / regime_probability_gate)
    -> cache.py      (train models, generate signal_cache.parquet + manifest.json)

Online Phase (Web Server)
  signal_cache.parquet + manifest.json
    -> service.py    (lazy-load on first request, query, aggregate)
    -> schemas.py    (typed Pydantic v2 responses)
    -> routes.py     (HTTP endpoints under /api/signals/v1/*)
    -> signals.html + signals.js (ECharts dashboard)
```

## Module Structure

```
src/ashare_similarity/prediction/signals/
  __init__.py     Public facade
  config.py       SignalConfig from AppConfig
  artifacts.py    Artifact / candidate reader
  selectors.py    Confidence selector replication
  cache.py        Signal cache builder
  service.py      SignalService (lazy-load, query)
  schemas.py      Pydantic v2 response models
  metrics.py      Accuracy, Wilson CI, Brier
```

## Data Flow

1. `build-signals` reads `frozen_candidates_20260503.json` to identify run artifacts
2. For each candidate, loads the feature cache parquet and run artifact
3. Replicates the exact train/test split and sampling protocol
4. Trains all candidate models using the same hyperparameters
5. Applies the frozen confidence selector parameters (no re-fitting)
6. Writes `signal_cache.parquet` (per-row predictions) and `manifest.json`
7. Web server lazy-loads cache on first API request

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/signals` | Dashboard HTML page |
| GET | `/api/signals/v1/status` | Cache status (always 200) |
| GET | `/api/signals/v1/dates` | Available dates |
| GET | `/api/signals/v1/daily` | Signals for a date |
| GET | `/api/signals/v1/stock` | Signals for a stock |
| GET | `/api/signals/v1/backtest` | Backtest summary + daily series |

## Date Layers

| Layer | Date Range | Purpose |
|-------|-----------|---------|
| dev_valid | 2025-07-01 to 2025-12-31 | Threshold selection / calibration |
| seen_research | 2026-01-01 to 2026-04-23 | Evaluation only |

Statistics are always computed per-layer, never mixed.
