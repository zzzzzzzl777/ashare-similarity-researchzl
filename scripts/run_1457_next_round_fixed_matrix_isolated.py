"""Run the 14:57 fixed matrix with one Python process per fold.

This wrapper exists because GPU/GBDT libraries on Windows can leave native
state behind after a large fold. The underlying fixed-matrix runner is still
the single source of truth for model configuration and result writing; this
script only orchestrates isolated child processes. A production leaderboard
should use a single explicit backend for all rows.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from run_1457_next_round_fixed_matrix import result_key, selected_variants, selected_windows, write_summary


def parse_args() -> argparse.Namespace:
    cfg = get_default_config()
    report_dir = cfg.storage.report_dir / "prediction"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof-date", required=True)
    parser.add_argument("--feature-cache", type=Path, required=True)
    parser.add_argument(
        "--matrix-csv",
        type=Path,
        default=report_dir / "next_round_1457_model_matrix_manifest_20260513.csv",
    )
    parser.add_argument(
        "--time-window-csv",
        type=Path,
        default=report_dir / "next_round_1457_time_window_manifest_20260513.csv",
    )
    parser.add_argument("--variant-id", action="append", default=[])
    parser.add_argument(
        "--stage",
        action="append",
        default=[],
        help="Model-matrix stages to run. Defaults to fixed_config_first.",
    )
    parser.add_argument("--scheme", action="append", default=[])
    parser.add_argument("--outer-fold", action="append", type=int, default=[], help="Run only these outer fold ids.")
    parser.add_argument("--max-folds-per-scheme", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budget", type=int, default=260)
    parser.add_argument("--train-rows", type=int, default=300_000)
    parser.add_argument("--test-rows", type=int, default=120_000)
    parser.add_argument(
        "--backend",
        choices=("gpu", "cpu", "gpu_with_cpu_retry"),
        default="gpu",
        help="Compute backend policy. Use cpu for reproducible production leaderboards; gpu_with_cpu_retry is diagnostic only.",
    )
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true", help="Print the isolated execution plan without running folds.")
    return parser.parse_args()


def read_latest_rows(jsonl_path: Path) -> dict[tuple[str, str, int, int, int], dict[str, Any]]:
    latest: dict[tuple[str, str, int, int, int], dict[str, Any]] = {}
    if not jsonl_path.exists():
        return latest
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            latest[result_key(row)] = row
    return latest


def is_completed(jsonl_path: Path, key: tuple[str, str, int, int, int]) -> bool:
    row = read_latest_rows(jsonl_path).get(key)
    return bool(row and str(row.get("status")) != "ERROR")


def child_command(args: argparse.Namespace, variant_id: str, scheme: str, outer_fold: int, *, force_cpu: bool) -> list[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_1457_next_round_fixed_matrix.py"),
        "--asof-date",
        args.asof_date,
        "--feature-cache",
        str(args.feature_cache),
        "--matrix-csv",
        str(args.matrix_csv),
        "--time-window-csv",
        str(args.time_window_csv),
        "--variant-id",
        variant_id,
        "--scheme",
        scheme,
        "--outer-fold",
        str(int(outer_fold)),
        "--seed",
        str(int(args.seed)),
        "--budget",
        str(int(args.budget)),
        "--train-rows",
        str(int(args.train_rows)),
        "--test-rows",
        str(int(args.test_rows)),
        "--resume",
    ]
    if force_cpu:
        cmd.append("--force-cpu")
    for stage in args.stage:
        cmd.extend(["--stage", str(stage)])
    return cmd


def run_child(
    args: argparse.Namespace,
    *,
    variant_id: str,
    scheme: str,
    outer_fold: int,
    force_cpu: bool,
    attempt: int,
    log_dir: Path,
) -> int:
    mode = "cpu" if force_cpu else "gpu"
    stem = f"{variant_id}__{scheme}__fold{int(outer_fold):02d}__{mode}__attempt{attempt}"
    stdout_path = log_dir / f"{stem}.out.log"
    stderr_path = log_dir / f"{stem}.err.log"
    started = time.perf_counter()
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        proc = subprocess.run(
            child_command(args, variant_id, scheme, outer_fold, force_cpu=force_cpu),
            cwd=REPO_ROOT,
            stdout=out,
            stderr=err,
            text=True,
        )
    elapsed = time.perf_counter() - started
    print(
        json.dumps(
            {
                "event": "child_done",
                "variant_id": variant_id,
                "scheme": scheme,
                "outer_fold": int(outer_fold),
                "mode": mode,
                "attempt": int(attempt),
                "returncode": int(proc.returncode),
                "elapsed_s": round(elapsed, 3),
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return int(proc.returncode)


def main() -> int:
    args = parse_args()
    cfg = get_default_config()
    report_dir = cfg.storage.report_dir / "prediction"
    jsonl_path = report_dir / f"next_round_1457_fixed_matrix_results_{args.asof_date}.jsonl"
    log_dir = report_dir / "isolated_matrix_logs" / args.asof_date
    log_dir.mkdir(parents=True, exist_ok=True)

    matrix_df = pd.read_csv(args.matrix_csv)
    window_df = pd.read_csv(args.time_window_csv)
    variants = selected_variants(matrix_df, args.variant_id, max_variants=0, stages=args.stage)
    windows = selected_windows(window_df, args.scheme, args.max_folds_per_scheme, args.outer_fold)
    plan: list[tuple[str, str, int]] = []
    for variant in variants.to_dict("records"):
        for window in windows.to_dict("records"):
            plan.append((str(variant["variant_id"]), str(window["scheme"]), int(window["outer_fold"])))

    print(
        json.dumps(
            {
                "event": "isolated_plan",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "asof_date": args.asof_date,
                "planned_fold_runs": len(plan),
                "variants": variants["variant_id"].astype(str).tolist(),
                "stages": args.stage or ["fixed_config_first"],
                "schemes": sorted(set(windows["scheme"].astype(str))),
                "backend": str(args.backend),
                "logs": str(log_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    if args.dry_run:
        return 0

    failures: list[dict[str, Any]] = []
    for index, (variant_id, scheme, outer_fold) in enumerate(plan, start=1):
        key = (variant_id, scheme, int(outer_fold), int(args.seed), int(args.budget))
        if is_completed(jsonl_path, key):
            print(json.dumps({"event": "skip_completed", "index": index, "total": len(plan), "key": list(key)}, ensure_ascii=False), flush=True)
            continue
        print(json.dumps({"event": "run_fold", "index": index, "total": len(plan), "key": list(key)}, ensure_ascii=False), flush=True)
        completed = False
        if args.backend == "cpu":
            for attempt in range(1, max(1, int(args.max_attempts)) + 1):
                returncode = run_child(
                    args,
                    variant_id=variant_id,
                    scheme=scheme,
                    outer_fold=outer_fold,
                    force_cpu=True,
                    attempt=attempt,
                    log_dir=log_dir,
                )
                if returncode == 0 and is_completed(jsonl_path, key):
                    completed = True
                    break
        else:
            for attempt in range(1, max(1, int(args.max_attempts)) + 1):
                returncode = run_child(
                    args,
                    variant_id=variant_id,
                    scheme=scheme,
                    outer_fold=outer_fold,
                    force_cpu=False,
                    attempt=attempt,
                    log_dir=log_dir,
                )
                if returncode == 0 and is_completed(jsonl_path, key):
                    completed = True
                    break
        if not completed and args.backend == "gpu_with_cpu_retry":
            returncode = run_child(
                args,
                variant_id=variant_id,
                scheme=scheme,
                outer_fold=outer_fold,
                force_cpu=True,
                attempt=1,
                log_dir=log_dir,
            )
            completed = returncode == 0 and is_completed(jsonl_path, key)
        if not completed:
            failures.append({"variant_id": variant_id, "scheme": scheme, "outer_fold": int(outer_fold)})
            print(json.dumps({"event": "fold_failed", "key": list(key)}, ensure_ascii=False), flush=True)

    latest = read_latest_rows(jsonl_path)
    completed_keys = {
        key
        for key, row in latest.items()
        if str(row.get("status")) != "ERROR"
    }
    planned_keys = {(v, s, f, int(args.seed), int(args.budget)) for v, s, f in plan}
    completed_count = len(planned_keys & completed_keys)
    csv_path = report_dir / f"next_round_1457_fixed_matrix_results_{args.asof_date}.csv"
    summary_path = report_dir / f"next_round_1457_fixed_matrix_summary_{args.asof_date}.json"
    write_summary(jsonl_path, csv_path, summary_path, active_variant_ids=set(variants["variant_id"].astype(str)))
    print(
        json.dumps(
            {
                "event": "isolated_done",
                "planned_fold_runs": len(plan),
                "completed_fold_runs": completed_count,
                "failures": failures,
                "summary": str(summary_path),
                "csv": str(csv_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
