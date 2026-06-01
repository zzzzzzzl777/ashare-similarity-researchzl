"""Step 0: 精度@阈值实证分析 — 第四轮训练计划"""
import pandas as pd
import numpy as np

PARQUET = (
    r"E:\ashare_similarity_runtime\data\reports\prediction\runs"
    r"\gpu_probe_20260503T113328Z_1b272829\test_predictions.parquet"
)
Q1_CUTOFF = "2026-03-31"


def wilson_lower(k, n, z=1.959964):
    if n == 0:
        return 0.0
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    spread = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return center - spread


def main():
    df = pd.read_parquet(PARQUET)
    df = df[df["date"] <= Q1_CUTOFF]
    n_days = df["date"].nunique()
    print(f"Total rows (Q1 only): {len(df)}, Trading days: {n_days}")
    print(f"Probability: mean={df['probability'].mean():.4f}, "
          f"std={df['probability'].std():.4f}\n")

    print(f"{'Threshold':>9} {'Count':>7} {'Hits':>6} {'Precision':>9} "
          f"{'Wilson_L':>8} {'Avg/Day':>7} {'Hit_Rate':>8}")
    print("-" * 65)

    for T in np.arange(0.55, 0.96, 0.01):
        mask = df["probability"] >= T
        n = mask.sum()
        if n < 30:
            continue
        hits = df.loc[mask, "actual"].sum()
        acc = hits / n
        wl = wilson_lower(hits, n)
        avg_day = n / n_days
        print(f"{T:>9.2f} {n:>7d} {hits:>6.0f} {acc:>9.4f} "
              f"{wl:>8.4f} {avg_day:>7.1f} {acc:>8.2%}")

    print("\n\n--- 每日候选数分布 (T=0.75) ---")
    T_demo = 0.75
    daily = df[df["probability"] >= T_demo].groupby("date").size()
    print(f"交易日数: {n_days}, 有候选的天数: {len(daily)}")
    print(f"每日候选数: mean={daily.mean():.1f}, median={daily.median():.0f}, "
          f"min={daily.min()}, max={daily.max()}")
    print(f"25%={daily.quantile(0.25):.0f}, 75%={daily.quantile(0.75):.0f}")


if __name__ == "__main__":
    main()
