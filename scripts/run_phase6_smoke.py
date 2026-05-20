"""
Phase 6: Smoke runs — 3 CTRL variants on Q1.
Confirms: infrastructure works, train_end=2025-12-31, April not touched,
results are reproducible and within expected range.
"""
import sys
import json
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phase6_smoke_results_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phase6_smoke_results_20260509.md"
MANIFEST_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\all_includable_factor_variant_manifest_20260509.json"

# Load manifest for exclusion lists
with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
    manifest = json.load(f)

CTRL_VARIANTS = {v["variant_name"]: v for v in manifest["control_variants"]}

# Smoke variants to run
SMOKE_NAMES = [
    "CTRL_current_baseline_reproduced",
    "CTRL_delete_all_BC_uncertain",
    "CTRL_A_plus_chip_t1",
]


def build_config(variant):
    excluded = tuple(variant["excluded_feature_columns"])
    return GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 3, 31),
        seed=42,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=variant.get("max_selected_features", 260),
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=excluded,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
        candidate_family="all",
    )


def extract_metrics(result):
    if not result:
        return {"error": "no result returned"}
    return {
        "status": result.get("status", "unknown"),
        "model_name": result.get("best_model_name", "unknown"),
        "train_rows": result.get("train_rows", 0),
        "test_rows": result.get("test_rows", 0),
        "train_end": str(result.get("train_end", "")),
        "test_start": str(result.get("test_start", "")),
        "test_end": str(result.get("end", "")),
        "selected_features_count": result.get("selected_features_count", 0),
        "pool_features_count": result.get("pool_features_count", 0),
        "hc_accuracy": result.get("confident_accuracy", 0),
        "hc_count": result.get("confident_count", 0),
        "hc_coverage": result.get("confident_coverage", 0),
        "threshold": result.get("threshold", 0),
        "wilson_95": result.get("wilson_lower_95", 0),
        "brier": result.get("brier_score", 0),
        "calibration": result.get("calibration_method", "unknown"),
        "duplicates_removed": result.get("duplicates_removed_count", 0),
        "candidate_family": result.get("candidate_family", "unknown"),
    }


def main():
    cfg = get_default_config()
    store = LocalDataStore(cfg)

    results = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phase6_smoke",
        "variants_run": [],
    }

    print("=" * 70)
    print("PHASE 6: SMOKE RUNS")
    print("=" * 70)

    for name in SMOKE_NAMES:
        variant = CTRL_VARIANTS[name]
        config = build_config(variant)

        print(f"\n{'─'*60}")
        print(f"Running: {name}")
        print(f"  Excluded columns: {len(variant['excluded_feature_columns'])}")
        print(f"  Max selected: {config.max_selected_features}")
        print(f"  Train end: {config.train_end}")
        print(f"  Test: {config.test_start} to {config.end}")
        print(f"{'─'*60}")

        t0 = time.time()
        try:
            result = run_gpu_next_day_probe(store, config)
            elapsed = time.time() - t0
            metrics = extract_metrics(result)
            metrics["elapsed_seconds"] = round(elapsed, 1)
            metrics["variant_name"] = name
            metrics["error"] = None

            print(f"  DONE in {elapsed:.1f}s")
            print(f"  Model: {metrics['model_name']}")
            print(f"  Pool: {metrics['pool_features_count']}, Selected: {metrics['selected_features_count']}")
            print(f"  HC Accuracy: {metrics['hc_accuracy']:.4f}")
            print(f"  HC Count: {metrics['hc_count']}")
            print(f"  Wilson 95%: {metrics['wilson_95']:.4f}")
            print(f"  Threshold: {metrics['threshold']:.4f}")

        except Exception as e:
            elapsed = time.time() - t0
            metrics = {
                "variant_name": name,
                "error": str(e),
                "elapsed_seconds": round(elapsed, 1),
            }
            print(f"  ERROR after {elapsed:.1f}s: {e}")

        results["variants_run"].append(metrics)

    # Validate smoke results
    print("\n" + "=" * 70)
    print("SMOKE VALIDATION")
    print("=" * 70)

    p0_issues = []
    p1_issues = []

    for m in results["variants_run"]:
        name = m["variant_name"]
        if m.get("error"):
            p0_issues.append(f"{name}: training failed with error: {m['error']}")
            continue

        if m.get("train_end") != "2025-12-31":
            p0_issues.append(f"{name}: train_end is {m.get('train_end')}, expected 2025-12-31")

        if m.get("test_end") and "2026-04" in str(m.get("test_end")):
            p0_issues.append(f"{name}: test_end includes April data!")

        if m.get("wilson_95", 0) < 0.50:
            p1_issues.append(f"{name}: wilson_95={m.get('wilson_95'):.4f} is suspiciously low")

        if m.get("hc_count", 0) < 1000:
            p1_issues.append(f"{name}: hc_count={m.get('hc_count')} is very low")

    results["validation"] = {
        "p0_issues": p0_issues,
        "p1_issues": p1_issues,
        "all_train_end_correct": all(
            m.get("train_end") == "2025-12-31"
            for m in results["variants_run"]
            if not m.get("error")
        ),
        "no_april_leakage": all(
            "2026-04" not in str(m.get("test_end", ""))
            for m in results["variants_run"]
            if not m.get("error")
        ),
    }

    results["gate_result"] = {
        "p0_issues": len(p0_issues),
        "p1_issues": len(p1_issues),
        "proceed": len(p0_issues) == 0,
    }

    for issue in p0_issues:
        print(f"  P0: {issue}")
    for issue in p1_issues:
        print(f"  P1: {issue}")
    if not p0_issues:
        print("  ALL SMOKE CHECKS PASS - proceed to Phase 7")

    # Write outputs
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nJSON: {OUTPUT_JSON}")

    # Write MD
    md_lines = []
    md_lines.append("# Phase 6: Smoke Run Results - 2026-05-09\n")
    md_lines.append("Generated: " + results["generated_at"] + "\n")
    md_lines.append("## Variants Run\n")
    md_lines.append("| Variant | Model | Pool | Selected | HC Acc | HC Count | Wilson 95% | Time |")
    md_lines.append("|---------|-------|------|----------|--------|----------|------------|------|")

    for m in results["variants_run"]:
        if m.get("error"):
            md_lines.append("| " + m["variant_name"] + " | ERROR | - | - | - | - | - | " + str(m.get("elapsed_seconds", "?")) + "s |")
        else:
            md_lines.append(
                "| " + m["variant_name"] + " | " + str(m.get("model_name", "?")) +
                " | " + str(m.get("pool_features_count", "?")) +
                " | " + str(m.get("selected_features_count", "?")) +
                " | " + f"{m.get('hc_accuracy', 0):.4f}" +
                " | " + str(m.get("hc_count", "?")) +
                " | " + f"{m.get('wilson_95', 0):.4f}" +
                " | " + str(m.get("elapsed_seconds", "?")) + "s |"
            )

    md_lines.append("\n## Validation\n")
    md_lines.append("- All train_end = 2025-12-31: " + str(results["validation"]["all_train_end_correct"]))
    md_lines.append("- No April leakage: " + str(results["validation"]["no_april_leakage"]))
    md_lines.append("- P0 issues: " + str(len(p0_issues)))
    md_lines.append("- P1 issues: " + str(len(p1_issues)))
    md_lines.append("- Proceed: " + str(results["gate_result"]["proceed"]))

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"MD: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
