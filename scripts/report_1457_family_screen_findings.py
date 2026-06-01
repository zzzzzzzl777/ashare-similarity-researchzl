"""Report stability-first findings for the 14:57 Tier-4 family screen."""
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
    parser.add_argument("--matrix-asof", required=True)
    parser.add_argument("--baseline-asof", default="20260513_tier3_full36_gpu_v1")
    parser.add_argument("--baseline-variant", default="pre_new_A_engineerable_control")
    parser.add_argument("--expected-fold-runs", type=int, default=60)
    parser.add_argument("--expected-backend", default="gpu")
    parser.add_argument("--expected-python", default=".venv5090")
    parser.add_argument("--screen-fold", action="append", type=int, default=[])
    parser.add_argument(
        "--mean-tolerance",
        type=float,
        default=0.001,
        help="Allowed mean Wilson drawdown for a stability-tradeoff candidate.",
    )
    parser.add_argument(
        "--accuracy-tolerance",
        type=float,
        default=0.002,
        help="Allowed mean accuracy drawdown for a stability-tradeoff candidate.",
    )
    parser.add_argument("--report-dir", type=Path, default=report_dir)
    return parser.parse_args()


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


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    for col in ["wilson_95", "confident_accuracy", "confident_count", "p0_selected_count"]:
        work[col] = numeric(work, col)
    return (
        work.groupby(["variant_id", "scheme"], dropna=False)
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
    )


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


def audit_rows(df: pd.DataFrame, args: argparse.Namespace) -> list[dict[str, Any]]:
    ok = df[ok_mask(df)].copy()
    issues: list[dict[str, Any]] = []
    issues.append(
        {
            "level": "P1",
            "code": "expected_screen_rows",
            "status": "PASS" if len(ok) >= args.expected_fold_runs else "FAIL",
            "detail": f"Completed rows {len(ok)}/{args.expected_fold_runs}.",
        }
    )
    errors = len(df[~ok_mask(df)])
    issues.append(
        {
            "level": "P0",
            "code": "no_error_rows",
            "status": "PASS" if errors == 0 else "FAIL",
            "detail": f"Non-completed rows {errors}.",
        }
    )
    p0_total = int(numeric(ok, "p0_selected_count").sum()) if not ok.empty else 0
    issues.append(
        {
            "level": "P0",
            "code": "no_p0_selected",
            "status": "PASS" if p0_total == 0 else "FAIL",
            "detail": f"P0 selected total {p0_total}.",
        }
    )
    backends = sorted(set(ok.get("compute_backend", pd.Series(dtype=str)).dropna().astype(str)))
    backend_ok = len(backends) == 1 and (not args.expected_backend or backends[0] == args.expected_backend)
    issues.append(
        {
            "level": "P0",
            "code": "single_expected_backend",
            "status": "PASS" if backend_ok else "FAIL",
            "detail": f"Backends {backends}; expected {args.expected_backend}.",
        }
    )
    pythons = sorted(set(ok.get("python_executable", pd.Series(dtype=str)).dropna().astype(str)))
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
    screen_raw = load_rows(args.report_dir, args.matrix_asof)
    screen_ok = screen_raw[ok_mask(screen_raw)].copy()
    folds = sorted({int(fold) for fold in (args.screen_fold or screen_ok["outer_fold"].dropna().astype(int).tolist())})

    baseline_raw = load_rows(args.report_dir, args.baseline_asof)
    baseline_ok = baseline_raw[
        ok_mask(baseline_raw)
        & baseline_raw["variant_id"].astype(str).eq(args.baseline_variant)
        & baseline_raw["outer_fold"].astype(int).isin(folds)
    ].copy()
    if baseline_ok.empty:
        raise SystemExit("Missing baseline rows for the selected screen folds.")

    screen_agg = aggregate(screen_ok)
    baseline_agg = aggregate(baseline_ok)
    base = baseline_agg.iloc[0].to_dict()
    for col in ["mean_wilson95", "min_wilson95", "std_wilson95", "mean_accuracy", "total_candidates"]:
        screen_agg[f"delta_{col}"] = pd.to_numeric(screen_agg[col], errors="coerce") - float(base[col])
    screen_agg["needs_full_23fold"] = True
    screen_agg["strict_candidate"] = (
        (screen_agg["p0_selected_total"].eq(0))
        & (screen_agg["mean_wilson95"].ge(float(base["mean_wilson95"])))
        & (screen_agg["min_wilson95"].ge(float(base["min_wilson95"])))
    )
    screen_agg["stability_tradeoff_candidate"] = (
        (screen_agg["p0_selected_total"].eq(0))
        & (~screen_agg["strict_candidate"])
        & (screen_agg["delta_mean_wilson95"].ge(-float(args.mean_tolerance)))
        & (screen_agg["delta_min_wilson95"].ge(0))
        & (screen_agg["delta_mean_accuracy"].ge(-float(args.accuracy_tolerance)))
    )
    screen_agg["full_23fold_candidate"] = screen_agg["strict_candidate"] | screen_agg["stability_tradeoff_candidate"]
    screen_agg["candidate_type"] = "screen_only"
    screen_agg.loc[screen_agg["stability_tradeoff_candidate"], "candidate_type"] = "stability_tradeoff_candidate"
    screen_agg.loc[screen_agg["strict_candidate"], "candidate_type"] = "strict_candidate"
    screen_agg = screen_agg.sort_values(
        ["full_23fold_candidate", "min_wilson95", "mean_wilson95", "std_wilson95"],
        ascending=[False, False, False, True],
    )
    candidates = screen_agg[screen_agg["full_23fold_candidate"]].head(4).copy()
    stable_candidate = candidates.iloc[0].to_dict() if not candidates.empty else screen_agg.iloc[0].to_dict()
    worst_rows = pd.concat([screen_ok, baseline_ok], ignore_index=True).sort_values(
        ["wilson_95", "confident_accuracy"], ascending=True
    )
    issues = audit_rows(screen_raw, args)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "matrix_asof": args.matrix_asof,
        "baseline_asof": args.baseline_asof,
        "baseline_variant": args.baseline_variant,
        "screen_folds": folds,
        "self_audit_issues": issues,
        "baseline_screen_reference": base,
        "candidate_tolerances": {
            "mean_wilson95_drawdown": args.mean_tolerance,
            "mean_accuracy_drawdown": args.accuracy_tolerance,
        },
        "stable_candidate": stable_candidate,
        "candidate_variants_requiring_full_23fold": candidates.to_dict("records"),
        "leaderboard": screen_agg.to_dict("records"),
        "worst_rows": worst_rows.head(30).to_dict("records"),
        "policy": {
            "phasec_role": "old_baseline_risk_reference_only",
            "q1_april_role": "seen_research_consistency_check_after_freeze_only",
            "tier4_role": "family_screen_only_no_champion_promotion",
        },
    }
    json_path = args.report_dir / f"next_round_1457_family_screen_findings_{args.matrix_asof}.json"
    md_path = REPO_ROOT / "docs" / f"next_round_1457_family_screen_findings_{args.matrix_asof}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        f"# 14:57 Tier-4 Family Stability Screen ({args.matrix_asof})",
        "",
        f"- Created at: {payload['created_at']}",
        f"- Screen folds: `{folds}`",
        f"- Baseline reference: `{args.baseline_variant}` from `{args.baseline_asof}` on the same folds.",
        f"- Stability-tradeoff tolerance: mean Wilson drawdown <= `{args.mean_tolerance}`, mean accuracy drawdown <= `{args.accuracy_tolerance}`.",
        "- Role: family screen only; no champion can be promoted from this 4-fold result.",
        "- Q1/April: not used for this screen and not allowed for model selection.",
        "",
        "## Baseline Reference",
        "",
        *table_lines(pd.DataFrame([base]), ["variant_id", "scheme", "folds", "mean_wilson95", "min_wilson95", "std_wilson95", "mean_accuracy", "total_candidates", "p0_selected_total"], 1),
        "",
        "## Stable Candidate",
        "",
        f"- Candidate: `{stable_candidate.get('variant_id')}`; mean={float(stable_candidate.get('mean_wilson95', 0)):.6f}, min={float(stable_candidate.get('min_wilson95', 0)):.6f}, std={float(stable_candidate.get('std_wilson95', 0)):.6f}.",
        f"- Candidate type: `{stable_candidate.get('candidate_type')}`.",
        "- Candidate status means only: eligible for complete 23-fold rolling validation.",
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
            "## Leaderboard",
            "",
            *table_lines(
                screen_agg,
                [
                    "variant_id",
                    "folds",
                    "mean_wilson95",
                    "min_wilson95",
                    "std_wilson95",
                    "mean_accuracy",
                    "total_candidates",
                    "delta_mean_wilson95",
                    "delta_min_wilson95",
                    "strict_candidate",
                    "stability_tradeoff_candidate",
                    "candidate_type",
                    "needs_full_23fold",
                ],
                40,
            ),
            "",
            "## Worst-Window Rows",
            "",
            *table_lines(
                worst_rows,
                ["variant_id", "outer_fold", "outer_valid_start", "outer_valid_end", "wilson_95", "confident_accuracy", "confident_count", "p0_selected_count"],
                30,
            ),
            "",
            "## Risk Notes",
            "",
            "- This screen deliberately uses known weak rolling folds plus the latest fold to reduce single-window optimism.",
            "- It still has only 4 folds, so any positive family result must run complete 23-fold fixed_recent_36m rolling before champion consideration.",
            "- PhaseC, Q1, and April do not participate in selection; Q1/April are only post-freeze seen-research consistency checks.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    p0_fail = [i for i in issues if i["level"] == "P0" and i["status"] == "FAIL"]
    p1_fail = [i for i in issues if i["level"] == "P1" and i["status"] == "FAIL"]
    print(json.dumps({"json": str(json_path), "md": str(md_path), "p0_fail": len(p0_fail), "p1_fail": len(p1_fail)}, ensure_ascii=False, indent=2))
    return 1 if p0_fail or p1_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
