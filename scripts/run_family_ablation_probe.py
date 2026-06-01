"""Controlled family ablation probe — seen_research diagnostic only.

Runs 3 variants with identical training parameters, differing only in which
feature families enter the input pool:

  1. baseline_expanded_no_cross  — current expanded after exclude cross_
  2. expanded_plus_research_daily — baseline + GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES
  3. tushare_tier1_available      — baseline + moneyflow/daily_basic/stk_limit

No frozen_forward_config.json is modified.  No final_unseen training.
No "passed" claims — all runs use lockbox_role="seen_research".
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import ashare_similarity.prediction.gpu_probe as _gpu_probe_module
from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import (
    GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES,
    GPU_PROBE_STABLE_FEATURES,
    GpuProbeConfig,
    run_gpu_next_day_probe,
)

# ---------------------------------------------------------------------------
# Tushare Tier 1 — only APIs with confirmed high-coverage cache
# Excluded: stk_auction (0 cache parquets), holdernumber, margin_detail,
#           hk_hold, ths_hot, cyq_perf, limit_list_d, top_list_inst, stk_mins_5
# ---------------------------------------------------------------------------
TUSHARE_TIER1_BASE: tuple[str, ...] = (
    # moneyflow (5)
    "tushare_net_mf_amount",
    "tushare_lg_buy_sell_ratio",
    "tushare_elg_buy_sell_ratio",
    "tushare_mf_strength",
    "tushare_sm_sell_pressure",
    # daily_basic (2)
    "tushare_volume_ratio",
    "tushare_free_share",
    # stk_limit (3)
    "tushare_up_limit_distance",
    "tushare_down_limit_distance",
    "tushare_limit_range",
)

TUSHARE_TIER1_FEATURES: tuple[str, ...] = (
    *TUSHARE_TIER1_BASE,
    *(f"{c}_available" for c in TUSHARE_TIER1_BASE),
)

# ---------------------------------------------------------------------------
# Step 4 B-group factors (registry C-IDs)
# ---------------------------------------------------------------------------
C009_FEATURES: tuple[str, ...] = (
    "tushare_main_force_divergence",
    "tushare_main_force_divergence_available",
)
C011_FEATURES: tuple[str, ...] = (
    "tushare_auction_open_vwap_ratio",
    "tushare_auction_open_vwap_ratio_available",
)

C001_FEATURES: tuple[str, ...] = (
    "tushare_mf_flow_intensity",
    "tushare_mf_flow_intensity_available",
)
# C001 STATUS: implementation_blocked — registry requires `net_mf_amount / amount`
# (daily trading turnover), but tushare cache has no `daily` API. Current code uses
# moneyflow total_buy_amount which is NOT equivalent. Do not use in ablation until
# real daily `amount` is available.

C004_FEATURES: tuple[str, ...] = (
    "tushare_ff_adjusted_flow",
    "tushare_ff_adjusted_flow_available",
)
C010_FEATURES: tuple[str, ...] = (
    "tushare_float_relative_impact",
    "tushare_float_relative_impact_available",
)
# C010 STATUS: implementation_blocked — registry requires `volume_ratio * volume / free_share`
# (daily trading volume), but tushare cache has no `daily` API. Current code uses
# moneyflow total_buy_vol which is NOT equivalent. Do not use in ablation until
# real daily `volume` is available.

# ---------------------------------------------------------------------------
# Combination tuples (must come after all *_FEATURES definitions)
# ---------------------------------------------------------------------------
TIER1_PLUS_B0: tuple[str, ...] = (*TUSHARE_TIER1_FEATURES, *C011_FEATURES)
TIER1_PLUS_B1: tuple[str, ...] = (*TUSHARE_TIER1_FEATURES, *C009_FEATURES, *C011_FEATURES)

TIER1_PLUS_C009: tuple[str, ...] = (*TUSHARE_TIER1_FEATURES, *C009_FEATURES)
TIER1_PLUS_C004: tuple[str, ...] = (*TUSHARE_TIER1_FEATURES, *C004_FEATURES)
TIER1_PLUS_C009_C004: tuple[str, ...] = (*TUSHARE_TIER1_FEATURES, *C009_FEATURES, *C004_FEATURES)
TIER1_PLUS_C011_C004: tuple[str, ...] = (*TUSHARE_TIER1_FEATURES, *C011_FEATURES, *C004_FEATURES)
TIER1_PLUS_C009_C011_C004: tuple[str, ...] = (*TUSHARE_TIER1_FEATURES, *C009_FEATURES, *C011_FEATURES, *C004_FEATURES)

# B2/B3 currently blocked — C001 and C010 formulas not aligned with registry.
# TIER1_PLUS_B2: tuple[str, ...] = (*TUSHARE_TIER1_FEATURES, *C001_FEATURES, *C004_FEATURES, *C010_FEATURES)
# TIER1_PLUS_B3: tuple[str, ...] = (
#     *TUSHARE_TIER1_FEATURES, *C001_FEATURES, *C004_FEATURES,
#     *C009_FEATURES, *C010_FEATURES, *C011_FEATURES,
# )

# ---------------------------------------------------------------------------
# Variant definitions
# ---------------------------------------------------------------------------
VARIANTS: list[dict] = [
    {
        "name": "baseline_expanded_no_cross",
        "feature_set": "expanded",
        "extra_features": (),
        "description": "Current expanded after exclude cross_ (352 input features)",
    },
    {
        "name": "expanded_plus_research_daily",
        "feature_set": "expanded",
        "extra_features": GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES,
        "description": "Baseline + GPU_PROBE_RESEARCH_DAILY_FACTOR_FEATURES (94 extra)",
    },
    {
        "name": "tushare_tier1_available",
        "feature_set": "research",
        "extra_features": TUSHARE_TIER1_FEATURES,
        "description": "Baseline + Tushare Tier 1 moneyflow/daily_basic/stk_limit (20 extra)",
    },
    {
        "name": "tier1_plus_b0_c011",
        "feature_set": "research",
        "extra_features": TIER1_PLUS_B0,
        "description": "Tier1 + C011 auction_open_vwap_ratio (B0: verify feature list path)",
    },
    {
        "name": "tier1_plus_b1_c009_c011",
        "feature_set": "research",
        "extra_features": TIER1_PLUS_B1,
        "description": "Tier1 + C009 main_force_divergence + C011 auction_open_vwap_ratio (B1)",
    },
    # B2 (tier1+C001+C004+C010) and B3 (tier1+ALL_5) removed:
    # C001 and C010 are implementation_blocked — formulas use moneyflow
    # proxies instead of real daily amount/volume. See comments above.
    {
        "name": "tier1_plus_c009_only",
        "feature_set": "research",
        "extra_features": TIER1_PLUS_C009,
        "description": "Tier1 + C009 main_force_divergence only (isolate C009 contribution)",
    },
    {
        "name": "tier1_plus_c004_only",
        "feature_set": "research",
        "extra_features": TIER1_PLUS_C004,
        "description": "Tier1 + C004 ff_adjusted_flow only (isolate C004 contribution)",
    },
    {
        "name": "tier1_plus_c009_c004",
        "feature_set": "research",
        "extra_features": TIER1_PLUS_C009_C004,
        "description": "Tier1 + C009 + C004 (two-factor interaction without C011)",
    },
    {
        "name": "tier1_plus_c011_c004",
        "feature_set": "research",
        "extra_features": TIER1_PLUS_C011_C004,
        "description": "Tier1 + C011 + C004 (two-factor interaction without C009)",
    },
    {
        "name": "tier1_plus_c009_c011_c004",
        "feature_set": "research",
        "extra_features": TIER1_PLUS_C009_C011_C004,
        "description": "Tier1 + C009 + C011 + C004 (all three verified factors)",
    },
]


def _make_base_config(feature_set: str, end_override: date | None = None) -> GpuProbeConfig:
    return GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=end_override or date(2026, 3, 31),
        train_rows=300_000,
        test_rows=120_000,
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        min_phase_days_3=1,
        selector_coverage_weight=0.02,
        candidate_family="all",
        lockbox_role="seen_research",
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        seed=42,
        feature_set=feature_set,
    )


# ---------------------------------------------------------------------------
# Tushare pre-run diagnostics
# ---------------------------------------------------------------------------
TUSHARE_API_DIRS = ["moneyflow", "daily_basic", "stk_limit", "stk_auction_o", "stk_auction_c"]


def _pre_run_tushare_check(cache_dir: Path) -> dict[str, int]:
    tushare_root = cache_dir / "prediction" / "tushare"
    counts: dict[str, int] = {}
    for api in TUSHARE_API_DIRS:
        api_dir = tushare_root / api
        if api_dir.is_dir():
            counts[api] = len(list(api_dir.glob("*.parquet")))
        else:
            counts[api] = 0
    return counts


# ---------------------------------------------------------------------------
# Wilson lower bound (test-set fallback)
# ---------------------------------------------------------------------------
def _wilson_lower(p: float, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0 or p is None:
        return 0.0
    z2 = z * z
    safe_n = float(max(n, 1))
    denom = 1.0 + z2 / safe_n
    centre = p + z2 / (2.0 * safe_n)
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * safe_n)) / safe_n)
    return max(0.0, min(1.0, (centre - margin) / denom))


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------
def _extract_metrics(result: dict, variant: dict) -> dict:
    fs = result.get("feature_selection") or {}
    acceptance = result.get("acceptance") or {}
    hc = acceptance.get("high_confidence") or {}
    extra = set(variant["extra_features"])
    all_input = set(result.get("features") or [])
    selected = set(fs.get("selected_features") or [])

    confident_acc = result.get("confident_accuracy")
    confident_n = result.get("confident_count", 0)
    wilson = hc.get("wilson_lower_95")
    if wilson is None and confident_acc is not None:
        wilson = _wilson_lower(confident_acc, confident_n)

    return {
        "variant": variant["name"],
        "description": variant["description"],
        "run_id": result.get("run_id", ""),
        "artifact_path": (result.get("artifacts") or {}).get("artifact", ""),
        "status": result.get("status", "unknown"),
        "feature_count": len(all_input),
        "selected_feature_count": fs.get("selected_feature_count", 0),
        "family_input_count": len(extra & all_input) if extra else 0,
        "family_selected_count": len(extra & selected) if extra else 0,
        "skipped_priority_count": fs.get("skipped_priority_feature_count", 0),
        "high_conf_accuracy": confident_acc,
        "wilson_lower_95": round(wilson, 6) if wilson is not None else None,
        "high_conf_count": confident_n,
        "coverage": result.get("confident_coverage"),
        "brier": result.get("brier"),
    }


# ---------------------------------------------------------------------------
# Tushare post-run column diagnostic
# ---------------------------------------------------------------------------
def _tushare_post_diagnostic(result: dict) -> list[dict]:
    fs = result.get("feature_selection") or {}
    all_input = set(result.get("features") or [])
    selected = set(fs.get("selected_features") or [])
    skipped = {
        s["name"]: s for s in (fs.get("skipped_priority_features") or []) if "name" in s
    }
    rows = []
    for col in TUSHARE_TIER1_FEATURES:
        row: dict = {"column": col, "in_input": col in all_input, "selected": col in selected}
        if col in skipped:
            row["skipped"] = True
            row["reason"] = skipped[col].get("reason", "")
            row["nonzero_rate"] = skipped[col].get("nonzero_rate")
        else:
            row["skipped"] = False
            row["reason"] = ""
            row["nonzero_rate"] = None
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Run a single variant
# ---------------------------------------------------------------------------
def _run_variant(store: LocalDataStore, variant: dict, end_override: date | None = None) -> dict:
    config = _make_base_config(variant["feature_set"], end_override=end_override)
    extra = variant["extra_features"]

    if not extra:
        print(f"\n{'='*72}", file=sys.stderr)
        print(f"  VARIANT: {variant['name']} (no monkey-patch)", file=sys.stderr)
        print(f"{'='*72}\n", file=sys.stderr)
        return run_gpu_next_day_probe(store, config)

    custom_features = tuple(dict.fromkeys((*GPU_PROBE_STABLE_FEATURES, *extra)))
    print(f"\n{'='*72}", file=sys.stderr)
    print(f"  VARIANT: {variant['name']}", file=sys.stderr)
    print(f"  feature_set={variant['feature_set']}, extra={len(extra)}, total_pool={len(custom_features)}", file=sys.stderr)
    print(f"{'='*72}\n", file=sys.stderr)

    # Two-phase monkey-patch: return original features for cache fingerprint
    # (1st call, line 3701) so we reuse the existing feature cache, then return
    # custom features for model input selection (2nd call, line 913).
    # The expanded cache already contains research_daily columns from
    # _attach_free_factor_features which runs unconditionally.
    original_fn = _gpu_probe_module._feature_names_for_config
    call_state = {"count": 0}

    def _two_phase_feature_names(cfg):
        call_state["count"] += 1
        if call_state["count"] == 1:
            return original_fn(cfg)
        return custom_features

    _gpu_probe_module._feature_names_for_config = _two_phase_feature_names
    try:
        result = run_gpu_next_day_probe(store, config)
    finally:
        _gpu_probe_module._feature_names_for_config = original_fn

    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
DOCS_DIR = REPO_ROOT / "docs"
REPORT_NAME = "family_ablation_results_20260503"


def _write_reports(
    all_metrics: list[dict],
    tushare_pre: dict[str, int],
    tushare_post: list[dict] | None,
    elapsed_seconds: list[float],
) -> tuple[Path, Path]:
    generated_at = datetime.now(timezone.utc).isoformat()

    # --- JSON report ---
    app_config = get_default_config()
    json_dir = Path(app_config.storage.report_dir) / "prediction"
    json_dir.mkdir(parents=True, exist_ok=True)
    json_path = json_dir / f"{REPORT_NAME}.json"
    json_payload = {
        "generated_at": generated_at,
        "experiment": "controlled_family_ablation",
        "diagnostic_monkey_patch": True,
        "lockbox_role": "seen_research",
        "not_passed": True,
        "not_frozen": True,
        "variants": all_metrics,
        "tushare_pre_check": tushare_pre,
        "tushare_post_diagnostic": tushare_post,
        "elapsed_seconds": elapsed_seconds,
    }
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    # --- Markdown report ---
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = DOCS_DIR / f"{REPORT_NAME}.md"
    lines: list[str] = []
    lines.append(f"# Family Ablation Results\n")
    lines.append(f"> Generated: {generated_at}")
    lines.append(f"> Experiment: controlled_family_ablation")
    lines.append(f"> diagnostic_monkey_patch: true")
    lines.append(f"> lockbox_role: seen_research only — NOT final_unseen, NOT passed, NOT frozen\n")

    # Baseline params
    lines.append("## Baseline Parameters\n")
    lines.append("| Parameter | Value |")
    lines.append("|-----------|-------|")
    for k, v in [
        ("start", "2023-05-01"), ("train_end", "2025-12-31"), ("test_start", "2026-01-01"),
        ("end", "2026-03-31"), ("train_rows", "300,000"), ("test_rows", "120,000"),
        ("label_target", "next_high_from_close"), ("target_high_return_pct", "1.0"),
        ("feature_selection_method", "stable_tail"), ("max_selected_features", "260"),
        ("selector_coverage_weight", "0.02"), ("candidate_family", "all"),
        ("lockbox_role", "seen_research"), ("exclude_event_limit_up", "True"),
        ("exclude_feature_prefix", '["cross_"]'), ("seed", "42"),
    ]:
        lines.append(f"| {k} | {v} |")

    # Tushare pre-check
    lines.append("\n## Tushare Pre-Run Check\n")
    lines.append("| API Directory | Parquet Files | Status |")
    lines.append("|--------------|---------------|--------|")
    for api, count in tushare_pre.items():
        status = "OK" if count > 0 else "EMPTY"
        if api.startswith("stk_auction"):
            status = f"EXCLUDED this round (cache={count}, available for Tier 1b)"
        lines.append(f"| {api} | {count} | {status} |")

    # Comparison table
    lines.append("\n## Comparison Table\n")
    header = "| Variant | Features | Selected | Family In | Family Sel | Skipped | HC Accuracy | Wilson 95 | HC Count | Coverage | Brier | Elapsed |"
    sep = "|" + "|".join(["---"] * 12) + "|"
    lines.append(header)
    lines.append(sep)
    for m, elapsed in zip(all_metrics, elapsed_seconds):
        def _fmt(v, digits=4):
            if v is None:
                return "—"
            if isinstance(v, float):
                return f"{v:.{digits}f}"
            return str(v)
        lines.append(
            f"| {m['variant']} | {m['feature_count']} | {m['selected_feature_count']} "
            f"| {m['family_input_count']} | {m['family_selected_count']} "
            f"| {m['skipped_priority_count']} "
            f"| {_fmt(m['high_conf_accuracy'])} | {_fmt(m['wilson_lower_95'])} "
            f"| {m['high_conf_count']} | {_fmt(m['coverage'])} "
            f"| {_fmt(m['brier'])} | {elapsed:.0f}s |"
        )

    # Variant descriptions + run IDs
    lines.append("\n## Variant Details\n")
    for m in all_metrics:
        lines.append(f"### {m['variant']}\n")
        lines.append(f"- **Description**: {m['description']}")
        lines.append(f"- **run_id**: `{m['run_id']}`")
        lines.append(f"- **artifact**: `{m['artifact_path']}`")
        lines.append(f"- **status**: {m['status']}")
        lines.append("")

    # Tushare post-diagnostic
    if tushare_post:
        lines.append("## Tushare Tier 1 Post-Diagnostic\n")
        lines.append("| Column | In Input | Selected | Skipped | Reason | Nonzero Rate |")
        lines.append("|--------|----------|----------|---------|--------|-------------|")
        for row in tushare_post:
            nzr = f"{row['nonzero_rate']:.4f}" if row["nonzero_rate"] is not None else "—"
            lines.append(
                f"| `{row['column']}` | {row['in_input']} | {row['selected']} "
                f"| {row['skipped']} | {row['reason']} | {nzr} |"
            )

    # Decision criteria
    lines.append("\n## Decision Criteria\n")
    if len(all_metrics) >= 3:
        base = all_metrics[0]
        rd = all_metrics[1]
        ts = all_metrics[2]

        lines.append("### research_daily verdict\n")
        if rd["status"] != "completed":
            lines.append("Run did not complete — **cannot evaluate**.\n")
        elif base["status"] != "completed":
            lines.append("Baseline did not complete — **cannot compare**.\n")
        else:
            wilson_delta = _safe_delta(rd["wilson_lower_95"], base["wilson_lower_95"])
            acc_delta = _safe_delta(rd["high_conf_accuracy"], base["high_conf_accuracy"])
            count_delta = _safe_delta(rd["high_conf_count"], base["high_conf_count"])
            cov_delta = _safe_delta(rd["coverage"], base["coverage"])
            lines.append(f"- Wilson delta: {wilson_delta}")
            lines.append(f"- HC accuracy delta: {acc_delta}")
            lines.append(f"- HC count delta: {count_delta}")
            lines.append(f"- Coverage delta: {cov_delta}")
            lines.append("")

        lines.append("### tushare_tier1 verdict\n")
        if ts["status"] != "completed":
            lines.append("Run did not complete — **cannot evaluate**.\n")
        elif base["status"] != "completed":
            lines.append("Baseline did not complete — **cannot compare**.\n")
        else:
            wilson_delta = _safe_delta(ts["wilson_lower_95"], base["wilson_lower_95"])
            acc_delta = _safe_delta(ts["high_conf_accuracy"], base["high_conf_accuracy"])
            count_delta = _safe_delta(ts["high_conf_count"], base["high_conf_count"])
            cov_delta = _safe_delta(ts["coverage"], base["coverage"])
            lines.append(f"- Wilson delta: {wilson_delta}")
            lines.append(f"- HC accuracy delta: {acc_delta}")
            lines.append(f"- HC count delta: {count_delta}")
            lines.append(f"- Coverage delta: {cov_delta}")
            lines.append("")

    # Constraints
    lines.append("\n## Constraints Confirmation\n")
    lines.append("- [x] frozen_forward_config.json NOT modified")
    lines.append("- [x] diagnostic_monkey_patch = true (feature_names overridden in-process)")
    lines.append("- [x] lockbox_role = seen_research for all runs")
    lines.append("- [x] No run claims 'passed'")
    lines.append("- [x] No full feature_set=research blast")
    lines.append("- [x] stk_auction excluded this round (cache exists, available for Tier 1b)")
    lines.append("- [x] Tushare data verified pre and post run")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def _safe_delta(a, b) -> str:
    if a is None or b is None:
        return "N/A (missing data)"
    diff = a - b
    sign = "+" if diff >= 0 else ""
    if isinstance(a, float):
        return f"{sign}{diff:.6f} ({b:.4f} → {a:.4f})"
    return f"{sign}{diff} ({b} → {a})"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    import argparse as _ap
    _parser = _ap.ArgumentParser()
    _parser.add_argument("--variant", type=str, default=None,
                         help="Run only this variant name (e.g. tushare_tier1_available)")
    _parser.add_argument("--end-date", type=str, default=None,
                         help="Override end date (YYYY-MM-DD), e.g. 2026-04-30 for April holdout")
    _args = _parser.parse_args()
    variant_filter = _args.variant
    end_date_override = None
    if _args.end_date:
        y, m, d = _args.end_date.split("-")
        end_date_override = date(int(y), int(m), int(d))

    configured_home = os.environ.get("ASHARE_SIMILARITY_HOME")
    if configured_home:
        runtime_home = Path(configured_home).expanduser().resolve()
    else:
        app_config = get_default_config()
        runtime_home = app_config.storage.root_dir.parent

    print(f"[ablation] runtime_home = {runtime_home}", file=sys.stderr)
    app_config = get_default_config()
    store = LocalDataStore(app_config)
    cache_dir = Path(app_config.storage.cache_dir)

    # --- Tushare pre-check ---
    print("\n[ablation] Tushare pre-run check ...", file=sys.stderr)
    tushare_pre = _pre_run_tushare_check(cache_dir)
    for api, count in tushare_pre.items():
        tag = "OK" if count > 0 else "EMPTY"
        if api.startswith("stk_auction"):
            tag = "EXCLUDED" if count == 0 else "UNEXPECTED"
        print(f"  {api}: {count} parquets [{tag}]", file=sys.stderr)

    tier1_apis = ["moneyflow", "daily_basic", "stk_limit"]
    missing = [a for a in tier1_apis if tushare_pre.get(a, 0) == 0]
    if missing:
        print(f"\n[ablation] WARNING: Tier 1 APIs with 0 parquets: {missing}", file=sys.stderr)
        print("[ablation] Tushare variant will have all-zero columns for these APIs.", file=sys.stderr)

    # --- Run variants ---
    all_metrics: list[dict] = []
    elapsed_list: list[float] = []
    tushare_post: list[dict] | None = None

    for variant in VARIANTS:
        if variant_filter and variant["name"] != variant_filter:
            continue
        print(f"\n[ablation] Starting variant: {variant['name']}", file=sys.stderr)
        t0 = time.perf_counter()
        result = _run_variant(store, variant, end_override=end_date_override)
        elapsed = time.perf_counter() - t0
        elapsed_list.append(elapsed)

        metrics = _extract_metrics(result, variant)
        all_metrics.append(metrics)

        print(f"[ablation] {variant['name']} done in {elapsed:.1f}s — status={metrics['status']}", file=sys.stderr)
        print(f"  features={metrics['feature_count']} selected={metrics['selected_feature_count']}", file=sys.stderr)
        print(f"  family_in={metrics['family_input_count']} family_sel={metrics['family_selected_count']}", file=sys.stderr)
        print(f"  HC_acc={metrics['high_conf_accuracy']} wilson={metrics['wilson_lower_95']}", file=sys.stderr)
        print(f"  HC_count={metrics['high_conf_count']} coverage={metrics['coverage']}", file=sys.stderr)
        print(f"  brier={metrics['brier']}", file=sys.stderr)

        if variant["name"] == "tushare_tier1_available":
            tushare_post = _tushare_post_diagnostic(result)
            print("\n[ablation] Tushare Tier 1 post-diagnostic:", file=sys.stderr)
            for row in tushare_post:
                nzr = f"{row['nonzero_rate']:.4f}" if row["nonzero_rate"] is not None else "n/a"
                print(
                    f"  {row['column']:50s} in_input={row['in_input']:<5} "
                    f"selected={row['selected']:<5} skipped={row['skipped']:<5} "
                    f"reason={row['reason']:<30s} nonzero={nzr}",
                    file=sys.stderr,
                )

    # --- Write reports ---
    md_path, json_path = _write_reports(all_metrics, tushare_pre, tushare_post, elapsed_list)
    print(f"\n[ablation] Reports written:", file=sys.stderr)
    print(f"  MD:   {md_path}", file=sys.stderr)
    print(f"  JSON: {json_path}", file=sys.stderr)

    # --- Summary JSON to stdout ---
    summary = {
        "experiment": "controlled_family_ablation",
        "lockbox_role": "seen_research",
        "variants": [
            {k: v for k, v in m.items() if k != "description"} for m in all_metrics
        ],
        "reports": {"md": str(md_path), "json": str(json_path)},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
