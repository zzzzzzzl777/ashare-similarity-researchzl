"""Audit next-round 14:57 protocol and fixed-matrix outputs.

The audit is intentionally lightweight so it can be run repeatedly while long
matrix jobs are still producing rows. It distinguishes incomplete work from
hard failures, and writes machine-readable plus human-readable artifacts.
"""
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

from run_1457_next_round_fixed_matrix import P0_CANONICAL_COLUMNS


def parse_args() -> argparse.Namespace:
    cfg = get_default_config()
    report_dir = cfg.storage.report_dir / "prediction"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof-date", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--matrix-asof", default=None)
    parser.add_argument("--expected-fold-runs", type=int, default=0)
    parser.add_argument("--expected-variants", type=int, default=0)
    parser.add_argument("--expected-schemes", type=int, default=0)
    parser.add_argument("--expected-backend", default="", help="Require one compute backend, for example cpu or gpu.")
    parser.add_argument("--expected-python", default="", help="Require matrix rows to come from this python executable suffix/path.")
    parser.add_argument("--report-dir", type=Path, default=report_dir)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": repr(exc)}


def add_issue(issues: list[dict[str, Any]], level: str, code: str, status: str, detail: str) -> None:
    issues.append({"level": level, "code": code, "status": status, "detail": detail})


def parse_json_list_cell(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text or text == "nan":
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item)]


def strict_p0_rows_from_selected_features(df: pd.DataFrame) -> list[dict[str, Any]]:
    if "selected_features_json" not in df.columns:
        return []
    rows: list[dict[str, Any]] = []
    strict = set(P0_CANONICAL_COLUMNS)
    for idx, row in df.iterrows():
        selected = parse_json_list_cell(row.get("selected_features_json"))
        found = sorted(set(selected) & strict)
        if found:
            rows.append(
                {
                    "row_index": int(idx),
                    "variant_id": row.get("variant_id"),
                    "scheme": row.get("scheme"),
                    "outer_fold": row.get("outer_fold"),
                    "run_id": row.get("run_id"),
                    "strict_p0_count": len(found),
                    "strict_p0_selected": found,
                }
            )
    return rows


def audit_protocol(report_dir: Path, asof: str, issues: list[dict[str, Any]]) -> None:
    self_audit_path = report_dir / f"next_round_1457_self_audit_{asof}.csv"
    if not self_audit_path.exists():
        add_issue(issues, "P0", "protocol_self_audit_exists", "FAIL", f"Missing {self_audit_path}.")
        return
    df = pd.read_csv(self_audit_path)
    failing = df[df["status"].astype(str).ne("PASS")]
    add_issue(
        issues,
        "P0",
        "protocol_self_audit_clean",
        "PASS" if failing.empty else "FAIL",
        f"Protocol non-PASS rows: {len(failing)}.",
    )


def audit_matrix(report_dir: Path, matrix_asof: str, args: argparse.Namespace, issues: list[dict[str, Any]]) -> dict[str, Any]:
    summary_path = report_dir / f"next_round_1457_fixed_matrix_summary_{matrix_asof}.json"
    csv_path = report_dir / f"next_round_1457_fixed_matrix_results_{matrix_asof}.csv"
    summary = read_json(summary_path)
    if not summary:
        add_issue(issues, "P1", "fixed_matrix_summary_exists", "WIP", f"Missing {summary_path}.")
        return {"summary_path": str(summary_path), "csv_path": str(csv_path), "rows": 0, "leaderboard": []}
    add_issue(
        issues,
        "P1",
        "fixed_matrix_summary_readable",
        "PASS" if "_read_error" not in summary else "FAIL",
        summary.get("_read_error", f"Read {summary_path}."),
    )
    rows = int(summary.get("fold_rows") or 0)
    expected = int(args.expected_fold_runs or 0)
    if expected:
        status = "PASS" if rows >= expected else "WIP"
        detail = f"Fold rows {rows}/{expected}."
    else:
        status = "PASS" if rows > 0 else "WIP"
        detail = f"Fold rows {rows}."
    add_issue(issues, "P1", "fixed_matrix_fold_rows", status, detail)

    df = pd.DataFrame()
    if csv_path.exists():
        df = pd.read_csv(csv_path)
    elif rows:
        add_issue(issues, "P1", "fixed_matrix_csv_exists", "FAIL", f"Missing {csv_path} despite summary rows.")
    if not df.empty:
        errors = df[df["status"].astype(str).eq("ERROR")]
        p0_rows = df[pd.to_numeric(df.get("p0_selected_count", 0), errors="coerce").fillna(0).gt(0)]
        recomputed_p0_rows = strict_p0_rows_from_selected_features(df)
        duplicate_keys = df.duplicated(["variant_id", "scheme", "outer_fold", "seed", "budget"]).sum()
        variants = int(df["variant_id"].nunique())
        schemes = int(df["scheme"].nunique())
        completed_df = df[df["status"].astype(str).ne("ERROR")].copy()
        add_issue(issues, "P0", "fixed_matrix_no_error_rows", "PASS" if errors.empty else "FAIL", f"ERROR rows: {len(errors)}.")
        add_issue(issues, "P0", "fixed_matrix_no_p0_selected", "PASS" if p0_rows.empty else "FAIL", f"P0 selected rows: {len(p0_rows)}.")
        if recomputed_p0_rows:
            sample = recomputed_p0_rows[0]
            detail = (
                f"Recomputed strict P0 rows: {len(recomputed_p0_rows)}; "
                f"sample run={sample.get('run_id')}, "
                f"features={sample.get('strict_p0_selected')[:8]}."
            )
        else:
            detail = "Recomputed strict P0 rows: 0."
        add_issue(
            issues,
            "P0",
            "fixed_matrix_no_strict_p0_selected_recomputed",
            "PASS" if not recomputed_p0_rows else "FAIL",
            detail,
        )
        add_issue(issues, "P1", "fixed_matrix_no_duplicate_keys", "PASS" if duplicate_keys == 0 else "FAIL", f"Duplicate keys: {int(duplicate_keys)}.")
        if "compute_backend" in completed_df.columns and not completed_df.empty:
            backends = sorted(set(completed_df["compute_backend"].dropna().astype(str)))
            expected_backend = str(args.expected_backend or "").strip()
            backend_ok = len(backends) == 1 and (not expected_backend or backends[0] == expected_backend)
            add_issue(
                issues,
                "P0",
                "fixed_matrix_single_compute_backend",
                "PASS" if backend_ok else "FAIL",
                f"Backends: {backends}; expected: {expected_backend or 'single backend'}.",
            )
        elif args.expected_backend:
            add_issue(
                issues,
                "P0",
                "fixed_matrix_single_compute_backend",
                "FAIL",
                "Missing compute_backend column on completed fixed-matrix rows.",
            )
        if args.expected_python:
            expected_python = str(args.expected_python).strip().lower()
            if "python_executable" in completed_df.columns and not completed_df.empty:
                pythons = sorted(set(completed_df["python_executable"].dropna().astype(str)))
                python_ok = len(pythons) == 1 and expected_python in pythons[0].lower()
                add_issue(
                    issues,
                    "P0",
                    "fixed_matrix_single_python_env",
                    "PASS" if python_ok else "FAIL",
                    f"Python envs: {pythons}; expected contains: {args.expected_python}.",
                )
            else:
                add_issue(
                    issues,
                    "P0",
                    "fixed_matrix_single_python_env",
                    "FAIL",
                    "Missing python_executable column on completed fixed-matrix rows.",
                )
        if args.expected_variants:
            add_issue(
                issues,
                "P1",
                "fixed_matrix_variant_coverage",
                "PASS" if variants >= args.expected_variants else "WIP",
                f"Variants {variants}/{args.expected_variants}.",
            )
        if args.expected_schemes:
            add_issue(
                issues,
                "P1",
                "fixed_matrix_scheme_coverage",
                "PASS" if schemes >= args.expected_schemes else "WIP",
                f"Schemes {schemes}/{args.expected_schemes}.",
            )
    return {
        "summary_path": str(summary_path),
        "csv_path": str(csv_path),
        "rows": rows,
        "leaderboard": summary.get("leaderboard") or [],
    }


def write_outputs(report_dir: Path, asof: str, matrix_asof: str, payload: dict[str, Any]) -> tuple[Path, Path, Path]:
    json_path = report_dir / f"next_round_1457_output_audit_{matrix_asof}.json"
    csv_path = report_dir / f"next_round_1457_output_audit_{matrix_asof}.csv"
    md_path = REPO_ROOT / "docs" / f"next_round_1457_output_audit_{matrix_asof}.md"
    pd.DataFrame(payload["issues"]).to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    top_rows = payload.get("matrix", {}).get("leaderboard", [])[:10]
    lines = [
        f"# 14:57 Next-Round Output Audit ({matrix_asof})",
        "",
        f"- Created at: {payload['created_at']}",
        f"- Protocol asof: `{asof}`",
        f"- Matrix rows: {payload.get('matrix', {}).get('rows', 0)}",
        f"- P0 fails: {payload['p0_fail_count']}",
        f"- P1 fails: {payload['p1_fail_count']}",
        f"- WIP rows: {payload['wip_count']}",
        "",
        "## Issues",
        "",
        "| level | code | status | detail |",
        "|---|---|---|---|",
    ]
    for issue in payload["issues"]:
        lines.append(f"| {issue['level']} | {issue['code']} | {issue['status']} | {issue['detail']} |")
    lines.extend(["", "## Leaderboard Preview", ""])
    if top_rows:
        lines.append("| variant | scheme | folds | mean_wilson_95 | min_wilson_95 | mean_accuracy | candidates | p0 |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for row in top_rows:
            lines.append(
                "| {variant_id} | {scheme} | {folds} | {mean_wilson_95:.6f} | {min_wilson_95:.6f} | {mean_accuracy:.6f} | {total_candidates} | {p0_selected_total} |".format(
                    **row
                )
            )
    else:
        lines.append("No leaderboard rows yet.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, csv_path, md_path


def main() -> int:
    args = parse_args()
    matrix_asof = args.matrix_asof or args.asof_date
    issues: list[dict[str, Any]] = []
    audit_protocol(args.report_dir, args.asof_date, issues)
    matrix_payload = audit_matrix(args.report_dir, matrix_asof, args, issues)
    p0_fail = [i for i in issues if i["level"] == "P0" and i["status"] == "FAIL"]
    p1_fail = [i for i in issues if i["level"] == "P1" and i["status"] == "FAIL"]
    wip = [i for i in issues if i["status"] == "WIP"]
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol_asof": args.asof_date,
        "matrix_asof": matrix_asof,
        "issues": issues,
        "matrix": matrix_payload,
        "p0_fail_count": len(p0_fail),
        "p1_fail_count": len(p1_fail),
        "wip_count": len(wip),
    }
    json_path, csv_path, md_path = write_outputs(args.report_dir, args.asof_date, matrix_asof, payload)
    print(json.dumps({"json": str(json_path), "csv": str(csv_path), "md": str(md_path), **{k: payload[k] for k in ("p0_fail_count", "p1_fail_count", "wip_count")}}, ensure_ascii=False, indent=2))
    return 1 if p0_fail or p1_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
