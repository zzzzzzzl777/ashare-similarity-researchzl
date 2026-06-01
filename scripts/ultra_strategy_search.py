"""Ultra-aggressive search: maximize April + OOS returns with acceptable drawdown.
Wider grid: topN up to 10, more filters, more recipes."""
import numpy as np, pandas as pd, torch, pickle, math
from pathlib import Path
import pyarrow.parquet as pq

PC_BUNDLE = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt")
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
    schema = set(pq.read_schema(str(CACHE_MAIN)).names)
    cols = [c for c in sorted(needed) if c in schema]

    # OOS only for speed (2025-07 ~ 2026-05)
    df = pd.read_parquet(str(CACHE_MAIN), columns=cols)
    df = df[(df["date"] >= "2025-07-01") & (df["date"] <= "2026-04-30")].copy()
    df = df[df["limit_up_like"] != 1].copy()
    df = df[df["short_phase_days_3"] >= 1].copy()
    df = df.reset_index(drop=True)
    n = len(df)
    print(f"OOS Data: {n:,} rows, {df['date'].nunique()} days")

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

    close_ret = df["next_close_return_pct"].fillna(0).to_numpy(dtype=np.float64)
    high_ret = np.where(np.isnan(df["next_high_return_pct"].to_numpy()),
                        close_ret, df["next_high_return_pct"].to_numpy(dtype=np.float64))
    low_ret = np.where(np.isnan(df["next_low_return_pct"].to_numpy()),
                       close_ret, df["next_low_return_pct"].to_numpy(dtype=np.float64))

    # More exit modes
    exits = {
        "close": close_ret.copy(),
        "tp10": np.where(high_ret >= 10, 10.0, close_ret),
        "tp7": np.where(high_ret >= 7, 7.0, close_ret),
        "tp5": np.where(high_ret >= 5, 5.0, close_ret),
        "sl3_tp10": np.where((high_ret >= 10) & ~(low_ret <= -3), 10.0,
                             np.where(low_ret <= -3, -3.0, close_ret)),
        "sl5_tp10": np.where((high_ret >= 10) & ~(low_ret <= -5), 10.0,
                             np.where(low_ret <= -5, -5.0, close_ret)),
        "sl3_tp7": np.where((high_ret >= 7) & ~(low_ret <= -3), 7.0,
                            np.where(low_ret <= -3, -3.0, close_ret)),
        "sl5_tp7": np.where((high_ret >= 7) & ~(low_ret <= -5), 7.0,
                            np.where(low_ret <= -5, -5.0, close_ret)),
    }

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
        ("t>=3|c5_60", (t_arr >= 3) & (c_arr >= 5) & (c_arr <= 60)),
        ("t5_30|c5_100", (t_arr >= 5) & (t_arr <= 30) & (c_arr >= 5) & (c_arr <= 100)),
        ("az>=1|vz>=0", (az_arr >= 1) & (vz >= 0)),
        ("t>=8|vz>=0", (t_arr >= 8) & (vz >= 0)),
    ]
    filter_dict = dict(filters)

    def compute_sort_key(recipe):
        p = probs.astype(np.float64)
        if recipe == "score_then_rsi6_low":
            return p * 1000 - rsi6
        if recipe == "volume_z_high":
            return vz * 1000 + p
        if recipe == "amount_z_high":
            return az_arr * 1000 + p
        if recipe == "activity_z_high":
            return s("range_pct") * s("turnover_z_20") * 1000 + p
        if recipe == "prob_desc":
            return p
        if recipe == "rsi6_low":
            return -rsi6 * 1000 + p
        return p

    recipes = ["score_then_rsi6_low", "volume_z_high", "amount_z_high",
               "activity_z_high", "prob_desc", "rsi6_low"]

    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"].to_numpy(), sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    n_days = len(day_values)
    day_months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()

    thresholds = [round(x / 100.0, 2) for x in range(55, 80)]
    top_ns = [1, 2, 3, 4, 5, 6, 8, 10]

    print(f"Grid: {len(thresholds)} thr x {len(top_ns)} topN x {len(filters)} filters x "
          f"{len(recipes)} recipes x {len(exits)} exits = "
          f"{len(thresholds)*len(top_ns)*len(filters)*len(recipes)*len(exits):,} combos")

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
                    if sig < 20:
                        continue
                    safe = np.where(valid, sel, 0)

                    for ename, exit_arr in exits.items():
                        realized = exit_arr[safe]
                        realized = np.where(valid, realized, 0.0)
                        dsum = realized.sum(axis=1)
                        davg = np.zeros(n_days)
                        davg[dv] = dsum[dv] / counts[dv]

                        # Monthly returns
                        monthly = {}
                        for month in sorted(set(day_months)):
                            midx = np.where(day_months == month)[0]
                            mdv = dv[midx]
                            if not mdv.any():
                                continue
                            monthly[month] = pct_prod(davg[midx][mdv])

                        apr = monthly.get("2026-04", 0)
                        oos_rets = [monthly.get(m, 0) for m in sorted(set(day_months))]
                        worst = min(oos_rets) if oos_rets else -99
                        avg_ret = np.mean(oos_rets) if oos_rets else 0
                        neg_months = sum(1 for r in oos_rets if r < -8)

                        # Filter: April > 30% AND worst month > -15% AND <2 months below -8%
                        if apr >= 30 and worst >= -15 and neg_months <= 1:
                            total = pct_prod(davg[dv])
                            dwin = float((davg[dv] > 0).mean())
                            results.append({
                                "thr": thr, "tn": tn, "f": fname, "r": recipe, "e": ename,
                                "apr": apr, "total": total, "worst": worst, "avg": avg_ret,
                                "dwin": dwin, "days": sig, "neg8": neg_months,
                                "monthly": monthly,
                            })
        print(f"  {recipe} done, {len(results):,} qualifying strategies", flush=True)

    print(f"\nStrategies with Apr>=30% AND worst>=-15% AND <=1 month<-8%: {len(results):,}")

    # Sort by combined score: Apr + total_oos - worst_penalty
    for r in results:
        r["score"] = r["apr"] * 2 + r["avg"] * 3 + min(r["worst"] + 5, 0) * 5

    ranked = sorted(results, key=lambda x: x["score"], reverse=True)

    print(f"\n{'='*140}")
    print("TOP 40 STRATEGIES: Apr>=30%, Worst>=-15%, <=1 month <-8%")
    print(f"{'='*140}")
    hdr = (f"{'#':<3} {'Thr':<5} {'N':<3} {'Filter':<14} {'Recipe':<22} {'Exit':<10} "
           f"{'Apr%':<7} {'Total%':<9} {'Avg%':<6} {'Worst%':<7} {'DWin':<5} {'Days':<4} {'Score':<6}")
    print(hdr)
    for i, r in enumerate(ranked[:40], 1):
        print(f"{i:<3} {r['thr']:<5} {r['tn']:<3} {r['f']:<14} {r['r']:<22} {r['e']:<10} "
              f"{r['apr']:>5.1f}% {r['total']:>7.1f}% {r['avg']:>4.1f}% {r['worst']:>5.1f}% "
              f"{r['dwin']:>4.0%} {r['days']:<4} {r['score']:>5.0f}")

    # Monthly detail for top 5
    if ranked:
        for idx in range(min(5, len(ranked))):
            r = ranked[idx]
            print(f"\n--- #{idx+1}: raw>={r['thr']} top{r['tn']} {r['f']} {r['r']} {r['e']} ---")
            print(f"    Apr: {r['apr']:.1f}% | Total OOS: {r['total']:.1f}% | "
                  f"Worst: {r['worst']:.1f}% | DWin: {r['dwin']:.0%}")
            months_sorted = sorted(r["monthly"].keys())
            row = "    "
            for m in months_sorted:
                ret = r["monthly"][m]
                marker = "!" if ret < -8 else ("*" if ret < -5 else " ")
                row += f"{m[5:7]}:{ret:>5.1f}{marker} "
            print(row)


if __name__ == "__main__":
    main()
