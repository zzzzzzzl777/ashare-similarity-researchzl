"""
Phase 7, Layer 1: Run all 24 S1 policy grid variants.
Each variant differs in which B-class families are included/excluded.
Goal: identify which B-class families contribute to Wilson improvement.
"""
import sys
import json
import math
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phase7_s1_policy_grid_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phase7_s1_policy_grid_20260509.md"
MANIFEST_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\all_includable_factor_variant_manifest_20260509.json"


def wilson_lower_95(n, p):
    if n == 0 or p == 0:
        return 0.0
    z = 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin) / denom


def run_variant(store, variant):
    excluded = tuple(variant["excluded_feature_columns"])
    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 12, 31),
        test_start=date(2026, 1, 1),
        end=date(2026, 3, 31),
        seed=42,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=260,
        min_phase_days_3=1,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=excluded,
        lockbox_role="seen_research",
        use_feature_cache=True,
        refresh_feature_cache=False,
        candidate_family="all",
    )

    t0 = time.time()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.time() - t0

    hc_acc = result.get("confident_accuracy", 0)
    hc_count = result.get("confident_count", 0)
    hc_coverage = result.get("confident_coverage", 0)
    w95 = wilson_lower_95(hc_count, hc_acc)

    return {
        "variant_name": variant["variant_name"],
        "b_class_policy": variant["b_class_policy"],
        "exclusion_count": variant["exclusion_count"],
        "model": result.get("model", "unknown"),
        "pool_features": result.get("feature_count", 0),
        "selected_features": 260,
        "hc_accuracy": round(hc_acc, 6),
        "hc_count": hc_count,
        "hc_coverage": round(hc_coverage, 6),
        "wilson_95": round(w95, 6),
        "brier": round(result.get("confident_brier", 0), 6),
        "elapsed_seconds": round(elapsed, 1),
        "status": result.get("status", "unknown"),
        "passes_wilson_75": w95 >= 0.75,
    }


def main():
    with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    s1_variants = manifest["s1_policy_grid"]

    cfg = get_default_config()
    store = LocalDataStore(cfg)

    print("=" * 70)
    print("PHASE 7, LAYER 1: S1 POLICY GRID (24 variants)")
    print("=" * 70)

    all_results = []
    for i, variant in enumerate(s1_variants):
        bp = variant["b_class_policy"]
        print(f"\n[{i+1:2d}/24] {variant['variant_name']}")
        print(f"       chip={bp['chip_cost']} hot={bp['hot_holder_hk']} tgb={bp['tgb']} ths={bp['ths_sector']}")

        try:
            r = run_variant(store, variant)
            all_results.append(r)
            status = "PASS" if r["passes_wilson_75"] else "BELOW"
            print(f"       HC={r['hc_accuracy']:.4f} N={r['hc_count']} W95={r['wilson_95']:.4f} [{status}] ({r['elapsed_seconds']:.0f}s)")
        except Exception as e:
            all_results.append({
                "variant_name": variant["variant_name"],
                "b_class_policy": variant["b_class_policy"],
                "error": str(e),
                "passes_wilson_75": False,
            })
            print(f"       ERROR: {e}")

    # Analysis
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    passing = [r for r in all_results if r.get("passes_wilson_75")]
    failing = [r for r in all_results if not r.get("passes_wilson_75") and not r.get("error")]
    errors = [r for r in all_results if r.get("error")]

    print(f"\nPassing Wilson >= 75%: {len(passing)}/{len(all_results)}")
    print(f"Below 75%: {len(failing)}")
    print(f"Errors: {len(errors)}")

    if passing:
        best = max(passing, key=lambda x: x.get("wilson_95", 0))
        print(f"\nBest: {best['variant_name']} (W95={best['wilson_95']:.4f})")
        print(f"  Policy: {best['b_class_policy']}")

    # Marginal analysis: effect of each family
    print("\n--- Marginal Family Effects ---")
    families = ["chip_cost", "hot_holder_hk", "tgb", "ths_sector"]
    for fam in families:
        with_fam = [r for r in all_results if r.get("b_class_policy", {}).get(fam) != "delete" and not r.get("error")]
        without_fam = [r for r in all_results if r.get("b_class_policy", {}).get(fam) == "delete" and not r.get("error")]
        if with_fam and without_fam:
            avg_with = sum(r.get("wilson_95", 0) for r in with_fam) / len(with_fam)
            avg_without = sum(r.get("wilson_95", 0) for r in without_fam) / len(without_fam)
            delta = avg_with - avg_without
            print(f"  {fam:15s}: include={avg_with:.4f} delete={avg_without:.4f} delta={delta:+.4f}")

    # Save results
    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phase7_s1_policy_grid",
        "total_variants": len(all_results),
        "passing_wilson_75": len(passing),
        "failing": len(failing),
        "errors": len(errors),
        "best_variant": best["variant_name"] if passing else None,
        "best_wilson_95": best.get("wilson_95") if passing else None,
        "variants": all_results,
        "gate_result": {
            "p0_issues": len(errors),
            "p1_issues": 0,
            "proceed": len(errors) == 0 and len(passing) > 0,
        },
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nJSON: {OUTPUT_JSON}")

    # Write MD
    md_lines = []
    md_lines.append("# Phase 7 Layer 1: S1 Policy Grid Results - 2026-05-09\n")
    md_lines.append("## Results (sorted by Wilson 95%)\n")
    md_lines.append("| # | Variant | chip | hot | tgb | ths | HC Acc | N | Wilson 95% | Pass |")
    md_lines.append("|---|---------|------|-----|-----|-----|--------|---|------------|------|")

    sorted_results = sorted(all_results, key=lambda x: x.get("wilson_95", 0), reverse=True)
    for i, r in enumerate(sorted_results):
        if r.get("error"):
            md_lines.append("| " + str(i+1) + " | " + r["variant_name"] + " | ERROR | | | | | | | |")
            continue
        bp = r.get("b_class_policy", {})
        passes = "YES" if r.get("passes_wilson_75") else "NO"
        md_lines.append(
            "| " + str(i+1) + " | " + r["variant_name"] +
            " | " + bp.get("chip_cost", "?") +
            " | " + bp.get("hot_holder_hk", "?") +
            " | " + bp.get("tgb", "?") +
            " | " + bp.get("ths_sector", "?") +
            " | " + f"{r.get('hc_accuracy', 0):.4f}" +
            " | " + str(r.get("hc_count", 0)) +
            " | " + f"{r.get('wilson_95', 0):.4f}" +
            " | " + passes + " |"
        )

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"MD: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
