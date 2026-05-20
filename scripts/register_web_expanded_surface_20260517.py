"""Register web-expanded short-line factor candidates.

Scope: factor-library metadata only.
No training, no gpu_probe, no model/frozen config changes.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path


REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
REPORT_PATH = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\web_expanded_factor_search_20260517.md")
HUMAN_REGISTRY_PATH = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\factor_registry.md")
BATCH_KEY = "candidates_20260517_web_expanded_surface"
SEARCH_DATE = "2026-05-17"


SOURCE_EVIDENCE = {
    "bigquant_hf_price_volume": "https://bigquant.com/square/paper/8fcfe5cd-cdd0-4c5e-af7c-f97fe0a15fa3",
    "changjiang_high_position_volume": "https://www.sdyanbao.com/detail/113659",
    "bigquant_auction": "https://bigquant.com/square/paper/cd07e2e7-68ae-47a5-8d41-f166e88700b2",
    "bigquant_auction_fields": "https://mf.bigquant.com/data/datasources/cn_stock_factors_auction",
    "kaiyuan_institution_behavior": "https://bigquant.com/square/paper/99a1c007-ef3e-45dd-8863-41f1d706dfc0",
    "gtja_alpha191": "https://bigquant.com/square/paper/fbca3176-2c2b-4b79-88db-d4d5692adb9d",
    "alpha191_github": "https://github.com/SelenaMa9812/Guotai-Junan-191-Alpha",
    "worldquant_alpha101": "https://arxiv.org/abs/1601.00991",
    "spectral_volume": "https://papers.ssrn.com/sol3/Delivery.cfm/4230610.pdf?abstractid=4230610",
    "order_imbalance": "https://www.sciencedirect.com/science/article/pii/S0304405X03001752",
    "shenzhen_extreme_order_flow": "https://arxiv.org/abs/1003.0168",
}


MINUTE_ASOF = (
    "For 14:57 live use only minute bars with bar_time <= 14:57; "
    "for post-close research use T+1 full-day bars."
)
AUCTION_ASOF = (
    "Use only the final opening auction snapshot known after 09:25. "
    "If the field is revised post-close, shift to T-1."
)
EVENT_ASOF = (
    "Use T-1 or explicit publication/announcement timestamp <= 14:57 only; "
    "same-day post-close records are forbidden for live 14:57."
)


DETAILS = [
    {
        "name": "auction_amount_to_float_mv",
        "family": "auction_open",
        "priority": "P0",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["bigquant_auction_fields", "bigquant_auction"],
        "data_need": "opening auction amount + share_float + prev_close",
        "required_columns": ["auction_open_amount", "free_share", "prev_close"],
        "frequency": "auction_daily",
        "computable_definition": "auction_open_amount / (free_share * prev_close + eps)",
        "asof_rule": AUCTION_ASOF,
        "leakage_risk": "low if auction snapshot timestamp is locked",
        "duplicate_check": "Distinct from auction_open_vwap_ratio and auction_vol_normalized; normalizes auction money by float market value.",
        "engineering_status": "engineerable_after_auction_and_share_float_join",
        "data_status": "needs_auction_field_mapping",
    },
    {
        "name": "auction_participation_breadth",
        "family": "auction_market",
        "priority": "P1",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["bigquant_auction_fields", "bigquant_auction"],
        "data_need": "opening auction universe snapshot",
        "required_columns": ["auction_open_amount"],
        "frequency": "auction_daily_market",
        "computable_definition": "count_stocks(auction_open_amount > threshold) / universe_count",
        "asof_rule": AUCTION_ASOF,
        "leakage_risk": "low if computed only from 09:25 snapshot",
        "duplicate_check": "Market-level auction breadth, not single-stock auction gap or VWAP ratio.",
        "engineering_status": "engineerable_after_auction_universe_cache",
        "data_status": "needs_auction_universe_cache",
    },
    {
        "name": "auction_open_gap_dispersion",
        "family": "auction_market",
        "priority": "P1",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["bigquant_auction_fields", "bigquant_auction"],
        "data_need": "opening auction price + prev_close for universe",
        "required_columns": ["auction_open_price", "prev_close"],
        "frequency": "auction_daily_market",
        "computable_definition": "std_cross_section((auction_open_price - prev_close) / (prev_close + eps))",
        "asof_rule": AUCTION_ASOF,
        "leakage_risk": "low if computed only from 09:25 snapshot",
        "duplicate_check": "Market regime dispersion, not per-stock auction gap.",
        "engineering_status": "engineerable_after_auction_universe_cache",
        "data_status": "needs_auction_universe_cache",
    },
    {
        "name": "lhb_institution_net_to_float",
        "family": "lhb",
        "priority": "P0",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["kaiyuan_institution_behavior"],
        "data_need": "top_inst/top_list institution buy/sell + share_float",
        "required_columns": ["institution_buy_amount", "institution_sell_amount", "free_share", "close"],
        "frequency": "event_daily",
        "computable_definition": "(institution_buy_amount - institution_sell_amount) / (free_share * close + eps)",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium;龙虎榜 records are usually after close, so live use should be T-1 unless timestamp proves earlier availability",
        "duplicate_check": "Refines lhb_net_buy_to_float by isolating institution-exclusive seats.",
        "engineering_status": "engineerable_after_top_inst_backfill",
        "data_status": "needs_top_inst_field_mapping",
    },
    {
        "name": "lhb_buy_seat_concentration_hhi",
        "family": "lhb",
        "priority": "P1",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["kaiyuan_institution_behavior"],
        "data_need": "top_list/top_inst detailed buy seat amounts",
        "required_columns": ["buy_seat_amounts"],
        "frequency": "event_daily",
        "computable_definition": "sum((buy_seat_amount_i / total_buy_amount)^2 for top buy seats)",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium; use T-1 unless publication timestamp is locked",
        "duplicate_check": "Seat concentration for LHB events, not block-trade seller concentration.",
        "engineering_status": "engineerable_if_lhb_seat_detail_exists",
        "data_status": "needs_top_list_detail_cache",
    },
    {
        "name": "insider_trade_net_to_float",
        "family": "holder_trade",
        "priority": "P1",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["data_unlocked:stk_holdertrade"],
        "data_need": "stk_holdertrade + share_float",
        "required_columns": ["holder_buy_shares", "holder_sell_shares", "free_share"],
        "frequency": "event_daily",
        "computable_definition": "(holder_buy_shares - holder_sell_shares) / (free_share + eps)",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium; use announcement timestamp or T-1",
        "duplicate_check": "New insider/holder-trade event family; not covered by moneyflow or LHB factors.",
        "engineering_status": "engineerable_after_stk_holdertrade_backfill",
        "data_status": "needs_stk_holdertrade_cache",
    },
    {
        "name": "insider_trade_recency_decay",
        "family": "holder_trade",
        "priority": "P2",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["data_unlocked:stk_holdertrade"],
        "data_need": "stk_holdertrade event dates + net direction",
        "required_columns": ["holder_trade_date", "holder_net_shares"],
        "frequency": "event_daily",
        "computable_definition": "sign(holder_net_shares) * exp(-days_since_latest_holder_trade / half_life)",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium; use announcement timestamp or T-1",
        "duplicate_check": "Recency decay of insider action, distinct from net trade size.",
        "engineering_status": "engineerable_after_stk_holdertrade_backfill",
        "data_status": "needs_stk_holdertrade_cache",
    },
    {
        "name": "survey_participant_intensity_change",
        "family": "research_event",
        "priority": "P1",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["data_unlocked:stk_surv", "kaiyuan_institution_behavior"],
        "data_need": "stk_surv participant count and institution type",
        "required_columns": ["survey_date", "participant_count"],
        "frequency": "event_daily",
        "computable_definition": "zscore(participant_count, trailing_120d_by_stock) - zscore(prev_participant_count, trailing_120d_by_stock)",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium; use survey/publication timestamp or T-1",
        "duplicate_check": "Different from research_survey_recency_decay; measures intensity acceleration.",
        "engineering_status": "engineerable_after_survey_backfill",
        "data_status": "needs_stk_surv_cache",
    },
    {
        "name": "forecast_directional_consensus",
        "family": "forecast_event",
        "priority": "P1",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["data_unlocked:forecast_vip"],
        "data_need": "forecast_vip directional forecast fields",
        "required_columns": ["forecast_type", "forecast_net_profit_low", "forecast_net_profit_high"],
        "frequency": "event_daily",
        "computable_definition": "signed_consensus(forecast_type, forecast_net_profit_mid_change) aggregated over latest event window",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium; use forecast announcement timestamp or T-1",
        "duplicate_check": "Different from forecast_revision_dispersion_change; captures direction/consensus rather than dispersion.",
        "engineering_status": "engineerable_after_forecast_backfill",
        "data_status": "needs_forecast_vip_cache",
    },
    {
        "name": "minute_return_state_transition_entropy",
        "family": "minute_hf",
        "priority": "P1",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["academic_intraday_markov", "shenzhen_extreme_order_flow"],
        "data_need": "1min bars",
        "required_columns": ["close"],
        "frequency": "1min",
        "computable_definition": "entropy of transition matrix over discretized 1min return states {-1,0,+1} up to 14:57",
        "asof_rule": MINUTE_ASOF,
        "leakage_risk": "low if minute cutoff is enforced",
        "duplicate_check": "State-transition entropy, not plain volume entropy or realized volatility.",
        "engineering_status": "engineerable_after_1min_cache",
        "data_status": "stk_mins_1_available_needs_full_cache_gate",
    },
    {
        "name": "minute_extreme_pre_peak_ratio",
        "family": "minute_hf",
        "priority": "P1",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["shenzhen_extreme_order_flow"],
        "data_need": "1min bars",
        "required_columns": ["close", "volume", "amount"],
        "frequency": "1min",
        "computable_definition": "max(volume or amount in N minutes before the largest absolute 1min return) / (max after event + eps)",
        "asof_rule": MINUTE_ASOF,
        "leakage_risk": "low for post-event within observed window; for live only use events observed before cutoff",
        "duplicate_check": "Captures lead-lag around intraday extremes, not generic large_amount_bar_push_return.",
        "engineering_status": "engineerable_after_1min_cache",
        "data_status": "stk_mins_1_available_needs_full_cache_gate",
    },
    {
        "name": "minute_volume_spectral_residual",
        "family": "minute_hf",
        "priority": "P1",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["spectral_volume"],
        "data_need": "1min bars + trailing historical volume profiles",
        "required_columns": ["volume"],
        "frequency": "1min",
        "computable_definition": "current intraday volume profile energy after removing historical dominant periodic components",
        "asof_rule": MINUTE_ASOF,
        "leakage_risk": "low if historical profile excludes current future bars",
        "duplicate_check": "Residual after removing periodic curve; distinct from raw minute_periodicity_energy_1_5_10.",
        "engineering_status": "engineerable_after_1min_history_matrix",
        "data_status": "needs_same_clock_volume_history",
    },
    {
        "name": "cumulative_volume_curve_surprise_1457",
        "family": "minute_hf",
        "priority": "P0",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["spectral_volume", "bigquant_hf_price_volume"],
        "data_need": "1min bars + expected intraday volume curve",
        "required_columns": ["volume"],
        "frequency": "1min",
        "computable_definition": "cum_volume_until_1457 / (expected_cum_volume_until_1457_from_same_clock_history + eps)",
        "asof_rule": MINUTE_ASOF,
        "leakage_risk": "low if expected curve is fit only on prior sessions",
        "duplicate_check": "Curve surprise at cutoff, not total volume ratio or tail volume share.",
        "engineering_status": "engineerable_after_1min_history_matrix",
        "data_status": "needs_same_clock_volume_history",
    },
    {
        "name": "minute_volume_synchronization_to_market",
        "family": "minute_market",
        "priority": "P1",
        "source_type": "web_expanded_surface_20260517",
        "source_refs": ["order_imbalance", "spectral_volume"],
        "data_need": "1min all-stock volume profiles",
        "required_columns": ["volume"],
        "frequency": "1min_market",
        "computable_definition": "corr(stock minute volume profile up to cutoff, market aggregate minute volume profile up to cutoff)",
        "asof_rule": MINUTE_ASOF,
        "leakage_risk": "low if all-stock profiles use only cutoff-safe bars",
        "duplicate_check": "Volume synchronization to market, not return beta or minute momentum rank.",
        "engineering_status": "engineerable_after_1min_universe_cache",
        "data_status": "needs_1min_universe_cache",
    },
]


def _walk_factor_objects(obj):
    if isinstance(obj, dict):
        if str(obj.get("factor_id", "")).startswith("C"):
            yield obj
        for value in obj.values():
            yield from _walk_factor_objects(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk_factor_objects(value)


def _remove_existing_batch(registry: dict) -> None:
    old = registry.pop(BATCH_KEY, None)
    if old is not None:
        batches = registry.get("meta", {}).get("candidate_batches", [])
        registry.setdefault("meta", {})["candidate_batches"] = [b for b in batches if b != BATCH_KEY]


def _next_factor_id(registry: dict) -> int:
    ids = []
    for item in _walk_factor_objects(registry):
        fid = item.get("factor_id", "")
        if len(fid) >= 4 and fid[0] == "C" and fid[1:].isdigit():
            ids.append(int(fid[1:]))
    return max(ids, default=0) + 1


def _prepare_details(start_id: int) -> list[dict]:
    prepared = []
    seen_names = set()
    for i, item in enumerate(DETAILS):
        obj = dict(item)
        obj["factor_id"] = f"C{start_id + i:03d}"
        obj["batch"] = BATCH_KEY
        obj["training_status"] = "not_trained"
        obj["lockbox_role"] = "research_candidate"
        obj["depends_on"] = obj.get("depends_on", [])
        obj["notes"] = obj.get("notes", "")
        obj["audit_20260517"] = {
            "status": "audited",
            "checks": [
                "explicit_formula",
                "data_need_named",
                "asof_rule_named",
                "not_exact_duplicate",
                "not_training_result_claim",
            ],
        }
        if obj["name"] in seen_names:
            raise ValueError(f"duplicate new name: {obj['name']}")
        seen_names.add(obj["name"])
        prepared.append(obj)
    return prepared


def _make_batch(details: list[dict]) -> dict:
    by_priority = dict(Counter(d["priority"] for d in details))
    by_family = dict(Counter(d["family"] for d in details))
    return {
        "search_date": SEARCH_DATE,
        "search_round": "web_expanded_surface_after_global_deep_search",
        "purpose": "Broaden public-web factor search beyond the earlier four-path scan; register only computable, asof-explicit short-line candidates.",
        "scope": "factor-library only; no training, no gpu_probe, no model or frozen config edits",
        "source_evidence": SOURCE_EVIDENCE,
        "selection_criteria": [
            "single-column or explicitly broadcast market feature",
            "computable definition is formula-like, not vague NLP advice",
            "data path exists or is a named fetch backlog",
            "14:57/asof rule is explicit",
            "not an exact duplicate of C001-C341 by name or definition",
        ],
        "total": len(details),
        "by_priority": by_priority,
        "by_family": by_family,
        "detail": details,
        "deferred_or_rejected_summary": {
            "alpha191_full_library": "Do not register 191 formulas as one factor. Needs separate formula catalog and dedup pass before individual C IDs.",
            "alpha101_full_library": "Already partly represented by C278-C281 and C338-C340; additional formulas require explicit per-formula translation.",
            "true_l2_orderbook": "OFI/depth/cancel-pressure factors remain deferred unless a stable L2/tick pipeline exists.",
            "pure_social_video_nlp": "Already represented by C286-C289 broad families; needs timestamped scrape and entity mapping before expansion.",
        },
    }


def _render_report(batch: dict) -> str:
    details = batch["detail"]
    lines = [
        "# Web Expanded Short-Line Factor Search 2026-05-17",
        "",
        "Scope: factor-library only. No training, no gpu_probe, no model or frozen config changes.",
        "",
        "## Search Surface",
        "",
    ]
    for key, url in SOURCE_EVIDENCE.items():
        lines.append(f"- `{key}`: {url}")
    lines += [
        "",
        "## Added To Registry",
        "",
        f"- Batch: `{BATCH_KEY}`",
        f"- Count: {batch['total']}",
        f"- ID range: `{details[0]['factor_id']}-{details[-1]['factor_id']}`",
        f"- Priority counts: {batch['by_priority']}",
        f"- Family counts: {batch['by_family']}",
        "",
        "| ID | Name | Priority | Family | Data Need | Engineering | Asof |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in details:
        lines.append(
            f"| {d['factor_id']} | {d['name']} | {d['priority']} | {d['family']} | "
            f"{d['data_need']} | {d['engineering_status']} | {d['asof_rule']} |"
        )
    lines += [
        "",
        "## Deferred / Not Registered",
        "",
    ]
    for key, value in batch["deferred_or_rejected_summary"].items():
        lines.append(f"- `{key}`: {value}")
    lines += [
        "",
        "## Validation",
        "",
        "1. JSON loads: PASS",
        "2. C IDs are continuous: PASS",
        "3. No duplicate factor_id: PASS",
        "4. No duplicate factor name: PASS",
        "5. meta registry count matches actual C objects: PASS",
        "6. New batch exists and count matches detail length: PASS",
        "7. All new entries have required fields: PASS",
        "8. All new entries are training_status=not_trained: PASS",
        "9. All new entries are lockbox_role=research_candidate: PASS",
        "10. No new entry claims is_passed/is_final_unseen/is_frozen_modified: PASS",
        "",
    ]
    return "\n".join(lines)


def _validate(registry: dict, batch: dict) -> list[str]:
    factors = list(_walk_factor_objects(registry))
    ids = [f["factor_id"] for f in factors]
    nums = sorted(int(fid[1:]) for fid in ids)
    names = [f.get("name") or f.get("column") for f in factors if f.get("name") or f.get("column")]
    checks = []
    assert len(ids) == len(set(ids)), "duplicate factor_id"
    checks.append("No duplicate factor_id")
    assert len(names) == len(set(names)), "duplicate factor name"
    checks.append("No duplicate factor name")
    assert nums == list(range(1, max(nums) + 1)), "non-continuous C IDs"
    checks.append("Continuous C IDs")
    assert registry["meta"]["registry_candidate_count"] == len(factors), "meta count mismatch"
    checks.append("Meta count matches")
    assert BATCH_KEY in registry, "missing new batch"
    assert len(registry[BATCH_KEY]["detail"]) == batch["total"], "batch count mismatch"
    checks.append("New batch count matches")
    for d in registry[BATCH_KEY]["detail"]:
        for field in [
            "factor_id",
            "name",
            "family",
            "priority",
            "computable_definition",
            "data_need",
            "asof_rule",
            "training_status",
            "lockbox_role",
        ]:
            assert field in d and d[field], f"missing field {field} in {d.get('factor_id')}"
        assert d["training_status"] == "not_trained"
        assert d["lockbox_role"] == "research_candidate"
        assert not d.get("is_passed")
        assert not d.get("is_final_unseen")
        assert not d.get("is_frozen_modified")
    checks.append("New entries required fields and lockbox status")
    return checks


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    _remove_existing_batch(registry)
    start_id = _next_factor_id(registry)
    details = _prepare_details(start_id)
    batch = _make_batch(details)
    registry[BATCH_KEY] = batch
    meta = registry.setdefault("meta", {})
    meta["updated"] = SEARCH_DATE
    meta["latest_candidate_batch"] = BATCH_KEY
    batches = list(meta.get("candidate_batches", []))
    if BATCH_KEY not in batches:
        batches.append(BATCH_KEY)
    meta["candidate_batches"] = batches
    meta["web_expanded_surface_20260517"] = {
        "new_candidates": len(details),
        "id_range": f"{details[0]['factor_id']}-{details[-1]['factor_id']}",
        "search_sources": list(SOURCE_EVIDENCE.keys()),
        "deferred": list(batch["deferred_or_rejected_summary"].keys()),
        "training_boundary": "not_trained; research_candidate only",
    }
    meta["registry_candidate_count"] = len(list(_walk_factor_objects(registry)))
    checks = _validate(registry, batch)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(_render_report(batch), encoding="utf-8")

    section = [
        "",
        "---",
        "",
        f"## Web Expanded Search {SEARCH_DATE}",
        "",
        f"> Batch: `{BATCH_KEY}`",
        f"> IDs: `{details[0]['factor_id']}-{details[-1]['factor_id']}`",
        f"> Count: {len(details)}",
        "> Scope: factor-library only; no training, no gpu_probe, no frozen/model changes.",
        "",
        "| ID | Name | Priority | Family | Status |",
        "|----|------|----------|--------|--------|",
    ]
    for d in details:
        section.append(
            f"| {d['factor_id']} | {d['name']} | {d['priority']} | {d['family']} | {d['engineering_status']} |"
        )
    section += [
        "",
        f"Full detail: [web_expanded_factor_search_20260517.md](web_expanded_factor_search_20260517.md)",
        "",
    ]
    text = HUMAN_REGISTRY_PATH.read_text(encoding="utf-8")
    marker = f"## Web Expanded Search {SEARCH_DATE}"
    if marker in text:
        text = text[: text.index("---\n\n" + marker)] if "---\n\n" + marker in text else text
    HUMAN_REGISTRY_PATH.write_text(text.rstrip() + "\n" + "\n".join(section), encoding="utf-8")

    print("Registered", len(details), "candidates", f"{details[0]['factor_id']}-{details[-1]['factor_id']}")
    print("Report", REPORT_PATH)
    print("Checks:", "; ".join(checks))


if __name__ == "__main__":
    main()
