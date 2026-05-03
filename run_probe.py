"""Run gpu probe with given coverage weight. Usage: python run_probe.py [coverage_weight]"""
import sys
from ashare_similarity.cli import main

cw = sys.argv[1] if len(sys.argv) > 1 else "0.02"
sys.argv = [
    "ashare-similarity", "gpu-prediction-probe",
    "--start", "2023-05-01",
    "--train-end", "2025-06-30",
    "--test-start", "2025-07-01",
    "--end", "2026-04-30",
    "--train-rows", "300000",
    "--test-rows", "120000",
    "--feature-set", "expanded",
    "--refresh-feature-cache",
    "--selector-coverage-weight", cw,
    "--label-target", "next_high_from_close",
    "--target-high-return-pct", "1.0",
]
main()
