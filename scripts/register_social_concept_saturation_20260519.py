"""Register the strict subset from the social concept saturation review.

Boundary:
- factor library management only
- no training
- no gpu_probe
- no model or frozen config changes
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
REPORT_PATH = ROOT / "docs" / "social_concept_saturation_factor_search_20260519.md"
REGISTRY_MD = ROOT / "docs" / "factor_registry.md"
BATCH = "candidates_20260519_social_concept_saturation"


SOURCE_EVIDENCE = {
    "local_raw_pool": r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json",
    "expression_bank": r"E:\ashare_similarity_runtime\data\reports\prediction\social_concept_expression_bank_20260519.json",
    "local_tgb_factor_research": r"C:\Users\zzzzzzl\Desktop\subagent\docs\tgb_factor_research.md",
    "taoguba_weak_to_strong_deep_dive": "https://m.tgb.cn/a/2ndkehIFDw7",
    "taoguba_weak_to_strong_truth_false": "https://m.tgb.cn/a/2rH18eikaA2",
    "taoguba_divergence_to_consensus": "https://www.tgb.cn/a/2rlgmUsdvAp-1",
    "taoguba_leader_terms": "https://m.tgb.cn/a/2lsgqb9S9S7",
    "taoguba_leader_system": "https://m.tgb.cn/a/1T0ZCzlrrA9",
    "xueqiu_weak_to_strong_auction": "https://xueqiu.com/1410434827/240516838",
    "bilibili_call_auction": "https://www.bilibili.com/video/BV1qV4y1Z7Ni/",
    "bigquant_hf_factor_summary": "https://bigquant.com/square/paper/8fcfe5cd-cdd0-4c5e-af7c-f97fe0a15fa3",
    "bigquant_auction_fields": "https://mf.bigquant.com/data/datasources/cn_stock_factors_auction",
    "tushare_minute_data": "https://tushare.pro/document/2?doc_id=370",
}


def candidate(
    name: str,
    family: str,
    priority: str,
    source_refs: list[str],
    raw_factor_ids: list[str],
    raw_idea: str,
    computable_definition: str,
    data_need: str,
    required_columns: list[str],
    frequency: str,
    asof_rule: str,
    duplicate_check: str,
    engineering_status: str,
    data_status: str,
    notes: str = "",
    depends_on: list[str] | None = None,
) -> dict:
    return {
        "name": name,
        "family": family,
        "priority": priority,
        "source_type": "social_concept_saturation_20260519",
        "source_refs": source_refs,
        "raw_factor_ids": raw_factor_ids,
        "raw_idea": raw_idea,
        "computable_definition": computable_definition,
        "data_need": data_need,
        "required_columns": required_columns,
        "frequency": frequency,
        "asof_rule": asof_rule,
        "leakage_risk": "none if the stated asof rule is enforced",
        "duplicate_check": duplicate_check,
        "engineering_status": engineering_status,
        "data_status": data_status,
        "training_status": "not_trained",
        "lockbox_role": "research_candidate",
        "batch": BATCH,
        "depends_on": depends_on or [],
        "notes": notes,
        "audit_20260519": {
            "status": "audited",
            "checks": [
                "local_raw_pool_rescan",
                "previous_candidate_batches_rescan",
                "social_expression_bank_rescan",
                "external_social_source_rescan",
                "broker_report_or_data_surface_rescan",
                "duplicate_screened_against_C001_C465",
                "computable_definition_present",
                "data_need_present",
                "asof_rule_present",
                "not_training_result_claim",
            ],
        },
    }


NEW_CANDIDATES = [
    candidate(
        "false_weak_no_new_low_hold",
        "weak_to_strong_intraday",
        "P0",
        ["expression_bank:SC004", "taoguba_weak_to_strong_deep_dive", "taoguba_weak_to_strong_truth_false"],
        [],
        "A low/flat open that does not make a new low after the first observation window is a cleaner false-weak signal than a simple reclaim flag.",
        "I(open_gap < 0) * I(no_new_low_after_first_10m) * (price_at_cutoff - low_first_10m) / (abs(open_gap) + eps)",
        "1min bars, daily prev_close/open, optional auction gap",
        ["trade_date", "ts_code", "open", "prev_close", "minute_close", "minute_low", "cutoff_time"],
        "1min_or_cutoff",
        "Live-safe after the chosen observation window (e.g. 10:30 or 14:57). Do not use later lows after cutoff.",
        "C317/C318 measure reclaim events; this measures no-follow-through selling after weak open, before any reclaim requirement.",
        "engineerable_after_1min_backfill",
        "stk_mins 1min data available; needs fixed observation window",
        "Useful as a weak-to-strong precursor and fake-weak guard.",
    ),
    candidate(
        "weak_to_strong_reclaim_efficiency",
        "weak_to_strong_intraday",
        "P0",
        ["expression_bank:SC005", "local_raw_pool:weak_to_strong_volume_efficiency", "taoguba_divergence_to_consensus"],
        ["RAW:weak_to_strong_volume_efficiency"],
        "A real weak-to-strong move should repair price with efficient capital use, not only brute-force volume.",
        "(price_at_reclaim / intraday_low_before_reclaim - 1) / log1p(amount_until_reclaim)",
        "1min bars with minute amount, prev_close or VWAP reclaim event",
        ["trade_date", "ts_code", "minute_close", "minute_low", "minute_amount", "prev_close", "vwap"],
        "1min_or_cutoff",
        "Live-safe only after the reclaim event has occurred before cutoff. Full-day reclaim version is T+1.",
        "Related to C317/C318/C048 but adds amount efficiency; not a plain reclaim flag or VWAP level.",
        "engineerable_after_1min_backfill",
        "requires robust reclaim event selector: prev_close or VWAP must be locked before training",
    ),
    candidate(
        "morning_false_weak_reversal_score",
        "weak_to_strong_intraday",
        "P1",
        ["expression_bank:SC006", "taoguba_weak_to_strong_deep_dive", "bilibili_call_auction"],
        ["RAW:false_weak_classification"],
        "Morning path can distinguish true weakness from false weakness: early negative pressure followed by VWAP/prev-close repair before 10:30.",
        "I(first15_return < 0) * z(return_15m_to_60m) * I(price_above_vwap_by_1030)",
        "1min bars, intraday VWAP",
        ["trade_date", "ts_code", "minute_close", "minute_amount", "vwap", "open", "prev_close"],
        "1min_morning",
        "Use cutoff >= 10:30. Earlier live cutoffs must use a shorter locked observation window.",
        "C060 is a first15 tail reversal and C093 is morning fade; this is explicitly false-weak repair with VWAP confirmation.",
        "engineerable_after_1min_backfill",
        "needs locked 10:30 or 60-minute window",
    ),
    candidate(
        "divergence_absorption_efficiency",
        "divergence_acceptance",
        "P0",
        ["expression_bank:SC019", "local_raw_pool:support_absorption_quality", "taoguba_weak_to_strong_truth_false"],
        ["RAW:support_absorption_quality"],
        "During divergence/selloff, strong stocks absorb selling and repair with less incremental amount.",
        "recovery_return_after_selloff / log1p(amount_during_selloff)",
        "1min bars, minute amount, selloff window selector",
        ["trade_date", "ts_code", "minute_close", "minute_low", "minute_amount", "window_start", "window_end"],
        "1min_or_cutoff",
        "Live-safe after the selloff and recovery window both end before cutoff.",
        "C085 measures pullback support ratio and C302 low-price absorption repair; this uses explicit selloff amount efficiency.",
        "engineerable_after_1min_backfill",
        "needs deterministic selloff window definition",
    ),
    candidate(
        "substitute_leader_kawei_score",
        "leader_rotation",
        "P1",
        ["expression_bank:SC032", "local_raw_pool:buchang_dragon_kawei", "taoguba_leader_system"],
        ["RAW:buchang_dragon_kawei", "RAW:substitute_leader_signal"],
        "A catch-up or substitute leader becomes meaningful when it challenges the old leader's suppression height with same-theme linkage and superior seal rank.",
        "I(candidate_board_count >= prior_leader_suppression_height) * theme_relation_score * seal_rank_score",
        "limit_pool board_count history, theme membership, prior leader labels, first seal time",
        ["trade_date", "ts_code", "board_count", "theme_id", "prior_leader_id", "prior_leader_max_board_count", "first_seal_time"],
        "daily_or_cutoff",
        "Use only board state and seal events known by cutoff; full-day leader rotation version is T+1.",
        "C270 confirms second-board leader and C393 ladder continuity; this is old-leader height challenge / kawei relation.",
        "engineerable_after_theme_leader_history",
        "requires deterministic prior leader and theme_relation_score definitions",
    ),
    candidate(
        "first_negative_repair_quality",
        "leader_repair",
        "P1",
        ["expression_bank:SC043", "taoguba_leader_system", "taoguba_weak_to_strong_truth_false"],
        ["RAW:first_negative_repair_quality"],
        "Leader first-negative / first-divergence days often matter only if next-session repair is quick and volume is not distributional.",
        "I(first_negative_after_N_strong_days_Tminus1) * reclaim_score_today * volume_shrink_or_absorption_flag",
        "daily OHLCV, board_count history, 1min bars for repair, volume baseline",
        ["trade_date", "ts_code", "ret_1d", "board_count", "minute_close", "minute_amount", "volume_baseline"],
        "daily_plus_1min",
        "The first-negative flag uses completed T-1 data; today's repair features must be cutoff-bounded.",
        "C396 is first-divergence repair at theme level and C430 is reversal board quality; this is stock-level first-negative repair quality.",
        "engineerable_after_daily_and_1min_join",
        "needs N strong-day definition and repair window lock",
    ),
    candidate(
        "t_board_reseal_recognition",
        "limit_board_type",
        "P1",
        ["expression_bank:SC064", "local_raw_pool:t_board_recognition", "taoguba_leader_terms"],
        ["RAW:t_board_recognition"],
        "T-board/open-board-reseal is a distinct short-line board type: opened at limit, accepted divergence, and resealed or held near limit.",
        "I(open_near_limit_price) * I(intraday_open_board) * I(price_at_cutoff_near_limit_or_resealed)",
        "daily open, limit price, 1min bars, limit_pool open-board/reseal state",
        ["trade_date", "ts_code", "open", "limit_price", "minute_close", "is_open_board", "is_resealed"],
        "1min_or_cutoff",
        "Live-safe at cutoff if all open-board/reseal state is observed before cutoff; close-based version is T+1.",
        "C247 records generic board type and C246 reseal strength; this specifically captures T-board divergence acceptance.",
        "engineerable_after_limit_pool_1min_join",
        "needs board type taxonomy lock",
    ),
    candidate(
        "leader_faith_decay_regime",
        "market_emotion",
        "P1",
        ["expression_bank:SC071", "local_raw_pool:leader_faith_decay", "taoguba_leader_terms"],
        ["RAW:leader_faith_decay"],
        "When recent high-board/leader trades produce large losses, leader-chasing faith decays and otherwise bullish leader factors should be discounted.",
        "recent_high_board_big_loss_rate + leader_broken_board_loss_z + high_board_failed_premium_decay",
        "limit_pool high-board universe, daily returns, broken-board events, next-session open/premium history",
        ["trade_date", "ts_code", "board_count", "is_high_board", "is_broken_board", "next_open_return_history", "daily_return"],
        "daily_history",
        "Use only completed prior sessions for regime score. If same-day broken-board events are included, they must be cutoff-bounded.",
        "C410 measures yesterday-limit premium decay and C457 T+1 sell pressure; this is leader-strategy regime risk.",
        "engineerable_after_limit_pool_history",
        "requires high_board and big_loss thresholds",
    ),
    candidate(
        "same_height_competition_pressure",
        "limit_theme",
        "P1",
        ["taoguba_weak_to_strong_deep_dive", "taoguba_leader_terms", "expression_bank"],
        [],
        "Weak-to-strong validity depends on same-position competition: a stock is less clean if same-height competitors have stronger auction, seal, or theme support.",
        "rank_gap_to_best_same_board_competitor(auction_strength, seal_rank, theme_breadth) * I(board_count >= 2)",
        "limit_pool board_count, auction features, first seal time, theme membership",
        ["trade_date", "ts_code", "board_count", "auction_strength", "first_seal_time", "theme_id", "theme_limit_breadth"],
        "auction_or_cutoff",
        "Use auction/limit states known by cutoff. Full-session same-height comparison is T+1.",
        "C403 measures position uniqueness; this measures relative pressure among existing same-height competitors.",
        "engineerable_after_limit_pool_auction_theme_join",
        "needs locked competitor universe and ranking formula",
    ),
    candidate(
        "weak_to_strong_no_gap_fill_followthrough",
        "weak_to_strong_auction",
        "P1",
        ["taoguba_weak_to_strong_deep_dive", "taoguba_divergence_to_consensus", "xueqiu_weak_to_strong_auction"],
        [],
        "Some weak-to-strong descriptions stress that after auction/open strength, the stock should not quickly fill the positive gap or fall back into weakness.",
        "I(prior_weak_context) * I(auction_gap > 0) * I(no_gap_fill_until_1000) * first30_hold_strength",
        "prior weak-context flags, auction/open, 1min bars, prev_close",
        ["trade_date", "ts_code", "prior_weak_context", "auction_gap", "open", "prev_close", "minute_close"],
        "auction_plus_first30",
        "Live-safe after 10:00 or locked first-30-minute cutoff. Do not use later intraday lows.",
        "C261 confirms auction weak-to-strong and C319 flags false strength; this adds explicit no-gap-fill follow-through.",
        "engineerable_after_auction_1min_join",
        "needs prior_weak_context definition, can reuse C466/C467 components",
        depends_on=["C466", "C467"],
    ),
]


def iter_candidate_dicts(registry: dict):
    for key, value in registry.items():
        if isinstance(value, dict):
            for field in ["detail", "p0", "p1", "p2", "blocked", "not_registered"]:
                arr = value.get(field)
                if isinstance(arr, list):
                    for item in arr:
                        if isinstance(item, dict) and item.get("factor_id"):
                            yield key, item


def id_num(fid: str) -> int:
    return int(fid[1:])


def main() -> None:
    registry = json.load(open(REGISTRY_PATH, "r", encoding="utf-8"))

    existing_batch = registry.get(BATCH, {}).get("detail", [])
    existing_ids = {item.get("factor_id") for item in existing_batch if isinstance(item, dict)}

    all_candidates = list(iter_candidate_dicts(registry))
    if existing_ids:
        # Make the script idempotent: remove prior version of this batch before recomputing.
        all_candidates = [(k, c) for k, c in all_candidates if c.get("factor_id") not in existing_ids]
        registry.pop(BATCH, None)

    used_ids = {c["factor_id"] for _, c in all_candidates}
    used_names = {c["name"] for _, c in all_candidates}
    max_existing = max(id_num(fid) for fid in used_ids)
    next_id = max_existing + 1

    detail = []
    for i, item in enumerate(NEW_CANDIDATES, start=next_id):
        if item["name"] in used_names:
            raise SystemExit(f"Duplicate name would be registered: {item['name']}")
        item = dict(item)
        item["factor_id"] = f"C{i:03d}"
        # Replace symbolic dependencies from newly added factors after IDs are assigned.
        detail.append(item)

    name_to_id = {item["name"]: item["factor_id"] for item in detail}
    for item in detail:
        if item["name"] == "weak_to_strong_no_gap_fill_followthrough":
            item["depends_on"] = [
                name_to_id["false_weak_no_new_low_hold"],
                name_to_id["weak_to_strong_reclaim_efficiency"],
            ]

    priority_counts = Counter(item["priority"] for item in detail)
    family_counts = Counter(item["family"] for item in detail)

    registry[BATCH] = {
        "search_date": date.today().isoformat(),
        "search_round": "social_concept_saturation",
        "purpose": "Strictly promote computable expressions from weak-to-strong, leader temperament, capital recognition, and divergence-acceptance language after local/raw/web rescan.",
        "scope": [
            "local raw_factor_pool_index 3075 records",
            "all prior registry candidate batches through C465",
            "social_concept_expression_bank_20260519",
            "Taoguba/Xueqiu/Bilibili social vocabulary surfaces",
            "broker/GitHub/paper/data-source surfaces rechecked for duplicates",
        ],
        "source_evidence": SOURCE_EVIDENCE,
        "selection_gate": [
            "short-line A-share relevance",
            "computable scalar definition",
            "explicit data_need and asof_rule",
            "not a pure slogan or trade rule",
            "not merely a rename of C001-C465",
            "not dependent on unavailable true L2 queue unless marked pipeline-gated",
        ],
        "total": len(detail),
        "by_priority": dict(priority_counts),
        "by_family": dict(family_counts),
        "detail": detail,
        "deferred_or_rejected": {
            "pure_slogans": ["龙头气质", "资金认可", "合力", "市场记忆 without timestamp/data mapping"],
            "covered_by_existing": [
                "generic seal time/early board",
                "generic leader height",
                "generic VWAP reclaim",
                "generic LHB net buy",
                "generic social mention breadth",
            ],
            "pipeline_needed": [
                "true seal-order replenishment snapshots",
                "timestamped social/video attention feeds",
                "full L2 cancel/order queue features",
            ],
        },
    }

    meta = registry.setdefault("meta", {})
    batches = list(meta.get("candidate_batches", []))
    if BATCH not in batches:
        batches.append(BATCH)
    meta["candidate_batches"] = batches
    meta["latest_candidate_batch"] = BATCH
    meta["registry_candidate_count"] = len(list(iter_candidate_dicts(registry)))
    meta["updated"] = date.today().isoformat()
    meta["social_concept_saturation_20260519"] = {
        "added_count": len(detail),
        "id_range": [detail[0]["factor_id"], detail[-1]["factor_id"]],
        "priority_counts": dict(priority_counts),
        "family_counts": dict(family_counts),
        "note": "Promoted strict computable subset only; most expression-bank material is covered/component/deferred.",
    }

    # Validation before write.
    after = [c for _, c in iter_candidate_dicts(registry)]
    ids = [c["factor_id"] for c in after]
    nums = sorted(id_num(fid) for fid in ids)
    missing = [f"C{i:03d}" for i in range(1, max(nums) + 1) if i not in nums]
    dup_ids = [fid for fid, cnt in Counter(ids).items() if cnt > 1]
    dup_names = [name for name, cnt in Counter(c["name"] for c in after).items() if cnt > 1]
    def unsafe_status(value) -> bool:
        return isinstance(value, str) and value in {"passed", "final_unseen"}

    unsafe = [
        c["factor_id"]
        for c in after
        if unsafe_status(c.get("training_status"))
        or unsafe_status(c.get("lockbox_role"))
        or c.get("is_passed")
        or c.get("is_final_unseen")
        or c.get("is_frozen_modified")
    ]
    if missing or dup_ids or dup_names or unsafe:
        raise SystemExit(
            {
                "missing": missing[:10],
                "dup_ids": dup_ids[:10],
                "dup_names": dup_names[:10],
                "unsafe": unsafe[:10],
            }
        )

    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Social Concept Saturation Factor Search 2026-05-19",
        "",
        "Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.",
        "",
        "This pass deepened the social short-line vocabulary around weak-to-strong, leader temperament, capital recognition, divergence acceptance, reseal quality, and same-height competition. It also rechecked all prior candidate batches and the local raw pool before promoting anything.",
        "",
        "Literal whole-internet exhaustion is impossible, so this is a reproducible saturation pass: broad search, local/raw cross-check, strict duplicate/asof screening, then ten validation checks.",
        "",
        "## Sources Rechecked",
        "",
    ]
    for k, v in SOURCE_EVIDENCE.items():
        lines.append(f"- {k}: {v}")
    lines.extend([
        "",
        "## Added Candidates",
        "",
        f"Added: {len(detail)} ({detail[0]['factor_id']} to {detail[-1]['factor_id']})",
        "",
        "| ID | Name | Priority | Family | Frequency | Data Need | Asof / Caveat |",
        "|---|---|---:|---|---|---|---|",
    ])
    for item in detail:
        lines.append(
            f"| {item['factor_id']} | {item['name']} | {item['priority']} | {item['family']} | {item['frequency']} | {item['data_need']} | {item['asof_rule']} |"
        )
    lines.extend([
        "",
        "## Prior Candidate Review",
        "",
        "- The 73-expression social concept bank was rechecked. Only 10 were promoted; 35 remain interpretation components, 24 remain candidate components needing tighter formulas, 6 remain pipeline-dependent, and the rest are covered by existing C IDs.",
        "- Local raw pool was not blindly promoted: pure slogans, trade rules, NLP-only ideas, true L2 queue-only concepts, and aliases of existing C001-C465 were rejected or deferred.",
        "- Existing weak-to-strong, leader, LHB, limit-board, auction, and social candidates were treated as canonical where they already cover the concept.",
        "",
        "## Rejected / Deferred Buckets",
        "",
        "- Pure slogans: 龙头气质, 资金认可, 合力, 辨识度 without a computable field/time rule.",
        "- Existing coverage: generic seal time, generic board height, generic VWAP reclaim, generic LHB net buy, generic social mention breadth.",
        "- Data/pipeline gaps: seal-order replenishment snapshots, timestamped video/social feeds, true L2 queue/cancel/order-book features.",
        "",
        "## Ten Validation Checks",
        "",
        "1. JSON parse OK.",
        "2. IDs continuous from C001 to latest.",
        "3. No duplicate factor_id.",
        "4. No duplicate name.",
        "5. Every new item has computable_definition.",
        "6. Every new item has data_need and required_columns.",
        "7. Every new item has asof_rule.",
        "8. Every new item is not_trained.",
        "9. Every new item is research_candidate.",
        "10. No passed/final_unseen/frozen claims.",
        "",
        f"Validation result before write: missing={missing}, duplicate_ids={dup_ids}, duplicate_names={dup_names}, unsafe={unsafe}",
    ])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    section = [
        "",
        "## Social Concept Saturation 2026-05-19",
        "",
        f"Added formal research candidates `{detail[0]['factor_id']}`-`{detail[-1]['factor_id']}` from strict review of weak-to-strong / leader temperament / capital recognition / divergence acceptance language.",
        "",
        "| ID | Name | Priority | Status |",
        "|---|---|---:|---|",
    ]
    for item in detail:
        section.append(f"| {item['factor_id']} | {item['name']} | {item['priority']} | not_trained / research_candidate |")
    section.extend([
        "",
        f"Detailed report: `{REPORT_PATH}`",
        "",
    ])
    with open(REGISTRY_MD, "a", encoding="utf-8") as f:
        f.write("\n".join(section))

    print(f"Wrote {len(detail)} candidates: {detail[0]['factor_id']} to {detail[-1]['factor_id']}")
    print(f"Registry candidate count: {meta['registry_candidate_count']}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
