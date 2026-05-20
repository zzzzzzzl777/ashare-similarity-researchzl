"""Print monthly return detail for top strategies across selection + holdout."""
import sys
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\scripts")
from run_dual_model_strategy_search import *

s2_bundle = load_bundle(S2_BUNDLE)
pc_bundle = load_bundle(PC_BUNDLE)

s2_sel = load_scoring_frame(CACHE_PRETRAIN, s2_bundle, "2023-02-01", "2023-04-30", "sel")
pc_sel = load_scoring_frame(CACHE_PRETRAIN, pc_bundle, "2023-02-01", "2023-04-30", "sel")
s2_sel["raw_prob"], s2_sel["iso_prob"] = predict_raw_and_iso(s2_bundle, s2_sel)
pc_sel["raw_prob"], pc_sel["iso_prob"] = predict_raw_and_iso(pc_bundle, pc_sel)

s2_hold = load_scoring_frame(CACHE_MAIN, s2_bundle, "2026-04-01", "2026-04-30", "hold")
pc_hold = load_scoring_frame(CACHE_MAIN, pc_bundle, "2026-04-01", "2026-04-30", "hold")
s2_hold["raw_prob"], s2_hold["iso_prob"] = predict_raw_and_iso(s2_bundle, s2_hold)
pc_hold["raw_prob"], pc_hold["iso_prob"] = predict_raw_and_iso(pc_bundle, pc_hold)

candidates = [
    ("S2_iso59_t1_amtz_close",  "s2", "iso_prob", 0.59, 1, "amount_z_high", "close", "turnover_5_30"),
    ("S2_raw65_t3_prob_close",  "s2", "raw_prob", 0.65, 3, "prob_desc",     "close", "turnover>=5"),
    ("S2_raw71_t1_amtz_close",  "s2", "raw_prob", 0.71, 1, "amount_z_high", "close", "turnover>=8"),
    ("PC_iso58_t1_actz_tp10",   "pc", "iso_prob", 0.58, 1, "activity_z_high","tp10", "close_5_60"),
    ("PC_raw65_t3_prob_close",  "pc", "raw_prob", 0.65, 3, "prob_desc",     "close", "turnover>=5"),
    ("PC_raw71_t1_amtz_close",  "pc", "raw_prob", 0.71, 1, "amount_z_high", "close", "turnover>=8"),
    ("PC_raw65_t5_prob_close",  "pc", "raw_prob", 0.65, 5, "prob_desc",     "close", "turnover>=5"),
]

def eval_strat(df, score_col, threshold, top_n, recipe, exit_mode, filter_name):
    exits = compute_all_exits(df)
    actual = df["actual"].fillna(0).to_numpy(dtype="float64")
    dates = df["date"].to_numpy()
    months = df["month"].to_numpy()
    flt = {n: m for n, m in build_filters(df)}
    fm = flt.get(filter_name, np.ones(len(df), dtype=bool))
    ranks = build_daily_ranks(df, score_col, recipe, fm, threshold)
    return eval_from_ranks(ranks, exits, actual, dates, months, top_n, exit_mode)

for label, model, sc, thr, tn, recipe, ex, filt in candidates:
    sel_df = s2_sel if model == "s2" else pc_sel
    hold_df = s2_hold if model == "s2" else pc_hold

    sr = eval_strat(sel_df, sc, thr, tn, recipe, ex, filt)
    hr = eval_strat(hold_df, sc, thr, tn, recipe, ex, filt)

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  {sc}>={thr} | top{tn} | {recipe} | {ex} | {filt}")
    print(f"{'='*70}")

    for window_name, res in [("SELECTION (2023-02~04)", sr), ("HOLDOUT (2026-04)", hr)]:
        if res is None:
            print(f"\n  [{window_name}] — no data")
            continue
        print(f"\n  [{window_name}]")
        print(f"  Total: {res['total_return_pct']:+.1f}%  DayWin={res['daily_win_rate']:.0%}  "
              f"H1={res['high1_hit_rate']:.0%}  Sharpe={res.get('sharpe') or 0:.1f}  "
              f"Days={res['signal_days']}  Tickets={res['tickets']}")
        print(f"  {'Month':<10} {'Days':>5} {'Tix':>5} {'Return':>8} {'DayWin':>7} {'TixWin':>7} {'H1':>6}")
        print(f"  {'-'*50}")
        for m in res["months"]:
            print(f"  {m['month']:<10} {m['signal_days']:>5} {m['tickets']:>5} "
                  f"{m['return_pct']:>+7.1f}% {m['daily_win_rate']:>6.0%} "
                  f"{m['ticket_win_rate']:>6.0%} {m['high1_hit_rate']:>5.0%}")

print("\nDone.")
