"""Tushare Tier 1 Complete 14 — single-variant seen_research diagnostic.

Adds stk_auction (4 base) to the previous Tier 1 (10 base) for a total
of 14 base + 14 _available = 28 extra features on top of GPU_PROBE_STABLE_FEATURES.

Compares against:
  - baseline_expanded_no_cross  (gpu_probe_20260503T113328Z_1b272829)
  - tushare_tier1_available     (gpu_probe_20260503T115829Z_d3222871, 10 base)

No frozen_forward_config.json is modified.  No final_unseen training.
No "passed" claims — lockbox_role="seen_research".
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
    GPU_PROBE_STABLE_FEATURES,
    GpuProbeConfig,
    run_gpu_next_day_probe,
)

TUSHARE_COMPLETE14_BASE: tuple[str, ...] = (
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
    # stk_auction (4) — NEW vs partial tier1
    "tushare_auction_open_vwap_ratio",
    "tushare_auction_open_vol",
    "tushare_auction_close_vwap_ratio",
    "tushare_auction_close_vol",
)

TUSHARE_COMPLETE14_FEATURES: tuple[str, ...] = (
    *TUSHARE_COMPLETE14_BASE,
    *(f"{c}_available" for c in TUSHARE_COMPLETE14_BASE),
)

PRIOR_RESULTS_JSON = Path(
    "E:/ashare_similarity_runtime/data/reports/prediction"
    "/family_ablation_results_20260503.json"
)

TUSHARE_API_DIRS = [
    "moneyflow", "daily_basic", "stk_limit", "stk_auction_o", "stk_auction_c",
]


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


def _wilson_lower(p: float, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0 or p is None:
        return 0.0
    z2 = z * z
    safe_n = float(max(n, 1))
    denom = 1.0 + z2 / safe_n
    centre = p + z2 / (2.0 * safe_n)
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * safe_n)) / safe_n)
    return max(0.0, min(1.0, (centre - margin) / denom))


def _extract_metrics(result: dict) -> dict:
    fs = result.get("feature_selection") or {}
    acceptance = result.get("acceptance") or {}
    hc = acceptance.get("high_confidence") or {}
    extra = set(TUSHARE_COMPLETE14_FEATURES)
    all_input = set(result.get("features") or [])
    selected = set(fs.get("selected_features") or [])

    confident_acc = result.get("confident_accuracy")
    confident_n = result.get("confident_count", 0)
    wilson = hc.get("wilson_lower_95")
    if wilson is None and confident_acc is not None:
        wilson = _wilson_lower(confident_acc, confident_n)

    return {
        "run_id": result.get("run_id", ""),
        "artifact_path": (result.get("artifacts") or {}).get("artifact", ""),
        "status": result.get("status", "unknown"),
        "feature_count": len(all_input),
        "selected_feature_count": fs.get("selected_feature_count", 0),
        "family_input_count": len(extra & all_input),
        "family_selected_count": len(extra & selected),
        "high_conf_accuracy": confident_acc,
        "wilson_lower_95": round(wilson, 6) if wilson is not None else None,
        "high_conf_count": confident_n,
        "coverage": result.get("confident_coverage"),
        "high_conf_brier": result.get("confident_brier"),
        "brier": result.get("brier"),
        "baseline_brier": result.get("baseline_brier"),
    }


def _column_diagnostic(result: dict) -> list[dict]:
    fs = result.get("feature_selection") or {}
    all_input = set(result.get("features") or [])
    selected = set(fs.get("selected_features") or [])
    skipped_map = {
        s["name"]: s for s in (fs.get("skipped_priority_features") or []) if "name" in s
    }
    rows = []
    for col in TUSHARE_COMPLETE14_FEATURES:
        row: dict = {"column": col, "in_input": col in all_input, "selected": col in selected}
        if col in skipped_map:
            row["skipped"] = True
            row["reason"] = skipped_map[col].get("reason", "")
        else:
            row["skipped"] = False
            row["reason"] = ""
        row["is_auction"] = col.replace("_available", "").startswith("tushare_auction_")
        rows.append(row)
    return rows


def _safe_delta(a, b, fmt: str = "f") -> str:
    if a is None or b is None:
        return "N/A"
    diff = a - b
    sign = "+" if diff >= 0 else ""
    if fmt == "f":
        return f"{sign}{diff:.6f} ({b:.4f} -> {a:.4f})"
    return f"{sign}{diff} ({b} -> {a})"


def _write_reports(
    metrics: dict,
    tushare_pre: dict[str, int],
    col_diag: list[dict],
    prior: dict,
    elapsed: float,
) -> tuple[Path, Path]:
    generated_at = datetime.now(timezone.utc).isoformat()
    baseline = prior["variants"][0]
    partial10 = prior["variants"][2]

    # --- JSON ---
    app_config = get_default_config()
    json_dir = Path(app_config.storage.report_dir) / "prediction"
    json_dir.mkdir(parents=True, exist_ok=True)
    json_path = json_dir / "tushare_tier1_complete14_results_20260503.json"
    json_payload = {
        "generated_at": generated_at,
        "experiment": "tushare_tier1_complete14",
        "diagnostic_monkey_patch": True,
        "lockbox_role": "seen_research",
        "not_passed": True,
        "not_frozen": True,
        "complete14": metrics,
        "baseline_reference": {
            "run_id": baseline["run_id"],
            "high_conf_accuracy": baseline["high_conf_accuracy"],
            "wilson_lower_95": baseline["wilson_lower_95"],
            "high_conf_count": baseline["high_conf_count"],
            "coverage": baseline["coverage"],
            "brier": baseline["brier"],
        },
        "partial10_reference": {
            "run_id": partial10["run_id"],
            "high_conf_accuracy": partial10["high_conf_accuracy"],
            "wilson_lower_95": partial10["wilson_lower_95"],
            "high_conf_count": partial10["high_conf_count"],
            "coverage": partial10["coverage"],
            "brier": partial10["brier"],
        },
        "tushare_pre_check": tushare_pre,
        "column_diagnostic": col_diag,
        "elapsed_seconds": elapsed,
    }
    json_path.write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # --- Markdown ---
    docs_dir = REPO_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    md_path = docs_dir / "tushare_tier1_complete14_results_20260503.md"

    lines: list[str] = []
    lines.append("# Tushare Tier 1 Complete 14 Results\n")
    lines.append(f"> Generated: {generated_at}")
    lines.append("> Experiment: tushare_tier1_complete14")
    lines.append("> diagnostic_monkey_patch: true")
    lines.append("> lockbox_role: seen_research only — NOT final_unseen, NOT passed, NOT frozen\n")

    lines.append("## Parameters\n")
    lines.append("| Parameter | Value |")
    lines.append("|-----------|-------|")
    for k, v in [
        ("start", "2023-05-01"), ("train_end", "2025-06-30"),
        ("test_start", "2025-07-01"), ("end", "2026-04-30"),
        ("train_rows", "300,000"), ("test_rows", "120,000"),
        ("label_target", "next_high_from_close"), ("target_high_return_pct", "1.0"),
        ("feature_selection_method", "stable_tail"), ("max_selected_features", "260"),
        ("selector_coverage_weight", "0.02"), ("candidate_family", "all"),
        ("lockbox_role", "seen_research"), ("exclude_event_limit_up", "True"),
        ("exclude_feature_prefix", '["cross_"]'), ("seed", "42"),
        ("feature_set (for cache)", "research"),
        ("model_input_pool", "GPU_PROBE_STABLE_FEATURES + 28 tushare complete14"),
        ("extra_base_columns", "14 (moneyflow 5 + daily_basic 2 + stk_limit 3 + stk_auction 4)"),
        ("extra_total_columns", "28 (14 base + 14 _available)"),
    ]:
        lines.append(f"| {k} | {v} |")

    lines.append("\n## Tushare Pre-Run Check\n")
    lines.append("| API Directory | Parquet Files | Status |")
    lines.append("|--------------|---------------|--------|")
    for api, count in tushare_pre.items():
        status = "OK" if count > 0 else "EMPTY"
        lines.append(f"| {api} | {count} | {status} |")

    lines.append("\n## Comparison Table\n")
    lines.append("| | baseline | partial_tier1_10 | **complete_tier1_14** |")
    lines.append("|---|---|---|---|")
    lines.append(f"| **run_id** | `{baseline['run_id']}` | `{partial10['run_id']}` | `{metrics['run_id']}` |")
    lines.append(f"| **input features** | {baseline['feature_count']} | {partial10['feature_count']} | {metrics['feature_count']} |")
    lines.append(f"| **family_in / family_sel** | {baseline['family_input_count']}/{baseline['family_selected_count']} | {partial10['family_input_count']}/{partial10['family_selected_count']} | {metrics['family_input_count']}/{metrics['family_selected_count']} |")

    def _pct(v):
        return f"{v:.2%}" if v is not None else "—"

    def _f4(v):
        return f"{v:.4f}" if v is not None else "—"

    lines.append(f"| **HC accuracy** | {_pct(baseline['high_conf_accuracy'])} | {_pct(partial10['high_conf_accuracy'])} | {_pct(metrics['high_conf_accuracy'])} |")
    lines.append(f"| **Wilson 95 lower** | {_pct(baseline['wilson_lower_95'])} | {_pct(partial10['wilson_lower_95'])} | {_pct(metrics['wilson_lower_95'])} |")
    lines.append(f"| **HC count** | {baseline['high_conf_count']} | {partial10['high_conf_count']} | {metrics['high_conf_count']} |")
    lines.append(f"| **HC coverage** | {_pct(baseline['coverage'])} | {_pct(partial10['coverage'])} | {_pct(metrics['coverage'])} |")
    lines.append(f"| **HC Brier** | — | — | {_f4(metrics['high_conf_brier'])} |")
    lines.append(f"| **All Brier** | {_f4(baseline['brier'])} | {_f4(partial10['brier'])} | {_f4(metrics['brier'])} |")

    lines.append("\n## Delta vs Baseline\n")
    lines.append("| Metric | Delta |")
    lines.append("|--------|-------|")
    lines.append(f"| HC accuracy | {_safe_delta(metrics['high_conf_accuracy'], baseline['high_conf_accuracy'])} |")
    lines.append(f"| Wilson 95 lower | {_safe_delta(metrics['wilson_lower_95'], baseline['wilson_lower_95'])} |")
    lines.append(f"| HC count | {_safe_delta(metrics['high_conf_count'], baseline['high_conf_count'], 'd')} |")
    lines.append(f"| HC coverage | {_safe_delta(metrics['coverage'], baseline['coverage'])} |")
    lines.append(f"| All Brier | {_safe_delta(metrics['brier'], baseline['brier'])} |")

    lines.append("\n## Delta vs Partial Tier1 (10 base)\n")
    lines.append("| Metric | Delta |")
    lines.append("|--------|-------|")
    lines.append(f"| HC accuracy | {_safe_delta(metrics['high_conf_accuracy'], partial10['high_conf_accuracy'])} |")
    lines.append(f"| Wilson 95 lower | {_safe_delta(metrics['wilson_lower_95'], partial10['wilson_lower_95'])} |")
    lines.append(f"| HC count | {_safe_delta(metrics['high_conf_count'], partial10['high_conf_count'], 'd')} |")
    lines.append(f"| HC coverage | {_safe_delta(metrics['coverage'], partial10['coverage'])} |")
    lines.append(f"| All Brier | {_safe_delta(metrics['brier'], partial10['brier'])} |")

    lines.append("\n## Column Diagnostic (28 features)\n")
    lines.append("| Column | In Input | Selected | Is Auction | Skipped | Reason |")
    lines.append("|--------|----------|----------|------------|---------|--------|")
    for row in col_diag:
        auction_tag = "**YES**" if row["is_auction"] else ""
        lines.append(
            f"| `{row['column']}` | {row['in_input']} | {row['selected']} "
            f"| {auction_tag} | {row['skipped']} | {row['reason']} |"
        )

    auction_base = [r for r in col_diag if r["is_auction"] and not r["column"].endswith("_available")]
    auction_selected = [r for r in auction_base if r["selected"]]
    lines.append(f"\n**Auction summary**: {len(auction_selected)}/{len(auction_base)} auction base columns selected.\n")

    lines.append("## Conclusion\n")
    lines.append("*(filled after run completes)*\n")

    lines.append("## Constraints Confirmation\n")
    lines.append("- [x] frozen_forward_config.json NOT modified")
    lines.append("- [x] diagnostic_monkey_patch = true")
    lines.append("- [x] lockbox_role = seen_research")
    lines.append("- [x] No run claims 'passed'")
    lines.append("- [x] baseline and partial10 from family_ablation_results_20260503.json (not re-run)")
    lines.append("- [x] stk_auction_o and stk_auction_c cache verified pre-run")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def main() -> int:
    app_config = get_default_config()
    store = LocalDataStore(app_config)
    cache_dir = Path(app_config.storage.cache_dir)

    # --- Pre-check ---
    print("[complete14] Pre-run tushare check ...", file=sys.stderr)
    tushare_pre = _pre_run_tushare_check(cache_dir)
    all_ok = True
    for api, count in tushare_pre.items():
        tag = "OK" if count > 0 else "EMPTY"
        print(f"  {api}: {count} parquets [{tag}]", file=sys.stderr)
        if count == 0:
            all_ok = False
    if not all_ok:
        print("[complete14] ABORT: some tushare APIs have 0 parquets", file=sys.stderr)
        return 1

    # --- Load prior results for comparison ---
    print(f"[complete14] Loading prior results from {PRIOR_RESULTS_JSON}", file=sys.stderr)
    prior = json.loads(PRIOR_RESULTS_JSON.read_text(encoding="utf-8"))

    # --- Build config ---
    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 6, 30),
        test_start=date(2025, 7, 1),
        end=date(2026, 4, 30),
        train_rows=300_000,
        test_rows=120_000,
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        selector_coverage_weight=0.02,
        candidate_family="all",
        lockbox_role="seen_research",
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        seed=42,
        feature_set="research",
    )

    custom_features = tuple(dict.fromkeys((*GPU_PROBE_STABLE_FEATURES, *TUSHARE_COMPLETE14_FEATURES)))
    expected_after_cross = len([f for f in custom_features if not f.startswith("cross_")])
    print(f"[complete14] Pool: GPU_PROBE_STABLE_FEATURES({len(GPU_PROBE_STABLE_FEATURES)}) + 28 tushare = {len(custom_features)} unique", file=sys.stderr)
    print(f"[complete14] After cross_ exclusion: ~{expected_after_cross} input features", file=sys.stderr)

    # --- Monkey-patch: 1st call for cache fingerprint, 2nd call for model input ---
    original_fn = _gpu_probe_module._feature_names_for_config
    call_state = {"count": 0}

    def _two_phase_feature_names(cfg):
        call_state["count"] += 1
        if call_state["count"] == 1:
            return original_fn(cfg)
        return custom_features

    print(f"\n{'='*72}", file=sys.stderr)
    print(f"  VARIANT: tushare_tier1_complete14", file=sys.stderr)
    print(f"  feature_set=research (for cache), model pool={len(custom_features)}", file=sys.stderr)
    print(f"{'='*72}\n", file=sys.stderr)

    _gpu_probe_module._feature_names_for_config = _two_phase_feature_names
    t0 = time.perf_counter()
    try:
        result = run_gpu_next_day_probe(store, config)
    finally:
        _gpu_probe_module._feature_names_for_config = original_fn
    elapsed = time.perf_counter() - t0

    # --- Extract metrics ---
    metrics = _extract_metrics(result)
    col_diag = _column_diagnostic(result)

    print(f"\n[complete14] Done in {elapsed:.1f}s — status={metrics['status']}", file=sys.stderr)
    print(f"  features={metrics['feature_count']} selected={metrics['selected_feature_count']}", file=sys.stderr)
    print(f"  family_in={metrics['family_input_count']} family_sel={metrics['family_selected_count']}", file=sys.stderr)
    print(f"  HC_acc={metrics['high_conf_accuracy']} wilson={metrics['wilson_lower_95']}", file=sys.stderr)
    print(f"  HC_count={metrics['high_conf_count']} coverage={metrics['coverage']}", file=sys.stderr)
    print(f"  HC_brier={metrics['high_conf_brier']} brier={metrics['brier']}", file=sys.stderr)

    print("\n[complete14] Column diagnostic:", file=sys.stderr)
    for row in col_diag:
        auction = " [AUCTION]" if row["is_auction"] else ""
        print(
            f"  {row['column']:50s} in={row['in_input']:<5} sel={row['selected']:<5}{auction}",
            file=sys.stderr,
        )

    # --- Write reports ---
    md_path, json_path = _write_reports(metrics, tushare_pre, col_diag, prior, elapsed)
    print(f"\n[complete14] Reports:", file=sys.stderr)
    print(f"  MD:   {md_path}", file=sys.stderr)
    print(f"  JSON: {json_path}", file=sys.stderr)

    # Summary to stdout
    print(json.dumps({
        "experiment": "tushare_tier1_complete14",
        "run_id": metrics["run_id"],
        "status": metrics["status"],
        "feature_count": metrics["feature_count"],
        "family_in": metrics["family_input_count"],
        "family_sel": metrics["family_selected_count"],
        "HC_accuracy": metrics["high_conf_accuracy"],
        "wilson_lower_95": metrics["wilson_lower_95"],
        "HC_count": metrics["high_conf_count"],
        "coverage": metrics["coverage"],
        "HC_brier": metrics["high_conf_brier"],
        "brier": metrics["brier"],
        "reports": {"md": str(md_path), "json": str(json_path)},
    }, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
