"""Batch runner: invokes each remaining variant as a separate process to avoid GPU memory leak."""
import json
import subprocess
import sys
import time
from pathlib import Path

MANIFEST_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\1457_no_hard_moneyflow_variant_manifest_20260507.json")
LEDGER_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\experiment_ledger_20260507.jsonl")
SCRIPT = Path(__file__).resolve().parent / "run_1457_no_hard_moneyflow_matrix.py"


def get_done():
    done = set()
    if LEDGER_PATH.exists():
        with open(LEDGER_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and "M1457_" in line:
                    entry = json.loads(line)
                    done.add(entry["variant"])
    return done


def main():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    done = get_done()
    remaining = [v["variant_name"] for v in manifest["variants"] if v["variant_name"] not in done]
    total = len(manifest["variants"])

    print(f"Done: {len(done)}/{total}, Remaining: {len(remaining)}")

    for i, name in enumerate(remaining):
        print(f"\n[{len(done)+i+1}/{total}] Running: {name}")
        t0 = time.time()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "run-single-variant", name],
            capture_output=True, text=True, timeout=600
        )
        elapsed = time.time() - t0

        if result.returncode != 0:
            print(f"  FAILED (exit={result.returncode}, {elapsed:.0f}s)")
            stderr_last = result.stderr.strip().split("\n")[-5:]
            for line in stderr_last:
                print(f"  ERR: {line}")
            if "CUDA error" in result.stderr or "out of memory" in result.stderr:
                print("  GPU OOM detected — waiting 10s for GPU cleanup...")
                time.sleep(10)
                continue
            if "P0 STOP" in result.stdout:
                print("  *** P0 STOP — HALTING ***")
                sys.exit(1)
        else:
            stdout_lines = result.stdout.strip().split("\n")
            metrics_line = [l for l in stdout_lines if "HC acc=" in l]
            if metrics_line:
                print(f"  {metrics_line[-1].strip()} ({elapsed:.0f}s)")
            else:
                print(f"  OK ({elapsed:.0f}s)")

    final_done = get_done()
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {len(final_done)}/{total} variants done")


if __name__ == "__main__":
    main()
