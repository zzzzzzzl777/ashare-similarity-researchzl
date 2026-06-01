"""Full-period strategy search for S2 and PhaseC.

This is a score-only search. It does not retrain either model.

Goal requested by user:
maximize strategy return from 2023-01 to the latest available labeled day,
for S2 and PhaseC separately.

Important caveat:
This is an in-sample strategy search over a long period that includes model
training-era dates. The top-return strategy is useful for exploration, but it is
not a clean production validation by itself.
"""

from __future__ import annotations

import json
import heapq
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import scripts.run_dual_model_strategy_search as base


OUT_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
DESKTOP = Path(r"C:\Users\zzzzzzl\Desktop")

RUN_TAG = "full_period_strategy_search_20260511"
OUT_JSON = OUT_DIR / f"{RUN_TAG}.json"
OUT_MD = ROOT / "docs" / f"{RUN_TAG}.md"
OUT_S2_CSV = OUT_DIR / f"{RUN_TAG}_s2_top500.csv"
OUT_PC_CSV = OUT_DIR / f"{RUN_TAG}_phasec_top500.csv"


SEGMENTS = [
    {
        "name": "2023-01 strict jan cache",
        "cache": Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\jan_2023_patched.parquet"),
        "start": "2023-01-01",
        "end": "2023-01-31",
        "quality": "strict",
    },
    {
        "name": "2023-02..04 strict pretrain cache",
        "cache": Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\pretrain_2023_02_04_patched.parquet"),
        "start": "2023-02-01",
        "end": "2023-04-30",
        "quality": "strict",
    },
    {
        "name": "2023-05 degraded cache",
        "cache": Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_bdb756c513324618.parquet"),
        "start": "2023-05-01",
        "end": "2023-06-07",
        "quality": "degraded_missing_bundle_features",
    },
    {
        "name": "2023-06..2026-05 strict main cache",
        "cache": Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_31ffa0367a4d893f.parquet"),
        "start": "2023-06-08",
        "end": "2026-05-31",
        "quality": "strict",
    },
]


def compute_all_exits_fast(df: pd.DataFrame) -> dict[str, object]:
    """Fast conservative exit arrays for large-grid search.

    The original helper resolves same-day SL+TP collisions with 5-minute bars.
    That is appropriate for a small candidate set, but too slow when sweeping
    all rows and all exit modes across 800+ days. For the coarse full-period
    search, same-day SL+TP collisions are conservatively counted as stop-loss.
    """
    import numpy as np

    close_ret = df["next_close_return_pct"].fillna(0).to_numpy(dtype=np.float64)
    high_ret = df["next_high_return_pct"].to_numpy(dtype=np.float64)
    low_ret = df["next_low_return_pct"].to_numpy(dtype=np.float64)
    high_ret = np.where(np.isnan(high_ret), close_ret, high_ret)
    low_ret = np.where(np.isnan(low_ret), close_ret, low_ret)

    exits: dict[str, object] = {}
    for mode_name, sl_pct, tp_pct in base.EXIT_MODES:
        if sl_pct is None and tp_pct is None:
            exits[mode_name] = close_ret.copy()
        elif sl_pct is not None and tp_pct is None:
            exits[mode_name] = np.where(low_ret <= sl_pct, sl_pct, close_ret)
        elif tp_pct is not None and sl_pct is None:
            exits[mode_name] = np.where(high_ret >= tp_pct, tp_pct, close_ret)
        else:
            sl_hit = low_ret <= sl_pct
            tp_hit = high_ret >= tp_pct
            result = close_ret.copy()
            result[tp_hit & ~sl_hit] = tp_pct
            result[sl_hit] = sl_pct
            exits[mode_name] = result
    return exits


def pct_prod_fast(arr: np.ndarray) -> float:
    if arr.size == 0:
        return 0.0
    v = np.clip(arr / 100.0, -0.95, 10.0)
    return float((np.prod(1.0 + v) - 1.0) * 100.0)


def sharpe_fast(arr: np.ndarray) -> float | None:
    if arr.size < 3:
        return None
    std = float(arr.std(ddof=1))
    if std == 0:
        return None
    return float(arr.mean() / std * math.sqrt(252))


class TopKeeper:
    def __init__(self, limit: int, key: str):
        self.limit = limit
        self.key = key
        self.heap: list[tuple[float, int, dict]] = []
        self.counter = 0

    def push(self, record: dict) -> None:
        score = record.get(self.key)
        if score is None:
            return
        item = (float(score), self.counter, record.copy())
        self.counter += 1
        if len(self.heap) < self.limit:
            heapq.heappush(self.heap, item)
        elif item[0] > self.heap[0][0]:
            heapq.heapreplace(self.heap, item)

    def sorted_desc(self) -> list[dict]:
        return [item[2] for item in sorted(self.heap, key=lambda x: x[0], reverse=True)]


def build_selected_cube(
    df: pd.DataFrame,
    score_col: str,
    recipe: str,
    filter_mask: np.ndarray,
    thresholds: list[float],
    day_indices: list[np.ndarray],
    max_top: int = 6,
) -> np.ndarray:
    """Selected row indices for all thresholds, days and top slots.

    For each day, rows are sorted once by the requested rank recipe. Each
    threshold then takes the first max_top rows that pass the probability gate.
    This is equivalent to daily top-N after thresholding, but avoids rebuilding
    a full rank vector for every threshold.
    """
    score = df[score_col].fillna(0).to_numpy(dtype=np.float64)
    sort_key = base.compute_sort_key(df, score_col, recipe)
    cube = np.full((len(thresholds), len(day_indices), max_top), -1, dtype=np.int32)

    for day_no, day_idx in enumerate(day_indices):
        idx = day_idx[filter_mask[day_idx]]
        if idx.size == 0:
            continue
        idx = idx[np.argsort(-sort_key[idx], kind="mergesort")]
        day_score = score[idx]
        for t_no, threshold in enumerate(thresholds):
            selected = idx[day_score >= threshold][:max_top]
            if selected.size:
                cube[t_no, day_no, : selected.size] = selected
    return cube


def eval_selection_cube(
    selected_for_threshold: np.ndarray,
    exits: dict[str, np.ndarray],
    actual: np.ndarray,
    day_months: np.ndarray,
    month_labels: np.ndarray,
    top_n: int,
    exit_mode: str,
    include_months: bool = False,
) -> dict | None:
    idx = selected_for_threshold[:, :top_n]
    valid = idx >= 0
    counts = valid.sum(axis=1)
    day_valid = counts > 0
    signal_days = int(day_valid.sum())
    tickets = int(counts.sum())
    if signal_days < 30 or tickets < 20:
        return None

    safe_idx = np.where(valid, idx, 0)
    realized_values = exits[exit_mode][safe_idx]
    realized_values = np.where(valid, realized_values, 0.0)
    daily_sum = realized_values.sum(axis=1)
    daily_avg_all = np.zeros(len(counts), dtype=np.float64)
    daily_avg_all[day_valid] = daily_sum[day_valid] / counts[day_valid]
    daily_returns = daily_avg_all[day_valid]

    actual_values = actual[safe_idx]
    actual_values = np.where(valid, actual_values, 0.0)
    high1 = float(actual_values.sum() / tickets)
    ticket_win = float(((realized_values > 0) & valid).sum() / tickets)
    daily_win = float((daily_returns > 0).mean())
    total_return = pct_prod_fast(daily_returns)
    sh = sharpe_fast(daily_returns)

    month_rets: list[float] = []
    monthly_rows: list[dict] = []
    for month in month_labels:
        m_day = day_valid & (day_months == month)
        if not m_day.any():
            continue
        m_daily = daily_avg_all[m_day]
        m_ret = pct_prod_fast(m_daily)
        month_rets.append(m_ret)
        if include_months:
            m_ticket_mask = m_day[:, None] & valid
            m_tickets = int(m_ticket_mask.sum())
            m_realized = realized_values[m_ticket_mask]
            m_actual = actual_values[m_ticket_mask]
            monthly_rows.append(
                {
                    "month": str(month),
                    "signal_days": int(m_day.sum()),
                    "tickets": m_tickets,
                    "daily_win_rate": float((m_daily > 0).mean()),
                    "ticket_win_rate": float((m_realized > 0).mean()) if m_tickets else 0.0,
                    "high1_hit_rate": float(m_actual.mean()) if m_tickets else 0.0,
                    "return_pct": m_ret,
                    "avg_daily_return_pct": float(m_daily.mean()),
                }
            )

    months_total = len(month_rets)
    months_positive = sum(1 for x in month_rets if x > 0)
    max_month = max(month_rets) if month_rets else 0.0
    min_month = min(month_rets) if month_rets else 0.0
    single_month_risk = (months_total >= 3 and months_positive <= 1) or (
        max_month > 0 and min_month < -10
    )

    balanced_score = (
        total_return
        + 80.0 * (daily_win - 0.55)
        + 0.3 * (sh or 0.0)
        + 2.0 * min(float(daily_returns.min()), 0.0)
        - 30.0 * (1 if single_month_risk else 0)
    )
    robust_score = (
        total_return * 0.4
        + 120.0 * (daily_win - 0.50)
        + 0.5 * (sh or 0.0)
        + 3.0 * min(float(daily_returns.min()), 0.0)
        - 50.0 * (1 if single_month_risk else 0)
        + (50.0 * (months_positive / months_total - 0.5) if months_total else 0.0)
    )

    result = {
        "signal_days": signal_days,
        "tickets": tickets,
        "avg_picks_per_day": round(tickets / signal_days, 2),
        "total_return_pct": total_return,
        "avg_daily_return_pct": float(daily_returns.mean()),
        "daily_win_rate": daily_win,
        "ticket_win_rate": ticket_win,
        "high1_hit_rate": high1,
        "high1_w95": base.wilson_lower(tickets, high1),
        "sharpe": sh,
        "max_daily_loss_pct": float(daily_returns.min()),
        "max_daily_gain_pct": float(daily_returns.max()),
        "months_positive": months_positive,
        "months_total": months_total,
        "single_month_risk": single_month_risk,
        "balanced_score": balanced_score,
        "robust_score": robust_score,
    }
    if include_months:
        result["months"] = monthly_rows
    return result


def run_search_for_model_fast(model_name: str, df: pd.DataFrame) -> tuple[list[dict], dict]:
    print(f"\n{'='*60}", flush=True)
    print(f"  Fast strategy search: {model_name} ({len(df):,} rows, {df['date'].nunique()} days)", flush=True)
    print(f"{'='*60}", flush=True)

    print("  Computing exit returns...", flush=True)
    t0 = time.time()
    exits = compute_all_exits_fast(df)
    print(f"    Done in {time.time()-t0:.1f}s", flush=True)

    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"], sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    day_months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()
    month_labels = np.array(sorted(set(day_months)))

    filters = base.build_filters(df)
    thresholds = [round(x / 100.0, 2) for x in range(50, 91)]
    top_ns = [1, 2, 3, 4, 5, 6]

    by_return = TopKeeper(1000, "total_return_pct")
    by_robust = TopKeeper(1000, "robust_score")
    total_combos = 0
    kept = 0
    t0 = time.time()

    for score_col in ["raw_prob", "iso_prob"]:
        for filter_name, filter_mask in filters:
            for recipe in base.RANK_RECIPES:
                cube = build_selected_cube(
                    df, score_col, recipe, filter_mask, thresholds, day_indices, max_top=max(top_ns)
                )
                for threshold_no, threshold in enumerate(thresholds):
                    selected = cube[threshold_no]
                    for top_n in top_ns:
                        if int((selected[:, :top_n] >= 0).sum()) < 20:
                            total_combos += len(base.EXIT_MODES)
                            continue
                        for exit_name, _, _ in base.EXIT_MODES:
                            total_combos += 1
                            record = eval_selection_cube(
                                selected, exits, actual, day_months, month_labels, top_n, exit_name
                            )
                            if not record:
                                continue
                            if record["months_total"] < 3 or record["signal_days"] < 30:
                                continue
                            record.update(
                                {
                                    "score_col": score_col,
                                    "threshold": float(threshold),
                                    "top_n": int(top_n),
                                    "filter_name": filter_name,
                                    "rank_recipe": recipe,
                                    "exit_mode": exit_name,
                                    "model": model_name,
                                }
                            )
                            kept += 1
                            by_return.push(record)
                            by_robust.push(record)

                print(
                    f"    {score_col} | {filter_name} | {recipe} | "
                    f"{total_combos:,} combos, {kept:,} kept, {time.time()-t0:.0f}s",
                    flush=True,
                )

    elapsed = time.time() - t0
    print(f"  Done: {total_combos:,} combos, {kept:,} kept in {elapsed:.0f}s", flush=True)

    top_return = by_return.sorted_desc()
    top_robust = by_robust.sorted_desc()
    summary = {
        "model": model_name,
        "total_combos": total_combos,
        "kept": kept,
        "elapsed_s": round(elapsed, 1),
        "best_return": top_return[0] if top_return else None,
        "best_robust": top_robust[0] if top_robust else None,
        "top20_return": top_return[:20],
        "top20_robust": top_robust[:20],
    }
    return top_return, summary


def enrich_months_for_strategy(df: pd.DataFrame, strategy: dict | None) -> dict | None:
    if not strategy:
        return None
    exits = compute_all_exits_fast(df)
    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"], sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    day_months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()
    month_labels = np.array(sorted(set(day_months)))
    filters = {name: mask for name, mask in base.build_filters(df)}
    cube = build_selected_cube(
        df,
        strategy["score_col"],
        strategy["rank_recipe"],
        filters[strategy["filter_name"]],
        [float(strategy["threshold"])],
        day_indices,
        max_top=max(6, int(strategy["top_n"])),
    )
    detail = eval_selection_cube(
        cube[0],
        exits,
        actual,
        day_months,
        month_labels,
        int(strategy["top_n"]),
        strategy["exit_mode"],
        include_months=True,
    )
    if detail:
        strategy.update(detail)
    return strategy


def load_full_frame(model_label: str, bundle: dict) -> tuple[pd.DataFrame, list[dict]]:
    frames: list[pd.DataFrame] = []
    audit: list[dict] = []
    feature_names = bundle["feature_names"]

    for seg in SEGMENTS:
        schema = set(pq.read_schema(str(seg["cache"])).names)
        missing = [f for f in feature_names if f not in schema]
        t0 = time.time()
        frame = base.load_scoring_frame(
            seg["cache"], bundle, seg["start"], seg["end"], f"{model_label}:{seg['name']}"
        )
        frame["source_segment"] = seg["name"]
        frame["source_quality"] = seg["quality"]
        frame["missing_bundle_features"] = len(missing)
        frames.append(frame)
        audit.append(
            {
                "model": model_label,
                "segment": seg["name"],
                "cache": str(seg["cache"]),
                "quality": seg["quality"],
                "start": seg["start"],
                "end": seg["end"],
                "rows": int(len(frame)),
                "days": int(frame["date"].nunique()) if len(frame) else 0,
                "min_date": str(frame["date"].min()) if len(frame) else None,
                "max_date": str(frame["date"].max()) if len(frame) else None,
                "missing_bundle_features": len(missing),
                "load_seconds": round(time.time() - t0, 1),
            }
        )
        print(
            f"  {model_label} {seg['name']}: rows={len(frame):,}, "
            f"days={frame['date'].nunique() if len(frame) else 0}, missing={len(missing)}",
            flush=True,
        )

    df = pd.concat(frames, ignore_index=True)
    before = len(df)
    df = df.drop_duplicates(subset=["date", "symbol"], keep="first").reset_index(drop=True)
    if len(df) != before:
        print(f"  {model_label}: dropped duplicate date/symbol rows {before-len(df):,}", flush=True)
    return df, audit


def add_scores(label: str, bundle: dict, df: pd.DataFrame) -> pd.DataFrame:
    print(f"Scoring {label}: {len(df):,} rows, {df['date'].nunique()} days...", flush=True)
    t0 = time.time()
    raw, iso = base.predict_raw_and_iso(bundle, df)
    out = df.copy()
    out["raw_prob"] = raw
    out["iso_prob"] = iso
    print(f"  scored in {time.time()-t0:.1f}s", flush=True)
    return out


def compact_strategy(r: dict | None) -> dict | None:
    if not r:
        return None
    keys = [
        "model",
        "score_col",
        "threshold",
        "top_n",
        "filter_name",
        "rank_recipe",
        "exit_mode",
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
        "balanced_score",
        "robust_score",
        "months",
    ]
    return {k: r.get(k) for k in keys}


def save_top_csv(results: list[dict], path: Path) -> None:
    rows = []
    for r in sorted(results, key=lambda x: x["total_return_pct"], reverse=True)[:500]:
        rows.append(
            {
                k: r.get(k)
                for k in [
                    "model",
                    "score_col",
                    "threshold",
                    "top_n",
                    "filter_name",
                    "rank_recipe",
                    "exit_mode",
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
                    "balanced_score",
                    "robust_score",
                ]
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def monthly_table(strategy: dict | None) -> str:
    if not strategy:
        return "_No valid strategy._"
    rows = strategy.get("months") or []
    lines = [
        "| Month | Days | Tickets | Return | Avg Daily | Daily Win | Ticket Win | High+1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for m in rows:
        lines.append(
            f"| {m['month']} | {m['signal_days']} | {m['tickets']} | "
            f"{m['return_pct']:.2f}% | {m['avg_daily_return_pct']:.2f}% | "
            f"{m['daily_win_rate']:.1%} | {m['ticket_win_rate']:.1%} | {m['high1_hit_rate']:.1%} |"
        )
    return "\n".join(lines)


def strategy_line(s: dict | None) -> str:
    if not s:
        return "_No valid strategy._"
    return (
        f"`{s['score_col']}>={s['threshold']}` | top{s['top_n']} | "
        f"`{s['filter_name']}` | `{s['rank_recipe']}` | `{s['exit_mode']}`  \n"
        f"Return **{s['total_return_pct']:.2f}%**, days {s['signal_days']}, tickets {s['tickets']}, "
        f"daily win {s['daily_win_rate']:.1%}, ticket win {s['ticket_win_rate']:.1%}, "
        f"high+1 {s['high1_hit_rate']:.1%}, W95 {s['high1_w95']:.1%}, "
        f"max daily loss {s['max_daily_loss_pct']:.2f}%, Sharpe {s.get('sharpe') or 0:.2f}."
    )


def main() -> None:
    base.compute_all_exits = compute_all_exits_fast

    print("Loading bundles...", flush=True)
    s2_bundle = base.load_bundle(base.S2_BUNDLE)
    pc_bundle = base.load_bundle(base.PC_BUNDLE)
    print(f"S2 features={len(s2_bundle['feature_names'])}", flush=True)
    print(f"PhaseC features={len(pc_bundle['feature_names'])}", flush=True)

    print("\nLoading full frames...", flush=True)
    s2_df, s2_audit = load_full_frame("S2", s2_bundle)
    pc_df, pc_audit = load_full_frame("PhaseC", pc_bundle)

    s2_df = add_scores("S2", s2_bundle, s2_df)
    pc_df = add_scores("PhaseC", pc_bundle, pc_df)

    print("\nRunning S2 full-period search...", flush=True)
    s2_results, s2_summary = run_search_for_model_fast("S2_full_202301_now", s2_df)
    print("\nRunning PhaseC full-period search...", flush=True)
    pc_results, pc_summary = run_search_for_model_fast("PhaseC_full_202301_now", pc_df)

    for key in ["best_return", "best_robust"]:
        enrich_months_for_strategy(s2_df, s2_summary.get(key))
        enrich_months_for_strategy(pc_df, pc_summary.get(key))
    for item in s2_summary.get("top20_return", []):
        enrich_months_for_strategy(s2_df, item)
    for item in pc_summary.get("top20_return", []):
        enrich_months_for_strategy(pc_df, item)

    save_top_csv(s2_results, OUT_S2_CSV)
    save_top_csv(pc_results, OUT_PC_CSV)

    payload = {
        "run_tag": RUN_TAG,
        "created_at": pd.Timestamp.now().isoformat(),
        "objective": "maximize total return over available 2023-01 to latest labeled date",
        "caveat": "This is in-sample strategy optimization over a period that may include model training-era dates.",
        "segments": [{**seg, "cache": str(seg["cache"])} for seg in SEGMENTS],
        "audit": s2_audit + pc_audit,
        "s2": {
            "summary": {k: v for k, v in s2_summary.items() if k not in ("top20_return", "top20_robust", "best_return", "best_robust")},
            "best_return": compact_strategy(s2_summary.get("best_return")),
            "best_robust": compact_strategy(s2_summary.get("best_robust")),
            "top20_return": [compact_strategy(r) for r in s2_summary.get("top20_return", [])],
        },
        "phasec": {
            "summary": {k: v for k, v in pc_summary.items() if k not in ("top20_return", "top20_robust", "best_return", "best_robust")},
            "best_return": compact_strategy(pc_summary.get("best_return")),
            "best_robust": compact_strategy(pc_summary.get("best_robust")),
            "top20_return": [compact_strategy(r) for r in pc_summary.get("top20_return", [])],
        },
        "outputs": {
            "json": str(OUT_JSON),
            "md": str(OUT_MD),
            "s2_top500_csv": str(OUT_S2_CSV),
            "phasec_top500_csv": str(OUT_PC_CSV),
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    s2_best = payload["s2"]["best_return"]
    pc_best = payload["phasec"]["best_return"]
    md = [
        "# Full Period Strategy Search - 2023-01 to latest",
        "",
        "## Scope",
        "- Frozen S2 and PhaseC bundles only; no model retraining.",
        "- Objective requested here: maximize total compounded return over all available data from 2023-01.",
        "- This is an exploratory in-sample strategy search, not a clean production validation.",
        "- 2023-05 to 2023-06-07 uses a degraded cache with missing bundle features; other listed segments are strict.",
        "",
        "## Best Return - S2",
        strategy_line(s2_best),
        "",
        monthly_table(s2_best),
        "",
        "## Best Return - PhaseC",
        strategy_line(pc_best),
        "",
        monthly_table(pc_best),
        "",
        "## Data Audit",
        "| Model | Segment | Days | Rows | Missing Bundle Features | Quality |",
        "|---|---|---:|---:|---:|---|",
    ]
    for a in payload["audit"]:
        md.append(
            f"| {a['model']} | {a['segment']} | {a['days']} | {a['rows']} | "
            f"{a['missing_bundle_features']} | {a['quality']} |"
        )
    md.extend(
        [
            "",
            "## Output Files",
            f"- JSON: `{OUT_JSON}`",
            f"- S2 top500 CSV: `{OUT_S2_CSV}`",
            f"- PhaseC top500 CSV: `{OUT_PC_CSV}`",
        ]
    )
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print("\nDONE", flush=True)
    print(f"S2 best return: {s2_best['total_return_pct']:.2f}% | {s2_best['score_col']}>={s2_best['threshold']} top{s2_best['top_n']} {s2_best['rank_recipe']} {s2_best['exit_mode']} {s2_best['filter_name']}", flush=True)
    print(f"PhaseC best return: {pc_best['total_return_pct']:.2f}% | {pc_best['score_col']}>={pc_best['threshold']} top{pc_best['top_n']} {pc_best['rank_recipe']} {pc_best['exit_mode']} {pc_best['filter_name']}", flush=True)
    print(f"JSON: {OUT_JSON}", flush=True)
    print(f"MD: {OUT_MD}", flush=True)


if __name__ == "__main__":
    main()
