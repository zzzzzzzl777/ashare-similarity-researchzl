"""Dual model strategy search: S2 vs PhaseC, find best balanced strategy for each."""
import numpy as np, pandas as pd, torch, pickle, math, time
from pathlib import Path
import pyarrow.parquet as pq

S2_BUNDLE = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T002433Z_a0ec8105\model_bundle.pt")
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


def load_and_score(bundle_path, df, n):
    payload = torch.load(str(bundle_path), map_location="cpu", weights_only=False)
    members = [pickle.loads(m["model_bytes"]) for m in payload["members"]]
    feature_names = list(payload["feature_names"])
    mean, std_val = payload["mean"], payload["std"].clone()
    std_val[std_val == 0] = 1.0
    selected_indices = payload["selected_indices"]

    raw_features = np.zeros((n, len(feature_names)), dtype=np.float32)
    for i, name in enumerate(feature_names):
        if name in df.columns:
            raw_features[:, i] = df[name].fillna(0).to_numpy(dtype=np.float32)
    x = torch.as_tensor(raw_features, dtype=torch.float32)
    x = (x - mean) / std_val
    if selected_indices is not None:
        x = x[:, selected_indices]
    probs = np.stack([m.predict_proba(x.numpy())[:, 1] for m in members]).mean(axis=0).astype(np.float32)
    return probs


def search_best(probs, df, n, model_name, day_codes, day_values, day_indices, n_days,
                day_months, day_dates, close_ret, high_ret, low_ret):
    t0 = time.time()

    exits = {
        "tp10": np.where(high_ret >= 10, 10.0, close_ret),
        "tp7": np.where(high_ret >= 7, 7.0, close_ret),
        "sl3_tp10": np.where((high_ret >= 10) & ~(low_ret <= -3), 10.0,
                             np.where(low_ret <= -3, -3.0, close_ret)),
        "sl5_tp10": np.where((high_ret >= 10) & ~(low_ret <= -5), 10.0,
                             np.where(low_ret <= -5, -5.0, close_ret)),
        "close": close_ret.copy(),
    }

    def s(col):
        return df[col].fillna(0).to_numpy(dtype=np.float64) if col in df.columns else np.zeros(n)

    t_arr, c_arr, vz, az_arr, rsi6 = s("turnover"), s("close"), s("volume_z_20"), s("amount_z_20"), s("rsi_6")
    tz20 = s("turnover_z_20")
    rng = s("range_pct")

    filters = [
        ("none", np.ones(n, dtype=bool)),
        ("vz>=0", vz >= 0),
        ("az>=0", az_arr >= 0),
        ("c>=5", c_arr >= 5),
        ("t>=5", t_arr >= 5),
        ("t>=3", t_arr >= 3),
        ("t>=5|vz>=0", (t_arr >= 5) & (vz >= 0)),
        ("t>=5|az>=0", (t_arr >= 5) & (az_arr >= 0)),
        ("t>=3|vz>=0", (t_arr >= 3) & (vz >= 0)),
        ("t5_20|c5_60", (t_arr >= 5) & (t_arr <= 20) & (c_arr >= 5) & (c_arr <= 60)),
        ("t5_30|c5_100", (t_arr >= 5) & (t_arr <= 30) & (c_arr >= 5) & (c_arr <= 100)),
        ("vz>=0|c>=5", (vz >= 0) & (c_arr >= 5)),
        ("az>=0|c>=5", (az_arr >= 0) & (c_arr >= 5)),
        ("az>=1|vz>=0", (az_arr >= 1) & (vz >= 0)),
    ]

    def compute_sort_key(recipe):
        p = probs.astype(np.float64)
        if recipe == "score_then_rsi6_low":
            return p * 1000 - rsi6
        if recipe == "amount_z_high":
            return az_arr * 1000 + p
        if recipe == "volume_z_high":
            return vz * 1000 + p
        if recipe == "activity_z_high":
            return rng * tz20 * 1000 + p
        if recipe == "prob_desc":
            return p
        if recipe == "rsi6_low":
            return -rsi6 * 1000 + p
        return p

    recipes = ["score_then_rsi6_low", "amount_z_high", "volume_z_high",
               "activity_z_high", "prob_desc", "rsi6_low"]

    pre_mask = day_dates < "2023-05-01"
    oos_mask = day_dates >= "2025-07-01"
    apr_mask = day_months == "2026-04"

    thresholds = [round(x / 100.0, 2) for x in range(55, 80)]
    top_ns = [1, 2, 3, 4]

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
                    if sig < 30:
                        continue
                    safe = np.where(valid, sel, 0)

                    for ename, exit_arr in exits.items():
                        realized = exit_arr[safe]
                        realized = np.where(valid, realized, 0.0)
                        dsum = realized.sum(axis=1)
                        davg = np.zeros(n_days)
                        davg[dv] = dsum[dv] / counts[dv]

                        pre_dv = pre_mask & dv
                        if not pre_dv.any():
                            continue
                        pre_ret = pct_prod(davg[pre_dv])
                        if pre_ret <= 0:
                            continue

                        oos_dv = oos_mask & dv
                        if not oos_dv.any():
                            continue
                        oos_ret = pct_prod(davg[oos_dv])
                        if oos_ret <= 0:
                            continue

                        apr_dv = apr_mask & dv
                        apr_ret = pct_prod(davg[apr_dv]) if apr_dv.any() else 0

                        oos_months_list = sorted(set(day_months[oos_mask]))
                        monthly_oos = {}
                        for m in oos_months_list:
                            midx = (day_months == m) & dv
                            if midx.any():
                                monthly_oos[m] = pct_prod(davg[midx])
                        worst_oos = min(monthly_oos.values()) if monthly_oos else -99
                        neg5_count = sum(1 for v in monthly_oos.values() if v < -5)

                        pre_months_list = sorted(set(day_months[pre_mask]))
                        monthly_pre = {}
                        for m in pre_months_list:
                            midx = (day_months == m) & dv
                            if midx.any():
                                monthly_pre[m] = pct_prod(davg[midx])
                        worst_pre = min(monthly_pre.values()) if monthly_pre else -99

                        dr = davg[dv]
                        total = pct_prod(dr)
                        dwin = float((dr > 0).mean())

                        results.append({
                            "thr": thr, "tn": tn, "f": fname, "r": recipe, "e": ename,
                            "pre": pre_ret, "oos": oos_ret, "apr": apr_ret,
                            "total": total, "dwin": dwin, "days": sig,
                            "worst_oos": worst_oos, "worst_pre": worst_pre,
                            "neg5": neg5_count, "monthly_oos": monthly_oos, "monthly_pre": monthly_pre,
                        })

        print(f"  [{model_name}] {recipe} done, {len(results):,} qualifying, {time.time()-t0:.0f}s", flush=True)

    # Composite score
    for r in results:
        oos_vals = list(r["monthly_oos"].values())
        avg_oos = np.mean(oos_vals) if oos_vals else 0
        r["avg_oos"] = avg_oos
        pre_bonus = min(r["pre"], 50) * 0.5
        worst_penalty = max(0, -r["worst_oos"] - 5) * 3
        r["score"] = r["apr"] * 2 + avg_oos * 3 + pre_bonus - worst_penalty - r["neg5"] * 10

    return results


def print_results(results, model_name):
    ranked = sorted(results, key=lambda x: x["score"], reverse=True)
    print(f"\n{'='*150}")
    print(f"[{model_name}] TOP 20 BALANCED (pre>0% AND oos>0%, ranked by composite)")
    print(f"{'='*150}")
    hdr = (f"{'#':<3} {'Thr':<5} {'N':<3} {'Filter':<14} {'Recipe':<22} {'Exit':<10} "
           f"{'Apr%':<7} {'AvgOOS':<7} {'WrstOOS':<8} {'Pre%':<7} {'WPre':<7} {'N<-5':<5} {'DWin':<5} {'Score':<6}")
    print(hdr)
    for i, r in enumerate(ranked[:20], 1):
        print(f"{i:<3} {r['thr']:<5} {r['tn']:<3} {r['f']:<14} {r['r']:<22} {r['e']:<10} "
              f"{r['apr']:>5.1f}% {r['avg_oos']:>5.1f}% {r['worst_oos']:>6.1f}% "
              f"{r['pre']:>5.1f}% {r['worst_pre']:>5.1f}% {r['neg5']:<5} {r['dwin']:>4.0%} {r['score']:>5.0f}")

    # Top 3 detail
    for idx in range(min(3, len(ranked))):
        r = ranked[idx]
        print(f"\n--- [{model_name}] #{idx+1}: raw>={r['thr']} top{r['tn']} {r['f']} {r['r']} {r['e']} ---")
        print(f"    Apr:{r['apr']:.1f}% | OOS:{r['oos']:.1f}% | Pre:{r['pre']:.1f}% | Total:{r['total']:.0f}%")
        row = "    PRE: "
        for m in sorted(r["monthly_pre"].keys()):
            row += f"{m[5:7]}:{r['monthly_pre'][m]:>5.1f}  "
        print(row)
        row = "    OOS: "
        for m in sorted(r["monthly_oos"].keys()):
            ret = r["monthly_oos"][m]
            marker = "!" if ret < -5 else " "
            row += f"{m[5:7]}:{ret:>5.1f}{marker} "
        print(row)

    return ranked


def main():
    t0 = time.time()

    # Load all data (need union of both models' features)
    payload_s2 = torch.load(str(S2_BUNDLE), map_location="cpu", weights_only=False)
    payload_pc = torch.load(str(PC_BUNDLE), map_location="cpu", weights_only=False)
    s2_features = set(payload_s2["feature_names"])
    pc_features = set(payload_pc["feature_names"])

    needed = META | STRAT | s2_features | pc_features
    frames = []
    for cp, s, e in [(CACHE_JAN, "2023-01-01", "2023-01-31"),
                     (CACHE_PRETRAIN, "2023-02-01", "2023-04-30"),
                     (CACHE_MAIN, "2023-06-01", "2026-05-31")]:
        schema = set(pq.read_schema(str(cp)).names)
        cols = [c for c in sorted(needed) if c in schema]
        tmp = pd.read_parquet(str(cp), columns=cols)
        tmp = tmp[(tmp["date"] >= s) & (tmp["date"] <= e)].copy()
        frames.append(tmp)

    df = pd.concat(frames, ignore_index=True).drop_duplicates(
        subset=["date", "symbol"], keep="first").reset_index(drop=True)
    df = df[df["limit_up_like"] != 1].copy()
    df = df[df["short_phase_days_3"] >= 1].copy()
    df = df.reset_index(drop=True)
    n = len(df)
    print(f"Data: {n:,} rows, {df['date'].nunique()} days, {df['date'].min()} ~ {df['date'].max()}")

    # Day structure
    day_codes, day_values = pd.factorize(df["date"].to_numpy(), sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    n_days = len(day_values)
    day_months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()
    day_dates = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m-%d").to_numpy()

    # Returns
    close_ret = df["next_close_return_pct"].fillna(0).to_numpy(dtype=np.float64)
    high_ret = np.where(np.isnan(df["next_high_return_pct"].to_numpy()),
                        close_ret, df["next_high_return_pct"].to_numpy(dtype=np.float64))
    low_ret = np.where(np.isnan(df["next_low_return_pct"].to_numpy()),
                       close_ret, df["next_low_return_pct"].to_numpy(dtype=np.float64))

    # Score S2
    print("\nScoring S2...")
    s2_probs = load_and_score(S2_BUNDLE, df, n)
    print(f"  S2 prob range: {s2_probs.min():.4f} ~ {s2_probs.max():.4f}")

    # Score PhaseC
    print("Scoring PhaseC...")
    pc_probs = load_and_score(PC_BUNDLE, df, n)
    print(f"  PC prob range: {pc_probs.min():.4f} ~ {pc_probs.max():.4f}")

    # Search S2
    print(f"\n{'#'*80}")
    print("SEARCHING S2 MODEL")
    print(f"{'#'*80}")
    s2_results = search_best(s2_probs, df, n, "S2", day_codes, day_values, day_indices,
                             n_days, day_months, day_dates, close_ret, high_ret, low_ret)

    # Search PhaseC
    print(f"\n{'#'*80}")
    print("SEARCHING PhaseC MODEL")
    print(f"{'#'*80}")
    pc_results = search_best(pc_probs, df, n, "PhaseC", day_codes, day_values, day_indices,
                             n_days, day_months, day_dates, close_ret, high_ret, low_ret)

    # Print results
    s2_ranked = print_results(s2_results, "S2")
    pc_ranked = print_results(pc_results, "PhaseC")

    # Head-to-head comparison
    print(f"\n{'='*150}")
    print("HEAD-TO-HEAD: S2 BEST vs PhaseC BEST")
    print(f"{'='*150}")
    if s2_ranked and pc_ranked:
        s2_best = s2_ranked[0]
        pc_best = pc_ranked[0]
        print(f"{'Metric':<20} {'S2 Best':<40} {'PhaseC Best':<40}")
        s2_desc = f"raw>={s2_best['thr']} top{s2_best['tn']} {s2_best['f']} {s2_best['r']} {s2_best['e']}"
        pc_desc = f"raw>={pc_best['thr']} top{pc_best['tn']} {pc_best['f']} {pc_best['r']} {pc_best['e']}"
        print(f"{'Strategy':<20} {s2_desc:<40} {pc_desc:<40}")
        print(f"{'April 2026':<20} {s2_best['apr']:>6.1f}%{'':<32} {pc_best['apr']:>6.1f}%")
        print(f"{'OOS Total':<20} {s2_best['oos']:>6.1f}%{'':<32} {pc_best['oos']:>6.1f}%")
        print(f"{'OOS Avg Monthly':<20} {s2_best['avg_oos']:>6.1f}%{'':<32} {pc_best['avg_oos']:>6.1f}%")
        print(f"{'OOS Worst Month':<20} {s2_best['worst_oos']:>6.1f}%{'':<32} {pc_best['worst_oos']:>6.1f}%")
        print(f"{'Pretrain Total':<20} {s2_best['pre']:>6.1f}%{'':<32} {pc_best['pre']:>6.1f}%")
        print(f"{'Pretrain Worst':<20} {s2_best['worst_pre']:>6.1f}%{'':<32} {pc_best['worst_pre']:>6.1f}%")
        print(f"{'Daily Win Rate':<20} {s2_best['dwin']:>6.1%}{'':<32} {pc_best['dwin']:>6.1%}")
        print(f"{'OOS Months <-5%':<20} {s2_best['neg5']:<40} {pc_best['neg5']}")
        print(f"{'Total Return':<20} {s2_best['total']:>6.0f}%{'':<32} {pc_best['total']:>6.0f}%")
        print(f"{'Signal Days':<20} {s2_best['days']:<40} {pc_best['days']}")
        print(f"{'Score':<20} {s2_best['score']:>6.0f}{'':<33} {pc_best['score']:>6.0f}")

    print(f"\nTotal time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
