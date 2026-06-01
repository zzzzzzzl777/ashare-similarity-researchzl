"""Return-oriented strategy search for frozen 14:57 model scores.

This is a post-model selector/backtest only:
- no retraining
- no HPO/model changes
- no Q1/April fitting inside the model

It compares raw_prob and iso_prob as separate probability sorting/gating
families on 2023-02/03/04 and 2026-04.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from compare_raw_vs_isotonic_rank import load_bundle, predict_raw_and_iso


PHASE_E_JSON = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\phaseE_frozen_april_20260509.json")
PRETRAIN_JSON = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\phaseC_pretrain_2023_02_04_validation_20260509.json")

OUT_JSON = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\return_strategy_search_20260510.json")
OUT_CSV = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\return_strategy_search_top_20260510.csv")

META_COLS = {
    "symbol",
    "name",
    "date",
    "label_date",
    "actual",
    "close",
    "next_close_return_pct",
    "next_high_return_pct",
    "next_low_return_pct",
    "limit_up_like",
    "short_phase_days_3",
}

STRATEGY_COLS = {
    "turnover",
    "turnover_z_20",
    "amount_z_20",
    "volume_z_20",
    "range_pct",
    "rsi_6",
    "rsi_14",
    "close_position",
    "upper_shadow_pct",
    "lower_shadow_pct",
    "body_pct",
    "cs_turnover_rank",
    "cs_amount_z_rank",
    "cs_volume_z_rank",
    "cs_range_rank",
}


def pct_prod(returns_pct: pd.Series) -> float:
    if len(returns_pct) == 0:
        return 0.0
    values = returns_pct.fillna(0).to_numpy(dtype=np.float64) / 100.0
    values = np.clip(values, -0.95, 10.0)
    return float((np.prod(1.0 + values) - 1.0) * 100.0)


def sharpe_like(daily_returns_pct: pd.Series) -> float | None:
    if len(daily_returns_pct) < 2:
        return None
    std = float(daily_returns_pct.std(ddof=1))
    if std == 0:
        return None
    return float(daily_returns_pct.mean() / std * math.sqrt(252))


def load_scoring_frame(cache_path: Path, bundle: dict, start: str, end: str, label: str) -> pd.DataFrame:
    schema_cols = set(pq.read_schema(str(cache_path)).names)
    needed = META_COLS | STRATEGY_COLS | set(bundle["feature_names"])
    cols = [c for c in sorted(needed) if c in schema_cols]
    missing = [c for c in bundle["feature_names"] if c not in schema_cols]
    if missing:
        raise RuntimeError(f"{cache_path} missing {len(missing)} bundle features, examples={missing[:10]}")

    frame = pd.read_parquet(str(cache_path), columns=cols)
    frame = frame[(frame["date"] >= start) & (frame["date"] <= end)].copy()
    if "limit_up_like" in frame.columns:
        frame = frame[frame["limit_up_like"] != 1].copy()
    if "short_phase_days_3" in frame.columns:
        frame = frame[frame["short_phase_days_3"] >= 1].copy()
    frame["window"] = label
    frame["month"] = frame["date"].astype(str).str.slice(0, 7)
    return frame


def build_frames() -> pd.DataFrame:
    phase_e = json.loads(PHASE_E_JSON.read_text(encoding="utf-8"))
    pretrain = json.loads(PRETRAIN_JSON.read_text(encoding="utf-8"))
    bundle = load_bundle(Path(phase_e["champion_bundle"]))

    frames = [
        load_scoring_frame(Path(pretrain["feature_cache"]), bundle, "2023-02-01", "2023-04-30", "pretrain_2023_02_04"),
        load_scoring_frame(Path(phase_e["feature_cache"]), bundle, "2026-04-01", "2026-04-30", "april_2026"),
    ]
    out_parts = []
    for frame in frames:
        raw_prob, iso_prob = predict_raw_and_iso(bundle, frame)
        frame = frame.copy()
        frame["raw_prob"] = raw_prob
        frame["iso_prob"] = iso_prob
        out_parts.append(frame)
    all_frame = pd.concat(out_parts, ignore_index=True)
    for col in STRATEGY_COLS:
        if col not in all_frame.columns:
            all_frame[col] = np.nan
    return all_frame


def filter_specs() -> list[tuple[str, Callable[[pd.DataFrame], pd.Series]]]:
    def always(df: pd.DataFrame) -> pd.Series:
        return pd.Series(True, index=df.index)

    specs: list[tuple[str, Callable[[pd.DataFrame], pd.Series]]] = [("none", always)]
    turnover_ranges = [
        ("turnover>=3", 3, None),
        ("turnover>=5", 5, None),
        ("turnover>=8", 8, None),
        ("turnover_3_20", 3, 20),
        ("turnover_5_20", 5, 20),
        ("turnover_5_30", 5, 30),
    ]
    for name, lo, hi in turnover_ranges:
        specs.append((name, lambda df, lo=lo, hi=hi: (df["turnover"] >= lo) & (True if hi is None else df["turnover"] <= hi)))

    close_ranges = [
        ("close_3_60", 3, 60),
        ("close_5_60", 5, 60),
        ("close_5_100", 5, 100),
        ("close>=3", 3, None),
        ("close>=5", 5, None),
    ]
    for name, lo, hi in close_ranges:
        specs.append((name, lambda df, lo=lo, hi=hi: (df["close"] >= lo) & (True if hi is None else df["close"] <= hi)))

    combo_specs = [
        ("turnover_5_20|close_3_60", lambda df: (df["turnover"] >= 5) & (df["turnover"] <= 20) & (df["close"] >= 3) & (df["close"] <= 60)),
        ("turnover_5_20|close_5_60", lambda df: (df["turnover"] >= 5) & (df["turnover"] <= 20) & (df["close"] >= 5) & (df["close"] <= 60)),
        ("turnover_3_30|close_3_100", lambda df: (df["turnover"] >= 3) & (df["turnover"] <= 30) & (df["close"] >= 3) & (df["close"] <= 100)),
        ("turnover>=5|rsi6<=60", lambda df: (df["turnover"] >= 5) & (df["rsi_6"] <= 60)),
        ("turnover>=5|range>=2", lambda df: (df["turnover"] >= 5) & (df["range_pct"] >= 2)),
        ("turnover>=5|amount_z>=0", lambda df: (df["turnover"] >= 5) & (df["amount_z_20"] >= 0)),
        ("turnover>=5|volume_z>=0", lambda df: (df["turnover"] >= 5) & (df["volume_z_20"] >= 0)),
        ("rsi6<=45", lambda df: df["rsi_6"] <= 45),
        ("rsi6<=55", lambda df: df["rsi_6"] <= 55),
        ("range>=2", lambda df: df["range_pct"] >= 2),
        ("amount_z>=0", lambda df: df["amount_z_20"] >= 0),
        ("volume_z>=0", lambda df: df["volume_z_20"] >= 0),
    ]
    specs.extend(combo_specs)
    return specs


def add_rank_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["activity_range_x_turnover_z"] = out["range_pct"].fillna(0) * out["turnover_z_20"].fillna(0)
    out["activity_range_x_turnover"] = out["range_pct"].fillna(0) * out["turnover"].fillna(0)
    out["low_rsi_score"] = -out["rsi_6"].fillna(999)
    return out


def select_group(group: pd.DataFrame, sort_col: str, rank_recipe: str, top_n: int) -> pd.DataFrame:
    if rank_recipe == "prob_desc":
        ordered = group.sort_values([sort_col, "symbol"], ascending=[False, True])
    elif rank_recipe == "rsi6_low":
        ordered = group.sort_values(["rsi_6", sort_col, "symbol"], ascending=[True, False, True])
    elif rank_recipe == "score_then_rsi6_low":
        ordered = group.sort_values([sort_col, "rsi_6", "symbol"], ascending=[False, True, True])
    elif rank_recipe == "activity_turnover_z_high":
        ordered = group.sort_values(["activity_range_x_turnover_z", sort_col, "symbol"], ascending=[False, False, True])
    elif rank_recipe == "activity_turnover_high":
        ordered = group.sort_values(["activity_range_x_turnover", sort_col, "symbol"], ascending=[False, False, True])
    elif rank_recipe == "turnover_z_high":
        ordered = group.sort_values(["turnover_z_20", sort_col, "symbol"], ascending=[False, False, True])
    elif rank_recipe == "amount_z_high":
        ordered = group.sort_values(["amount_z_20", sort_col, "symbol"], ascending=[False, False, True])
    elif rank_recipe == "volume_z_high":
        ordered = group.sort_values(["volume_z_20", sort_col, "symbol"], ascending=[False, False, True])
    elif rank_recipe == "range_high":
        ordered = group.sort_values(["range_pct", sort_col, "symbol"], ascending=[False, False, True])
    else:
        raise ValueError(rank_recipe)
    return ordered.head(top_n)


def compute_realized(df: pd.DataFrame, exit_mode: str) -> pd.Series:
    close_ret = df["next_close_return_pct"].fillna(0).astype(float)
    low_ret = df["next_low_return_pct"].fillna(close_ret).astype(float)
    if exit_mode == "close":
        return close_ret
    if exit_mode == "stop1_close":
        return pd.Series(np.where(low_ret <= -1.0, -1.0, close_ret), index=df.index)
    if exit_mode == "stop2_close":
        return pd.Series(np.where(low_ret <= -2.0, -2.0, close_ret), index=df.index)
    raise ValueError(exit_mode)


def eval_strategy(df: pd.DataFrame, spec: dict) -> tuple[dict, pd.DataFrame]:
    score_col = spec["score_col"]
    mask = df[score_col] >= spec["threshold"]
    mask &= spec["filter_mask"]
    pool = add_rank_columns(df[mask].copy())

    selected_parts = []
    for _, group in pool.groupby("date", sort=True):
        selected_parts.append(select_group(group, spec["sort_col"], spec["rank_recipe"], spec["top_n"]))

    if not selected_parts:
        return {}, pd.DataFrame()
    selected = pd.concat(selected_parts, ignore_index=True)
    selected["realized_pct"] = compute_realized(selected, spec["exit_mode"])
    selected["win"] = selected["realized_pct"] > 0

    daily = (
        selected.groupby(["month", "date"], sort=True)
        .agg(
            picks=("symbol", "count"),
            daily_return_pct=("realized_pct", "mean"),
            daily_win=("realized_pct", lambda s: float(s.mean() > 0)),
            ticket_win_rate=("win", "mean"),
            avg_next_high=("next_high_return_pct", "mean"),
            avg_next_close=("next_close_return_pct", "mean"),
        )
        .reset_index()
    )
    monthly_rows = []
    for month, mg in daily.groupby("month", sort=True):
        monthly_rows.append(
            {
                "month": month,
                "signal_days": int(mg["date"].nunique()),
                "tickets": int(mg["picks"].sum()),
                "daily_win_rate": float(mg["daily_win"].mean()),
                "ticket_win_rate": float(selected.loc[selected["month"] == month, "win"].mean()),
                "return_pct": pct_prod(mg["daily_return_pct"]),
                "avg_daily_return_pct": float(mg["daily_return_pct"].mean()),
            }
        )

    total_days = int(daily["date"].nunique())
    total_tickets = int(len(selected))
    result = {
        "score_col": score_col,
        "sort_col": spec["sort_col"],
        "threshold": float(spec["threshold"]),
        "top_n": int(spec["top_n"]),
        "filter_name": spec["filter_name"],
        "rank_recipe": spec["rank_recipe"],
        "exit_mode": spec["exit_mode"],
        "signal_days": total_days,
        "tickets": total_tickets,
        "avg_picks_per_signal_day": float(total_tickets / total_days) if total_days else 0.0,
        "active_months": int(len(monthly_rows)),
        "total_return_pct": pct_prod(daily["daily_return_pct"]),
        "avg_daily_return_pct": float(daily["daily_return_pct"].mean()),
        "daily_win_rate": float(daily["daily_win"].mean()),
        "ticket_win_rate": float(selected["win"].mean()),
        "sharpe_like": sharpe_like(daily["daily_return_pct"]),
        "max_daily_loss_pct": float(daily["daily_return_pct"].min()),
        "max_daily_gain_pct": float(daily["daily_return_pct"].max()),
        "max_ticket_loss_pct": float(selected["realized_pct"].min()),
        "max_ticket_gain_pct": float(selected["realized_pct"].max()),
        "months": monthly_rows,
    }
    return result, selected


def sort_pool(pool: pd.DataFrame, sort_col: str, rank_recipe: str) -> pd.DataFrame:
    if rank_recipe == "prob_desc":
        ordered = pool.sort_values(["date", sort_col, "symbol"], ascending=[True, False, True])
    elif rank_recipe == "rsi6_low":
        ordered = pool.sort_values(["date", "rsi_6", sort_col, "symbol"], ascending=[True, True, False, True])
    elif rank_recipe == "score_then_rsi6_low":
        ordered = pool.sort_values(["date", sort_col, "rsi_6", "symbol"], ascending=[True, False, True, True])
    elif rank_recipe == "activity_turnover_z_high":
        ordered = pool.sort_values(["date", "activity_range_x_turnover_z", sort_col, "symbol"], ascending=[True, False, False, True])
    elif rank_recipe == "activity_turnover_high":
        ordered = pool.sort_values(["date", "activity_range_x_turnover", sort_col, "symbol"], ascending=[True, False, False, True])
    elif rank_recipe == "turnover_z_high":
        ordered = pool.sort_values(["date", "turnover_z_20", sort_col, "symbol"], ascending=[True, False, False, True])
    elif rank_recipe == "amount_z_high":
        ordered = pool.sort_values(["date", "amount_z_20", sort_col, "symbol"], ascending=[True, False, False, True])
    elif rank_recipe == "volume_z_high":
        ordered = pool.sort_values(["date", "volume_z_20", sort_col, "symbol"], ascending=[True, False, False, True])
    elif rank_recipe == "range_high":
        ordered = pool.sort_values(["date", "range_pct", sort_col, "symbol"], ascending=[True, False, False, True])
    else:
        raise ValueError(rank_recipe)
    ordered = ordered.copy()
    ordered["daily_rank"] = ordered.groupby("date", sort=False).cumcount() + 1
    return ordered


def eval_ranked_strategy(ranked: pd.DataFrame, spec: dict, top_n: int, exit_mode: str) -> dict | None:
    selected = ranked[ranked["daily_rank"] <= top_n].copy()
    if selected.empty:
        return None
    selected["realized_pct"] = compute_realized(selected, exit_mode)
    selected["win"] = selected["realized_pct"] > 0
    daily = (
        selected.groupby(["month", "date"], sort=True)
        .agg(
            picks=("symbol", "count"),
            daily_return_pct=("realized_pct", "mean"),
            daily_win=("realized_pct", lambda s: float(s.mean() > 0)),
            ticket_win_rate=("win", "mean"),
            avg_next_high=("next_high_return_pct", "mean"),
            avg_next_close=("next_close_return_pct", "mean"),
        )
        .reset_index()
    )
    monthly_rows = []
    for month, mg in daily.groupby("month", sort=True):
        monthly_rows.append(
            {
                "month": month,
                "signal_days": int(mg["date"].nunique()),
                "tickets": int(mg["picks"].sum()),
                "daily_win_rate": float(mg["daily_win"].mean()),
                "ticket_win_rate": float(selected.loc[selected["month"] == month, "win"].mean()),
                "return_pct": pct_prod(mg["daily_return_pct"]),
                "avg_daily_return_pct": float(mg["daily_return_pct"].mean()),
            }
        )
    total_days = int(daily["date"].nunique())
    total_tickets = int(len(selected))
    return {
        "score_col": spec["score_col"],
        "sort_col": spec["sort_col"],
        "threshold": float(spec["threshold"]),
        "top_n": int(top_n),
        "filter_name": spec["filter_name"],
        "rank_recipe": spec["rank_recipe"],
        "exit_mode": exit_mode,
        "signal_days": total_days,
        "tickets": total_tickets,
        "avg_picks_per_signal_day": float(total_tickets / total_days) if total_days else 0.0,
        "active_months": int(len(monthly_rows)),
        "total_return_pct": pct_prod(daily["daily_return_pct"]),
        "avg_daily_return_pct": float(daily["daily_return_pct"].mean()),
        "daily_win_rate": float(daily["daily_win"].mean()),
        "ticket_win_rate": float(selected["win"].mean()),
        "sharpe_like": sharpe_like(daily["daily_return_pct"]),
        "max_daily_loss_pct": float(daily["daily_return_pct"].min()),
        "max_daily_gain_pct": float(daily["daily_return_pct"].max()),
        "max_ticket_loss_pct": float(selected["realized_pct"].min()),
        "max_ticket_gain_pct": float(selected["realized_pct"].max()),
        "months": monthly_rows,
    }


def strategy_search(df: pd.DataFrame) -> tuple[list[dict], dict[str, pd.DataFrame]]:
    thresholds = [round(x / 100.0, 2) for x in range(60, 91)]
    top_ns = [1, 2, 3, 4, 5, 6, 8, 10]
    rank_recipes = [
        "prob_desc",
        "score_then_rsi6_low",
        "rsi6_low",
        "activity_turnover_z_high",
        "activity_turnover_high",
        "turnover_z_high",
        "amount_z_high",
        "volume_z_high",
        "range_high",
    ]
    exit_modes = ["close", "stop1_close", "stop2_close"]

    filters = []
    for name, fn in filter_specs():
        try:
            filters.append((name, fn(df).fillna(False)))
        except Exception:
            continue

    results: list[dict] = []
    saved_selected: dict[str, pd.DataFrame] = {}
    for score_col in ["raw_prob", "iso_prob"]:
        for filter_name, filter_mask in filters:
            for threshold in thresholds:
                base_count = int(((df[score_col] >= threshold) & filter_mask).sum())
                if base_count == 0:
                    continue
                base = df[(df[score_col] >= threshold) & filter_mask].copy()
                if base["month"].nunique() < 4:
                    continue
                base = add_rank_columns(base)
                for rank_recipe in rank_recipes:
                    ranked = sort_pool(base, score_col, rank_recipe)
                    if ranked.empty:
                        continue
                    for top_n in top_ns:
                        for exit_mode in exit_modes:
                            spec = {
                                "score_col": score_col,
                                "sort_col": score_col,
                                "threshold": threshold,
                                "top_n": top_n,
                                "filter_name": filter_name,
                                "filter_mask": filter_mask,
                                "rank_recipe": rank_recipe,
                                "exit_mode": exit_mode,
                            }
                            result = eval_ranked_strategy(ranked, spec, top_n, exit_mode)
                            if not result:
                                continue
                            # Usability guard: all target months should participate and avoid tiny lucky samples.
                            if result["active_months"] < 4 or result["signal_days"] < 30 or result["tickets"] < 40:
                                continue
                            key = f"{score_col}|{threshold}|{top_n}|{filter_name}|{rank_recipe}|{exit_mode}"
                            result["strategy_key"] = key
                            results.append(result)
    return results, saved_selected


def brief(result: dict) -> dict:
    return {
        k: result[k]
        for k in [
            "strategy_key",
            "score_col",
            "threshold",
            "top_n",
            "filter_name",
            "rank_recipe",
            "exit_mode",
            "signal_days",
            "tickets",
            "active_months",
            "total_return_pct",
            "daily_win_rate",
            "ticket_win_rate",
            "sharpe_like",
            "max_daily_loss_pct",
            "max_daily_gain_pct",
        ]
    }


def main() -> None:
    df = build_frames()
    results, _ = strategy_search(df)
    if not results:
        raise RuntimeError("No strategy passed usability guards")

    results_sorted = sorted(results, key=lambda r: (r["total_return_pct"], r["daily_win_rate"], r["signal_days"]), reverse=True)
    raw_sorted = [r for r in results_sorted if r["score_col"] == "raw_prob"]
    iso_sorted = [r for r in results_sorted if r["score_col"] == "iso_prob"]

    # A less aggressive ranking for reference: return first, but penalize weak win rate and large losses.
    for r in results:
        r["balanced_score"] = (
            r["total_return_pct"]
            + 100.0 * (r["daily_win_rate"] - 0.70)
            + 0.5 * (r["sharpe_like"] or 0.0)
            + 3.0 * min(r["max_daily_loss_pct"], 0.0)
        )
    balanced_sorted = sorted(results, key=lambda r: r["balanced_score"], reverse=True)

    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "return_strategy_search",
        "methodology": "frozen score-only selector search; 2023-02/03/04 + 2026-04; raw_prob and iso_prob compared separately",
        "rows": int(len(df)),
        "months": sorted(df["month"].unique().tolist()),
        "total_strategies_kept_after_guards": len(results),
        "guards": {
            "active_months_min": 4,
            "signal_days_min": 30,
            "tickets_min": 40,
        },
        "best_total_return": brief(results_sorted[0]),
        "best_raw_total_return": brief(raw_sorted[0]) if raw_sorted else None,
        "best_iso_total_return": brief(iso_sorted[0]) if iso_sorted else None,
        "best_balanced": brief(balanced_sorted[0]),
        "top20_total_return": [brief(r) | {"months": r["months"]} for r in results_sorted[:20]],
        "top10_raw": [brief(r) | {"months": r["months"]} for r in raw_sorted[:10]],
        "top10_iso": [brief(r) | {"months": r["months"]} for r in iso_sorted[:10]],
    }
    OUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame([brief(r) for r in results_sorted[:500]]).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"JSON: {OUT_JSON}")
    print(f"CSV: {OUT_CSV}")


if __name__ == "__main__":
    main()
