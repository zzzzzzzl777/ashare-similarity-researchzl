"""OOS-only strategy search for PhaseC model.

Searches over thresholds, topN, filters, rank recipes, and exit modes
on pure out-of-sample data (2025-07 to 2026-04).
"""
import sys, time, math
import numpy as np
import pandas as pd
import torch, pickle
from pathlib import Path
import pyarrow.parquet as pq

PC_BUNDLE = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt")
CACHE = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_31ffa0367a4d893f.parquet")

META_COLS = {"symbol", "date", "label_date", "actual", "close",
             "next_close_return_pct", "next_high_return_pct", "next_low_return_pct",
             "limit_up_like", "short_phase_days_3"}
STRATEGY_COLS = {"turnover", "turnover_z_20", "amount_z_20", "volume_z_20",
                 "range_pct", "rsi_6", "rsi_14", "close_position",
                 "upper_shadow_pct", "lower_shadow_pct", "body_pct",
                 "cs_turnover_rank", "cs_amount_z_rank", "cs_volume_z_rank", "cs_range_rank"}

EXIT_MODES = [
    ("close", None, None),
    ("tp3", None, 3.0), ("tp5", None, 5.0), ("tp7", None, 7.0), ("tp10", None, 10.0),
    ("sl2", -2.0, None), ("sl3", -3.0, None), ("sl5", -5.0, None),
    ("sl2_tp5", -2.0, 5.0), ("sl2_tp7", -2.0, 7.0), ("sl3_tp7", -3.0, 7.0),
    ("sl3_tp10", -3.0, 10.0), ("sl5_tp10", -5.0, 10.0),
]

RANK_RECIPES = ["prob_desc", "score_then_rsi6_low", "amount_z_high", "volume_z_high",
                "activity_z_high", "rsi6_low"]

FILTERS_SPEC = [
    ("none", None),
    ("vz>=0", "volume_z_20>=0"),
    ("az>=0", "amount_z_20>=0"),
    ("t>=5|vz>=0", "turnover>=5&volume_z_20>=0"),
    ("t>=5|az>=0", "turnover>=5&amount_z_20>=0"),
    ("close>=5", "close>=5"),
    ("t>=5", "turnover>=5"),
    ("t5_20|c5_60", "turnover>=5&turnover<=20&close>=5&close<=60"),
]


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
    # Load bundle
    payload = torch.load(str(PC_BUNDLE), map_location="cpu", weights_only=False)
    members = [pickle.loads(m["model_bytes"]) for m in payload["members"]]
    iso_model = pickle.loads(payload["iso_model_bytes"]) if payload.get("iso_model_bytes") else None
    feature_names = list(payload["feature_names"])
    mean = payload["mean"]
    std_val = payload["std"].clone()
    std_val[std_val == 0] = 1.0
    selected_indices = payload["selected_indices"]
    print(f"PhaseC: {len(feature_names)} features, {len(selected_indices)} selected")

    # Load OOS data
    schema_cols = set(pq.read_schema(str(CACHE)).names)
    needed = META_COLS | STRATEGY_COLS | set(feature_names)
    cols = [c for c in sorted(needed) if c in schema_cols]

    print("Loading OOS data (2025-07 to 2026-04)...")
    t0 = time.time()
    df = pd.read_parquet(str(CACHE), columns=cols)
    df = df[(df["date"] >= "2025-07-01") & (df["date"] <= "2026-04-30")].copy()
    if "limit_up_like" in df.columns:
        df = df[df["limit_up_like"] != 1].copy()
    if "short_phase_days_3" in df.columns:
        df = df[df["short_phase_days_3"] >= 1].copy()
    df["month"] = df["date"].astype(str).str.slice(0, 7)
    df = df.reset_index(drop=True)
    n = len(df)
    print(f"Loaded: {n:,} rows, {df['date'].nunique()} days in {time.time()-t0:.1f}s")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")

    # Score
    print("Scoring...")
    t0 = time.time()
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
    print(f"Scored in {time.time()-t0:.1f}s")

    # Compute exits
    print("Computing exits...")
    close_ret = df["next_close_return_pct"].fillna(0).to_numpy(dtype=np.float64)
    high_ret = df["next_high_return_pct"].to_numpy(dtype=np.float64)
    low_ret = df["next_low_return_pct"].to_numpy(dtype=np.float64)
    high_ret = np.where(np.isnan(high_ret), close_ret, high_ret)
    low_ret = np.where(np.isnan(low_ret), close_ret, low_ret)

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

    # Build filters
    def s(col):
        return df[col].fillna(0).to_numpy(dtype=np.float64) if col in df.columns else np.zeros(n)

    t_arr, c_arr = s("turnover"), s("close")
    vz, az_arr = s("volume_z_20"), s("amount_z_20")

    filters = [
        ("none", np.ones(n, dtype=bool)),
        ("vz>=0", vz >= 0),
        ("az>=0", az_arr >= 0),
        ("t>=5|vz>=0", (t_arr >= 5) & (vz >= 0)),
        ("t>=5|az>=0", (t_arr >= 5) & (az_arr >= 0)),
        ("close>=5", c_arr >= 5),
        ("t>=5", t_arr >= 5),
        ("t5_20|c5_60", (t_arr >= 5) & (t_arr <= 20) & (c_arr >= 5) & (c_arr <= 60)),
    ]
    filter_dict = dict(filters)

    # Sort keys
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
        elif recipe == "activity_z_high":
            return s("range_pct") * s("turnover_z_20") * 1000 + prob
        elif recipe == "rsi6_low":
            return -s("rsi_6") * 1000 + prob
        return prob

    # Day structure
    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"].to_numpy(), sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    n_days = len(day_values)

    thresholds = [round(x / 100.0, 2) for x in range(65, 82)]
    top_ns = [1, 2, 3, 4, 5, 6]

    print(f"\nSearch grid: {len(thresholds)} thresholds x {len(top_ns)} topN x "
          f"{len(filters)} filters x {len(RANK_RECIPES)} recipes x {len(EXIT_MODES)} exits")
    print(f"Total combos: {len(thresholds)*len(top_ns)*len(filters)*len(RANK_RECIPES)*len(EXIT_MODES):,}")

    results = []
    t0 = time.time()

    for recipe in RANK_RECIPES:
        sort_key = compute_sort_key(recipe)
        for filter_name, filter_mask in filters:
            for threshold in thresholds:
                pool_mask = (raw_prob >= threshold) & filter_mask
                if not pool_mask.any():
                    continue

                max_top = max(top_ns)
                day_sel = np.full((n_days, max_top), -1, dtype=np.int32)
                for day_no, day_idx in enumerate(day_indices):
                    idx = day_idx[pool_mask[day_idx]]
                    if idx.size == 0:
                        continue
                    idx = idx[np.argsort(-sort_key[idx], kind="mergesort")][:max_top]
                    day_sel[day_no, :idx.size] = idx

                for top_n in top_ns:
                    sel = day_sel[:, :top_n]
                    valid = sel >= 0
                    counts = valid.sum(axis=1)
                    day_valid = counts > 0
                    signal_days = int(day_valid.sum())
                    tickets = int(counts.sum())
                    if signal_days < 20 or tickets < 20:
                        continue

                    safe_idx = np.where(valid, sel, 0)
                    actual_values = actual[safe_idx]
                    actual_values = np.where(valid, actual_values, 0.0)
                    h1 = float(actual_values.sum() / tickets)

                    for exit_name, _, _ in EXIT_MODES:
                        realized = exits[exit_name][safe_idx]
                        realized = np.where(valid, realized, 0.0)
                        daily_sum = realized.sum(axis=1)
                        daily_avg = np.zeros(n_days, dtype=np.float64)
                        daily_avg[day_valid] = daily_sum[day_valid] / counts[day_valid]
                        daily_returns = daily_avg[day_valid]

                        total_return = pct_prod(daily_returns)
                        sh = sharpe_ratio(daily_returns)
                        dwr = float((daily_returns > 0).mean())
                        twr = float(((realized > 0) & valid).sum() / tickets)

                        results.append({
                            "threshold": threshold, "top_n": top_n,
                            "filter": filter_name, "recipe": recipe, "exit": exit_name,
                            "signal_days": signal_days, "tickets": tickets,
                            "total_return": total_return, "sharpe": sh,
                            "daily_win": dwr, "ticket_win": twr, "high1": h1,
                            "avg_daily_pct": float(daily_returns.mean()),
                            "max_loss": float(daily_returns.min()),
                        })

    elapsed = time.time() - t0
    print(f"Done: {len(results):,} valid strategies in {elapsed:.0f}s")

    # Sort and display
    by_return = sorted(results, key=lambda r: r["total_return"], reverse=True)
    by_sharpe = sorted(results, key=lambda r: r["sharpe"] or 0, reverse=True)

    print(f"\n{'='*90}")
    print(f"TOP 25 BY TOTAL RETURN (OOS: 2025-07 to 2026-04)")
    print(f"{'='*90}")
    hdr = f"{'#':<3} {'Thr':<6} {'N':<3} {'Filter':<14} {'Recipe':<22} {'Exit':<10} {'Ret%':<9} {'Shrp':<6} {'DWin':<6} {'H1':<6} {'Days':<4} {'Loss':<7}"
    print(hdr)
    for i, r in enumerate(by_return[:25], 1):
        print(f"{i:<3} {r['threshold']:<6} {r['top_n']:<3} {r['filter']:<14} {r['recipe']:<22} {r['exit']:<10} "
              f"{r['total_return']:>7.1f}% {r['sharpe'] or 0:>5.2f} {r['daily_win']:>5.1%} {r['high1']:>5.1%} {r['signal_days']:<4} {r['max_loss']:>6.2f}%")

    print(f"\n{'='*90}")
    print(f"TOP 20 BY SHARPE (min 50 days active)")
    print(f"{'='*90}")
    sf = [r for r in by_sharpe if r["signal_days"] >= 50]
    print(hdr)
    for i, r in enumerate(sf[:20], 1):
        print(f"{i:<3} {r['threshold']:<6} {r['top_n']:<3} {r['filter']:<14} {r['recipe']:<22} {r['exit']:<10} "
              f"{r['total_return']:>7.1f}% {r['sharpe'] or 0:>5.2f} {r['daily_win']:>5.1%} {r['high1']:>5.1%} {r['signal_days']:<4} {r['max_loss']:>6.2f}%")

    print(f"\n{'='*90}")
    print(f"TOP 15 with tp10 (Codex best exit)")
    print(f"{'='*90}")
    tp10 = [r for r in by_return if r["exit"] == "tp10"]
    print(hdr)
    for i, r in enumerate(tp10[:15], 1):
        print(f"{i:<3} {r['threshold']:<6} {r['top_n']:<3} {r['filter']:<14} {r['recipe']:<22} {r['exit']:<10} "
              f"{r['total_return']:>7.1f}% {r['sharpe'] or 0:>5.2f} {r['daily_win']:>5.1%} {r['high1']:>5.1%} {r['signal_days']:<4} {r['max_loss']:>6.2f}%")

    # Monthly breakdown of overall best
    best = by_return[0]
    print(f"\n{'='*90}")
    print(f"BEST STRATEGY MONTHLY BREAKDOWN")
    print(f"{'='*90}")
    print(f"raw_prob >= {best['threshold']}, top{best['top_n']}, filter={best['filter']}, "
          f"recipe={best['recipe']}, exit={best['exit']}")
    print(f"Return {best['total_return']:.1f}%, Sharpe {best['sharpe'] or 0:.2f}, "
          f"DailyWin {best['daily_win']:.1%}, High+1 {best['high1']:.1%}, Days {best['signal_days']}")

    pool_mask = (raw_prob >= best["threshold"]) & filter_dict[best["filter"]]
    sort_key = compute_sort_key(best["recipe"])
    day_sel = np.full((n_days, best["top_n"]), -1, dtype=np.int32)
    for day_no, day_idx in enumerate(day_indices):
        idx = day_idx[pool_mask[day_idx]]
        if idx.size == 0:
            continue
        idx = idx[np.argsort(-sort_key[idx], kind="mergesort")][:best["top_n"]]
        day_sel[day_no, :idx.size] = idx

    day_months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()
    unique_months = sorted(set(day_months))

    print(f"\n{'Month':<8} {'Days':<5} {'Tix':<5} {'Return%':<10} {'DWin':<7} {'TWin':<7} {'H+1':<6}")
    for month in unique_months:
        m_days_idx = np.where(day_months == month)[0]
        m_sel = day_sel[m_days_idx]
        m_valid = m_sel >= 0
        m_tickets = int(m_valid.sum())
        if m_tickets == 0:
            continue
        m_safe = np.where(m_valid, m_sel, 0)
        m_realized = exits[best["exit"]][m_safe]
        m_realized = np.where(m_valid, m_realized, 0.0)
        m_actual_v = actual[m_safe]
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
        print(f"{month:<8} {int(m_day_valid.sum()):<5} {m_tickets:<5} {m_ret:>8.2f}% "
              f"{m_dwin:>6.1%} {m_twin:>6.1%} {m_h1:>5.1%}")

    # Also show Codex's best strategy on OOS
    print(f"\n{'='*90}")
    print(f"CODEX BEST (raw>=0.73, top1, vz>=0, score_then_rsi6_low, tp10) on OOS")
    print(f"{'='*90}")
    codex_match = [r for r in results if r["threshold"] == 0.73 and r["top_n"] == 1
                   and r["filter"] == "vz>=0" and r["recipe"] == "score_then_rsi6_low"
                   and r["exit"] == "tp10"]
    if codex_match:
        r = codex_match[0]
        print(f"Return {r['total_return']:.1f}%, Sharpe {r['sharpe'] or 0:.2f}, "
              f"DailyWin {r['daily_win']:.1%}, High+1 {r['high1']:.1%}, "
              f"Days {r['signal_days']}, MaxLoss {r['max_loss']:.2f}%")


if __name__ == "__main__":
    main()
