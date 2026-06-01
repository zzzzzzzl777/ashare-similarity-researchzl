"""Global optimal strategy search v2 - FAST version.

Key optimizations vs v1:
1. Narrower threshold range: 0.55-0.80 (26 vs 36)
2. topN: 1,2,3,5 (4 vs 7)
3. Focused exit modes: 8 most useful (vs 19)
4. 15 filters (trimmed redundant ones)
5. Simplified eval without per-window overhead for initial sweep
6. Two-pass: fast coarse sweep -> enriched top strategies

Uses 550a cache: 811K rows, 2237 days, 2017-02 to 2026-04.
PhaseC bundle: CatBoost, 200 selected features.
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
RUN_TAG = "global_optimal_strategy_v2_20260519"

THRESHOLDS = [round(x / 100.0, 2) for x in range(55, 81)]
TOP_NS = [1, 2, 3, 5]
SCORE_COLS = ["raw_prob", "iso_prob"]

FAST_EXIT_MODES = [
    ("close", None, None),
    ("sl2", -2.0, None),
    ("sl3", -3.0, None),
    ("tp5", None, 5.0),
    ("tp7", None, 7.0),
    ("tp10", None, 10.0),
    ("sl2_tp5", -2.0, 5.0),
    ("sl3_tp7", -3.0, 7.0),
]

RANK_RECIPES = [
    "prob_desc", "amount_z_high", "volume_z_high",
    "score_then_rsi6_low", "prob_x_amount_z", "prob_x_volume_z",
    "activity_z_high", "turnover_z_high",
]


def build_filters(df: pd.DataFrame) -> list[tuple[str, np.ndarray]]:
    n = len(df)
    def s(col):
        return df[col].fillna(0).to_numpy(dtype=np.float64) if col in df.columns else np.zeros(n)
    t, c, rsi6, rng, az, vz = s("turnover"), s("close"), s("rsi_6"), s("range_pct"), s("amount_z_20"), s("volume_z_20")
    specs = [
        ("none", np.ones(n, dtype=bool)),
        ("turnover>=5", t >= 5),
        ("turnover_5_20", (t >= 5) & (t <= 20)),
        ("turnover_5_30", (t >= 5) & (t <= 30)),
        ("close_5_60", (c >= 5) & (c <= 60)),
        ("close_5_100", (c >= 5) & (c <= 100)),
        ("close_10_50", (c >= 10) & (c <= 50)),
        ("t5_20|c5_60", (t >= 5) & (t <= 20) & (c >= 5) & (c <= 60)),
        ("t>=5|az>=0", (t >= 5) & (az >= 0)),
        ("t>=5|vz>=0", (t >= 5) & (vz >= 0)),
        ("t>=5|rng>=2", (t >= 5) & (rng >= 2)),
        ("rsi6<=55", rsi6 <= 55),
        ("az>=0", az >= 0),
        ("vz>=0", vz >= 0),
        ("az>0|vz>0", (az > 0) & (vz > 0)),
    ]
    return specs


def compute_exits(df: pd.DataFrame) -> dict[str, np.ndarray]:
    close_ret = df["next_close_return_pct"].fillna(0).to_numpy(dtype=np.float64)
    high_ret = df["next_high_return_pct"].to_numpy(dtype=np.float64)
    low_ret = df["next_low_return_pct"].to_numpy(dtype=np.float64)
    high_ret = np.where(np.isnan(high_ret), close_ret, high_ret)
    low_ret = np.where(np.isnan(low_ret), close_ret, low_ret)
    exits = {}
    for name, sl, tp in FAST_EXIT_MODES:
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


def eval_fast(cube_thr, exits_arr, actual, top_n):
    idx = cube_thr[:, :top_n]
    valid = idx >= 0
    counts = valid.sum(axis=1)
    dv = counts > 0
    sig_days = int(dv.sum())
    tix = int(counts.sum())
    if sig_days < 20 or tix < 20:
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
    }


def enrich_strategy(df, day_dates, day_indices, actual, exits_full, fmask_dict, rec):
    fmask = fmask_dict[rec["filter_name"]]
    cube = build_cube(df, rec["score_col"], rec["rank_recipe"], fmask,
                      [rec["threshold"]], day_indices, max(5, rec["top_n"]))
    selected = cube[0]
    top_n = rec["top_n"]
    idx = selected[:, :top_n]
    valid = idx >= 0
    counts = valid.sum(axis=1)
    dv = counts > 0
    si = np.where(valid, idx, 0)

    exit_name = rec["exit_mode"]
    for ename, sl, tp in FAST_EXIT_MODES:
        if ename == exit_name:
            break
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

    windows = {
        "oos_2025h2_2026": ("2025-07-01", "2026-12-31"),
        "recent_2026": ("2026-01-01", "2026-12-31"),
        "pretrain": ("2017-01-01", "2023-04-30"),
        "train_era": ("2023-05-01", "2025-06-30"),
    }
    wret = {}
    for wn, (ws, we) in windows.items():
        wm = dv & (day_dates >= ws) & (day_dates <= we)
        wd = da[wm]
        if wd.size < 3:
            wret[wn] = None
        else:
            wret[wn] = round(pct_prod(wd), 2)

    rec["months"] = monthly
    rec["oos_return_pct"] = wret.get("oos_2025h2_2026")
    rec["recent_return_pct"] = wret.get("recent_2026")
    rec["pretrain_return_pct"] = wret.get("pretrain")
    rec["train_era_return_pct"] = wret.get("train_era")

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
        if v is None: return
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
    print("  GLOBAL OPTIMAL STRATEGY SEARCH v2 (FAST) - PhaseC 2017-2026")
    print("=" * 70)

    bundle = base.load_bundle(PC_BUNDLE)
    print(f"Bundle: {bundle['model_name']}, {len(bundle['feature_names'])} feats, {len(bundle['selected_indices'])} selected")

    df = base.load_scoring_frame(CACHE_FULL, bundle, "2017-01-01", "2026-05-31", "full")
    print(f"Data: {len(df):,} rows, {df['date'].nunique()} days, {df['date'].min()} to {df['date'].max()}")

    raw, iso = base.predict_raw_and_iso(bundle, df)
    df["raw_prob"] = raw
    df["iso_prob"] = iso
    print(f"Scored: raw mean={raw.mean():.4f} p90={np.percentile(raw,90):.4f} | iso mean={iso.mean():.4f} p90={np.percentile(iso,90):.4f}")

    exits = compute_exits(df)
    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"], sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    day_dates = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m-%d").to_numpy()

    filters = build_filters(df)
    fmask_dict = {name: mask for name, mask in filters}
    max_top = max(TOP_NS)

    by_ret = TopK(300, "total_return_pct")
    by_sharpe = TopK(300, "sharpe")
    by_winrate = TopK(300, "daily_win_rate")

    total = 0
    kept = 0
    t0 = time.time()
    n_exits = len(FAST_EXIT_MODES)

    grid_size = len(SCORE_COLS) * len(filters) * len(RANK_RECIPES) * len(THRESHOLDS) * len(TOP_NS) * n_exits
    print(f"\nGrid: {len(SCORE_COLS)}x{len(filters)}x{len(RANK_RECIPES)}x{len(THRESHOLDS)}x{len(TOP_NS)}x{n_exits} = {grid_size:,} combos")

    for sc in SCORE_COLS:
        for fname, fmask in filters:
            for recipe in RANK_RECIPES:
                cube = build_cube(df, sc, recipe, fmask, THRESHOLDS, day_indices, max_top)
                for ti, thr in enumerate(THRESHOLDS):
                    sel = cube[ti]
                    for tn in TOP_NS:
                        if int((sel[:, :tn] >= 0).sum()) < 20:
                            total += n_exits
                            continue
                        for ename, _, _ in FAST_EXIT_MODES:
                            total += 1
                            rec = eval_fast(sel, exits[ename], actual, tn)
                            if not rec or rec["signal_days"] < 20:
                                continue
                            rec.update({"score_col": sc, "threshold": float(thr),
                                        "top_n": int(tn), "filter_name": fname,
                                        "rank_recipe": recipe, "exit_mode": ename})
                            kept += 1
                            by_ret.push(rec)
                            by_sharpe.push(rec)
                            by_winrate.push(rec)

                el = time.time() - t0
                print(f"  {sc} | {fname:20s} | {recipe:20s} | {total:>10,} | {kept:>8,} | {el:>5.0f}s | {total/max(el,1):>6,.0f}/s", flush=True)

    print(f"\nPass 1 done: {total:,} combos, {kept:,} kept, {time.time()-t0:.0f}s")

    print("\nPass 2: enriching top strategies with monthly/yearly/window details...")
    exits_full = exits

    seen = set()
    all_top = []
    for lst in [by_ret.top(), by_sharpe.top(), by_winrate.top()]:
        for r in lst[:100]:
            key = (r["score_col"], r["threshold"], r["top_n"], r["filter_name"], r["rank_recipe"], r["exit_mode"])
            if key not in seen:
                seen.add(key)
                all_top.append(r)

    print(f"  Enriching {len(all_top)} unique strategies...")
    for i, r in enumerate(all_top):
        enrich_strategy(df, day_dates, day_indices, actual, exits_full, fmask_dict, r)
        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(all_top)}", flush=True)

    by_oos = sorted([r for r in all_top if r.get("oos_return_pct") is not None],
                    key=lambda x: x["oos_return_pct"], reverse=True)
    by_recent = sorted([r for r in all_top if r.get("recent_return_pct") is not None],
                       key=lambda x: x["recent_return_pct"], reverse=True)
    by_total = sorted(all_top, key=lambda x: x["total_return_pct"], reverse=True)

    robust = [r for r in all_top
              if r.get("oos_return_pct") is not None and r["oos_return_pct"] > 0
              and r.get("pretrain_return_pct") is not None and r["pretrain_return_pct"] > 0
              and r.get("months_positive", 0) > r.get("months_total", 1) * 0.55]
    by_robust_total = sorted(robust, key=lambda x: x["total_return_pct"], reverse=True)
    by_robust_oos = sorted(robust, key=lambda x: x["oos_return_pct"], reverse=True)

    def fmt(r, rank):
        oos = r.get("oos_return_pct", "N/A")
        rec_ = r.get("recent_return_pct", "N/A")
        pre = r.get("pretrain_return_pct", "N/A")
        mdd = r.get("max_drawdown_pct", "N/A")
        mp = r.get("months_positive", "?")
        mt = r.get("months_total", "?")
        return (
            f"  #{rank}: {r['score_col']}>={r['threshold']} top{r['top_n']} | "
            f"{r['filter_name']} | {r['rank_recipe']} | {r['exit_mode']}\n"
            f"       Total:{r['total_return_pct']:.1f}%  OOS:{oos}%  Recent:{rec_}%  Pre:{pre}%  "
            f"Sharpe:{r.get('sharpe','N/A')}  Win:{r['daily_win_rate']:.1%}  H1:{r['high1_hit_rate']:.1%}  "
            f"MDD:{mdd}%  Mo:{mp}/{mt}"
        )

    for label, lst in [
        ("TOP 10 BY TOTAL RETURN", by_total),
        ("TOP 10 BY OOS RETURN (2025H2-2026)", by_oos),
        ("TOP 10 BY RECENT RETURN (2026)", by_recent),
        ("TOP 10 ROBUST (pretrain+OOS positive, >55% months+) BY TOTAL", by_robust_total),
        ("TOP 10 ROBUST BY OOS", by_robust_oos),
    ]:
        print(f"\n{'='*70}")
        print(f"  {label}")
        print(f"{'='*70}")
        for i, r in enumerate(lst[:10], 1):
            print(fmt(r, i))

    if by_robust_total:
        best = by_robust_total[0]
    elif by_total:
        best = by_total[0]
    else:
        print("No strategies found!")
        return

    print(f"\n{'='*70}")
    print(f"  RECOMMENDED STRATEGY - MONTHLY BREAKDOWN")
    print(f"{'='*70}")
    print(f"  {best['score_col']}>={best['threshold']} top{best['top_n']} | {best['filter_name']} | {best['rank_recipe']} | {best['exit_mode']}")
    print(f"  Total: {best['total_return_pct']:.1f}%  OOS: {best.get('oos_return_pct','N/A')}%  Recent: {best.get('recent_return_pct','N/A')}%")
    print(f"  Sharpe: {best.get('sharpe','N/A')}  Win: {best['daily_win_rate']:.1%}  MDD: {best.get('max_drawdown_pct','N/A')}%")
    print(f"\n  {'Month':<10} {'Days':>5} {'Tix':>5} {'Return':>10} {'AvgD':>8} {'DWin':>7} {'TWin':>7} {'H1':>7}")
    print(f"  {'-'*65}")
    for m in best.get("months", []):
        print(f"  {m['month']:<10} {m['days']:>5} {m['tickets']:>5} {m['return_pct']:>9.2f}% {m['avg_daily']:>7.3f}% {m['daily_win']:>6.1%} {m['ticket_win']:>6.1%} {m['high1']:>6.1%}")

    print(f"\n  YEARLY:")
    for y, ret in sorted(best.get("yearly", {}).items()):
        print(f"    {y}: {ret:>10.1f}%")

    def save_list(lst, name):
        rows = []
        for r in lst[:200]:
            row = {k: v for k, v in r.items() if k not in ("months", "yearly", "windows")}
            rows.append(row)
        p = OUT_DIR / f"{RUN_TAG}_{name}.csv"
        pd.DataFrame(rows).to_csv(p, index=False, encoding="utf-8-sig")
        print(f"  Saved: {p}")

    save_list(by_total, "by_total_return")
    save_list(by_oos, "by_oos_return")
    save_list(by_recent, "by_recent_return")
    save_list(by_robust_total, "robust_by_total")
    save_list(by_robust_oos, "robust_by_oos")

    payload = {
        "run_tag": RUN_TAG,
        "created_at": pd.Timestamp.now().isoformat(),
        "data": f"{len(df):,} rows, {df['date'].nunique()} days",
        "combos": total, "kept": kept,
        "elapsed_s": round(time.time() - t_start, 1),
        "recommended": {k: v for k, v in best.items()},
        "top5_total": [{k: v for k, v in r.items() if k not in ("windows",)} for r in by_total[:5]],
        "top5_oos": [{k: v for k, v in r.items() if k not in ("windows",)} for r in by_oos[:5]],
        "top5_robust": [{k: v for k, v in r.items() if k not in ("windows",)} for r in by_robust_total[:5]],
    }
    jp = OUT_DIR / f"{RUN_TAG}.json"
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"  JSON: {jp}")
    print(f"\nTotal time: {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
