"""Evaluate candidate strategies on both selection + holdout for dual-model comparison."""
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
    ("S2_iso59_t1_amtz_close", "s2", "iso_prob", 0.59, 1, "amount_z_high", "close", "turnover_5_30"),
    ("S2_iso59_t3_amtz_close", "s2", "iso_prob", 0.59, 3, "amount_z_high", "close", "turnover_5_30"),
    ("S2_iso59_t5_amtz_close", "s2", "iso_prob", 0.59, 5, "amount_z_high", "close", "turnover_5_30"),
    ("S2_raw65_t3_prob_close", "s2", "raw_prob", 0.65, 3, "prob_desc", "close", "turnover>=5"),
    ("S2_raw65_t5_prob_close", "s2", "raw_prob", 0.65, 5, "prob_desc", "close", "turnover>=5"),
    ("S2_raw60_t5_prob_close", "s2", "raw_prob", 0.60, 5, "prob_desc", "close", "turnover>=5"),
    ("S2_raw71_t1_amtz_close", "s2", "raw_prob", 0.71, 1, "amount_z_high", "close", "turnover>=8"),
    ("S2_raw66_t1_rsi_tp2", "s2", "raw_prob", 0.66, 1, "score_then_rsi6_low", "tp2", "turnover>=8"),
    ("S2_raw64_t3_rng_sl1tp3", "s2", "raw_prob", 0.64, 3, "range_high", "sl1_tp3", "t5_20|c5_60"),
    ("S2_raw65_t3_prob_sl2tp5", "s2", "raw_prob", 0.65, 3, "prob_desc", "sl2_tp5", "turnover>=5"),
    ("PC_iso58_t1_actz_tp10", "pc", "iso_prob", 0.58, 1, "activity_z_high", "tp10", "close_5_60"),
    ("PC_iso58_t3_actz_close", "pc", "iso_prob", 0.58, 3, "activity_z_high", "close", "close_5_60"),
    ("PC_iso58_t5_actz_close", "pc", "iso_prob", 0.58, 5, "activity_z_high", "close", "close_5_60"),
    ("PC_raw65_t3_prob_close", "pc", "raw_prob", 0.65, 3, "prob_desc", "close", "turnover>=5"),
    ("PC_raw65_t5_prob_close", "pc", "raw_prob", 0.65, 5, "prob_desc", "close", "turnover>=5"),
    ("PC_raw60_t5_prob_close", "pc", "raw_prob", 0.60, 5, "prob_desc", "close", "turnover>=5"),
    ("PC_raw71_t1_amtz_close", "pc", "raw_prob", 0.71, 1, "amount_z_high", "close", "turnover>=8"),
    ("PC_raw66_t1_rsi_tp2", "pc", "raw_prob", 0.66, 1, "score_then_rsi6_low", "tp2", "turnover>=8"),
    ("PC_raw64_t3_rng_sl1tp3", "pc", "raw_prob", 0.64, 3, "range_high", "sl1_tp3", "t5_20|c5_60"),
    ("PC_raw65_t3_prob_sl2tp5", "pc", "raw_prob", 0.65, 3, "prob_desc", "sl2_tp5", "turnover>=5"),
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

print(f"{'Label':<28} {'SEL_ret':>8} {'S_dw':>5} {'S_h1':>5} {'S_sh':>5} | {'H_ret':>7} {'H_dw':>5} {'H_h1':>5} {'Flag':>7}")
print("-" * 95)

for label, model, sc, thr, tn, recipe, ex, filt in candidates:
    sel_df = s2_sel if model == "s2" else pc_sel
    hold_df = s2_hold if model == "s2" else pc_hold
    sr = eval_strat(sel_df, sc, thr, tn, recipe, ex, filt)
    hr = eval_strat(hold_df, sc, thr, tn, recipe, ex, filt)
    if sr:
        s_ret = f"{sr['total_return_pct']:.1f}%"
        s_dw = f"{sr['daily_win_rate']:.0%}"
        s_h1 = f"{sr['high1_hit_rate']:.0%}"
        s_sh = f"{sr.get('sharpe', 0) or 0:.1f}"
    else:
        s_ret = s_dw = s_h1 = s_sh = "N/A"
    if hr:
        h_ret = f"{hr['total_return_pct']:.1f}%"
        h_dw = f"{hr['daily_win_rate']:.0%}"
        h_h1 = f"{hr['high1_hit_rate']:.0%}"
        flag = ""
        if sr and sr['total_return_pct'] > 0 and hr['total_return_pct'] < sr['total_return_pct'] * 0.3:
            flag = "OVERFIT"
        elif hr['total_return_pct'] < 0:
            flag = "LOSS"
    else:
        h_ret = h_dw = h_h1 = "N/A"
        flag = "NO_DATA"
    print(f"{label:<28} {s_ret:>8} {s_dw:>5} {s_h1:>5} {s_sh:>5} | {h_ret:>7} {h_dw:>5} {h_h1:>5} {flag:>7}")
