"""Hit rate analysis at different probability thresholds for S2 vs PhaseC."""
import numpy as np, pandas as pd, torch, pickle
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


def main():
    # Load S2 and PC feature sets
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

    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    dates = df["date"].to_numpy()
    day_dates = pd.to_datetime(pd.Series(dates))
    date_str = day_dates.dt.strftime("%Y-%m-%d").to_numpy()

    pre_mask = date_str < "2023-05-01"
    train_mask = (date_str >= "2023-05-01") & (date_str < "2025-07-01")
    oos_mask = date_str >= "2025-07-01"

    print(f"Data: {n:,} rows")
    print(f"  Pretrain: {pre_mask.sum():,} | Train: {train_mask.sum():,} | OOS: {oos_mask.sum():,}")

    # Score both models
    print("\nScoring S2...")
    s2_probs = load_and_score(S2_BUNDLE, df, n)
    print("Scoring PhaseC...")
    pc_probs = load_and_score(PC_BUNDLE, df, n)

    # Thresholds to check
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.72, 0.73, 0.75, 0.77, 0.80, 0.85, 0.90]

    print(f"\n{'='*130}")
    print("HIGH+1 HIT RATE BY THRESHOLD (actual=1 means next-day high >= close*1.01)")
    print(f"{'='*130}")

    header = (f"{'Thr':<6} | {'--- S2 ---':<45} | {'--- PhaseC ---':<45}")
    print(header)
    sub = (f"{'':6} | {'All':>8} {'Pre':>8} {'Train':>8} {'OOS':>8} {'#All':>7} | "
           f"{'All':>8} {'Pre':>8} {'Train':>8} {'OOS':>8} {'#All':>7}")
    print(sub)
    print("-" * 130)

    for thr in thresholds:
        # S2
        s2_sel = s2_probs >= thr
        s2_n = int(s2_sel.sum())
        s2_hit_all = float(actual[s2_sel].mean()) * 100 if s2_n > 0 else 0
        s2_hit_pre = float(actual[s2_sel & pre_mask].mean()) * 100 if (s2_sel & pre_mask).any() else 0
        s2_hit_trn = float(actual[s2_sel & train_mask].mean()) * 100 if (s2_sel & train_mask).any() else 0
        s2_hit_oos = float(actual[s2_sel & oos_mask].mean()) * 100 if (s2_sel & oos_mask).any() else 0
        s2_n_pre = int((s2_sel & pre_mask).sum())
        s2_n_trn = int((s2_sel & train_mask).sum())
        s2_n_oos = int((s2_sel & oos_mask).sum())

        # PhaseC
        pc_sel = pc_probs >= thr
        pc_n = int(pc_sel.sum())
        pc_hit_all = float(actual[pc_sel].mean()) * 100 if pc_n > 0 else 0
        pc_hit_pre = float(actual[pc_sel & pre_mask].mean()) * 100 if (pc_sel & pre_mask).any() else 0
        pc_hit_trn = float(actual[pc_sel & train_mask].mean()) * 100 if (pc_sel & train_mask).any() else 0
        pc_hit_oos = float(actual[pc_sel & oos_mask].mean()) * 100 if (pc_sel & oos_mask).any() else 0
        pc_n_pre = int((pc_sel & pre_mask).sum())
        pc_n_trn = int((pc_sel & train_mask).sum())
        pc_n_oos = int((pc_sel & oos_mask).sum())

        print(f">={thr:<4} | {s2_hit_all:>6.1f}% {s2_hit_pre:>6.1f}% {s2_hit_trn:>6.1f}% {s2_hit_oos:>6.1f}% {s2_n:>6} | "
              f"{pc_hit_all:>6.1f}% {pc_hit_pre:>6.1f}% {pc_hit_trn:>6.1f}% {pc_hit_oos:>6.1f}% {pc_n:>6}")

    # Per-threshold sample counts
    print(f"\n{'='*130}")
    print("SAMPLE COUNTS BY THRESHOLD AND PERIOD")
    print(f"{'='*130}")
    header2 = (f"{'Thr':<6} | {'--- S2 Count ---':<30} | {'--- PhaseC Count ---':<30}")
    print(header2)
    sub2 = (f"{'':6} | {'Pre':>7} {'Train':>7} {'OOS':>7} {'Total':>7} | "
            f"{'Pre':>7} {'Train':>7} {'OOS':>7} {'Total':>7}")
    print(sub2)
    print("-" * 130)
    for thr in thresholds:
        s2_sel = s2_probs >= thr
        pc_sel = pc_probs >= thr
        print(f">={thr:<4} | {int((s2_sel & pre_mask).sum()):>7} {int((s2_sel & train_mask).sum()):>7} "
              f"{int((s2_sel & oos_mask).sum()):>7} {int(s2_sel.sum()):>7} | "
              f"{int((pc_sel & pre_mask).sum()):>7} {int((pc_sel & train_mask).sum()):>7} "
              f"{int((pc_sel & oos_mask).sum()):>7} {int(pc_sel.sum()):>7}")

    # Monthly hit rate at the strategy thresholds
    print(f"\n{'='*130}")
    print("MONTHLY HIT RATE: S2 (>=0.72) vs PhaseC (>=0.73)")
    print(f"{'='*130}")
    months_col = pd.to_datetime(pd.Series(dates)).dt.strftime("%Y-%m").to_numpy()
    all_months = sorted(set(months_col))

    s2_sel = s2_probs >= 0.72
    pc_sel = pc_probs >= 0.73

    print(f"{'Month':<8} | {'S2 Hit%':>8} {'S2 #':>5} | {'PC Hit%':>8} {'PC #':>5} | Period")
    print("-" * 70)
    for m in all_months:
        mmask = months_col == m
        s2m = s2_sel & mmask
        pcm = pc_sel & mmask
        s2_hit = float(actual[s2m].mean()) * 100 if s2m.any() else 0
        pc_hit = float(actual[pcm].mean()) * 100 if pcm.any() else 0
        s2_cnt = int(s2m.sum())
        pc_cnt = int(pcm.sum())
        period = "PRE" if m < "2023-05" else ("TRAIN" if m < "2025-07" else "OOS")
        print(f"  {m:<7} | {s2_hit:>6.1f}% {s2_cnt:>5} | {pc_hit:>6.1f}% {pc_cnt:>5} | {period}")

    # Wilson lower bound at key thresholds
    print(f"\n{'='*130}")
    print("WILSON 95% LOWER BOUND BY THRESHOLD")
    print(f"{'='*130}")
    import math
    z = 1.96
    def wilson_lower(hits, total):
        if total == 0:
            return 0.0
        p = hits / total
        denom = 1 + z*z/total
        center = p + z*z/(2*total)
        spread = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total))
        return (center - spread) / denom

    print(f"{'Thr':<6} | {'S2 Wilson95':<15} {'S2 Hit%':<10} {'S2 N':<8} | {'PC Wilson95':<15} {'PC Hit%':<10} {'PC N':<8}")
    print("-" * 90)
    for thr in thresholds:
        s2_sel = s2_probs >= thr
        pc_sel = pc_probs >= thr
        s2_hits = int(actual[s2_sel].sum())
        s2_total = int(s2_sel.sum())
        pc_hits = int(actual[pc_sel].sum())
        pc_total = int(pc_sel.sum())
        s2_wl = wilson_lower(s2_hits, s2_total) * 100
        pc_wl = wilson_lower(pc_hits, pc_total) * 100
        s2_hr = s2_hits / s2_total * 100 if s2_total > 0 else 0
        pc_hr = pc_hits / pc_total * 100 if pc_total > 0 else 0
        print(f">={thr:<4} | {s2_wl:>10.1f}%     {s2_hr:>6.1f}%    {s2_total:<8} | "
              f"{pc_wl:>10.1f}%     {pc_hr:>6.1f}%    {pc_total:<8}")


if __name__ == "__main__":
    main()
