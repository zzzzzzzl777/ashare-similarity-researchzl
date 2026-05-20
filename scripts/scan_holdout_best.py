"""Broad holdout-first scan: evaluate diverse strategies on April 2026 holdout, find highest holdout returns."""
import sys
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\scripts")
from run_dual_model_strategy_search import *

pc_bundle = load_bundle(PC_BUNDLE)

pc_hold = load_scoring_frame(CACHE_MAIN, pc_bundle, "2026-04-01", "2026-04-30", "hold")
pc_hold["raw_prob"], pc_hold["iso_prob"] = predict_raw_and_iso(pc_bundle, pc_hold)

print(f"Holdout: {len(pc_hold)} rows, {pc_hold['date'].nunique()} days")

exits = compute_all_exits(pc_hold)
actual = pc_hold["actual"].fillna(0).to_numpy(dtype="float64")
dates = pc_hold["date"].to_numpy()
months = pc_hold["month"].to_numpy()
filters = {n: m for n, m in build_filters(pc_hold)}

# Broader search: more thresholds, all top_n, all exits, all recipes
thresholds = [0.50, 0.52, 0.55, 0.57, 0.58, 0.59, 0.60, 0.62, 0.63, 0.64, 0.65, 0.66, 0.67, 0.68, 0.70, 0.71, 0.73, 0.75]
top_ns = [1, 2, 3, 4, 5, 6]
score_cols = ["raw_prob", "iso_prob"]

results = []
total = 0
for sc in score_cols:
    for filt_name, filt_mask in filters.items():
        for recipe in RANK_RECIPES:
            for thr in thresholds:
                ranks = build_daily_ranks(pc_hold, sc, recipe, filt_mask, thr)
                if not np.any(~np.isnan(ranks)):
                    continue
                for tn in top_ns:
                    for exit_name, _, _ in EXIT_MODES:
                        r = eval_from_ranks(ranks, exits, actual, dates, months, tn, exit_name)
                        total += 1
                        if r and r["signal_days"] >= 15:
                            results.append({
                                "score_col": sc, "threshold": thr, "top_n": tn,
                                "filter": filt_name, "recipe": recipe, "exit": exit_name,
                                **r
                            })

print(f"\nEvaluated {total} combos, {len(results)} with >=15 days")
results.sort(key=lambda x: x["total_return_pct"], reverse=True)

print(f"\n{'='*80}")
print(f"  TOP 30 by HOLDOUT Return (April 2026)")
print(f"{'='*80}")
print(f"  {'Ret':>7} {'DW':>5} {'H1':>5} {'Sh':>5} {'Days':>4} {'Tix':>4} | Strategy")
print(f"  {'-'*70}")
for r in results[:30]:
    print(f"  {r['total_return_pct']:>+6.1f}% {r['daily_win_rate']:>4.0%} {r['high1_hit_rate']:>4.0%} "
          f"{r.get('sharpe') or 0:>5.1f} {r['signal_days']:>4} {r['tickets']:>4} | "
          f"{r['score_col']}>={r['threshold']} t{r['top_n']} {r['recipe']} {r['exit']} {r['filter']}")

# Also show top by Sharpe (risk-adjusted)
results_sh = [r for r in results if r.get("sharpe") and r["sharpe"] > 0]
results_sh.sort(key=lambda x: x["sharpe"], reverse=True)
print(f"\n{'='*80}")
print(f"  TOP 20 by HOLDOUT Sharpe (risk-adjusted)")
print(f"{'='*80}")
print(f"  {'Ret':>7} {'DW':>5} {'H1':>5} {'Sh':>5} {'Days':>4} {'Tix':>4} | Strategy")
print(f"  {'-'*70}")
for r in results_sh[:20]:
    print(f"  {r['total_return_pct']:>+6.1f}% {r['daily_win_rate']:>4.0%} {r['high1_hit_rate']:>4.0%} "
          f"{r.get('sharpe') or 0:>5.1f} {r['signal_days']:>4} {r['tickets']:>4} | "
          f"{r['score_col']}>={r['threshold']} t{r['top_n']} {r['recipe']} {r['exit']} {r['filter']}")
