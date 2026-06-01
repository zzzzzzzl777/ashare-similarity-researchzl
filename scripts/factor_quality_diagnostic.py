"""Read-only factor quality diagnostic for Tushare daily + Research Daily factors.

Reads existing feature cache parquets and tushare raw caches.
Does NOT run any training, does NOT modify any config, does NOT pull data.
Output: docs/factor_quality_diagnostic_20260503.md
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_HOME = Path("E:/ashare_similarity_runtime")
FEATURE_CACHE_DIR = RUNTIME_HOME / "data" / "reports" / "prediction" / "feature_cache"
TUSHARE_CACHE_DIR = RUNTIME_HOME / "data" / "cache" / "prediction" / "tushare"
FROZEN_ARTIFACT_DIR = (
    RUNTIME_HOME / "data" / "reports" / "prediction" / "runs"
    / "gpu_probe_20260501T155956Z_d64e3464"
)

RESEARCH_FEATURE_CACHE = FEATURE_CACHE_DIR / "gpu_probe_features_27f3f4cc8c1b747f.parquet"

TUSHARE_SUB_SOURCES = {
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
    "cyq_perf": [
        "tushare_winner_rate", "tushare_cost_concentration", "tushare_cost_position",
    ],
    "stk_auction": [
        "tushare_auction_open_vwap_ratio", "tushare_auction_open_vol",
        "tushare_auction_close_vwap_ratio", "tushare_auction_close_vol",
    ],
    "stk_holdernumber": ["tushare_holder_num", "tushare_holder_num_delta_pct"],
    "stk_limit": [
        "tushare_up_limit_distance", "tushare_down_limit_distance", "tushare_limit_range",
    ],
}

RESEARCH_DAILY_COLUMNS = [
    "market_limit_seal_success_rate", "seal_rate_80_threshold",
    "market_limit_down_rate", "market_one_word_board_count",
    "market_high_leader_crash_count", "cycle_day_count", "divergence_day_count",
    "buy_sell_cycle_phase", "liquidity_exhaustion_signal", "market_split_signal",
    "quant_climax_type", "vol_stagnation_signal", "bull_rotation_upgrade",
    "theme_capacity_score", "market_amount_ratio_20", "market_amount_percentile_60",
    "volume_is_king_signal", "ground_volume_risk", "post_decline_transition",
    "decline_stabilize_signal", "weak_friday_risk", "prev_top20_chase_return",
    "prev_top20_chase_win_rate", "prev_bottom20_rebound_return",
    "money_effect_spread_20", "collapse_warning_signal", "bullish_pivot_recognition",
    "limit_premium_failure_signal", "bad_sentiment_no_sweep",
    "high_leader_crash_sentiment_collapse", "no_theme_rotation_mode",
    "money_effect_sector_rotation", "full_position_trigger", "late_cycle_position_cap",
    "bear_position_reduction", "strong_market_regime", "weak_market_oversold_regime",
    "bull_hotspot_bear_oversold", "shrink_after_rotten", "explosive_vol_next_weak",
    "break_node_new_dragon", "dragon_replace_signal", "mid_cap_trap_risk",
    "buy_rise_divergence", "bet_decline_exhaustion", "board_keep_break_signal",
    "one_day_trip_risk_proxy",
]


def load_selected_260() -> list[str]:
    with open(FROZEN_ARTIFACT_DIR / "artifact.json", encoding="utf-8") as f:
        art = json.load(f)
    return art["result"]["feature_selection"]["selected_features"]


def compute_column_stats(df: pd.DataFrame, columns: list[str]) -> list[dict]:
    results = []
    for col in columns:
        if col not in df.columns:
            results.append({"column": col, "in_cache": False})
            continue
        series = df[col]
        total = len(series)
        nan_count = int(series.isna().sum())
        nan_pct = nan_count / total if total > 0 else 0
        valid = series.dropna()
        nonzero_count = int((valid != 0).sum())
        nonzero_pct = nonzero_count / len(valid) if len(valid) > 0 else 0
        std_val = float(valid.std()) if len(valid) > 1 else 0.0
        mean_val = float(valid.mean()) if len(valid) > 0 else 0.0
        min_val = float(valid.min()) if len(valid) > 0 else float("nan")
        max_val = float(valid.max()) if len(valid) > 0 else float("nan")
        near_constant = (std_val < 1e-8) or (nonzero_pct < 0.01)
        results.append({
            "column": col,
            "in_cache": True,
            "nan_pct": nan_pct,
            "nonzero_pct": nonzero_pct,
            "std": std_val,
            "mean": mean_val,
            "min": min_val,
            "max": max_val,
            "near_constant": near_constant,
            "flag_nan_high": nan_pct > 0.30,
        })
    return results


def compute_top_correlations(
    df: pd.DataFrame,
    target_cols: list[str],
    reference_cols: list[str],
    threshold: float = 0.90,
) -> dict[str, list[tuple[str, float]]]:
    target_in = [c for c in target_cols if c in df.columns]
    ref_in = [c for c in reference_cols if c in df.columns]
    if not target_in or not ref_in:
        return {}
    all_cols = list(set(target_in + ref_in))
    sub = df[all_cols].select_dtypes(include=[np.number])
    corr_matrix = sub.corr()
    results: dict[str, list[tuple[str, float]]] = {}
    for tc in target_in:
        if tc not in corr_matrix.columns:
            continue
        high_corr = []
        for rc in ref_in:
            if rc == tc or rc not in corr_matrix.columns:
                continue
            val = corr_matrix.loc[tc, rc]
            if abs(val) >= threshold:
                high_corr.append((rc, round(float(val), 4)))
        if high_corr:
            high_corr.sort(key=lambda x: -abs(x[1]))
            results[tc] = high_corr[:5]
    return results


def audit_tushare_raw_cache() -> list[dict]:
    results = []
    api_dirs = {
        "moneyflow": "moneyflow",
        "daily_basic": "daily_basic",
        "stk_limit": "stk_limit",
        "stk_auction_o": "stk_auction_o",
        "stk_auction_c": "stk_auction_c",
        "stk_holdernumber": "stk_holdernumber",
        "hk_hold": "hk_hold",
        "margin_detail": "margin_detail",
        "cyq_perf": "cyq_perf",
        "ths_hot": "ths_hot",
        "limit_list_d": "limit_list_d",
        "top_list": "top_list",
        "top_inst": "top_inst",
    }
    for api_name, dir_name in api_dirs.items():
        api_dir = TUSHARE_CACHE_DIR / dir_name
        if not api_dir.exists():
            results.append({"api": api_name, "exists": False})
            continue
        files = sorted([
            f.name for f in api_dir.iterdir()
            if f.suffix == ".parquet" and not f.name.startswith("_")
        ])
        is_per_stock = api_name == "cyq_perf"
        if is_per_stock:
            stock_count = len(files)
            sample_file = api_dir / files[0] if files else None
            date_count = 0
            date_min = date_max = None
            if sample_file and sample_file.exists():
                try:
                    sample_df = pd.read_parquet(sample_file)
                    if "trade_date" in sample_df.columns:
                        dates = pd.to_datetime(sample_df["trade_date"], format="%Y%m%d", errors="coerce").dropna()
                        date_count = len(dates.unique())
                        date_min = str(dates.min().date())
                        date_max = str(dates.max().date())
                    row_count = len(sample_df)
                except Exception:
                    row_count = 0
            results.append({
                "api": api_name, "exists": True, "is_per_stock": True,
                "stock_count": stock_count, "sample_dates": date_count,
                "date_min": date_min, "date_max": date_max,
            })
        else:
            date_strs = sorted([f.replace(".parquet", "") for f in files])
            date_count = len(date_strs)
            date_min = date_strs[0] if date_strs else None
            date_max = date_strs[-1] if date_strs else None
            sample_file = api_dir / files[len(files) // 2] if files else None
            stock_count = 0
            sample_cols = []
            if sample_file and sample_file.exists():
                try:
                    sample_df = pd.read_parquet(sample_file)
                    stock_col = next(
                        (c for c in ["ts_code", "code", "symbol"] if c in sample_df.columns),
                        None,
                    )
                    if stock_col:
                        stock_count = sample_df[stock_col].nunique()
                    sample_cols = list(sample_df.columns)
                except Exception:
                    pass
            results.append({
                "api": api_name, "exists": True, "is_per_stock": False,
                "date_count": date_count, "date_min": date_min, "date_max": date_max,
                "sample_stock_count": stock_count, "sample_columns": sample_cols,
            })
    return results


def generate_report(
    tushare_stats: list[dict],
    research_stats: list[dict],
    tushare_raw_audit: list[dict],
    tushare_corr: dict,
    research_corr: dict,
    selected_260: list[str],
    cache_meta: dict,
) -> str:
    lines = [
        "# Factor Quality Diagnostic Report",
        "",
        "> Generated: " + datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "> Scope: **seen_research diagnostic only** — read-only, no training, no config changes",
        "> Feature cache: `gpu_probe_features_27f3f4cc8c1b747f.parquet`",
        f"> Cache rows: {cache_meta.get('rows', '?')}, created: {cache_meta.get('created_at', '?')}",
        f"> Selected 260 source: frozen artifact `gpu_probe_20260501T155956Z_d64e3464`",
        "",
        "---",
        "",
        "## 1. Tushare Raw Cache Audit",
        "",
        "Per-API date/stock coverage from `E:\\ashare_similarity_runtime\\data\\cache\\prediction\\tushare\\`.",
        "Excludes `stk_mins_5` (18% stock coverage, not recommended yet).",
        "",
        "| API | Partitioning | Files/Dates | Date Range | Sample Stocks | Columns |",
        "|-----|-------------|-------------|------------|---------------|---------|",
    ]
    for r in tushare_raw_audit:
        if not r.get("exists", False):
            lines.append(f"| {r['api']} | — | 0 | — | — | — |")
            continue
        if r.get("is_per_stock"):
            lines.append(
                f"| {r['api']} | per-stock | {r['stock_count']} stocks | "
                f"{r.get('date_min','?')} ~ {r.get('date_max','?')} | "
                f"{r.get('sample_dates', '?')} dates/stock | per-stock parquet |"
            )
        else:
            cols_str = str(len(r.get("sample_columns", [])))
            lines.append(
                f"| {r['api']} | per-date | {r['date_count']} dates | "
                f"{r.get('date_min','?')} ~ {r.get('date_max','?')} | "
                f"{r.get('sample_stock_count', '?')} | {cols_str} cols |"
            )
    lines += ["", "---", ""]

    lines += [
        "## 2. Tushare Factor Column Stats (from research feature cache)",
        "",
        "Source: research-scope feature cache (259k rows, 2023-05 ~ 2026-04).",
        "Base columns only (excluding `_available` suffixes).",
        "",
        "| Sub-Source | Column | NaN% | Nonzero% | Std | Mean | Min | Max | Flags |",
        "|-----------|--------|------|----------|-----|------|-----|-----|-------|",
    ]
    for sub_source, cols in TUSHARE_SUB_SOURCES.items():
        for stat in tushare_stats:
            if stat["column"] not in cols:
                continue
            if not stat.get("in_cache", False):
                lines.append(f"| {sub_source} | `{stat['column']}` | — | — | — | — | — | — | NOT IN CACHE |")
                continue
            flags = []
            if stat.get("near_constant"):
                flags.append("NEAR_CONST")
            if stat.get("flag_nan_high"):
                flags.append("NaN>30%")
            flag_str = ", ".join(flags) if flags else "—"
            lines.append(
                f"| {sub_source} | `{stat['column']}` | "
                f"{stat['nan_pct']:.2%} | {stat['nonzero_pct']:.2%} | "
                f"{stat['std']:.4f} | {stat['mean']:.4f} | "
                f"{stat['min']:.4f} | {stat['max']:.4f} | {flag_str} |"
            )
    lines += ["", "---", ""]

    lines += [
        "## 3. Research Daily Factor Column Stats",
        "",
        "Extended emotion/board structure columns from `GPU_PROBE_RESEARCH_FACTOR_COLUMNS` (47 base).",
        "These are market-level daily factors computed from local cache (100% coverage expected).",
        "",
        "| Column | NaN% | Nonzero% | Std | Mean | Min | Max | Flags |",
        "|--------|------|----------|-----|------|-----|-----|-------|",
    ]
    for stat in research_stats:
        if not stat.get("in_cache", False):
            lines.append(f"| `{stat['column']}` | — | — | — | — | — | — | NOT IN CACHE |")
            continue
        flags = []
        if stat.get("near_constant"):
            flags.append("NEAR_CONST")
        if stat.get("flag_nan_high"):
            flags.append("NaN>30%")
        flag_str = ", ".join(flags) if flags else "—"
        lines.append(
            f"| `{stat['column']}` | "
            f"{stat['nan_pct']:.2%} | {stat['nonzero_pct']:.2%} | "
            f"{stat['std']:.4f} | {stat['mean']:.4f} | "
            f"{stat['min']:.4f} | {stat['max']:.4f} | {flag_str} |"
        )
    lines += ["", "---", ""]

    lines += [
        "## 4. Near-Constant Summary",
        "",
        "Features with std < 1e-8 or nonzero_pct < 1%.",
        "",
        "| Family | Column | Reason |",
        "|--------|--------|--------|",
    ]
    for stat in tushare_stats + research_stats:
        if not stat.get("in_cache") or not stat.get("near_constant"):
            continue
        reason_parts = []
        if stat.get("std", 1) < 1e-8:
            reason_parts.append(f"std={stat['std']:.2e}")
        if stat.get("nonzero_pct", 1) < 0.01:
            reason_parts.append(f"nonzero={stat['nonzero_pct']:.2%}")
        family = "tushare" if stat["column"].startswith("tushare_") else "research_daily"
        lines.append(f"| {family} | `{stat['column']}` | {', '.join(reason_parts)} |")
    lines += ["", "---", ""]

    lines += [
        "## 5. High NaN (>30%) Summary",
        "",
        "| Family | Column | NaN% |",
        "|--------|--------|------|",
    ]
    for stat in tushare_stats + research_stats:
        if not stat.get("in_cache") or not stat.get("flag_nan_high"):
            continue
        family = "tushare" if stat["column"].startswith("tushare_") else "research_daily"
        lines.append(f"| {family} | `{stat['column']}` | {stat['nan_pct']:.2%} |")
    no_high_nan = not any(
        s.get("in_cache") and s.get("flag_nan_high")
        for s in tushare_stats + research_stats
    )
    if no_high_nan:
        lines.append("| — | (none) | — |")
    lines += ["", "---", ""]

    lines += [
        "## 6. High Correlation with Selected 260 (|r| >= 0.90)",
        "",
        "| Target Column | Correlated With | r |",
        "|---------------|----------------|---|",
    ]
    all_corr = {**tushare_corr, **research_corr}
    if not all_corr:
        lines.append("| (none) | — | — |")
    else:
        for target_col, pairs in sorted(all_corr.items()):
            for ref_col, r_val in pairs:
                lines.append(f"| `{target_col}` | `{ref_col}` | {r_val:.4f} |")
    lines += ["", "---", ""]

    tushare_in = sum(1 for s in tushare_stats if s.get("in_cache"))
    tushare_nc = sum(1 for s in tushare_stats if s.get("near_constant"))
    research_in = sum(1 for s in research_stats if s.get("in_cache"))
    research_nc = sum(1 for s in research_stats if s.get("near_constant"))
    tushare_corr_count = len(tushare_corr)
    research_corr_count = len(research_corr)

    lines += [
        "## 7. Summary & Recommendations",
        "",
        "### Tushare Daily Factors",
        "",
        f"- **{tushare_in}** base columns present in research feature cache (out of {len([c for cols in TUSHARE_SUB_SOURCES.values() for c in cols])} target)",
        f"- **{tushare_nc}** flagged as near-constant",
        f"- **{tushare_corr_count}** have |r| >= 0.90 correlation with selected 260",
        f"- Raw cache covers {sum(1 for r in tushare_raw_audit if r.get('exists'))} API endpoints",
        "",
        "### Research Daily Factors",
        "",
        f"- **{research_in}** base columns present in research feature cache (out of {len(RESEARCH_DAILY_COLUMNS)} target)",
        f"- **{research_nc}** flagged as near-constant",
        f"- **{research_corr_count}** have |r| >= 0.90 correlation with selected 260",
        "- These are market-level daily factors — same value for all stocks on a given date",
        "",
        "### Ablation Priority",
        "",
        "Per `unused_factor_family_audit_20260503.md` recommendations:",
        "",
        "1. **Research Daily (Tier 1)**: 47 base columns, 100% coverage, zero external dependency.",
        "   Several members showed signal in prior research runs. Recommend as first ablation target.",
        "",
        "2. **Tushare Tier 1** (high coverage): `daily_basic`(2), `stk_limit`(3), `stk_auction`(4), `moneyflow`(5) = 14 base columns.",
        "   All have 804 daily cache files (2023-01-03 ~ 2026-04-30).",
        "",
        "3. **Tushare Tier 2** (medium coverage): `cyq_perf`(3), `margin_detail`(5), `stk_holdernumber`(2) = 10 base columns.",
        "",
        "4. **Tushare Tier 3** (sparse): `limit_list_d`(6), `top_list_inst`(5), `hk_hold`(2), `ths_hot`(2) = 15 base columns.",
        "   `hk_hold` starts later and has fewer dates; `ths_hot` starts 2023-08-21.",
        "",
        "5. **NOT recommended**: `stk_mins_5` (18% stock coverage, excluded from this audit).",
        "",
        "### Discipline",
        "",
        "- This is a **seen_research diagnostic only** — no forward or passed implications.",
        "- Frozen config `gpu_probe_20260501T155956Z_d64e3464` remains unchanged.",
        "- Any ablation runs must follow forward_runbook.md protocol.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    print("Loading selected 260 from frozen artifact...")
    selected_260 = load_selected_260()
    print(f"  selected_260 count: {len(selected_260)}")

    print("Loading research feature cache metadata...")
    meta_path = FEATURE_CACHE_DIR / "gpu_probe_features_27f3f4cc8c1b747f.json"
    with open(meta_path, encoding="utf-8") as f:
        cache_meta = json.load(f)

    all_tushare_base = [c for cols in TUSHARE_SUB_SOURCES.values() for c in cols]
    target_cols = list(set(all_tushare_base + RESEARCH_DAILY_COLUMNS + selected_260))
    target_cols_in_cache = [c for c in target_cols if c in cache_meta["columns"]]

    print(f"Loading feature cache parquet ({len(target_cols_in_cache)} columns)...")
    df = pd.read_parquet(RESEARCH_FEATURE_CACHE, columns=target_cols_in_cache)
    print(f"  loaded: {df.shape[0]} rows x {df.shape[1]} columns")

    print("Computing Tushare column stats...")
    tushare_stats = compute_column_stats(df, all_tushare_base)

    print("Computing Research Daily column stats...")
    research_stats = compute_column_stats(df, RESEARCH_DAILY_COLUMNS)

    print("Auditing Tushare raw cache...")
    tushare_raw_audit = audit_tushare_raw_cache()

    print("Computing correlations (Tushare vs selected 260)...")
    tushare_corr = compute_top_correlations(df, all_tushare_base, selected_260, threshold=0.90)

    print("Computing correlations (Research Daily vs selected 260)...")
    research_corr = compute_top_correlations(df, RESEARCH_DAILY_COLUMNS, selected_260, threshold=0.90)

    print("Generating report...")
    report = generate_report(
        tushare_stats, research_stats, tushare_raw_audit,
        tushare_corr, research_corr, selected_260, cache_meta,
    )

    output_path = REPO_ROOT / "docs" / "factor_quality_diagnostic_20260503.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
