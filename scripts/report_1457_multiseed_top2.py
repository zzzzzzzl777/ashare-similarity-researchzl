"""Aggregate Top-2 full-rolling results across multiple seeds and sources."""
from __future__ import annotations

import argparse
import json
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


OK_STATUS = {"ok", "completed", "complete", "success"}


def parse_args() -> argparse.Namespace:
    cfg = get_default_config()
    report_dir = cfg.storage.report_dir / "prediction"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--row-source",
        action="append",
        required=True,
        help="Source in the form MATRIX_ASOF|VARIANT_ID|ROLE.",
    )
    parser.add_argument("--scheme", default="fixed_recent_36m")
    parser.add_argument("--expected-folds-per-seed", type=int, default=23)
    parser.add_argument("--expected-seeds", type=int, default=3)
    parser.add_argument("--expected-backend", default="gpu")
    parser.add_argument("--expected-python", default=".venv5090")
    parser.add_argument("--report-name", default="tier6_top2_multiseed")
    parser.add_argument("--report-dir", type=Path, default=report_dir)
    return parser.parse_args()


def parse_source(value: str) -> tuple[str, str, str]:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) != 3 or not all(parts):
        raise SystemExit(f"Invalid --row-source {value!r}; expected MATRIX_ASOF|VARIANT_ID|ROLE.")
    return parts[0], parts[1], parts[2]


def load_rows(report_dir: Path, matrix_asof: str) -> pd.DataFrame:
    jsonl_path = report_dir / f"next_round_1457_fixed_matrix_results_{matrix_asof}.jsonl"
    csv_path = report_dir / f"next_round_1457_fixed_matrix_results_{matrix_asof}.csv"
    rows: list[dict[str, Any]] = []
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        df = pd.DataFrame(rows)
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        raise SystemExit(f"Missing matrix rows: {jsonl_path} / {csv_path}")
    key_cols = ["variant_id", "scheme", "outer_fold", "seed", "budget"]
    return df.sort_values(key_cols).drop_duplicates(key_cols, keep="last").copy()


def ok_mask(df: pd.DataFrame) -> pd.Series:
    return df.get("status", pd.Series([""] * len(df))).astype(str).str.lower().isin(OK_STATUS)


def numeric(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col not in df.columns:
        return pd.Series([default] * len(df), index=df.index)
    return pd.to_numeric(df[col], errors="coerce").fillna(default)


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


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["wilson_95", "confident_accuracy", "confident_count", "confident_coverage", "p0_selected_count"]:
        df[col] = numeric(df, col)
    return (
        df.groupby(["role", "variant_id", "scheme"], dropna=False)
        .agg(
            seeds=("seed", lambda s: ",".join(str(int(x)) for x in sorted(set(pd.to_numeric(s, errors="coerce").dropna())))),
            seed_count=("seed", lambda s: len(set(pd.to_numeric(s, errors="coerce").dropna().astype(int)))),
            fold_runs=("outer_fold", "count"),
            mean_wilson95=("wilson_95", "mean"),
            min_wilson95=("wilson_95", "min"),
            std_wilson95=("wilson_95", "std"),
            mean_accuracy=("confident_accuracy", "mean"),
            min_accuracy=("confident_accuracy", "min"),
            total_candidates=("confident_count", "sum"),
            mean_candidates=("confident_count", "mean"),
            mean_coverage=("confident_coverage", "mean"),
            p0_selected_total=("p0_selected_count", "sum"),
        )
        .reset_index()
    )


def audit_rows(df: pd.DataFrame, leaderboard: pd.DataFrame, args: argparse.Namespace) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    expected_rows = int(args.expected_folds_per_seed) * int(args.expected_seeds)
    incomplete = leaderboard[leaderboard["fold_runs"].astype(int) < expected_rows]
    issues.append(
        {
            "level": "P1",
            "code": "expected_rows_per_variant",
            "status": "PASS" if incomplete.empty else "FAIL",
            "detail": f"Expected {expected_rows} rows per variant; incomplete variants {incomplete[['variant_id','fold_runs']].to_dict('records')}.",
        }
    )
    seed_counts = sorted(set(leaderboard["seed_count"].astype(int))) if not leaderboard.empty else []
    issues.append(
        {
            "level": "P1",
            "code": "expected_seed_count",
            "status": "PASS" if seed_counts == [int(args.expected_seeds)] else "FAIL",
            "detail": f"Seed counts {seed_counts}; expected {args.expected_seeds}.",
        }
    )
    fold_sets = {
        str(row.variant_id): sorted(set(df[df["variant_id"].astype(str).eq(str(row.variant_id))]["outer_fold"].astype(int)))
        for row in leaderboard.itertuples()
    }
    unique_fold_sets = {tuple(v) for v in fold_sets.values()}
    issues.append(
        {
            "level": "P1",
            "code": "same_fold_set",
            "status": "PASS" if len(unique_fold_sets) == 1 else "FAIL",
            "detail": f"Fold sets {fold_sets}.",
        }
    )
    p0_total = int(numeric(df, "p0_selected_count").sum())
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
    return issues


def main() -> int:
    args = parse_args()
    chunks: list[pd.DataFrame] = []
    for source in args.row_source:
        matrix_asof, variant_id, role = parse_source(source)
        raw = load_rows(args.report_dir, matrix_asof)
        part = raw[
            ok_mask(raw)
            & raw["variant_id"].astype(str).eq(variant_id)
            & raw["scheme"].astype(str).eq(str(args.scheme))
        ].copy()
        part["source_asof"] = matrix_asof
        part["role"] = role
        chunks.append(part)
    combined = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    if combined.empty:
        raise SystemExit("No completed rows found for the requested sources.")
    key_cols = ["variant_id", "scheme", "outer_fold", "seed", "budget"]
    combined = combined.sort_values(["variant_id", "seed", "outer_fold", "source_asof"]).drop_duplicates(key_cols, keep="last")
    leaderboard = aggregate(combined)
    stability = leaderboard.sort_values(
        ["p0_selected_total", "min_wilson95", "mean_wilson95", "std_wilson95", "mean_accuracy"],
        ascending=[True, False, False, True, False],
    ).reset_index(drop=True)
    mean_first = leaderboard.sort_values(
        ["p0_selected_total", "mean_wilson95", "min_wilson95", "std_wilson95", "mean_accuracy"],
        ascending=[True, False, False, True, False],
    ).reset_index(drop=True)
    worst_rows = combined.sort_values(["wilson_95", "confident_accuracy"], ascending=True).head(60).copy()
    issues = audit_rows(combined, leaderboard, args)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "report_name": args.report_name,
        "scheme": args.scheme,
        "row_sources": args.row_source,
        "self_audit_issues": issues,
        "stability_first_leaderboard": stability.to_dict("records"),
        "mean_first_leaderboard": mean_first.to_dict("records"),
        "worst_rows": worst_rows.to_dict("records"),
        "policy": {
            "champion_rule": "multi_seed_full_rolling_stability_first",
            "q1_april_role": "post_freeze_seen_research_consistency_only",
            "phasec_role": "old_baseline_risk_reference_only",
        },
    }
    json_path = args.report_dir / f"next_round_1457_{args.report_name}.json"
    md_path = REPO_ROOT / "docs" / f"next_round_1457_{args.report_name}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    top = stability.iloc[0].to_dict()
    mean_top = mean_first.iloc[0].to_dict()
    lines = [
        f"# 14:57 Top2 Multi-Seed Stability Report ({args.report_name})",
        "",
        f"- Created at: {payload['created_at']}",
        f"- Scheme: `{args.scheme}`",
        f"- Expected seeds: `{args.expected_seeds}`; expected folds per seed: `{args.expected_folds_per_seed}`.",
        "- Selection policy: full rolling, multi-seed, stability first; Q1/April are excluded from selection.",
        "",
        "## Decision Snapshot",
        "",
        f"- Stability-first leader: `{top.get('variant_id')}`; seeds={top.get('seeds')}; min={float(top.get('min_wilson95', 0)):.6f}, mean={float(top.get('mean_wilson95', 0)):.6f}, std={float(top.get('std_wilson95', 0)):.6f}.",
        f"- Mean-first leader: `{mean_top.get('variant_id')}`; mean={float(mean_top.get('mean_wilson95', 0)):.6f}, min={float(mean_top.get('min_wilson95', 0)):.6f}.",
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
            "## Stability-First Leaderboard",
            "",
            *table_lines(
                stability,
                [
                    "role",
                    "variant_id",
                    "seeds",
                    "fold_runs",
                    "mean_wilson95",
                    "min_wilson95",
                    "std_wilson95",
                    "mean_accuracy",
                    "total_candidates",
                    "mean_coverage",
                    "p0_selected_total",
                ],
            ),
            "",
            "## Worst-Window Rows",
            "",
            *table_lines(
                worst_rows,
                [
                    "role",
                    "variant_id",
                    "seed",
                    "outer_fold",
                    "outer_valid_start",
                    "outer_valid_end",
                    "wilson_95",
                    "confident_accuracy",
                    "confident_count",
                    "p0_selected_count",
                ],
                60,
            ),
            "",
            "## Risk Notes",
            "",
            "- This report is valid only when P0=0 and the expected row/seed audits pass.",
            "- If a candidate wins min_wilson95 but loses mean outside tolerance, keep it as challenger rather than champion.",
            "- Future final-forward data must remain outside this selection loop.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    p0_fail = [i for i in issues if i["level"] == "P0" and i["status"] == "FAIL"]
    p1_fail = [i for i in issues if i["level"] == "P1" and i["status"] == "FAIL"]
    print(json.dumps({"json": str(json_path), "md": str(md_path), "p0_fail": len(p0_fail), "p1_fail": len(p1_fail)}, ensure_ascii=False, indent=2))
    return 1 if p0_fail or p1_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
