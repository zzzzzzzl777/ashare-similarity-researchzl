"""Compare a full-rolling challenger against the Tier-3 stability baselines."""
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
    parser.add_argument("--challenger-asof", required=True)
    parser.add_argument("--challenger-variant", required=True)
    parser.add_argument("--baseline-asof", default="20260513_tier3_full36_gpu_v1")
    parser.add_argument(
        "--baseline-variant",
        action="append",
        default=["pre_new_A_engineerable_control", "all_A_engineerable"],
    )
    parser.add_argument("--scheme", default="fixed_recent_36m")
    parser.add_argument("--expected-folds", type=int, default=23)
    parser.add_argument("--expected-backend", default="gpu")
    parser.add_argument("--expected-python", default=".venv5090")
    parser.add_argument("--mean-tolerance", type=float, default=0.001)
    parser.add_argument("--accuracy-tolerance", type=float, default=0.002)
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


def prepare_slice(df: pd.DataFrame, *, variant_ids: set[str], scheme: str, source_asof: str, role: str) -> pd.DataFrame:
    out = df[
        ok_mask(df)
        & df["variant_id"].astype(str).isin(variant_ids)
        & df["scheme"].astype(str).eq(scheme)
    ].copy()
    out["source_asof"] = source_asof
    out["role"] = role
    for col in ["wilson_95", "confident_accuracy", "confident_count", "confident_coverage", "p0_selected_count"]:
        out[col] = numeric(out, col)
    return out


def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["role", "source_asof", "variant_id", "scheme"], dropna=False)
        .agg(
            folds=("outer_fold", "count"),
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


def audit_rows(combined: pd.DataFrame, leaderboard: pd.DataFrame, args: argparse.Namespace) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    challenger_rows = combined[combined["role"].eq("challenger")]
    issues.append(
        {
            "level": "P1",
            "code": "challenger_full_fold_count",
            "status": "PASS" if len(challenger_rows) >= args.expected_folds else "FAIL",
            "detail": f"Challenger completed folds {len(challenger_rows)}/{args.expected_folds}.",
        }
    )
    fold_sets = {
        str(row.variant_id): set(combined[combined["variant_id"].astype(str).eq(str(row.variant_id))]["outer_fold"].astype(int))
        for row in leaderboard.itertuples()
    }
    unique_fold_sets = {tuple(sorted(v)) for v in fold_sets.values()}
    issues.append(
        {
            "level": "P1",
            "code": "same_fold_set",
            "status": "PASS" if len(unique_fold_sets) == 1 and len(next(iter(unique_fold_sets), ())) >= args.expected_folds else "FAIL",
            "detail": f"Fold sets {fold_sets}.",
        }
    )
    p0_total = int(numeric(combined, "p0_selected_count").sum())
    issues.append(
        {
            "level": "P0",
            "code": "no_p0_selected",
            "status": "PASS" if p0_total == 0 else "FAIL",
            "detail": f"P0 selected total {p0_total}.",
        }
    )
    backends = sorted(set(combined.get("compute_backend", pd.Series(dtype=str)).dropna().astype(str)))
    backend_ok = len(backends) == 1 and (not args.expected_backend or backends[0] == args.expected_backend)
    issues.append(
        {
            "level": "P0",
            "code": "single_expected_backend",
            "status": "PASS" if backend_ok else "FAIL",
            "detail": f"Backends {backends}; expected {args.expected_backend}.",
        }
    )
    pythons = sorted(set(combined.get("python_executable", pd.Series(dtype=str)).dropna().astype(str)))
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
    baseline_rows = load_rows(args.report_dir, args.baseline_asof)
    challenger_rows = load_rows(args.report_dir, args.challenger_asof)
    baseline = prepare_slice(
        baseline_rows,
        variant_ids={str(v) for v in args.baseline_variant},
        scheme=args.scheme,
        source_asof=args.baseline_asof,
        role="baseline",
    )
    challenger = prepare_slice(
        challenger_rows,
        variant_ids={str(args.challenger_variant)},
        scheme=args.scheme,
        source_asof=args.challenger_asof,
        role="challenger",
    )
    combined = pd.concat([baseline, challenger], ignore_index=True)
    if combined.empty:
        raise SystemExit("No completed comparison rows found.")

    leaderboard = aggregate(combined)
    stable_sorted = leaderboard.sort_values(
        ["p0_selected_total", "min_wilson95", "mean_wilson95", "std_wilson95", "mean_accuracy"],
        ascending=[True, False, False, True, False],
    ).reset_index(drop=True)
    mean_sorted = leaderboard.sort_values(
        ["p0_selected_total", "mean_wilson95", "min_wilson95", "std_wilson95", "mean_accuracy"],
        ascending=[True, False, False, True, False],
    ).reset_index(drop=True)

    stable_baseline = leaderboard[leaderboard["variant_id"].astype(str).eq("pre_new_A_engineerable_control")]
    challenger_agg = leaderboard[leaderboard["variant_id"].astype(str).eq(str(args.challenger_variant))]
    if stable_baseline.empty:
        raise SystemExit("Missing pre_new_A_engineerable_control baseline rows.")
    if challenger_agg.empty:
        raise SystemExit("Missing challenger aggregate rows.")
    base = stable_baseline.iloc[0]
    chal = challenger_agg.iloc[0]
    challenger_decision = {
        "beats_stable_baseline_min": bool(chal["min_wilson95"] > base["min_wilson95"]),
        "within_mean_tolerance": bool(chal["mean_wilson95"] >= base["mean_wilson95"] - float(args.mean_tolerance)),
        "within_accuracy_tolerance": bool(chal["mean_accuracy"] >= base["mean_accuracy"] - float(args.accuracy_tolerance)),
        "p0_clean": bool(chal["p0_selected_total"] == 0),
        "next_step": "eligible_for_multi_seed_or_freeze_gate"
        if (
            chal["min_wilson95"] > base["min_wilson95"]
            and chal["mean_wilson95"] >= base["mean_wilson95"] - float(args.mean_tolerance)
            and chal["mean_accuracy"] >= base["mean_accuracy"] - float(args.accuracy_tolerance)
            and chal["p0_selected_total"] == 0
        )
        else "keep_stable_baseline_or_continue_family_search",
    }

    worst_rows = combined.sort_values(["wilson_95", "confident_accuracy"], ascending=True).head(40).copy()
    issues = audit_rows(combined, leaderboard, args)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "challenger_asof": args.challenger_asof,
        "challenger_variant": args.challenger_variant,
        "baseline_asof": args.baseline_asof,
        "baseline_variants": args.baseline_variant,
        "scheme": args.scheme,
        "self_audit_issues": issues,
        "stability_first_leaderboard": stable_sorted.to_dict("records"),
        "mean_first_leaderboard": mean_sorted.to_dict("records"),
        "challenger_vs_stable_baseline": challenger_decision,
        "worst_rows": worst_rows.to_dict("records"),
        "policy": {
            "champion_rule": "stability_first_full_rolling_only",
            "tier4_role": "screen_only",
            "q1_april_role": "post_freeze_seen_research_consistency_only",
            "phasec_role": "old_baseline_risk_reference_only",
        },
    }
    json_path = args.report_dir / f"next_round_1457_challenger_vs_baselines_{args.challenger_asof}.json"
    md_path = REPO_ROOT / "docs" / f"next_round_1457_challenger_vs_baselines_{args.challenger_asof}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    stable_top = stable_sorted.iloc[0].to_dict()
    mean_top = mean_sorted.iloc[0].to_dict()
    lines = [
        f"# 14:57 Challenger vs Baselines ({args.challenger_asof})",
        "",
        f"- Created at: {payload['created_at']}",
        f"- Challenger: `{args.challenger_variant}` from `{args.challenger_asof}`.",
        f"- Baselines: `{', '.join(args.baseline_variant)}` from `{args.baseline_asof}`.",
        "- Selection policy: fixed_recent_36m full rolling, stability first; Q1/April are not used.",
        "",
        "## Decision Snapshot",
        "",
        f"- Stability-first leader: `{stable_top.get('variant_id')}`; min={float(stable_top.get('min_wilson95', 0)):.6f}, mean={float(stable_top.get('mean_wilson95', 0)):.6f}, std={float(stable_top.get('std_wilson95', 0)):.6f}.",
        f"- Mean-first leader: `{mean_top.get('variant_id')}`; mean={float(mean_top.get('mean_wilson95', 0)):.6f}, min={float(mean_top.get('min_wilson95', 0)):.6f}.",
        f"- Challenger next step: `{challenger_decision['next_step']}`.",
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
                stable_sorted,
                [
                    "role",
                    "variant_id",
                    "folds",
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
                    "outer_fold",
                    "outer_valid_start",
                    "outer_valid_end",
                    "wilson_95",
                    "confident_accuracy",
                    "confident_count",
                    "p0_selected_count",
                ],
                40,
            ),
            "",
            "## Risk Notes",
            "",
            "- This report compares only full 23-fold fixed_recent_36m rows.",
            "- A challenger may proceed only if it improves tail stability without unacceptable mean/accuracy drawdown and with P0=0.",
            "- PhaseC, Q1, and April remain outside the selection loop.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    p0_fail = [i for i in issues if i["level"] == "P0" and i["status"] == "FAIL"]
    p1_fail = [i for i in issues if i["level"] == "P1" and i["status"] == "FAIL"]
    print(json.dumps({"json": str(json_path), "md": str(md_path), "p0_fail": len(p0_fail), "p1_fail": len(p1_fail)}, ensure_ascii=False, indent=2))
    return 1 if p0_fail or p1_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
