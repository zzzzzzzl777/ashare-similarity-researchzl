"""Create the tier-1 findings report for the next-round 14:57 study."""
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


def parse_args() -> argparse.Namespace:
    cfg = get_default_config()
    report_dir = cfg.storage.report_dir / "prediction"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof-date", default="20260513")
    parser.add_argument("--matrix-asof", default="20260513_tier1_even")
    parser.add_argument("--report-dir", type=Path, default=report_dir)
    return parser.parse_args()


def round_float(value: Any, digits: int = 6) -> Any:
    try:
        if pd.isna(value):
            return None
        return round(float(value), digits)
    except Exception:
        return value


def table_lines(df: pd.DataFrame, columns: list[str], max_rows: int = 20) -> list[str]:
    if df.empty:
        return ["No rows."]
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in df.head(max_rows).to_dict("records"):
        values = []
        for col in columns:
            value = row.get(col)
            if isinstance(value, float):
                values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def main() -> int:
    args = parse_args()
    fixed_csv = args.report_dir / f"next_round_1457_fixed_matrix_results_{args.matrix_asof}.csv"
    bundle_csv = args.report_dir / f"next_round_1457_existing_bundle_scores_{args.matrix_asof}.csv"
    audit_json = args.report_dir / f"next_round_1457_output_audit_{args.matrix_asof}.json"
    fixed = pd.read_csv(fixed_csv)
    bundles = pd.read_csv(bundle_csv)
    fixed = fixed[fixed["status"].astype(str).eq("completed")].copy()

    variant_agg = fixed.groupby("variant_id", dropna=False).agg(
        folds=("outer_fold", "count"),
        mean_wilson95=("wilson_95", "mean"),
        min_wilson95=("wilson_95", "min"),
        mean_accuracy=("confident_accuracy", "mean"),
        total_candidates=("confident_count", "sum"),
        p0_selected_total=("p0_selected_count", "sum"),
    ).reset_index().sort_values(["mean_wilson95", "min_wilson95"], ascending=False)

    scheme_agg = fixed.groupby("scheme", dropna=False).agg(
        folds=("outer_fold", "count"),
        mean_wilson95=("wilson_95", "mean"),
        min_wilson95=("wilson_95", "min"),
        mean_accuracy=("confident_accuracy", "mean"),
        total_candidates=("confident_count", "sum"),
    ).reset_index().sort_values(["mean_wilson95", "min_wilson95"], ascending=False)

    combo_agg = fixed.groupby(["variant_id", "scheme"], dropna=False).agg(
        folds=("outer_fold", "count"),
        mean_wilson95=("wilson_95", "mean"),
        min_wilson95=("wilson_95", "min"),
        mean_accuracy=("confident_accuracy", "mean"),
        total_candidates=("confident_count", "sum"),
        p0_selected_total=("p0_selected_count", "sum"),
    ).reset_index().sort_values(["mean_wilson95", "min_wilson95"], ascending=False)

    q4 = fixed[fixed["outer_fold"].eq(28)].copy().sort_values("wilson_95", ascending=False)
    bundle_agg = bundles.groupby("bundle_id", dropna=False).agg(
        folds=("outer_fold", "count"),
        mean_pge075_wilson95=("pge_075_wilson95", "mean"),
        min_pge075_wilson95=("pge_075_wilson95", "min"),
        mean_daily_top5_wilson95=("daily_top5_wilson95", "mean"),
        min_daily_top5_wilson95=("daily_top5_wilson95", "min"),
        pge075_count=("pge_075_count", "sum"),
    ).reset_index().sort_values(["mean_daily_top5_wilson95", "mean_pge075_wilson95"], ascending=False)
    bundle_outer = bundles.groupby(["bundle_id", "outer_fold", "outer_valid_start", "outer_valid_end"], dropna=False).agg(
        pge075_wilson95=("pge_075_wilson95", "mean"),
        pge075_accuracy=("pge_075_accuracy", "mean"),
        pge075_count=("pge_075_count", "mean"),
        daily_top5_wilson95=("daily_top5_wilson95", "mean"),
        daily_top5_accuracy=("daily_top5_accuracy", "mean"),
    ).reset_index().sort_values(["outer_fold", "daily_top5_wilson95"], ascending=[True, False])

    audit = json.loads(audit_json.read_text(encoding="utf-8")) if audit_json.exists() else {}
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "matrix_asof": args.matrix_asof,
        "audit": {
            "p0_fail_count": audit.get("p0_fail_count"),
            "p1_fail_count": audit.get("p1_fail_count"),
            "wip_count": audit.get("wip_count"),
        },
        "variant_aggregate": variant_agg.to_dict("records"),
        "scheme_aggregate": scheme_agg.to_dict("records"),
        "combo_leaderboard": combo_agg.head(30).to_dict("records"),
        "q4_2025": q4.to_dict("records"),
        "existing_bundle_aggregate": bundle_agg.to_dict("records"),
        "existing_bundle_by_outer_fold": bundle_outer.to_dict("records"),
        "decision": {
            "tier1_champion_candidate": "all_A_engineerable + expanding_from_fair_start",
            "stable_control_candidate": "pre_new_A_engineerable_control + fixed_start_2018 / expanding_from_fair_start",
            "new_5min_status": "has_signal_but_not_standalone_champion",
            "b_proxy_status": "pending_explicit_proxy_columns; not run in fixed matrix",
            "next_action": "expand top schemes/factor sets to full rolling folds, then score Q1/April as seen-research only.",
        },
    }
    json_path = args.report_dir / f"next_round_1457_tier1_findings_{args.matrix_asof}.json"
    md_path = REPO_ROOT / "docs" / f"next_round_1457_tier1_findings_{args.matrix_asof}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        f"# 14:57 Next-Round Tier-1 Findings ({args.matrix_asof})",
        "",
        f"- Created at: {payload['created_at']}",
        f"- Fixed matrix rows: {len(fixed)}",
        f"- Existing bundle score rows: {len(bundles)}",
        f"- Audit: P0={payload['audit'].get('p0_fail_count')}, P1={payload['audit'].get('p1_fail_count')}, WIP={payload['audit'].get('wip_count')}",
        "",
        "## Decisions",
        "",
        "- Tier-1 fixed-matrix leader: `all_A_engineerable + expanding_from_fair_start`.",
        "- Most stable control: `pre_new_A_engineerable_control` with `fixed_start_2018` or `expanding_from_fair_start`.",
        "- `C174-C188` has signal, but `new_5min_family_only` is not a standalone champion; keep it for add/delete and full rolling tests.",
        "- `all_A_plus_B_t1_proxy_policy` is proxy-pending; do not run it until explicit T-1/proxy feature columns exist.",
        "- Do not choose a champion from this 2-fold-per-scheme tier; expand the top schemes to full rolling folds next.",
        "",
        "## Fixed Matrix By Variant",
        "",
        *table_lines(variant_agg, ["variant_id", "folds", "mean_wilson95", "min_wilson95", "mean_accuracy", "total_candidates", "p0_selected_total"]),
        "",
        "## Fixed Matrix By Scheme",
        "",
        *table_lines(scheme_agg, ["scheme", "folds", "mean_wilson95", "min_wilson95", "mean_accuracy", "total_candidates"]),
        "",
        "## Fixed Matrix Top Combos",
        "",
        *table_lines(combo_agg, ["variant_id", "scheme", "folds", "mean_wilson95", "min_wilson95", "mean_accuracy", "total_candidates", "p0_selected_total"], max_rows=18),
        "",
        "## 2025Q4 Stress Fold",
        "",
        *table_lines(q4, ["variant_id", "scheme", "wilson_95", "confident_accuracy", "confident_count", "p0_selected_count"], max_rows=18),
        "",
        "## Existing Bundle Score-Only",
        "",
        "Existing bundles are score-only and should not be merged numerically with fixed-matrix retraining metrics.",
        "",
        *table_lines(bundle_agg, ["bundle_id", "folds", "mean_pge075_wilson95", "min_pge075_wilson95", "mean_daily_top5_wilson95", "min_daily_top5_wilson95", "pge075_count"]),
        "",
        "## Existing Bundle By Outer Fold",
        "",
        *table_lines(bundle_outer, ["bundle_id", "outer_fold", "outer_valid_start", "outer_valid_end", "pge075_wilson95", "pge075_accuracy", "pge075_count", "daily_top5_wilson95", "daily_top5_accuracy"], max_rows=24),
        "",
        "## Next Actions",
        "",
        "1. Expand full rolling folds for `all_A_engineerable`, `pre_new_A_engineerable_control`, and `new_5min_family_only` on `expanding_from_fair_start`, `fixed_start_2018`, `fixed_start_2020`, and `fixed_recent_36m`.",
        "2. Keep `fixed_recent_24m` and `fixed_recent_60m` as diagnostic windows, not primary champion selectors.",
        "3. Implement explicit B-class proxy columns before rerunning the B-policy variant.",
        "4. After full rolling, use Q1/April only as seen-research consistency checks, not as final pass/fail.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"json": str(json_path), "md": str(md_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
