"""Focused replay: compute metrics ONLY on perturbed rows (with 5-min data)."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import numpy as np
import pandas as pd
import lightgbm as lgb
from pathlib import Path
from datetime import date as dt_date

RUN_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260504T033857Z_074fe9ea")
FEATURE_CACHE_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_383b5a3c0e707ae9.parquet")
MIN5_DIR = Path(r"E:\ashare_similarity_runtime\data\cache\prediction\tushare\stk_mins_5")

APRIL_START = dt_date(2026, 4, 1)
APRIL_END = dt_date(2026, 4, 30)

with open(RUN_DIR / "artifact.json") as f:
    artifact = json.load(f)
SELECTED_FEATURES = artifact["result"]["feature_selection"]["selected_features"]

# Load feature cache
print("Loading feature cache...")
data = pd.read_parquet(FEATURE_CACHE_PATH)
data["date"] = pd.to_datetime(data["date"])

# Get selected features available in cache
selected = [f for f in SELECTED_FEATURES if f in data.columns]
print(f"Selected features in cache: {len(selected)}/260")

# Train/test split
train_data = data[data["date"] <= pd.Timestamp("2025-12-31")]
apr_test = data[(data["date"].dt.date >= APRIL_START) & (data["date"].dt.date <= APRIL_END)].copy()
print(f"April test rows: {len(apr_test)}")

# Train LightGBM
print("Training LightGBM...")
train_valid = train_data.dropna(subset=["actual"])
if len(train_valid) > 300_000:
    train_valid = train_valid.sample(300_000, random_state=42)

X_train = train_valid[selected].to_numpy(dtype=np.float32)
X_train = np.nan_to_num(X_train, nan=0.0)
mean = X_train.mean(axis=0)
std = np.clip(X_train.std(axis=0), 1e-6, None)
y_train = train_valid["actual"].to_numpy(dtype=np.float32)

X_train_norm = (X_train - mean) / std
dtrain = lgb.Dataset(X_train_norm, label=y_train)
params = {
    "objective": "binary", "metric": "binary_logloss",
    "num_leaves": 127, "learning_rate": 0.05,
    "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 5,
    "min_child_samples": 50, "seed": 42, "verbose": -1,
}
model = lgb.train(params, dtrain, num_boost_round=500)

# Predict on original April features
X_test_orig = apr_test[selected].to_numpy(dtype=np.float32)
X_test_orig = np.nan_to_num(X_test_orig, nan=0.0)
X_test_orig_norm = (X_test_orig - mean) / std
prob_orig = model.predict(X_test_orig_norm)

# Load 14:55 as-of data
print("Reconstructing 14:55 as-of OHLCV...")
asof_records = []
min5_files = list(MIN5_DIR.glob("*.parquet"))
for i, fpath in enumerate(min5_files):
    sym = fpath.stem.split(".")[0]
    df = pd.read_parquet(fpath)
    df["trade_time"] = pd.to_datetime(df["trade_time"])
    df["dt"] = df["trade_time"].dt.date
    mask = (df["dt"] >= APRIL_START) & (df["dt"] <= APRIL_END)
    apr = df[mask]
    if apr.empty:
        continue
    for d, day_df in apr.groupby("dt"):
        t = pd.Timestamp(f"{d} 14:55:00")
        before = day_df[day_df["trade_time"] <= t]
        final_bar = day_df[day_df["trade_time"] == pd.Timestamp(f"{d} 15:00:00")]
        if before.empty or final_bar.empty:
            continue
        asof_records.append({
            "symbol": sym, "date": pd.Timestamp(d),
            "close_1455": before.iloc[-1]["close"],
            "close_final": final_bar.iloc[0]["close"],
            "vol_1455": before["vol"].sum(),
            "vol_final": day_df["vol"].sum(),
            "amount_1455": before["amount"].sum(),
            "amount_final": day_df["amount"].sum(),
        })

asof_df = pd.DataFrame(asof_records)
print(f"  As-of snapshots: {len(asof_df)} ({asof_df['symbol'].nunique()} syms, {asof_df['date'].dt.date.nunique()} dates)")

# Merge
apr_test_reset = apr_test.reset_index(drop=True)
apr_merged = apr_test_reset.merge(
    asof_df[["symbol", "date", "close_1455", "close_final", "vol_1455", "vol_final", "amount_1455", "amount_final"]],
    on=["symbol", "date"], how="left"
)
has_asof = apr_merged["close_final"].notna()
print(f"  Rows with 14:55 data: {has_asof.sum()}/{len(apr_merged)} ({has_asof.mean()*100:.1f}%)")

# Compute perturbation ratios
close_ratio = np.ones(len(apr_merged))
vol_ratio = np.ones(len(apr_merged))
amount_ratio = np.ones(len(apr_merged))
close_ratio[has_asof] = (apr_merged.loc[has_asof, "close_1455"] / apr_merged.loc[has_asof, "close_final"]).values
vol_ratio[has_asof] = (apr_merged.loc[has_asof, "vol_1455"] / apr_merged.loc[has_asof, "vol_final"]).values
amount_ratio[has_asof] = (apr_merged.loc[has_asof, "amount_1455"] / apr_merged.loc[has_asof, "amount_final"]).values

# Feature perturbation
feature_idx = {name: i for i, name in enumerate(selected)}
CLOSE_DEP = ["ret_1","ret_2","ret_3","ret_5","ret_10","ret_20","ret_accel_1_3","ret_accel_3_10",
    "ret_mean_3","ret_mean_5","ret_mean_10","intraday_return","overnight_intraday_gap",
    "overnight_vs_intraday","reversal_intraday","close_position","ma_gap_5","ma_gap_10","ma_gap_20",
    "mean_reversion_distance_5","bollinger_position_20","dist_high_10","dist_high_20","dist_low_10",
    "dist_low_20","breakout_20","breakdown_20","price_position_20","price_position_60",
    "cost_position_20","cost_position_60","ret_lag_0","close_pos_lag_0",
    "ret1_x_volume_z5","ret1_x_close_position","ret5_x_volume_z10",
    "macd_hist","macd_signal","rsi_6","rsi_14","kdj_k","kdj_d","kdj_j",
    "cci_20","williams_r_14","t_plus_1_selling_pressure"]
VOL_DEP = ["volume_chg_1","volume_chg_5","volume_z_5","volume_z_10","volume_z_20",
    "volume_z_lag_0","obv_trend_5","mfi_14","volume_to_mean_20",
    "volume_price_divergence_5","money_flow_fire","climax_volume_ratio_60",
    "range_x_volume_z5","upper_shadow_x_volume_z","lower_shadow_x_volume_z",
    "ret1_x_volume_z5","ret5_x_volume_z10","volume_z_x_cs_ret_rank"]
AMT_DEP = ["amount_chg_1","amount_chg_5","amount_z_20","amount_z_lag_0",
    "amount_to_mean_20","amount_to_max_20","climax_amount_ratio_60",
    "amount_z_x_range","daily_amount_300m_gate","amount_300m_turnover_quality"]
TURN_DEP = ["turnover","turnover_mean_3","turnover_mean_5","turnover_chg_1","turnover_chg_5",
    "turnover_z_20","turnover_to_max_20","turnover_sum_5","turnover_sum_10",
    "turnover_sum_20","turnover_accel_5_20","turnover_x_range","limit_up_turnover"]

X_test_perturbed = X_test_orig.copy()
perturbed_set = set()
for feat in CLOSE_DEP:
    if feat in feature_idx:
        X_test_perturbed[:, feature_idx[feat]] += (close_ratio - 1)
        perturbed_set.add(feat)
for feat in VOL_DEP:
    if feat in feature_idx:
        X_test_perturbed[:, feature_idx[feat]] *= vol_ratio
        perturbed_set.add(feat)
for feat in AMT_DEP:
    if feat in feature_idx:
        X_test_perturbed[:, feature_idx[feat]] *= amount_ratio
        perturbed_set.add(feat)
for feat in TURN_DEP:
    if feat in feature_idx:
        X_test_perturbed[:, feature_idx[feat]] *= vol_ratio
        perturbed_set.add(feat)

print(f"  Perturbed features: {len(perturbed_set)}/260")

# Predict with perturbed features
X_test_perturbed_norm = (X_test_perturbed - mean) / std
prob_asof = model.predict(X_test_perturbed_norm)

apr_merged["prob_orig"] = prob_orig
apr_merged["prob_asof"] = prob_asof
apr_merged["prob_diff"] = prob_asof - prob_orig

# ===== METRICS: ONLY on rows with actual perturbation =====
pr = apr_merged[has_asof].copy()
print(f"\n{'='*70}")
print(f"RESULTS: Perturbed rows ONLY ({len(pr)} rows, {pr['symbol'].nunique()} symbols)")
print(f"{'='*70}")

diff = pr["prob_diff"]
abs_diff = diff.abs()
print(f"\n  Probability difference stats:")
print(f"    mean_abs_diff:   {abs_diff.mean():.6f}")
print(f"    median_abs_diff: {abs_diff.median():.6f}")
print(f"    P95_abs_diff:    {abs_diff.quantile(0.95):.6f}")
print(f"    P99_abs_diff:    {abs_diff.quantile(0.99):.6f}")
print(f"    max_abs_diff:    {abs_diff.max():.6f}")
print(f"    std_diff:        {diff.std():.6f}")

print(f"\n  Correlation:")
print(f"    Pearson:  {pr['prob_orig'].corr(pr['prob_asof']):.6f}")
print(f"    Spearman: {pr['prob_orig'].corr(pr['prob_asof'], method='spearman'):.6f}")

# Top-N overlap
print(f"\n  Top-N overlap (within {len(pr)} perturbed rows):")
for n in [30, 50, 100]:
    if len(pr) >= n:
        top_orig = set(pr.nlargest(n, "prob_orig").index)
        top_asof = set(pr.nlargest(n, "prob_asof").index)
        overlap = len(top_orig & top_asof) / n
        print(f"    Top{n}: {overlap*100:.1f}%")

# Per-day top-10 overlap
print(f"\n  Per-day top-10 overlap:")
daily_overlaps = []
for d, day_df in pr.groupby(pr["date"].dt.date):
    if len(day_df) < 10:
        continue
    n = min(10, len(day_df))
    top_orig = set(day_df.nlargest(n, "prob_orig").index)
    top_asof = set(day_df.nlargest(n, "prob_asof").index)
    overlap = len(top_orig & top_asof) / n
    daily_overlaps.append({"date": str(d), "overlap": overlap, "n_rows": len(day_df)})
    print(f"    {d}: overlap={overlap*100:.0f}% (n={len(day_df)})")
if daily_overlaps:
    mean_overlap = np.mean([x["overlap"] for x in daily_overlaps])
    min_overlap = min(x["overlap"] for x in daily_overlaps)
    print(f"    --- Mean: {mean_overlap*100:.1f}%, Min: {min_overlap*100:.0f}%")

# Threshold analysis
print(f"\n  Threshold analysis:")
for thresh in [0.60, 0.65, 0.70, 0.75, 0.80]:
    orig_set = set(pr[pr["prob_orig"] >= thresh].index)
    asof_set = set(pr[pr["prob_asof"] >= thresh].index)
    if orig_set:
        recall = len(orig_set & asof_set) / len(orig_set)
        jaccard = len(orig_set & asof_set) / len(orig_set | asof_set) if (orig_set | asof_set) else 0
        print(f"    T>={thresh}: orig={len(orig_set)}, asof={len(asof_set)}, "
              f"recall={recall*100:.1f}%, jaccard={jaccard*100:.1f}%")
    else:
        print(f"    T>={thresh}: 0 candidates")

# Precision comparison
if "actual" in pr.columns:
    print(f"\n  Precision at threshold (perturbed rows):")
    for thresh in [0.60, 0.65, 0.70, 0.75]:
        orig_c = pr[pr["prob_orig"] >= thresh]
        asof_c = pr[pr["prob_asof"] >= thresh]
        if len(orig_c) > 5 and len(asof_c) > 5:
            print(f"    T>={thresh}: orig={orig_c['actual'].mean()*100:.1f}% (n={len(orig_c)}), "
                  f"asof={asof_c['actual'].mean()*100:.1f}% (n={len(asof_c)})")

# Biggest movers
print(f"\n  Biggest probability changes (prob_orig >= 0.60):")
high = pr[pr["prob_orig"] >= 0.60].copy()
if len(high) > 0:
    high["abs_diff"] = high["prob_diff"].abs()
    worst = high.nlargest(15, "abs_diff")
    print(worst[["symbol", "date", "prob_orig", "prob_asof", "prob_diff"]].to_string())

# Non-reconstructable features
MONEYFLOW = ["tushare_net_mf_amount","tushare_lg_buy_sell_ratio","tushare_elg_buy_sell_ratio",
    "tushare_mf_strength","tushare_sm_sell_pressure","tushare_main_force_divergence","tushare_ff_adjusted_flow"]
mf_in_sel = [f for f in MONEYFLOW if f in selected]
not_perturbed = [f for f in selected if f not in perturbed_set]

print(f"\n{'='*70}")
print(f"NON-RECONSTRUCTABLE / NOT PERTURBED FEATURES")
print(f"{'='*70}")
print(f"  Total not perturbed: {len(not_perturbed)}/260")
print(f"  Moneyflow (no intraday history): {mf_in_sel}")
print(f"  tushare_volume_ratio (computable from pytdx vol / 5d avg): ['tushare_volume_ratio']")

# Categorize not-perturbed
lag_feats = [f for f in not_perturbed if "_lag_" in f and f not in ["ret_lag_0","range_lag_0","close_pos_lag_0","volume_z_lag_0","amount_z_lag_0"]]
calendar = [f for f in not_perturbed if "day_of_week" in f or "month_" in f]
market = [f for f in not_perturbed if f.startswith("market_") or f.startswith("emotion_") or "board_" in f or f.startswith("prev_")]
cs = [f for f in not_perturbed if f.startswith("cs_") or f.startswith("rel_")]
sector = [f for f in not_perturbed if f.startswith("sector_")]
tushare_limit = [f for f in not_perturbed if "limit_distance" in f or "limit_range" in f]
other = [f for f in not_perturbed if f not in lag_feats and f not in calendar and f not in market and f not in cs and f not in sector and f not in tushare_limit and f not in mf_in_sel]

print(f"\n  Breakdown of {len(not_perturbed)} not-perturbed features:")
print(f"    Lag T-1+ (correct as-is): {len(lag_feats)}")
print(f"    Calendar (correct): {len(calendar)}")
print(f"    Market/board/prev (correct pre-14:55): {len(market)}")
print(f"    Cross-sectional cs_*/rel_* (need full mkt snap): {len(cs)}")
print(f"    Sector (need sector data): {len(sector)}")
print(f"    Tushare limit (correct, pre-open): {len(tushare_limit)}")
print(f"    Moneyflow (NOT available at 14:55): {len(mf_in_sel)}")
print(f"    Other: {len(other)}")
if other:
    print(f"      {other[:30]}")

# Save full results
output = {
    "n_perturbed_rows": len(pr),
    "n_symbols": int(pr["symbol"].nunique()),
    "coverage_pct": float(has_asof.mean() * 100),
    "ohlcv_diffs": {
        "close_mean_abs_pct": float(abs((pr["close_1455"]/pr["close_final"]-1)*100).mean()) if "close_1455" in pr.columns else None,
        "vol_mean_pct": float(((pr["vol_1455"]/pr["vol_final"]-1)*100).mean()) if "vol_1455" in pr.columns else None,
    },
    "prob_diffs": {
        "mean_abs": float(abs_diff.mean()),
        "median_abs": float(abs_diff.median()),
        "p95_abs": float(abs_diff.quantile(0.95)),
        "p99_abs": float(abs_diff.quantile(0.99)),
        "max_abs": float(abs_diff.max()),
    },
    "correlation": {
        "pearson": float(pr["prob_orig"].corr(pr["prob_asof"])),
        "spearman": float(pr["prob_orig"].corr(pr["prob_asof"], method="spearman")),
    },
    "daily_top10_overlaps": daily_overlaps,
    "n_perturbed_features": len(perturbed_set),
    "n_not_perturbed": len(not_perturbed),
    "moneyflow_not_available": mf_in_sel,
}

out_path = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\replay_1457_detailed_metrics.json")
with open(out_path, "w") as f:
    json.dump(output, f, indent=2, default=str)
print(f"\nSaved to: {out_path}")
