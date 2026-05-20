"""Validate strategies on pre-training data (2023-01 to 2023-04)."""
import sys, time, math
import numpy as np
import pandas as pd
import torch, pickle
from pathlib import Path
import pyarrow.parquet as pq

PC_BUNDLE = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt")
CACHE_JAN = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\jan_2023_patched.parquet")
CACHE_PRETRAIN = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\pretrain_2023_02_04_patched.parquet")

META_COLS = {"symbol", "date", "label_date", "actual", "close",
             "next_close_return_pct", "next_high_return_pct", "next_low_return_pct",
             "limit_up_like", "short_phase_days_3"}
STRATEGY_COLS = {"turnover", "turnover_z_20", "amount_z_20", "volume_z_20",
                 "range_pct", "rsi_6", "rsi_14", "close_position"}


def pct_prod(arr):
    if arr.size == 0:
        return 0.0
    v = np.clip(arr / 100.0, -0.95, 10.0)
    return float((np.prod(1.0 + v) - 1.0) * 100.0)


def sharpe_ratio(arr):
    if arr.size < 3:
        return None
    std = float(arr.std(ddof=1))
    if std == 0:
        return None
    return float(arr.mean() / std * math.sqrt(252))


def main():
    payload = torch.load(str(PC_BUNDLE), map_location="cpu", weights_only=False)
    members = [pickle.loads(m["model_bytes"]) for m in payload["members"]]
    feature_names = list(payload["feature_names"])
    mean = payload["mean"]
    std_val = payload["std"].clone()
    std_val[std_val == 0] = 1.0
    selected_indices = payload["selected_indices"]

    needed = META_COLS | STRATEGY_COLS | set(feature_names)

    # Load Jan 2023
    print("Loading Jan 2023...")
    schema1 = set(pq.read_schema(str(CACHE_JAN)).names)
    cols1 = [c for c in sorted(needed) if c in schema1]
    df1 = pd.read_parquet(str(CACHE_JAN), columns=cols1)
    df1 = df1[(df1["date"] >= "2023-01-01") & (df1["date"] <= "2023-01-31")].copy()
    print(f"  Jan: {len(df1):,} rows, {df1['date'].nunique()} days")

    # Load Feb-Apr 2023
    print("Loading Feb-Apr 2023...")
    schema2 = set(pq.read_schema(str(CACHE_PRETRAIN)).names)
    cols2 = [c for c in sorted(needed) if c in schema2]
    df2 = pd.read_parquet(str(CACHE_PRETRAIN), columns=cols2)
    df2 = df2[(df2["date"] >= "2023-02-01") & (df2["date"] <= "2023-04-30")].copy()
    print(f"  Feb-Apr: {len(df2):,} rows, {df2['date'].nunique()} days")

    # Combine
    df = pd.concat([df1, df2], ignore_index=True)
    if "limit_up_like" in df.columns:
        df = df[df["limit_up_like"] != 1].copy()
    if "short_phase_days_3" in df.columns:
        df = df[df["short_phase_days_3"] >= 1].copy()
    df = df.reset_index(drop=True)
    n = len(df)
    print(f"Combined: {n:,} rows, {df['date'].nunique()} days")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")

    # Score
    print("Scoring...")
    raw_features = np.zeros((n, len(feature_names)), dtype=np.float32)
    for i, name in enumerate(feature_names):
        if name in df.columns:
            raw_features[:, i] = df[name].fillna(0).to_numpy(dtype=np.float32)
    x = torch.as_tensor(raw_features, dtype=torch.float32)
    x = (x - mean) / std_val
    if selected_indices is not None:
        x = x[:, selected_indices]
    x_np = x.numpy()
    member_probs = [m.predict_proba(x_np)[:, 1].astype(np.float32) for m in members]
    raw_prob = np.stack(member_probs, axis=0).mean(axis=0).astype(np.float32)
    df["raw_prob"] = raw_prob
    print(f"  raw_prob range: {raw_prob.min():.4f} ~ {raw_prob.max():.4f}")

    # Exits
    close_ret = df["next_close_return_pct"].fillna(0).to_numpy(dtype=np.float64)
    high_ret = df["next_high_return_pct"].to_numpy(dtype=np.float64)
    low_ret = df["next_low_return_pct"].to_numpy(dtype=np.float64)
    high_ret = np.where(np.isnan(high_ret), close_ret, high_ret)
    low_ret = np.where(np.isnan(low_ret), close_ret, low_ret)

    EXIT_MODES = [
        ("close", None, None), ("tp10", None, 10.0), ("sl5_tp10", -5.0, 10.0),
        ("tp7", None, 7.0), ("tp5", None, 5.0), ("sl3_tp10", -3.0, 10.0),
    ]
    exits = {}
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

    # Filters
    def s(col):
        return df[col].fillna(0).to_numpy(dtype=np.float64) if col in df.columns else np.zeros(n)

    t_arr, c_arr = s("turnover"), s("close")
    vz = s("volume_z_20")

    filter_dict = {
        "none": np.ones(n, dtype=bool),
        "vz>=0": vz >= 0,
        "t5_20|c5_60": (t_arr >= 5) & (t_arr <= 20) & (c_arr >= 5) & (c_arr <= 60),
        "t>=5": t_arr >= 5,
    }

    def compute_sort_key(recipe):
        prob = df["raw_prob"].to_numpy(dtype=np.float64)
        if recipe == "prob_desc":
            return prob
        elif recipe == "score_then_rsi6_low":
            return prob * 1000 - s("rsi_6")
        elif recipe == "amount_z_high":
            return s("amount_z_20") * 1000 + prob
        elif recipe == "volume_z_high":
            return s("volume_z_20") * 1000 + prob
        return prob

    actual_arr = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"].to_numpy(), sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    n_days = len(day_values)
    day_months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()

    strategies = [
        ("OOS Best: raw>=0.67 top1 t5_20|c5_60 score_then_rsi6_low tp10",
         0.67, 1, "t5_20|c5_60", "score_then_rsi6_low", "tp10"),
        ("OOS Best close: raw>=0.67 top1 t5_20|c5_60 score_then_rsi6_low close",
         0.67, 1, "t5_20|c5_60", "score_then_rsi6_low", "close"),
        ("OOS #2: raw>=0.67 top1 t5_20|c5_60 score_then_rsi6_low sl5_tp10",
         0.67, 1, "t5_20|c5_60", "score_then_rsi6_low", "sl5_tp10"),
        ("Codex Best: raw>=0.73 top1 vz>=0 score_then_rsi6_low tp10",
         0.73, 1, "vz>=0", "score_then_rsi6_low", "tp10"),
        ("Codex S2: raw>=0.69 top1 t>=5 score_then_rsi6_low tp10",
         0.69, 1, "t>=5", "score_then_rsi6_low", "tp10"),
        ("Lower thr: raw>=0.65 top1 t5_20|c5_60 score_then_rsi6_low tp10",
         0.65, 1, "t5_20|c5_60", "score_then_rsi6_low", "tp10"),
    ]

    print(f"\n{'='*90}")
    print("STRATEGY VALIDATION ON PRE-TRAINING DATA (2023-01 to 2023-04)")
    print(f"{'='*90}")

    for name, threshold, top_n, filter_name, recipe, exit_mode in strategies:
        pool_mask = (raw_prob >= threshold) & filter_dict[filter_name]
        sort_key = compute_sort_key(recipe)

        day_sel = np.full((n_days, top_n), -1, dtype=np.int32)
        for day_no, day_idx in enumerate(day_indices):
            idx = day_idx[pool_mask[day_idx]]
            if idx.size == 0:
                continue
            idx = idx[np.argsort(-sort_key[idx], kind="mergesort")][:top_n]
            day_sel[day_no, :idx.size] = idx

        valid = day_sel >= 0
        counts = valid.sum(axis=1)
        day_valid = counts > 0
        signal_days = int(day_valid.sum())
        tickets = int(counts.sum())

        if tickets == 0:
            print(f"\n{name}")
            print("  NO SIGNALS")
            continue

        safe_idx = np.where(valid, day_sel, 0)
        realized = exits[exit_mode][safe_idx]
        realized = np.where(valid, realized, 0.0)
        actual_v = actual_arr[safe_idx]
        actual_v = np.where(valid, actual_v, 0.0)

        daily_sum = realized.sum(axis=1)
        daily_avg = np.zeros(n_days, dtype=np.float64)
        daily_avg[day_valid] = daily_sum[day_valid] / counts[day_valid]
        daily_returns = daily_avg[day_valid]

        total_return = pct_prod(daily_returns)
        sh = sharpe_ratio(daily_returns)
        dwr = float((daily_returns > 0).mean())
        twr = float(((realized > 0) & valid).sum() / tickets)
        h1 = float(actual_v.sum() / tickets)

        print(f"\n{name}")
        print(f"  Return: {total_return:.1f}% | Sharpe: {sh or 0:.2f} | "
              f"DailyWin: {dwr:.1%} | TicketWin: {twr:.1%} | High+1: {h1:.1%}")
        print(f"  Days: {signal_days} | Tickets: {tickets} | MaxLoss: {float(daily_returns.min()):.2f}%")

        unique_months = sorted(set(day_months))
        print(f"  {'Month':<8} {'Days':<5} {'Tix':<5} {'Return%':<10} {'DWin':<7} {'TWin':<7} {'H+1':<6}")
        for month in unique_months:
            m_days_idx = np.where(day_months == month)[0]
            m_sel = day_sel[m_days_idx]
            m_valid = m_sel >= 0
            m_tickets = int(m_valid.sum())
            if m_tickets == 0:
                continue
            m_safe = np.where(m_valid, m_sel, 0)
            m_realized = exits[exit_mode][m_safe]
            m_realized = np.where(m_valid, m_realized, 0.0)
            m_actual_v = actual_arr[m_safe]
            m_actual_v = np.where(m_valid, m_actual_v, 0.0)
            m_counts = m_valid.sum(axis=1)
            m_day_valid = m_counts > 0
            m_daily_sum = m_realized.sum(axis=1)
            m_daily_avg = np.zeros(len(m_days_idx), dtype=np.float64)
            m_daily_avg[m_day_valid] = m_daily_sum[m_day_valid] / m_counts[m_day_valid]
            m_daily_ret = m_daily_avg[m_day_valid]
            m_ret = pct_prod(m_daily_ret)
            m_dwin = float((m_daily_ret > 0).mean()) if m_daily_ret.size > 0 else 0
            m_twin = float(((m_realized > 0) & m_valid).sum() / m_tickets)
            m_h1 = float(m_actual_v.sum() / m_tickets)
            print(f"  {month:<8} {int(m_day_valid.sum()):<5} {m_tickets:<5} "
                  f"{m_ret:>8.2f}% {m_dwin:>6.1%} {m_twin:>6.1%} {m_h1:>5.1%}")


if __name__ == "__main__":
    main()
