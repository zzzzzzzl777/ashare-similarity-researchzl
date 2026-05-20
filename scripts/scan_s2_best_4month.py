"""Find S2's own best 4-month combined strategy."""
import sys
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\scripts")
from run_dual_model_strategy_search import *

s2_bundle = load_bundle(S2_BUNDLE)

s2_sel = load_scoring_frame(CACHE_PRETRAIN, s2_bundle, "2023-02-01", "2023-04-30", "sel")
s2_sel["raw_prob"], s2_sel["iso_prob"] = predict_raw_and_iso(s2_bundle, s2_sel)
s2_hold = load_scoring_frame(CACHE_MAIN, s2_bundle, "2026-04-01", "2026-04-30", "hold")
s2_hold["raw_prob"], s2_hold["iso_prob"] = predict_raw_and_iso(s2_bundle, s2_hold)

combined = pd.concat([s2_sel, s2_hold], ignore_index=True)
print(f"S2 Combined: {len(combined)} rows, {combined['date'].nunique()} days")

exits = compute_all_exits(combined)
actual = combined["actual"].fillna(0).to_numpy(dtype="float64")
dates = combined["date"].to_numpy()
months = combined["month"].to_numpy()
filters = {n: m for n, m in build_filters(combined)}

thresholds = [0.50, 0.52, 0.53, 0.55, 0.57, 0.58, 0.59, 0.60, 0.62, 0.63, 0.64, 0.65, 0.66, 0.67, 0.68, 0.70, 0.71, 0.73, 0.75]
top_ns = [1, 2, 3, 4, 5, 6]
score_cols = ["raw_prob", "iso_prob"]

results = []
total = 0
for sc in score_cols:
    for filt_name, filt_mask in filters.items():
        for recipe in RANK_RECIPES:
            for thr in thresholds:
                ranks = build_daily_ranks(combined, sc, recipe, filt_mask, thr)
                if not np.any(~np.isnan(ranks)):
                    continue
                for tn in top_ns:
                    for exit_name, _, _ in EXIT_MODES:
                        r = eval_from_ranks(ranks, exits, actual, dates, months, tn, exit_name)
                        total += 1
                        if r and r["signal_days"] >= 60:
                            results.append({
                                "score_col": sc, "threshold": thr, "top_n": tn,
                                "filter": filt_name, "recipe": recipe, "exit": exit_name,
                                **r
                            })

print(f"\nEvaluated {total} combos, {len(results)} with >=60 days")
results.sort(key=lambda x: x["total_return_pct"], reverse=True)

print(f"\n{'='*90}")
print(f"  S2 TOP 30 — COMBINED 4-month Total Return")
print(f"{'='*90}")
print(f"  {'Ret':>8} {'DW':>5} {'H1':>5} {'Sh':>5} {'Days':>4} {'Tix':>4} | Strategy")
print(f"  {'-'*80}")
for r in results[:30]:
    print(f"  {r['total_return_pct']:>+7.1f}% {r['daily_win_rate']:>4.0%} {r['high1_hit_rate']:>4.0%} "
          f"{r.get('sharpe') or 0:>5.1f} {r['signal_days']:>4} {r['tickets']:>4} | "
          f"{r['score_col']}>={r['threshold']} t{r['top_n']} {r['recipe']} {r['exit']} {r['filter']}")

# Monthly detail for top 5 (deduplicated)
print(f"\n\n{'='*90}")
print(f"  S2 MONTHLY DETAIL — Top unique strategies")
print(f"{'='*90}")
seen = set()
count = 0
for r in results:
    short_key = (r['top_n'], r['recipe'], r['exit'], r['filter'])
    if short_key in seen:
        continue
    seen.add(short_key)
    count += 1
    if count > 6:
        break
    print(f"\n  #{count} | {r['score_col']}>={r['threshold']} | top{r['top_n']} | {r['recipe']} | {r['exit']} | {r['filter']}")
    print(f"       Total={r['total_return_pct']:+.1f}% DW={r['daily_win_rate']:.0%} H1={r['high1_hit_rate']:.0%} Sharpe={r.get('sharpe') or 0:.1f} Days={r['signal_days']} Tix={r['tickets']}")
    for m in r["months"]:
        print(f"       {m['month']} | {m['signal_days']:>2}d {m['tickets']:>3}tix | ret={m['return_pct']:+.1f}% dw={m['daily_win_rate']:.0%} tw={m['ticket_win_rate']:.0%} h1={m['high1_hit_rate']:.0%}")
