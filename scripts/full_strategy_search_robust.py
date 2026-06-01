"""Full-period strategy search on ALL available PhaseC-compatible data.

Uses:
- Jan 2023 patched cache (2023-01)
- Pretrain cache (2023-02 ~ 2023-04)
- Main cache (2023-06 ~ 2026-05)

Total ~780 days. Searches for strategies robust across ALL periods.
"""
import sys, time, math
import numpy as np
import pandas as pd
import torch, pickle
from pathlib import Path
import pyarrow.parquet as pq

PC_BUNDLE = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt")
CACHE_JAN = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\jan_2023_patched.parquet")
CACHE_PRETRAIN = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\pretrain_2023_02_04_patched.parquet")
CACHE_MAIN = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_31ffa0367a4d893f.parquet")

META_COLS = {"symbol", "date", "label_date", "actual", "close",
             "next_close_return_pct", "next_high_return_pct", "next_low_return_pct",
             "limit_up_like", "short_phase_days_3"}
STRATEGY_COLS = {"turnover", "turnover_z_20", "amount_z_20", "volume_z_20",
                 "range_pct", "rsi_6", "rsi_14", "close_position"}

EXIT_MODES = [
    ("close", None, None),
    ("tp3", None, 3.0), ("tp5", None, 5.0), ("tp7", None, 7.0), ("tp10", None, 10.0),
    ("sl2", -2.0, None), ("sl3", -3.0, None), ("sl5", -5.0, None),
    ("sl2_tp5", -2.0, 5.0), ("sl2_tp7", -2.0, 7.0),
    ("sl3_tp7", -3.0, 7.0), ("sl3_tp10", -3.0, 10.0), ("sl5_tp10", -5.0, 10.0),
]

RANK_RECIPES = ["prob_desc", "score_then_rsi6_low", "amount_z_high",
                "volume_z_high", "activity_z_high", "rsi6_low"]


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


def max_drawdown(daily_returns):
    if len(daily_returns) == 0:
        return 0.0
    cum = np.cumprod(1.0 + np.clip(daily_returns / 100.0, -0.95, 10.0))
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    return float(dd.min() * 100.0)


def main():
    # Load bundle
    payload = torch.load(str(PC_BUNDLE), map_location="cpu", weights_only=False)
    members = [pickle.loads(m["model_bytes"]) for m in payload["members"]]
    feature_names = list(payload["feature_names"])
    mean = payload["mean"]
    std_val = payload["std"].clone()
    std_val[std_val == 0] = 1.0
    selected_indices = payload["selected_indices"]
    print(f"PhaseC: {len(feature_names)} features, {len(selected_indices)} selected")

    needed = META_COLS | STRATEGY_COLS | set(feature_names)

    # Load all segments
    frames = []

    print("Loading Jan 2023...")
    schema1 = set(pq.read_schema(str(CACHE_JAN)).names)
    cols1 = [c for c in sorted(needed) if c in schema1]
    df1 = pd.read_parquet(str(CACHE_JAN), columns=cols1)
    df1 = df1[(df1["date"] >= "2023-01-01") & (df1["date"] <= "2023-01-31")].copy()
    frames.append(df1)
    print(f"  {len(df1):,} rows, {df1['date'].nunique()} days")

    print("Loading Feb-Apr 2023...")
    schema2 = set(pq.read_schema(str(CACHE_PRETRAIN)).names)
    cols2 = [c for c in sorted(needed) if c in schema2]
    df2 = pd.read_parquet(str(CACHE_PRETRAIN), columns=cols2)
    df2 = df2[(df2["date"] >= "2023-02-01") & (df2["date"] <= "2023-04-30")].copy()
    frames.append(df2)
    print(f"  {len(df2):,} rows, {df2['date'].nunique()} days")

    print("Loading Main cache (2023-06 ~ 2026-05)...")
    schema3 = set(pq.read_schema(str(CACHE_MAIN)).names)
    cols3 = [c for c in sorted(needed) if c in schema3]
    df3 = pd.read_parquet(str(CACHE_MAIN), columns=cols3)
    frames.append(df3)
    print(f"  {len(df3):,} rows, {df3['date'].nunique()} days")

    # Combine
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["date", "symbol"], keep="first").reset_index(drop=True)
    if "limit_up_like" in df.columns:
        df = df[df["limit_up_like"] != 1].copy()
    if "short_phase_days_3" in df.columns:
        df = df[df["short_phase_days_3"] >= 1].copy()
    df = df.reset_index(drop=True)
    n = len(df)
    print(f"\nCombined: {n:,} rows, {df['date'].nunique()} days")
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

    # Exits
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

    # Filters
    def s(col):
        return df[col].fillna(0).to_numpy(dtype=np.float64) if col in df.columns else np.zeros(n)

    t_arr, c_arr = s("turnover"), s("close")
    vz, az_arr = s("volume_z_20"), s("amount_z_20")
    rsi6 = s("rsi_6")

    filters = [
        ("none", np.ones(n, dtype=bool)),
        ("vz>=0", vz >= 0),
        ("az>=0", az_arr >= 0),
        ("t>=5|vz>=0", (t_arr >= 5) & (vz >= 0)),
        ("t>=5|az>=0", (t_arr >= 5) & (az_arr >= 0)),
        ("close>=5", c_arr >= 5),
        ("t>=5", t_arr >= 5),
        ("t5_20|c5_60", (t_arr >= 5) & (t_arr <= 20) & (c_arr >= 5) & (c_arr <= 60)),
        ("t>=3", t_arr >= 3),
        ("t3_20|c5_100", (t_arr >= 3) & (t_arr <= 20) & (c_arr >= 5) & (c_arr <= 100)),
    ]
    filter_dict = dict(filters)

    # Sort keys
    def compute_sort_key(recipe):
        prob = df["raw_prob"].to_numpy(dtype=np.float64)
        if recipe == "prob_desc":
            return prob
        elif recipe == "score_then_rsi6_low":
            return prob * 1000 - rsi6
        elif recipe == "amount_z_high":
            return az_arr * 1000 + prob
        elif recipe == "volume_z_high":
            return vz * 1000 + prob
        elif recipe == "activity_z_high":
            return s("range_pct") * s("turnover_z_20") * 1000 + prob
        elif recipe == "rsi6_low":
            return -rsi6 * 1000 + prob
        return prob

    # Day structure
    actual = df["actual"].fillna(0).to_numpy(dtype=np.float64)
    day_codes, day_values = pd.factorize(df["date"].to_numpy(), sort=True)
    day_indices = [np.where(day_codes == i)[0] for i in range(len(day_values))]
    n_days = len(day_values)
    day_months = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m").to_numpy()

    # Define time windows for robustness check
    day_dates_str = pd.to_datetime(pd.Series(day_values)).dt.strftime("%Y-%m-%d").to_numpy()
    pretrain_mask = day_dates_str < "2023-05-01"     # 2023-01 to 2023-04
    train_mask = (day_dates_str >= "2023-05-01") & (day_dates_str < "2025-07-01")  # training era
    oos_mask = day_dates_str >= "2025-07-01"         # OOS (dev_valid + seen_research)

    thresholds = [round(x / 100.0, 2) for x in range(65, 82)]
    top_ns = [1, 2, 3, 4, 5, 6]

    print(f"\nSearch grid: {len(thresholds)} thresholds x {len(top_ns)} topN x "
          f"{len(filters)} filters x {len(RANK_RECIPES)} recipes x {len(EXIT_MODES)} exits")
    total_grid = len(thresholds) * len(top_ns) * len(filters) * len(RANK_RECIPES) * len(EXIT_MODES)
    print(f"Total combos: {total_grid:,}")
    print(f"Days: pretrain={pretrain_mask.sum()}, train={train_mask.sum()}, oos={oos_mask.sum()}")

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
                    if signal_days < 30 or tickets < 30:
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

                        # Full period metrics
                        total_return = pct_prod(daily_returns)
                        sh = sharpe_ratio(daily_returns)
                        dwr = float((daily_returns > 0).mean())
                        twr = float(((realized > 0) & valid).sum() / tickets)
                        mdd = max_drawdown(daily_returns)

                        # Sub-period returns
                        pre_ret = pct_prod(daily_avg[pretrain_mask & day_valid])
                        train_ret = pct_prod(daily_avg[train_mask & day_valid])
                        oos_ret = pct_prod(daily_avg[oos_mask & day_valid])

                        pre_days = int((pretrain_mask & day_valid).sum())
                        oos_days = int((oos_mask & day_valid).sum())

                        # Monthly win rate
                        unique_months = sorted(set(day_months[day_valid]))
                        months_pos = 0
                        months_total = len(unique_months)
                        for m in unique_months:
                            m_mask = day_valid & (day_months == m)
                            if m_mask.any():
                                m_ret = pct_prod(daily_avg[m_mask])
                                if m_ret > 0:
                                    months_pos += 1

                        # Robustness: must be positive in both pretrain and OOS
                        robust = pre_ret > 0 and oos_ret > 0

                        results.append({
                            "threshold": threshold, "top_n": top_n,
                            "filter": filter_name, "recipe": recipe, "exit": exit_name,
                            "signal_days": signal_days, "tickets": tickets,
                            "total_return": total_return, "sharpe": sh,
                            "daily_win": dwr, "ticket_win": twr, "high1": h1,
                            "avg_daily_pct": float(daily_returns.mean()),
                            "max_loss": float(daily_returns.min()),
                            "max_dd": mdd,
                            "pre_ret": pre_ret, "train_ret": train_ret, "oos_ret": oos_ret,
                            "pre_days": pre_days, "oos_days": oos_days,
                            "months_pos": months_pos, "months_total": months_total,
                            "robust": robust,
                        })

        print(f"  {recipe} done, {len(results):,} strategies so far, {time.time()-t0:.0f}s", flush=True)

    elapsed = time.time() - t0
    print(f"\nDone: {len(results):,} valid strategies in {elapsed:.0f}s")

    # Filter robust strategies and sort
    robust_results = [r for r in results if r["robust"]]
    print(f"Robust (positive in both pretrain & OOS): {len(robust_results):,}")

    by_total = sorted(robust_results, key=lambda r: r["total_return"], reverse=True)
    by_sharpe = sorted(robust_results, key=lambda r: r["sharpe"] or 0, reverse=True)
    by_oos = sorted(robust_results, key=lambda r: r["oos_ret"], reverse=True)

    # Display
    hdr = (f"{'#':<3} {'Thr':<5} {'N':<2} {'Filter':<14} {'Recipe':<22} {'Exit':<10} "
           f"{'Total%':<8} {'Shrp':<5} {'DWin':<5} {'H1':<5} "
           f"{'Pre%':<8} {'OOS%':<8} {'MDD%':<7} {'M+/M':<5}")

    print(f"\n{'='*120}")
    print(f"TOP 30 ROBUST STRATEGIES BY TOTAL RETURN (must be + in pretrain AND OOS)")
    print(f"{'='*120}")
    print(hdr)
    for i, r in enumerate(by_total[:30], 1):
        print(f"{i:<3} {r['threshold']:<5} {r['top_n']:<2} {r['filter']:<14} {r['recipe']:<22} {r['exit']:<10} "
              f"{r['total_return']:>6.0f}% {r['sharpe'] or 0:>4.1f} {r['daily_win']:>4.0%} {r['high1']:>4.0%} "
              f"{r['pre_ret']:>6.1f}% {r['oos_ret']:>6.1f}% {r['max_dd']:>6.1f}% {r['months_pos']}/{r['months_total']}")

    print(f"\n{'='*120}")
    print(f"TOP 20 ROBUST BY SHARPE (min 100 days)")
    print(f"{'='*120}")
    sf = [r for r in by_sharpe if r["signal_days"] >= 100]
    print(hdr)
    for i, r in enumerate(sf[:20], 1):
        print(f"{i:<3} {r['threshold']:<5} {r['top_n']:<2} {r['filter']:<14} {r['recipe']:<22} {r['exit']:<10} "
              f"{r['total_return']:>6.0f}% {r['sharpe'] or 0:>4.1f} {r['daily_win']:>4.0%} {r['high1']:>4.0%} "
              f"{r['pre_ret']:>6.1f}% {r['oos_ret']:>6.1f}% {r['max_dd']:>6.1f}% {r['months_pos']}/{r['months_total']}")

    print(f"\n{'='*120}")
    print(f"TOP 20 ROBUST BY OOS RETURN")
    print(f"{'='*120}")
    print(hdr)
    for i, r in enumerate(by_oos[:20], 1):
        print(f"{i:<3} {r['threshold']:<5} {r['top_n']:<2} {r['filter']:<14} {r['recipe']:<22} {r['exit']:<10} "
              f"{r['total_return']:>6.0f}% {r['sharpe'] or 0:>4.1f} {r['daily_win']:>4.0%} {r['high1']:>4.0%} "
              f"{r['pre_ret']:>6.1f}% {r['oos_ret']:>6.1f}% {r['max_dd']:>6.1f}% {r['months_pos']}/{r['months_total']}")

    # Monthly breakdown for the best robust strategy
    if by_total:
        best = by_total[0]
        print(f"\n{'='*120}")
        print(f"BEST ROBUST STRATEGY MONTHLY BREAKDOWN")
        print(f"{'='*120}")
        print(f"raw_prob >= {best['threshold']}, top{best['top_n']}, filter={best['filter']}, "
              f"recipe={best['recipe']}, exit={best['exit']}")
        print(f"Total: {best['total_return']:.0f}% | Sharpe: {best['sharpe'] or 0:.2f} | "
              f"DWin: {best['daily_win']:.1%} | H+1: {best['high1']:.1%} | "
              f"Pre: {best['pre_ret']:.1f}% | OOS: {best['oos_ret']:.1f}%")

        pool_mask = (raw_prob >= best["threshold"]) & filter_dict[best["filter"]]
        sort_key = compute_sort_key(best["recipe"])
        day_sel = np.full((n_days, best["top_n"]), -1, dtype=np.int32)
        for day_no, day_idx in enumerate(day_indices):
            idx = day_idx[pool_mask[day_idx]]
            if idx.size == 0:
                continue
            idx = idx[np.argsort(-sort_key[idx], kind="mergesort")][:best["top_n"]]
            day_sel[day_no, :idx.size] = idx

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
            period = "PRE" if month < "2023-05" else ("TRAIN" if month < "2025-07" else "OOS")
            print(f"  {month:<7} {int(m_day_valid.sum()):<5} {m_tickets:<5} "
                  f"{m_ret:>8.2f}% {m_dwin:>6.1%} {m_twin:>6.1%} {m_h1:>5.1%}  [{period}]")

    # Also show how Codex best performs on full data
    print(f"\n{'='*120}")
    print("CODEX BEST (raw>=0.73, top1, vz>=0, score_then_rsi6_low, tp10) FULL PERIOD")
    print(f"{'='*120}")
    codex_match = [r for r in results if r["threshold"] == 0.73 and r["top_n"] == 1
                   and r["filter"] == "vz>=0" and r["recipe"] == "score_then_rsi6_low"
                   and r["exit"] == "tp10"]
    if codex_match:
        r = codex_match[0]
        print(f"Total: {r['total_return']:.0f}% | Sharpe: {r['sharpe'] or 0:.2f} | "
              f"DWin: {r['daily_win']:.1%} | H+1: {r['high1']:.1%}")
        print(f"Pre: {r['pre_ret']:.1f}% | Train: {r['train_ret']:.1f}% | OOS: {r['oos_ret']:.1f}%")
        print(f"Robust: {r['robust']} | MDD: {r['max_dd']:.1f}% | Months+: {r['months_pos']}/{r['months_total']}")


if __name__ == "__main__":
    main()
