"""Summarize next-round 14:57 evidence across trained variants and old bundles."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import sys

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
    parser.add_argument("--matrix-asof", default="20260513_tier1_even")
    parser.add_argument("--bundle-asof", default="20260513_tier1_even_scoreonly_v2")
    parser.add_argument("--expected-matrix-rows", type=int, default=36)
    parser.add_argument("--expected-bundle-rows", type=int, default=24)
    parser.add_argument(
        "--matrix-csv",
        type=Path,
        default=report_dir / "next_round_1457_fixed_matrix_results_20260513_tier1_even.csv",
    )
    parser.add_argument(
        "--bundle-csv",
        type=Path,
        default=report_dir / "next_round_1457_existing_bundle_scores_20260513_tier1_even_scoreonly_v2.csv",
    )
    parser.add_argument(
        "--matrix-audit-json",
        type=Path,
        default=report_dir / "next_round_1457_output_audit_20260513_tier1_even.json",
    )
    parser.add_argument("--desktop-copy", action="store_true", default=True)
    parser.add_argument("--no-desktop-copy", action="store_false", dest="desktop_copy")
    return parser.parse_args()


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def aggregate_matrix(df: pd.DataFrame) -> pd.DataFrame:
    completed = df[df["status"].astype(str).eq("completed")].copy()
    completed["wilson_95"] = _num(completed["wilson_95"])
    completed["confident_accuracy"] = _num(completed["confident_accuracy"])
    completed["confident_count"] = _num(completed["confident_count"]).fillna(0)
    completed["p0_selected_count"] = _num(completed["p0_selected_count"]).fillna(0)
    agg = completed.groupby(["variant_id", "scheme"], dropna=False).agg(
        folds=("outer_fold", "count"),
        mean_pge075_wilson95=("wilson_95", "mean"),
        min_pge075_wilson95=("wilson_95", "min"),
        mean_pge075_accuracy=("confident_accuracy", "mean"),
        total_pge075=("confident_count", "sum"),
        p0_total=("p0_selected_count", "sum"),
        outer_start=("outer_valid_start", "min"),
        outer_end=("outer_valid_end", "max"),
    )
    out = agg.reset_index().rename(columns={"variant_id": "candidate_id"})
    out.insert(0, "evidence_source", "fixed_config_train")
    out["missing_feature_total"] = 0
    return out


def aggregate_bundles(df: pd.DataFrame) -> pd.DataFrame:
    completed = df[df["status"].astype(str).eq("completed")].copy()
    for col in [
        "pge_075_wilson95",
        "pge_075_accuracy",
        "pge_075_count",
        "daily_top5_wilson95",
        "missing_feature_count",
        "missing_selected_feature_count",
    ]:
        if col in completed.columns:
            completed[col] = _num(completed[col])
    agg = completed.groupby(["bundle_id", "scheme"], dropna=False).agg(
        folds=("outer_fold", "count"),
        mean_pge075_wilson95=("pge_075_wilson95", "mean"),
        min_pge075_wilson95=("pge_075_wilson95", "min"),
        mean_pge075_accuracy=("pge_075_accuracy", "mean"),
        total_pge075=("pge_075_count", "sum"),
        mean_daily_top5_wilson95=("daily_top5_wilson95", "mean"),
        min_daily_top5_wilson95=("daily_top5_wilson95", "min"),
        missing_feature_total=("missing_feature_count", "sum"),
        missing_selected_feature_total=("missing_selected_feature_count", "sum"),
        outer_start=("outer_valid_start", "min"),
        outer_end=("outer_valid_end", "max"),
    )
    out = agg.reset_index().rename(columns={"bundle_id": "candidate_id"})
    out.insert(0, "evidence_source", "score_only_existing_bundle")
    out["p0_total"] = 0
    return out


def audit_inputs(matrix: pd.DataFrame, bundles: pd.DataFrame, audit_json: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    matrix_audit = json.loads(audit_json.read_text(encoding="utf-8")) if audit_json.exists() else {}

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    add("matrix_rows_expected", len(matrix) == args.expected_matrix_rows, f"{len(matrix)} / {args.expected_matrix_rows}")
    add("bundle_rows_expected", len(bundles) == args.expected_bundle_rows, f"{len(bundles)} / {args.expected_bundle_rows}")
    add(
        "matrix_audit_clean",
        int(matrix_audit.get("p0_fail_count", -1)) == 0
        and int(matrix_audit.get("p1_fail_count", -1)) == 0
        and int(matrix_audit.get("wip_count", -1)) == 0,
        json.dumps(
            {
                "p0": matrix_audit.get("p0_fail_count"),
                "p1": matrix_audit.get("p1_fail_count"),
                "wip": matrix_audit.get("wip_count"),
            },
            ensure_ascii=False,
        ),
    )
    add(
        "matrix_completed_only",
        matrix["status"].astype(str).eq("completed").all(),
        str(matrix["status"].astype(str).value_counts().to_dict()),
    )
    add(
        "bundle_completed_only",
        bundles["status"].astype(str).eq("completed").all(),
        str(bundles["status"].astype(str).value_counts().to_dict()),
    )
    add(
        "bundle_no_missing_features",
        int(_num(bundles.get("missing_feature_count", pd.Series(dtype=float))).fillna(0).sum()) == 0
        and int(_num(bundles.get("missing_selected_feature_count", pd.Series(dtype=float))).fillna(0).sum()) == 0,
        "missing feature columns are zero",
    )
    combined_dates = pd.concat(
        [
            pd.to_datetime(matrix["outer_valid_end"], errors="coerce"),
            pd.to_datetime(bundles["outer_valid_end"], errors="coerce"),
        ],
        ignore_index=True,
    )
    add(
        "no_q1_or_april_in_stage1_outer",
        bool(combined_dates.max() < pd.Timestamp("2026-01-01")),
        f"max outer_valid_end={combined_dates.max().date() if not pd.isna(combined_dates.max()) else 'NA'}",
    )
    return checks


def markdown_table(df: pd.DataFrame, columns: list[str], limit: int) -> str:
    view = df.loc[:, columns].head(limit).copy()
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):.6f}")
    return view.to_markdown(index=False)


def build_report(
    *,
    combined: pd.DataFrame,
    checks: list[dict[str, Any]],
    matrix: pd.DataFrame,
    bundles: pd.DataFrame,
    out_csv: Path,
    out_json: Path,
) -> str:
    pass_count = sum(1 for item in checks if item["status"] == "PASS")
    fail_count = len(checks) - pass_count
    top_cols = [
        "evidence_source",
        "candidate_id",
        "scheme",
        "folds",
        "mean_pge075_wilson95",
        "min_pge075_wilson95",
        "mean_pge075_accuracy",
        "total_pge075",
    ]
    top_fixed = combined[combined["evidence_source"].eq("fixed_config_train")]
    top_bundles = combined[combined["evidence_source"].eq("score_only_existing_bundle")]
    checks_df = pd.DataFrame(checks)
    by_scheme = (
        top_fixed.groupby("scheme", dropna=False)
        .agg(
            best_mean_wilson=("mean_pge075_wilson95", "max"),
            best_min_wilson=("min_pge075_wilson95", "max"),
            variants=("candidate_id", "nunique"),
        )
        .reset_index()
        .sort_values(["best_mean_wilson", "best_min_wilson"], ascending=False)
    )
    lines = [
        "# 14:57 下一轮训练 Phase 1 证据汇总",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 自审结论",
        "",
        f"- 输入审计：PASS={pass_count}，FAIL={fail_count}。",
        f"- 固定训练矩阵：{len(matrix)} 行；旧 bundle score-only：{len(bundles)} 行。",
        f"- 合并 leaderboard：{len(combined)} 行。",
        f"- 输出 CSV：`{out_csv}`",
        f"- 输出 JSON：`{out_json}`",
        "",
        checks_df.to_markdown(index=False),
        "",
        "## 统一 Leaderboard（按 p>=0.75 Wilson 均值排序）",
        "",
        markdown_table(combined, top_cols, 16),
        "",
        "## 固定训练矩阵前排",
        "",
        markdown_table(top_fixed, top_cols, 12),
        "",
        "## 旧 S2/PhaseC Score-Only 基线",
        "",
        markdown_table(
            top_bundles,
            top_cols + ["mean_daily_top5_wilson95", "min_daily_top5_wilson95", "missing_feature_total"],
            12,
        ),
        "",
        "## 时间窗口初判",
        "",
        markdown_table(by_scheme, ["scheme", "best_mean_wilson", "best_min_wilson", "variants"], 12),
        "",
        "## 当前判断",
        "",
        "- 不能再用 2026-04 单月准确率决定冠军；tier1 的多窗口证据显示窗口选择会显著改变结论。",
        "- `fixed_start_2018` 与 `expanding_from_fair_start` 是第一梯队；`fixed_recent_36m` 和 `fixed_start_2020` 可做稳健性陪跑；`fixed_recent_24m/60m` 暂时落后。",
        "- `all_A_engineerable` 在 expanding 上均值最高，但 `pre_new_A_engineerable_control` 在 2018/expanding 的最差窗口更稳；新 5min 因子单独可用但还不能单独当冠军。",
        "- S2/PhaseC 旧 bundle 在 score-only 下仍有参考价值，尤其可作为风险基线；但它们不是同协议重训模型，不能直接替代下一轮冠军训练。",
        "",
        "## 自动进入下一步",
        "",
        "- Stage2 扩大 fold：`all_A_engineerable`、`pre_new_A_engineerable_control`、`new_5min_family_only`。",
        "- Stage2 窗口：`expanding_from_fair_start`、`fixed_start_2018`、`fixed_recent_36m`、`fixed_start_2020`。",
        "- 每个方案先取 4 个均匀 fold 复核，继续要求 P0=0、P1=0、WIP=0；通过后再做 HPO/multi-seed/frozen score-only。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    cfg = get_default_config()
    report_dir = cfg.storage.report_dir / "prediction"
    docs_dir = Path("docs")
    matrix = pd.read_csv(args.matrix_csv)
    bundles = pd.read_csv(args.bundle_csv)
    fixed = aggregate_matrix(matrix)
    scored = aggregate_bundles(bundles)
    combined = pd.concat([fixed, scored], ignore_index=True, sort=False)
    combined = combined.sort_values(["mean_pge075_wilson95", "min_pge075_wilson95"], ascending=False)
    checks = audit_inputs(matrix, bundles, args.matrix_audit_json, args)
    stem = f"next_round_1457_stage1_combined_{args.asof_date}"
    out_csv = report_dir / f"{stem}.csv"
    out_json = report_dir / f"{stem}.json"
    out_md = docs_dir / f"{stem}.md"
    out_audit = report_dir / f"{stem}_audit.json"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_csv, index=False, encoding="utf-8-sig")
    out_json.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "rows": combined.to_dict("records"),
                "inputs": {
                    "matrix_csv": str(args.matrix_csv),
                    "bundle_csv": str(args.bundle_csv),
                    "matrix_audit_json": str(args.matrix_audit_json),
                },
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    out_audit.write_text(json.dumps({"checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8")
    report = build_report(
        combined=combined,
        checks=checks,
        matrix=matrix,
        bundles=bundles,
        out_csv=out_csv,
        out_json=out_json,
    )
    out_md.write_text(report, encoding="utf-8")
    desktop_path = None
    if args.desktop_copy:
        desktop_path = Path.home() / "Desktop" / f"14点57下一轮训练Phase1证据汇总_{args.asof_date}.md"
        desktop_path.write_text(report, encoding="utf-8")
    fail_count = sum(1 for item in checks if item["status"] != "PASS")
    print(
        json.dumps(
            {
                "csv": str(out_csv),
                "json": str(out_json),
                "audit": str(out_audit),
                "md": str(out_md),
                "desktop_md": str(desktop_path) if desktop_path else None,
                "fail_count": fail_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
