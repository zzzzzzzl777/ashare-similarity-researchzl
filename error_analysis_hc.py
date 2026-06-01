"""
Error analysis of high-confidence predictions from the latest all-family run.
Focus: What is keeping Wilson lower bound below 75%?
"""

import pandas as pd
import numpy as np
from pathlib import Path

PARQUET_PATH = r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260503T071809Z_f57a2059\test_predictions.parquet"

def main():
    print("=" * 80)
    print("HIGH-CONFIDENCE PREDICTION ERROR ANALYSIS")
    print("=" * 80)

    # 1. Load data
    df = pd.read_parquet(PARQUET_PATH)
    print(f"\nDataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"\nOverall stats:")
    print(f"  Total samples: {len(df)}")
    print(f"  Positive labels (actual==1): {df['actual'].sum()} ({df['actual'].mean()*100:.2f}%)")

    # 2. Filter to high-confidence positive candidates
    hc = df[(df['confident'] == 1) & (df['predicted_label'] == 1)].copy()
    print(f"\n  HC positive candidates: {len(hc)} ({len(hc)/len(df)*100:.2f}% of total)")
    print(f"  HC hits (actual==1): {hc['actual'].sum()} / {len(hc)}")
    print(f"  HC precision (raw): {hc['actual'].mean()*100:.2f}%")

    # Wilson lower bound calculation
    n = len(hc)
    p_hat = hc['actual'].mean()
    z = 1.96  # 95% confidence
    wilson_lb = (p_hat + z**2/(2*n) - z*np.sqrt(p_hat*(1-p_hat)/n + z**2/(4*n**2))) / (1 + z**2/n)
    print(f"  Wilson lower bound (95%): {wilson_lb*100:.2f}%")

    # =========================================================================
    # 3. Per-date statistics
    # =========================================================================
    print("\n" + "=" * 80)
    print("PER-DATE STATISTICS")
    print("=" * 80)

    date_stats = []
    for date_val, grp in df.groupby('date'):
        hc_grp = grp[(grp['confident'] == 1) & (grp['predicted_label'] == 1)]
        total = len(grp)
        hc_count = len(hc_grp)
        hc_hits = int(hc_grp['actual'].sum()) if hc_count > 0 else 0
        hc_prec = hc_grp['actual'].mean() if hc_count > 0 else np.nan
        natural_rate = grp['actual'].mean()
        lift = (hc_prec / natural_rate) if (hc_count > 0 and natural_rate > 0) else np.nan
        hc_misses = hc_count - hc_hits

        date_stats.append({
            'date': date_val,
            'total_samples': total,
            'hc_count': hc_count,
            'hc_hits': hc_hits,
            'hc_misses': hc_misses,
            'hc_precision': hc_prec,
            'natural_hit_rate': natural_rate,
            'lift': lift
        })

    ds = pd.DataFrame(date_stats).sort_values('hc_precision', ascending=True)

    print(f"\nTotal unique dates: {len(ds)}")
    print(f"Dates with HC candidates: {ds['hc_count'].gt(0).sum()}")

    # Threshold analysis
    ds_with_hc = ds[ds['hc_count'] > 0]
    below_75 = ds_with_hc[ds_with_hc['hc_precision'] < 0.75]
    below_60 = ds_with_hc[ds_with_hc['hc_precision'] < 0.60]
    below_50 = ds_with_hc[ds_with_hc['hc_precision'] < 0.50]

    print(f"\nDays with HC precision < 75%: {len(below_75)} / {len(ds_with_hc)} ({len(below_75)/len(ds_with_hc)*100:.1f}%)")
    print(f"Days with HC precision < 60%: {len(below_60)} / {len(ds_with_hc)} ({len(below_60)/len(ds_with_hc)*100:.1f}%)")
    print(f"Days with HC precision < 50%: {len(below_50)} / {len(ds_with_hc)} ({len(below_50)/len(ds_with_hc)*100:.1f}%)")

    print(f"\n--- TOP 20 WORST DAYS (lowest HC precision) ---")
    worst = ds_with_hc.head(20)
    print(worst[['date', 'total_samples', 'hc_count', 'hc_hits', 'hc_misses', 'hc_precision', 'natural_hit_rate', 'lift']].to_string(index=False))

    print(f"\n--- TOP 20 BEST DAYS (highest HC precision) ---")
    best = ds_with_hc.sort_values('hc_precision', ascending=False).head(20)
    print(best[['date', 'total_samples', 'hc_count', 'hc_hits', 'hc_misses', 'hc_precision', 'natural_hit_rate', 'lift']].to_string(index=False))

    # =========================================================================
    # 4. Feature comparison: HC hits vs HC misses
    # =========================================================================
    print("\n" + "=" * 80)
    print("FEATURE COMPARISON: HC HITS vs HC MISSES")
    print("=" * 80)

    hits = hc[hc['actual'] == 1]
    misses = hc[hc['actual'] == 0]

    print(f"\nHC Hits: {len(hits)}, HC Misses: {len(misses)}")

    # Identify numeric columns to compare
    numeric_cols = []
    candidate_cols = ['close', 'limit_up_like', 'turnover', 'amount', 'pct_change',
                      'next_high_return_pct', 'probability', 'pred_proba',
                      'market_cap', 'volume', 'open', 'high', 'low']
    for col in candidate_cols:
        if col in hc.columns and pd.api.types.is_numeric_dtype(hc[col]):
            numeric_cols.append(col)

    # Also check for any other numeric columns we might have missed
    all_numeric = hc.select_dtypes(include=[np.number]).columns.tolist()
    extra_numeric = [c for c in all_numeric if c not in numeric_cols and c not in ['actual', 'predicted_label', 'confident']]
    if extra_numeric:
        print(f"\nAdditional numeric columns found: {extra_numeric}")
        numeric_cols.extend(extra_numeric[:10])  # limit to avoid too much output

    print(f"\nComparing columns: {numeric_cols}")

    comparison_rows = []
    for col in numeric_cols:
        if col in hc.columns:
            h_mean = hits[col].mean()
            h_med = hits[col].median()
            m_mean = misses[col].mean()
            m_med = misses[col].median()
            diff_pct = ((m_mean - h_mean) / h_mean * 100) if h_mean != 0 else np.nan
            comparison_rows.append({
                'feature': col,
                'hits_mean': h_mean,
                'hits_median': h_med,
                'misses_mean': m_mean,
                'misses_median': m_med,
                'diff_mean_pct': diff_pct
            })

    comp_df = pd.DataFrame(comparison_rows)
    print("\n" + comp_df.to_string(index=False))

    # Probability distribution comparison
    if 'probability' in hc.columns:
        prob_col = 'probability'
    elif 'pred_proba' in hc.columns:
        prob_col = 'pred_proba'
    else:
        prob_col = None

    if prob_col:
        print(f"\n--- Probability Distribution ({prob_col}) ---")
        print(f"  Hits:   mean={hits[prob_col].mean():.4f}, std={hits[prob_col].std():.4f}, "
              f"Q25={hits[prob_col].quantile(0.25):.4f}, Q50={hits[prob_col].quantile(0.50):.4f}, Q75={hits[prob_col].quantile(0.75):.4f}")
        print(f"  Misses: mean={misses[prob_col].mean():.4f}, std={misses[prob_col].std():.4f}, "
              f"Q25={misses[prob_col].quantile(0.25):.4f}, Q50={misses[prob_col].quantile(0.50):.4f}, Q75={misses[prob_col].quantile(0.75):.4f}")

        # Overlap analysis
        threshold_90 = hits[prob_col].quantile(0.10)  # bottom 10% of hits
        misses_above = (misses[prob_col] >= threshold_90).sum()
        print(f"\n  Bottom 10% hits threshold: {threshold_90:.4f}")
        print(f"  Misses above this threshold: {misses_above} / {len(misses)} ({misses_above/len(misses)*100:.1f}%)")
        print(f"  => {100 - misses_above/len(misses)*100:.1f}% of misses have probability below bottom-10% of hits")

    # =========================================================================
    # 5. Primary error sources
    # =========================================================================
    print("\n" + "=" * 80)
    print("PRIMARY ERROR SOURCES")
    print("=" * 80)

    # Dates contributing most HC misses
    miss_by_date = ds_with_hc.sort_values('hc_misses', ascending=False)
    print(f"\n--- Top 20 dates by HC miss count ---")
    print(miss_by_date[['date', 'hc_count', 'hc_hits', 'hc_misses', 'hc_precision', 'natural_hit_rate']].head(20).to_string(index=False))

    total_misses = miss_by_date['hc_misses'].sum()
    top10_misses = miss_by_date['hc_misses'].head(10).sum()
    print(f"\nTotal HC misses: {total_misses}")
    print(f"Top 10 worst days contribute: {top10_misses} misses ({top10_misses/total_misses*100:.1f}% of all misses)")

    # Monthly pattern
    print(f"\n--- Monthly clustering of HC misses ---")
    ds_with_hc_copy = ds_with_hc.copy()
    ds_with_hc_copy['date_parsed'] = pd.to_datetime(ds_with_hc_copy['date'])
    ds_with_hc_copy['year_month'] = ds_with_hc_copy['date_parsed'].dt.to_period('M')

    monthly = ds_with_hc_copy.groupby('year_month').agg(
        days=('date', 'count'),
        total_hc=('hc_count', 'sum'),
        total_hits=('hc_hits', 'sum'),
        total_misses=('hc_misses', 'sum')
    ).reset_index()
    monthly['precision'] = monthly['total_hits'] / monthly['total_hc']
    monthly = monthly.sort_values('precision', ascending=True)
    print(monthly.to_string(index=False))

    # Weekly pattern (day of week)
    print(f"\n--- Day-of-week pattern ---")
    ds_with_hc_copy['dow'] = ds_with_hc_copy['date_parsed'].dt.day_name()
    dow_stats = ds_with_hc_copy.groupby('dow').agg(
        days=('date', 'count'),
        total_hc=('hc_count', 'sum'),
        total_hits=('hc_hits', 'sum'),
        total_misses=('hc_misses', 'sum')
    ).reset_index()
    dow_stats['precision'] = dow_stats['total_hits'] / dow_stats['total_hc']
    dow_stats = dow_stats.sort_values('precision', ascending=True)
    print(dow_stats.to_string(index=False))

    # Market condition proxy: natural hit rate correlation
    print(f"\n--- Correlation: natural hit rate vs HC precision ---")
    corr = ds_with_hc[['natural_hit_rate', 'hc_precision']].corr().iloc[0, 1]
    print(f"  Pearson correlation: {corr:.4f}")

    # When natural hit rate is low (bad market days), how does HC do?
    nat_q25 = ds_with_hc['natural_hit_rate'].quantile(0.25)
    nat_q75 = ds_with_hc['natural_hit_rate'].quantile(0.75)

    bad_market = ds_with_hc[ds_with_hc['natural_hit_rate'] <= nat_q25]
    good_market = ds_with_hc[ds_with_hc['natural_hit_rate'] >= nat_q75]

    bad_prec = bad_market['hc_hits'].sum() / bad_market['hc_count'].sum() if bad_market['hc_count'].sum() > 0 else 0
    good_prec = good_market['hc_hits'].sum() / good_market['hc_count'].sum() if good_market['hc_count'].sum() > 0 else 0

    print(f"\n  Natural hit rate Q25 threshold: {nat_q25:.4f}")
    print(f"  Natural hit rate Q75 threshold: {nat_q75:.4f}")
    print(f"  HC precision on BAD market days (bottom 25% natural rate): {bad_prec*100:.2f}% (n={bad_market['hc_count'].sum()})")
    print(f"  HC precision on GOOD market days (top 25% natural rate): {good_prec*100:.2f}% (n={good_market['hc_count'].sum()})")
    print(f"  Gap: {(good_prec - bad_prec)*100:.2f} pp")

    # HC count vs precision
    print(f"\n--- HC candidate volume vs precision ---")
    hc_q75 = ds_with_hc['hc_count'].quantile(0.75)
    hc_q25 = ds_with_hc['hc_count'].quantile(0.25)

    high_vol = ds_with_hc[ds_with_hc['hc_count'] >= hc_q75]
    low_vol = ds_with_hc[ds_with_hc['hc_count'] <= hc_q25]

    hv_prec = high_vol['hc_hits'].sum() / high_vol['hc_count'].sum() if high_vol['hc_count'].sum() > 0 else 0
    lv_prec = low_vol['hc_hits'].sum() / low_vol['hc_count'].sum() if low_vol['hc_count'].sum() > 0 else 0

    print(f"  High-volume days (HC >= {hc_q75:.0f}): precision={hv_prec*100:.2f}% (n={high_vol['hc_count'].sum()})")
    print(f"  Low-volume days (HC <= {hc_q25:.0f}): precision={lv_prec*100:.2f}% (n={low_vol['hc_count'].sum()})")

    # =========================================================================
    # 6. Summary: What is keeping Wilson below 75%?
    # =========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY: WHAT IS MOST LIKELY KEEPING WILSON BELOW 75%?")
    print("=" * 80)

    print(f"""
Key findings:

1. RAW PRECISION: {p_hat*100:.2f}% with Wilson LB at {wilson_lb*100:.2f}%
   - Need Wilson LB >= 75%, which requires raw precision well above 75%
   - Gap to close: {(0.75 - wilson_lb)*100:.2f} pp on Wilson LB

2. BAD DAYS IMPACT:
   - {len(below_75)} out of {len(ds_with_hc)} days have HC precision < 75%
   - Top 10 worst days account for {top10_misses} / {total_misses} misses ({top10_misses/total_misses*100:.1f}%)
   - These catastrophic days dilute the overall precision significantly

3. MARKET CONDITION SENSITIVITY:
   - Correlation between natural hit rate and HC precision: {corr:.4f}
   - Bad market days: {bad_prec*100:.2f}% precision vs Good market days: {good_prec*100:.2f}%
   - The model struggles to maintain selectivity when the overall market is weak

4. VOLUME-PRECISION TRADEOFF:
   - High-volume days precision: {hv_prec*100:.2f}% vs Low-volume: {lv_prec*100:.2f}%
   - {"Model is less selective on high-volume days" if hv_prec < lv_prec else "Volume does not appear to be the issue"}

5. ACTIONABLE RECOMMENDATIONS:
   - Consider a market regime filter to suppress HC signals on weak market days
   - The probability threshold for 'confident' may need tightening
   - Focus on reducing exposure during the worst {len(below_50)} zero/sub-50% days
   - A dynamic confidence threshold based on market conditions could help
""")

if __name__ == "__main__":
    main()
