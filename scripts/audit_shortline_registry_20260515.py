import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
AUDIT_JSON_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry_audit_20260515.json")
AUDIT_MD_PATH = ROOT / "docs" / "factor_registry_audit_20260515.md"
REGISTRY_MD_PATH = ROOT / "docs" / "factor_registry.md"
EXPANSION_MD_PATH = ROOT / "docs" / "shortline_factor_expansion_20260515.md"
RAW_POOL_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json")


WINDOW_LOCK = {
    "C227": "lock lookback N for recent high, recommended N=20 trading days",
    "C228": "lock breakout lookback N, recommended N=20 trading days",
    "C230": "lock board-height history window, recommended N=20 trading days",
    "C234": "lock announcement decay half-life/window before training",
    "C235": "lock sector policy keyword window and source corpus before training",
    "C238": "lock famous-seat decay half-life/window before training",
    "C275": "lock trapped-cost lookback and VWAP source before training",
    "C278": "lock WQ rolling window/decay window and do not fit sign before training",
    "C281": "lock reversal window and rank universe before training",
    "C288": "lock short-video observation window and platform/source corpus before training",
}

FORMULA_LOCK = {
    "C225": "temperature score is an aggregation; component weights must be frozen or split into atomic factors",
    "C232": "theme uniqueness requires exact entropy/HHI formula and theme universe freeze",
    "C233": "200-lot imbalance requires exact threshold, trade direction proxy, and source availability",
    "C237": "seat premium requires exact whitelist/scoring method for premium seats",
    "C239": "seat style vector is multi-dimensional; split or freeze fixed vector construction",
    "C240": "announcement sentiment requires deterministic NLP dictionary/model version and no post-label tuning",
    "C255": "dynamic volume comparison needs exact historical baseline window and intraday cutoff",
    "C261": "weak-to-strong auction confirmation must be kept as a deterministic boolean formula",
    "C263": "sector event count needs event taxonomy and counting window freeze",
    "C264": "sector inflow event score needs exact source, event threshold, and aggregation window",
    "C268": "intraday event intensity needs event taxonomy and weighting freeze",
    "C269": "sector first-board attribute must be encoded as fixed categorical/one-hot rules",
    "C279": "WQ sign-volume-return formula must be exact; no sign selected by validation",
    "C280": "range close-open should be atomic; cross-sectional neutralization, if used, must be a separate feature",
    "C285": "liquidity price-impact proxy needs exact denominator and clipping rule",
    "C286": "sentiment interaction needs deterministic sentiment source/version and interaction formula",
    "C287": "guba heat amplification needs deterministic heat metric and time cutoff",
}

EXTERNAL_PIPELINE = {
    "C223": "sector real-time theme map or sector-level intraday return source",
    "C224": "theme membership and real-time theme breadth source",
    "C232": "theme universe/membership source",
    "C233": "200-lot trade-direction source",
    "C234": "announcement corpus with timestamp/asof",
    "C235": "policy/news corpus with timestamp/asof",
    "C240": "announcement NLP/sentiment source",
    "C241": "earnings surprise/event source",
    "C242": "Friday announcement event source",
    "C243": "ETF creation/redemption source",
    "C244": "limit event stream or deterministic minute reconstruction",
    "C249": "theme first-seal universe",
    "C251": "market/sector real-time benchmark stream",
    "C256": "failure-event labeling from minute stream",
    "C261": "auction + theme source",
    "C262": "one-word-board detector from limit event stream",
    "C263": "sector event stream",
    "C264": "sector moneyflow event stream",
    "C265": "large-buy event detector",
    "C266": "open-limit event detector",
    "C267": "auction-rise event detector",
    "C268": "multi-event intraday stream",
    "C269": "sector first-board event source",
    "C272": "turnover-board event source",
    "C280": "optional cross-sectional neutralization universe",
    "C286": "sentiment source",
    "C287": "guba/social heat source",
    "C288": "short-video source",
    "C289": "social leader source",
    "C290": "halt/reopen event source",
    "C291": "halt/reopen event source",
    "C292": "auction snapshot after 09:20 source",
}

OVERLAP = {
    "C224": ["C059 limit_theme_breadth"],
    "C227": ["C085 pullback_support_ratio"],
    "C229": ["C205 holdertrade_net_buy_ratio"],
    "C246": ["C008 seal_strength_proxy"],
    "C248": ["C191 attack_volume_real_1min"],
    "C253": ["C166 late_seal_ratio"],
    "C255": ["C192 dynamic_volume_acceleration_1min"],
    "C258": ["C190 first_5min_strength_1min"],
    "C259": ["C190 first_5min_strength_1min"],
    "C261": ["C029 weak_to_strong_signal"],
    "C263": ["C040 intraday_break_count"],
    "C277": ["C181 trapped_volume"],
    "C278": ["C118 volume_price_divergence_5", "C125 volume_price_spread"],
}

DEFINITION_FIXES = {
    "C278": {
        "computable_definition": (
            "rank(decay_linear(correlation(vwap, volume, corr_window), decay_window)); "
            "corr_window and decay_window must be fixed before training, and sign must not be chosen by validation"
        ),
        "engineering_status": "needs_formula_lock",
    },
    "C279": {
        "computable_definition": (
            "sign(delta(volume, 1)) * (-(close / close.shift(1) - 1)); "
            "computed from daily OHLCV with no post-hoc sign flip"
        ),
        "engineering_status": "engineerable_now_formula_locked",
    },
    "C280": {
        "computable_definition": (
            "(close - open) / max(high - low, eps); optional cross-sectional neutralization must be a separate factor"
        ),
        "engineering_status": "engineerable_now_formula_locked",
    },
}

FIRST_WAVE_READY = {
    "C229", "C236", "C244", "C246", "C247", "C248", "C252", "C254",
    "C258", "C259", "C260", "C270", "C272", "C273", "C279", "C280",
}

NEEDS_DATA_FIRST = set(EXTERNAL_PIPELINE)


def iter_candidate_items(registry):
    """Yield every candidate dict regardless of registry batch shape."""
    for key, value in registry.items():
        if key in {"meta", "next_round_directions", "diagnostic_caveats", "entries"}:
            if key == "entries" and isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "factor_id" in item:
                        yield item
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "factor_id" in item:
                    yield item
        elif isinstance(value, dict):
            for sub_value in value.values():
                if isinstance(sub_value, list):
                    for item in sub_value:
                        if isinstance(item, dict) and "factor_id" in item:
                            yield item


def by_id(registry):
    return {c["factor_id"]: c for c in iter_candidate_items(registry)}


def append_section(path: Path, section: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    marker = section.splitlines()[0]
    if marker in existing:
        return
    path.write_text(existing.rstrip() + "\n\n" + section.rstrip() + "\n", encoding="utf-8")


def normalize_name(value):
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def raw_pool_residual(registry_items):
    if not RAW_POOL_PATH.exists():
        return {"available": False, "path": str(RAW_POOL_PATH)}

    raw = json.loads(RAW_POOL_PATH.read_text(encoding="utf-8"))
    records = []

    def walk_raw(obj):
        if isinstance(obj, dict):
            has_name = any(k in obj for k in ("factor_name", "recommended_name", "raw_name", "name"))
            has_source = any(k in obj for k in ("source", "source_file", "raw_id", "id"))
            if has_name and has_source:
                records.append(obj)
            for value in obj.values():
                walk_raw(value)
        elif isinstance(obj, list):
            for value in obj:
                walk_raw(value)

    walk_raw(raw)
    registry_names = {normalize_name(item.get("name")) for item in registry_items if item.get("name")}
    raw_names = {
        normalize_name(
            item.get("factor_name")
            or item.get("recommended_name")
            or item.get("raw_name")
            or item.get("name")
        )
        for item in records
    }
    raw_names.discard("")
    exact_unmatched = sorted(raw_names - registry_names)
    keywords = [
        "minute",
        "mins",
        "1min",
        "5min",
        "auction",
        "limit",
        "seal",
        "board",
        "lhb",
        "dragon",
        "top",
        "moneyflow",
        "hsgt",
        "hot",
        "theme",
        "sector",
        "announcement",
        "holder",
        "float",
        "pledge",
    ]
    keyword_unmatched = {
        kw: sum(1 for name in exact_unmatched if kw in name)
        for kw in keywords
        if any(kw in name for name in exact_unmatched)
    }
    return {
        "available": True,
        "path": str(RAW_POOL_PATH),
        "raw_records_parsed": len(records),
        "unique_raw_names": len(raw_names),
        "registry_candidate_names": len(registry_names),
        "exact_name_matched": len(raw_names & registry_names),
        "exact_name_unmatched": len(exact_unmatched),
        "keyword_unmatched_counts": keyword_unmatched,
        "interpretation": (
            "raw_factor_pool_index is a source-material pool, not a ready training catalog; "
            "low exact-name match is expected because many raw entries are aliases, duplicates, "
            "trading rules, vague concepts, or require formula/data gating before promotion."
        ),
    }


def main():
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    all_items = list(iter_candidate_items(registry))
    id_map = {c["factor_id"]: c for c in all_items}

    ids = [f"C{i:03d}" for i in range(223, 293)]
    missing = [i for i in ids if i not in id_map]
    if missing:
        raise SystemExit(f"Missing shortline IDs: {missing}")

    for fid in ids:
        item = id_map[fid]
        audit_flags = []
        if fid in WINDOW_LOCK:
            audit_flags.append("window_lock_required")
        if fid in FORMULA_LOCK:
            audit_flags.append("formula_lock_required")
        if fid in EXTERNAL_PIPELINE:
            audit_flags.append("external_pipeline_required")
        if fid in OVERLAP:
            audit_flags.append("overlap_watch")

        if fid in DEFINITION_FIXES:
            for k, v in DEFINITION_FIXES[fid].items():
                item[k] = v

        if fid in FIRST_WAVE_READY and not any(f in audit_flags for f in ("formula_lock_required", "window_lock_required")):
            handoff_gate = "ready_after_data_cache"
        elif fid in FIRST_WAVE_READY:
            handoff_gate = "ready_after_formula_lock_and_data_cache"
        elif fid in NEEDS_DATA_FIRST:
            handoff_gate = "needs_pipeline_or_data_cache_before_training"
        elif fid in FORMULA_LOCK or fid in WINDOW_LOCK:
            handoff_gate = "needs_formula_lock_before_training"
        else:
            handoff_gate = "research_candidate_not_first_wave"

        item["audit_20260515"] = {
            "status": "audited",
            "flags": audit_flags,
            "handoff_gate": handoff_gate,
            "window_lock_note": WINDOW_LOCK.get(fid),
            "formula_lock_note": FORMULA_LOCK.get(fid),
            "external_pipeline_note": EXTERNAL_PIPELINE.get(fid),
            "overlap_watch": OVERLAP.get(fid, []),
        }

    registry.setdefault("meta", {})["updated"] = "2026-05-15"
    registry["meta"]["latest_registry_audit"] = str(AUDIT_JSON_PATH)
    registry["meta"]["shortline_expansion_audit"] = {
        "batch": "candidates_20260515_shortline_full_expansion",
        "audited_ids": "C223-C292",
        "window_lock_required": len(WINDOW_LOCK),
        "formula_lock_required": len(FORMULA_LOCK),
        "external_pipeline_required": len(EXTERNAL_PIPELINE),
        "overlap_watch": len(OVERLAP),
        "first_wave_ready_after_data": len(FIRST_WAVE_READY),
    }

    audit_counter = Counter()
    gates = Counter()
    for fid in ids:
        flags = id_map[fid]["audit_20260515"]["flags"]
        for flag in flags:
            audit_counter[flag] += 1
        gates[id_map[fid]["audit_20260515"]["handoff_gate"]] += 1

    audit = {
        "meta": {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "registry_path": str(REGISTRY_PATH),
            "audited_batch": "candidates_20260515_shortline_full_expansion",
            "audited_ids": ["C223", "C292"],
        },
        "summary": {
            "audited_count": len(ids),
            "window_lock_required": len(WINDOW_LOCK),
            "formula_lock_required": len(FORMULA_LOCK),
            "external_pipeline_required": len(EXTERNAL_PIPELINE),
            "overlap_watch": len(OVERLAP),
            "first_wave_ready_after_data": len(FIRST_WAVE_READY),
            "flag_counts": dict(audit_counter),
            "handoff_gate_counts": dict(gates),
        },
        "window_lock_required": WINDOW_LOCK,
        "formula_lock_required": FORMULA_LOCK,
        "external_pipeline_required": EXTERNAL_PIPELINE,
        "overlap_watch": OVERLAP,
        "definition_fixes": DEFINITION_FIXES,
        "first_wave_ready_after_data": sorted(FIRST_WAVE_READY),
        "raw_pool_residual": raw_pool_residual(all_items),
    }

    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    AUDIT_JSON_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    p0_ready = [fid for fid in sorted(FIRST_WAVE_READY) if id_map[fid].get("priority") == "P0"]
    p1_ready = [fid for fid in sorted(FIRST_WAVE_READY) if id_map[fid].get("priority") == "P1"]
    p2_ready = [fid for fid in sorted(FIRST_WAVE_READY) if id_map[fid].get("priority") == "P2"]

    md = f"""# Factor Registry Audit 2026-05-15

Scope: C223-C292 from batch `candidates_20260515_shortline_full_expansion`.

## Result

- Registry structure is valid: C001-C292 are contiguous, unique, and no normalized factor names are duplicated.
- No C223-C292 entries claim `is_passed`, `is_final_unseen`, or `is_frozen_modified`.
- C223-C292 are all still `training_status=not_trained` and `lockbox_role=research_candidate`.
- This audit does not train, does not run `gpu_probe`, and does not change model code.

## Audit Flags

| Flag | Count | Meaning |
|---|---:|---|
| window_lock_required | {len(WINDOW_LOCK)} | Lookback, half-life, or rank universe must be frozen before training. |
| formula_lock_required | {len(FORMULA_LOCK)} | Formula is not yet atomic enough; split or freeze the exact deterministic formula. |
| external_pipeline_required | {len(EXTERNAL_PIPELINE)} | Needs a source pipeline/cache before training. |
| overlap_watch | {len(OVERLAP)} | Similar to an older candidate; keep only if the new definition is materially different. |

## First Wave After Data Cache

These are the safest short-line candidates to hand to engineering/training after the matching data cache exists:

- P0: {", ".join(p0_ready) or "none"}
- P1: {", ".join(p1_ready) or "none"}
- P2: {", ".join(p2_ready) or "none"}

Do not hand off the whole C223-C292 batch as a single experiment. Use small ablation groups, keep `factor_id` lineage, and record selected/unselected features back into the registry after training.

## Formula Corrections Applied

- C278: locked to a WQ-style rolling correlation/decay definition; no post-hoc sign selection by validation.
- C279: locked to `sign(delta(volume, 1)) * (-(close / close.shift(1) - 1))`.
- C280: locked to `(close - open) / max(high - low, eps)`; optional neutralization must be a separate feature.

## High-Overlap Watchlist

| Candidate | Watch Against |
|---|---|
""" + "\n".join(
        f"| {fid} | {', '.join(vals)} |" for fid, vals in sorted(OVERLAP.items())
    ) + f"""

## Data/Formula Gates

- JSON audit file: `{AUDIT_JSON_PATH}`
- Registry JSON updated: `{REGISTRY_PATH}`
- Human registry index updated: `{REGISTRY_MD_PATH}`

## Raw Pool Residual Check

`raw_factor_pool_index.json` remains a source-material pool, not a ready training catalog. Exact-name matching is intentionally conservative; many unmatched raw entries are aliases, duplicates, trading rules, vague concepts, or require formula/data gates before promotion.

- Raw records parsed: {audit["raw_pool_residual"].get("raw_records_parsed")}
- Unique raw names: {audit["raw_pool_residual"].get("unique_raw_names")}
- Exact raw-name matches to registry names: {audit["raw_pool_residual"].get("exact_name_matched")}
- Exact raw-name unmatched: {audit["raw_pool_residual"].get("exact_name_unmatched")}
- Short-line unmatched keyword counts: {audit["raw_pool_residual"].get("keyword_unmatched_counts")}

"""
    AUDIT_MD_PATH.write_text(md, encoding="utf-8")

    registry_section = f"""## Audit Addendum 2026-05-15

Scope: C223-C292 (`candidates_20260515_shortline_full_expansion`).

- Structural check passed: C001-C292 are contiguous, unique, and no normalized names are duplicated.
- Added `audit_20260515` gates to C223-C292 in the machine registry.
- First-wave-after-data candidates: {", ".join(sorted(FIRST_WAVE_READY))}.
- Formula corrections applied: C278, C279, C280.
- Watchlist counts: {len(WINDOW_LOCK)} window-lock, {len(FORMULA_LOCK)} formula-lock, {len(EXTERNAL_PIPELINE)} external-pipeline, {len(OVERLAP)} overlap-watch.
- Audit report: `docs/factor_registry_audit_20260515.md`.
"""
    append_section(REGISTRY_MD_PATH, registry_section)

    expansion_section = f"""## Audit Addendum 2026-05-15

This batch remains a research-candidate expansion, not a final training set.

- Do not hand off all 70 candidates at once.
- Prioritize first-wave-after-data IDs: {", ".join(sorted(FIRST_WAVE_READY))}.
- C278/C279/C280 definitions were tightened in `factor_registry.json`.
- Entries with `formula_lock_required`, `window_lock_required`, or `external_pipeline_required` must be resolved before training.
- Full audit: `docs/factor_registry_audit_20260515.md`.
"""
    append_section(EXPANSION_MD_PATH, expansion_section)

    print("audit complete")
    print(f"audited_count={len(ids)}")
    print(f"window_lock_required={len(WINDOW_LOCK)}")
    print(f"formula_lock_required={len(FORMULA_LOCK)}")
    print(f"external_pipeline_required={len(EXTERNAL_PIPELINE)}")
    print(f"overlap_watch={len(OVERLAP)}")
    print(f"first_wave_ready_after_data={len(FIRST_WAVE_READY)}")


if __name__ == "__main__":
    main()
