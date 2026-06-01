"""Sequential coverage-weight sweep for Batch 1 factors.

Runs 3 probes sequentially with coverage_weight = 0.02, 0.10, 0.50
to find accuracy >= 75% + coverage >= 10% sweet spot.
"""
import json
import sys
import os

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

os.chdir(r"C:\Users\zzzzzzl\Desktop\subagent")

from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe
from ashare_similarity.prediction.local_data_store import LocalDataStore
from datetime import date

store = LocalDataStore(r"E:\ashare_similarity_runtime")

results = []
for cw in [0.02, 0.10, 0.50]:
    print(f"\n{'='*60}")
    print(f"Running probe with selector_coverage_weight = {cw}")
    print(f"{'='*60}", flush=True)

    config = GpuProbeConfig(
        start=date(2023, 5, 1),
        train_end=date(2025, 6, 30),
        test_start=date(2025, 7, 1),
        end=date(2026, 4, 30),
        train_rows=300_000,
        test_rows=120_000,
        feature_set="expanded",
        refresh_feature_cache=(cw == 0.02),
        selector_coverage_weight=cw,
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
    )

    result = run_gpu_next_day_probe(store, config)

    run_id = result.get("run_id", "unknown")
    hc = result.get("acceptance", {}).get("high_confidence", {})
    summary = {
        "coverage_weight": cw,
        "run_id": run_id,
        "hc_accuracy": hc.get("accuracy"),
        "wilson_95": hc.get("wilson_lower_95"),
        "coverage": hc.get("coverage"),
        "hc_count": hc.get("rows"),
        "coverage_gate_met": hc.get("coverage_gate_met"),
        "accuracy_met": hc.get("accuracy_met"),
        "wilson_met": hc.get("wilson_lower_met"),
        "passed": result.get("acceptance", {}).get("passed"),
    }
    results.append(summary)
    print(f"\nSummary: {json.dumps(summary, indent=2)}", flush=True)

print(f"\n{'='*60}")
print("ALL RESULTS:")
print(f"{'='*60}")
for r in results:
    cw = r["coverage_weight"]
    acc = r.get("hc_accuracy", 0) or 0
    wil = r.get("wilson_95", 0) or 0
    cov = r.get("coverage", 0) or 0
    cnt = r.get("hc_count", 0) or 0
    ok = "PASS" if (acc >= 0.75 and wil >= 0.75 and cov >= 0.10) else "FAIL"
    print(f"  cw={cw:.2f}: acc={acc:.4f} wilson={wil:.4f} cov={cov:.4f} count={cnt:,} [{ok}]")

with open(r"E:\ashare_similarity_runtime\data\reports\prediction\coverage_weight_sweep.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nResults saved to coverage_weight_sweep.json")
