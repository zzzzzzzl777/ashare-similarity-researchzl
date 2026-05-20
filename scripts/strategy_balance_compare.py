"""Detailed monthly comparison of candidate strategies.
Goal: High April return WITHOUT bad months elsewhere."""
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

    exits = {
        "close": close_ret.copy(),
        "tp10": np.where(high_ret >= 10, 10.0, close_ret),
        "tp7": np.where(high_ret >= 7, 7.0, close_ret),
        "sl5_tp10": np.where((high_ret >= 10) & ~(low_ret <= -5), 10.0,
                             np.where(low_ret <= -5, -5.0, close_ret)),
    }

    def s(col):
        return df[col].fillna(0).to_numpy(dtype=np.float64) if col in df.columns else np.zeros(n)

    t_arr, c_arr, vz, az_arr, rsi6 = s("turnover"), s("close"), s("volume_z_20"), s("amount_z_20"), s("rsi_6")
    filter_dict = {
        "none": np.ones(n, dtype=bool),
        "vz>=0": vz >= 0,
        "t>=5|vz>=0": (t_arr >= 5) & (vz >= 0),
        "t5_20|c5_60": (t_arr >= 5) & (t_arr <= 20) & (c_arr >= 5) & (c_arr <= 60),
        "t>=5": t_arr >= 5,
        "t>=3|vz>=0": (t_arr >= 3) & (vz >= 0),
    }

    def compute_sort_key(recipe):
        p = probs.astype(np.float64)
        if recipe == "score_then_rsi6_low":
            return p * 1000 - rsi6
        if recipe == "volume_z_high":
            return vz * 1000 + p
        if recipe == "amount_z_high":
            return az_arr * 1000 + p
        if recipe == "prob_desc":
            return p
        return p

    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"].to_numpy(), sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    n_days = len(day_values)
    day_months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()

    candidates = [
        ("A: 0.73/1/vz>=0/rsi6/tp10", 0.73, 1, "vz>=0", "score_then_rsi6_low", "tp10"),
        ("B: 0.74/1/vz>=0/rsi6/tp10", 0.74, 1, "vz>=0", "score_then_rsi6_low", "tp10"),
        ("C: 0.69/1/t>=5/rsi6/tp10", 0.69, 1, "t>=5", "score_then_rsi6_low", "tp10"),
        ("D: 0.71/2/t5c5/vol_z/tp10", 0.71, 2, "t5_20|c5_60", "volume_z_high", "tp10"),
        ("E: 0.70/3/t5c5/prob/tp10", 0.70, 3, "t5_20|c5_60", "prob_desc", "tp10"),
        ("F: 0.69/2/t>=5|vz/rsi6/tp10", 0.69, 2, "t>=5|vz>=0", "score_then_rsi6_low", "tp10"),
        ("G: 0.71/3/t5c5/amt_z/tp10", 0.71, 3, "t5_20|c5_60", "amount_z_high", "tp10"),
        ("H: 0.73/2/vz>=0/rsi6/tp10", 0.73, 2, "vz>=0", "score_then_rsi6_low", "tp10"),
        ("I: 0.67/1/t>=5/rsi6/tp10", 0.67, 1, "t>=5", "score_then_rsi6_low", "tp10"),
        ("J: 0.60/1/t5c5/rsi6/sl5tp10", 0.60, 1, "t5_20|c5_60", "score_then_rsi6_low", "sl5_tp10"),
    ]

    print(f"\nEvaluating {len(candidates)} strategies...\n")

    # Build monthly table
    all_monthly = {}
    for name, thr, tn, fname, recipe, exit_mode in candidates:
        pool = (probs >= thr) & filter_dict[fname]
        sk = compute_sort_key(recipe)
        dsel = np.full((n_days, tn), -1, dtype=np.int32)
        for di, didx in enumerate(day_indices):
            idx = didx[pool[didx]]
            if idx.size == 0:
                continue
            idx = idx[np.argsort(-sk[idx])[:tn]]
            dsel[di, :idx.size] = idx

        valid = dsel >= 0
        counts = valid.sum(axis=1)
        dv = counts > 0
        safe = np.where(valid, dsel, 0)
        realized = exits[exit_mode][safe]
        realized = np.where(valid, realized, 0.0)
        dsum = realized.sum(axis=1)
        davg = np.zeros(n_days)
        davg[dv] = dsum[dv] / counts[dv]

        monthly = {}
        for month in sorted(set(day_months)):
            midx = np.where(day_months == month)[0]
            mdv = dv[midx]
            if not mdv.any():
                continue
            mdr = davg[midx][mdv]
            monthly[month] = pct_prod(mdr)
        all_monthly[name] = monthly

    # Print comparison table - OOS months only
    oos_months = sorted([m for m in sorted(set(day_months)) if m >= "2025-07"])
    pre_months = sorted([m for m in sorted(set(day_months)) if m < "2023-05"])

    print("=" * 140)
    print("OOS MONTHLY RETURNS (2025-07 ~ 2026-05)")
    print("=" * 140)
    header = f"{'Strategy':<30}"
    for m in oos_months:
        header += f" {m[5:]:<6}"
    header += f" {'AVG':<6} {'WORST':<7} {'M+':<3}"
    print(header)
    print("-" * 140)

    for name, _, _, _, _, _ in candidates:
        monthly = all_monthly[name]
        row = f"{name:<30}"
        oos_rets = []
        for m in oos_months:
            ret = monthly.get(m, 0)
            oos_rets.append(ret)
            marker = "*" if ret < -5 else " "
            row += f" {ret:>5.1f}{marker}"
        avg_oos = np.mean(oos_rets) if oos_rets else 0
        worst = min(oos_rets) if oos_rets else 0
        mpos = sum(1 for r in oos_rets if r > 0)
        row += f" {avg_oos:>5.1f} {worst:>6.1f} {mpos}/{len(oos_rets)}"
        print(row)

    print()
    print("=" * 140)
    print("PRE-TRAINING MONTHLY RETURNS (2023-01 ~ 2023-04)")
    print("=" * 140)
    header = f"{'Strategy':<30}"
    for m in pre_months:
        header += f" {m[5:]:<6}"
    header += f" {'TOTAL':<7}"
    print(header)
    print("-" * 140)

    for name, _, _, _, _, _ in candidates:
        monthly = all_monthly[name]
        row = f"{name:<30}"
        pre_rets = []
        for m in pre_months:
            ret = monthly.get(m, 0)
            pre_rets.append(ret)
            row += f" {ret:>5.1f} "
        total_pre = pct_prod(np.array(pre_rets))
        row += f" {total_pre:>5.1f}%"
        print(row)

    # Composite scoring
    print()
    print("=" * 140)
    print("COMPOSITE RANKING: Apr + Avg_OOS*2 - penalty_for_bad_months")
    print("=" * 140)
    scores = []
    for name, _, _, _, _, _ in candidates:
        monthly = all_monthly[name]
        apr = monthly.get("2026-04", 0)
        oos_rets = [monthly.get(m, 0) for m in oos_months]
        pre_rets = [monthly.get(m, 0) for m in pre_months]
        avg_oos = np.mean(oos_rets)
        worst_oos = min(oos_rets)
        worst_pre = min(pre_rets) if pre_rets else 0
        oos_neg5 = sum(1 for r in oos_rets if r < -5)
        pre_neg10 = sum(1 for r in pre_rets if r < -10)
        # Score: reward high April + high average, penalize deep drawdowns
        score = apr * 1.5 + avg_oos * 3 - oos_neg5 * 8 - pre_neg10 * 15 + min(worst_oos + 5, 0) * 2
        scores.append((name, apr, avg_oos, worst_oos, oos_neg5, worst_pre, score))

    scores.sort(key=lambda x: x[6], reverse=True)
    print(f"{'#':<3} {'Strategy':<30} {'Apr%':<7} {'AvgOOS':<7} {'WorstOOS':<9} "
          f"{'OOS<-5%':<8} {'WPre':<7} {'Score':<7}")
    for i, (name, apr, avg_oos, worst_oos, neg5, wpre, score) in enumerate(scores, 1):
        print(f"{i:<3} {name:<30} {apr:>5.1f}% {avg_oos:>5.1f}% {worst_oos:>7.1f}% "
              f"{neg5:>5} {wpre:>5.1f}% {score:>6.1f}")


if __name__ == "__main__":
    main()
