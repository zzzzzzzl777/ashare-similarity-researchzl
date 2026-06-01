"""Research Daily Clean 39 — single-variant seen_research diagnostic.

Removes 6 near-constant + 2 redundant columns from the full 47 research
daily base, yielding 39 base + 39 _available = 78 extra features on top
of GPU_PROBE_STABLE_FEATURES.

Compares against:
  - baseline_expanded_no_cross  (gpu_probe_20260503T113328Z_1b272829)
  - dirty94                     (gpu_probe_20260503T113537Z_058b885e, full 47 base)
  - tushare_complete14          (gpu_probe_20260503T123107Z_b05caa22)

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

EXCLUDED_NEAR_CONSTANT: frozenset[str] = frozenset({
    "seal_rate_80_threshold",
    "no_theme_rotation_mode",
    "money_effect_sector_rotation",
    "mid_cap_trap_risk",
    "bet_decline_exhaustion",
    "one_day_trip_risk_proxy",
})

EXCLUDED_REDUNDANT: frozenset[str] = frozenset({
    "market_limit_down_rate",
    "market_limit_seal_success_rate",
})

EXCLUDED_ALL = EXCLUDED_NEAR_CONSTANT | EXCLUDED_REDUNDANT

RESEARCH_DAILY_CLEAN39_BASE: tuple[str, ...] = (
    "market_one_word_board_count",
    "market_high_leader_crash_count",
    "cycle_day_count",
    "divergence_day_count",
    "buy_sell_cycle_phase",
    "liquidity_exhaustion_signal",
    "market_split_signal",
    "quant_climax_type",
    "vol_stagnation_signal",
    "bull_rotation_upgrade",
    "theme_capacity_score",
    "market_amount_ratio_20",
    "market_amount_percentile_60",
    "volume_is_king_signal",
    "ground_volume_risk",
    "post_decline_transition",
    "decline_stabilize_signal",
    "weak_friday_risk",
    "prev_top20_chase_return",
    "prev_top20_chase_win_rate",
    "prev_bottom20_rebound_return",
    "money_effect_spread_20",
    "collapse_warning_signal",
    "bullish_pivot_recognition",
    "limit_premium_failure_signal",
    "bad_sentiment_no_sweep",
    "high_leader_crash_sentiment_collapse",
    "full_position_trigger",
    "late_cycle_position_cap",
    "bear_position_reduction",
    "strong_market_regime",
    "weak_market_oversold_regime",
    "bull_hotspot_bear_oversold",
    "shrink_after_rotten",
    "explosive_vol_next_weak",
    "break_node_new_dragon",
    "dragon_replace_signal",
    "buy_rise_divergence",
    "board_keep_break_signal",
)

assert len(RESEARCH_DAILY_CLEAN39_BASE) == 39, f"Expected 39, got {len(RESEARCH_DAILY_CLEAN39_BASE)}"
assert not (set(RESEARCH_DAILY_CLEAN39_BASE) & EXCLUDED_ALL), "Clean set contains excluded columns"

RESEARCH_DAILY_CLEAN39_FEATURES: tuple[str, ...] = (
    *RESEARCH_DAILY_CLEAN39_BASE,
    *(f"{c}_available" for c in RESEARCH_DAILY_CLEAN39_BASE),
)

PRIOR_RESULTS_JSON = Path(
    "E:/ashare_similarity_runtime/data/reports/prediction"
    "/family_ablation_results_20260503.json"
)
COMPLETE14_RESULTS_JSON = Path(
    "E:/ashare_similarity_runtime/data/reports/prediction"
    "/tushare_tier1_complete14_results_20260503.json"
)


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
    extra = set(RESEARCH_DAILY_CLEAN39_FEATURES)
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
    for col in RESEARCH_DAILY_CLEAN39_FEATURES:
        row: dict = {"column": col, "in_input": col in all_input, "selected": col in selected}
        if col in skipped_map:
            row["skipped"] = True
            row["reason"] = skipped_map[col].get("reason", "")
        else:
            row["skipped"] = False
            row["reason"] = ""
        row["is_base"] = not col.endswith("_available")
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


def _pct(v):
    return f"{v:.2%}" if v is not None else "—"


def _f4(v):
    return f"{v:.4f}" if v is not None else "—"


def _write_reports(
    metrics: dict,
    col_diag: list[dict],
    prior: dict,
    complete14: dict,
    elapsed: float,
) -> tuple[Path, Path]:
    generated_at = datetime.now(timezone.utc).isoformat()
    baseline = prior["variants"][0]
    dirty94 = prior["variants"][1]
    c14 = complete14["complete14"]

    # --- JSON ---
    app_config = get_default_config()
    json_dir = Path(app_config.storage.report_dir) / "prediction"
    json_dir.mkdir(parents=True, exist_ok=True)
    json_path = json_dir / "research_daily_clean39_results_20260503.json"
    json_payload = {
        "generated_at": generated_at,
        "experiment": "research_daily_clean39",
        "diagnostic_monkey_patch": True,
        "lockbox_role": "seen_research",
        "not_passed": True,
        "not_frozen": True,
        "clean39": metrics,
        "baseline_reference": {
            "run_id": baseline["run_id"],
            "high_conf_accuracy": baseline["high_conf_accuracy"],
            "wilson_lower_95": baseline["wilson_lower_95"],
            "high_conf_count": baseline["high_conf_count"],
            "coverage": baseline["coverage"],
            "brier": baseline["brier"],
        },
        "dirty94_reference": {
            "run_id": dirty94["run_id"],
            "high_conf_accuracy": dirty94["high_conf_accuracy"],
            "wilson_lower_95": dirty94["wilson_lower_95"],
            "high_conf_count": dirty94["high_conf_count"],
            "coverage": dirty94["coverage"],
            "brier": dirty94["brier"],
        },
        "complete14_reference": {
            "run_id": c14["run_id"],
            "high_conf_accuracy": c14["high_conf_accuracy"],
            "wilson_lower_95": c14["wilson_lower_95"],
            "high_conf_count": c14["high_conf_count"],
            "coverage": c14["coverage"],
            "brier": c14["brier"],
        },
        "excluded_columns": {
            "near_constant": sorted(EXCLUDED_NEAR_CONSTANT),
            "redundant": sorted(EXCLUDED_REDUNDANT),
        },
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
    md_path = docs_dir / "research_daily_clean39_results_20260503.md"

    lines: list[str] = []
    lines.append("# Research Daily Clean 39 Results\n")
    lines.append(f"> Generated: {generated_at}")
    lines.append("> Experiment: research_daily_clean39")
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
        ("model_input_pool", "GPU_PROBE_STABLE_FEATURES + 78 research daily clean39"),
        ("extra_base_columns", "39 (47 full - 6 near-constant - 2 redundant)"),
        ("extra_total_columns", "78 (39 base + 39 _available)"),
    ]:
        lines.append(f"| {k} | {v} |")

    lines.append("\n## Excluded Columns (8)\n")
    lines.append("### Near-constant (6)\n")
    lines.append("| Column | Nonzero% | Reason |")
    lines.append("|--------|----------|--------|")
    for col, nz, reason in [
        ("seal_rate_80_threshold", "0.09%", "binary < 1 in 1000"),
        ("no_theme_rotation_mode", "0.93%", "near-constant"),
        ("money_effect_sector_rotation", "0.78%", "near-constant"),
        ("mid_cap_trap_risk", "0.89%", "near-constant"),
        ("bet_decline_exhaustion", "0.44%", "near-constant"),
        ("one_day_trip_risk_proxy", "0.59%", "near-constant"),
    ]:
        lines.append(f"| `{col}` | {nz} | {reason} |")

    lines.append("\n### Redundant with selected 260 (2)\n")
    lines.append("| Column | Correlated With | r |")
    lines.append("|--------|----------------|---|")
    lines.append("| `market_limit_down_rate` | `market_limit_down_count` | 1.0000 |")
    lines.append("| `market_limit_seal_success_rate` | `market_broken_board_rate` | -1.0000 |")

    lines.append("\n## Comparison Table\n")
    lines.append("| | baseline | dirty94 | complete14 | **clean39** |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| **run_id** | `{baseline['run_id']}` | `{dirty94['run_id']}` | `{c14['run_id']}` | `{metrics['run_id']}` |")
    lines.append(f"| **input features** | {baseline['feature_count']} | {dirty94['feature_count']} | {c14['feature_count']} | {metrics['feature_count']} |")
    lines.append(f"| **family_in / family_sel** | {baseline['family_input_count']}/{baseline['family_selected_count']} | {dirty94['family_input_count']}/{dirty94['family_selected_count']} | {c14['family_input_count']}/{c14['family_selected_count']} | {metrics['family_input_count']}/{metrics['family_selected_count']} |")
    lines.append(f"| **HC accuracy** | {_pct(baseline['high_conf_accuracy'])} | {_pct(dirty94['high_conf_accuracy'])} | {_pct(c14['high_conf_accuracy'])} | {_pct(metrics['high_conf_accuracy'])} |")
    lines.append(f"| **Wilson 95 lower** | {_pct(baseline['wilson_lower_95'])} | {_pct(dirty94['wilson_lower_95'])} | {_pct(c14['wilson_lower_95'])} | {_pct(metrics['wilson_lower_95'])} |")
    lines.append(f"| **HC count** | {baseline['high_conf_count']} | {dirty94['high_conf_count']} | {c14['high_conf_count']} | {metrics['high_conf_count']} |")
    lines.append(f"| **HC coverage** | {_pct(baseline['coverage'])} | {_pct(dirty94['coverage'])} | {_pct(c14['coverage'])} | {_pct(metrics['coverage'])} |")
    lines.append(f"| **HC Brier** | — | — | {_f4(c14.get('high_conf_brier'))} | {_f4(metrics['high_conf_brier'])} |")
    lines.append(f"| **All Brier** | {_f4(baseline['brier'])} | {_f4(dirty94['brier'])} | {_f4(c14['brier'])} | {_f4(metrics['brier'])} |")

    lines.append("\n## Delta vs Baseline\n")
    lines.append("| Metric | Delta |")
    lines.append("|--------|-------|")
    lines.append(f"| HC accuracy | {_safe_delta(metrics['high_conf_accuracy'], baseline['high_conf_accuracy'])} |")
    lines.append(f"| Wilson 95 lower | {_safe_delta(metrics['wilson_lower_95'], baseline['wilson_lower_95'])} |")
    lines.append(f"| HC count | {_safe_delta(metrics['high_conf_count'], baseline['high_conf_count'], 'd')} |")
    lines.append(f"| HC coverage | {_safe_delta(metrics['coverage'], baseline['coverage'])} |")
    lines.append(f"| All Brier | {_safe_delta(metrics['brier'], baseline['brier'])} |")

    lines.append("\n## Delta vs Dirty94 (full 47 base)\n")
    lines.append("| Metric | Delta |")
    lines.append("|--------|-------|")
    lines.append(f"| HC accuracy | {_safe_delta(metrics['high_conf_accuracy'], dirty94['high_conf_accuracy'])} |")
    lines.append(f"| Wilson 95 lower | {_safe_delta(metrics['wilson_lower_95'], dirty94['wilson_lower_95'])} |")
    lines.append(f"| HC count | {_safe_delta(metrics['high_conf_count'], dirty94['high_conf_count'], 'd')} |")
    lines.append(f"| HC coverage | {_safe_delta(metrics['coverage'], dirty94['coverage'])} |")
    lines.append(f"| All Brier | {_safe_delta(metrics['brier'], dirty94['brier'])} |")

    lines.append("\n## Delta vs Tushare Complete14\n")
    lines.append("| Metric | Delta |")
    lines.append("|--------|-------|")
    lines.append(f"| HC accuracy | {_safe_delta(metrics['high_conf_accuracy'], c14['high_conf_accuracy'])} |")
    lines.append(f"| Wilson 95 lower | {_safe_delta(metrics['wilson_lower_95'], c14['wilson_lower_95'])} |")
    lines.append(f"| HC count | {_safe_delta(metrics['high_conf_count'], c14['high_conf_count'], 'd')} |")
    lines.append(f"| HC coverage | {_safe_delta(metrics['coverage'], c14['coverage'])} |")
    lines.append(f"| All Brier | {_safe_delta(metrics['brier'], c14['brier'])} |")

    lines.append("\n## Column Diagnostic (78 features)\n")
    lines.append("| Column | In Input | Selected | Base? | Skipped | Reason |")
    lines.append("|--------|----------|----------|-------|---------|--------|")
    for row in col_diag:
        base_tag = "base" if row["is_base"] else "_avail"
        lines.append(
            f"| `{row['column']}` | {row['in_input']} | {row['selected']} "
            f"| {base_tag} | {row['skipped']} | {row['reason']} |"
        )

    base_rows = [r for r in col_diag if r["is_base"]]
    base_selected = [r for r in base_rows if r["selected"]]
    lines.append(f"\n**Selection summary**: {len(base_selected)}/{len(base_rows)} clean39 base columns selected.\n")

    lines.append("## Conclusion\n")
    lines.append("*(filled after run completes)*\n")

    lines.append("## Constraints Confirmation\n")
    lines.append("- [x] frozen_forward_config.json NOT modified")
    lines.append("- [x] diagnostic_monkey_patch = true")
    lines.append("- [x] lockbox_role = seen_research")
    lines.append("- [x] No run claims 'passed'")
    lines.append("- [x] baseline, dirty94, complete14 from prior results (not re-run)")
    lines.append("- [x] 6 near-constant + 2 redundant columns excluded from clean set")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def main() -> int:
    app_config = get_default_config()
    store = LocalDataStore(app_config)

    # --- Load prior results ---
    print("[clean39] Loading prior results ...", file=sys.stderr)
    prior = json.loads(PRIOR_RESULTS_JSON.read_text(encoding="utf-8"))
    complete14 = json.loads(COMPLETE14_RESULTS_JSON.read_text(encoding="utf-8"))
    print(f"  baseline:   {prior['variants'][0]['run_id']}", file=sys.stderr)
    print(f"  dirty94:    {prior['variants'][1]['run_id']}", file=sys.stderr)
    print(f"  complete14: {complete14['complete14']['run_id']}", file=sys.stderr)

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

    custom_features = tuple(dict.fromkeys((*GPU_PROBE_STABLE_FEATURES, *RESEARCH_DAILY_CLEAN39_FEATURES)))
    expected_after_cross = len([f for f in custom_features if not f.startswith("cross_")])
    print(f"[clean39] Pool: GPU_PROBE_STABLE_FEATURES({len(GPU_PROBE_STABLE_FEATURES)}) + 78 clean39 = {len(custom_features)} unique", file=sys.stderr)
    print(f"[clean39] After cross_ exclusion: ~{expected_after_cross} input features", file=sys.stderr)

    # --- Monkey-patch ---
    original_fn = _gpu_probe_module._feature_names_for_config
    call_state = {"count": 0}

    def _two_phase_feature_names(cfg):
        call_state["count"] += 1
        if call_state["count"] == 1:
            return original_fn(cfg)
        return custom_features

    print(f"\n{'='*72}", file=sys.stderr)
    print(f"  VARIANT: research_daily_clean39", file=sys.stderr)
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

    print(f"\n[clean39] Done in {elapsed:.1f}s — status={metrics['status']}", file=sys.stderr)
    print(f"  features={metrics['feature_count']} selected={metrics['selected_feature_count']}", file=sys.stderr)
    print(f"  family_in={metrics['family_input_count']} family_sel={metrics['family_selected_count']}", file=sys.stderr)
    print(f"  HC_acc={metrics['high_conf_accuracy']} wilson={metrics['wilson_lower_95']}", file=sys.stderr)
    print(f"  HC_count={metrics['high_conf_count']} coverage={metrics['coverage']}", file=sys.stderr)
    print(f"  HC_brier={metrics['high_conf_brier']} brier={metrics['brier']}", file=sys.stderr)

    print("\n[clean39] Column diagnostic:", file=sys.stderr)
    for row in col_diag:
        base_tag = " [BASE]" if row["is_base"] else ""
        print(
            f"  {row['column']:50s} in={row['in_input']:<5} sel={row['selected']:<5}{base_tag}",
            file=sys.stderr,
        )

    # --- Write reports ---
    md_path, json_path = _write_reports(metrics, col_diag, prior, complete14, elapsed)
    print(f"\n[clean39] Reports:", file=sys.stderr)
    print(f"  MD:   {md_path}", file=sys.stderr)
    print(f"  JSON: {json_path}", file=sys.stderr)

    # Summary to stdout
    print(json.dumps({
        "experiment": "research_daily_clean39",
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
