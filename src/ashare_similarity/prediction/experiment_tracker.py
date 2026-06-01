"""Lightweight utilities for listing and comparing past prediction runs.

The heavy lifting (artifact writing, lockbox ledger, latest pointers) lives in
gpu_probe._write_gpu_probe_artifacts.  This module only *reads* those artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_REPORT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")


def list_runs(
    report_dir: Path = _DEFAULT_REPORT_DIR,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return summaries of the most recent *limit* runs, newest first."""
    runs_dir = report_dir / "runs"
    if not runs_dir.is_dir():
        return []

    summaries: list[dict[str, Any]] = []
    for run_dir in sorted(runs_dir.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        metrics_path = run_dir / "metrics.json"
        if not metrics_path.exists():
            continue
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        summaries.append(
            {
                "run_id": run_dir.name,
                "run_dir": str(run_dir),
                **_extract_key_metrics(metrics),
            }
        )
        if len(summaries) >= limit:
            break
    return summaries


def compare_runs(
    run_ids: list[str],
    report_dir: Path = _DEFAULT_REPORT_DIR,
) -> list[dict[str, Any]]:
    """Load key metrics for specific *run_ids* for side-by-side comparison."""
    results: list[dict[str, Any]] = []
    for rid in run_ids:
        metrics_path = report_dir / "runs" / rid / "metrics.json"
        if not metrics_path.exists():
            results.append({"run_id": rid, "error": "not found"})
            continue
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            results.append({"run_id": rid, "error": str(exc)})
            continue
        results.append({"run_id": rid, **_extract_key_metrics(metrics)})
    return results


def load_artifact(
    run_id: str,
    report_dir: Path = _DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    """Load the full artifact.json for a single run."""
    path = report_dir / "runs" / run_id / "artifact.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_key_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    get = metrics.get
    return {
        "accuracy": get("accuracy"),
        "high_conf_accuracy": get("high_conf_accuracy"),
        "high_conf_count": get("high_conf_count"),
        "high_conf_coverage": get("high_conf_coverage"),
        "wilson_95_lower": get("wilson_95_lower"),
        "brier": get("brier"),
        "auc": get("auc"),
        "acceptance_passed": get("acceptance_passed"),
    }
