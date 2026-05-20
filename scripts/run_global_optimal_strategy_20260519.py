"""Global optimal strategy search: PhaseC on full 2017-2026 data.

Uses the 550a feature cache (877K rows, 2237 trading days, 2017-02 to 2026-04)
with the PhaseC bundle (200 selected features, CatBoost).

Search dimensions extended vs prior searches:
- Thresholds: 0.50-0.85 (step 0.01)
- Top N: 1-8
- 25 filters (existing 21 + 4 new combo filters)
- 11 rank recipes
- 19 exit modes
- 2 score columns (raw_prob, iso_prob)

Time windows evaluated per strategy:
- Full period (all data)
- OOS 2025-07 to 2026-04 (never seen in training)
- Recent 2026-01 to 2026-04 (most relevant for current market)
- Pretrain 2017-02 to 2023-04
- Train era 2023-05 to 2025-06

Ranking: composite score weighting recent OOS performance heavily.
"""

from __future__ import annotations

import heapq
import json
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

PC_BUNDLE = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt"
)
CACHE_FULL = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_550a77f54882058f.parquet"
)

OUT_DIR = Path(r"C:\Users\zzzzzzl\Desktop")
RUN_TAG = "global_optimal_strategy_20260519"

THRESHOLDS = [round(x / 100.0, 2) for x in range(50, 86)]
TOP_NS = [1, 2, 3, 4, 5, 6, 8]
SCORE_COLS = ["raw_prob", "iso_prob"]

EXIT_MODES = base.EXIT_MODES

RANK_RECIPES = base.RANK_RECIPES


def build_extended_filters(df: pd.DataFrame) -> list[tuple[str, np.ndarray]]:
    filters = base.build_filters(df)
    n = len(df)

    def s(col):
        return df[col].fillna(0).to_numpy(dtype=np.float64) if col in df.columns else np.zeros(n)

    t = s("turnover")
    c = s("close")
    az = s("amount_z_20")
    vz = s("volume_z_20")
    rng = s("range_pct")
    rsi6 = s("rsi_6")

    extras = [
        ("t3_15|c5_30", (t >= 3) & (t <= 15) & (c >= 5) & (c <= 30)),
        ("t5_20|c5_60|az>0", (t >= 5) & (t <= 20) & (c >= 5) & (c <= 60) & (az > 0)),
        ("close_10_50", (c >= 10) & (c <= 50)),
        ("az>0|vz>0", (az > 0) & (vz > 0)),
    ]
    for name, mask in extras:
        filters.append((name, mask))
    return filters


def compute_exits_fast(df: pd.DataFrame) -> dict[str, np.ndarray]:
    close_ret = df["next_close_return_pct"].fillna(0).to_numpy(dtype=np.float64)
    high_ret = df["next_high_return_pct"].to_numpy(dtype=np.float64)
    low_ret = df["next_low_return_pct"].to_numpy(dtype=np.float64)
    high_ret = np.where(np.isnan(high_ret), close_ret, high_ret)
    low_ret = np.where(np.isnan(low_ret), close_ret, low_ret)

    exits: dict[str, np.ndarray] = {}
    for mode_name, sl_pct, tp_pct in EXIT_MODES:
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


def pct_prod(arr: np.ndarray) -> float:
    if arr.size == 0:
        return 0.0
    v = np.clip(arr / 100.0, -0.95, 10.0)
    return float((np.prod(1.0 + v) - 1.0) * 100.0)


def sharpe(arr: np.ndarray) -> float | None:
    if arr.size < 3:
        return None
    std = float(arr.std(ddof=1))
    if std == 0:
        return None
    return float(arr.mean() / std * math.sqrt(252))


def max_drawdown_pct(daily_returns: np.ndarray) -> float:
    if daily_returns.size == 0:
        return 0.0
    cum = np.cumprod(1.0 + np.clip(daily_returns / 100.0, -0.95, 10.0))
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak * 100.0
    return float(dd.min())


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


def build_cube(
    df: pd.DataFrame,
    score_col: str,
    recipe: str,
    filter_mask: np.ndarray,
    thresholds: list[float],
    day_indices: list[np.ndarray],
    max_top: int,
) -> np.ndarray:
    score = df[score_col].fillna(0).to_numpy(dtype=np.float64)
    sort_key = base.compute_sort_key(df, score_col, recipe)
    cube = np.full((len(thresholds), len(day_indices), max_top), -1, dtype=np.int32)
    for day_no, day_idx in enumerate(day_indices):
        idx = day_idx[filter_mask[day_idx]]
        if idx.size == 0:
            continue
        idx = idx[np.argsort(-sort_key[idx], kind="mergesort")]
        day_score = score[idx]
        for t_no, thr in enumerate(thresholds):
            sel = idx[day_score >= thr][:max_top]
            if sel.size:
                cube[t_no, day_no, :sel.size] = sel
    return cube


def eval_cube_multiwindow(
    cube_for_thr: np.ndarray,
    exits: dict[str, np.ndarray],
    actual: np.ndarray,
    day_dates: np.ndarray,
    top_n: int,
    exit_mode: str,
) -> dict | None:
    idx = cube_for_thr[:, :top_n]
    valid = idx >= 0
    counts = valid.sum(axis=1)
    day_valid = counts > 0
    signal_days = int(day_valid.sum())
    tickets = int(counts.sum())
    if signal_days < 20 or tickets < 20:
        return None

    safe_idx = np.where(valid, idx, 0)
    realized = exits[exit_mode][safe_idx]
    realized = np.where(valid, realized, 0.0)
    daily_sum = realized.sum(axis=1)
    daily_avg = np.zeros(len(counts), dtype=np.float64)
    daily_avg[day_valid] = daily_sum[day_valid] / counts[day_valid]
    daily_returns = daily_avg[day_valid]

    actual_vals = actual[safe_idx]
    actual_vals = np.where(valid, actual_vals, 0.0)
    high1 = float(actual_vals.sum() / tickets)
    ticket_win = float(((realized > 0) & valid).sum() / tickets)
    daily_win = float((daily_returns > 0).mean())
    total_return = pct_prod(daily_returns)
    sh = sharpe(daily_returns)
    mdd = max_drawdown_pct(daily_returns)

    valid_day_dates = day_dates[day_valid]
    daily_returns_full = daily_avg

    windows = {
        "full": (None, None),
        "oos": ("2025-07-01", None),
        "recent_q1q2": ("2026-01-01", None),
        "pretrain": (None, "2023-04-30"),
        "train_era": ("2023-05-01", "2025-06-30"),
    }
    window_metrics = {}
    for wname, (wstart, wend) in windows.items():
        wmask = np.ones(len(day_dates), dtype=bool)
        if wstart:
            wmask &= day_dates >= wstart
        if wend:
            wmask &= day_dates <= wend
        wmask &= day_valid
        w_returns = daily_avg[wmask]
        if w_returns.size < 5:
            window_metrics[wname] = None
            continue
        w_idx_mask = wmask[:, None] & valid
        w_tickets = int(w_idx_mask.sum())
        w_realized = realized[wmask & day_valid.reshape(-1)]
        w_actual = actual_vals[wmask & day_valid.reshape(-1)]
        w_daily = w_returns[w_returns != 0] if wname != "full" else w_returns
        w_daily_valid = daily_avg[wmask]
        window_metrics[wname] = {
            "return_pct": pct_prod(w_daily_valid),
            "days": int(wmask.sum()),
            "daily_win": float((w_daily_valid > 0).mean()) if w_daily_valid.size else 0,
            "sharpe": sharpe(w_daily_valid),
            "max_dd": max_drawdown_pct(w_daily_valid),
        }

    months_str = np.array([d[:7] for d in day_dates])
    unique_months = sorted(set(months_str[day_valid]))
    month_returns = []
    monthly_detail = []
    for m in unique_months:
        mmask = day_valid & (months_str == m)
        m_daily = daily_avg[mmask]
        m_ret = pct_prod(m_daily)
        month_returns.append(m_ret)
        m_idx_mask = mmask[:, None] & valid
        m_tix = int(m_idx_mask.sum())
        m_realized_flat = realized[m_idx_mask]
        m_actual_flat = actual_vals[m_idx_mask]
        monthly_detail.append({
            "month": m,
            "days": int(mmask.sum()),
            "tickets": m_tix,
            "return_pct": round(m_ret, 2),
            "avg_daily": round(float(m_daily.mean()), 3),
            "daily_win": round(float((m_daily > 0).mean()), 3),
            "ticket_win": round(float((m_realized_flat > 0).mean()), 3) if m_tix else 0,
            "high1": round(float(m_actual_flat.mean()), 3) if m_tix else 0,
        })

    months_pos = sum(1 for r in month_returns if r > 0)
    months_tot = len(month_returns)

    oos_ret = window_metrics.get("oos")
    recent_ret = window_metrics.get("recent_q1q2")

    composite = (
        0.25 * total_return / max(abs(total_return), 1)
        + 0.30 * ((recent_ret["return_pct"] if recent_ret else 0) / 100.0)
        + 0.20 * ((oos_ret["return_pct"] if oos_ret else 0) / 100.0)
        + 0.10 * (sh or 0) / 5.0
        + 0.10 * (daily_win - 0.5) * 10
        + 0.05 * (months_pos / max(months_tot, 1) - 0.5) * 2
    )

    return {
        "signal_days": signal_days,
        "tickets": tickets,
        "total_return_pct": round(total_return, 2),
        "daily_win_rate": round(daily_win, 4),
        "ticket_win_rate": round(ticket_win, 4),
        "high1_hit_rate": round(high1, 4),
        "high1_w95": round(base.wilson_lower(tickets, high1), 4),
        "sharpe": round(sh, 2) if sh else None,
        "max_drawdown_pct": round(mdd, 2),
        "max_daily_loss_pct": round(float(daily_returns.min()), 2),
        "months_positive": months_pos,
        "months_total": months_tot,
        "oos_return_pct": round(oos_ret["return_pct"], 2) if oos_ret else None,
        "recent_return_pct": round(recent_ret["return_pct"], 2) if recent_ret else None,
        "pretrain_return_pct": round(window_metrics["pretrain"]["return_pct"], 2) if window_metrics.get("pretrain") else None,
        "composite_score": round(composite, 4),
        "windows": window_metrics,
        "months": monthly_detail,
    }


def main():
    t_start = time.time()
    print("=" * 70)
    print("  GLOBAL OPTIMAL STRATEGY SEARCH - PhaseC 2017-2026")
    print("=" * 70)

    print("\nLoading PhaseC bundle...", flush=True)
    bundle = base.load_bundle(PC_BUNDLE)
    print(f"  Model: {bundle['model_name']}, features: {len(bundle['feature_names'])}, selected: {len(bundle['selected_indices'])}")

    print(f"\nLoading full feature cache: {CACHE_FULL}", flush=True)
    df = base.load_scoring_frame(CACHE_FULL, bundle, "2017-01-01", "2026-05-31", "full_2017_2026")
    print(f"  Loaded: {len(df):,} rows, {df['date'].nunique()} trading days")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

    print("\nScoring with PhaseC bundle...", flush=True)
    t0 = time.time()
    raw, iso = base.predict_raw_and_iso(bundle, df)
    df["raw_prob"] = raw
    df["iso_prob"] = iso
    print(f"  Scored in {time.time()-t0:.1f}s")
    print(f"  raw_prob: mean={raw.mean():.4f}, median={np.median(raw):.4f}, p75={np.percentile(raw,75):.4f}, p90={np.percentile(raw,90):.4f}")
    print(f"  iso_prob: mean={iso.mean():.4f}, median={np.median(iso):.4f}, p75={np.percentile(iso,75):.4f}, p90={np.percentile(iso,90):.4f}")

    print("\nComputing exits...", flush=True)
    t0 = time.time()
    exits = compute_exits_fast(df)
    print(f"  Done in {time.time()-t0:.1f}s")

    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"], sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    day_dates = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m-%d").to_numpy()

    filters = build_extended_filters(df)
    max_top = max(TOP_NS)

    by_return = TopKeeper(500, "total_return_pct")
    by_composite = TopKeeper(500, "composite_score")
    by_oos = TopKeeper(500, "oos_return_pct")
    by_recent = TopKeeper(500, "recent_return_pct")

    total_combos = 0
    kept = 0
    t0 = time.time()

    print(f"\nSearch grid: {len(SCORE_COLS)} scores x {len(THRESHOLDS)} thresholds x {len(filters)} filters x {len(RANK_RECIPES)} recipes x {len(TOP_NS)} topN x {len(EXIT_MODES)} exits")
    est = len(SCORE_COLS) * len(filters) * len(RANK_RECIPES) * len(THRESHOLDS) * len(TOP_NS) * len(EXIT_MODES)
    print(f"  Estimated combos: {est:,}")

    for score_col in SCORE_COLS:
        for fi, (filter_name, filter_mask) in enumerate(filters):
            for recipe in RANK_RECIPES:
                cube = build_cube(df, score_col, recipe, filter_mask, THRESHOLDS, day_indices, max_top)
                for t_no, thr in enumerate(THRESHOLDS):
                    selected = cube[t_no]
                    for top_n in TOP_NS:
                        if int((selected[:, :top_n] >= 0).sum()) < 20:
                            total_combos += len(EXIT_MODES)
                            continue
                        for exit_name, _, _ in EXIT_MODES:
                            total_combos += 1
                            rec = eval_cube_multiwindow(
                                selected, exits, actual, day_dates, top_n, exit_name
                            )
                            if not rec:
                                continue
                            if rec["months_total"] < 3 or rec["signal_days"] < 20:
                                continue
                            rec.update({
                                "score_col": score_col,
                                "threshold": float(thr),
                                "top_n": int(top_n),
                                "filter_name": filter_name,
                                "rank_recipe": recipe,
                                "exit_mode": exit_name,
                            })
                            kept += 1
                            by_return.push(rec)
                            by_composite.push(rec)
                            by_oos.push(rec)
                            by_recent.push(rec)

                elapsed = time.time() - t0
                rate = total_combos / max(elapsed, 1)
                print(
                    f"  [{score_col}] {filter_name:20s} | {recipe:20s} | "
                    f"{total_combos:>10,} combos | {kept:>8,} kept | "
                    f"{elapsed:>6.0f}s | {rate:>8,.0f}/s",
                    flush=True,
                )

    elapsed_total = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  SEARCH COMPLETE: {total_combos:,} combos, {kept:,} kept, {elapsed_total:.0f}s")
    print(f"{'='*70}")

    def fmt(r):
        return (
            f"  {r['score_col']}>={r['threshold']} top{r['top_n']} | "
            f"{r['filter_name']} | {r['rank_recipe']} | {r['exit_mode']}\n"
            f"    Total: {r['total_return_pct']:.1f}%  OOS: {r.get('oos_return_pct','N/A')}%  "
            f"Recent: {r.get('recent_return_pct','N/A')}%  Sharpe: {r.get('sharpe','N/A')}  "
            f"Win: {r['daily_win_rate']:.1%}  H1: {r['high1_hit_rate']:.1%}  "
            f"MDD: {r['max_drawdown_pct']:.1f}%  Months+: {r['months_positive']}/{r['months_total']}"
        )

    top_return = by_return.sorted_desc()
    top_composite = by_composite.sorted_desc()
    top_oos = by_oos.sorted_desc()
    top_recent = by_recent.sorted_desc()

    print("\n>>> TOP 10 BY TOTAL RETURN <<<")
    for i, r in enumerate(top_return[:10], 1):
        print(f"\n#{i}:")
        print(fmt(r))

    print("\n>>> TOP 10 BY COMPOSITE SCORE (balanced) <<<")
    for i, r in enumerate(top_composite[:10], 1):
        print(f"\n#{i}:")
        print(fmt(r))

    print("\n>>> TOP 10 BY OOS RETURN (2025-07 to 2026-04) <<<")
    for i, r in enumerate(top_oos[:10], 1):
        print(f"\n#{i}:")
        print(fmt(r))

    print("\n>>> TOP 10 BY RECENT RETURN (2026 Q1-Q2) <<<")
    for i, r in enumerate(top_recent[:10], 1):
        print(f"\n#{i}:")
        print(fmt(r))

    def save_csv(results, name):
        rows = []
        for r in results[:200]:
            row = {k: v for k, v in r.items() if k not in ("windows", "months")}
            rows.append(row)
        path = OUT_DIR / f"{RUN_TAG}_{name}.csv"
        pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  Saved: {path}")
        return path

    save_csv(top_return, "top200_by_return")
    save_csv(top_composite, "top200_by_composite")
    save_csv(top_oos, "top200_by_oos")
    save_csv(top_recent, "top200_by_recent")

    best = top_composite[0] if top_composite else top_return[0]
    best_months = best.get("months", [])
    print(f"\n{'='*70}")
    print(f"  BEST COMPOSITE STRATEGY - MONTHLY BREAKDOWN")
    print(f"{'='*70}")
    print(f"  Strategy: {best['score_col']}>={best['threshold']} top{best['top_n']} | {best['filter_name']} | {best['rank_recipe']} | {best['exit_mode']}")
    print(f"  Total Return: {best['total_return_pct']:.1f}%  |  OOS: {best.get('oos_return_pct','N/A')}%  |  Recent: {best.get('recent_return_pct','N/A')}%")
    print(f"  Sharpe: {best.get('sharpe','N/A')}  |  Daily Win: {best['daily_win_rate']:.1%}  |  MDD: {best['max_drawdown_pct']:.1f}%")
    print(f"\n  {'Month':<10} {'Days':>5} {'Tix':>5} {'Return':>10} {'AvgDaily':>10} {'DayWin':>8} {'TixWin':>8} {'H1':>8}")
    print(f"  {'-'*10} {'-'*5} {'-'*5} {'-'*10} {'-'*10} {'-'*8} {'-'*8} {'-'*8}")
    for m in best_months:
        print(
            f"  {m['month']:<10} {m['days']:>5} {m['tickets']:>5} "
            f"{m['return_pct']:>9.2f}% {m['avg_daily']:>9.3f}% "
            f"{m['daily_win']:>7.1%} {m['ticket_win']:>7.1%} {m['high1']:>7.1%}"
        )

    yearly = {}
    for m in best_months:
        y = m["month"][:4]
        if y not in yearly:
            yearly[y] = []
        yearly[y].append(m["return_pct"])
    print(f"\n  YEARLY SUMMARY:")
    for y in sorted(yearly):
        rets = yearly[y]
        yr_ret = pct_prod(np.array(rets))
        pos = sum(1 for r in rets if r > 0)
        print(f"    {y}: {yr_ret:>10.1f}%  months: {pos}/{len(rets)} positive")

    payload = {
        "run_tag": RUN_TAG,
        "created_at": pd.Timestamp.now().isoformat(),
        "bundle": str(PC_BUNDLE),
        "cache": str(CACHE_FULL),
        "data_rows": len(df),
        "data_days": int(df["date"].nunique()),
        "date_range": f"{df['date'].min()} to {df['date'].max()}",
        "total_combos": total_combos,
        "kept": kept,
        "elapsed_s": round(time.time() - t_start, 1),
        "best_composite": {k: v for k, v in best.items() if k != "windows"},
        "top10_return": [{k: v for k, v in r.items() if k not in ("windows", "months")} for r in top_return[:10]],
        "top10_composite": [{k: v for k, v in r.items() if k not in ("windows", "months")} for r in top_composite[:10]],
        "top10_oos": [{k: v for k, v in r.items() if k not in ("windows", "months")} for r in top_oos[:10]],
        "top10_recent": [{k: v for k, v in r.items() if k not in ("windows", "months")} for r in top_recent[:10]],
    }
    json_path = OUT_DIR / f"{RUN_TAG}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n  JSON saved: {json_path}")
    print(f"\n  Total time: {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
