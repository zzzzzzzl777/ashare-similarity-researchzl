"""Run Batch 2 probe via CLI: Batch 1 + THS sector factors."""
import os
import sys

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ashare_similarity.cli import main

for cw in ["0.02", "0.10"]:
    print(f"\n{'='*60}", flush=True)
    print(f"Batch 2 probe: coverage_weight={cw}", flush=True)
    print(f"{'='*60}", flush=True)

    sys.argv = [
        "ashare-similarity", "gpu-prediction-probe",
        "--start", "2023-05-01",
        "--train-end", "2025-06-30",
        "--test-start", "2025-07-01",
        "--end", "2026-04-30",
        "--train-rows", "300000",
        "--test-rows", "120000",
        "--feature-set", "expanded",
        "--selector-coverage-weight", cw,
        "--label-target", "next_high_from_close",
        "--target-high-return-pct", "1.0",
    ]
    if cw == "0.02":
        sys.argv.append("--refresh-feature-cache")
    try:
        main()
    except SystemExit:
        pass
    print(f"\nDone with cw={cw}", flush=True)
