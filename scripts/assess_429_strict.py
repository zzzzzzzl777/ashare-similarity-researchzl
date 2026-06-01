"""
Strict second-pass assessment of 429 candidates.
Much tighter than first pass: catches order-book/L2 factors, vague lifecycle concepts,
simple universe filters, and concept-level duplicates missed by name matching.
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

REGISTRY_PATH = r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json"
Q500_PATH = r"E:\ashare_similarity_runtime\data\reports\prediction\raw_to_registry_review_queue_500_20260506.json"

all_impl_raw = (set(GPU_PROBE_FEATURES) | set(GPU_PROBE_STABLE_FEATURES) |
                set(GPU_PROBE_RESEARCH_FEATURES) | set(TUSHARE_FACTOR_COLUMNS) |
                set(BOARD_STRUCTURE_COLUMNS) | set(MARKET_EMOTION_COLUMNS))


def normalize_name(name):
    n = name.lower().strip()
    n = re.sub(r"[^a-z0-9_]", "_", n)
    n = re.sub(r"_+", "_", n)
    return n.strip("_")


all_impl_norm = set(normalize_name(f) for f in all_impl_raw)


def load_registry_data():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
    cid_pattern = re.compile(r"^C\d{3}$")
    names = {}
    definitions = {}
    for batch_key in registry["meta"]["candidate_batches"]:
        batch = registry[batch_key]
        entries = []
        if "detail" in batch and isinstance(batch["detail"], list):
            entries.extend(batch["detail"])
        for pkey in ["p0", "p1", "p2", "blocked"]:
            if pkey in batch and isinstance(batch[pkey], list):
                entries.extend(batch[pkey])
        for c in entries:
            if not isinstance(c, dict):
                continue
            fid = c.get("factor_id")
            if not fid or not cid_pattern.match(str(fid)):
                continue
            name = c.get("name", "")
            if name:
                norm = normalize_name(name)
                names[norm] = fid
                defn = c.get("computable_definition", "")
                if defn:
                    definitions[norm] = defn.lower()
    return names, definitions


# ============ REJECTION CATEGORIES ============

# L2 / Order book / Tick data indicators
L2_PATTERNS = [
    "ask_slope", "bid_slope", "visible_bid", "visible_ask",
    "actual_buy_volume", "actual_sell_volume", "hidden_ratio",
    "ofi", "order_flow_imbalance", "normalized_ofi",
    "depth", "order_book", "bid_ask", "bid_volume", "ask_volume",
    "buy_volume", "sell_volume", "trade_direction",
    "vpin", "tick_", "microstructure", "tick_imbalance",
    "order_count", "order_size", "trade_count",
    "aggressor", "passive_", "active_",
    "level2", "l2_", "quote_", "spread_",
    "large_order", "small_order", "medium_order",
    "institutional_order", "retail_order",
    "iceberg", "hidden_order", "dark_pool",
]

L2_CN_PATTERNS = [
    "盘口", "委托", "买一", "卖一", "十档", "五档",
    "逐笔", "主动买", "主动卖", "大单", "小单", "中单",
    "超大单", "委买", "委卖", "挂单", "撤单",
    "机构单", "散户单", "量化单",
]

# Trading strategy / Position management (NOT market factors)
STRATEGY_PATTERNS = [
    "half_position", "full_position", "position_size",
    "stop_loss", "take_profit", "entry_", "exit_",
    "chase_half", "chase_full", "guard_position",
    "dynamic_stop", "trailing_stop",
]

STRATEGY_CN_PATTERNS = [
    "半仓", "全仓", "仓位", "加仓", "减仓", "止损", "止盈",
    "建仓", "清仓", "持仓", "打板策略", "排板策略",
    "做T", "高抛低吸策略",
]

# NLP / Text / Subjective / Mysticism
NLP_PATTERNS = [
    "name_geography", "mysticism", "hint_direction",
    "text_signal", "news_sentiment", "title_keyword",
    "nlp_", "language_model", "gpt_", "bert_",
    "solo_stock_direction_hint", "position_stock_signal",
]

NLP_CN_PATTERNS = [
    "名字", "谐音", "语料", "暗示方向", "玄学", "地域暗示",
    "名称暗示", "文本分析", "舆情",
]

# Universe filters (not predictive factors)
FILTER_PATTERNS = [
    "min_daily_volume", "min_amount", "min_market_cap",
    "max_price", "min_price", "is_st", "is_new",
]

FILTER_CN_PATTERNS = [
    "最低日成交", "最低流通", "最低市值",
]

# Vague lifecycle / stage concepts that can't be precisely computed
VAGUE_PATTERNS = [
    "lifecycle_stage", "theme_lifecycle", "lifecycle",
    "market_regime", "regime_detection",
    "sustainability_score", "continuation_prob",
    "survival_", "probability_model",
]

# Cross-market factors (already excluded from expanded pool via cross_ prefix)
CROSS_MARKET_PATTERNS = [
    "hk_close", "hk_return", "us_close", "us_return",
    "global_", "overseas_", "foreign_market",
    "sp500", "nasdaq", "dow_jones", "nikkei", "ftse",
]

# Generic/Trivial factors that are just existing feature renames
TRIVIAL_DUPLICATES = {
    "sector_batch_limit_effect": "sector_limit_up_count (same concept: sector limit-up count threshold)",
    "sector_followup_count": "sector_limit_up_count - 1 (count excluding self)",
    "is_sector_leader": "sector_strength_rank == 1 (binary from existing rank)",
    "dragon_head_flag": "sector_strength_rank == 1 (same as is_sector_leader)",
    "sector_momentum_1d": "sector_pct_change (existing sector return)",
    "sector_momentum_rank": "sector_strength_rank (existing)",
    "min_daily_volume_300m": "universe filter, not predictive factor",
    "dynamic_volume_comparison": "volume_ratio variants already exist (volume_vs_prev, etc)",
    "quant_next_day_cash": "quant-surge undefined criterion",
    "volume_price_health": "vague composite without clear formula",
    "success_prob": "needs seal_order_queue (L2)",
    "sector_leader_return": "sector_pct_change_best (existing: best sector return)",
    "index_component_return": "sector_pct_change (index return already available)",
    "concept_count_hot": "overlaps hot_rank / sector features",
    "sector_rotation_signal": "sector_duration_days / sector_climax_signal (existing rotation indicators)",
}


def classify_candidate(c, registry_names, registry_defs):
    """
    Strictly classify a candidate.
    Returns (decision, reason_code, reason_detail)
    """
    name = c["factor_name"]
    norm = c["normalized_name"]
    raw_text = c["raw_text"]
    data_needs = c["data_needs"]
    text_combined = (name + " " + raw_text).lower()

    # === REJECT: Trivial/concept duplicates (hardcoded from prior review) ===
    if norm in TRIVIAL_DUPLICATES:
        return "reject", "concept_duplicate", TRIVIAL_DUPLICATES[norm]

    # === REJECT: L2 / Order book factors ===
    for pat in L2_PATTERNS:
        if pat in norm or pat in text_combined:
            return "reject", "needs_level2_orderbook", f"pattern: {pat}"
    for pat in L2_CN_PATTERNS:
        if pat in raw_text:
            return "reject", "needs_level2_orderbook", f"CN pattern: {pat}"

    # === REJECT: Trading strategy / position management ===
    for pat in STRATEGY_PATTERNS:
        if pat in norm:
            return "reject", "trading_strategy", f"pattern: {pat}"
    for pat in STRATEGY_CN_PATTERNS:
        if pat in raw_text:
            # Allow if the factor is about measuring market behavior around these concepts
            if any(x in norm for x in ["ratio", "rate", "count", "pct", "strength", "effect"]):
                continue
            return "reject", "trading_strategy", f"CN pattern: {pat}"

    # === REJECT: NLP / Text / Subjective ===
    for pat in NLP_PATTERNS:
        if pat in norm or pat in text_combined:
            return "reject", "requires_nlp_text", f"pattern: {pat}"
    for pat in NLP_CN_PATTERNS:
        if pat in raw_text:
            return "reject", "requires_nlp_text", f"CN pattern: {pat}"

    # === REJECT: Universe filters ===
    for pat in FILTER_PATTERNS:
        if pat in norm:
            return "reject", "universe_filter_not_factor", f"pattern: {pat}"
    for pat in FILTER_CN_PATTERNS:
        if pat in raw_text and "率" not in raw_text and "比" not in raw_text:
            return "reject", "universe_filter_not_factor", f"CN pattern: {pat}"

    # === DEFER: Cross-market (excluded from expanded pool) ===
    for pat in CROSS_MARKET_PATTERNS:
        if pat in norm:
            return "defer", "cross_market_excluded", f"pattern: {pat}; cross_ features excluded from expanded pool"

    # === DEFER: Vague lifecycle/stage concepts ===
    for pat in VAGUE_PATTERNS:
        if pat in norm or pat in text_combined:
            return "defer", "vague_concept", f"pattern: {pat}"

    # === REJECT: Name-based duplicate against registry ===
    if norm in registry_names:
        return "reject", "exact_name_duplicate", f"matches {registry_names[norm]}"
    if len(norm) >= 5:
        for rn, fid in registry_names.items():
            if len(rn) >= 5:
                if norm in rn or rn in norm:
                    return "reject", "substring_name_duplicate", f"overlaps {fid} ({rn})"

    # === REJECT: Name-based duplicate against implemented features ===
    if norm in all_impl_norm:
        return "reject", "implemented_exact", f"exact match in implemented features"
    if len(norm) >= 5:
        for impl in all_impl_norm:
            if len(impl) >= 5:
                if norm in impl or impl in norm:
                    return "reject", "implemented_substring", f"overlaps implemented: {impl}"

    # === DEFER: Very short raw_text with no formula indication ===
    if len(raw_text.strip()) < 15:
        return "defer", "insufficient_raw_text", "raw_text too short to derive formula"

    # === DEFER: No quantifiable operation in raw_text ===
    quant_indicators = ["/", "÷", "×", "*", "+", "-", "=",
                        "ratio", "count", "avg", "mean", "sum", "max", "min", "std",
                        "率", "比", "数", "量", "幅", "差", "指数",
                        ">", "<", ">=", "<=", "排名", "百分位"]
    has_quant = any(x in text_combined for x in quant_indicators)
    if not has_quant:
        # Check if it's at least a binary/flag factor
        flag_indicators = ["是否", "flag", "binary", "bool", "exists",
                          "有无", "判断", "识别", "检测"]
        has_flag = any(x in text_combined for x in flag_indicators)
        if not has_flag:
            return "defer", "no_quantifiable_operation", "no mathematical/logical operation found in description"

    # === Additional concept-level duplicate checks ===
    # Sector return/momentum variants that overlap existing sector features
    if "sector" in norm and any(x in norm for x in ["momentum", "return", "pct", "change", "strength"]):
        existing_sector = [f for f in all_impl_norm if "sector" in f and any(x in f for x in ["pct", "strength", "momentum", "return"])]
        if existing_sector:
            return "reject", "sector_feature_overlap", f"overlaps existing sector features: {existing_sector[:3]}"

    # Board count/height variants
    if norm in ("hardness_three_exists", "three_board_exists", "max_height_three"):
        return "reject", "concept_duplicate", "market_max_board_height >= 3"

    # If passes all checks, promote
    return "promote", "passes_strict_review", None


def derive_entry(c, factor_id):
    """Derive a full registry entry for a promoted candidate."""
    name = c["factor_name"]
    norm = c["normalized_name"]
    raw_text = c["raw_text"]
    data_needs = c["data_needs"]

    # Determine family
    family = "misc"
    if "sector" in norm or "theme" in norm:
        family = "sector_structure"
    elif "board" in norm or "limit" in norm or "seal" in norm:
        family = "board_structure"
    elif "volume" in norm or "turnover" in norm or "amount" in norm:
        family = "volume_structure"
    elif "price" in norm or "return" in norm or "pct" in norm:
        family = "price_structure"
    elif "emotion" in norm or "sentiment" in norm:
        family = "market_emotion"
    elif "leader" in norm or "dragon" in norm:
        family = "leader_factor"
    elif "momentum" in norm or "strength" in norm:
        family = "momentum"
    elif "wave" in norm or "cycle" in norm or "rotation" in norm:
        family = "cycle_factor"
    elif "flow" in norm or "money" in norm:
        family = "capital_flow"
    elif any(x in norm for x in ["ratio", "rate"]):
        family = "ratio_factor"

    # Extract computable definition from raw_text
    definition = raw_text.strip()
    if "|" in definition:
        parts = [p.strip() for p in definition.split("|")]
        parts = [p for p in parts if p and len(p) > 3]
        # Find the description part (usually 3rd column in table format)
        if len(parts) >= 3:
            # Skip factor_name column, take description
            for p in parts[1:]:
                if not p.startswith("`") and len(p) > 10:
                    definition = p
                    break
        elif len(parts) >= 2:
            definition = max(parts, key=len)
    # Truncate to reasonable length
    definition = definition[:300]

    # Data need
    dn_str = ", ".join(data_needs) if data_needs else "unknown"

    # Engineering hint
    if "limit_pool" in data_needs:
        impl_hint = "stock_zt_pool APIs via free_data_factors.py + limit_list_d cache (804 days)"
    elif "sector_theme" in data_needs and "daily_ohlcv" in data_needs:
        impl_hint = "ths_index_member for sector membership + daily OHLCV"
    elif "sector_theme" in data_needs:
        impl_hint = "ths_daily/moneyflow_ind_dc cache for sector features"
    elif "daily_ohlcv" in data_needs:
        impl_hint = "Daily OHLCV from main dataframe (always available)"
    elif "cross_market" in data_needs:
        impl_hint = "index_global cache (804 files)"
    else:
        impl_hint = "Needs investigation"

    # Priority
    priority = c.get("priority", "unknown")
    if priority == "unknown":
        if c.get("score", 0) >= 43:
            priority = "P2"
        else:
            priority = "P3"

    return {
        "factor_id": factor_id,
        "name": name,
        "family": family,
        "source_type": "taoguba",
        "raw_factor_id": c["raw_factor_id"],
        "raw_source_path": c.get("source_file", ""),
        "raw_source_line": c.get("source_line", 0),
        "raw_idea": raw_text[:200],
        "computable_definition": definition,
        "data_need": dn_str,
        "asof_rule": "T-day close" if c.get("asof_time") == "after_close" else c.get("asof_time", "unknown"),
        "leakage_risk": "none",
        "related_existing_features": [],
        "duplicate_check": "Passed name exact+substring against 152 registry + 783 implemented features",
        "engineering_status": "candidate",
        "priority": priority,
        "implementation_hint": impl_hint,
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    }


def main():
    registry_names, registry_defs = load_registry_data()
    print(f"Registry names: {len(registry_names)}")
    print(f"Implemented features: {len(all_impl_norm)}")

    with open(Q500_PATH, "r", encoding="utf-8") as f:
        q = json.load(f)
    candidates = q["candidates"]
    print(f"Candidates to assess: {len(candidates)}")

    promote = []
    reject = []
    defer = []

    for c in candidates:
        decision, reason, detail = classify_candidate(c, registry_names, registry_defs)
        c["_decision"] = decision
        c["_reason"] = reason
        c["_detail"] = detail
        if decision == "promote":
            promote.append(c)
        elif decision == "reject":
            reject.append(c)
        else:
            defer.append(c)

    print(f"\n=== STRICT ASSESSMENT ===")
    print(f"  promote: {len(promote)}")
    print(f"  reject:  {len(reject)}")
    print(f"  defer:   {len(defer)}")

    print(f"\nRejection reasons:")
    for k, v in Counter(c["_reason"] for c in reject).most_common():
        print(f"  {k}: {v}")

    print(f"\nDeferral reasons:")
    for k, v in Counter(c["_reason"] for c in defer).most_common():
        print(f"  {k}: {v}")

    # --- Now do THIRD pass: deduplicate within promote list ---
    # Many raw pool entries describe the same concept under different names
    # Group by normalized_name and keep only one representative per concept
    seen_concepts = set()
    deduped_promote = []
    concept_dups = []

    for c in promote:
        norm = c["normalized_name"]
        # Check if we've already promoted something very similar
        is_dup = False
        for seen in seen_concepts:
            if len(norm) >= 5 and len(seen) >= 5:
                if norm in seen or seen in norm:
                    is_dup = True
                    c["_decision"] = "reject"
                    c["_reason"] = "intra_queue_duplicate"
                    c["_detail"] = f"substring overlap with already-promoted: {seen}"
                    concept_dups.append(c)
                    break
        if not is_dup:
            seen_concepts.add(norm)
            deduped_promote.append(c)

    if concept_dups:
        reject.extend(concept_dups)
        print(f"\n  Intra-queue duplicates removed: {len(concept_dups)}")
        print(f"  Final promote after dedup: {len(deduped_promote)}")

    # Save results
    output = {
        "summary": {
            "total_assessed": len(candidates),
            "promoted": len(deduped_promote),
            "rejected": len(reject),
            "deferred": len(defer),
            "id_range": f"C153-C{152 + len(deduped_promote):03d}" if deduped_promote else "none",
        },
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
        } for c in deduped_promote],
        "reject": [{
            "rank": c["rank"],
            "factor_name": c["factor_name"],
            "reason": c["_reason"],
            "detail": c["_detail"],
        } for c in reject],
        "defer": [{
            "rank": c["rank"],
            "factor_name": c["factor_name"],
            "reason": c["_reason"],
            "detail": c["_detail"],
        } for c in defer],
    }

    out_path = r"C:\Users\zzzzzzl\Desktop\subagent\scripts\_assessment_429_strict.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")
    print(f"Promote ID range: C153-C{152 + len(deduped_promote):03d}")


if __name__ == "__main__":
    main()
