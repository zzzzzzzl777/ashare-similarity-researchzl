"""Comprehensive dual-model strategy search with expanded grid."""
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


def search_model(probs, df, n, model_name, day_indices, n_days, day_months, day_dates,
                 close_ret, high_ret, low_ret, actual):
    t0 = time.time()

    exits = {
        "close": close_ret.copy(),
        "tp5": np.where(high_ret >= 5, 5.0, close_ret),
        "tp7": np.where(high_ret >= 7, 7.0, close_ret),
        "tp10": np.where(high_ret >= 10, 10.0, close_ret),
        "sl2_tp5": np.where((high_ret >= 5) & ~(low_ret <= -2), 5.0,
                            np.where(low_ret <= -2, -2.0, close_ret)),
        "sl2_tp7": np.where((high_ret >= 7) & ~(low_ret <= -2), 7.0,
                            np.where(low_ret <= -2, -2.0, close_ret)),
        "sl3_tp7": np.where((high_ret >= 7) & ~(low_ret <= -3), 7.0,
                            np.where(low_ret <= -3, -3.0, close_ret)),
        "sl3_tp10": np.where((high_ret >= 10) & ~(low_ret <= -3), 10.0,
                             np.where(low_ret <= -3, -3.0, close_ret)),
        "sl5_tp10": np.where((high_ret >= 10) & ~(low_ret <= -5), 10.0,
                             np.where(low_ret <= -5, -5.0, close_ret)),
    }

    def s(col):
        return df[col].fillna(0).to_numpy(dtype=np.float64) if col in df.columns else np.zeros(n)

    t_arr, c_arr = s("turnover"), s("close")
    vz, az_arr = s("volume_z_20"), s("amount_z_20")
    rsi6 = s("rsi_6")
    tz20, rng = s("turnover_z_20"), s("range_pct")

    filters = [
        ("none", np.ones(n, dtype=bool)),
        ("vz>=0", vz >= 0),
        ("az>=0", az_arr >= 0),
        ("c>=5", c_arr >= 5),
        ("c>=10", c_arr >= 10),
        ("t>=3", t_arr >= 3),
        ("t>=5", t_arr >= 5),
        ("t>=8", t_arr >= 8),
        ("t>=3|vz>=0", (t_arr >= 3) & (vz >= 0)),
        ("t>=5|vz>=0", (t_arr >= 5) & (vz >= 0)),
        ("t>=5|az>=0", (t_arr >= 5) & (az_arr >= 0)),
        ("t>=8|vz>=0", (t_arr >= 8) & (vz >= 0)),
        ("t5_20|c5_60", (t_arr >= 5) & (t_arr <= 20) & (c_arr >= 5) & (c_arr <= 60)),
        ("t5_30|c5_100", (t_arr >= 5) & (t_arr <= 30) & (c_arr >= 5) & (c_arr <= 100)),
        ("t3_30|c5_100", (t_arr >= 3) & (t_arr <= 30) & (c_arr >= 5) & (c_arr <= 100)),
        ("vz>=0|c>=5", (vz >= 0) & (c_arr >= 5)),
        ("az>=0|c>=5", (az_arr >= 0) & (c_arr >= 5)),
        ("az>=1|vz>=0", (az_arr >= 1) & (vz >= 0)),
        ("vz>=1", vz >= 1),
        ("az>=1", az_arr >= 1),
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
        if recipe == "prob_x_vz":
            return p * (1 + np.clip(vz, 0, 10))
        if recipe == "prob_x_az":
            return p * (1 + np.clip(az_arr, 0, 10))
        return p

    recipes = ["score_then_rsi6_low", "amount_z_high", "volume_z_high",
               "activity_z_high", "prob_desc", "rsi6_low", "prob_x_vz", "prob_x_az"]

    pre_mask = day_dates < "2023-05-01"
    oos_mask = day_dates >= "2025-07-01"
    apr_mask = day_months == "2026-04"

    thresholds = [round(x / 100.0, 2) for x in range(55, 82)]
    top_ns = [1, 2, 3, 4, 5, 6]

    total_combos = len(thresholds) * len(top_ns) * len(filters) * len(recipes) * len(exits)
    print(f"  [{model_name}] Grid: {len(thresholds)} thr x {len(top_ns)} topN x {len(filters)} filt x "
          f"{len(recipes)} recipes x {len(exits)} exits = {total_combos:,}")

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
                    tix = int(counts.sum())

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
                        neg10_count = sum(1 for v in monthly_oos.values() if v < -10)

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

                        # H+1 hit rate
                        act_v = actual[safe]
                        act_v = np.where(valid, act_v, 0.0)
                        h1 = float(act_v.sum() / tix) if tix > 0 else 0

                        results.append({
                            "thr": thr, "tn": tn, "f": fname, "r": recipe, "e": ename,
                            "pre": pre_ret, "oos": oos_ret, "apr": apr_ret,
                            "total": total, "dwin": dwin, "days": sig, "tix": tix, "h1": h1,
                            "worst_oos": worst_oos, "worst_pre": worst_pre,
                            "neg5": neg5_count, "neg10": neg10_count,
                            "monthly_oos": monthly_oos, "monthly_pre": monthly_pre,
                        })

        print(f"  [{model_name}] {recipe} done, {len(results):,} qualifying, {time.time()-t0:.0f}s", flush=True)

    # Composite scores - multiple perspectives
    for r in results:
        oos_vals = list(r["monthly_oos"].values())
        avg_oos = np.mean(oos_vals) if oos_vals else 0
        r["avg_oos"] = avg_oos
        pre_bonus = min(r["pre"], 50) * 0.5
        worst_penalty = max(0, -r["worst_oos"] - 5) * 3
        r["score_balanced"] = r["apr"] * 2 + avg_oos * 3 + pre_bonus - worst_penalty - r["neg5"] * 10
        r["score_april"] = r["apr"] * 3 + avg_oos * 2 + pre_bonus - r["neg10"] * 15
        r["score_stable"] = avg_oos * 4 + min(r["pre"], 30) * 1 - worst_penalty * 2 - r["neg5"] * 15 + r["apr"]

    return results


def print_top(results, model_name, sort_key, title, n=15):
    ranked = sorted(results, key=lambda x: x[sort_key], reverse=True)
    print(f"\n{'='*160}")
    print(f"[{model_name}] {title}")
    print(f"{'='*160}")
    hdr = (f"{'#':<3} {'Thr':<5} {'N':<3} {'Filter':<14} {'Recipe':<20} {'Exit':<10} "
           f"{'Apr%':<7} {'AvgOOS':<7} {'WrstOOS':<8} {'Pre%':<7} {'WPre':<7} "
           f"{'N<-5':<5} {'DWin':<5} {'H+1':<5} {'Scr':<6}")
    print(hdr)
    for i, r in enumerate(ranked[:n], 1):
        print(f"{i:<3} {r['thr']:<5} {r['tn']:<3} {r['f']:<14} {r['r']:<20} {r['e']:<10} "
              f"{r['apr']:>5.1f}% {r['avg_oos']:>5.1f}% {r['worst_oos']:>6.1f}% "
              f"{r['pre']:>5.1f}% {r['worst_pre']:>5.1f}% {r['neg5']:<5} "
              f"{r['dwin']:>4.0%} {r['h1']:>4.0%} {r[sort_key]:>5.0f}")
    return ranked


def print_detail(results, model_name, sort_key, top_n=3):
    ranked = sorted(results, key=lambda x: x[sort_key], reverse=True)
    for idx in range(min(top_n, len(ranked))):
        r = ranked[idx]
        print(f"\n--- [{model_name}] #{idx+1}: raw>={r['thr']} top{r['tn']} {r['f']} {r['r']} {r['e']} ---")
        print(f"    Apr:{r['apr']:.1f}% | OOS:{r['oos']:.1f}% | Pre:{r['pre']:.1f}% | "
              f"Total:{r['total']:.0f}% | DWin:{r['dwin']:.1%} | H+1:{r['h1']:.1%}")
        row = "    PRE: "
        for m in sorted(r["monthly_pre"].keys()):
            ret = r["monthly_pre"][m]
            marker = "!" if ret < -10 else ("*" if ret < -5 else " ")
            row += f"{m[5:7]}:{ret:>5.1f}{marker} "
        print(row)
        row = "    OOS: "
        for m in sorted(r["monthly_oos"].keys()):
            ret = r["monthly_oos"][m]
            marker = "!" if ret < -10 else ("*" if ret < -5 else " ")
            row += f"{m[5:7]}:{ret:>5.1f}{marker} "
        print(row)


def main():
    t0 = time.time()

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
    print(f"Data: {n:,} rows, {df['date'].nunique()} days")

    day_codes, day_values = pd.factorize(df["date"].to_numpy(), sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    n_days = len(day_values)
    day_months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()
    day_dates = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m-%d").to_numpy()

    close_ret = df["next_close_return_pct"].fillna(0).to_numpy(dtype=np.float64)
    high_ret = np.where(np.isnan(df["next_high_return_pct"].to_numpy()),
                        close_ret, df["next_high_return_pct"].to_numpy(dtype=np.float64))
    low_ret = np.where(np.isnan(df["next_low_return_pct"].to_numpy()),
                       close_ret, df["next_low_return_pct"].to_numpy(dtype=np.float64))
    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)

    # Score both
    print("\nScoring S2...")
    s2_probs = load_and_score(S2_BUNDLE, df, n)
    print(f"  range: {s2_probs.min():.4f} ~ {s2_probs.max():.4f}")
    print("Scoring PhaseC...")
    pc_probs = load_and_score(PC_BUNDLE, df, n)
    print(f"  range: {pc_probs.min():.4f} ~ {pc_probs.max():.4f}")

    # Search S2
    print(f"\n{'#'*80}")
    print("SEARCHING S2")
    print(f"{'#'*80}")
    s2_res = search_model(s2_probs, df, n, "S2", day_indices, n_days, day_months,
                          day_dates, close_ret, high_ret, low_ret, actual)
    print(f"  S2 total qualifying: {len(s2_res):,}")

    # Search PhaseC
    print(f"\n{'#'*80}")
    print("SEARCHING PhaseC")
    print(f"{'#'*80}")
    pc_res = search_model(pc_probs, df, n, "PC", day_indices, n_days, day_months,
                          day_dates, close_ret, high_ret, low_ret, actual)
    print(f"  PhaseC total qualifying: {len(pc_res):,}")

    # === S2 Rankings ===
    print_top(s2_res, "S2", "score_balanced", "TOP 15 BALANCED (Apr + OOS avg + pretrain)", 15)
    print_detail(s2_res, "S2", "score_balanced", 3)

    print_top(s2_res, "S2", "score_april", "TOP 15 APRIL-FOCUSED", 15)
    print_detail(s2_res, "S2", "score_april", 3)

    print_top(s2_res, "S2", "score_stable", "TOP 15 STABILITY-FOCUSED (low drawdown)", 15)
    print_detail(s2_res, "S2", "score_stable", 3)

    # === PhaseC Rankings ===
    print_top(pc_res, "PC", "score_balanced", "TOP 15 BALANCED (Apr + OOS avg + pretrain)", 15)
    print_detail(pc_res, "PC", "score_balanced", 3)

    print_top(pc_res, "PC", "score_april", "TOP 15 APRIL-FOCUSED", 15)
    print_detail(pc_res, "PC", "score_april", 3)

    print_top(pc_res, "PC", "score_stable", "TOP 15 STABILITY-FOCUSED (low drawdown)", 15)
    print_detail(pc_res, "PC", "score_stable", 3)

    # === Head to Head: best from each ===
    print(f"\n{'='*160}")
    print("GRAND FINAL: BEST OF EACH MODEL (balanced score)")
    print(f"{'='*160}")
    s2_best = sorted(s2_res, key=lambda x: x["score_balanced"], reverse=True)[0]
    pc_best = sorted(pc_res, key=lambda x: x["score_balanced"], reverse=True)[0]

    for label, r in [("S2 BEST", s2_best), ("PC BEST", pc_best)]:
        print(f"\n  {label}: raw>={r['thr']} top{r['tn']} {r['f']} {r['r']} {r['e']}")
        print(f"    Apr: {r['apr']:.1f}% | OOS: {r['oos']:.1f}% | Pre: {r['pre']:.1f}% | "
              f"Total: {r['total']:.0f}% | DWin: {r['dwin']:.1%} | H+1: {r['h1']:.1%}")
        print(f"    OOS avg: {r['avg_oos']:.1f}% | Worst OOS: {r['worst_oos']:.1f}% | "
              f"Worst Pre: {r['worst_pre']:.1f}% | Months<-5%: {r['neg5']}")
        row = "    PRE: "
        for m in sorted(r["monthly_pre"].keys()):
            ret = r["monthly_pre"][m]
            marker = "!" if ret < -10 else ("*" if ret < -5 else " ")
            row += f"{m[5:7]}:{ret:>5.1f}{marker} "
        print(row)
        row = "    OOS: "
        for m in sorted(r["monthly_oos"].keys()):
            ret = r["monthly_oos"][m]
            marker = "!" if ret < -10 else ("*" if ret < -5 else " ")
            row += f"{m[5:7]}:{ret:>5.1f}{marker} "
        print(row)

    print(f"\nTotal time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
