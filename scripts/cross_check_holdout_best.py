"""Cross-check: top holdout strategies evaluated on BOTH selection and holdout."""
import sys
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\scripts")
from run_dual_model_strategy_search import *

pc_bundle = load_bundle(PC_BUNDLE)
s2_bundle = load_bundle(S2_BUNDLE)

pc_sel = load_scoring_frame(CACHE_PRETRAIN, pc_bundle, "2023-02-01", "2023-04-30", "sel")
pc_sel["raw_prob"], pc_sel["iso_prob"] = predict_raw_and_iso(pc_bundle, pc_sel)
pc_hold = load_scoring_frame(CACHE_MAIN, pc_bundle, "2026-04-01", "2026-04-30", "hold")
pc_hold["raw_prob"], pc_hold["iso_prob"] = predict_raw_and_iso(pc_bundle, pc_hold)

s2_sel = load_scoring_frame(CACHE_PRETRAIN, s2_bundle, "2023-02-01", "2023-04-30", "sel")
s2_sel["raw_prob"], s2_sel["iso_prob"] = predict_raw_and_iso(s2_bundle, s2_sel)
s2_hold = load_scoring_frame(CACHE_MAIN, s2_bundle, "2026-04-01", "2026-04-30", "hold")
s2_hold["raw_prob"], s2_hold["iso_prob"] = predict_raw_and_iso(s2_bundle, s2_hold)

candidates = [
    # Top holdout return discoveries
    ("PC_iso55_t1_prob_close_rsi55",  "pc", "iso_prob", 0.55, 1, "prob_desc",           "close", "rsi6<=55"),
    ("PC_iso66_t1_srsi_close_t5",     "pc", "iso_prob", 0.66, 1, "score_then_rsi6_low", "close", "turnover>=5"),
    ("PC_iso50_t1_srsi_close_c360",   "pc", "iso_prob", 0.50, 1, "score_then_rsi6_low", "close", "close_3_60"),
    ("PC_iso57_t6_prob_tp10_t520c560", "pc", "iso_prob", 0.57, 6, "prob_desc",          "tp10",  "t5_20|c5_60"),
    ("PC_raw71_t3_pxa_tp2_t520c560",  "pc", "raw_prob", 0.71, 3, "prob_x_amount_z",    "tp2",   "t5_20|c5_60"),
    # Previous best
    ("PC_raw71_t1_amtz_close_t8",     "pc", "raw_prob", 0.71, 1, "amount_z_high",       "close", "turnover>=8"),
    ("PC_raw65_t3_prob_close_t5",     "pc", "raw_prob", 0.65, 3, "prob_desc",           "close", "turnover>=5"),
    # S2 versions of top holdout patterns
    ("S2_iso55_t1_prob_close_rsi55",  "s2", "iso_prob", 0.55, 1, "prob_desc",           "close", "rsi6<=55"),
    ("S2_iso66_t1_srsi_close_t5",     "s2", "iso_prob", 0.66, 1, "score_then_rsi6_low", "close", "turnover>=5"),
    ("S2_raw71_t1_amtz_close_t8",     "s2", "raw_prob", 0.71, 1, "amount_z_high",       "close", "turnover>=8"),
    # More aggressive combos
    ("PC_iso55_t1_srsi_close_rsi55",  "pc", "iso_prob", 0.55, 1, "score_then_rsi6_low", "close", "rsi6<=55"),
    ("PC_iso60_t1_srsi_tp10_t5",      "pc", "iso_prob", 0.60, 1, "score_then_rsi6_low", "tp10",  "turnover>=5"),
    ("PC_iso55_t2_srsi_close_rsi55",  "pc", "iso_prob", 0.55, 2, "score_then_rsi6_low", "close", "rsi6<=55"),
    ("PC_iso55_t1_prob_tp10_rsi55",   "pc", "iso_prob", 0.55, 1, "prob_desc",           "tp10",  "rsi6<=55"),
    ("PC_raw65_t1_srsi_close_t5",     "pc", "raw_prob", 0.65, 1, "score_then_rsi6_low", "close", "turnover>=5"),
    ("PC_raw60_t1_srsi_close_rsi55",  "pc", "raw_prob", 0.60, 1, "score_then_rsi6_low", "close", "rsi6<=55"),
    ("PC_iso67_t3_prob_sl1tp5_t520",  "pc", "iso_prob", 0.67, 3, "prob_desc",           "sl1_tp5","turnover_5_20"),
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

print(f"{'Label':<35} {'S_ret':>7} {'S_dw':>5} {'S_h1':>5} {'S_sh':>5} | {'H_ret':>7} {'H_dw':>5} {'H_h1':>5} {'H_sh':>5} | Note")
print("-" * 110)

for label, model, sc, thr, tn, recipe, ex, filt in candidates:
    sel_df = s2_sel if model == "s2" else pc_sel
    hold_df = s2_hold if model == "s2" else pc_hold
    sr = eval_strat(sel_df, sc, thr, tn, recipe, ex, filt)
    hr = eval_strat(hold_df, sc, thr, tn, recipe, ex, filt)

    if sr:
        s_ret = f"{sr['total_return_pct']:+.1f}%"
        s_dw = f"{sr['daily_win_rate']:.0%}"
        s_h1 = f"{sr['high1_hit_rate']:.0%}"
        s_sh = f"{sr.get('sharpe') or 0:.1f}"
    else:
        s_ret = s_dw = s_h1 = s_sh = "N/A"

    if hr:
        h_ret = f"{hr['total_return_pct']:+.1f}%"
        h_dw = f"{hr['daily_win_rate']:.0%}"
        h_h1 = f"{hr['high1_hit_rate']:.0%}"
        h_sh = f"{hr.get('sharpe') or 0:.1f}"
    else:
        h_ret = h_dw = h_h1 = h_sh = "N/A"

    # Note
    note = ""
    if sr and hr:
        if hr['total_return_pct'] > 0 and sr['total_return_pct'] > 0:
            if hr['total_return_pct'] >= sr['total_return_pct'] * 0.3:
                note = "OK"
            else:
                note = "OVERFIT"
        elif sr['total_return_pct'] < 0 and hr['total_return_pct'] > 0:
            note = "REGIME+"
        elif hr['total_return_pct'] < 0:
            note = "LOSS"
    print(f"{label:<35} {s_ret:>7} {s_dw:>5} {s_h1:>5} {s_sh:>5} | {h_ret:>7} {h_dw:>5} {h_h1:>5} {h_sh:>5} | {note}")

# Now show monthly detail for top 5 holdout performers
print(f"\n\n{'='*80}")
print("  MONTHLY DETAIL — Top holdout strategies")
print(f"{'='*80}")

top_holdout = [
    ("PC_iso55_t1_prob_close_rsi55",  "pc", "iso_prob", 0.55, 1, "prob_desc",           "close", "rsi6<=55"),
    ("PC_iso66_t1_srsi_close_t5",     "pc", "iso_prob", 0.66, 1, "score_then_rsi6_low", "close", "turnover>=5"),
    ("PC_iso55_t1_srsi_close_rsi55",  "pc", "iso_prob", 0.55, 1, "score_then_rsi6_low", "close", "rsi6<=55"),
    ("PC_raw71_t1_amtz_close_t8",     "pc", "raw_prob", 0.71, 1, "amount_z_high",       "close", "turnover>=8"),
    ("PC_iso67_t3_prob_sl1tp5_t520",  "pc", "iso_prob", 0.67, 3, "prob_desc",           "sl1_tp5","turnover_5_20"),
]

for label, model, sc, thr, tn, recipe, ex, filt in top_holdout:
    sel_df = pc_sel
    hold_df = pc_hold
    sr = eval_strat(sel_df, sc, thr, tn, recipe, ex, filt)
    hr = eval_strat(hold_df, sc, thr, tn, recipe, ex, filt)
    print(f"\n--- {label} ---")
    print(f"    {sc}>={thr} | top{tn} | {recipe} | {ex} | {filt}")
    for wn, res in [("SEL", sr), ("HOLD", hr)]:
        if not res:
            print(f"  [{wn}] N/A")
            continue
        print(f"  [{wn}] Total={res['total_return_pct']:+.1f}% DW={res['daily_win_rate']:.0%} H1={res['high1_hit_rate']:.0%} Sharpe={res.get('sharpe') or 0:.1f}")
        for m in res["months"]:
            print(f"    {m['month']} | {m['signal_days']:>2}d {m['tickets']:>3}tix | ret={m['return_pct']:+.1f}% dw={m['daily_win_rate']:.0%} h1={m['high1_hit_rate']:.0%}")
