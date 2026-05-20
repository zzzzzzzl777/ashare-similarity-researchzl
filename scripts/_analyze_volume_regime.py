"""Volume-based market regime analysis: IS vs OOS hit rate gap."""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

CSV = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\batch_postclose_all_candidates.csv")

df = pd.read_csv(CSV, dtype=str)
df["probability"] = df["probability"].astype(float)
df["next_high_return_pct"] = pd.to_numeric(df["next_high_return_pct"], errors="coerce")
df["next_close_return_pct"] = pd.to_numeric(df["next_close_return_pct"], errors="coerce")
df["close"] = pd.to_numeric(df["close"], errors="coerce")
if "换手" in df.columns:
    df["turnover_rate"] = pd.to_numeric(df["换手"], errors="coerce")
else:
    df["turnover_rate"] = np.nan

df["_date"] = pd.to_datetime(df["date"], format="mixed")
df["is_hit"] = df["hit"] == "hit"
df["verified"] = df["hit"].isin(["hit", "miss"])

# Define IS (train feature dates 2023-06-08 ~ 2025-06-30) vs OOS
train_start = pd.Timestamp("2023-06-08")
train_end = pd.Timestamp("2025-06-30")

df["period"] = np.where(
    (df["_date"] >= train_start) & (df["_date"] <= train_end), "IS",
    np.where(df["_date"] < train_start, "OOS_backward", "OOS_forward")
)

verified = df[df["verified"]].copy()
print(f"Total verified: {len(verified)}, IS={len(verified[verified.period=='IS'])}, "
      f"OOS_bwd={len(verified[verified.period=='OOS_backward'])}, OOS_fwd={len(verified[verified.period=='OOS_forward'])}")

# ── 1. Daily market turnover (成交额) from candidate average close * turnover_rate proxy ──
# We don't have direct market volume, but we can use per-candidate turnover_rate
# Group by date, get median turnover_rate as a proxy for market activity
daily = verified.groupby("_date").agg(
    n_cands=("is_hit", "count"),
    n_hits=("is_hit", "sum"),
    median_turnover=("turnover_rate", "median"),
    mean_turnover=("turnover_rate", "mean"),
    median_close=("close", "median"),
    period=("period", "first"),
).reset_index()
daily["hit_rate"] = daily["n_hits"] / daily["n_cands"]

print("\n" + "="*70)
print("1. 按候选股换手率中位数分组 (Volume Regime by Turnover Rate)")
print("="*70)

# Bin by median turnover quartiles (computed on full dataset)
daily["turnover_q"] = pd.qcut(daily["median_turnover"], 4, labels=["Q1_低换手", "Q2", "Q3", "Q4_高换手"], duplicates="drop")

for q in daily["turnover_q"].cat.categories:
    sub = daily[daily["turnover_q"] == q]
    print(f"\n  {q}:")
    for p in ["IS", "OOS_backward", "OOS_forward"]:
        sp = sub[sub["period"] == p]
        if len(sp) == 0:
            continue
        total_cands = sp["n_cands"].sum()
        total_hits = sp["n_hits"].sum()
        hr = total_hits / total_cands * 100 if total_cands > 0 else 0
        print(f"    {p:15s}: {len(sp):4d} days, {total_cands:6d} cands, HR={hr:.2f}%")

# ── 2. Use absolute turnover bins ──
print("\n" + "="*70)
print("2. 按绝对换手率水平分组 (Fixed Turnover Bins)")
print("="*70)

# Per-candidate analysis with turnover bins
verified["turnover_bin"] = pd.cut(
    verified["turnover_rate"],
    bins=[0, 2, 5, 10, 20, 100],
    labels=["0-2%", "2-5%", "5-10%", "10-20%", "20%+"],
    right=True
)

for tb in ["0-2%", "2-5%", "5-10%", "10-20%", "20%+"]:
    sub = verified[verified["turnover_bin"] == tb]
    if len(sub) == 0:
        continue
    print(f"\n  换手率 {tb}:")
    for p in ["IS", "OOS_backward", "OOS_forward"]:
        sp = sub[sub["period"] == p]
        if len(sp) == 0:
            continue
        hr = sp["is_hit"].mean() * 100
        avg_ret = sp["next_high_return_pct"].mean()
        print(f"    {p:15s}: {len(sp):6d} cands, HR={hr:.2f}%, avg_high_ret={avg_ret:.2f}%")

# ── 3. Volume distribution comparison IS vs OOS ──
print("\n" + "="*70)
print("3. 换手率分布对比 (IS vs OOS)")
print("="*70)

for p in ["IS", "OOS_backward", "OOS_forward"]:
    sub = verified[verified["period"] == p]["turnover_rate"]
    if len(sub) == 0:
        continue
    print(f"  {p:15s}: median={sub.median():.2f}%, mean={sub.mean():.2f}%, "
          f"p25={sub.quantile(0.25):.2f}%, p75={sub.quantile(0.75):.2f}%")

# ── 4. Half-yearly timeline ──
print("\n" + "="*70)
print("4. 半年度时间线 (Volume + Hit Rate)")
print("="*70)

verified["half_year"] = verified["_date"].dt.year.astype(str) + "-" + np.where(verified["_date"].dt.month <= 6, "H1", "H2")

hy = verified.groupby("half_year").agg(
    n=("is_hit", "count"),
    hits=("is_hit", "sum"),
    median_turnover=("turnover_rate", "median"),
    mean_turnover=("turnover_rate", "mean"),
    period=("period", "first"),
).reset_index()
hy["hr"] = hy["hits"] / hy["n"] * 100

print(f"  {'半年':10s} {'期间':15s} {'候选数':>7s} {'命中率':>7s} {'中位换手':>8s} {'均值换手':>8s}")
print(f"  {'-'*10} {'-'*15} {'-'*7} {'-'*7} {'-'*8} {'-'*8}")
for _, r in hy.iterrows():
    print(f"  {r['half_year']:10s} {r['period']:15s} {r['n']:7d} {r['hr']:6.2f}% {r['median_turnover']:7.2f}% {r['mean_turnover']:7.2f}%")

# ── 5. Same-turnover-regime IS vs OOS gap ──
print("\n" + "="*70)
print("5. 同换手率环境下 IS vs OOS 命中率差 (核心分析)")
print("="*70)

verified["turnover_q"] = pd.qcut(verified["turnover_rate"], 5, labels=["Q1_最低", "Q2", "Q3", "Q4", "Q5_最高"], duplicates="drop")

gaps = []
for q in verified["turnover_q"].cat.categories:
    sub = verified[verified["turnover_q"] == q]
    is_hr = sub[sub["period"] == "IS"]["is_hit"].mean() * 100
    oos_bwd_hr = sub[sub["period"] == "OOS_backward"]["is_hit"].mean() * 100
    oos_fwd_hr = sub[sub["period"] == "OOS_forward"]["is_hit"].mean() * 100
    is_n = len(sub[sub["period"] == "IS"])
    bwd_n = len(sub[sub["period"] == "OOS_backward"])
    fwd_n = len(sub[sub["period"] == "OOS_forward"])

    gap_bwd = is_hr - oos_bwd_hr if bwd_n > 0 else float("nan")
    gap_fwd = is_hr - oos_fwd_hr if fwd_n > 0 else float("nan")

    print(f"\n  {q}:")
    print(f"    IS:          {is_n:6d} cands, HR={is_hr:.2f}%")
    if bwd_n > 0:
        print(f"    OOS_backward:{bwd_n:6d} cands, HR={oos_bwd_hr:.2f}%  gap={gap_bwd:+.2f}pp")
    if fwd_n > 0:
        print(f"    OOS_forward: {fwd_n:6d} cands, HR={oos_fwd_hr:.2f}%  gap={gap_fwd:+.2f}pp")
    gaps.append({"q": q, "is_hr": is_hr, "oos_bwd_hr": oos_bwd_hr, "oos_fwd_hr": oos_fwd_hr,
                 "gap_bwd": gap_bwd, "gap_fwd": gap_fwd})

print("\n  ── 汇总 ──")
print(f"  {'分位':10s} {'IS HR':>7s} {'OOS后HR':>8s} {'gap后':>7s} {'OOS前HR':>8s} {'gap前':>7s}")
for g in gaps:
    bwd = f"{g['oos_bwd_hr']:.2f}%" if not np.isnan(g['oos_bwd_hr']) else "N/A"
    fwd = f"{g['oos_fwd_hr']:.2f}%" if not np.isnan(g['oos_fwd_hr']) else "N/A"
    gb = f"{g['gap_bwd']:+.2f}" if not np.isnan(g['gap_bwd']) else "N/A"
    gf = f"{g['gap_fwd']:+.2f}" if not np.isnan(g['gap_fwd']) else "N/A"
    print(f"  {str(g['q']):10s} {g['is_hr']:6.2f}% {bwd:>8s} {gb:>7s} {fwd:>8s} {gf:>7s}")

# ── 6. Volume activity level (high/low volume days) ──
print("\n" + "="*70)
print("6. 放量日 vs 缩量日 命中率对比")
print("="*70)

# Define high/low volume days: daily median turnover above/below overall median
overall_median = daily["median_turnover"].median()
daily["vol_regime"] = np.where(daily["median_turnover"] >= overall_median, "放量日", "缩量日")

for vr in ["放量日", "缩量日"]:
    sub = daily[daily["vol_regime"] == vr]
    print(f"\n  {vr} (median turnover {'≥' if vr=='放量日' else '<'} {overall_median:.2f}%):")
    for p in ["IS", "OOS_backward", "OOS_forward"]:
        sp = sub[sub["period"] == p]
        if len(sp) == 0:
            continue
        total_cands = sp["n_cands"].sum()
        total_hits = sp["n_hits"].sum()
        hr = total_hits / total_cands * 100
        print(f"    {p:15s}: {len(sp):4d} days, {total_cands:6d} cands, HR={hr:.2f}%")

# ── 7. Conclusion ──
print("\n" + "="*70)
print("7. 结论")
print("="*70)

is_total = verified[verified["period"] == "IS"]
oos_bwd_total = verified[verified["period"] == "OOS_backward"]
oos_fwd_total = verified[verified["period"] == "OOS_forward"]

is_hr = is_total["is_hit"].mean() * 100
bwd_hr = oos_bwd_total["is_hit"].mean() * 100
fwd_hr = oos_fwd_total["is_hit"].mean() * 100

print(f"\n  Overall: IS={is_hr:.2f}%, OOS_backward={bwd_hr:.2f}%, OOS_forward={fwd_hr:.2f}%")
print(f"  IS-OOS_backward gap: {is_hr - bwd_hr:.2f}pp")
print(f"  IS-OOS_forward gap: {is_hr - fwd_hr:.2f}pp")

# Check if gap narrows in any volume quintile
min_gap_bwd = min(g["gap_bwd"] for g in gaps if not np.isnan(g["gap_bwd"]))
max_gap_bwd = max(g["gap_bwd"] for g in gaps if not np.isnan(g["gap_bwd"]))
print(f"\n  Volume quintile gap range (backward): {min_gap_bwd:.2f}pp ~ {max_gap_bwd:.2f}pp")
print(f"  Gap spread: {max_gap_bwd - min_gap_bwd:.2f}pp")

if max_gap_bwd - min_gap_bwd > 5:
    print("\n  >>> 换手率环境对 IS-OOS gap 有显著影响，部分 gap 可归因于市场活跃度差异")
else:
    print("\n  >>> 换手率环境对 IS-OOS gap 影响有限，gap 在各换手率分位下基本均匀")
    print("  >>> 进一步支持 gap 主要来源是过拟合，而非市场风格/流动性差异")
