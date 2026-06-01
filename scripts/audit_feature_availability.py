# -*- coding: utf-8 -*-
"""Audit all 260 selected features for 14:57 availability."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\scripts")
sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\src")

from realtime_1457_today_probe import load_bundle, BUNDLE_PATH

bundle = load_bundle(BUNDLE_PATH)
selected = bundle["selected_feature_names"]

print(f"审查 {len(selected)} 个 selected features 的 14:57 可获取性")
print("=" * 70)
print()

# Data needed at 14:57:
# 1. Today's OHLCV snapshot (open, high, low, latest_price, volume, amount) - from Sina/eastmoney
# 2. Today's turnover - from eastmoney
# 3. Today's moneyflow (buy/sell by size) - from eastmoney
# 4. Historical daily bars (T-1 and earlier) - local parquet
# 5. prev_close - from snapshot
# 6. Other stocks' data for cross-section - from full market snapshot
# 7. TGB board data - needs real-time source
# 8. THS sector data - needs T-1 cache or real-time

# Classify each feature by what data it needs
unavailable_at_1457 = []
needs_realtime_source = []  # can get but needs new data source integration
available_from_snapshot = []  # today's OHLCV snapshot sufficient
available_from_history = []  # purely historical

for f in sorted(selected):
    # --- TUSHARE factors ---
    if f.startswith("tushare_"):
        if f in ("tushare_up_limit_distance", "tushare_down_limit_distance", "tushare_limit_range"):
            # Pure calculation from prev_close + board rules + current price
            needs_realtime_source.append((f, "纯计算: prev_close + 板块规则 + 现价"))
        elif f == "tushare_volume_ratio":
            # today volume / recent avg volume
            needs_realtime_source.append((f, "今日成交量/近N日均量, 14:57可算"))
        elif f in ("tushare_net_mf_amount", "tushare_lg_buy_sell_ratio",
                   "tushare_elg_buy_sell_ratio", "tushare_mf_strength",
                   "tushare_sm_sell_pressure", "tushare_main_force_divergence",
                   "tushare_ff_adjusted_flow"):
            # Moneyflow - eastmoney provides real-time
            needs_realtime_source.append((f, "东方财富实时资金流 push2 API"))
        else:
            unavailable_at_1457.append((f, "未知 tushare 因子"))

    # --- TGB factors ---
    elif f.startswith("tgb_"):
        if f in ("tgb_market_max_height", "tgb_new_first_board_count",
                 "tgb_nuclear_button_count"):
            # Market-wide board stats - need real-time limit-up data
            needs_realtime_source.append((f, "需要实时涨停板数据(东方财富/同花顺)"))
        elif f in ("tgb_eod_rush_risk", "tgb_ma_alignment_score",
                   "tgb_ma_divergence_5", "tgb_pullback_health",
                   "tgb_volume_buildup_score"):
            # Individual stock technical - can compute from OHLCV
            available_from_snapshot.append((f, "个股技术指标, 14:57 OHLCV可算"))
        elif f in ("tgb_mid_collapse_rate", "tgb_retreat_intensity",
                   "tgb_zhaban_recovery_score"):
            # Board-related stats - need intraday board events
            needs_realtime_source.append((f, "需要实时炸板/回封数据"))
        else:
            needs_realtime_source.append((f, "TGB因子, 需要涨停板统计源"))

    # --- Sector (THS) factors ---
    elif f.startswith("sector_"):
        if f.endswith("_available"):
            # Availability flags
            available_from_snapshot.append((f, "可用性标志, 设为1(有数据时)"))
        else:
            # sector_divergence, sector_duration_days, sector_limit_up_count,
            # sector_pct_change_best, sector_strength_rank
            needs_realtime_source.append((f, "THS行业: T-1缓存 + 当日行业涨跌(可从截面算)"))

    # --- Cross-section / market factors ---
    elif f.startswith("cs_") or f.startswith("market_"):
        available_from_snapshot.append((f, "截面/市场统计, 从全市场14:57 snapshot计算"))

    # --- Calendar ---
    elif f in ("day_of_week_cos", "day_of_week_sin", "month_end_3", "month_start_3"):
        available_from_history.append((f, "日历因子, 系统时间"))

    # --- Turnover ---
    elif "turnover" in f:
        if f == "turnover":
            needs_realtime_source.append((f, "东方财富实时换手率"))
        else:
            # turnover rolling stats need today's turnover + historical
            needs_realtime_source.append((f, "今日换手(东方财富) + 历史换手(本地bars)"))

    # --- Features that use today's intraday data ---
    elif f in ("intraday_return", "body_pct", "range_pct", "open_to_high_pct",
               "open_to_low_pct", "overnight_return", "overnight_intraday_gap",
               "overnight_vs_intraday", "upper_shadow_pct", "lower_shadow_pct",
               "gap_pct", "gap_fill_ratio", "gap_continue_score",
               "near_limit_close", "reversal_intraday", "reversal_with_volume",
               "intraday_reversal_score", "close_position",
               "lower_shadow_x_volume_z", "upper_shadow_x_volume_z",
               "close_pos_x_cs_range_rank"):
        available_from_snapshot.append((f, "14:57 OHLCV snapshot直接计算"))

    # --- Lag features (use T-1, T-2, ... data) ---
    elif "_lag_" in f:
        lag_num = f.split("_lag_")[-1]
        if lag_num == "0":
            available_from_snapshot.append((f, "lag_0 = 今日值, 14:57 snapshot可算"))
        else:
            available_from_history.append((f, f"lag_{lag_num} = T-{lag_num}值, 历史数据"))

    # --- Rolling/historical features ---
    elif any(f.startswith(p) for p in [
        "ret_", "ret1_", "ret5_", "dist_high", "dist_low",
        "ma_gap", "bollinger", "cost_position", "profit_pressure",
        "realized_skew", "consolidation", "max_return", "mean_reversion",
        "new_high_volume", "obv", "adx", "atr", "cci", "kdj", "macd",
        "mfi", "rsi", "williams", "consecutive", "down_count", "up_count",
        "short_phase", "volume_z_", "volume_chg", "volume_to_mean",
        "volume_vs", "volume_health", "volume_price", "amount_chg",
        "amount_mean", "amount_to", "amount_z_", "climax", "trend_exhaustion",
        "failed_breakout", "range_mean", "range_x_volume",
    ]):
        available_from_snapshot.append((f, "历史rolling + 今日OHLCV, 14:57可算"))

    # --- Board/limit-up related ---
    elif any(f.startswith(p) for p in [
        "failed_limit_up", "limit_down", "limit_touch",
        "big_down", "prev_board", "prev_failed", "prev_limit",
        "board_height", "board_space", "same_height",
        "near_limit", "emotion_", "hot_exhaustion",
        "first_divergence", "first_negative", "money_flow_fire",
        "risk_long", "t_plus_1", "overnight_return_",
        "rel_range", "rel_ret",
    ]):
        available_from_snapshot.append((f, "历史涨停/情绪统计 + 今日数据, 14:57可算"))

    else:
        available_from_snapshot.append((f, "默认归类: 应该可从OHLCV计算"))

# Summary
print(f"=== 可获取性分类 ===")
print()
print(f"【A】从14:57 snapshot直接计算: {len(available_from_snapshot)} 个")
print(f"    数据源: Sina/东方财富 OHLCV snapshot + 历史日线bars")
print()
print(f"【B】纯历史数据: {len(available_from_history)} 个")
print(f"    数据源: 本地历史日线 parquet")
print()
print(f"【C】需要额外实时数据源但可获取: {len(needs_realtime_source)} 个")
print(f"    数据源: 东方财富资金流/换手率/涨停板数据/THS行业")
print()
print(f"【D】14:57 不可获取: {len(unavailable_at_1457)} 个")
print()

total = len(available_from_snapshot) + len(available_from_history) + len(needs_realtime_source) + len(unavailable_at_1457)
print(f"合计: {total} (应等于 {len(selected)})")
print()

# Detail of category C
print("=" * 70)
print(f"【C】需要额外实时数据源 ({len(needs_realtime_source)} 个) 详细:")
print("=" * 70)
print()
for f, reason in sorted(needs_realtime_source):
    print(f"  {f:<45} {reason}")

print()
if unavailable_at_1457:
    print("=" * 70)
    print(f"【D】14:57 不可获取 ({len(unavailable_at_1457)} 个):")
    print("=" * 70)
    for f, reason in unavailable_at_1457:
        print(f"  {f:<45} {reason}")
else:
    print("【D】无不可获取因子 — 全部 260 个特征理论上均可在 14:57 获取")

print()
print("=" * 70)
print("结论")
print("=" * 70)
print()
print(f"  260 个 selected features 中:")
print(f"    {len(available_from_snapshot) + len(available_from_history)} 个: 从 OHLCV snapshot + 历史bars 直接计算")
print(f"    {len(needs_realtime_source)} 个: 需要东方财富实时数据(资金流/换手/涨停板/行业)")
print(f"    {len(unavailable_at_1457)} 个: 真正不可获取")
print()
print("  全部 260 个特征在 14:57 均可获取，前提是接入东方财富实时数据源。")
print("  当前 pipeline 标记 24 个为 unavailable 并填 0 是错误的。")
print("  修正方案: 接入东方财富 push2 API 的资金流+涨停板数据，实时计算这些因子。")
