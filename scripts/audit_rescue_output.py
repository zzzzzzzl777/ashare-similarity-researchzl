# -*- coding: utf-8 -*-
"""Post-hoc audit of 2026-05-06 rescue run output.

Applies tradability gates and reclassifies the 670-row raw output.
Does NOT re-run inference. Does NOT modify model/factors/thresholds.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

SCORED_PATH = Path(r"C:\Users\zzzzzzl\Desktop\realtime_1457_candidates_20260506_live.csv")
SNAPSHOT_PATH = Path(r"C:\Users\zzzzzzl\Desktop\raw_snapshot_20260506_pre1457.csv")
INSPECTION_OUT = Path(r"C:\Users\zzzzzzl\Desktop\realtime_1457_inspection_20260506.csv")
AUDIT_OUT = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\realtime_1457_corrected_audit_20260506.json")

THRESHOLD = 0.52


def get_limit_pct(sym, is_st):
    s = str(sym).zfill(6)
    if s.startswith(("300", "301", "688")):
        return 20.0
    elif s.startswith(("8", "4")):
        return 30.0
    else:
        return 5.0 if is_st else 10.0


def main():
    scored = pd.read_csv(SCORED_PATH, encoding="utf-8-sig")
    snapshot = pd.read_csv(SNAPSHOT_PATH, encoding="utf-8-sig")

    scored["symbol"] = scored["symbol"].astype(str).str.zfill(6)
    snapshot["symbol"] = snapshot["symbol"].astype(str).str.zfill(6)

    # Merge snapshot fields
    snap_cols = snapshot[["symbol", "name", "prev_close", "pct_change", "volume", "amount"]].copy()
    snap_cols = snap_cols.rename(columns={"name": "name_snap", "volume": "vol_snap", "amount": "amt_snap"})
    merged = scored.merge(snap_cols, on="symbol", how="left")

    # Use name from scored if available, else from snapshot
    # IMPORTANT: For ST detection, must use SNAPSHOT name (current market status)
    # The scored CSV name comes from stale cache and may lack ST prefix
    merged["display_name"] = merged["name"].fillna(merged["name_snap"])
    merged["snap_name"] = merged["name_snap"].fillna(merged["name"])

    # --- TRADABILITY GATES ---

    # 1. ST / *ST / 退市风险 — use SNAPSHOT name (has current ST markers)
    merged["is_st"] = merged["snap_name"].str.contains(r"ST|退", na=False, case=False)

    # 2. 停牌 / 无成交
    merged["is_suspended"] = (
        (merged["latest_price"].isna())
        | (merged["latest_price"] <= 0)
        | (merged["vol_snap"].fillna(0) == 0)
        | (merged["amt_snap"].fillna(0) == 0)
    )

    # 3. 涨停不可买
    merged["board_limit_pct"] = merged.apply(
        lambda r: get_limit_pct(r["symbol"], r["is_st"]), axis=1
    )
    merged["up_limit_price"] = (
        merged["prev_close"] * (1 + merged["board_limit_pct"] / 100)
    ).round(2)
    merged["is_limit_up"] = (
        (merged["latest_price"] >= merged["up_limit_price"] * 0.995)
        | (merged["pct_change"] >= merged["board_limit_pct"] - 0.5)
    )

    # 4. Price abnormal
    merged["price_abnormal"] = (merged["latest_price"] > 5000) | (merged["latest_price"] < 0.1)

    # 5. Turnover missing (all are missing from Sina)
    merged["turnover_missing"] = merged["turnover_asof_1457"].isna()

    # --- CLASSIFICATION ---
    merged["tradable"] = ~(
        merged["is_st"] | merged["is_suspended"] | merged["is_limit_up"] | merged["price_abnormal"]
    )

    def get_invalid_reason(row):
        reasons = []
        if row["is_st"]:
            reasons.append("ST/退市风险")
        if row["is_suspended"]:
            reasons.append("停牌/无成交")
        if row["is_limit_up"]:
            reasons.append("涨停不可买")
        if row["price_abnormal"]:
            reasons.append("价格异常")
        return "; ".join(reasons) if reasons else ""

    merged["invalid_reason"] = merged.apply(get_invalid_reason, axis=1)

    # --- AUDIT ---
    raw_scored_count = len(merged)
    threshold_passed_count = int((merged["probability"] >= THRESHOLD).sum())
    tradable_mask = merged["tradable"] & (merged["probability"] >= THRESHOLD)
    tradability_gate_passed_count = int(tradable_mask.sum())
    final_candidate_count = tradability_gate_passed_count  # no topK

    st_count = int(merged["is_st"].sum())
    suspended_count = int(merged["is_suspended"].sum())
    limit_up_count = int(merged["is_limit_up"].sum())
    price_abnormal_count = int(merged["price_abnormal"].sum())
    turnover_missing_count = int(merged["turnover_missing"].sum())

    print("=" * 70)
    print("CORRECTED AUDIT — 2026-05-06 post_1457_rescue")
    print("=" * 70)
    print()
    print("## Pipeline Classification")
    print(f"  raw_scored_count:              {raw_scored_count}")
    print(f"  threshold_passed_count:        {threshold_passed_count}  (threshold={THRESHOLD})")
    print(f"  tradability_gate_passed_count: {tradability_gate_passed_count}")
    print(f"  final_candidate_count:         {final_candidate_count}  (no topK applied)")
    print()
    print("## Failed Gate Reasons")
    print(f"  st_or_risk_count:              {st_count}")
    print(f"  suspended_or_no_volume_count:  {suspended_count}")
    print(f"  limit_up_or_near_limit_count:  {limit_up_count}")
    print(f"  price_abnormal_count:          {price_abnormal_count}")
    print(f"  turnover_missing_count:        {turnover_missing_count}  (ALL — Sina does not provide)")
    print()
    print("## Conclusion")
    print("  当前不产生正式候选。")
    print("  原因: short_only=False + turnover全缺失 + 概率分布异常(全体>=0.60)")
    print("  670只输出仅为工程诊断，不可用于交易。")
    print()

    # Detail: limit-up caught
    limit_ups = merged[merged["is_limit_up"]].sort_values("probability", ascending=False)
    print(f"## 涨停/接近涨停 被拦截 ({len(limit_ups)} 只):")
    for _, r in limit_ups.head(15).iterrows():
        print(f"  {r['symbol']} {str(r['display_name'])[:8]:<10} "
              f"price={r['latest_price']:>7.2f} prev={r['prev_close']:>7.2f} "
              f"limit={r['up_limit_price']:>7.2f} pct={r['pct_change']:>+6.1f}%")

    print()
    st_stocks = merged[merged["is_st"]].sort_values("probability", ascending=False)
    print(f"## ST/退市风险 被拦截 ({len(st_stocks)} 只):")
    for _, r in st_stocks.iterrows():
        print(f"  {r['symbol']} {str(r['display_name'])[:10]:<12} "
              f"price={r['latest_price']:>7.2f} prob={r['probability']:.4f}")

    # --- SAVE INSPECTION CSV ---
    out = merged[[
        "symbol", "display_name", "probability", "latest_price", "prev_close",
        "pct_change", "high_asof_1457", "low_asof_1457", "vol_snap", "amt_snap",
        "up_limit_price", "board_limit_pct",
        "is_st", "is_suspended", "is_limit_up", "price_abnormal", "tradable",
        "invalid_reason", "turnover_missing",
        "unavailable_feature_count", "approximated_feature_count", "fallback_feature_count",
        "feature_mode", "universe_tag",
    ]].copy()
    out = out.rename(columns={"display_name": "name"})
    out = out.sort_values("probability", ascending=False).reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    out["output_type"] = "inspection_only"
    out["valid_for_trading"] = False
    out.to_csv(INSPECTION_OUT, index=False, encoding="utf-8-sig")
    print(f"\nInspection CSV: {INSPECTION_OUT}")

    # --- SAVE AUDIT JSON ---
    audit = {
        "generated_at": datetime.now().isoformat(),
        "run_type": "post_1457_rescue",
        "raw_scored_count": raw_scored_count,
        "threshold": THRESHOLD,
        "threshold_passed_count": threshold_passed_count,
        "tradability_gate_passed_count": tradability_gate_passed_count,
        "final_candidate_count": final_candidate_count,
        "failed_gate_reasons": {
            "st_or_risk_count": st_count,
            "suspended_or_no_volume_count": suspended_count,
            "limit_up_or_near_limit_count": limit_up_count,
            "price_abnormal_count": price_abnormal_count,
        },
        "turnover_missing_count": turnover_missing_count,
        "conclusion": "当前不产生正式候选。short_only=False + turnover全缺失 + 概率分布异常。仅工程诊断。",
        "probability_anomaly": {
            "min": float(merged["probability"].min()),
            "median": float(merged["probability"].median()),
            "max": float(merged["probability"].max()),
            "unique_values": int(merged["probability"].nunique()),
            "all_above_threshold": bool((merged["probability"] >= THRESHOLD).all()),
            "root_cause": "short_only=False使全池无差别评分; turnover缺失导致feature分布偏移; isotonic calibration阶梯效应",
        },
    }
    with open(AUDIT_OUT, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)
    print(f"Audit JSON: {AUDIT_OUT}")


if __name__ == "__main__":
    main()
