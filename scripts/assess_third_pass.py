"""
Third pass: human-level strict review of 289 candidates.
Applies hard blacklist + field-alias detection + future-variable check +
concept-duplicate expansion + formula-minimality requirement.
OUTPUT ONLY - does NOT modify factor_registry.
"""
import json
import re
import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\zzzzzzl\Desktop\subagent\src")
from ashare_similarity.prediction.gpu_probe import (
    GPU_PROBE_FEATURES, GPU_PROBE_STABLE_FEATURES,
    GPU_PROBE_RESEARCH_FEATURES
)
from ashare_similarity.prediction.free_data_factors import (
    BOARD_STRUCTURE_COLUMNS, MARKET_EMOTION_COLUMNS, TUSHARE_FACTOR_COLUMNS
)

ASSESSMENT_PATH = r"C:\Users\zzzzzzl\Desktop\subagent\scripts\_assessment_429_strict.json"
REGISTRY_PATH = r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json"


def normalize_name(name):
    n = name.lower().strip()
    n = re.sub(r"[^a-z0-9_]", "_", n)
    n = re.sub(r"_+", "_", n)
    return n.strip("_")


all_impl_raw = (set(GPU_PROBE_FEATURES) | set(GPU_PROBE_STABLE_FEATURES) |
                set(GPU_PROBE_RESEARCH_FEATURES) | set(TUSHARE_FACTOR_COLUMNS) |
                set(BOARD_STRUCTURE_COLUMNS) | set(MARKET_EMOTION_COLUMNS))
all_impl_norm = set(normalize_name(f) for f in all_impl_raw)

# ============================================================
# HARD BLACKLIST (user-specified + prior reject/defer)
# ============================================================
HARD_BLACKLIST = {
    "limit_up_count_market", "today_limit_up", "closed_limit_up",
    "final_close", "peak_price", "z_t", "limit_up_with_volume",
    "sector_batch_limit_effect", "second_board_confirm_leader",
    "opening_seal_speed", "asking_chase_half_position",
    "name_geography_mysticism", "solo_stock_direction_hint",
    "position_stock_signal", "echelon_position_battle",
    "node_second_board_fault_tolerance", "board_keep_break_rule",
    "chip_reflexivity",
}

# ============================================================
# FIELD ALIASES: raw_text is just `x = stock.field` or trivial rename
# ============================================================
FIELD_ALIAS_PATTERNS = [
    r"^current_price$", r"^current_gain$", r"^daily_volume$",
    r"^real_body$", r"^gap$", r"^vol_ratio$",
    r"^limitup_count$", r"^limitup_premium$",
    r"^target$", r"^confidence$",
    r"^hot_buy$", r"^bt_volume$", r"^next_day_volume$",
]

FIELD_ALIAS_RAW_PATTERNS = [
    # Patterns like "x = stock.something" without real computation
    r"^\w+ = stock\.\w+$",
    r"^\w+ = market_data\.\w+\s*(#.*)?$",
]

# ============================================================
# FUTURE VARIABLES
# ============================================================
FUTURE_KEYWORDS = [
    "next_day", "next_open", "next_close", "next_high",
    "tomorrow", "future_return", "t+1_", "t_plus_1",
    "after_limit",  # min price AFTER limit-up = future
    "after_breakout",  # volume AFTER breakout = future
]

# ============================================================
# TRADING STRATEGY / POSITION MANAGEMENT (expanded)
# ============================================================
STRATEGY_REJECT_NAMES = [
    "chase_only_when_market_up", "leader_timing_not_size",
    "no_20cm_board", "board_keep_break_rule",
    "zt_count_position_mapping", "node_second_board_fault_tolerance",
    "demon_stock_relaunch_timing", "sell_price_vs_close",
    "lurking_capital_trap", "repair_anchor_logic",
    "supplement_rise_node", "absolute_height_highlow_cut",
    "height_determines_direction", "first_divergence_type",
    "midcap_supplement_prob", "potential_outside_buy",
    "ipo_open_board_entry",  # trading action: "buy on first open board day"
]

STRATEGY_CN_EXTENDED = [
    "追涨需", "追涨操作", "打板策略", "买入目标", "卖点",
    "操作框架", "保容错", "锚定逻辑", "介入时机", "资金陷阱",
    "回避标记", "回避", "不碰",
]

# ============================================================
# CONCEPT DUPLICATES (expanded beyond name matching)
# ============================================================
CONCEPT_DUP_MAP = {
    # norm_name: (existing_concept, reason)
    "limitup_count": ("market_limit_up_count", "field alias"),
    "limitup_premium": ("prev_limit_up_premium", "field alias"),
    "vol_ratio": ("volume_ratio", "field alias: today_vol/avg_5d already exists"),
    "volume_change": ("volume_vs_prev", "formula equivalent (volume change ratio)"),
    "current_gain": ("pct_change", "trivial: (price-pre_close)/pre_close = pct_change"),
    "real_body": ("body_pct", "trivial: abs(close-open), candle body size"),
    "daily_volume": ("amount/volume", "raw field, not a derived factor"),
    "market_avg_height": ("market_avg_board_height", "likely same as existing avg height"),
    "max_consecutive_board_height": ("market_max_board_height", "same concept: max board height"),
    "seal_time_factor": ("seal_time", "already in stable: seal time feature"),
    "seal_time_distribution": ("seal_time", "variant of seal_time"),
    "seal_ratio_factor": ("seal_money_to_float_mv", "seal ratio = seal_money/amount, equivalent"),
    "seal_ratio_score": ("seal_money_to_float_mv", "scored version of seal ratio"),
    "huifeng_quality": ("board_open_count + seal_money", "composite of existing seal quality features"),
    "sector_followup_count": ("sector_limit_up_count", "same concept minus self"),
    "bidding_limit_count": ("auction features", "needs auction data, likely exists"),
    "avg_gap": ("prev_limit_up_premium", "yesterday limit-up avg open gap = premium"),
    "total_amount": ("amount", "trivial: sum of existing amount field over lookback"),
    "total_volume": ("volume", "trivial: sum of existing volume field over lookback"),
    "avg_cost": ("vwap / avg_price", "trivial: total_amount/total_volume = avg_price already exists"),
    "close_to_limit": ("pct_change", "trivial: (close-prev_close)/prev_close = pct_change"),
    "vol_declining": ("volume_vs_prev", "volume < 0.7 * avg = volume_vs_prev threshold"),
    "price_new_high_5d": ("high_pct_5d or similar", "trivial: close >= max(high, 5d)"),
    "price_new_low_5d": ("low_pct_5d or similar", "trivial: close <= min(low, 5d)"),
    "volume_falling": ("volume_vs_prev", "volume at highs declining = volume_vs_prev variant"),
    "open_pct": ("open_pct_change or auction features", "needs auction price_925, not pure daily"),
    "vol_trend": ("volume_vs_prev", "categorical version of volume trend (uses auction 9:22/9:24)"),
    "night_change": ("cross_market", "needs overnight/night session data (not A-share daily)"),
    "short_balance_ratio": ("margin data", "needs margin_detail API (not daily_ohlcv)"),
    "net_sell": ("shareholder data", "needs reduce/increase amount (not daily_ohlcv)"),
    "quant_sector_weight": ("sector_turnover_ratio", "sector_turnover/market_turnover trivial ratio"),
    "wti_close_change": ("cross_market", "cross-market oil futures, excluded from expanded"),
    "news_surge_t": ("external NLP", "needs news volume data, not market data"),
}

# ============================================================
# L2/TICK/INTRADAY disguised as daily
# ============================================================
L2_DISGUISED = [
    "quant_fake_seal_detection",  # needs tick to detect "秒撤"
    "attack_volume",  # explicitly P3 = needs L2 in source doc
    "volume_during_open",  # needs intraday segmentation
    "pulse_volume_signal",  # "开盘30分钟" = needs minute bars
    "multi_seat_score",  # needs LHB seat-level data (actually lhb, not daily)
    "sell_cancel_rate",  # uses stock_l2.sell_cancel_amount = Level2
    "buy_cancel_rate",  # uses stock_l2.buy_cancel_amount = Level2
    "drop_volume",  # "5分钟" needs minute bars
    "late_chase_volume",  # "last 30m / first 30m" needs minute bars
    "expected_open_volume",  # context is 排板(queue-board) = L2
    "known_amount",  # needs LHB seat-level identity data
]

# ============================================================
# VAGUE / SUBJECTIVE / CATEGORICAL (can't produce numeric factor)
# ============================================================
VAGUE_REJECT = [
    "sector_first_board_attr",  # categorical: "独苗/板块效应/蹭热点"
    "board_echelon_city_cluster",  # needs geographic metadata
    "quant_eruption_signal",  # "量化起爆" undefined criterion
    "quant_oscillation_stock",  # "大涨一天跌一天" too simplistic
    "super_theme_settlement_days",  # "沉淀期" hard to compute start/end
    "themed_sub_ipo",  # "次新+热点叠加" vague interaction
    "new_ipo_opening_drain",  # "新股开板资金分流" causal narrative
    "position_uniqueness",  # "唯一的20cm二连板" very specific rare event
    "target",  # selection criterion description, not a factor
    "sibling_stock_signal",  # needs corporate relationship data
    "stock_personality_history",  # vague composite "股性评分"
    "feature_i",  # generic variable name, not a specific factor
    "composite",  # cross-market composite (a50+us+hk), already excluded
    "Buy_Signal",  # trading signal, not a factor
    "passed",  # boolean based on undefined "left_pressure_price"
    "close_back",  # trivial: close > open or close > prev_close
    "recovering",  # needs intraday 13:30 data point
    "is_algo_heavy",  # needs algo detection model (not available)
]

# ============================================================
# FORMULA MINIMALITY: raw_text must contain at least a 2-operand operation
# ============================================================
def has_real_formula(raw_text, name):
    """Check if raw_text contains a genuine 2+ operand computation."""
    text = raw_text.strip()

    # Pattern: "x = stock.field" → no computation
    if re.match(r'^[\w_]+ = stock\.[\w_]+\s*(#.*)?$', text):
        return False
    # Pattern: "x = market_data.field" → no computation
    if re.match(r'^[\w_]+ = market_data\.[\w_]+\s*(#.*)?$', text):
        return False
    # Pattern: "x = some_function()" with no visible formula
    if re.match(r'^[\w_]+ = [\w_]+\(\)\s*(#.*)?$', text):
        return False
    # Very short with just a name
    if len(text) < 20 and "=" not in text and "/" not in text and "比" not in text and "率" not in text:
        return False
    # Just "Factor NNN: `name` - Chinese title"
    if re.match(r'^Factor \d+: `[\w_]+`\s*-\s*.+$', text):
        # Only title, no formula
        if "/" not in text and "比" not in text and "率" not in text and "数" not in text:
            return False
    # Has at least one arithmetic/comparison/aggregation operator
    operators = ["/", "*", "+", "-", ">", "<", ">=", "<=", "==",
                 "mean(", "sum(", "count(", "max(", "min(", "std(",
                 "ratio", "率", "比", "÷"]
    # Must have operator AND at least two distinct variable references
    has_op = any(op in text for op in operators)
    # Count distinct variable-like tokens
    vars_in_text = re.findall(r'[a-z_]{3,}', text.lower())
    distinct_vars = len(set(vars_in_text))

    return has_op and distinct_vars >= 2


def third_pass(candidate):
    """
    Apply all hard rules. Returns (decision, reason, detail).
    """
    name = candidate["factor_name"]
    norm = candidate["normalized_name"]
    raw_text = candidate["raw_text"]

    # 1. Hard blacklist
    if norm in HARD_BLACKLIST:
        return "reject", "hard_blacklist", f"Previously rejected/deferred: {norm}"

    # 2. Field alias (name patterns)
    for pat in FIELD_ALIAS_PATTERNS:
        if re.match(pat, norm):
            return "reject", "field_alias", f"Name matches trivial field pattern: {pat}"

    # 3. Concept duplicate map
    if norm in CONCEPT_DUP_MAP:
        existing, reason = CONCEPT_DUP_MAP[norm]
        return "reject", "concept_duplicate_expanded", f"{existing}: {reason}"

    # 4. Future variable
    text_lower = (name + " " + raw_text).lower()
    for kw in FUTURE_KEYWORDS:
        if kw in text_lower:
            return "reject", "future_variable", f"Contains future reference: {kw}"

    # 5. Trading strategy (name-based)
    if norm in [normalize_name(n) for n in STRATEGY_REJECT_NAMES]:
        return "reject", "trading_strategy_expanded", f"Trading action/strategy description"

    # 5b. Trading strategy (CN patterns in raw_text)
    for pat in STRATEGY_CN_EXTENDED:
        if pat in raw_text:
            return "reject", "trading_strategy_cn", f"CN trading pattern: {pat}"

    # 6. L2/tick disguised as daily
    if norm in [normalize_name(n) for n in L2_DISGUISED]:
        return "reject", "l2_disguised_as_daily", f"Requires intraday/tick/LHB despite daily label"

    # 7. Vague/subjective/categorical
    if norm in [normalize_name(n) for n in VAGUE_REJECT]:
        return "reject", "vague_categorical", f"Categorical output or undefined criterion"

    # 8. Formula minimality check
    if not has_real_formula(raw_text, name):
        return "defer", "no_real_formula", f"raw_text lacks 2-operand computation: '{raw_text[:60]}'"

    # 9. Additional concept/data checks for false positives
    # Cross-market factors
    cross_names = ["eu_close_return", "vix_close", "vix_change", "hsi_close",
                   "hsi_afternoon_session", "wti_close_change"]
    if norm in cross_names:
        return "defer", "cross_market_excluded", f"Cross-market factor, excluded from expanded pool"

    # Needs minute bars / intraday
    minute_names = ["max_5min_volume", "attack_quality", "down_vol",
                    "late_chase_volume", "recovering", "drop_volume"]
    if norm in minute_names:
        return "reject", "needs_minute_bars", f"Requires 5-min/intraday data"

    # Needs L2 / special data (not daily OHLCV)
    special_data = ["quant_crowding", "buy_sell_imbalance", "large_trade_ratio",
                    "signedvolume", "volume_zscore",
                    "mbr", "nb_flow", "insider_net_i",
                    "style_embedding_distance", "z_cn", "ind_crowd_j"]
    if norm in special_data:
        return "reject", "needs_special_data", f"Requires margin/northbound/insider/fundamental/ML data"

    # Underdefined variables (formula references unavailable fields)
    underdefined = ["vacuum_ratio", "breakout_gain", "breakout_amount",
                    "second_break", "nuclear_ratio", "price_vs_cost",
                    "step2_pass", "weak_to_strong_volume_efficiency"]
    # But nuclear_ratio IS potentially computable, let's keep it
    # price_vs_cost IS computable as close vs weighted avg cost
    careful_defer = ["vacuum_ratio", "breakout_gain", "breakout_amount",
                     "second_break", "step2_pass",
                     "weak_to_strong_volume_efficiency"]
    if norm in careful_defer:
        return "defer", "underdefined_variables", f"Formula references fields not available from standard data"

    # Concept duplicates: open_board_rate = 1 - seal_rate
    if norm == "open_board_rate":
        return "reject", "concept_duplicate_expanded", "complement of seal_rate_80_threshold (1 - seal_rate)"
    if norm == "premiums":
        return "reject", "concept_duplicate_expanded", "time series of prev_limit_up_premium (already exists)"
    if norm in ("board_effect_required", "no_20cm_board"):
        return "reject", "trading_strategy_expanded", "Trading rule / avoidance criterion"
    if norm == "strong_pool_reason":
        return "defer", "categorical_text", "Reason string from API, not numeric"
    if norm in ("residual",):
        return "defer", "underdefined_variables", "ETF residual needs ETF price decomposition model"

    # 10. Additional substring duplicate check against implemented features
    # (stricter: check if the core concept word is in any implemented feature)
    core_words = set(re.findall(r'[a-z]{5,}', norm))
    for impl in all_impl_norm:
        impl_words = set(re.findall(r'[a-z]{5,}', impl))
        # If 2+ significant words overlap, likely duplicate
        overlap = core_words & impl_words
        if len(overlap) >= 2 and any(len(w) >= 6 for w in overlap):
            return "reject", "word_overlap_implemented", f"Core words {overlap} overlap with {impl}"

    # Passed all checks
    return "promote", "passes_third_pass", None


def main():
    with open(ASSESSMENT_PATH, "r", encoding="utf-8") as f:
        assessment = json.load(f)

    candidates = assessment["promote"]  # 289 from second pass
    print(f"Input: {len(candidates)} candidates from second-pass promote")

    results = {"promote": [], "reject": [], "defer": []}

    for c in candidates:
        decision, reason, detail = third_pass(c)
        c["_r3_decision"] = decision
        c["_r3_reason"] = reason
        c["_r3_detail"] = detail
        results[decision].append(c)

    print(f"\n=== THIRD PASS RESULTS ===")
    print(f"  promote: {len(results['promote'])}")
    print(f"  reject:  {len(results['reject'])}")
    print(f"  defer:   {len(results['defer'])}")

    print(f"\nRejection reasons:")
    for k, v in Counter(c["_r3_reason"] for c in results["reject"]).most_common():
        print(f"  {k}: {v}")

    print(f"\nDeferral reasons:")
    for k, v in Counter(c["_r3_reason"] for c in results["defer"]).most_common():
        print(f"  {k}: {v}")

    # Show promoted candidates (safe print)
    print(f"\n=== PROMOTED ({len(results['promote'])}) ===")
    for i, c in enumerate(results["promote"]):
        safe_raw = c['raw_text'][:100].encode('ascii', 'replace').decode('ascii')
        print(f"  {i+1:3d}. {c['factor_name']:45s} [{c['raw_factor_id']}] score={c['score']}")
        print(f"       raw: {safe_raw}")
        print()

    # Save full results
    output = {
        "input_count": len(candidates),
        "promote_count": len(results["promote"]),
        "reject_count": len(results["reject"]),
        "defer_count": len(results["defer"]),
        "promote": [{
            "rank": c["rank"],
            "raw_factor_id": c["raw_factor_id"],
            "factor_name": c["factor_name"],
            "normalized_name": c["normalized_name"],
            "data_needs": c["data_needs"],
            "asof_time": c["asof_time"],
            "priority": c["priority"],
            "score": c["score"],
            "raw_text": c["raw_text"],
            "section": c.get("section", ""),
            "source_file": c.get("source_file", ""),
            "source_line": c.get("source_line", 0),
        } for c in results["promote"]],
        "reject": [{
            "rank": c["rank"],
            "factor_name": c["factor_name"],
            "reason": c["_r3_reason"],
            "detail": c["_r3_detail"],
            "raw_text": c["raw_text"][:100],
        } for c in results["reject"]],
        "defer": [{
            "rank": c["rank"],
            "factor_name": c["factor_name"],
            "reason": c["_r3_reason"],
            "detail": c["_r3_detail"],
            "raw_text": c["raw_text"][:100],
        } for c in results["defer"]],
    }

    out_path = r"C:\Users\zzzzzzl\Desktop\subagent\scripts\_assessment_third_pass.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
