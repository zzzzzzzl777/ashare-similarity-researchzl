"""Run Batch 2 with coverage_weight=0.50 to push coverage."""
import sys
import os

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ashare_similarity.cli import main

sys.argv = [
    "ashare-similarity", "gpu-prediction-probe",
    "--start", "2023-05-01",
    "--train-end", "2025-06-30",
    "--test-start", "2025-07-01",
    "--end", "2026-04-30",
    "--train-rows", "300000",
    "--test-rows", "120000",
    "--feature-set", "expanded",
    "--selector-coverage-weight", "0.50",
    "--label-target", "next_high_from_close",
    "--target-high-return-pct", "1.0",
]
try:
    main()
except SystemExit:
    pass
print("Done.", flush=True)
