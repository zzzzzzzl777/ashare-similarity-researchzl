"""Build machine-readable raw factor pool index and cross-reference with registry."""
import json
import re
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

FILES_MAP = {
    "tgb": r"C:\Users\zzzzzzl\Desktop\subagent\run_logs\factor_doc_scan_tgb_desktop_latest.jsonl",
    "short": r"C:\Users\zzzzzzl\Desktop\subagent\run_logs\factor_doc_scan_short_desktop_latest.jsonl",
    "explore": r"C:\Users\zzzzzzl\Desktop\subagent\run_logs\factor_doc_scan_explore_desktop_latest.jsonl",
}

REGISTRY_PATH = r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json"
OUTPUT_PATH = r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json"


def normalize_name(name):
    n = name.lower().strip()
    n = re.sub(r"[^a-z0-9_]", "_", n)
    n = re.sub(r"_+", "_", n)
    return n.strip("_")


def load_all_records():
    all_records = []
    source_counts = {}
    for src_key, path in FILES_MAP.items():
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    obj["_source_file"] = src_key
                    records.append(obj)
        source_counts[src_key] = len(records)
        all_records.extend(records)
    return all_records, source_counts


def load_registry():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
    candidates = []
    cid_pattern = re.compile(r"^C\d{3}$")
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
            candidates.append({
                "factor_id": fid,
                "name": c.get("name", ""),
                "name_lower": normalize_name(c.get("name", "")),
                "raw_idea": c.get("raw_idea", ""),
            })
    return registry, candidates


def build_registry_lookups(candidates):
    name_set = set(c["name_lower"] for c in candidates)
    keywords = {}
    for c in candidates:
        words = set(re.findall(r"[a-z_]+", c["name_lower"]))
        words.update(re.findall(r"[a-z]{4,}", c.get("raw_idea", "").lower()))
        keywords[c["factor_id"]] = words
    return name_set, keywords


def match_to_registry(record, norm_name, registry_name_set, registry_keywords, candidates):
    if norm_name in registry_name_set:
        for c in candidates:
            if c["name_lower"] == norm_name:
                return ("exact_name_match", c["factor_id"])

    for c in candidates:
        if len(norm_name) >= 4 and len(c["name_lower"]) >= 4:
            if norm_name in c["name_lower"] or c["name_lower"] in norm_name:
                return ("partial_name_match", c["factor_id"])

    raw_words = set(re.findall(r"[a-z]{4,}", norm_name))
    raw_words.update(re.findall(r"[a-z]{4,}", record.get("raw_text", "").lower()))
    for cid, kwords in registry_keywords.items():
        overlap = raw_words & kwords
        if len(overlap) >= 3 and any(len(w) >= 5 for w in overlap):
            return ("keyword_overlap", cid)

    return ("no_match", None)


def classify_status(record):
    if record.get("needs_level2"):
        return "blocked_level2_or_nonfree"

    asof = record.get("asof_time", "unknown")
    data_needs = record.get("data_needs", [])
    leakage = record.get("future_leakage_risk", "unknown")
    free = record.get("free_data", False)

    if isinstance(data_needs, list) and "level2" in data_needs:
        return "blocked_level2_or_nonfree"

    if asof == "unknown" and data_needs == ["unknown"]:
        return "raw_unreviewed"

    if asof == "unknown" and data_needs != ["unknown"]:
        return "needs_asof_check"

    if isinstance(data_needs, list) and "unknown" in data_needs:
        return "needs_data_check"

    if leakage == "medium":
        return "needs_engineering_review"

    if free and leakage == "low":
        return "ready_for_registry_review"

    if not free and leakage == "low":
        return "needs_data_check"

    return "needs_engineering_review"


def main():
    all_records, source_counts = load_all_records()
    print(f"Loaded {len(all_records)} records from {len(FILES_MAP)} sources")

    registry, candidates = load_registry()
    print(f"Registry candidates: {len(candidates)}")

    registry_name_set, registry_keywords = build_registry_lookups(candidates)

    # Build duplicate groups
    raw_text_groups = defaultdict(list)
    name_groups = defaultdict(list)
    for i, r in enumerate(all_records):
        raw_text_groups[r["raw_text"]].append(i)
        name_groups[r["factor_name"]].append(i)

    # Build index records
    index_records = []
    for i, r in enumerate(all_records):
        raw_id = f"RAW{i+1:06d}"
        norm_name = normalize_name(r["factor_name"])
        match_status, matched_id = match_to_registry(
            r, norm_name, registry_name_set, registry_keywords, candidates
        )

        exact_dup_group = None
        if len(raw_text_groups[r["raw_text"]]) > 1:
            exact_dup_group = hashlib.md5(r["raw_text"].encode()).hexdigest()[:8]

        same_name_grp = None
        if len(name_groups[r["factor_name"]]) > 1:
            same_name_grp = r["factor_name"]

        status = classify_status(r)

        index_records.append({
            "raw_factor_id": raw_id,
            "source_file": r["_source_file"],
            "source_path": r.get("source_path", ""),
            "source_line": r.get("line_number", 0),
            "factor_name": r["factor_name"],
            "raw_text": r["raw_text"],
            "section": r.get("section", ""),
            "data_needs": r.get("data_needs", []),
            "asof_time": r.get("asof_time", "unknown"),
            "future_leakage_risk": r.get("future_leakage_risk", "unknown"),
            "free_data": r.get("free_data", False),
            "needs_level2": r.get("needs_level2", False),
            "suggested_bucket": r.get("suggested_bucket", "research"),
            "priority": r.get("priority", "unknown"),
            "normalized_name": norm_name,
            "exact_duplicate_group": exact_dup_group,
            "same_name_group": same_name_grp,
            "registry_match_status": match_status,
            "matched_registry_id": matched_id,
            "readiness_status": status,
        })

    # Compute stats
    match_stats = Counter(r["registry_match_status"] for r in index_records)
    status_stats = Counter(r["readiness_status"] for r in index_records)
    norm_nonempty = sum(1 for r in index_records if r["normalized_name"])

    print(f"\n=== REGISTRY MATCH STATS ===")
    for k, v in match_stats.most_common():
        print(f"  {k}: {v}")

    print(f"\n=== READINESS STATUS ===")
    for k, v in status_stats.most_common():
        print(f"  {k}: {v}")

    print(f"\nnormalized_name non-empty: {norm_nonempty}/{len(index_records)} ({norm_nonempty/len(index_records)*100:.1f}%)")

    # Registry mapping summary
    matched_registry_ids = set()
    for r in index_records:
        if r["matched_registry_id"]:
            matched_registry_ids.add(r["matched_registry_id"])

    all_registry_ids = set(c["factor_id"] for c in candidates)

    print(f"\n=== REGISTRY <-> RAW MAPPING ===")
    print(f"Registry candidates total: {len(all_registry_ids)}")
    print(f"Registry IDs matched to raw pool: {len(matched_registry_ids)}")
    print(f"Registry IDs with NO raw match: {len(all_registry_ids - matched_registry_ids)}")
    print(f"Raw records matched to registry: {sum(1 for r in index_records if r['matched_registry_id'])}")
    print(f"Raw records NOT in registry: {sum(1 for r in index_records if not r['matched_registry_id'])}")

    # Save index
    output = {
        "meta": {
            "created": "2026-05-06",
            "total_records": len(index_records),
            "unique_factor_names": len(set(r["factor_name"] for r in index_records)),
            "unique_normalized_names": len(set(r["normalized_name"] for r in index_records)),
            "source_files": dict(FILES_MAP),
            "source_counts": source_counts,
            "registry_reference": REGISTRY_PATH,
            "registry_candidate_count": len(candidates),
            "match_summary": dict(match_stats),
            "readiness_summary": dict(status_stats),
            "mapping_summary": {
                "registry_matched_to_raw": len(matched_registry_ids),
                "registry_not_in_raw": len(all_registry_ids - matched_registry_ids),
                "raw_matched_to_registry": sum(1 for r in index_records if r["matched_registry_id"]),
                "raw_not_in_registry": sum(1 for r in index_records if not r["matched_registry_id"]),
            },
            "exact_duplicate_groups": sum(1 for v in raw_text_groups.values() if len(v) > 1),
            "same_name_groups": sum(1 for v in name_groups.values() if len(v) > 1),
        },
        "records": index_records,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    file_size = Path(OUTPUT_PATH).stat().st_size
    print(f"\nSaved: {OUTPUT_PATH} ({file_size // 1024} KB)")

    # Also output summary for use in other files
    summary = {
        "source_counts": source_counts,
        "total": len(index_records),
        "unique_names": len(set(r["factor_name"] for r in index_records)),
        "match_stats": dict(match_stats),
        "status_stats": dict(status_stats),
        "mapping": output["meta"]["mapping_summary"],
        "matched_registry_ids": sorted(matched_registry_ids),
        "unmatched_registry_ids": sorted(all_registry_ids - matched_registry_ids),
    }
    print(f"\n=== SUMMARY JSON ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
