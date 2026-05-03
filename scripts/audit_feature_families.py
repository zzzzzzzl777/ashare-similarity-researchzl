"""Feature family audit — code-derived grouping + unused factor cross-tabulation.

Read-only audit. Does NOT modify training logic, configuration, or launch training.

Usage:
    python scripts/audit_feature_families.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.prediction.gpu_probe import (
    GPU_PROBE_BASE_FEATURES,
    GPU_PROBE_CROSS_MARKET_FEATURES,
    GPU_PROBE_FEATURES,
    GPU_PROBE_FREE_FACTOR_FEATURES,
    GPU_PROBE_INTRADAY_FACTOR_FEATURES,
    GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES,
    GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS,
    GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES,
    GPU_PROBE_RESEARCH_FEATURES,
    GPU_PROBE_RESEARCH_FREE_FACTOR_FEATURES,
    GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS,
    GPU_PROBE_STABLE_DAILY_FACTOR_FEATURES,
    GPU_PROBE_STABLE_FEATURES,
    GPU_PROBE_TGB_FACTOR_FEATURES,
    GPU_PROBE_THS_SECTOR_FEATURES,
    GPU_PROBE_TUSHARE_FACTOR_FEATURES,
)

POINTER_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\gpu_probe_latest.json")
TUSHARE_CACHE_ROOT = Path(r"E:\ashare_similarity_runtime\data\cache\prediction\tushare")
REPORT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
DOCS_DIR = REPO_ROOT / "docs"

TUSHARE_SUB_SOURCES: dict[str, list[str]] = {
    "moneyflow": [
        "tushare_net_mf_amount", "tushare_lg_buy_sell_ratio",
        "tushare_elg_buy_sell_ratio", "tushare_mf_strength", "tushare_sm_sell_pressure",
    ],
    "limit_list_d": [
        "tushare_seal_ratio", "tushare_open_times", "tushare_first_time_minutes",
        "tushare_up_stat_days", "tushare_limit_type", "tushare_limit_turnover",
    ],
    "top_list_inst": [
        "tushare_lhb_net_buy", "tushare_lhb_net_rate", "tushare_lhb_appeared",
        "tushare_inst_buy_count", "tushare_inst_net_buy",
    ],
    "hk_hold": ["tushare_hk_ratio", "tushare_hk_ratio_delta_1d"],
    "margin_detail": [
        "tushare_rzye", "tushare_rzye_delta_pct", "tushare_rzmre_ratio",
        "tushare_margin_net", "tushare_rqye_ratio",
    ],
    "ths_hot": ["tushare_hot_rank", "tushare_hot_value"],
    "daily_basic": ["tushare_volume_ratio", "tushare_free_share"],
    "cyq_perf": ["tushare_winner_rate", "tushare_cost_concentration", "tushare_cost_position"],
    "stk_auction": [
        "tushare_auction_open_vwap_ratio", "tushare_auction_open_vol",
        "tushare_auction_close_vwap_ratio", "tushare_auction_close_vol",
    ],
    "holdernumber": ["tushare_holder_num", "tushare_holder_num_delta_pct"],
    "stk_limit": ["tushare_up_limit_distance", "tushare_down_limit_distance", "tushare_limit_range"],
    "stk_mins_5": [
        "tushare_last_30min_return", "tushare_first_15min_volume_ratio",
        "tushare_vwap_deviation", "tushare_intraday_volatility",
        "tushare_up_volume_ratio", "tushare_high_time_pct", "tushare_close_vs_vwap",
    ],
}

TUSHARE_COVERAGE_NOTES: dict[str, str] = {
    "moneyflow": "high (~100% stock-day coverage)",
    "limit_list_d": "sparse (~2% stock-day; only limit-up stocks per day)",
    "top_list_inst": "sparse (~2% stock-day; only Dragon Tiger stocks)",
    "hk_hold": "~17% stock-day (northbound-held stocks only)",
    "margin_detail": "~36% stock-day (margin-eligible stocks only)",
    "ths_hot": "~25% stock-day (hot-list stocks only)",
    "daily_basic": "high (~100% stock-day)",
    "cyq_perf": "~55% stock-day (chip analysis coverage)",
    "stk_auction": "high (~100% stock-day)",
    "holdernumber": "quarterly release, ~high stock coverage per report",
    "stk_limit": "high (~100% stock-day)",
    "stk_mins_5": "~18% stock coverage (514 full + 82 partial / 3195 stocks)",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _count_parquets(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for f in directory.iterdir() if f.suffix == ".parquet")


def _with_available(columns: tuple[str, ...] | set[str]) -> set[str]:
    base = set(columns)
    return base | {f"{c}_available" for c in columns if not c.endswith("_available")}


def main() -> int:
    pointer = _load_json(POINTER_PATH)
    artifact_path = Path(pointer["artifact"])
    artifact = _load_json(artifact_path)
    result = artifact["result"]

    run_id = artifact["run_id"]
    feature_set = result["feature_set"]
    lockbox_role = artifact["lockbox_role"]
    exclude_prefix = result.get("exclude_feature_prefix", [])
    fs = result["feature_selection"]

    current_input = set(result["features"])
    selected = set(fs["selected_features"])
    input_unselected = current_input - selected
    skipped_priority = {s["feature"]: s for s in fs.get("skipped_priority_features", [])}

    research_raw = GPU_PROBE_RESEARCH_FEATURES
    research_unique = set(research_raw)
    research_not_in_current = research_unique - current_input

    # ------------------------------------------------------------------ #
    # Section 1: Pool sizes (raw vs unique)
    # ------------------------------------------------------------------ #
    ALL_CONSTANTS: OrderedDict[str, tuple[str, ...]] = OrderedDict([
        ("GPU_PROBE_FEATURES", GPU_PROBE_FEATURES),
        ("GPU_PROBE_STABLE_FEATURES", GPU_PROBE_STABLE_FEATURES),
        ("GPU_PROBE_BASE_FEATURES", GPU_PROBE_BASE_FEATURES),
        ("GPU_PROBE_RESEARCH_FEATURES", GPU_PROBE_RESEARCH_FEATURES),
        ("GPU_PROBE_FREE_FACTOR_FEATURES", GPU_PROBE_FREE_FACTOR_FEATURES),
        ("GPU_PROBE_RESEARCH_FREE_FACTOR_FEATURES", GPU_PROBE_RESEARCH_FREE_FACTOR_FEATURES),
        ("GPU_PROBE_STABLE_DAILY_FACTOR_FEATURES", GPU_PROBE_STABLE_DAILY_FACTOR_FEATURES),
        ("GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES", GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES),
        ("GPU_PROBE_TGB_FACTOR_FEATURES", GPU_PROBE_TGB_FACTOR_FEATURES),
        ("GPU_PROBE_THS_SECTOR_FEATURES", GPU_PROBE_THS_SECTOR_FEATURES),
        ("GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES", GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES),
        ("GPU_PROBE_INTRADAY_FACTOR_FEATURES", GPU_PROBE_INTRADAY_FACTOR_FEATURES),
        ("GPU_PROBE_TUSHARE_FACTOR_FEATURES", GPU_PROBE_TUSHARE_FACTOR_FEATURES),
        ("GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS", GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS),
        ("GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS", GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS),
        ("GPU_PROBE_CROSS_MARKET_FEATURES", GPU_PROBE_CROSS_MARKET_FEATURES),
    ])

    pool_sizes: dict[str, dict] = {}
    for name, tup in ALL_CONSTANTS.items():
        pool_sizes[name] = {"raw_count": len(tup), "unique_count": len(set(tup)),
                            "has_duplicates": len(tup) != len(set(tup))}

    # ------------------------------------------------------------------ #
    # Section 2: Official intersection table (non-mutually-exclusive)
    # ------------------------------------------------------------------ #
    OFFICIAL_FAMILIES: OrderedDict[str, set[str]] = OrderedDict([
        ("cross_market", _with_available(GPU_PROBE_CROSS_MARKET_FEATURES)),
        ("tgb", set(GPU_PROBE_TGB_FACTOR_FEATURES)),
        ("ths_sector", set(GPU_PROBE_THS_SECTOR_FEATURES)),
        ("stable_daily_factor", set(GPU_PROBE_STABLE_DAILY_FACTOR_FEATURES)),
        ("research_daily_factor", set(GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES)),
        ("limit_pool", set(GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES)),
        ("intraday", set(GPU_PROBE_INTRADAY_FACTOR_FEATURES)),
        ("tushare", set(GPU_PROBE_TUSHARE_FACTOR_FEATURES)),
        ("research_symbol_proxy", set(GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS)),
        ("research_cross_section", set(GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS)),
        ("free_factor_features", set(GPU_PROBE_FREE_FACTOR_FEATURES)),
        ("research_free_factor_features", set(GPU_PROBE_RESEARCH_FREE_FACTOR_FEATURES)),
    ])

    intersection_table: list[dict] = []
    for fam_name, fam_set in OFFICIAL_FAMILIES.items():
        row = {
            "family": fam_name,
            "family_unique_count": len(fam_set),
            "in_current_input": len(fam_set & current_input),
            "selected": len(fam_set & selected),
            "input_unselected": len(fam_set & input_unselected),
            "not_in_current": len(fam_set - current_input),
            "example_selected": sorted(fam_set & selected)[:3],
            "example_unselected": sorted(fam_set & input_unselected)[:3],
            "example_not_in_current": sorted(fam_set - current_input)[:3],
        }
        intersection_table.append(row)

    # ------------------------------------------------------------------ #
    # Section 3: Owner assignment table (mutually exclusive, first-match)
    # ------------------------------------------------------------------ #
    OWNER_PRIORITY: list[tuple[str, set[str]]] = [
        ("cross_market", _with_available(GPU_PROBE_CROSS_MARKET_FEATURES)),
        ("tgb", set(GPU_PROBE_TGB_FACTOR_FEATURES)),
        ("ths_sector", set(GPU_PROBE_THS_SECTOR_FEATURES)),
        ("stable_daily_factor", set(GPU_PROBE_STABLE_DAILY_FACTOR_FEATURES)),
        ("research_daily_factor", set(GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES)),
        ("limit_pool", set(GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES)),
        ("intraday", set(GPU_PROBE_INTRADAY_FACTOR_FEATURES)),
        ("tushare", set(GPU_PROBE_TUSHARE_FACTOR_FEATURES)),
        ("research_symbol_proxy", set(GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS)),
        ("research_cross_section", set(GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS)),
    ]

    assigned: dict[str, str] = {}
    for feat in sorted(research_unique):
        for fam_name, fam_set in OWNER_PRIORITY:
            if feat in fam_set:
                assigned[feat] = fam_name
                break
        else:
            assigned[feat] = "core_price_volume"

    owner_counts: dict[str, dict] = {}
    for fam_name in [p[0] for p in OWNER_PRIORITY] + ["core_price_volume"]:
        members = {f for f, o in assigned.items() if o == fam_name}
        owner_counts[fam_name] = {
            "owned_count": len(members),
            "in_current_input": len(members & current_input),
            "selected": len(members & selected),
            "input_unselected": len(members & input_unselected),
            "not_in_current": len(members - current_input),
        }

    orphans = research_unique - set(assigned.keys())
    duplicates = [f for f in assigned if list(assigned.values()).count(assigned[f]) > 1 and False]

    # ------------------------------------------------------------------ #
    # Section 4: Fact verification
    # ------------------------------------------------------------------ #
    stable_set = set(GPU_PROBE_STABLE_FEATURES)
    excluded_by_prefix_set = set()
    for prefix in exclude_prefix:
        excluded_by_prefix_set |= {f for f in stable_set if f.startswith(prefix)}

    stable_after_prefix = stable_set - excluded_by_prefix_set
    stable_only_missing = stable_after_prefix - current_input
    current_not_in_stable = current_input - stable_set
    unexpected = stable_only_missing

    fact_checks: list[dict] = []

    fact_checks.append({
        "check": "expanded maps to GPU_PROBE_STABLE_FEATURES",
        "result": feature_set == "expanded",
        "detail": f"artifact feature_set = '{feature_set}'",
    })

    fact_checks.append({
        "check": "stable excludes research_symbol AND research_cross_section",
        "result": (
            len(stable_set & set(GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS)) == 0
            and len(stable_set & set(GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS)) == 0
        ),
        "detail": (
            f"stable ∩ research_symbol = {len(stable_set & set(GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS))}, "
            f"stable ∩ research_cs = {len(stable_set & set(GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS))}"
        ),
    })

    cross_in_current = {f for f in current_input if any(f.startswith(p) for p in exclude_prefix)}
    fact_checks.append({
        "check": "exclude_feature_prefix=[cross_] removed cross_ features from current_input",
        "result": len(cross_in_current) == 0,
        "detail": (
            f"exclude_feature_prefix = {exclude_prefix}, "
            f"cross_ features in stable = {len(excluded_by_prefix_set)}, "
            f"cross_ features in current_input = {len(cross_in_current)}"
        ),
    })

    fact_checks.append({
        "check": "expanded / current_input reconciliation",
        "result": len(stable_only_missing) == 0 and len(current_not_in_stable) == 0,
        "detail": {
            "stable_unique": len(stable_set),
            "excluded_by_prefix": len(excluded_by_prefix_set),
            "excluded_by_prefix_features": sorted(excluded_by_prefix_set),
            "stable_after_prefix_exclusion": len(stable_after_prefix),
            "current_input_count": len(current_input),
            "stable_only_missing_from_current": sorted(stable_only_missing),
            "current_not_in_stable": sorted(current_not_in_stable),
            "dropped_or_unexpected": sorted(unexpected),
        },
    })

    tgb_in = len(set(GPU_PROBE_TGB_FACTOR_FEATURES) & current_input)
    ths_in = len(set(GPU_PROBE_THS_SECTOR_FEATURES) & current_input)
    sdaily_in = len(set(GPU_PROBE_STABLE_DAILY_FACTOR_FEATURES) & current_input)
    tushare_in = len(set(GPU_PROBE_TUSHARE_FACTOR_FEATURES) & current_input)
    intraday_in = len(set(GPU_PROBE_INTRADAY_FACTOR_FEATURES) & current_input)
    lp_in = len(set(GPU_PROBE_LIMIT_POOL_FACTOR_FEATURES) & current_input)
    rdaily_in = len(set(GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES) & current_input)
    rsymbol_in = len(set(GPU_PROBE_RESEARCH_SYMBOL_FACTOR_COLUMNS) & current_input)
    rcs_in = len(set(GPU_PROBE_RESEARCH_CROSS_SECTION_FACTOR_COLUMNS) & current_input)

    fact_checks.append({
        "check": "family presence in current_input",
        "result": (
            tgb_in > 0 and ths_in > 0 and sdaily_in > 0
            and tushare_in == 0 and intraday_in == 0 and lp_in == 0
            and rdaily_in == 0 and rsymbol_in == 0 and rcs_in == 0
        ),
        "detail": {
            "tgb_in_current": tgb_in,
            "ths_sector_in_current": ths_in,
            "stable_daily_in_current": sdaily_in,
            "tushare_in_current": tushare_in,
            "intraday_in_current": intraday_in,
            "limit_pool_in_current": lp_in,
            "research_daily_in_current": rdaily_in,
            "research_symbol_in_current": rsymbol_in,
            "research_cs_in_current": rcs_in,
        },
    })

    # ------------------------------------------------------------------ #
    # Section 5: Tushare sub-source breakdown
    # ------------------------------------------------------------------ #
    tushare_sub_report: list[dict] = []
    mapped_tushare = set()
    for api, columns in TUSHARE_SUB_SOURCES.items():
        cols_set = set(columns)
        avail_set = {f"{c}_available" for c in columns}
        all_set = cols_set | avail_set
        mapped_tushare |= all_set

        cache_dir = TUSHARE_CACHE_ROOT / api.replace("top_list_inst", "top_list")
        if api == "stk_mins_5":
            cache_dir = TUSHARE_CACHE_ROOT / "stk_mins_5"
        parquet_count = _count_parquets(cache_dir)

        tushare_sub_report.append({
            "api": api,
            "base_columns": len(columns),
            "with_available": len(all_set),
            "columns": columns,
            "coverage_note": TUSHARE_COVERAGE_NOTES.get(api, "unknown"),
            "cache_parquet_count": parquet_count,
            "in_current_input": len(all_set & current_input),
            "selected": len(all_set & selected),
        })

    unmapped_tushare = set(GPU_PROBE_TUSHARE_FACTOR_FEATURES) - mapped_tushare
    tushare_sub_column_sum = sum(len(cols) for cols in TUSHARE_SUB_SOURCES.values())

    # ------------------------------------------------------------------ #
    # Section 6: Annotate input_unselected with family + reason
    # ------------------------------------------------------------------ #
    unselected_annotated: list[dict] = []
    for feat in sorted(input_unselected):
        owner = assigned.get(feat, "core_price_volume")
        reason = "stable_tail_low_score"
        if feat in skipped_priority:
            sp = skipped_priority[feat]
            reason = f"near_constant (nonzero_rate={sp.get('nonzero_rate', '?')}, std={sp.get('std', '?')})"
        elif feat.endswith("_available"):
            reason = "availability_flag_low_variance"
        unselected_annotated.append({"feature": feat, "owner_family": owner, "reason": reason})

    # ------------------------------------------------------------------ #
    # Section 7: Annotate research_not_in_current with family
    # ------------------------------------------------------------------ #
    not_in_current_annotated: list[dict] = []
    for feat in sorted(research_not_in_current):
        owner = assigned.get(feat, "core_price_volume")
        not_in_current_annotated.append({"feature": feat, "owner_family": owner})

    # ------------------------------------------------------------------ #
    # Build JSON output
    # ------------------------------------------------------------------ #
    json_output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "artifact_path": str(artifact_path),
        "lockbox_role": lockbox_role,
        "feature_set": feature_set,
        "exclude_feature_prefix": exclude_prefix,
        "pool_sizes": pool_sizes,
        "set_counts": {
            "current_input": len(current_input),
            "selected": len(selected),
            "input_unselected": len(input_unselected),
            "research_raw_count": len(research_raw),
            "research_unique_count": len(research_unique),
            "research_not_in_current": len(research_not_in_current),
        },
        "official_intersection_table": intersection_table,
        "owner_assignment_table": [
            {"family": fam, **counts} for fam, counts in owner_counts.items()
        ],
        "owner_assignment_checks": {
            "total_assigned": len(assigned),
            "research_unique": len(research_unique),
            "orphan_count": len(orphans),
            "orphans": sorted(orphans),
        },
        "fact_checks": fact_checks,
        "tushare_sub_sources": tushare_sub_report,
        "tushare_sub_column_sum": tushare_sub_column_sum,
        "tushare_unmapped_features": sorted(unmapped_tushare),
        "input_unselected_features": unselected_annotated,
        "research_not_in_current_features": not_in_current_annotated,
    }

    json_path = REPORT_DIR / "unused_factor_family_audit_20260503.json"
    json_path.write_text(json.dumps(json_output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] JSON written: {json_path}")

    # ------------------------------------------------------------------ #
    # Build Markdown output
    # ------------------------------------------------------------------ #
    md_lines: list[str] = []
    md = md_lines.append

    md("# Feature Family Audit — Code-Derived Grouping")
    md("")
    md(f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    md(f"> Run: `{run_id}`")
    md(f"> feature_set: `{feature_set}` → dispatches to `GPU_PROBE_STABLE_FEATURES`")
    md(f"> lockbox_role: `{lockbox_role}` (NOT final_unseen, NOT passed)")
    md(f"> exclude_feature_prefix: `{exclude_prefix}`")
    md("")

    md("---")
    md("")
    md("## 1. Pool Sizes (Raw vs Unique)")
    md("")
    md("| Constant | Raw | Unique | Duplicates? |")
    md("|----------|-----|--------|-------------|")
    for name, info in pool_sizes.items():
        dup = "YES" if info["has_duplicates"] else "no"
        md(f"| `{name}` | {info['raw_count']} | {info['unique_count']} | {dup} |")
    md("")

    md("## 2. Set Arithmetic")
    md("")
    md("| Set | Count |")
    md("|-----|-------|")
    md(f"| current_input (artifact result.features) | {len(current_input)} |")
    md(f"| selected (feature_selection.selected_features) | {len(selected)} |")
    md(f"| input_unselected (current_input − selected) | {len(input_unselected)} |")
    md(f"| research_raw (GPU_PROBE_RESEARCH_FEATURES raw len) | {len(research_raw)} |")
    md(f"| research_unique | {len(research_unique)} |")
    md(f"| research_not_in_current (research_unique − current_input) | {len(research_not_in_current)} |")
    md("")

    md("## 3. Official Intersection Table (Non-Mutually-Exclusive)")
    md("")
    md("Each row shows how a **code-defined constant set** intersects with current_input / selected.")
    md("Features CAN appear in multiple families (constants overlap by design).")
    md("")
    md("| Family | Unique | In Input | Selected | Unselected | Not In Input | Ex. Selected | Ex. Not-In-Input |")
    md("|--------|--------|----------|----------|------------|--------------|--------------|------------------|")
    for row in intersection_table:
        ex_sel = ", ".join(row["example_selected"][:2]) or "—"
        ex_not = ", ".join(row["example_not_in_current"][:2]) or "—"
        md(f"| {row['family']} | {row['family_unique_count']} | {row['in_current_input']} "
           f"| {row['selected']} | {row['input_unselected']} | {row['not_in_current']} "
           f"| {ex_sel} | {ex_not} |")
    md("")

    md("## 4. Owner Assignment Table (Mutually Exclusive, First-Match)")
    md("")
    md("Each feature assigned to exactly one family by priority order.")
    md(f"Total assigned: {len(assigned)}, research_unique: {len(research_unique)}, orphans: {len(orphans)}")
    md("")
    md("| Family | Owned | In Input | Selected | Unselected | Not In Input |")
    md("|--------|-------|----------|----------|------------|--------------|")
    for fam_name in [p[0] for p in OWNER_PRIORITY] + ["core_price_volume"]:
        c = owner_counts[fam_name]
        md(f"| {fam_name} | {c['owned_count']} | {c['in_current_input']} "
           f"| {c['selected']} | {c['input_unselected']} | {c['not_in_current']} |")
    md("")

    md("## 5. Fact Verification")
    md("")
    for fc in fact_checks:
        status = "PASS" if fc["result"] else "FAIL"
        md(f"### [{status}] {fc['check']}")
        md("")
        detail = fc["detail"]
        if isinstance(detail, dict):
            for k, v in detail.items():
                if isinstance(v, list) and len(v) > 10:
                    md(f"- **{k}**: {len(v)} items")
                elif isinstance(v, list):
                    md(f"- **{k}**: {v}")
                else:
                    md(f"- **{k}**: {v}")
        else:
            md(f"- {detail}")
        md("")

    md("## 6. Tushare Sub-Source Breakdown")
    md("")
    md("| API | Base Cols | +Avail | Cache Parquets | Coverage Note | In Input | Selected |")
    md("|-----|-----------|--------|----------------|---------------|----------|----------|")
    for sr in tushare_sub_report:
        md(f"| {sr['api']} | {sr['base_columns']} | {sr['with_available']} "
           f"| {sr['cache_parquet_count']} | {sr['coverage_note']} "
           f"| {sr['in_current_input']} | {sr['selected']} |")
    md("")
    md(f"Sub-source base column sum: {tushare_sub_column_sum} "
       f"(should equal TUSHARE_FACTOR_COLUMNS unique base: "
       f"{len([f for f in GPU_PROBE_TUSHARE_FACTOR_FEATURES if not f.endswith('_available')])})")
    if unmapped_tushare:
        md(f"Unmapped tushare features: {sorted(unmapped_tushare)}")
    md("")

    md("## 7. Input-Unselected Features (the 92)")
    md("")
    md("| Feature | Owner Family | Reason |")
    md("|---------|-------------|--------|")
    for item in unselected_annotated:
        md(f"| `{item['feature']}` | {item['owner_family']} | {item['reason']} |")
    md("")

    md("## 8. Next-Step Recommendations")
    md("")
    md("### A. Already in input pool, not selected (review candidates)")
    md("")
    md("These 92 features entered the training pipeline but were eliminated by stable_tail.")
    md("Most are `_available` flags (near-constant, no action needed) or board per-stock")
    md("features zeroed out by `exclude_event_limit_up` + `short_only` sample filter.")
    md("")
    md("**Actionable subset** (non-available, non-near-constant):")
    md("")
    actionable = [i for i in unselected_annotated
                  if "near_constant" not in i["reason"] and "availability_flag" not in i["reason"]]
    for item in actionable:
        md(f"- `{item['feature']}` ({item['owner_family']})")
    md("")

    md("### B. Not in input pool — needs feature_set=research or config change")
    md("")
    family_groups: dict[str, list[str]] = {}
    for item in not_in_current_annotated:
        family_groups.setdefault(item["owner_family"], []).append(item["feature"])
    for fam, feats in sorted(family_groups.items(), key=lambda x: -len(x[1])):
        base_feats = [f for f in feats if not f.endswith("_available")]
        md(f"- **{fam}**: {len(feats)} total ({len(base_feats)} base + {len(feats)-len(base_feats)} _available)")
    md("")

    md("### C. Priority ablation suggestion")
    md("")
    md("Do NOT open all families at once. Pick 1-2 with best data readiness:")
    md("")
    md("1. **research_daily_factor** (47 base, 100% coverage, zero external dependency).")
    md("   Several members already proved signal in prior research runs")
    md("   (`seal_rate_80_threshold`, `buy_sell_cycle_phase`, `cycle_day_count`, etc.).")
    md("   Ablation: run `feature_set=expanded` + manually add these 47 columns to stable set,")
    md("   compare HC metrics on `seen_research` split.")
    md("")
    md("2. **tushare** — but NOT all 46 at once. Sub-source priority by coverage:")
    md("   - Tier 1 (high coverage): daily_basic(2), stk_limit(3), stk_auction(4), moneyflow(5) = 14 columns")
    md("   - Tier 2 (medium): cyq_perf(3), margin_detail(5), holdernumber(2) = 10 columns")
    md("   - Tier 3 (sparse): limit_list_d(6), top_list_inst(5), hk_hold(2), ths_hot(2) = 15 columns")
    md("   - Tier 4 (blocked): stk_mins_5(7) — 18% stock coverage, wait for pull completion")
    md("   Start ablation with Tier 1 only (14 columns).")
    md("")
    md("### D. Explicitly not recommended yet")
    md("")
    md("- **limit_pool**: 19% date coverage, 49/50 near-constant in prior research run")
    md("- **intraday (stk_mins_5)**: 18% stock coverage, need full pull")
    md("- **research_symbol_proxy / research_cross_section**: 0 selected in prior research runs")
    md("")

    md_path = DOCS_DIR / "unused_factor_family_audit_20260503.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[OK] Markdown written: {md_path}")

    # ------------------------------------------------------------------ #
    # Console summary
    # ------------------------------------------------------------------ #
    print()
    print(f"Run: {run_id}")
    print(f"feature_set={feature_set}, lockbox_role={lockbox_role}")
    print(f"current_input={len(current_input)}, selected={len(selected)}, "
          f"input_unselected={len(input_unselected)}")
    print(f"research_unique={len(research_unique)}, research_not_in_current={len(research_not_in_current)}")
    print()
    print("Fact checks:")
    for fc in fact_checks:
        status = "PASS" if fc["result"] else "FAIL"
        print(f"  [{status}] {fc['check']}")
    print()
    print(f"Owner assignment: {len(assigned)} features, {len(orphans)} orphans")
    print(f"Tushare sub-source column sum: {tushare_sub_column_sum}")
    if unmapped_tushare:
        print(f"  WARNING: unmapped tushare features: {sorted(unmapped_tushare)}")

    all_pass = all(fc["result"] for fc in fact_checks)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
