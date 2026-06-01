"""Aggressive strategy search: higher topN, lower thresholds, maximize returns."""
import numpy as np, pandas as pd, torch, pickle, math
from pathlib import Path
import pyarrow.parquet as pq

PC_BUNDLE = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt")
CACHE_JAN = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\jan_2023_patched.parquet")
CACHE_PRETRAIN = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\pretrain_2023_02_04_patched.parquet")
CACHE_MAIN = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_31ffa0367a4d893f.parquet")

META = {"symbol", "date", "actual", "close", "next_close_return_pct",
        "next_high_return_pct", "next_low_return_pct", "limit_up_like", "short_phase_days_3"}
STRAT = {"turnover", "turnover_z_20", "amount_z_20", "volume_z_20", "range_pct", "rsi_6"}


def pct_prod(arr):
    if arr.size == 0:
        return 0.0
    return float((np.prod(1.0 + np.clip(arr / 100, -0.95, 10.0)) - 1.0) * 100.0)


def main():
    payload = torch.load(str(PC_BUNDLE), map_location="cpu", weights_only=False)
    members = [pickle.loads(m["model_bytes"]) for m in payload["members"]]
    feature_names = list(payload["feature_names"])
    mean, std_val = payload["mean"], payload["std"].clone()
    std_val[std_val == 0] = 1.0
    selected_indices = payload["selected_indices"]

    needed = META | STRAT | set(feature_names)

    # Load all data
    frames = []
    for cache_path, start, end in [
        (CACHE_JAN, "2023-01-01", "2023-01-31"),
        (CACHE_PRETRAIN, "2023-02-01", "2023-04-30"),
        (CACHE_MAIN, "2023-06-01", "2026-05-31"),
    ]:
        schema = set(pq.read_schema(str(cache_path)).names)
        cols = [c for c in sorted(needed) if c in schema]
        tmp = pd.read_parquet(str(cache_path), columns=cols)
        tmp = tmp[(tmp["date"] >= start) & (tmp["date"] <= end)].copy()
        frames.append(tmp)

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["date", "symbol"], keep="first").reset_index(drop=True)
    df = df[df["limit_up_like"] != 1].copy()
    df = df[df["short_phase_days_3"] >= 1].copy()
    df = df.reset_index(drop=True)
    n = len(df)
    print(f"Data: {n:,} rows, {df['date'].nunique()} days, {df['date'].min()} ~ {df['date'].max()}")

    # Score
    raw_features = np.zeros((n, len(feature_names)), dtype=np.float32)
    for i, name in enumerate(feature_names):
        if name in df.columns:
            raw_features[:, i] = df[name].fillna(0).to_numpy(dtype=np.float32)
    x = torch.as_tensor(raw_features, dtype=torch.float32)
    x = (x - mean) / std_val
    x = x[:, selected_indices]
    probs = np.stack([m.predict_proba(x.numpy())[:, 1] for m in members]).mean(axis=0).astype(np.float32)
    df["raw_prob"] = probs
    print(f"Scored. prob range: {probs.min():.3f} ~ {probs.max():.3f}")

    # Exits
    close_ret = df["next_close_return_pct"].fillna(0).to_numpy(dtype=np.float64)
    high_ret = df["next_high_return_pct"].to_numpy(dtype=np.float64)
    low_ret = df["next_low_return_pct"].to_numpy(dtype=np.float64)
    high_ret = np.where(np.isnan(high_ret), close_ret, high_ret)
    low_ret = np.where(np.isnan(low_ret), close_ret, low_ret)

    exits = {
        "close": close_ret.copy(),
        "tp10": np.where(high_ret >= 10.0, 10.0, close_ret),
        "tp7": np.where(high_ret >= 7.0, 7.0, close_ret),
        "tp5": np.where(high_ret >= 5.0, 5.0, close_ret),
        "sl3_tp10": np.where((high_ret >= 10) & ~(low_ret <= -3), 10.0,
                             np.where(low_ret <= -3, -3.0, close_ret)),
        "sl5_tp10": np.where((high_ret >= 10) & ~(low_ret <= -5), 10.0,
                             np.where(low_ret <= -5, -5.0, close_ret)),
    }

    # Filters
    def s(col):
        return df[col].fillna(0).to_numpy(dtype=np.float64) if col in df.columns else np.zeros(n)

    t_arr, c_arr, vz, az_arr, rsi6 = s("turnover"), s("close"), s("volume_z_20"), s("amount_z_20"), s("rsi_6")
    filters = [
        ("none", np.ones(n, dtype=bool)),
        ("vz>=0", vz >= 0),
        ("t>=5|vz>=0", (t_arr >= 5) & (vz >= 0)),
        ("t5_20|c5_60", (t_arr >= 5) & (t_arr <= 20) & (c_arr >= 5) & (c_arr <= 60)),
        ("t>=5", t_arr >= 5),
        ("t>=3|vz>=0", (t_arr >= 3) & (vz >= 0)),
    ]
    filter_dict = dict(filters)

    # Rank recipes
    def compute_sort_key(recipe):
        p = probs.astype(np.float64)
        if recipe == "score_then_rsi6_low":
            return p * 1000 - rsi6
        if recipe == "volume_z_high":
            return vz * 1000 + p
        if recipe == "activity_z_high":
            return s("range_pct") * s("turnover_z_20") * 1000 + p
        if recipe == "amount_z_high":
            return az_arr * 1000 + p
        return p  # prob_desc

    recipes = ["score_then_rsi6_low", "volume_z_high", "activity_z_high", "amount_z_high", "prob_desc"]

    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"].to_numpy(), sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    n_days = len(day_values)
    day_months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()
    day_dates = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m-%d").to_numpy()

    # Period masks
    pre_mask = day_dates < "2023-05-01"
    oos_mask = day_dates >= "2025-07-01"
    apr_mask = (day_months == "2026-04")

    # Extended search grid
    thresholds = [round(x / 100.0, 2) for x in range(60, 80)]
    top_ns = [1, 2, 3, 4, 5, 6, 8, 10]
    exit_modes = ["tp10", "close", "sl5_tp10", "tp7", "sl3_tp10"]

    print(f"Grid: {len(thresholds)} thr x {len(top_ns)} topN x {len(filters)} filters x "
          f"{len(recipes)} recipes x {len(exit_modes)} exits")

    results = []
    for recipe in recipes:
        sk = compute_sort_key(recipe)
        for fname, fmask in filters:
            for thr in thresholds:
                pool = (probs >= thr) & fmask
                if not pool.any():
                    continue
                max_t = max(top_ns)
                dsel = np.full((n_days, max_t), -1, dtype=np.int32)
                for di, didx in enumerate(day_indices):
                    idx = didx[pool[didx]]
                    if idx.size == 0:
                        continue
                    idx = idx[np.argsort(-sk[idx])[:max_t]]
                    dsel[di, :idx.size] = idx

                for tn in top_ns:
                    sel = dsel[:, :tn]
                    valid = sel >= 0
                    counts = valid.sum(axis=1)
                    dv = counts > 0
                    sig = int(dv.sum())
                    tix = int(counts.sum())
                    if sig < 30:
                        continue
                    safe = np.where(valid, sel, 0)

                    for ename in exit_modes:
                        realized = exits[ename][safe]
                        realized = np.where(valid, realized, 0.0)
                        dsum = realized.sum(axis=1)
                        davg = np.zeros(n_days)
                        davg[dv] = dsum[dv] / counts[dv]
                        dr = davg[dv]

                        total = pct_prod(dr)
                        pre_ret = pct_prod(davg[pre_mask & dv]) if (pre_mask & dv).any() else 0
                        oos_ret = pct_prod(davg[oos_mask & dv]) if (oos_mask & dv).any() else 0
                        apr_ret = pct_prod(davg[apr_mask & dv]) if (apr_mask & dv).any() else 0
                        dwin = float((dr > 0).mean())

                        # H1 hit rate
                        act_v = actual[safe]
                        act_v = np.where(valid, act_v, 0.0)
                        h1 = float(act_v.sum() / tix)

                        robust = pre_ret > -5 and oos_ret > 0

                        results.append({
                            "thr": thr, "tn": tn, "f": fname, "r": recipe, "e": ename,
                            "total": total, "pre": pre_ret, "oos": oos_ret, "apr": apr_ret,
                            "days": sig, "tix": tix, "dwin": dwin, "h1": h1, "robust": robust,
                        })
        print(f"  {recipe} done, {len(results):,} so far", flush=True)

    print(f"\nTotal strategies: {len(results):,}")
    robust = [r for r in results if r["robust"]]
    print(f"Robust (pre>-5% AND oos>0): {len(robust):,}")

    # Sort by different criteria
    by_total = sorted(robust, key=lambda r: r["total"], reverse=True)
    by_oos = sorted(robust, key=lambda r: r["oos"], reverse=True)
    by_apr = sorted(robust, key=lambda r: r["apr"], reverse=True)

    hdr = f"{'#':<3} {'Thr':<5} {'N':<3} {'Filter':<14} {'Recipe':<22} {'Exit':<10} {'Total%':<10} {'OOS%':<9} {'Apr%':<8} {'Pre%':<8} {'DWin':<5} {'H1':<5} {'Days'}"

    print(f"\n{'='*130}")
    print("TOP 30 BY TOTAL RETURN (robust)")
    print(f"{'='*130}")
    print(hdr)
    for i, r in enumerate(by_total[:30], 1):
        print(f"{i:<3} {r['thr']:<5} {r['tn']:<3} {r['f']:<14} {r['r']:<22} {r['e']:<10} "
              f"{r['total']:>8.0f}% {r['oos']:>7.1f}% {r['apr']:>6.1f}% {r['pre']:>6.1f}% "
              f"{r['dwin']:>4.0%} {r['h1']:>4.0%} {r['days']}")

    print(f"\n{'='*130}")
    print("TOP 30 BY OOS RETURN (2025-07 ~ 2026-04)")
    print(f"{'='*130}")
    print(hdr)
    for i, r in enumerate(by_oos[:30], 1):
        print(f"{i:<3} {r['thr']:<5} {r['tn']:<3} {r['f']:<14} {r['r']:<22} {r['e']:<10} "
              f"{r['total']:>8.0f}% {r['oos']:>7.1f}% {r['apr']:>6.1f}% {r['pre']:>6.1f}% "
              f"{r['dwin']:>4.0%} {r['h1']:>4.0%} {r['days']}")

    print(f"\n{'='*130}")
    print("TOP 30 BY APRIL 2026 RETURN")
    print(f"{'='*130}")
    print(hdr)
    for i, r in enumerate(by_apr[:30], 1):
        print(f"{i:<3} {r['thr']:<5} {r['tn']:<3} {r['f']:<14} {r['r']:<22} {r['e']:<10} "
              f"{r['total']:>8.0f}% {r['oos']:>7.1f}% {r['apr']:>6.1f}% {r['pre']:>6.1f}% "
              f"{r['dwin']:>4.0%} {r['h1']:>4.0%} {r['days']}")

    # Monthly for best total
    best = by_total[0]
    print(f"\n{'='*130}")
    print(f"BEST TOTAL MONTHLY: raw>={best['thr']} top{best['tn']} {best['f']} {best['r']} {best['e']}")
    print(f"{'='*130}")
    pool = (probs >= best["thr"]) & filter_dict[best["f"]]
    sk = compute_sort_key(best["r"])
    dsel = np.full((n_days, best["tn"]), -1, dtype=np.int32)
    for di, didx in enumerate(day_indices):
        idx = didx[pool[didx]]
        if idx.size == 0:
            continue
        idx = idx[np.argsort(-sk[idx])[:best["tn"]]]
        dsel[di, :idx.size] = idx

    print(f"{'Month':<8} {'Days':<5} {'Tix':<5} {'Return%':<10} {'DWin':<7} {'TWin':<7} {'H+1':<6}")
    for month in sorted(set(day_months)):
        midx = np.where(day_months == month)[0]
        ms = dsel[midx]
        mv = ms >= 0
        mt = int(mv.sum())
        if mt == 0:
            continue
        msafe = np.where(mv, ms, 0)
        mr = exits[best["e"]][msafe]
        mr = np.where(mv, mr, 0.0)
        ma = actual[msafe]
        ma = np.where(mv, ma, 0.0)
        mc = mv.sum(axis=1)
        mdv = mc > 0
        mds = mr.sum(axis=1)
        mda = np.zeros(len(midx))
        mda[mdv] = mds[mdv] / mc[mdv]
        mdr = mda[mdv]
        mret = pct_prod(mdr)
        mdwin = float((mdr > 0).mean()) if mdr.size > 0 else 0
        mtwin = float(((mr > 0) & mv).sum() / mt)
        mh1 = float(ma.sum() / mt)
        period = "PRE" if month < "2023-05" else ("OOS" if month >= "2025-07" else "TRN")
        print(f"  {month:<7} {int(mdv.sum()):<5} {mt:<5} {mret:>8.2f}% "
              f"{mdwin:>6.1%} {mtwin:>6.1%} {mh1:>5.1%}  [{period}]")


if __name__ == "__main__":
    main()
