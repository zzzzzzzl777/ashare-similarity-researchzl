"""Freeze the stability-first 14:57 champion candidate.

This is intentionally separate from the historical PhaseC/S2 bundle scripts.
It reuses the next-round factor protocol and matrix manifest, trains exactly
one selected champion variant on the frozen training window, and writes a
self-audited handoff row for the resulting bundle.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

from run_1457_next_round_fixed_matrix import (
    build_exclusion,
    effective_include_factor_ids,
    force_feature_cache,
    wilson_lower,
)


def parse_args() -> argparse.Namespace:
    cfg = get_default_config()
    report_dir = cfg.storage.report_dir / "prediction"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof-date", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--variant-id", default="pre_new_A_engineerable_control")
    parser.add_argument(
        "--factor-csv",
        type=Path,
        default=report_dir / "next_round_1457_factor_source_discovery_20260513.csv",
    )
    parser.add_argument(
        "--matrix-csv",
        type=Path,
        default=report_dir / "next_round_1457_model_matrix_manifest_20260513.csv",
    )
    parser.add_argument("--feature-cache", type=Path, default=None)
    parser.add_argument("--train-start", default="2023-01-01")
    parser.add_argument("--train-end", default="2025-12-31")
    parser.add_argument("--test-start", default="2026-05-06")
    parser.add_argument("--test-end", default="2026-05-11")
    parser.add_argument("--frozen-at", default="2026-05-02")
    parser.add_argument("--lockbox-role", default="final_unseen")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budget", type=int, default=260)
    parser.add_argument("--train-rows", type=int, default=300_000)
    parser.add_argument("--test-rows", type=int, default=60_000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime, Path)):
        return str(value)
    raise TypeError(type(value).__name__)


def _load_variant(matrix_df: pd.DataFrame, variant_id: str) -> dict[str, Any]:
    matches = matrix_df[matrix_df["variant_id"].astype(str).eq(variant_id)]
    if matches.empty:
        raise SystemExit(f"variant_id not found in matrix manifest: {variant_id}")
    return matches.iloc[0].to_dict()


def _audit_row(row: dict[str, Any], *, frozen_at: date, forbid_seen_train_end: date) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    def add(level: str, code: str, status: str, detail: str) -> None:
        issues.append({"level": level, "code": code, "status": status, "detail": detail})

    status = str(row.get("status") or "")
    add("P0", "run_completed", "PASS" if status == "completed" else "FAIL", f"status={status}")

    backend = str(row.get("compute_backend") or "")
    add("P0", "strict_gpu_backend", "PASS" if backend == "gpu" else "FAIL", f"compute_backend={backend}")

    py = str(row.get("python_executable") or "")
    add("P0", "expected_python_env", "PASS" if ".venv5090" in py else "FAIL", py)

    lockbox = str(row.get("lockbox_role") or "")
    test_start = date.fromisoformat(str(row.get("test_start"))[:10])
    add(
        "P0",
        "final_unseen_after_freeze",
        "PASS" if lockbox == "final_unseen" and test_start > frozen_at else "FAIL",
        f"lockbox={lockbox}; test_start={test_start}; frozen_at={frozen_at}",
    )

    train_end = date.fromisoformat(str(row.get("train_end"))[:10])
    add(
        "P0",
        "q1_april_not_in_train",
        "PASS" if train_end <= forbid_seen_train_end else "FAIL",
        f"train_end={train_end}; max_allowed={forbid_seen_train_end}",
    )

    p0_count = int(row.get("p0_selected_count") or 0)
    add("P0", "p0_selected_zero", "PASS" if p0_count == 0 else "FAIL", f"p0_selected_count={p0_count}")

    bundle_pass = bool(row.get("model_bundle_validation_passed"))
    add("P0", "bundle_self_validation", "PASS" if bundle_pass else "FAIL", str(row.get("model_bundle_validation")))

    bundle_path = Path(str(row.get("model_bundle_path") or ""))
    add("P0", "bundle_exists", "PASS" if bundle_path.exists() else "FAIL", str(bundle_path))

    count = int(row.get("confident_count") or 0)
    add("P1", "forward_sample_nonempty", "PASS" if count > 0 else "FAIL", f"confident_count={count}")

    return issues


def main() -> int:
    args = parse_args()
    cfg = get_default_config()
    out_dir = cfg.storage.report_dir / "prediction"
    out_dir.mkdir(parents=True, exist_ok=True)

    factor_df = pd.read_csv(args.factor_csv)
    matrix_df = pd.read_csv(args.matrix_csv)
    variant = _load_variant(matrix_df, args.variant_id)
    include_ids, variant_audit = effective_include_factor_ids(variant, matrix_df)
    exclude_features, exclusion_audit = build_exclusion(
        factor_df=factor_df,
        include_factor_ids=include_ids,
        include_b_policy=bool(variant.get("include_b_policy")),
    )
    if args.feature_cache:
        force_feature_cache(args.feature_cache)

    train_start = date.fromisoformat(args.train_start)
    train_end = date.fromisoformat(args.train_end)
    test_start = date.fromisoformat(args.test_start)
    test_end = date.fromisoformat(args.test_end)
    frozen_at = date.fromisoformat(args.frozen_at)

    planned = {
        "variant_id": args.variant_id,
        "train_start": train_start,
        "train_end": train_end,
        "test_start": test_start,
        "test_end": test_end,
        "frozen_at": frozen_at,
        "lockbox_role": args.lockbox_role,
        "seed": args.seed,
        "budget": args.budget,
        "effective_include_factor_count": len(include_ids),
        "excluded_feature_count": len(exclude_features),
        "feature_cache": str(args.feature_cache) if args.feature_cache else None,
    }
    print(json.dumps(planned, ensure_ascii=False, indent=2, default=_json_default), flush=True)
    if args.dry_run:
        return 0

    config = GpuProbeConfig(
        start=train_start,
        train_end=train_end,
        test_start=test_start,
        end=test_end,
        train_rows=args.train_rows,
        test_rows=args.test_rows,
        seed=args.seed,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=args.budget,
        min_phase_days_3=1,
        selector_coverage_weight=0.02,
        candidate_family="all",
        lockbox_role=args.lockbox_role,
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=exclude_features,
        use_feature_cache=True,
        refresh_feature_cache=False,
        force_cpu=False,
    )

    store = LocalDataStore(cfg)
    started = time.perf_counter()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.perf_counter() - started

    fs = result.get("feature_selection") or {}
    selected = list(fs.get("selected_features") or [])
    p0_selected = sorted(set(selected) & set(exclude_features))
    artifacts = result.get("artifacts") or {}
    bundle_validation = result.get("model_bundle_validation") or {}
    force_cpu = bool(result.get("force_cpu"))
    device = str(result.get("device") or ("cpu" if force_cpu else "unknown"))
    compute_backend = "cpu" if force_cpu or device == "cpu" else "gpu"
    confident_acc = result.get("confident_accuracy")
    confident_count = int(result.get("confident_count") or 0)
    run_dir = Path(artifacts["run_dir"]) if artifacts.get("run_dir") else None

    row: dict[str, Any] = {
        "asof_date": args.asof_date,
        "variant_id": args.variant_id,
        "role": "champion_candidate_freeze",
        "train_start": str(train_start),
        "train_end": str(train_end),
        "test_start": str(test_start),
        "test_end": str(test_end),
        "frozen_at": str(frozen_at),
        "seed": int(args.seed),
        "budget": int(args.budget),
        "elapsed_s": round(elapsed, 3),
        "status": result.get("status", "unknown"),
        "model": result.get("model"),
        "model_kind": result.get("model_kind"),
        "compute_backend": compute_backend,
        "device": device,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "gpu_scope": result.get("gpu_scope"),
        "gpu_enabled": bool(result.get("gpu_enabled")),
        "force_cpu": force_cpu,
        "lockbox_role": result.get("lockbox_role"),
        "final_acceptance_eligible": bool(result.get("final_acceptance_eligible")),
        "run_id": result.get("run_id"),
        "run_dir": str(run_dir) if run_dir else None,
        "artifact_path": artifacts.get("artifact"),
        "test_predictions_path": artifacts.get("test_predictions"),
        "model_bundle_path": str(run_dir / "model_bundle.pt") if run_dir else None,
        "model_bundle_status": result.get("model_bundle_status"),
        "model_bundle_validation_passed": bool(bundle_validation.get("passed")),
        "model_bundle_validation": bundle_validation,
        "confident_accuracy": confident_acc,
        "confident_count": confident_count,
        "confident_coverage": result.get("confident_coverage"),
        "wilson_95": wilson_lower(confident_acc, confident_count),
        "brier": result.get("brier"),
        "baseline_brier": result.get("baseline_brier"),
        "selected_feature_count": len(selected),
        "p0_selected_count": len(p0_selected),
        "p0_selected": p0_selected,
        "selected_features": selected,
        "feature_cache": (result.get("feature_cache") or {}).get("path"),
        "variant_audit": variant_audit,
        "exclusion_audit": exclusion_audit,
    }
    row["self_audit_issues"] = _audit_row(
        row,
        frozen_at=frozen_at,
        forbid_seen_train_end=date(2025, 12, 31),
    )

    stem = f"next_round_1457_champion_freeze_{args.asof_date}_{args.variant_id}"
    json_path = out_dir / f"{stem}.json"
    csv_path = out_dir / f"{stem}.csv"
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    flat = {k: v for k, v in row.items() if k not in {"selected_features", "p0_selected", "variant_audit", "exclusion_audit", "model_bundle_validation", "self_audit_issues"}}
    flat["selected_features_json"] = json.dumps(selected, ensure_ascii=False)
    flat["p0_selected_json"] = json.dumps(p0_selected, ensure_ascii=False)
    pd.DataFrame([flat]).to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(json.dumps({"json": str(json_path), "csv": str(csv_path), "audit": row["self_audit_issues"]}, ensure_ascii=False, indent=2, default=_json_default), flush=True)
    return 0 if all(item["status"] == "PASS" for item in row["self_audit_issues"] if item["level"] == "P0") else 1


if __name__ == "__main__":
    raise SystemExit(main())
