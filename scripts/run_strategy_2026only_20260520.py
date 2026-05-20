"""Strategy search using ONLY 2026 data (Jan-May).

Uses 10c11 cache which has 2026-01-02 to 2026-05-08.
Full grid: 2 scores x 25 filters x 11 recipes x 31 thresholds x 8 topN x 19 exits.
~80 trading days, so min_days threshold lowered to 10.
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
CACHE_10C = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_10c11fc874db003c.parquet"
)

OUT_DIR = Path(r"C:\Users\zzzzzzl\Desktop")
RUN_TAG = "strategy_2026only_20260520"

THRESHOLDS = [round(x / 100.0, 2) for x in range(50, 81)]
TOP_NS = [1, 2, 3, 4, 5, 6, 8, 10]
SCORE_COLS = ["raw_prob", "iso_prob"]

EXIT_MODES = base.EXIT_MODES
RANK_RECIPES = base.RANK_RECIPES


def build_filters(df: pd.DataFrame) -> list[tuple[str, np.ndarray]]:
    n = len(df)
    def s(col):
        return df[col].fillna(0).to_numpy(dtype=np.float64) if col in df.columns else np.zeros(n)
    t, c, rsi6, rng = s("turnover"), s("close"), s("rsi_6"), s("range_pct")
    az, vz, tz = s("amount_z_20"), s("volume_z_20"), s("turnover_z_20")
    specs = [
        ("none", np.ones(n, dtype=bool)),
        ("turnover>=3", t >= 3),
        ("turnover>=5", t >= 5),
        ("turnover>=8", t >= 8),
        ("turnover_3_20", (t >= 3) & (t <= 20)),
        ("turnover_5_20", (t >= 5) & (t <= 20)),
        ("turnover_5_30", (t >= 5) & (t <= 30)),
        ("close_3_60", (c >= 3) & (c <= 60)),
        ("close_5_60", (c >= 5) & (c <= 60)),
        ("close_5_100", (c >= 5) & (c <= 100)),
        ("close>=5", c >= 5),
        ("close_10_50", (c >= 10) & (c <= 50)),
        ("t5_20|c5_60", (t >= 5) & (t <= 20) & (c >= 5) & (c <= 60)),
        ("t>=5|az>=0", (t >= 5) & (az >= 0)),
        ("t>=5|vz>=0", (t >= 5) & (vz >= 0)),
        ("t>=5|rng>=2", (t >= 5) & (rng >= 2)),
        ("rsi6<=45", rsi6 <= 45),
        ("rsi6<=55", rsi6 <= 55),
        ("range>=2", rng >= 2),
        ("az>=0", az >= 0),
        ("vz>=0", vz >= 0),
        ("az>0|vz>0", (az > 0) & (vz > 0)),
        ("t>=5|rsi6<=55", (t >= 5) & (rsi6 <= 55)),
        ("tz>=0", tz >= 0),
        ("t5_30|c5_100", (t >= 5) & (t <= 30) & (c >= 5) & (c <= 100)),
    ]
    return specs


def compute_exits(df: pd.DataFrame) -> dict[str, np.ndarray]:
    close_ret = df["next_close_return_pct"].fillna(0).to_numpy(dtype=np.float64)
    high_ret = df["next_high_return_pct"].to_numpy(dtype=np.float64)
    low_ret = df["next_low_return_pct"].to_numpy(dtype=np.float64)
    high_ret = np.where(np.isnan(high_ret), close_ret, high_ret)
    low_ret = np.where(np.isnan(low_ret), close_ret, low_ret)
    exits = {}
    for name, sl, tp in EXIT_MODES:
        if sl is None and tp is None:
            exits[name] = close_ret.copy()
        elif sl is not None and tp is None:
            exits[name] = np.where(low_ret <= sl, sl, close_ret)
        elif tp is not None and sl is None:
            exits[name] = np.where(high_ret >= tp, tp, close_ret)
        else:
            sl_hit = low_ret <= sl
            tp_hit = high_ret >= tp
            r = close_ret.copy()
            r[tp_hit & ~sl_hit] = tp
            r[sl_hit] = sl
            exits[name] = r
    return exits


def pct_prod(arr):
    if arr.size == 0:
        return 0.0
    v = np.clip(arr / 100.0, -0.95, 10.0)
    return float((np.prod(1.0 + v) - 1.0) * 100.0)


def build_cube(df, score_col, recipe, fmask, thresholds, day_indices, max_top):
    score = df[score_col].fillna(0).to_numpy(dtype=np.float64)
    sort_key = base.compute_sort_key(df, score_col, recipe)
    n_thr = len(thresholds)
    n_days = len(day_indices)
    cube = np.full((n_thr, n_days, max_top), -1, dtype=np.int32)
    for d, didx in enumerate(day_indices):
        idx = didx[fmask[didx]]
        if idx.size == 0:
            continue
        idx = idx[np.argsort(-sort_key[idx], kind="mergesort")]
        ds = score[idx]
        for ti, thr in enumerate(thresholds):
            sel = idx[ds >= thr][:max_top]
            if sel.size:
                cube[ti, d, :sel.size] = sel
    return cube


def eval_fast(cube_thr, exits_arr, actual, top_n, min_days=10):
    idx = cube_thr[:, :top_n]
    valid = idx >= 0
    counts = valid.sum(axis=1)
    dv = counts > 0
    sig_days = int(dv.sum())
    tix = int(counts.sum())
    if sig_days < min_days or tix < min_days:
        return None

    si = np.where(valid, idx, 0)
    rv = exits_arr[si]
    rv = np.where(valid, rv, 0.0)
    ds = rv.sum(axis=1)
    da = np.zeros(len(counts), dtype=np.float64)
    da[dv] = ds[dv] / counts[dv]
    dr = da[dv]

    av = actual[si]
    av = np.where(valid, av, 0.0)
    h1 = float(av.sum() / tix)
    tw = float(((rv > 0) & valid).sum() / tix)
    dw = float((dr > 0).mean())
    tr = pct_prod(dr)

    std = float(dr.std(ddof=1)) if dr.size >= 3 else 0
    sh = float(dr.mean() / std * math.sqrt(252)) if std > 0 else None

    return {
        "signal_days": sig_days, "tickets": tix,
        "total_return_pct": round(tr, 2),
        "daily_win_rate": round(dw, 4),
        "ticket_win_rate": round(tw, 4),
        "high1_hit_rate": round(h1, 4),
        "high1_w95": round(base.wilson_lower(tix, h1), 4),
        "sharpe": round(sh, 2) if sh else None,
        "max_daily_loss_pct": round(float(dr.min()), 2),
        "avg_daily_return_pct": round(float(dr.mean()), 4),
    }


def enrich_strategy(df, day_dates, day_indices, actual, exits_full, fmask_dict, rec):
    fmask = fmask_dict[rec["filter_name"]]
    cube = build_cube(df, rec["score_col"], rec["rank_recipe"], fmask,
                      [rec["threshold"]], day_indices, max(10, rec["top_n"]))
    selected = cube[0]
    top_n = rec["top_n"]
    idx = selected[:, :top_n]
    valid = idx >= 0
    counts = valid.sum(axis=1)
    dv = counts > 0
    si = np.where(valid, idx, 0)

    exit_name = rec["exit_mode"]
    rv = exits_full[exit_name][si]
    rv = np.where(valid, rv, 0.0)
    ds = rv.sum(axis=1)
    da = np.zeros(len(counts), dtype=np.float64)
    da[dv] = ds[dv] / counts[dv]

    av = actual[si]
    av = np.where(valid, av, 0.0)

    months_str = np.array([d[:7] for d in day_dates])
    unique_months = sorted(set(months_str[dv]))
    monthly = []
    for m in unique_months:
        mm = dv & (months_str == m)
        md = da[mm]
        mret = pct_prod(md)
        mi = mm[:, None] & valid
        mt = int(mi.sum())
        mr = rv[mi]
        ma = av[mi]
        monthly.append({
            "month": m,
            "days": int(mm.sum()),
            "tickets": mt,
            "return_pct": round(mret, 2),
            "avg_daily": round(float(md.mean()), 3),
            "daily_win": round(float((md > 0).mean()), 3),
            "ticket_win": round(float((mr > 0).mean()), 3) if mt else 0,
            "high1": round(float(ma.mean()), 3) if mt else 0,
        })

    rec["months"] = monthly

    cum = np.cumprod(1.0 + np.clip(da[dv] / 100, -0.95, 10.0))
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak * 100
    rec["max_drawdown_pct"] = round(float(dd.min()), 2)

    months_pos = sum(1 for m in monthly if m["return_pct"] > 0)
    rec["months_positive"] = months_pos
    rec["months_total"] = len(monthly)

    yearly = {}
    for m in monthly:
        y = m["month"][:4]
        yearly.setdefault(y, []).append(m["return_pct"])
    rec["yearly"] = {y: round(pct_prod(np.array(rs)), 2) for y, rs in sorted(yearly.items())}

    return rec


class TopK:
    def __init__(self, k, key):
        self.k = k
        self.key = key
        self.heap = []
        self.c = 0
    def push(self, r):
        v = r.get(self.key)
        if v is None:
            return
        item = (float(v), self.c, r.copy())
        self.c += 1
        if len(self.heap) < self.k:
            heapq.heappush(self.heap, item)
        elif item[0] > self.heap[0][0]:
            heapq.heapreplace(self.heap, item)
    def top(self):
        return [i[2] for i in sorted(self.heap, key=lambda x: x[0], reverse=True)]


def main():
    t_start = time.time()
    print("=" * 70)
    print("  STRATEGY SEARCH - 2026 ONLY (Jan~May) - PhaseC")
    print("=" * 70)

    bundle = base.load_bundle(PC_BUNDLE)
    print(f"Bundle: {bundle['model_name']}, {len(bundle['feature_names'])} feats, "
          f"{len(bundle['selected_indices'])} selected")

    df = base.load_scoring_frame(CACHE_10C, bundle, "2026-01-01", "2026-05-31", "2026only")
    print(f"Data: {len(df):,} rows, {df['date'].nunique()} days, "
          f"{df['date'].min()} to {df['date'].max()}")

    raw, iso = base.predict_raw_and_iso(bundle, df)
    df["raw_prob"] = raw
    df["iso_prob"] = iso
    print(f"Scored: raw mean={raw.mean():.4f} p90={np.percentile(raw,90):.4f} | "
          f"iso mean={iso.mean():.4f} p90={np.percentile(iso,90):.4f}")

    exits = compute_exits(df)
    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"], sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    day_dates = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m-%d").to_numpy()

    filters = build_filters(df)
    fmask_dict = {name: mask for name, mask in filters}
    max_top = max(TOP_NS)

    by_ret = TopK(500, "total_return_pct")
    by_sharpe = TopK(500, "sharpe")
    by_winrate = TopK(500, "daily_win_rate")

    total = 0
    kept = 0
    t0 = time.time()
    n_exits = len(EXIT_MODES)

    grid_size = (len(SCORE_COLS) * len(filters) * len(RANK_RECIPES)
                 * len(THRESHOLDS) * len(TOP_NS) * n_exits)
    print(f"\nGrid: {len(SCORE_COLS)}x{len(filters)}x{len(RANK_RECIPES)}"
          f"x{len(THRESHOLDS)}x{len(TOP_NS)}x{n_exits} = {grid_size:,} combos")

    for sc in SCORE_COLS:
        for fname, fmask in filters:
            for recipe in RANK_RECIPES:
                cube = build_cube(df, sc, recipe, fmask, THRESHOLDS, day_indices, max_top)
                for ti, thr in enumerate(THRESHOLDS):
                    sel = cube[ti]
                    for tn in TOP_NS:
                        if int((sel[:, :tn] >= 0).sum()) < 10:
                            total += n_exits
                            continue
                        for ename, _, _ in EXIT_MODES:
                            total += 1
                            rec = eval_fast(sel, exits[ename], actual, tn, min_days=10)
                            if not rec or rec["signal_days"] < 10:
                                continue
                            rec.update({
                                "score_col": sc,
                                "threshold": float(thr),
                                "top_n": int(tn),
                                "filter_name": fname,
                                "rank_recipe": recipe,
                                "exit_mode": ename,
                            })
                            kept += 1
                            by_ret.push(rec)
                            by_sharpe.push(rec)
                            by_winrate.push(rec)

                el = time.time() - t0
                print(f"  {sc} | {fname:20s} | {recipe:20s} | "
                      f"{total:>10,} | {kept:>8,} | {el:>5.0f}s | "
                      f"{total/max(el,1):>6,.0f}/s", flush=True)

    print(f"\nPass 1 done: {total:,} combos, {kept:,} kept, {time.time()-t0:.0f}s")

    # Pass 2: enrich top strategies
    print("\nPass 2: enriching top strategies...")
    seen = set()
    all_top = []
    for lst in [by_ret.top(), by_sharpe.top(), by_winrate.top()]:
        for r in lst[:150]:
            key = (r["score_col"], r["threshold"], r["top_n"],
                   r["filter_name"], r["rank_recipe"], r["exit_mode"])
            if key not in seen:
                seen.add(key)
                all_top.append(r)

    print(f"  Enriching {len(all_top)} unique strategies...")
    for i, r in enumerate(all_top):
        enrich_strategy(df, day_dates, day_indices, actual, exits, fmask_dict, r)
        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(all_top)}", flush=True)

    by_total = sorted(all_top, key=lambda x: x["total_return_pct"], reverse=True)
    by_sh = sorted([r for r in all_top if r.get("sharpe")],
                   key=lambda x: x["sharpe"], reverse=True)
    by_dw = sorted(all_top, key=lambda x: x["daily_win_rate"], reverse=True)

    # Robust: all months positive
    robust = [r for r in all_top
              if r.get("months_positive", 0) == r.get("months_total", 1)
              and r.get("months_total", 0) >= 3]
    by_robust = sorted(robust, key=lambda x: x["total_return_pct"], reverse=True)

    # Semi-robust: >= 80% months positive
    semi = [r for r in all_top
            if r.get("months_total", 0) >= 3
            and r.get("months_positive", 0) >= r.get("months_total", 1) * 0.8]
    by_semi = sorted(semi, key=lambda x: x["total_return_pct"], reverse=True)

    def fmt(r, rank):
        mdd = r.get("max_drawdown_pct", "N/A")
        mp = r.get("months_positive", "?")
        mt = r.get("months_total", "?")
        sh = r.get("sharpe", "N/A")
        return (
            f"  #{rank}: {r['score_col']}>={r['threshold']} top{r['top_n']} | "
            f"{r['filter_name']} | {r['rank_recipe']} | {r['exit_mode']}\n"
            f"       Total:{r['total_return_pct']:.1f}%  "
            f"Sharpe:{sh}  Win:{r['daily_win_rate']:.1%}  TWin:{r['ticket_win_rate']:.1%}  "
            f"H1:{r['high1_hit_rate']:.1%}  "
            f"MDD:{mdd}%  Days:{r['signal_days']}  Tix:{r['tickets']}  Mo:{mp}/{mt}"
        )

    for label, lst in [
        ("TOP 15 BY TOTAL RETURN (2026)", by_total),
        ("TOP 10 BY SHARPE (2026)", by_sh),
        ("TOP 10 BY DAILY WIN RATE (2026)", by_dw),
        ("TOP 10 ALL-MONTHS-POSITIVE (ROBUST)", by_robust),
        ("TOP 10 >=80%-MONTHS-POSITIVE (SEMI-ROBUST)", by_semi),
    ]:
        n_show = 15 if "TOTAL" in label else 10
        print(f"\n{'='*70}")
        print(f"  {label}")
        print(f"{'='*70}")
        for i, r in enumerate(lst[:n_show], 1):
            print(fmt(r, i))

    best = by_robust[0] if by_robust else by_total[0] if by_total else None
    if not best:
        print("No strategies found!")
        return

    print(f"\n{'='*70}")
    print(f"  RECOMMENDED STRATEGY - MONTHLY BREAKDOWN")
    print(f"{'='*70}")
    print(f"  {best['score_col']}>={best['threshold']} top{best['top_n']} | "
          f"{best['filter_name']} | {best['rank_recipe']} | {best['exit_mode']}")
    print(f"  Total: {best['total_return_pct']:.1f}%  Sharpe: {best.get('sharpe','N/A')}  "
          f"Win: {best['daily_win_rate']:.1%}  MDD: {best.get('max_drawdown_pct','N/A')}%")
    print(f"\n  {'Month':<10} {'Days':>5} {'Tix':>5} {'Return':>10} {'AvgD':>8} "
          f"{'DWin':>7} {'TWin':>7} {'H1':>7}")
    print(f"  {'-'*65}")
    for m in best.get("months", []):
        print(f"  {m['month']:<10} {m['days']:>5} {m['tickets']:>5} "
              f"{m['return_pct']:>9.2f}% {m['avg_daily']:>7.3f}% "
              f"{m['daily_win']:>6.1%} {m['ticket_win']:>6.1%} {m['high1']:>6.1%}")

    # Also show top 3 by total return monthly breakdown
    print(f"\n{'='*70}")
    print(f"  TOP 3 TOTAL RETURN - MONTHLY DETAILS")
    print(f"{'='*70}")
    for rank, strat in enumerate(by_total[:3], 1):
        print(f"\n  --- #{rank}: {strat['score_col']}>={strat['threshold']} top{strat['top_n']} | "
              f"{strat['filter_name']} | {strat['rank_recipe']} | {strat['exit_mode']} ---")
        print(f"  Total:{strat['total_return_pct']:.1f}% Sharpe:{strat.get('sharpe','N/A')} "
              f"Win:{strat['daily_win_rate']:.1%} MDD:{strat.get('max_drawdown_pct','N/A')}%")
        for m in strat.get("months", []):
            print(f"    {m['month']}: {m['return_pct']:>8.2f}% ({m['days']}d, {m['tickets']}t, "
                  f"dw={m['daily_win']:.1%}, tw={m['ticket_win']:.1%}, h1={m['high1']:.1%})")

    # Save outputs
    def save_list(lst, name):
        rows = []
        for r in lst[:300]:
            row = {k: v for k, v in r.items() if k not in ("months", "yearly")}
            rows.append(row)
        p = OUT_DIR / f"{RUN_TAG}_{name}.csv"
        pd.DataFrame(rows).to_csv(p, index=False, encoding="utf-8-sig")
        print(f"  Saved: {p}")

    save_list(by_total, "by_total_return")
    save_list(by_sh, "by_sharpe")
    save_list(by_robust, "robust_all_months_positive")
    save_list(by_semi, "semi_robust_80pct")

    payload = {
        "run_tag": RUN_TAG,
        "created_at": pd.Timestamp.now().isoformat(),
        "data_range": "2026-01 to 2026-05",
        "rows": len(df),
        "trading_days": int(df["date"].nunique()),
        "combos_searched": total,
        "combos_kept": kept,
        "elapsed_s": round(time.time() - t_start, 1),
        "recommended": {k: v for k, v in best.items()},
        "top5_total": [{k: v for k, v in r.items()} for r in by_total[:5]],
        "top5_sharpe": [{k: v for k, v in r.items() if k != "months"} for r in by_sh[:5]],
        "top5_robust": [{k: v for k, v in r.items()} for r in by_robust[:5]],
    }
    jp = OUT_DIR / f"{RUN_TAG}.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                  encoding="utf-8")
    print(f"  JSON: {jp}")
    print(f"\nTotal time: {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
