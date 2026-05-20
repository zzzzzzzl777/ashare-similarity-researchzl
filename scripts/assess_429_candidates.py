"""
Batch review of 429 raw-to-registry candidates.
Classifies each as promote/reject/defer based on 8 criteria:
1. Computable (clear formula from market data)
2. Free/available data only
3. Clear asof time, no future function
4. No Level2 requirement
5. Not trading rules / position mgmt / subjective / text-NLP
6. Not duplicate of C001-C152 or 783 implemented features
7. Can write computable_definition
8. Can write data_need, asof_rule, leakage_risk, duplicate_check, implementation_hint
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


def load_registry_names():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
    cid_pattern = re.compile(r"^C\d{3}$")
    names = {}  # name -> factor_id
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
                names[normalize_name(name)] = fid
    return names


# --- REJECTION PATTERNS ---

# Keywords indicating trading strategy / position management (not a factor)
STRATEGY_KEYWORDS = [
    "半仓", "全仓", "仓位", "加仓", "减仓", "止损", "止盈",
    "买入", "卖出", "清仓", "建仓", "持仓", "打板", "排板",
    "追涨", "低吸", "做T", "t+0", "挂单", "委托",
    "half_position", "full_position", "stop_loss", "take_profit",
    "position_size", "entry_signal", "exit_signal",
]

# Keywords indicating NLP / text / subjective / mysticism
NLP_KEYWORDS = [
    "名字", "谐音", "语料", "文本", "暗示", "玄学", "地域",
    "名称", "NLP", "sentiment_text", "news_", "title_",
    "geography", "mysticism", "hint", "name_",
]

# Keywords indicating Level2 / tick data requirement
L2_KEYWORDS = [
    "逐笔", "委托队列", "买一", "卖一", "十档", "level2",
    "tick", "order_book", "bid_ask", "order_flow",
    "盘口", "五档",
]

# Patterns for things that are clearly just reference values, not predictive factors
NON_FACTOR_PATTERNS = [
    r"^today_limit_up$", r"^closed_limit_up$", r"^final_close$",
    r"^peak_price$", r"^z_t$", r"^abull$",
]


def check_strategy(name, raw_text):
    """Check if this is a trading strategy, not a market factor."""
    text = (name + " " + raw_text).lower()
    for kw in STRATEGY_KEYWORDS:
        if kw in text:
            # Some legitimate factors contain these words in context
            # e.g., "seal_order" is not a strategy
            if kw in ("追涨", "打板", "排板") and ("率" in raw_text or "count" in name or "ratio" in name):
                continue
            if kw in ("买入", "卖出") and ("net" in name or "ratio" in name or "amount" in name):
                continue
            return True, kw
    return False, None


def check_nlp(name, raw_text):
    """Check if this requires NLP/text/subjective analysis."""
    text = (name + " " + raw_text).lower()
    for kw in NLP_KEYWORDS:
        if kw in text:
            return True, kw
    return False, None


def check_l2(name, raw_text):
    """Check if this requires Level2 data."""
    text = (name + " " + raw_text).lower()
    for kw in L2_KEYWORDS:
        if kw in text:
            return True, kw
    return False, None


def check_non_factor(name):
    """Check if this is not actually a factor (reference value, source label, etc)."""
    norm = normalize_name(name)
    for pat in NON_FACTOR_PATTERNS:
        if re.match(pat, norm):
            return True
    return False


def find_duplicate(norm_name, registry_names):
    """Check for duplicate against registry + implemented features.
    Returns (is_dup, overlap_with) or (False, None).
    """
    # Exact match to registry
    if norm_name in registry_names:
        return True, f"registry:{registry_names[norm_name]}"

    # Exact match to implemented
    if norm_name in all_impl_norm:
        return True, f"implemented:{norm_name}"

    # Substring match to registry (both directions, min 5 chars)
    if len(norm_name) >= 5:
        for rn, fid in registry_names.items():
            if len(rn) >= 5:
                if norm_name in rn or rn in norm_name:
                    return True, f"registry_substr:{fid}({rn})"

    # Substring match to implemented
    if len(norm_name) >= 5:
        for impl in all_impl_norm:
            if len(impl) >= 5:
                if norm_name in impl or impl in norm_name:
                    return True, f"impl_substr:{impl}"

    return False, None


# --- CONCEPT-LEVEL DUPLICATE DETECTION ---
# These are concepts that are equivalent to existing features even though name doesn't match

CONCEPT_DUPLICATES = {
    # raw_name_pattern: (existing_feature, reason)
    "limit_up_count": ("market_limit_up_count", "same concept: market-wide limit-up count"),
    "today_limit": ("is_limit_up", "trivial: close==high_limit"),
    "closed_limit": ("is_limit_up", "trivial: close==high_limit"),
    "final_close": ("is_limit_up", "trivial: did it close at limit"),
    "peak_price": (None, "not a factor: reference price value"),
    "z_t": (None, "not a factor: generic macro state variable label"),
    "abull": (None, "not a factor: data source reference"),
    "success_prob": ("seal_money_to_float_mv", "needs seal_order_queue (L2 data)"),
}


def check_concept_duplicate(norm_name, raw_text):
    """Check for concept-level duplicates that substring matching won't catch."""
    for pattern, (existing, reason) in CONCEPT_DUPLICATES.items():
        if pattern in norm_name:
            return True, f"{existing}: {reason}" if existing else reason
    return False, None


# --- FORMULA DERIVABILITY ---

def can_derive_formula(name, raw_text, data_needs):
    """
    Heuristic: can we write a computable_definition from the raw_text?
    Returns (can_compute, formula_sketch, rejection_reason)
    """
    text = raw_text.lower()
    norm = normalize_name(name)

    # If raw_text contains a formula-like pattern
    has_formula = any(x in text for x in ["/", "÷", "×", "*", "+", "-", "=", "ratio", "count", "avg", "mean", "sum", "max", "min", "std"])
    has_comparison = any(x in text for x in [">", "<", ">=", "<=", "前", "后", "超过", "达到"])
    has_condition = any(x in text for x in ["是否", "if", "when", "whether", "binary", "flag"])

    # If it has ratio/count/avg type operations, likely computable
    if has_formula or has_comparison or has_condition:
        return True, None, None

    # Very short raw_text with no formula cues -> hard to derive
    if len(raw_text) < 20 and not has_formula:
        return False, None, "raw_text too short/vague for formula derivation"

    # Check for purely descriptive/narrative text with no quantifiable signal
    if all(x not in text for x in ["率", "比", "数", "量", "幅", "价", "值",
                                     "count", "ratio", "rate", "vol", "price",
                                     "pct", "change", "return", "avg", "sum"]):
        return False, None, "no quantifiable metric in description"

    return True, None, None


# --- MAIN ASSESSMENT ---

def assess_candidate(c, registry_names):
    """
    Assess a single candidate. Returns:
    (decision, reason, details)
    decision: "promote" | "reject" | "defer"
    """
    name = c["factor_name"]
    norm = c["normalized_name"]
    raw_text = c["raw_text"]
    data_needs = c["data_needs"]

    # Check non-factor
    if check_non_factor(name):
        return "reject", "not_a_factor", f"{name} is a reference value/label, not a predictive factor"

    # Check concept duplicate
    is_concept_dup, concept_reason = check_concept_duplicate(norm, raw_text)
    if is_concept_dup:
        return "reject", "concept_duplicate", concept_reason

    # Check NLP/text/subjective
    is_nlp, nlp_kw = check_nlp(name, raw_text)
    if is_nlp:
        return "reject", "requires_nlp_text", f"keyword: {nlp_kw}"

    # Check strategy/position management
    is_strategy, strat_kw = check_strategy(name, raw_text)
    if is_strategy:
        return "reject", "trading_strategy", f"keyword: {strat_kw}"

    # Check Level2
    is_l2, l2_kw = check_l2(name, raw_text)
    if is_l2:
        return "defer", "needs_level2", f"keyword: {l2_kw}"

    # Check name-based duplicate
    is_dup, dup_info = find_duplicate(norm, registry_names)
    if is_dup:
        return "reject", "duplicate", dup_info

    # Check formula derivability
    can_compute, _, formula_reason = can_derive_formula(name, raw_text, data_needs)
    if not can_compute:
        return "defer", "unclear_formula", formula_reason

    # If we get here, it passes basic checks. Now deeper assessment:
    # - Does it have clear asof_time?
    if c["asof_time"] == "unknown":
        return "defer", "unknown_asof", "asof_time not determined"

    # Passed all checks -> promote
    return "promote", "passes_all_criteria", None


def derive_definition(c):
    """Derive computable_definition and other fields from raw_text."""
    name = c["factor_name"]
    norm = c["normalized_name"]
    raw_text = c["raw_text"]
    data_needs = c["data_needs"]
    text_lower = raw_text.lower()

    # Try to extract formula from raw_text patterns
    definition = ""
    family = "unknown"
    impl_hint = ""

    # Pattern matching for common factor types
    if "ratio" in norm or "率" in raw_text or "/" in raw_text:
        if "sector" in norm or "板块" in raw_text or "题材" in raw_text:
            family = "sector_structure"
        elif "volume" in norm or "量" in raw_text or "换手" in raw_text:
            family = "volume_structure"
        elif "seal" in norm or "封" in raw_text:
            family = "board_quality"
        else:
            family = "ratio_factor"
    elif "count" in norm or "数" in raw_text:
        if "sector" in norm or "板块" in raw_text:
            family = "sector_structure"
        elif "limit" in norm or "涨停" in raw_text:
            family = "board_structure"
        else:
            family = "count_factor"
    elif "strength" in norm or "强度" in raw_text or "力" in raw_text:
        family = "momentum"
    elif "return" in norm or "收益" in raw_text or "涨幅" in raw_text:
        family = "return_factor"
    elif "sector" in norm or "板块" in raw_text or "题材" in raw_text:
        family = "sector_structure"
    elif "board" in norm or "连板" in raw_text or "涨停" in raw_text:
        family = "board_structure"
    elif "volume" in norm or "量" in raw_text or "成交" in raw_text:
        family = "volume_structure"
    elif "price" in norm or "价" in raw_text:
        family = "price_structure"
    elif "emotion" in norm or "情绪" in raw_text:
        family = "market_emotion"
    elif "leader" in norm or "龙" in raw_text:
        family = "leader_factor"
    else:
        family = "misc"

    # Build computable definition from raw_text
    # Extract the core formula description
    definition = raw_text[:200].strip()
    if "|" in definition:
        parts = [p.strip() for p in definition.split("|") if p.strip()]
        if len(parts) >= 3:
            definition = parts[2] if len(parts[2]) > len(parts[1]) else parts[1]
        elif len(parts) >= 2:
            definition = parts[1]

    # Engineering path
    if "limit_pool" in data_needs:
        impl_hint = "stock_zt_pool APIs via free_data_factors.py + limit_list_d cache"
    elif "sector_theme" in data_needs:
        impl_hint = "ths_index_member + ths_daily cache for sector membership"
    elif "daily_ohlcv" in data_needs:
        impl_hint = "Daily OHLCV from main dataframe"
    elif "cross_market" in data_needs:
        impl_hint = "index_global cache (804 files)"
    else:
        impl_hint = "Needs investigation"

    return definition, family, impl_hint


def main():
    # Load registry names for dedup
    registry_names = load_registry_names()
    print(f"Registry names for dedup: {len(registry_names)}")
    print(f"Implemented features for dedup: {len(all_impl_norm)}")

    # Load queue
    with open(Q500_PATH, "r", encoding="utf-8") as f:
        q = json.load(f)

    candidates = q["candidates"]
    print(f"Candidates to assess: {len(candidates)}")

    # Assess each
    results = {"promote": [], "reject": [], "defer": []}
    for c in candidates:
        decision, reason, details = assess_candidate(c, registry_names)
        c["_decision"] = decision
        c["_reason"] = reason
        c["_details"] = details
        results[decision].append(c)

    print(f"\nAssessment results:")
    print(f"  promote: {len(results['promote'])}")
    print(f"  reject: {len(results['reject'])}")
    print(f"  defer: {len(results['defer'])}")

    # Rejection reasons breakdown
    print(f"\nRejection reasons:")
    rej_reasons = Counter(c["_reason"] for c in results["reject"])
    for k, v in rej_reasons.most_common():
        print(f"  {k}: {v}")

    print(f"\nDeferral reasons:")
    def_reasons = Counter(c["_reason"] for c in results["defer"])
    for k, v in def_reasons.most_common():
        print(f"  {k}: {v}")

    # Output results for next step
    output = {
        "summary": {
            "total": len(candidates),
            "promote": len(results["promote"]),
            "reject": len(results["reject"]),
            "defer": len(results["defer"]),
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
            "section": c["section"],
        } for c in results["promote"]],
        "reject": [{
            "rank": c["rank"],
            "factor_name": c["factor_name"],
            "reason": c["_reason"],
            "details": c["_details"],
        } for c in results["reject"]],
        "defer": [{
            "rank": c["rank"],
            "factor_name": c["factor_name"],
            "reason": c["_reason"],
            "details": c["_details"],
        } for c in results["defer"]],
    }

    out_path = r"C:\Users\zzzzzzl\Desktop\subagent\scripts\_assessment_429.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nWritten assessment to {out_path}")


if __name__ == "__main__":
    main()
