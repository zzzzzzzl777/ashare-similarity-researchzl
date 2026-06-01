# Raw Factor Pool Audit — 2026-05-06

## Sources

| # | File | Source Doc | Records |
|---|------|-----------|---------|
| 1 | `factor_doc_scan_tgb_desktop_latest.jsonl` | 淘股吧短线因子提取文档 (549 KB) | 1,614 |
| 2 | `factor_doc_scan_short_desktop_latest.jsonl` | 短线操盘文档 (490 KB) | 1,245 |
| 3 | `factor_doc_scan_explore_desktop_latest.jsonl` | 因子探索文档 (53 KB) | 216 |
| | **Total** | | **3,075** |

All three are structured JSONL with 17 fields per record: `factor_name`, `raw_text`, `section`, `data_needs`, `asof_time`, `future_leakage_risk`, `free_data`, `needs_level2`, `needs_minute`, `needs_daily`, `priority`, `suggested_bucket`, `source_path`, `source_hash`, `source_mtime`, `source_size`, `line_number`.

---

## Key Statistics

| Metric | Value |
|--------|-------|
| Total records | 3,075 |
| Unique `factor_name` | 2,581 |
| Unique `normalized_name` | 2,581 |
| Exact `raw_text` duplicates | 164 records (58 groups) |
| Same-name duplicates | 807 records (313 groups) |
| Overall name-dedup rate | 16.1% (494 surplus records) |
| Exact-text dedup rate | 5.3% |

---

## By `data_needs` (flattened, multi-label)

| data_needs | Count | % of pool |
|-----------|-------|-----------|
| unknown | 1,785 | 58.0% |
| daily_ohlcv | 570 | 18.5% |
| limit_pool | 303 | 9.9% |
| sector_theme | 234 | 7.6% |
| minute | 229 | 7.4% |
| auction | 118 | 3.8% |
| lhb | 105 | 3.4% |
| level2 | 75 | 2.4% |
| announcement | 52 | 1.7% |
| hot_rank | 42 | 1.4% |
| cross_market | 27 | 0.9% |

---

## By `asof_time`

| asof_time | Count | % |
|-----------|-------|---|
| unknown | 1,804 | 58.7% |
| after_close | 862 | 28.0% |
| intraday_snapshot | 206 | 6.7% |
| after_close+intraday_snapshot | 148 | 4.8% |
| intraday_snapshot+after_close | 39 | 1.3% |
| source_limited_history+after_close | 9 | 0.3% |
| intraday_snapshot+source_limited_history+after_close | 7 | 0.2% |

---

## By `future_leakage_risk`

| Risk | Count | % |
|------|-------|---|
| low | 2,481 | 80.7% |
| medium | 594 | 19.3% |

---

## By `suggested_bucket`

| Bucket | Count | % |
|--------|-------|---|
| research | 2,960 | 96.3% |
| blocked | 75 | 2.4% |
| expanded | 40 | 1.3% |

---

## By `priority`

| Priority | Count | % |
|----------|-------|---|
| unknown | 2,915 | 94.8% |
| P2 | 49 | 1.6% |
| P1 | 47 | 1.5% |
| P0 | 41 | 1.3% |
| P3 | 23 | 0.7% |

---

## By `free_data`

| Value | Count | % |
|-------|-------|---|
| False | 2,028 | 65.9% |
| True | 1,047 | 34.1% |

---

## By `needs_level2`

| Value | Count | % |
|-------|-------|---|
| False | 3,000 | 97.6% |
| True | 75 | 2.4% |

---

## Readiness Classification

| Status | Count | % | Description |
|--------|-------|---|-------------|
| raw_unreviewed | 1,761 | 57.3% | Both asof_time and data_needs unknown; cannot assess without manual review |
| ready_for_registry_review | 697 | 22.7% | free_data=True, leakage=low, data/asof known — best candidates for registry |
| needs_engineering_review | 501 | 16.3% | leakage=medium or non-free with known data — requires formula/asof analysis |
| blocked_level2_or_nonfree | 75 | 2.4% | Requires Level-2 tick data — cannot implement with current cache |
| needs_data_check | 24 | 0.8% | data_needs known but asof unknown or free_data=False with low leakage |
| needs_asof_check | 17 | 0.6% | data_needs specified but asof_time unknown |

---

## Duplicate Analysis

### Exact raw_text duplicates (58 groups, 164 records)
These are identical text appearing in multiple source documents. Safe to deduplicate — keep one representative.

### Same-name duplicates (313 groups, 807 records)
Same `factor_name` appearing in different contexts or with different raw_text. These may represent:
- Same concept described differently in different sections
- Same name used for genuinely different factors
- Same factor with expanded/abbreviated descriptions

Recommendation: Keep all, tag with `same_name_group` for human review.

---

## Registry Cross-Reference Summary

| Dimension | Count |
|-----------|-------|
| Registry candidates (C001-C132) | 132 |
| Registry IDs matched to raw pool | 75 (56.8%) |
| Registry IDs with NO raw pool match | 57 (43.2%) |
| Raw pool records matched to registry | 235 (7.6%) |
| Raw pool records NOT in registry | 2,840 (92.4%) |

### Why 57 registry candidates have no raw pool match
These candidates (including C039-C041 blocked candidates) were:
- Created from GitHub papers/academic sources (not in taoguba documents)
- Created from social media/live trading observations
- Derived through engineering combination of existing concepts
- Named differently from any raw pool entry (synonym mismatch)

This is expected — the registry draws from 3 search paths (taoguba, github_paper, social_live), while the raw pool only covers the taoguba/短线/探索 desktop documents.

---

## Machine-Readable Index

**Path**: `E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json`

Size: 2,855 KB | Records: 3,075 | Format: JSON with `meta` + `records` array

Each record contains 20 fields including `raw_factor_id` (RAW000001-RAW003075), `normalized_name`, `readiness_status`, `registry_match_status`, and `matched_registry_id`.

---

## Encoding Status

**raw_text/section fields**: Valid UTF-8 Chinese. Zero records with high-latin byte patterns or unicode replacement characters detected. The "mojibake" appearance in terminal output is a Windows console codepage display issue, NOT data corruption. All markdown/JSON files render correctly in any UTF-8 editor.

**source_path fields**: Stored as filesystem-native encoding strings (Windows cp936 → UTF-8 JSON). These paths can be resolved programmatically via `os.listdir()` + size matching, but contain garbled display characters when printed to non-UTF-8 consoles.

**No raw_text_encoding_status field added** — no repair needed since the data is not actually corrupted.

---

## Constraints Confirmation

- [x] No training executed
- [x] No gpu_probe changes
- [x] No frozen_forward_config changes
- [x] No passed/final_unseen/final_accepted claims
- [x] Registry structure preserved (all 128 candidates intact)
- [x] Only additive changes to registry (new summary fields)

---

*Audit completed 2026-05-06. Next: review queue generation + registry summary field updates.*
