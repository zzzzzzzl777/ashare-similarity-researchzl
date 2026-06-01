"""Register final tail candidates from the saturation review.

Factor-library only. No training, no gpu_probe, no model/frozen config changes.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
HUMAN_REGISTRY_PATH = ROOT / "docs" / "factor_registry.md"
REPORT_PATH = ROOT / "docs" / "saturation_pass3_tail_factor_search_20260518.md"
BATCH = "candidates_20260518_saturation_pass3_tail"
TODAY = "2026-05-18"


SOURCES = {
    "raw_pool_index": r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json",
    "factor_data_availability_audit": str(ROOT / "docs" / "factor_data_availability_audit.md"),
    "option_factor_report": "https://bigquant.com/square/paper/14d6d637-8496-44a1-b17b-3b6ba54985a4",
    "etf_factor_report": "https://bigquant.com/square/paper/2e0f3709-241e-41b9-a3ea-c79c1e088c66",
    "hf_bigquant": "https://bigquant.com/square/paper/8fcfe5cd-cdd0-4c5e-af7c-f97fe0a15fa3",
}


def factor(fid, name, family, priority, source_refs, raw_factor_ids, raw_idea, definition, data_need, cols, freq, asof, dup, eng, data_status, notes=""):
    return {
        "factor_id": f"C{fid:03d}",
        "name": name,
        "family": family,
        "priority": priority,
        "source_type": "saturation_pass3_tail_20260518",
        "source_refs": source_refs,
        "raw_factor_ids": raw_factor_ids,
        "raw_idea": raw_idea,
        "computable_definition": definition,
        "data_need": data_need,
        "required_columns": cols,
        "frequency": freq,
        "asof_rule": asof,
        "leakage_risk": "none if the stated asof rule is enforced",
        "duplicate_check": dup,
        "engineering_status": eng,
        "data_status": data_status,
        "training_status": "not_trained",
        "lockbox_role": "research_candidate",
        "batch": BATCH,
        "depends_on": [],
        "notes": notes,
        "audit_20260518": {
            "status": "audited",
            "checks": [
                "tail_saturation_review",
                "raw_pool_top_remaining_review",
                "duplicate_screened_against_C001_C450",
                "computable_definition_present",
                "data_need_present",
                "asof_rule_present",
                "not_training_result_claim",
            ],
        },
    }


DETAIL = [
    factor(
        451,
        "option_unusual_volume_shock",
        "option_market",
        "P2",
        ["raw_pool_index", "option_factor_report"],
        ["RAW003075"],
        "Option volume spikes can indicate informed demand or volatility-event hedging.",
        "option_volume_t / (rolling_mean(option_volume,20) + eps)",
        "option daily volume by underlying and option type; underlying to stock/ETF mapping",
        ["trade_date", "underlying_code", "option_volume", "option_type"],
        "daily",
        "Use after-close opt_daily for T+1 unless intraday option volume is timestamped.",
        "C418 is PCR level; this is total unusual option activity shock.",
        "needs_option_daily_pipeline",
        "P2 until underlying mapping and option coverage are confirmed",
    ),
    factor(
        452,
        "option_iv_rv_spread",
        "option_market",
        "P2",
        ["raw_pool_index", "option_factor_report"],
        ["RAW003074"],
        "Implied volatility minus realized volatility can proxy fear or overpricing of near-term risk.",
        "atm_implied_volatility - realized_volatility_Nd",
        "option implied volatility, underlying realized volatility",
        ["trade_date", "underlying_code", "atm_iv", "realized_volatility"],
        "daily",
        "Use only IV fields available by date; realized volatility must not include future returns beyond T.",
        "C419 is cross-sectional IV skew; this is level spread versus realized volatility.",
        "needs_option_iv_fields",
        "P2 until IV field reliability is audited",
    ),
    factor(
        453,
        "option_iv_term_structure_inversion",
        "option_market",
        "P2",
        ["raw_pool_index", "option_factor_report"],
        ["RAW003071"],
        "Near-month IV above next-month IV can indicate short-term fear or event pressure.",
        "near_month_atm_iv / (next_month_atm_iv + eps) - 1",
        "option IV by maturity and underlying",
        ["trade_date", "underlying_code", "near_month_atm_iv", "next_month_atm_iv"],
        "daily",
        "Use after-close option chain data for T+1 unless timestamped intraday option chain is available.",
        "C419 covers put-call skew; C453 covers maturity term-structure inversion.",
        "needs_option_iv_term_structure",
        "P2 until maturity mapping is locked",
    ),
    factor(
        454,
        "etf_premium_discount_arbitrage_pressure",
        "etf_flow",
        "P1",
        ["raw_pool_index", "etf_factor_report"],
        ["RAW001976", "RAW002376", "RAW002377", "RAW002986"],
        "ETF premium/discount can create arbitrage pressure that transmits to holdings.",
        "sum(weight_ij * etf_premium_discount_j * abs(etf_premium_discount_j) for ETF j holding stock i)",
        "ETF premium/discount or IOPV, ETF holdings weights, constituent stock mapping",
        ["trade_date", "ts_code", "fund_code", "weight", "premium_discount"],
        "daily_or_intraday_if_iopv",
        "Daily ETF premium is T+1; intraday IOPV premium can be same-day only if timestamped before cutoff.",
        "C417 maps ETF flow; C454 maps ETF premium/discount arbitrage pressure.",
        "needs_etf_iopv_or_premium_pipeline",
        "P1 if daily ETF premium is cached; same-day variant requires IOPV timestamps",
    ),
    factor(
        455,
        "last_5min_return_pressure",
        "minute_tail",
        "P1",
        ["raw_pool_index", "hf_bigquant"],
        ["RAW003057"],
        "Last-5-minute return captures final capital push or exit pressure.",
        "close_last_observed / close_5min_before_last_observed - 1",
        "1min bars close",
        ["trade_date", "ts_code", "bar_time", "close"],
        "1min",
        "At 14:57 use the last observed 5-minute window ending at or before cutoff; never use post-cutoff bars.",
        "C133 is last-30-minute return; C455 isolates the final 5-minute pressure.",
        "engineerable_after_1min_cache",
        "separate 14:57 and full-close variants",
    ),
    factor(
        456,
        "intraday_return_curve_shape",
        "minute_path",
        "P1",
        ["raw_pool_index", "hf_bigquant"],
        ["RAW003053", "RAW003054", "RAW003055", "RAW003056"],
        "The shape of returns across open, midday, afternoon, and tail windows can distinguish trend from fade.",
        "weighted_slope([first5_return, first15_return, midday_return, afternoon_start_return, tail_return])",
        "1min bars close and fixed intraday windows",
        ["trade_date", "ts_code", "bar_time", "close"],
        "1min",
        "Only include windows completed by cutoff; missing future windows must be masked for live replay.",
        "Existing factors cover individual first-volume or last-30 return; this captures the return curve shape.",
        "engineerable_after_1min_cache",
        "window weights must be fixed before training",
    ),
    factor(
        457,
        "t_plus1_limit_sell_pressure",
        "limit_board",
        "P1",
        ["raw_pool_index"],
        ["RAW003030"],
        "After a prior limit-up, T+1 sellability can create natural sell pressure from trapped/early holders.",
        "I(stock was limit_up on T-1) * turnover_pressure_proxy_T",
        "limit_pool prior-day limit-up flag and current turnover/auction/minute volume",
        ["trade_date", "ts_code", "is_prev_limit_up", "turnover_rate", "auction_amount", "amount_to_cutoff"],
        "daily_or_1min",
        "Use prior-day limit flag and current cutoff-bounded turnover/auction volume.",
        "No C001-C450 candidate explicitly encodes T+1 sell-pressure after previous limit-up.",
        "needs_limit_pool_turnover_join",
        "direction should be learned; can be positive for strong relay or negative for sell pressure",
    ),
    factor(
        458,
        "index_option_expiry_week_gate",
        "option_market_regime",
        "P2",
        ["raw_pool_index", "option_factor_report"],
        ["RAW003031"],
        "Index option/futures expiry week can change market-wide volatility and dealer hedging pressure.",
        "I(trade_date in index_option_expiry_week) * market_volatility_or_pcr_state",
        "trading calendar, option expiry calendar, market volatility/PCR state",
        ["trade_date", "is_expiry_week", "market_volatility", "pcr"],
        "daily",
        "Expiry calendar is known in advance; market state inputs must obey their own asof rules.",
        "No existing option-market candidate encodes expiry-calendar regime.",
        "needs_option_expiry_calendar",
        "P2 market-regime gate broadcast to stocks",
    ),
    factor(
        459,
        "hot_concept_count_exposure",
        "theme_attention",
        "P2",
        ["raw_pool_index"],
        ["RAW003017"],
        "Stocks attached to multiple currently hot concepts may receive broader short-line attention.",
        "count(theme_id where theme_heat_percentile >= threshold and stock belongs to theme_id)",
        "stock-theme membership and theme heat score",
        ["trade_date", "ts_code", "theme_id", "theme_heat_percentile"],
        "daily_or_cutoff",
        "Use only theme heat available by cutoff; full-day theme heat is T+1.",
        "C169/C170 describe theme exposure weights; C459 counts only currently hot concepts.",
        "needs_theme_heat_pipeline",
        "P2 until theme heat source is versioned",
    ),
]


def iter_candidate_rows(data: dict) -> list[dict]:
    rows = []
    for key in data.get("meta", {}).get("candidate_batches", []):
        batch = data.get(key)
        if not isinstance(batch, dict):
            continue
        for field in ("detail", "p0", "p1", "p2", "blocked"):
            entries = batch.get(field)
            if isinstance(entries, list):
                rows.extend(x for x in entries if isinstance(x, dict) and x.get("factor_id"))
    return rows


def append_human_registry() -> None:
    section = [
        "",
        "## Saturation Pass 3 Tail Review 2026-05-18",
        "",
        "Purpose: final tail review of top remaining raw-pool candidates after pass 2. Registry only: no training, no gpu_probe, no model/frozen config changes.",
        "",
        f"Batch: `{BATCH}`",
        "",
        "| ID | Name | Priority | Family | Data Need | Status |",
        "|---|---|---:|---|---|---|",
    ]
    for row in DETAIL:
        section.append(f"| {row['factor_id']} | `{row['name']}` | {row['priority']} | {row['family']} | {row['data_need']} | {row['engineering_status']} |")
    section.extend([
        "",
        "Asof notes:",
        "- C451-C453 and C458 are option-market candidates; normally T+1 unless timestamped intraday option data exists.",
        "- C454 is ETF premium/discount; daily version is T+1, intraday IOPV version requires timestamps.",
        "- C455-C457 can be cutoff-bounded with 1min/auction/limit data.",
        "- C459 requires timestamped or versioned theme heat.",
    ])
    with HUMAN_REGISTRY_PATH.open("a", encoding="utf-8") as f:
        f.write("\n".join(section) + "\n")


def write_report(validation: dict) -> None:
    lines = [
        "# Saturation Pass 3 Tail Factor Search 2026-05-18",
        "",
        "Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.",
        "",
        f"Added candidates: {len(DETAIL)} ({DETAIL[0]['factor_id']} to {DETAIL[-1]['factor_id']})",
        "",
        "| ID | Name | Priority | Family | Frequency | Data Need | Asof / Caveat |",
        "|---|---|---:|---|---|---|---|",
    ]
    for row in DETAIL:
        lines.append(f"| {row['factor_id']} | {row['name']} | {row['priority']} | {row['family']} | {row['frequency']} | {row['data_need']} | {row['asof_rule']} |")
    lines.extend([
        "",
        "## Non-Adds After Tail Review",
        "",
        "- Generic technical aliases such as Bollinger position and MA distance remain covered by the technical bank.",
        "- Basic board-count, seal-time, one-word-board, and open-count aliases are already represented by C-series limit-board features.",
        "- L2/tick/orderbook items remain blocked.",
        "",
        "## Validation",
        "",
        f"- Total candidates after write: {validation['total_candidates']}",
        f"- Missing IDs: {validation['missing_ids']}",
        f"- Duplicate IDs: {validation['duplicate_ids']}",
        f"- Unsafe status count: {validation['unsafe_status_count']}",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if BATCH in data:
        raise SystemExit(f"{BATCH} already exists; refusing to duplicate")
    existing_ids = {row["factor_id"] for row in iter_candidate_rows(data)}
    overlap = sorted(existing_ids & {row["factor_id"] for row in DETAIL})
    if overlap:
        raise SystemExit(f"ID overlap: {overlap}")

    data[BATCH] = {
        "search_date": TODAY,
        "search_round": "saturation_pass3_tail",
        "purpose": "final tail review of top remaining raw-pool candidates",
        "scope": "factor-library only; no training; no gpu_probe; no model/frozen config changes",
        "source_evidence": SOURCES,
        "selection_gate": [
            "explicit computable scalar definition",
            "named data need and required columns",
            "asof rule and leakage boundary",
            "non-duplicate against C001-C450",
            "training_status remains not_trained",
            "lockbox_role remains research_candidate",
        ],
        "total": len(DETAIL),
        "by_priority": dict(Counter(row["priority"] for row in DETAIL)),
        "by_family": dict(Counter(row["family"] for row in DETAIL)),
        "detail": DETAIL,
    }

    meta = data.setdefault("meta", {})
    batches = meta.setdefault("candidate_batches", [])
    if BATCH not in batches:
        batches.append(BATCH)
    meta["updated"] = TODAY
    meta["latest_candidate_batch"] = BATCH
    meta["saturation_pass3_tail_20260518"] = {
        "added_count": len(DETAIL),
        "id_range": [DETAIL[0]["factor_id"], DETAIL[-1]["factor_id"]],
        "priority_counts": dict(Counter(row["priority"] for row in DETAIL)),
        "family_counts": dict(Counter(row["family"] for row in DETAIL)),
    }

    all_rows = iter_candidate_rows(data)
    all_ids = [row["factor_id"] for row in all_rows]
    numeric_ids = sorted(int(fid[1:]) for fid in all_ids if fid.startswith("C") and fid[1:].isdigit())
    missing = [f"C{i:03d}" for i in range(1, max(numeric_ids) + 1) if i not in numeric_ids]
    duplicates = sorted(fid for fid, count in Counter(all_ids).items() if count > 1)
    unsafe_status_count = sum(
        int(bool(row.get("is_passed"))) + int(bool(row.get("is_final_unseen"))) + int(bool(row.get("is_frozen_modified")))
        for row in all_rows
    )
    meta["registry_candidate_count"] = len(set(all_ids))
    validation = {
        "total_candidates": meta["registry_candidate_count"],
        "missing_ids": missing,
        "duplicate_ids": duplicates,
        "unsafe_status_count": unsafe_status_count,
    }

    REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    append_human_registry()
    write_report(validation)
    print(f"Added {len(DETAIL)} candidates: {DETAIL[0]['factor_id']}-{DETAIL[-1]['factor_id']}")
    print(f"Total candidates: {validation['total_candidates']}")
    print(f"Missing IDs: {validation['missing_ids']}")
    print(f"Duplicate IDs: {validation['duplicate_ids']}")
    print(f"Unsafe status count: {validation['unsafe_status_count']}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
