"""Register event-gap candidates found in the saturation pass.

Factor-library only. No training, no gpu_probe, no model/frozen config changes.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
HUMAN_REGISTRY_PATH = ROOT / "docs" / "factor_registry.md"
REPORT_PATH = ROOT / "docs" / "saturation_pass5_event_gap_factor_search_20260519.md"
BATCH = "candidates_20260519_saturation_pass5_event_gap"
TODAY = "2026-05-19"


SOURCES = {
    "raw_pool_index": r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json",
    "short_term_factors_research": str(ROOT / "docs" / "short_term_factors_research.md"),
    "tushare_repurchase": "https://tushare.pro/document/2?doc_id=124",
    "tushare_anns_d": "https://tushare.pro/document/2?doc_id=176",
    "tushare_suspend_d": "https://tushare.pro/document/2?doc_id=214",
}


def factor(
    fid: int,
    name: str,
    family: str,
    priority: str,
    source_refs: list[str],
    raw_factor_ids: list[str],
    raw_idea: str,
    definition: str,
    data_need: str,
    cols: list[str],
    freq: str,
    asof: str,
    dup: str,
    eng: str,
    data_status: str,
    notes: str = "",
) -> dict:
    return {
        "factor_id": f"C{fid:03d}",
        "name": name,
        "family": family,
        "priority": priority,
        "source_type": "saturation_pass5_event_gap_20260519",
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
        "audit_20260519": {
            "status": "audited",
            "checks": [
                "registry_only",
                "no_training_or_gpu_probe",
                "raw_pool_review",
                "web_source_review",
                "duplicate_screened_against_C001_C459",
                "computable_definition_present",
                "data_need_present",
                "asof_rule_present",
                "training_status_not_trained",
                "lockbox_role_research_candidate",
            ],
        },
    }


DETAIL = [
    factor(
        460,
        "buyback_plan_strength",
        "buyback_event",
        "P1",
        ["raw_pool_index", "short_term_factors_research", "tushare_repurchase"],
        ["RAW000612", "RAW002576", "RAW002577"],
        "Repurchase plan announcements can signal management support; stronger plans combine larger cash amount and higher buyback price ceiling.",
        "log1p(plan_amount) / (float_mv + eps) * max(high_limit / close_at_asof - 1, 0) * proc_weight(proc)",
        "repurchase announcement rows, daily close, float market value",
        ["ann_date", "ts_code", "proc", "amount", "high_limit", "low_limit", "close_at_asof", "float_mv"],
        "event_daily",
        "Use ann_date/rec_time if available; otherwise treat announcement rows as after-close and use from next tradable session only.",
        "No C001-C459 candidate covers stock repurchase announcements; this is not holdertrade, pledge, unlock, or block_trade.",
        "engineerable_after_repurchase_backfill",
        "repurchase API is structured; needs 2017+ backfill and proc mapping",
        "Suggested proc_weight: plan/shareholder-approved > implementation > completed; lock before training.",
    ),
    factor(
        461,
        "buyback_execution_pressure",
        "buyback_event",
        "P1",
        ["raw_pool_index", "tushare_repurchase"],
        ["RAW002576", "RAW002577"],
        "Actual repurchase execution can create realized demand support and reduce free float pressure.",
        "rolling_sum(actual_repurchase_amount, N days) / (rolling_mean(daily_amount, N) + eps)",
        "repurchase implementation/completion rows and daily amount",
        ["ann_date", "ts_code", "proc", "amount", "vol", "daily_amount"],
        "event_daily",
        "Use only implementation/completion announcements whose ann_date or rec_time is <= cutoff; no same-day use without timestamp.",
        "C460 measures plan strength; C461 measures realized execution intensity versus trading liquidity.",
        "engineerable_after_repurchase_backfill",
        "requires deduplication of repeated repurchase progress announcements",
    ),
    factor(
        462,
        "buyback_price_support_gap",
        "buyback_event",
        "P2",
        ["raw_pool_index", "short_term_factors_research", "tushare_repurchase"],
        ["RAW000612"],
        "When an active buyback ceiling is far above current price, the program may act as a support/attention anchor.",
        "max(active_high_limit / close_at_asof - 1, 0) * exp(-days_to_expiry / tau)",
        "active repurchase plan high_limit/exp_date and daily close",
        ["trade_date", "ts_code", "active_high_limit", "exp_date", "close_at_asof"],
        "daily",
        "Only active plans announced before cutoff may be used; expire at exp_date or completion announcement.",
        "C460 includes amount and plan strength; C462 isolates price-ceiling support gap for active programs.",
        "needs_active_repurchase_state_table",
        "P2 until active-plan state table is built without double-counting overlapping plans",
    ),
    factor(
        463,
        "esop_discount_incentive_gap",
        "employee_stock_ownership",
        "P2",
        ["raw_pool_index", "short_term_factors_research", "tushare_anns_d"],
        ["RAW000613"],
        "Employee stock ownership plans with meaningful discount and lock-up can create incentive/support narratives.",
        "max(1 - esop_purchase_price / close_at_asof, 0) * log1p(plan_amount) / (float_mv + eps)",
        "announcement title/pdf extraction for employee stock ownership plan, purchase price, amount, lock-up; daily close and float_mv",
        ["ann_date", "rec_time", "ts_code", "title", "url", "esop_purchase_price", "plan_amount", "lockup_months", "close_at_asof", "float_mv"],
        "event_daily",
        "Use ann_date/rec_time; if PDF parsing is post-close only, use T+1. Never use completion details before announcement time.",
        "No C001-C459 candidate captures ESOP discount/lock-up event; distinct from holdertrade and equity pledge.",
        "needs_anns_d_pdf_parser",
        "P2 because structured ESOP fields must be extracted from announcements",
    ),
    factor(
        464,
        "private_placement_break_repair_gap",
        "private_placement_event",
        "P2",
        ["raw_pool_index", "short_term_factors_research", "tushare_anns_d"],
        ["RAW000610", "RAW000614", "RAW001130", "RAW002674"],
        "Stocks trading below recent private-placement price may have repair/support narratives if the placement is recent and large.",
        "max(private_placement_price / close_at_asof - 1, 0) * placement_amount / (float_mv + eps) * recency_decay",
        "private placement announcement or issuance details, placement price/amount, daily close, float_mv",
        ["ann_date", "rec_time", "ts_code", "private_placement_price", "placement_amount", "close_at_asof", "float_mv"],
        "event_daily",
        "Use only placement terms announced before cutoff; if parsed from announcements after close, use next tradable session.",
        "No C001-C459 candidate targets private-placement break/reversion support; not the same as unlock pressure or buyback.",
        "needs_private_placement_parser",
        "P2 until placement terms are reliably extracted and locked",
    ),
    factor(
        465,
        "ma_restructure_announcement_surprise",
        "ma_restructure_event",
        "P2",
        ["raw_pool_index", "short_term_factors_research", "tushare_anns_d", "tushare_suspend_d"],
        ["RAW000611", "RAW001129", "RAW002673"],
        "Major asset restructuring/M&A announcements can create short-line event repricing, especially after suspension or material progress updates.",
        "event_score(title/pdf) * log1p(deal_size) / (float_mv + eps) * progress_weight * same_industry_bonus",
        "announcement title/pdf extraction, optional suspend/resume flag, deal size, industry relation, daily close/float_mv",
        ["ann_date", "rec_time", "ts_code", "title", "url", "deal_size", "float_mv", "suspend_type", "resume_date"],
        "event_daily",
        "Use only announcements and suspend/resume records available by cutoff; resumption-day gap features must use open/observed minute data only.",
        "C290/C291 are generic halt-reopen relaxation; C465 is M&A/restructuring-specific event surprise intensity.",
        "needs_anns_d_ma_parser",
        "P2 because text classification and deal-size extraction must be audited",
    ),
]


def iter_candidate_rows(data: dict) -> list[dict]:
    rows: list[dict] = []
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
        "## Saturation Pass 5 Event-Gap Review 2026-05-19",
        "",
        "Purpose: fill event-driven gaps after registry/raw-pool/web saturation checks. Registry only: no training, no gpu_probe, no model/frozen config changes.",
        "",
        f"Batch: `{BATCH}`",
        "",
        "| ID | Name | Priority | Family | Data Need | Status |",
        "|---|---|---:|---|---|---|",
    ]
    for row in DETAIL:
        section.append(
            f"| {row['factor_id']} | `{row['name']}` | {row['priority']} | {row['family']} | {row['data_need']} | {row['engineering_status']} |"
        )
    section.extend(
        [
            "",
            "Asof notes:",
            "- C460-C462 use Tushare `repurchase`; same-day use requires reliable `rec_time`, otherwise use T+1.",
            "- C463-C465 use `anns_d`/PDF-derived event fields; all text extraction must be point-in-time and versioned.",
            "- C465 may optionally join `suspend_d`, but it must not use full-day resumption returns before cutoff.",
        ]
    )
    with HUMAN_REGISTRY_PATH.open("a", encoding="utf-8") as f:
        f.write("\n".join(section) + "\n")


def write_report(validation: dict) -> None:
    lines = [
        "# Saturation Pass 5 Event-Gap Factor Search 2026-05-19",
        "",
        "Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.",
        "",
        "This pass expanded search across broker-report/event ideas, local raw pool, Tushare official API coverage, and prior saturation docs. Literal whole-web exhaustion is impossible, so this report records a reproducible saturation pass and strict non-add reasons.",
        "",
        f"Added candidates: {len(DETAIL)} ({DETAIL[0]['factor_id']} to {DETAIL[-1]['factor_id']})",
        "",
        "| ID | Name | Priority | Family | Frequency | Data Need | Asof / Caveat |",
        "|---|---|---:|---|---|---|---|",
    ]
    for row in DETAIL:
        lines.append(
            f"| {row['factor_id']} | {row['name']} | {row['priority']} | {row['family']} | {row['frequency']} | {row['data_need']} | {row['asof_rule']} |"
        )
    lines.extend(
        [
            "",
            "## Search Surfaces Checked",
            "",
            "- Local registry C001-C459 keyword scan: buyback/repurchase/esop/private placement/MA/restructuring had no registered candidate coverage.",
            "- Local raw pool: buyback RAW000612/RAW002576/RAW002577, ESOP RAW000613, private placement RAW000610/RAW000614/RAW001130/RAW002674, M&A RAW000611/RAW001129/RAW002673.",
            "- Web/API evidence: Tushare `repurchase`, `anns_d`, and `suspend_d` provide the minimum fields or source documents needed to engineer the event families.",
            "- Prior minute, limit-pool, LHB, option, ETF, theme, social, and high-frequency surfaces were rechecked as duplicate-heavy, so no extra C466+ was added from those families in this pass.",
            "",
            "## Non-Adds After Ten Checks",
            "",
            "1. Generic low-open/high-open wording: already covered by auction/gap families such as weak-to-strong, gap fill, opening premium, and auction breadth.",
            "2. Generic seal-order/board wording: already covered by seal amount/time/open-count/board-height families, or requires true L2 order book.",
            "3. Generic minute HCVP/LCVP/VPIN/jump wording: already covered by C356-C387 and C437-C445/C455-C456.",
            "4. Generic LHB/hot-money wording: already covered by C042/C229/C328/C345-C346/C412-C414/C444-C445.",
            "5. Unlock/holdertrade/block-trade wording: already covered by C198-C205, C221, C329-C332, C347-C348, C370.",
            "6. Options/ETF/convertible-bond tails: already covered by C417-C459 unless new data fields are confirmed.",
            "7. Announcement concepts without formula or parseable fields: deferred, not registered.",
            "8. Pure strategy rules without scalar feature definition: rejected.",
            "9. Future-return/next-day-outcome labels: rejected unless recast as point-in-time state variables.",
            "10. Raw aliases that only rename implemented columns: rejected as duplicates.",
            "",
            "## Validation",
            "",
            f"- Total candidates after write: {validation['total_candidates']}",
            f"- Missing IDs: {validation['missing_ids']}",
            f"- Duplicate IDs: {validation['duplicate_ids']}",
            f"- Unsafe status count: {validation['unsafe_status_count']}",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if BATCH in data:
        raise SystemExit(f"{BATCH} already exists; refusing to duplicate")

    existing_rows = iter_candidate_rows(data)
    existing_ids = {row["factor_id"] for row in existing_rows}
    new_ids = {row["factor_id"] for row in DETAIL}
    overlap = sorted(existing_ids & new_ids)
    if overlap:
        raise SystemExit(f"ID overlap: {overlap}")

    existing_names = {str(row.get("name", "")).lower() for row in existing_rows}
    dup_names = sorted(row["name"] for row in DETAIL if row["name"].lower() in existing_names)
    if dup_names:
        raise SystemExit(f"Name overlap: {dup_names}")

    data[BATCH] = {
        "search_date": TODAY,
        "search_round": "saturation_pass5_event_gap",
        "purpose": "event-driven gap fill after whole-surface saturation review",
        "scope": "factor-library only; no training; no gpu_probe; no model/frozen config changes",
        "source_evidence": SOURCES,
        "selection_gate": [
            "explicit computable scalar definition",
            "named data need and required columns",
            "asof rule and leakage boundary",
            "non-duplicate against C001-C459",
            "source has either local raw-pool evidence or official API/document support",
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
    meta["saturation_pass5_event_gap_20260519"] = {
        "added_count": len(DETAIL),
        "id_range": [DETAIL[0]["factor_id"], DETAIL[-1]["factor_id"]],
        "priority_counts": dict(Counter(row["priority"] for row in DETAIL)),
        "family_counts": dict(Counter(row["family"] for row in DETAIL)),
        "note": "Registered only event-driven gaps that survived duplicate/asof/data checks.",
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
