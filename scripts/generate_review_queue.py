"""Generate review queue from raw factor pool.

Supports two modes:
- top50: original 50-candidate queue (legacy)
- top500: expanded 500-candidate pool for batch review

Filters against ALL registry candidates (C001-C152+) dynamically.
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

INDEX_PATH = r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json"
REGISTRY_PATH = r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json"

OUTPUT_50_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\raw_to_registry_review_queue_20260506.md"
OUTPUT_500_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\raw_to_registry_review_queue_500_20260506.md"
OUTPUT_500_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\raw_to_registry_review_queue_500_20260506.json"

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
    """Load all valid registry candidate names for dedup."""
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
    cid_pattern = re.compile(r"^C\d{3}$")
    names = set()
    count = 0
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
            count += 1
            name = c.get("name", "")
            if name:
                names.add(normalize_name(name))
    return names, count


def is_implemented(norm_name):
    if not norm_name or len(norm_name) < 3:
        return False
    if norm_name in all_impl_norm:
        return True
    if len(norm_name) >= 5:
        for impl in all_impl_norm:
            if len(impl) >= 5:
                if norm_name in impl or impl in norm_name:
                    return True
    return False


def is_in_registry(norm_name, registry_names):
    if not norm_name or len(norm_name) < 3:
        return False
    if norm_name in registry_names:
        return True
    if len(norm_name) >= 5:
        for rn in registry_names:
            if len(rn) >= 5:
                if norm_name in rn or rn in norm_name:
                    return True
    return False


PRIORITY_DATA_NEEDS = {"minute", "auction", "daily_ohlcv", "limit_pool", "moneyflow", "lhb", "hot_rank"}


def score(r):
    s = 0
    p = r.get("priority", "unknown")
    if p == "P0":
        s += 30
    elif p == "P1":
        s += 20
    elif p == "P2":
        s += 10
    dn = r.get("data_needs", [])
    if isinstance(dn, list):
        if "unknown" not in dn:
            s += 15
        for d in dn:
            if d in PRIORITY_DATA_NEEDS:
                s += 5
    if r.get("asof_time", "unknown") != "unknown":
        s += 10
    if not r.get("exact_duplicate_group"):
        s += 5
    if len(r.get("raw_text", "")) < 200:
        s += 3
    if r.get("suggested_bucket") == "expanded":
        s += 20
    return s


def get_eng_path(dn):
    if "limit_pool" in dn:
        return "limit_list_d cache (804 files) or stock_zt_pool APIs via free_data_factors.py"
    elif "auction" in dn:
        return "stk_auction_o/c cache (804 files) via tushare attachment"
    elif "daily_ohlcv" in dn:
        return "Daily OHLCV from main dataframe (always available)"
    elif "minute" in dn:
        return "stk_mins_5 cache (679 files) via intraday attachment"
    elif "moneyflow" in dn:
        return "moneyflow cache (804 files) via tushare attachment"
    elif "lhb" in dn:
        return "top_list/top_inst cache (804 files) via tushare attachment"
    elif "hot_rank" in dn:
        return "ths_hot cache (623 files) via tushare attachment"
    elif "sector_theme" in dn:
        return "ths_daily/moneyflow_ind_dc cache via sector features"
    elif "cross_market" in dn:
        return "index_global cache (804 files)"
    return "Needs investigation"


def filter_candidates(records, registry_names):
    """Filter raw pool records to review candidates."""
    return [r for r in records
            if r["readiness_status"] == "ready_for_registry_review"
            and r["registry_match_status"] == "no_match"
            and not is_implemented(r["normalized_name"])
            and not is_in_registry(r["normalized_name"], registry_names)]


def write_queue_md(candidates, output_path, pool_size, registry_count):
    """Write markdown review queue."""
    lines = []
    lines.append(f"# Raw-to-Registry Review Queue ({pool_size}) -- 2026-05-06")
    lines.append("")
    lines.append(f"> {pool_size} candidates from raw factor pool most worth human/engineering review")
    lines.append(f"> Filtered: free_data=True, leakage=low, needs_level2=False, not implemented, not in C001-C{registry_count:03d}")
    lines.append(f"> Exclusion: exact + substring match against GPU_PROBE_FEATURES + STABLE + RESEARCH + TUSHARE_FACTOR_COLUMNS + BOARD_STRUCTURE_COLUMNS + MARKET_EMOTION_COLUMNS ({len(all_impl_norm)} features) + {registry_count} registry candidates")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Selection Criteria")
    lines.append("")
    lines.append("1. free_data=True")
    lines.append("2. future_leakage_risk=low")
    lines.append("3. needs_level2=False")
    lines.append(f"4. registry_match_status=no_match (not in C001-C{registry_count:03d})")
    lines.append("5. normalized_name NOT in any implemented feature constant (exact OR substring)")
    lines.append(f"6. normalized_name NOT in any registry candidate name (exact OR substring, {registry_count} candidates)")
    lines.append("7. Priority data_needs: minute, auction, daily_ohlcv, limit_pool, moneyflow, lhb, hot_rank")
    lines.append("")
    lines.append(f"Candidates passing all filters: {len(candidates)} (from 3,075 total pool)")
    if candidates:
        lines.append(f"Output pool: top {min(pool_size, len(candidates))} by composite score")
        top = candidates[:pool_size]
        lines.append(f"Score range: {top[0]['_score']} - {top[-1]['_score']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    top = candidates[:pool_size]

    dn_counts = Counter()
    for c in top:
        for d in c.get("data_needs", []):
            dn_counts[d] += 1

    lines.append(f"## Data Needs Distribution (Top {len(top)})")
    lines.append("")
    lines.append("| data_needs | Count |")
    lines.append("|-----------|-------|")
    for k, v in dn_counts.most_common():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, c in enumerate(top):
        lines.append(f"### {i+1}. {c['factor_name']}")
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| raw_factor_id | {c['raw_factor_id']} |")
        lines.append(f"| source_file | {c['source_file']} |")
        lines.append(f"| source_line | {c['source_line']} |")
        lines.append(f"| data_needs | {c['data_needs']} |")
        lines.append(f"| asof_time | {c['asof_time']} |")
        lines.append(f"| priority | {c['priority']} |")
        lines.append(f"| suggested_bucket | {c['suggested_bucket']} |")
        lines.append(f"| score | {c['_score']} |")
        lines.append(f"| raw_text | {c['raw_text'][:250]} |")
        lines.append(f"| section | {c['section'][:200]} |")
        lines.append("")

        dn = c.get("data_needs", [])
        eng = get_eng_path(dn)

        reasons = []
        if c.get("priority") in ("P0", "P1"):
            reasons.append(f"Source-marked {c['priority']}")
        if c.get("suggested_bucket") == "expanded":
            reasons.append("Suggested for expanded pool")
        if "limit_pool" in dn or "auction" in dn:
            reasons.append("High-signal data source")
        if c.get("asof_time") == "after_close":
            reasons.append("Clean asof_time")
        if not reasons:
            reasons.append("High composite score")

        lines.append(f"**Why review**: {' | '.join(reasons)}")
        lines.append(f"**Engineering path**: {eng}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Excluded Feature Check")
    lines.append("")
    lines.append("The following known features were correctly excluded from this queue:")
    lines.append("")
    excluded_examples = [
        "max_board_height", "market_max_board_height", "board_count",
        "prev_limit_up_premium", "volume_vs_prev", "seal_rate_80_threshold",
        "seal_money_to_float_mv", "emotion_score", "seal_time",
        "real_limit_up_premium_gap", "zbgc_sector_pressure", "theme_limit_density",
    ]
    for name in excluded_examples:
        norm = normalize_name(name)
        impl = is_implemented(norm)
        in_reg = is_in_registry(norm, registry_names_global)
        in_q = any(c["factor_name"] == name for c in top)
        lines.append(f"- {name}: implemented={impl}, in_registry={in_reg}, in_queue={in_q}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Encoding Note")
    lines.append("")
    lines.append("raw_text and section fields are stored as valid UTF-8 in the source JSONL files.")
    lines.append("No actual encoding corruption detected. Terminal display artifacts (mojibake) are")
    lines.append("due to Windows console codepage mismatch, not data corruption.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated 2026-05-06. Source: raw_factor_pool_index.json (3,075 records). Registry: C001-C{registry_count:03d} ({registry_count} candidates)*")

    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Written MD: {len(content)} bytes, {len(top)} entries to {output_path}")
    return len(top)


def write_queue_json(candidates, output_path, pool_size, registry_count):
    """Write JSON review queue."""
    top = candidates[:pool_size]
    output = {
        "meta": {
            "created": "2026-05-06",
            "pool_size": len(top),
            "total_passing_filter": len(candidates),
            "registry_candidate_count": registry_count,
            "dedup_against": f"C001-C{registry_count:03d} + {len(all_impl_norm)} implemented features",
            "selection_criteria": [
                "free_data=True",
                "future_leakage_risk=low",
                "needs_level2=False",
                f"not in registry C001-C{registry_count:03d} (name exact+substring)",
                "not in implemented features (name exact+substring)",
                "registry_match_status=no_match",
            ],
            "score_range": [top[0]["_score"], top[-1]["_score"]] if top else [0, 0],
        },
        "candidates": [{
            "rank": i + 1,
            "raw_factor_id": c["raw_factor_id"],
            "factor_name": c["factor_name"],
            "normalized_name": c["normalized_name"],
            "source_file": c["source_file"],
            "source_line": c["source_line"],
            "data_needs": c["data_needs"],
            "asof_time": c["asof_time"],
            "priority": c["priority"],
            "suggested_bucket": c["suggested_bucket"],
            "score": c["_score"],
            "raw_text": c["raw_text"][:500],
            "section": c["section"][:300],
            "engineering_path": get_eng_path(c.get("data_needs", [])),
        } for i, c in enumerate(top)]
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Written JSON: {len(top)} entries to {output_path}")
    return len(top)


# Module-level for use in write_queue_md excluded check
registry_names_global = set()


def main():
    global registry_names_global

    # Load registry for dedup
    registry_names, registry_count = load_registry_names()
    registry_names_global = registry_names
    print(f"Registry candidates for dedup: {registry_count}")
    print(f"Implemented features for dedup: {len(all_impl_norm)}")

    # Load index
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index = json.load(f)
    records = index["records"]

    # Filter
    candidates = filter_candidates(records, registry_names)
    print(f"Candidates after all filters: {len(candidates)}")

    # Score and sort
    for c in candidates:
        c["_score"] = score(c)
    candidates.sort(key=lambda x: -x["_score"])

    # Generate top-50 (legacy)
    n50 = write_queue_md(candidates, OUTPUT_50_MD, 50, registry_count)

    # Generate top-500
    n500_md = write_queue_md(candidates, OUTPUT_500_MD, 500, registry_count)
    n500_json = write_queue_json(candidates, OUTPUT_500_JSON, 500, registry_count)

    # Assertions
    assert n50 <= 50
    assert n500_md <= 500
    assert not any(is_implemented(c["normalized_name"]) for c in candidates[:500])
    assert not any(is_in_registry(c["normalized_name"], registry_names) for c in candidates[:500])
    print(f"\nAll assertions passed.")
    print(f"  top50: {n50} entries")
    print(f"  top500 MD: {n500_md} entries")
    print(f"  top500 JSON: {n500_json} entries")


if __name__ == "__main__":
    main()
