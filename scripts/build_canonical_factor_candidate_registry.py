"""Build a canonical audit registry for short-line factor candidates.

This script is factor-library bookkeeping only:
- no training
- no gpu_probe
- no model-code changes
- no writes to the formal factor_registry.json

It reads:
- formal C registry
- temporary O candidate reports
- raw factor pool index

It writes:
- docs/canonical_factor_candidate_registry_20260517.md
- E:/ashare_similarity_runtime/data/reports/prediction/canonical_factor_candidate_registry_20260517.json
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
DOCS = PROJECT / "docs"
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
RAW_POOL_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json")
OUT_JSON = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\canonical_factor_candidate_registry_20260517.json")
OUT_MD = DOCS / "canonical_factor_candidate_registry_20260517.md"

O_REPORTS = [
    DOCS / "four_source_shortline_omnibus_candidate_scan_20260517.md",
    DOCS / "four_source_shortline_omnibus_candidate_addendum_20260517.md",
    DOCS / "four_source_shortline_omnibus_candidate_addendum2_20260517.md",
    DOCS / "four_source_shortline_omnibus_candidate_addendum3_20260517.md",
]


STOP_TOKENS = {
    "factor",
    "score",
    "ratio",
    "signal",
    "index",
    "flag",
    "proxy",
    "canonical",
    "clean",
    "recheck",
    "raw",
    "v2",
    "real",
    "simple",
    "quality",
    "strength",
    "count",
    "rate",
    "rank",
    "state",
    "stage",
    "effect",
    "event",
    "new",
    "stock",
    "market",
    "daily",
    "intraday",
}

SYNONYMS = {
    "zt": "limit",
    "limitup": "limit",
    "limit_up": "limit",
    "up": "limit",
    "seal": "seal",
    "reseal": "seal",
    "board": "board",
    "openboard": "open_board",
    "zhaban": "broken_board",
    "broken": "broken_board",
    "dragon": "leader",
    "leader": "leader",
    "sector": "theme",
    "theme": "theme",
    "concept": "theme",
    "echelon": "tier",
    "tier": "tier",
    "volume": "volume",
    "vol": "volume",
    "amount": "amount",
    "turnover": "turnover",
    "flow": "flow",
    "moneyflow": "flow",
    "northbound": "northbound",
    "hsgt": "northbound",
    "lhb": "dragon_list",
    "dragon_list": "dragon_list",
    "seat": "seat",
    "guba": "social",
    "forum": "social",
    "attention": "attention",
    "sentiment": "sentiment",
    "minute": "minute",
    "auction": "auction",
    "open": "open",
    "close": "close",
    "tail": "tail",
    "morning": "morning",
    "shock": "shock",
    "reversal": "reversal",
    "breakout": "breakout",
    "premium": "premium",
    "decay": "decay",
    "capacity": "capacity",
    "emotion": "emotion",
    "cycle": "cycle",
    "regime": "regime",
    "risk": "risk",
    "ipo": "ipo",
    "subnew": "ipo",
    "sub_new": "ipo",
    "float": "float",
    "pledge": "pledge",
    "forecast": "forecast",
    "survey": "survey",
    "announcement": "announcement",
    "regulatory": "regulatory",
    "block": "block_trade",
    "trade": "trade",
    "orderbook": "orderbook",
    "order": "order",
    "tick": "tick",
    "liquidity": "liquidity",
    "vwap": "vwap",
    "gap": "gap",
    "breadth": "breadth",
}

FAMILY_RULES = [
    ("limit_board", {"limit", "seal", "board", "broken_board"}),
    ("theme_leader", {"theme", "leader", "tier", "capacity"}),
    ("minute_hf", {"minute", "vwap", "shock", "tail", "morning", "liquidity", "trend"}),
    ("auction_open", {"auction", "open", "gap"}),
    ("flow_lhb", {"dragon_list", "seat", "flow", "northbound", "block_trade"}),
    ("social_attention", {"social", "attention", "sentiment"}),
    ("event_fundamental", {"forecast", "survey", "announcement", "regulatory", "pledge", "float", "ipo"}),
    ("cross_market", {"shibor", "global", "cb", "hk", "wti", "us", "macro"}),
    ("level2_tick", {"orderbook", "order", "tick", "spread"}),
    ("daily_technical", {"volume", "turnover", "breakout", "reversal", "cost"}),
]

STATUS_RANK = {
    "formal_registry": 0,
    "ready_engineering_review": 1,
    "needs_formula_lock": 2,
    "needs_data_pipeline": 3,
    "needs_engineering_review": 3,
    "needs_data_check": 3,
    "needs_asof_check": 3,
    "blocked_level2_or_scrape": 4,
    "blocked_level2_or_nonfree": 4,
    "raw_unreviewed": 5,
    "unknown": 6,
}


@dataclass
class Candidate:
    uid: str
    name: str
    source: str
    priority: str = ""
    status: str = ""
    data_need: str = ""
    formula: str = ""
    family_hint: str = ""
    duplicate_watch: str = ""
    origin_file: str = ""
    raw_text: str = ""
    canonical_key: str = ""
    family: str = ""


@dataclass
class CanonicalGroup:
    key: str
    family: str
    representative: str
    status: str
    priority: str
    members: list[Candidate] = field(default_factory=list)
    data_needs: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    formulas: list[str] = field(default_factory=list)
    raw_examples: list[str] = field(default_factory=list)


def safe_load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def split_tokens(name: str) -> list[str]:
    raw = re.sub(r"[^A-Za-z0-9_]+", "_", name.lower())
    raw = re.sub(r"([a-z])([0-9])", r"\1_\2", raw)
    toks = [t for t in raw.split("_") if t]
    out = []
    for t in toks:
        t = SYNONYMS.get(t, t)
        if t and t not in STOP_TOKENS:
            out.append(t)
    return out


def canonical_key(name: str, data_need: str = "", formula: str = "") -> str:
    toks = split_tokens(name)
    text = f"{name} {data_need} {formula}".lower()
    # Add high-signal concepts from text that may not appear in the name.
    for k, v in SYNONYMS.items():
        if k in text and v not in toks and v not in STOP_TOKENS:
            toks.append(v)
    # Preserve a few meaningful numeric horizons.
    for n in re.findall(r"\b(1|3|5|10|15|20|30|60)\b", text):
        token = f"n{n}"
        if token not in toks:
            toks.append(token)
    if not toks:
        toks = [re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "unnamed"]
    # Sort for duplicate grouping, but keep at most 6 tokens to avoid overfitting long names.
    unique = sorted(dict.fromkeys(toks))
    return "__".join(unique[:8])


def assign_family(name: str, data_need: str = "", formula: str = "") -> str:
    toks = set(split_tokens(f"{name} {data_need} {formula}"))
    for fam, rules in FAMILY_RULES:
        if toks & rules:
            return fam
    return "misc_review"


def normalize_status(status: str, source: str) -> str:
    s = (status or "").strip()
    if source == "formal_registry":
        return "formal_registry"
    if not s:
        return "unknown"
    return s


def better_status(a: str, b: str) -> str:
    return a if STATUS_RANK.get(a, 99) <= STATUS_RANK.get(b, 99) else b


def better_priority(a: str, b: str) -> str:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "blocked": 4, "": 9, "unknown": 9}
    return a if order.get(a, 9) <= order.get(b, 9) else b


def flatten_formal_candidates(reg: dict[str, Any]) -> list[Candidate]:
    seen: set[str] = set()
    out: list[Candidate] = []

    def visit(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            fid = obj.get("factor_id") or obj.get("id")
            name = obj.get("name") or obj.get("factor_name") or obj.get("candidate_name")
            if isinstance(fid, str) and re.fullmatch(r"C\d{3}", fid) and fid not in seen:
                seen.add(fid)
                out.append(
                    Candidate(
                        uid=fid,
                        name=str(name or fid),
                        source="formal_registry",
                        priority=str(obj.get("priority") or obj.get("pri") or ""),
                        status="formal_registry",
                        data_need=str(obj.get("data_need") or obj.get("required_columns") or obj.get("data_needs") or ""),
                        formula=str(obj.get("formula") or obj.get("computable_definition") or obj.get("formula_sketch") or ""),
                        family_hint=str(obj.get("family") or obj.get("group") or ""),
                        origin_file=path,
                        raw_text=str(obj.get("raw_idea") or obj.get("raw_text") or ""),
                    )
                )
            for k, v in obj.items():
                visit(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                visit(item, f"{path}[{i}]")

    visit(reg, "factor_registry")
    return out


def parse_o_reports(paths: list[Path]) -> list[Candidate]:
    out: list[Candidate] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if not re.match(r"^\| O\d{3} \|", line):
                continue
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) < 8:
                continue
            oid, name, pri, source_lane, data_need, formula, status, duplicate_watch = parts[:8]
            out.append(
                Candidate(
                    uid=oid,
                    name=name,
                    source="temporary_o_queue",
                    priority=pri,
                    status=status,
                    data_need=data_need,
                    formula=formula,
                    family_hint=source_lane,
                    duplicate_watch=duplicate_watch,
                    origin_file=str(path),
                )
            )
    return out


def parse_raw_pool(path: Path) -> list[Candidate]:
    raw = safe_load_json(path)
    records = raw.get("records") or raw.get("raw_records") or raw.get("items") or []
    if isinstance(records, dict):
        records = list(records.values())
    out: list[Candidate] = []
    for r in records:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("raw_factor_id") or "")
        name = str(r.get("factor_name") or r.get("normalized_name") or rid)
        if not name:
            continue
        data_need = r.get("data_needs") or ""
        out.append(
            Candidate(
                uid=rid or f"RAW_UNKNOWN_{len(out)+1}",
                name=name,
                source="raw_pool",
                priority=str(r.get("priority") or "unknown"),
                status=str(r.get("readiness_status") or "raw_unreviewed"),
                data_need=json.dumps(data_need, ensure_ascii=False) if not isinstance(data_need, str) else data_need,
                formula=str(r.get("raw_text") or ""),
                family_hint=str(r.get("suggested_bucket") or ""),
                duplicate_watch=str(r.get("matched_registry_id") or r.get("registry_match_status") or ""),
                origin_file=str(r.get("source_path") or r.get("source_file") or RAW_POOL_PATH),
                raw_text=str(r.get("raw_text") or ""),
            )
        )
    return out


def enrich_candidates(candidates: list[Candidate]) -> None:
    for c in candidates:
        c.status = normalize_status(c.status, c.source)
        c.canonical_key = canonical_key(c.name, c.data_need, c.formula)
        c.family = assign_family(c.name, c.data_need, c.formula)


def build_groups(candidates: list[Candidate]) -> dict[str, CanonicalGroup]:
    groups: dict[str, CanonicalGroup] = {}
    for c in candidates:
        key = c.canonical_key
        if key not in groups:
            groups[key] = CanonicalGroup(
                key=key,
                family=c.family,
                representative=c.name,
                status=c.status,
                priority=c.priority,
            )
        g = groups[key]
        g.members.append(c)
        g.sources.add(c.source)
        if c.data_need:
            g.data_needs.add(c.data_need)
        if c.formula and len(g.formulas) < 4:
            g.formulas.append(c.formula)
        if c.raw_text and len(g.raw_examples) < 3:
            g.raw_examples.append(c.raw_text[:240])
        g.status = better_status(g.status, c.status)
        g.priority = better_priority(g.priority, c.priority)
        # Prefer formal names, then O queue names, then shorter names.
        if c.source == "formal_registry":
            g.representative = c.name
        elif "formal_registry" not in g.sources and c.source == "temporary_o_queue":
            g.representative = c.name
        elif len(c.name) < len(g.representative) and c.source != "raw_pool":
            g.representative = c.name
        if g.family == "misc_review" and c.family != "misc_review":
            g.family = c.family
    return groups


def group_decision(g: CanonicalGroup) -> str:
    if "formal_registry" in g.sources:
        return "already_formal_registry"
    if "temporary_o_queue" in g.sources:
        if g.status == "ready_engineering_review":
            return "engineering_review_first"
        if g.status in {"needs_formula_lock", "needs_data_pipeline", "blocked_level2_or_scrape"}:
            return g.status
        return "o_queue_review"
    # raw-only group
    if g.status == "ready_for_registry_review":
        return "raw_only_possible_candidate"
    if g.status in {"needs_engineering_review", "needs_data_check", "needs_asof_check"}:
        return "raw_only_needs_review"
    if g.status in {"blocked_level2_or_nonfree", "blocked_level2_or_scrape"}:
        return "blocked_or_data_missing"
    return "raw_only_low_priority_or_duplicate"


def compact_list(items: list[str], n: int = 3) -> str:
    clean = []
    for item in items:
        item = re.sub(r"\s+", " ", str(item)).strip()
        if item and item not in clean:
            clean.append(item)
    if not clean:
        return ""
    extra = len(clean) - n
    head = clean[:n]
    return "; ".join(head) + (f"; +{extra} more" if extra > 0 else "")


def main() -> None:
    reg = safe_load_json(REGISTRY_PATH)
    formal = flatten_formal_candidates(reg)
    o_candidates = parse_o_reports(O_REPORTS)
    raw_candidates = parse_raw_pool(RAW_POOL_PATH)
    all_candidates = formal + o_candidates + raw_candidates
    enrich_candidates(all_candidates)
    groups = build_groups(all_candidates)

    for g in groups.values():
        g.members.sort(key=lambda c: (c.source != "formal_registry", c.source != "temporary_o_queue", c.uid))

    decisions = Counter(group_decision(g) for g in groups.values())
    family_counts = Counter(g.family for g in groups.values())
    source_counts = Counter(c.source for c in all_candidates)
    status_counts = Counter(g.status for g in groups.values())

    # High-value table: no formal registry, at least one O queue member or raw ready group.
    review_groups = [
        g
        for g in groups.values()
        if group_decision(g)
        in {
            "engineering_review_first",
            "needs_formula_lock",
            "needs_data_pipeline",
            "raw_only_possible_candidate",
            "raw_only_needs_review",
        }
    ]
    review_groups.sort(
        key=lambda g: (
            STATUS_RANK.get(g.status, 99),
            {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(g.priority, 9),
            -len(g.members),
            g.family,
            g.representative,
        )
    )

    raw_only_ready = [
        g
        for g in groups.values()
        if "raw_pool" in g.sources
        and "temporary_o_queue" not in g.sources
        and "formal_registry" not in g.sources
        and g.status in {"ready_for_registry_review", "needs_engineering_review", "needs_data_check", "needs_asof_check"}
    ]
    raw_only_ready.sort(
        key=lambda g: (
            STATUS_RANK.get(g.status, 99),
            {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(g.priority, 9),
            -len(g.members),
            g.representative,
        )
    )

    out = {
        "meta": {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "canonical closed-loop audit for short-line factor candidates",
            "formal_registry_path": str(REGISTRY_PATH),
            "raw_pool_path": str(RAW_POOL_PATH),
            "o_reports": [str(p) for p in O_REPORTS],
            "formal_candidate_count_parsed": len(formal),
            "temporary_o_candidate_count": len(o_candidates),
            "raw_pool_record_count": len(raw_candidates),
            "input_candidate_rows_total": len(all_candidates),
            "canonical_group_count": len(groups),
        },
        "summary": {
            "source_counts": dict(source_counts),
            "decision_counts": dict(decisions),
            "family_counts": dict(family_counts),
            "canonical_status_counts": dict(status_counts),
            "raw_only_ready_or_needs_review_count": len(raw_only_ready),
        },
        "canonical_groups": [
            {
                "canonical_key": g.key,
                "representative": g.representative,
                "family": g.family,
                "decision": group_decision(g),
                "status": g.status,
                "priority": g.priority,
                "sources": sorted(g.sources),
                "member_count": len(g.members),
                "member_ids": [m.uid for m in g.members[:50]],
                "member_names": [m.name for m in g.members[:20]],
                "data_needs": sorted(g.data_needs)[:20],
                "formula_examples": g.formulas[:4],
            }
            for g in sorted(groups.values(), key=lambda x: (x.family, group_decision(x), x.representative))
        ],
        "priority_review_queue": [
            {
                "canonical_key": g.key,
                "representative": g.representative,
                "family": g.family,
                "decision": group_decision(g),
                "status": g.status,
                "priority": g.priority,
                "member_count": len(g.members),
                "member_ids": [m.uid for m in g.members[:20]],
                "data_needs": sorted(g.data_needs)[:8],
                "formula_examples": g.formulas[:2],
            }
            for g in review_groups[:180]
        ],
        "raw_only_review_queue": [
            {
                "canonical_key": g.key,
                "representative": g.representative,
                "family": g.family,
                "decision": group_decision(g),
                "status": g.status,
                "priority": g.priority,
                "member_count": len(g.members),
                "member_ids": [m.uid for m in g.members[:20]],
                "data_needs": sorted(g.data_needs)[:8],
                "formula_examples": g.formulas[:2],
            }
            for g in raw_only_ready[:120]
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Canonical Factor Candidate Registry Audit 2026-05-17")
    lines.append("")
    lines.append("Scope: factor-library closed-loop audit only. No training, no `gpu_probe`, no model-code changes, no formal registry writes.")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Formal registry: `{REGISTRY_PATH}`")
    lines.append(f"- Raw pool: `{RAW_POOL_PATH}`")
    lines.append("- O reports:")
    for p in O_REPORTS:
        lines.append(f"  - `{p}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---:|")
    lines.append(f"| formal C candidates parsed | {len(formal)} |")
    lines.append(f"| temporary O candidates parsed | {len(o_candidates)} |")
    lines.append(f"| raw pool records parsed | {len(raw_candidates)} |")
    lines.append(f"| total input rows | {len(all_candidates)} |")
    lines.append(f"| canonical groups after merge | {len(groups)} |")
    lines.append(f"| raw-only groups still needing review | {len(raw_only_ready)} |")
    lines.append("")
    lines.append("## Decision Counts")
    lines.append("")
    lines.append("| decision | canonical groups |")
    lines.append("|---|---:|")
    for k, v in decisions.most_common():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("## Family Counts")
    lines.append("")
    lines.append("| family | canonical groups |")
    lines.append("|---|---:|")
    for k, v in family_counts.most_common():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("## What This Means")
    lines.append("")
    lines.append("- The O001-O450 queue is not 450 independent finished factors. It is a wide search queue.")
    lines.append("- The canonical groups are the deduplicated working units for CC engineering review.")
    lines.append("- `already_formal_registry` groups are already represented by the current formal C registry or previous formal batches.")
    lines.append("- `engineering_review_first` groups are the cleanest next candidates for possible C293+ promotion.")
    lines.append("- `needs_formula_lock` and `needs_data_pipeline` should not be added until the formula or data path is locked.")
    lines.append("- `raw_only_*` groups are not covered well by the O queue; they are the true residual candidates from raw pool.")
    lines.append("")
    lines.append("## Priority Engineering Review Queue")
    lines.append("")
    lines.append("| rank | canonical | family | decision | status | pri | members | example ids | data needs |")
    lines.append("|---:|---|---|---|---|---|---:|---|---|")
    for i, g in enumerate(review_groups[:80], 1):
        ids = ", ".join(m.uid for m in g.members[:6])
        needs = compact_list(sorted(g.data_needs), 2)
        lines.append(
            f"| {i} | {g.representative} | {g.family} | {group_decision(g)} | {g.status} | {g.priority} | {len(g.members)} | {ids} | {needs} |"
        )
    lines.append("")
    lines.append("## Raw-Only Residual Review Queue")
    lines.append("")
    lines.append("These groups are not formal C candidates and do not appear in the O001-O450 queue by exact canonical key. They are the remaining raw-pool ideas worth manual review, mostly due to aliasing, formula looseness, or missing data.")
    lines.append("")
    lines.append("| rank | canonical | family | decision | status | pri | members | example ids | data needs |")
    lines.append("|---:|---|---|---|---|---|---:|---|---|")
    for i, g in enumerate(raw_only_ready[:80], 1):
        ids = ", ".join(m.uid for m in g.members[:8])
        needs = compact_list(sorted(g.data_needs), 2)
        lines.append(
            f"| {i} | {g.representative} | {g.family} | {group_decision(g)} | {g.status} | {g.priority} | {len(g.members)} | {ids} | {needs} |"
        )
    lines.append("")
    lines.append("## Recommended CC Prompt")
    lines.append("")
    lines.append("```text")
    lines.append("You are only doing factor-library engineering review. Do not train, do not run gpu_probe, do not change model/training code, and do not write the formal factor_registry until the promote list is reviewed.")
    lines.append("")
    lines.append("Inputs:")
    lines.append(f"1. {OUT_MD}")
    lines.append(f"2. {OUT_JSON}")
    lines.append("")
    lines.append("Task:")
    lines.append("1. Use priority_review_queue as the primary input, not the raw O001-O450 list.")
    lines.append("2. For each candidate, decide promote/reject/defer.")
    lines.append("3. For promote, provide exact formula, required columns, asof rule, duplicate check against the current formal C registry, and implementation site.")
    lines.append("4. For defer, state exactly which data or formula decision is missing.")
    lines.append("5. For reject, state whether it is duplicate, not a stock-day factor, not asof-safe, or not computable.")
    lines.append("```")
    lines.append("")
    lines.append("## Output JSON")
    lines.append("")
    lines.append(f"- Machine-readable canonical registry: `{OUT_JSON}`")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")
    print(json.dumps(out["meta"], ensure_ascii=False, indent=2))
    print("decision_counts", dict(decisions))
    print("family_counts", dict(family_counts))


if __name__ == "__main__":
    main()
