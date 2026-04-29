# Release Checklist

## Before tagging

- [ ] `python -m pytest -q`
- [ ] If using an external data drive, `ashare_similarity.local.ps1` exists locally and bare `python -m ashare_similarity.cli doctor` resolves to the same data root as the scripts
- [ ] `powershell -ExecutionPolicy Bypass -File .\prepare_daily_ready.ps1`
- [ ] `run_logs/daily_ready.json` exists and shows `cache_status.daily.cached_symbols == filtered_universe_count`
- [ ] `run_logs/daily_ready.json` shows daily windows `5 / 8 / 10 / 20` with no missing or stale windows
- [ ] Every default daily index has `stale == false`, `artifact_missing == false`, and was built from the full cached universe; `symbol_count` may be lower for newly listed stocks without enough bars for that window
- [ ] `python -m ashare_similarity.cli doctor --frequency daily --window-size 10 --symbol 000333 --end-date <latest_data_at>` reports `overall_ready: true`, `coverage.cached_symbols == coverage.filtered_universe_count`, and `indexes.search_ready == true`
- [ ] If CUDA is available, `doctor.acceleration.active_backend` reports `torch-cuda-chunked` or another GPU backend; otherwise CPU fallback is explicitly shown
- [ ] Wheel build passes
- [ ] Homepage, `/api/search`, `/api/status`, export endpoints smoke-tested
- [ ] README / docs updated if user-facing behavior changed
- [ ] `CHANGELOG.md` updated
- [ ] Data / storage compatibility impact reviewed

## Before publishing

- [ ] Confirm default startup host and security boundary text are still accurate
- [ ] Confirm free-data limitations are still documented
- [ ] Confirm issue / PR templates still match current debugging workflow
