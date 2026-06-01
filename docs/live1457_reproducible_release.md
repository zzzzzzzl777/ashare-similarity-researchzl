# 14:57 PhaseC Web Reproducible Release

This repository contains the code and frozen runtime artifacts needed to bring
up the current PhaseC 14:57 candidate web console after a fresh clone of the
`codex/research-freeze-forward` branch.

## Included Runtime Artifacts

Artifacts are stored with Git LFS under `artifacts/`:

| File | Purpose |
| --- | --- |
| `live1457_phasec_core_20260521.tar.gz` | Frozen PhaseC model bundle, selected feature cache, model metadata, and historical validation CSVs. |
| `live1457_daily_bars_20260514.tar.gz` | Daily OHLCV parquet snapshot used by the live feature builders. |

The full raw Tushare cache is intentionally not committed because it is tens of
gigabytes and includes provider-specific local cache state. The live scripts use
local cache first and require `TUSHARE_TOKEN` or `TSY_TUSHARE_TOKEN` only when a
network fallback pull is needed.

## Fresh Clone Setup

Do not use GitHub's ZIP download for this release. The runtime archives are Git
LFS objects; a ZIP download or a clone without `git lfs pull` may contain only
small pointer files.

```powershell
git clone --branch codex/research-freeze-forward https://github.com/zzzzzzzl777/ashare-similarity-researchzl.git
cd ashare-similarity-researchzl
git lfs install
git lfs pull
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[gpu]"
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_live1457_runtime.ps1
```

If you want the runtime data somewhere other than
`E:\ashare_similarity_runtime\data`, pass a path explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_live1457_runtime.ps1 `
  -RuntimeRoot "D:\ashare_similarity_runtime\data"
$env:ASHARE_SIMILARITY_RUNTIME_DATA = "D:\ashare_similarity_runtime\data"
```

## Start The Web Console

```powershell
powershell -ExecutionPolicy Bypass -File .\start_1457_picker_web.ps1 -NoBrowser
```

Default local URL:

```text
http://127.0.0.1:8765/
```

For a VM or another machine on the LAN/Tailscale, use the host machine address
with port `8765`.

## Operational Notes

- `formal` is the production-style 14:57 path. It must use saved realtime
  snapshot data and must not silently zero-fill missing formal features.
- `postclose` is for after-close verification only.
- `test` is diagnostic only and can tolerate missing data for debugging.
- The bundled daily bars snapshot is sufficient to reproduce the current
  frozen state. Future trading days still need daily cache refreshes and valid
  realtime network access.
- A new machine still needs working realtime network access for the formal
  14:57 path. Configure `TUSHARE_TOKEN` or `TSY_TUSHARE_TOKEN` when fallback
  provider pulls are needed.
- `scripts/realtime_1457_today_probe.py`,
  `scripts/run_1457_live_sim.py`, and `scripts/serve_1457_picker_web.py` read
  `ASHARE_SIMILARITY_RUNTIME_DATA` / `ASHARE_SIMILARITY_DATA` when the runtime
  root is not the default.
