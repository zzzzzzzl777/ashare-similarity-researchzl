"""PhaseC cross-window constrained strategy search.

This is a score-only diagnostic script. It does not retrain any model.

Goal:
- Use the frozen PhaseC bundle.
- Evaluate the same strategy grid on 2026-04 and 2023-02/03/04.
- Prefer strategies that are useful in current market conditions while not
  failing older validation months.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
import argparse
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_dual_model_strategy_search import (  # noqa: E402
    CACHE_MAIN,
    CACHE_PRETRAIN,
    EXIT_MODES,
    PC_BUNDLE,
    S2_BUNDLE,
    RANK_RECIPES,
    build_daily_ranks,
    build_filters,
    compute_all_exits,
    load_bundle,
    load_scoring_frame,
    predict_raw_and_iso,
    run_holdout_eval,
)


OUT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
DEFAULT_STAMP = "20260511"


def pct(v: float | None) -> float | None:
    if v is None:
        return None
    return round(float(v), 4)


def compact_metrics(r: dict | None) -> dict | None:
    if not r:
        return None
    keys = [
        "signal_days",
        "tickets",
        "avg_picks_per_day",
        "total_return_pct",
        "avg_daily_return_pct",
        "daily_win_rate",
        "ticket_win_rate",
        "high1_hit_rate",
        "high1_w95",
        "sharpe",
        "max_daily_loss_pct",
        "max_daily_gain_pct",
        "months_positive",
        "months_total",
        "single_month_risk",
        "months",
    ]
    return {k: r.get(k) for k in keys}


def month_return_map(r: dict | None) -> dict[str, float]:
    if not r:
        return {}
    return {m["month"]: float(m["return_pct"]) for m in r.get("months", [])}


def max_draw_penalty(r: dict | None) -> float:
    if not r:
        return 100.0
    return max(0.0, -float(r.get("max_daily_loss_pct", 0.0)))


def cross_score(apr: dict, val: dict) -> float:
    """Balanced diagnostic score, not an investable guarantee."""
    val_months = month_return_map(val)
    val_rets = [val_months.get(m, -99.0) for m in ["2023-02", "2023-03", "2023-04"]]
    min_val_month = min(val_rets)
    month_pos = sum(1 for x in val_rets if x > 0)
    score = 0.35 * float(apr["total_return_pct"])
    score += 0.35 * float(val["total_return_pct"])
    score += 30.0 * (float(apr["daily_win_rate"]) - 0.55)
    score += 35.0 * (float(val["daily_win_rate"]) - 0.50)
    score += 20.0 * (float(apr["high1_hit_rate"]) - 0.75)
    score += 20.0 * (float(val["high1_hit_rate"]) - 0.75)
    score += 2.0 * (float(apr.get("sharpe") or 0.0) + float(val.get("sharpe") or 0.0))
    score += 16.0 * month_pos
    score += min(15.0, max(-30.0, min_val_month))
    score -= 2.0 * max_draw_penalty(apr)
    score -= 2.0 * max_draw_penalty(val)
    return float(score)


def classify(apr: dict | None, val: dict | None) -> str:
    if not apr or not val:
        return "invalid"
    val_months = month_return_map(val)
    val_rets = [val_months.get(m, -999.0) for m in ["2023-02", "2023-03", "2023-04"]]
    all_val_pos = all(x > 0 for x in val_rets)
    val_total_pos = float(val["total_return_pct"]) > 0
    apr_pos = float(apr["total_return_pct"]) > 0
    apr_days_ok = int(apr["signal_days"]) >= 18
    val_days_ok = int(val["signal_days"]) >= 45
    if apr_pos and all_val_pos and apr_days_ok and val_days_ok:
        return "strict_23_all_months_positive"
    if apr_pos and val_total_pos and sum(x > 0 for x in val_rets) >= 2 and apr_days_ok and val_days_ok:
        return "balanced_23_total_positive"
    if apr_pos and float(apr["total_return_pct"]) >= 20 and val_total_pos:
        return "current_strong_23_total_positive"
    if apr_pos:
        return "current_only_not_main"
    return "invalid"


def base_row(strat: dict, apr: dict, val: dict, category: str) -> dict:
    val_months = month_return_map(val)
    return {
        "category": category,
        "score": round(cross_score(apr, val), 4),
        "score_col": strat["score_col"],
        "threshold": strat["threshold"],
        "top_n": strat["top_n"],
        "filter_name": strat["filter_name"],
        "rank_recipe": strat["rank_recipe"],
        "exit_mode": strat["exit_mode"],
        "apr_return": round(float(apr["total_return_pct"]), 4),
        "apr_days": apr["signal_days"],
        "apr_tickets": apr["tickets"],
        "apr_daily_win": round(float(apr["daily_win_rate"]), 4),
        "apr_high1": round(float(apr["high1_hit_rate"]), 4),
        "apr_w95": round(float(apr["high1_w95"]), 4),
        "apr_sharpe": pct(apr.get("sharpe")),
        "apr_max_loss": round(float(apr["max_daily_loss_pct"]), 4),
        "val_return": round(float(val["total_return_pct"]), 4),
        "val_days": val["signal_days"],
        "val_tickets": val["tickets"],
        "val_daily_win": round(float(val["daily_win_rate"]), 4),
        "val_high1": round(float(val["high1_hit_rate"]), 4),
        "val_w95": round(float(val["high1_w95"]), 4),
        "val_sharpe": pct(val.get("sharpe")),
        "val_max_loss": round(float(val["max_daily_loss_pct"]), 4),
        "ret_2023_02": round(val_months.get("2023-02", 0.0), 4),
        "ret_2023_03": round(val_months.get("2023-03", 0.0), 4),
        "ret_2023_04": round(val_months.get("2023-04", 0.0), 4),
    }


def maybe_keep(bucket: list[dict], row: dict, limit: int = 300) -> None:
    bucket.append(row)
    if len(bucket) > limit * 3:
        bucket.sort(key=lambda x: x["score"], reverse=True)
        del bucket[limit:]


def prepare_frame(bundle: dict, cache: Path, start: str, end: str, label: str):
    print(f"[load] {label}: {start}..{end}", flush=True)
    df = load_scoring_frame(cache, bundle, start, end, label)
    raw, iso = predict_raw_and_iso(bundle, df)
    df["raw_prob"] = raw
    df["iso_prob"] = iso
    print(f"[load] {label}: rows={len(df):,}, days={df['date'].nunique()}", flush=True)
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["phasec", "s2"], default="phasec")
    parser.add_argument("--stamp", default=DEFAULT_STAMP)
    args = parser.parse_args()

    bundle_path = PC_BUNDLE if args.model == "phasec" else S2_BUNDLE
    out_json = OUT_DIR / f"{args.model}_cross_window_constrained_search_{args.stamp}.json"
    out_csv = OUT_DIR / f"{args.model}_cross_window_constrained_top_strategies_{args.stamp}.csv"
    desktop_csv = Path(fr"C:\Users\zzzzzzl\Desktop\{args.model}_cross_window_constrained_top_strategies_{args.stamp}.csv")

    t_start = time.time()
    bundle = load_bundle(bundle_path)
    apr_df = prepare_frame(bundle, CACHE_MAIN, "2026-04-01", "2026-04-30", "apr_2026")
    val_df = prepare_frame(bundle, CACHE_PRETRAIN, "2023-02-01", "2023-04-30", "val_2023")

    print("[prep] computing exits", flush=True)
    apr_exits = compute_all_exits(apr_df)
    val_exits = compute_all_exits(val_df)

    apr_actual = apr_df["actual"].fillna(0).to_numpy(dtype=np.float64)
    val_actual = val_df["actual"].fillna(0).to_numpy(dtype=np.float64)
    apr_dates = apr_df["date"].to_numpy()
    val_dates = val_df["date"].to_numpy()
    apr_months = apr_df["month"].to_numpy()
    val_months = val_df["month"].to_numpy()
    apr_filters = build_filters(apr_df)
    val_filters = {name: mask for name, mask in build_filters(val_df)}

    from scripts.run_dual_model_strategy_search import eval_from_ranks  # noqa: WPS433

    thresholds = [round(x / 100.0, 2) for x in range(50, 91)]
    top_ns = [1, 2, 3, 4, 5, 6]

    buckets: dict[str, list[dict]] = {
        "strict_23_all_months_positive": [],
        "balanced_23_total_positive": [],
        "current_strong_23_total_positive": [],
        "current_only_not_main": [],
    }
    total_rank_sets = 0
    total_evals = 0
    last_log = time.time()

    for score_col in ["raw_prob", "iso_prob"]:
        for filter_name, apr_filter in apr_filters:
            val_filter = val_filters.get(filter_name)
            if val_filter is None:
                continue
            for recipe in RANK_RECIPES:
                for threshold in thresholds:
                    apr_ranks = build_daily_ranks(apr_df, score_col, recipe, apr_filter, threshold)
                    val_ranks = build_daily_ranks(val_df, score_col, recipe, val_filter, threshold)
                    total_rank_sets += 1
                    if np.all(np.isnan(apr_ranks)) or np.all(np.isnan(val_ranks)):
                        continue
                    for top_n in top_ns:
                        for exit_name, _, _ in EXIT_MODES:
                            total_evals += 1
                            apr = eval_from_ranks(apr_ranks, apr_exits, apr_actual, apr_dates, apr_months, top_n, exit_name)
                            if apr is None:
                                continue
                            val = eval_from_ranks(val_ranks, val_exits, val_actual, val_dates, val_months, top_n, exit_name)
                            if val is None:
                                continue
                            strat = {
                                "score_col": score_col,
                                "threshold": threshold,
                                "top_n": top_n,
                                "filter_name": filter_name,
                                "rank_recipe": recipe,
                                "exit_mode": exit_name,
                            }
                            cat = classify(apr, val)
                            if cat == "invalid":
                                continue
                            maybe_keep(buckets[cat], base_row(strat, apr, val, cat))

                    if time.time() - last_log >= 30:
                        kept = sum(len(v) for v in buckets.values())
                        print(
                            f"[progress] {score_col} {filter_name} {recipe} th={threshold:.2f} "
                            f"rank_sets={total_rank_sets:,} evals={total_evals:,} kept_top={kept} "
                            f"elapsed={time.time() - t_start:.0f}s",
                            flush=True,
                        )
                        last_log = time.time()

    all_rows: list[dict] = []
    for cat, rows in buckets.items():
        rows.sort(key=lambda x: x["score"], reverse=True)
        buckets[cat] = rows[:100]
        all_rows.extend(rows[:100])
    all_rows.sort(key=lambda x: (x["category"] != "strict_23_all_months_positive", -x["score"]))

    fieldnames = list(all_rows[0].keys()) if all_rows else []
    for path in [out_csv, desktop_csv]:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

    summary = {
        "created_at": "2026-05-11",
        "model": args.model,
        "bundle": str(bundle_path),
        "purpose": f"{args.model} cross-window constrained strategy search; score-only, no retrain",
        "windows": {
            "current": "2026-04-01..2026-04-30",
            "validation": "2023-02-01..2023-04-30",
        },
        "total_rank_sets": total_rank_sets,
        "total_evals": total_evals,
        "elapsed_s": round(time.time() - t_start, 1),
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "best_by_bucket": {k: (v[0] if v else None) for k, v in buckets.items()},
        "top_rows": all_rows[:50],
        "outputs": {
            "json": str(out_json),
            "csv": str(out_csv),
            "desktop_csv": str(desktop_csv),
        },
    }
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[done] {args.model} cross-window constrained search", flush=True)
    print(json.dumps(summary["bucket_counts"], ensure_ascii=False, indent=2), flush=True)
    for cat, best in summary["best_by_bucket"].items():
        if not best:
            print(f"[best] {cat}: NONE", flush=True)
            continue
        print(
            f"[best] {cat}: score={best['score']:.2f} "
            f"{best['score_col']}>={best['threshold']} top{best['top_n']} "
            f"{best['filter_name']} {best['rank_recipe']} {best['exit_mode']} | "
            f"apr={best['apr_return']:.2f}% val={best['val_return']:.2f}% "
            f"23m=({best['ret_2023_02']:.2f},{best['ret_2023_03']:.2f},{best['ret_2023_04']:.2f})",
            flush=True,
        )


if __name__ == "__main__":
    main()
