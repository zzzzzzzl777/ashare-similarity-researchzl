"""Create findings reports for formal 14:57 next-round model matrices."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ashare_similarity.config import get_default_config


def parse_args() -> argparse.Namespace:
    cfg = get_default_config()
    report_dir = cfg.storage.report_dir / "prediction"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof-date", default="20260513")
    parser.add_argument("--matrix-asof", required=True)
    parser.add_argument("--tier-label", default="Tier-2")
    parser.add_argument(
        "--run-note",
        default="Formal GPU-only matrix screen; it narrows candidates but does not freeze a champion by itself.",
    )
    parser.add_argument("--expected-fold-runs", type=int, default=48)
    parser.add_argument("--expected-backend", default="gpu")
    parser.add_argument("--expected-python", default=".venv5090")
    parser.add_argument("--report-dir", type=Path, default=report_dir)
    return parser.parse_args()


def slugify(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z._-]+", "_", value.strip().lower())
    return text.strip("_") or "matrix"


def round_float(value: Any, digits: int = 6) -> Any:
    try:
        if pd.isna(value):
            return None
        return round(float(value), digits)
    except Exception:
        return value


def table_lines(df: pd.DataFrame, columns: list[str], max_rows: int = 30) -> list[str]:
    if df.empty:
        return ["No rows."]
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in df.head(max_rows).to_dict("records"):
        values: list[str] = []
        for col in columns:
            value = row.get(col)
            if isinstance(value, float):
                values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def classify_status(df: pd.DataFrame) -> pd.Series:
    status = df.get("status", pd.Series([""] * len(df))).astype(str).str.lower()
    return status.isin({"ok", "completed", "complete", "success"})


def load_clean_matrix(csv_path: Path, jsonl_path: Path) -> pd.DataFrame:
    jsonl_rows: list[dict[str, Any]] = []
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                jsonl_rows.append(json.loads(line))
    if jsonl_rows:
        df = pd.DataFrame(jsonl_rows)
    else:
        df = pd.read_csv(csv_path)
    key_cols = ["variant_id", "scheme", "outer_fold", "seed", "budget"]
    df = df.sort_values(["variant_id", "scheme", "outer_fold"]).drop_duplicates(key_cols, keep="last")
    ok = classify_status(df)
    return df[ok].copy()


def aggregate(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    return (
        df.groupby(group_cols, dropna=False)
        .agg(
            folds=("outer_fold", "count"),
            mean_wilson95=("wilson_95", "mean"),
            min_wilson95=("wilson_95", "min"),
            std_wilson95=("wilson_95", "std"),
            mean_accuracy=("confident_accuracy", "mean"),
            min_accuracy=("confident_accuracy", "min"),
            total_candidates=("confident_count", "sum"),
            mean_candidates=("confident_count", "mean"),
            p0_selected_total=("p0_selected_count", "sum"),
        )
        .reset_index()
        .sort_values(["mean_wilson95", "min_wilson95"], ascending=False)
    )


def build_decision(
    combo_agg: pd.DataFrame,
    variant_agg: pd.DataFrame,
    scheme_agg: pd.DataFrame,
    tier_label: str,
) -> dict[str, Any]:
    top_combo = combo_agg.iloc[0].to_dict() if not combo_agg.empty else {}
    top_variant = variant_agg.iloc[0].to_dict() if not variant_agg.empty else {}
    top_scheme = scheme_agg.iloc[0].to_dict() if not scheme_agg.empty else {}
    fixed_recent = combo_agg[combo_agg["scheme"].astype(str).eq("fixed_recent_36m")]
    stable_source = fixed_recent if not fixed_recent.empty else combo_agg
    stable_sorted = stable_source.sort_values(["min_wilson95", "mean_wilson95"], ascending=False)
    stable_combo = stable_sorted.iloc[0].to_dict() if not stable_sorted.empty else top_combo
    return {
        "matrix_leader": {
            "variant_id": top_combo.get("variant_id"),
            "scheme": top_combo.get("scheme"),
            "mean_wilson95": round_float(top_combo.get("mean_wilson95")),
            "min_wilson95": round_float(top_combo.get("min_wilson95")),
            "folds": int(top_combo.get("folds") or 0),
        },
        "best_variant_family": {
            "variant_id": top_variant.get("variant_id"),
            "mean_wilson95": round_float(top_variant.get("mean_wilson95")),
            "min_wilson95": round_float(top_variant.get("min_wilson95")),
        },
        "best_time_window_scheme": {
            "scheme": top_scheme.get("scheme"),
            "mean_wilson95": round_float(top_scheme.get("mean_wilson95")),
            "min_wilson95": round_float(top_scheme.get("min_wilson95")),
        },
        "stable_window_candidate": {
            "variant_id": stable_combo.get("variant_id"),
            "scheme": stable_combo.get("scheme"),
            "mean_wilson95": round_float(stable_combo.get("mean_wilson95")),
            "min_wilson95": round_float(stable_combo.get("min_wilson95")),
        },
        "interpretation": [
            f"{tier_label} is a formal GPU-only matrix run, not a final champion freeze unless explicitly labeled frozen.",
            "A single month such as 2026-04 is not enough to select a model; mean, worst-fold, and stability must all be used.",
            "Q1 and April remain seen-research only and must not feed training, feature selection, calibration, thresholding, or HPO.",
        ],
    }


def audit_inputs(df: pd.DataFrame, args: argparse.Namespace) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    rows = len(df)
    issues.append(
        {
            "level": "P1",
            "code": "expected_fold_rows",
            "status": "PASS" if rows >= args.expected_fold_runs else "FAIL",
            "detail": f"Completed fold rows {rows}/{args.expected_fold_runs}.",
        }
    )
    p0_total = int(pd.to_numeric(df.get("p0_selected_count", 0), errors="coerce").fillna(0).sum())
    issues.append(
        {
            "level": "P0",
            "code": "no_p0_selected",
            "status": "PASS" if p0_total == 0 else "FAIL",
            "detail": f"P0 selected total {p0_total}.",
        }
    )
    backends = sorted(set(df.get("compute_backend", pd.Series(dtype=str)).dropna().astype(str)))
    backend_ok = len(backends) == 1 and (not args.expected_backend or backends[0] == args.expected_backend)
    issues.append(
        {
            "level": "P0",
            "code": "single_expected_backend",
            "status": "PASS" if backend_ok else "FAIL",
            "detail": f"Backends {backends}; expected {args.expected_backend}.",
        }
    )
    pythons = sorted(set(df.get("python_executable", pd.Series(dtype=str)).dropna().astype(str)))
    expected_python = str(args.expected_python or "").lower()
    python_ok = len(pythons) == 1 and (not expected_python or expected_python in pythons[0].lower())
    issues.append(
        {
            "level": "P0",
            "code": "single_expected_python",
            "status": "PASS" if python_ok else "FAIL",
            "detail": f"Python envs {pythons}; expected contains {args.expected_python}.",
        }
    )
    if "model_bundle_validation_passed" in df.columns:
        failed_bundles = df[df["model_bundle_validation_passed"].astype(str).str.lower().isin({"false", "0", "nan"})]
    else:
        failed_bundles = pd.DataFrame()
    issues.append(
        {
            "level": "P1",
            "code": "bundle_validation_passed",
            "status": "PASS" if failed_bundles.empty else "FAIL",
            "detail": f"Rows with failed bundle validation {len(failed_bundles)}.",
        }
    )
    return issues


def main() -> int:
    args = parse_args()
    csv_path = args.report_dir / f"next_round_1457_fixed_matrix_results_{args.matrix_asof}.csv"
    audit_json = args.report_dir / f"next_round_1457_output_audit_{args.matrix_asof}.json"
    jsonl_path = args.report_dir / f"next_round_1457_fixed_matrix_results_{args.matrix_asof}.jsonl"
    if not csv_path.exists() and not jsonl_path.exists():
        raise SystemExit(f"Missing matrix CSV/JSONL: {csv_path} / {jsonl_path}")
    fixed = load_clean_matrix(csv_path, jsonl_path)
    combo_agg = aggregate(fixed, ["variant_id", "scheme"])
    variant_agg = aggregate(fixed, ["variant_id"])
    scheme_agg = aggregate(fixed, ["scheme"])
    fold_agg = aggregate(fixed, ["outer_fold", "outer_valid_start", "outer_valid_end"])
    worst_rows = fixed.sort_values(["wilson_95", "confident_accuracy"], ascending=True).head(20).copy()
    issues = audit_inputs(fixed, args)
    audit_payload = json.loads(audit_json.read_text(encoding="utf-8")) if audit_json.exists() else {}
    decision = build_decision(combo_agg, variant_agg, scheme_agg, args.tier_label)
    report_slug = slugify(args.tier_label)

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tier_label": args.tier_label,
        "run_note": args.run_note,
        "matrix_asof": args.matrix_asof,
        "input_csv": str(csv_path),
        "input_jsonl": str(jsonl_path),
        "external_audit": {
            "path": str(audit_json),
            "p0_fail_count": audit_payload.get("p0_fail_count"),
            "p1_fail_count": audit_payload.get("p1_fail_count"),
            "wip_count": audit_payload.get("wip_count"),
        },
        "self_audit_issues": issues,
        "decision": decision,
        "combo_leaderboard": combo_agg.to_dict("records"),
        "variant_aggregate": variant_agg.to_dict("records"),
        "scheme_aggregate": scheme_agg.to_dict("records"),
        "outer_fold_aggregate": fold_agg.to_dict("records"),
        "worst_rows": worst_rows.to_dict("records"),
    }
    json_path = args.report_dir / f"next_round_1457_{report_slug}_findings_{args.matrix_asof}.json"
    md_path = REPO_ROOT / "docs" / f"next_round_1457_{report_slug}_findings_{args.matrix_asof}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        f"# 14:57 Next-Round {args.tier_label} Findings ({args.matrix_asof})",
        "",
        f"- Created at: {payload['created_at']}",
        f"- Completed matrix rows: {len(fixed)}",
        f"- Source CSV: `{csv_path}`",
        f"- External audit: P0={payload['external_audit'].get('p0_fail_count')}, P1={payload['external_audit'].get('p1_fail_count')}, WIP={payload['external_audit'].get('wip_count')}",
        "",
        "## Decision Snapshot",
        "",
        f"- Matrix leader: `{decision['matrix_leader'].get('variant_id')} + {decision['matrix_leader'].get('scheme')}`; mean Wilson95={decision['matrix_leader'].get('mean_wilson95')}, worst={decision['matrix_leader'].get('min_wilson95')}.",
        f"- Best variant family: `{decision['best_variant_family'].get('variant_id')}`.",
        f"- Best time-window scheme: `{decision['best_time_window_scheme'].get('scheme')}`.",
        f"- Stable window candidate: `{decision['stable_window_candidate'].get('variant_id')} + {decision['stable_window_candidate'].get('scheme')}`.",
        f"- {args.run_note}",
        "",
        "## Self Audit",
        "",
        "| level | code | status | detail |",
        "|---|---|---|---|",
    ]
    for issue in issues:
        lines.append(f"| {issue['level']} | {issue['code']} | {issue['status']} | {issue['detail']} |")
    lines.extend(
        [
            "",
            "## Combo Leaderboard",
            "",
            *table_lines(
                combo_agg,
                [
                    "variant_id",
                    "scheme",
                    "folds",
                    "mean_wilson95",
                    "min_wilson95",
                    "std_wilson95",
                    "mean_accuracy",
                    "total_candidates",
                    "p0_selected_total",
                ],
                max_rows=30,
            ),
            "",
            "## Variant Aggregate",
            "",
            *table_lines(
                variant_agg,
                ["variant_id", "folds", "mean_wilson95", "min_wilson95", "std_wilson95", "mean_accuracy", "total_candidates", "p0_selected_total"],
            ),
            "",
            "## Time-Window Aggregate",
            "",
            *table_lines(
                scheme_agg,
                ["scheme", "folds", "mean_wilson95", "min_wilson95", "std_wilson95", "mean_accuracy", "total_candidates", "p0_selected_total"],
            ),
            "",
            "## Worst Rows",
            "",
            *table_lines(
                worst_rows,
                ["variant_id", "scheme", "outer_fold", "outer_valid_start", "outer_valid_end", "wilson_95", "confident_accuracy", "confident_count", "p0_selected_count"],
                max_rows=20,
            ),
            "",
            "## Interpretation",
            "",
            "- Do not use 2026-04 single-month accuracy as the champion selector; it is only a seen-research stress window.",
            "- Prefer candidates that keep the worst rolling fold high while preserving enough candidates for daily topK use.",
            "- Treat `new_5min_family_only` as evidence that the C174-C188 family has standalone signal; final selection still needs add/delete against the full A matrix.",
            "- Continue with explicit B-proxy feature columns before any B-policy champion attempt; do not reuse same-name T-day moneyflow/CYQ fields.",
            "",
            "## Next Actions",
            "",
            "1. Expand the leading combos to full rolling folds and multi-seed/HPO only after this audit is clean.",
            "2. Run family add/delete and beam search on all engineerable factors, including C174-C188.",
            "3. Freeze 1-3 champion/challenger bundles and score Q1/April as seen-research only.",
            "4. Use future post-freeze months as the only final-forward gate.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    p0_fail = [i for i in issues if i["level"] == "P0" and i["status"] == "FAIL"]
    p1_fail = [i for i in issues if i["level"] == "P1" and i["status"] == "FAIL"]
    print(json.dumps({"json": str(json_path), "md": str(md_path), "p0_fail": len(p0_fail), "p1_fail": len(p1_fail)}, ensure_ascii=False, indent=2))
    return 1 if p0_fail or p1_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
