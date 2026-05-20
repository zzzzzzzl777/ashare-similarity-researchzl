"""Register all-channel short-line factor expansion candidates.

Registry-only update. This script does not train, run gpu_probe, or change
model/frozen configs.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
HUMAN_REGISTRY_PATH = ROOT / "docs" / "factor_registry.md"
REPORT_PATH = ROOT / "docs" / "all_channel_factor_expansion_20260518.md"
BATCH = "candidates_20260518_all_channel_expansion"
TODAY = "2026-05-18"


SOURCES = {
    "raw_pool_index": r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json",
    "raw_queue_500": str(ROOT / "docs" / "raw_to_registry_review_queue_500_20260506.md"),
    "factor_data_availability_audit": str(ROOT / "docs" / "factor_data_availability_audit.md"),
    "short_term_factors_research": str(ROOT / "docs" / "short_term_factors_research.md"),
    "limit_industry_effect_bigquant": "https://mf.bigquant.com/square/paper/a6dded73-c8d3-4111-9110-632e73a911a1",
    "limit_industry_effect_pdf": "https://bigdata-s3.wmcloud.com/researchreport/2023-12/507a2d79c1b778addb41193fd781efde.pdf",
    "guba_sentiment_paper": "https://arxiv.org/abs/2404.12001",
    "qlib_github": "https://github.com/microsoft/qlib",
    "alpha101_github": "https://github.com/ChadThackray/Alpha101",
    "etf_factor_report": "https://bigquant.com/square/paper/2e0f3709-241e-41b9-a3ea-c79c1e088c66",
    "option_factor_report": "https://bigquant.com/square/paper/14d6d637-8496-44a1-b17b-3b6ba54985a4",
    "convertible_bond_report": "https://pdf.dfcfw.com/pdf/H3_AP202403251628072093_1.pdf?1711384657000.pdf",
    "margin_factor_report": "https://bigquant.com/square/paper/dca4d47c-61d8-477c-b351-751bcaef5217",
}


def factor(
    fid: int,
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
) -> dict:
    return {
        "factor_id": f"C{fid:03d}",
        "name": name,
        "family": family,
        "priority": priority,
        "source_type": "all_channel_expansion_20260518",
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
        "depends_on": [],
        "notes": notes,
        "audit_20260518": {
            "status": "audited",
            "checks": [
                "all_channel_web_search",
                "local_raw_pool_cross_check",
                "duplicate_screened_against_C001_C416",
                "computable_definition_present",
                "data_need_present",
                "asof_rule_present",
                "not_training_result_claim",
            ],
        },
    }


DETAIL = [
    factor(
        417,
        "etf_constituent_flow_pressure",
        "etf_flow",
        "P1",
        ["raw_pool_index", "etf_factor_report"],
        ["RAW001971", "RAW001972"],
        "ETF creations/redemptions and ETF share changes can transmit flow pressure to constituent stocks.",
        "sum(etf_net_flow_j * constituent_weight_ij for ETF j holding stock i) / (float_mv_i + eps)",
        "ETF constituent weights, ETF net flow or share change, ETF NAV/close, stock float market value",
        ["trade_date", "ts_code", "fund_code", "weight", "etf_net_flow", "nav", "float_mv"],
        "daily",
        "Use after-close ETF/fund data for T+1 unless constituent flow timestamps prove same-day availability.",
        "C243 is ETF creation/redemption pressure at ETF level; this maps ETF flow pressure to each stock constituent.",
        "needs_etf_holding_flow_join",
        "requires ETF holdings/fund-flow cache; no same-day use without timestamps",
    ),
    factor(
        418,
        "option_pcr_market_sentiment",
        "option_market",
        "P2",
        ["raw_pool_index", "option_factor_report"],
        ["RAW001990", "RAW001991", "RAW002207", "RAW002208", "RAW002406", "RAW002407"],
        "Put-call volume and open-interest ratios proxy option-market risk appetite.",
        "zscore(put_volume / (call_volume + eps)) + zscore(put_oi / (call_oi + eps))",
        "option daily volume/open-interest by underlying, option basic mapping, market or ETF underlying mapping",
        ["trade_date", "underlying_code", "put_volume", "call_volume", "put_oi", "call_oi"],
        "daily",
        "Use opt_daily after close for next-day prediction; intraday option data must be separately timestamped before same-day use.",
        "No existing registry candidate captures PCR volume/OI option sentiment.",
        "needs_option_daily_pipeline",
        "market-level or underlying-ETF-level feature broadcast/mapped to stocks; P2 until mapping is fixed",
    ),
    factor(
        419,
        "option_iv_skew_risk",
        "option_market",
        "P2",
        ["raw_pool_index", "option_factor_report"],
        ["RAW002204", "RAW002205", "RAW002206"],
        "Option implied-volatility skew can proxy tail-risk demand and short-term sentiment.",
        "(put_iv_25delta - call_iv_25delta) / (atm_iv + eps)",
        "option implied volatility or fields sufficient to compute IV, option delta/moneyness, underlying mapping",
        ["trade_date", "underlying_code", "put_iv_25delta", "call_iv_25delta", "atm_iv"],
        "daily",
        "Use only option fields published by cutoff; if IV is computed after close, this is T+1 only.",
        "C409 uses realized lottery skew from stock returns; this uses option-implied skew.",
        "needs_option_iv_fields",
        "data-gated until reliable IV/delta fields are confirmed",
    ),
    factor(
        420,
        "convertible_forced_redemption_pressure",
        "convertible_bond",
        "P1",
        ["raw_pool_index", "short_term_factors_research", "convertible_bond_report"],
        ["RAW002696", "RAW002697"],
        "Stocks with linked convertibles near forced-redemption triggers may face special short-line pressure.",
        "count(close_last_30d > 1.3 * conversion_price) / 15",
        "convertible-stock mapping, conversion price, stock daily close, convertible status",
        ["trade_date", "ts_code", "cb_code", "conversion_price", "close"],
        "daily",
        "Use stock close and conversion-price information known by T close; for intraday use, replace close with cutoff price and mark proxy.",
        "C219 is broad convertible risk appetite; this is stock-level forced-redemption trigger pressure.",
        "needs_cb_basic_and_stock_join",
        "engineerable if cb_basic/conversion terms are cached",
    ),
    factor(
        421,
        "convertible_equity_linkage_premium_gap",
        "convertible_bond",
        "P2",
        ["short_term_factors_research", "convertible_bond_report"],
        [],
        "Low conversion premium can make convertible price action more tightly linked to the underlying stock.",
        "underlying_ret_1d * max(0, premium_threshold - conversion_premium_rate)",
        "convertible daily price, conversion value/premium, underlying stock return",
        ["trade_date", "ts_code", "cb_code", "cb_close", "conversion_value", "conversion_premium_rate", "ret_1d"],
        "daily",
        "Use after-close convertible daily data for next-day prediction unless intraday convertible quotes are timestamped.",
        "Distinct from C420 trigger pressure and C219 market appetite; this is linked-stock sensitivity conditioned on premium gap.",
        "needs_cb_daily_join",
        "P2 until convertible premium fields and stock mapping coverage are confirmed",
    ),
    factor(
        422,
        "limit_spillover_network_traction",
        "limit_network",
        "P1",
        ["limit_industry_effect_bigquant", "limit_industry_effect_pdf"],
        [],
        "Price-limit events can spill over through industry, theme, and co-limit networks.",
        "sum(network_weight_ij * signed_limit_event_j for peer j over recent K days)",
        "limit_pool, industry/theme membership, co-limit/correlation network, daily returns",
        ["trade_date", "ts_code", "peer_code", "network_weight", "is_limit_up", "is_limit_down"],
        "daily_or_1457_proxy",
        "Use only peer limit events known by cutoff; for full T close signals use next-day prediction.",
        "C411 is industry aggregate reversal; this is stock-level peer-network traction.",
        "needs_peer_network_cache",
        "engineerable from limit_pool plus industry/theme/correlation network",
    ),
    factor(
        423,
        "news_surge_sentiment_event_factor",
        "news_attention",
        "P2",
        ["raw_pool_index", "guba_sentiment_paper"],
        ["RAW001948", "RAW001950", "RAW002015"],
        "Abnormal news volume combined with sentiment can identify short-line event attention.",
        "((news_count_t - rolling_mean(news_count,20)) / (rolling_std(news_count,20) + eps)) * avg_sentiment_asof",
        "timestamped stock news count, NLP sentiment, stock-symbol mapping",
        ["event_time", "trade_date", "ts_code", "news_count", "avg_sentiment"],
        "event_or_daily",
        "For same-day use, include only news items whose event_time is <= cutoff; otherwise shift to T+1.",
        "C240 is announcement sentiment; this captures broader timestamped news surge plus sentiment.",
        "needs_timestamped_news_pipeline",
        "P2 because text pipeline quality and symbol mapping must be audited",
    ),
    factor(
        424,
        "margin_buy_intensity_relative",
        "margin_derivative",
        "P1",
        ["raw_pool_index", "margin_factor_report"],
        ["RAW001351", "RAW002767", "RAW002768", "RAW002769"],
        "Margin-buy amount relative to turnover can signal leveraged demand intensity.",
        "(margin_buy_amount / (daily_amount + eps)) / (rolling_mean(margin_buy_amount / daily_amount, 20) + eps)",
        "margin_detail financing buy amount, daily amount, stock identifier mapping",
        ["trade_date", "ts_code", "rzmre", "amount"],
        "daily",
        "Margin data is normally after-close; use for next-day prediction unless same-day timestamp is proven.",
        "C055/C069 emphasize balance or chase behavior; C424 uses buy-amount intensity relative to turnover and its own history.",
        "needs_margin_detail_join",
        "engineerable after margin_detail coverage audit",
    ),
    factor(
        425,
        "short_selling_pressure_ratio",
        "margin_derivative",
        "P2",
        ["factor_data_availability_audit", "margin_factor_report"],
        [],
        "Short-selling activity can proxy local bearish pressure or hedging demand.",
        "short_sell_volume_or_amount / (daily_volume_or_amount + eps)",
        "margin short-selling volume/amount fields and daily volume/amount",
        ["trade_date", "ts_code", "rqmcl", "rqye", "volume", "amount"],
        "daily",
        "Use after-close margin data for next-day prediction; same-day use requires timestamped margin updates.",
        "No existing registry candidate directly measures short-selling pressure ratio; related margin factors focus on financing side.",
        "needs_margin_short_fields",
        "P2 because A-share short-selling coverage may be sparse",
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
        "## All-Channel Factor Expansion 2026-05-18",
        "",
        "Purpose: expanded search across local raw pool, broker reports, papers, GitHub/open-source, social/TGB ideas, and data-availability notes. Registry only: no training, no gpu_probe, no model/frozen config changes.",
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
            "- C417 ETF constituent flow is T+1 unless ETF flow/holding timestamps prove same-day availability.",
            "- C418-C419 option features are T+1 unless intraday option data is available and timestamped.",
            "- C420-C421 convertible features are daily/T+1 unless intraday convertible quotes and conversion terms are timestamped.",
            "- C422 can be 14:57-capable if peer limit events are cutoff-bounded.",
            "- C423 requires timestamped news and symbol mapping before same-day use.",
            "- C424-C425 margin features are normally after-close/T+1.",
        ]
    )
    with HUMAN_REGISTRY_PATH.open("a", encoding="utf-8") as f:
        f.write("\n".join(section) + "\n")


def write_report(validation: dict) -> None:
    priority_counts = Counter(row["priority"] for row in DETAIL)
    family_counts = Counter(row["family"] for row in DETAIL)
    lines = [
        "# All-Channel Factor Expansion 2026-05-18",
        "",
        "Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.",
        "",
        "## Search Surface",
        "",
        "- Local raw pool and raw-to-registry queues: ETF flow, PCR/OI, IV skew, convertible forced redemption, margin intensity, news surge.",
        "- Broker/report direction: price-limit industry/network spillover, ETF flow, option sentiment, convertible-bond short-line pressure, margin/short-selling behavior.",
        "- Academic/open-source direction: social/news sentiment, qlib/alpha technical libraries, price-limit network ideas.",
        "- Social/TGB direction: no extra pure-text idea was registered unless it could be reduced to a stock-date scalar with data and asof fields.",
        "",
        "## Result",
        "",
        f"- Added candidates: {len(DETAIL)} ({DETAIL[0]['factor_id']} to {DETAIL[-1]['factor_id']})",
        f"- Priority counts: {dict(priority_counts)}",
        f"- Family counts: {dict(family_counts)}",
        "- All additions remain `training_status=not_trained` and `lockbox_role=research_candidate`.",
        "",
        "## Added Candidates",
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
            "## Explicit Non-Adds",
            "",
            "- Pure generic Alpha101/Alpha191 formulas were not re-added because the registry already has technical-indicator bank coverage unless a formula has distinct short-line context.",
            "- Untimestamped social/video slogans were not registered as same-day factors.",
            "- True L2/tick order-book queue and cancellation factors remain outside the registry until stable data fields exist.",
            "- Any factor whose only definition was `current_price = close` or a direct alias of an existing feature was rejected as duplicate/non-factor.",
            "",
            "## Ten Checks",
            "",
        ]
    )
    for idx, check in enumerate(
        [
            "existing C001-C416 duplicate-name screen",
            "existing C001-C416 duplicate-formula screen",
            "raw pool no-match review",
            "ETF source and data-field feasibility check",
            "option PCR/OI/IV data-field feasibility check",
            "convertible-bond source and stock mapping check",
            "margin/short-selling field feasibility check",
            "news/social timestamp and asof check",
            "14:57 vs T close vs T+1 leakage classification",
            "registry integrity check after write",
        ],
        1,
    ):
        lines.append(f"{idx}. {check}")
    lines.extend(
        [
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
    new_ids = [row["factor_id"] for row in DETAIL]
    overlap = sorted(existing_ids & set(new_ids))
    if overlap:
        raise SystemExit(f"ID overlap: {overlap}")

    data[BATCH] = {
        "search_date": TODAY,
        "search_round": "all_channel_expansion",
        "purpose": "expand short-line factor library from all available web/local source surfaces",
        "scope": "factor-library only; no training; no gpu_probe; no model/frozen config changes",
        "source_evidence": SOURCES,
        "selection_gate": [
            "explicit computable scalar definition",
            "named data need and required columns",
            "asof rule and leakage boundary",
            "non-duplicate against C001-C416",
            "training_status remains not_trained",
            "lockbox_role remains research_candidate",
        ],
        "total": len(DETAIL),
        "by_priority": dict(Counter(row["priority"] for row in DETAIL)),
        "by_family": dict(Counter(row["family"] for row in DETAIL)),
        "detail": DETAIL,
        "deferred_or_rejected": [
            {
                "bucket": "pure_text_social_rules",
                "reason": "No timestamped stock-date scalar yet; keep in raw pool until symbol/time extraction is reliable.",
            },
            {
                "bucket": "true_l2_orderbook",
                "reason": "Requires stable L2/tick queue/cancel fields, not currently in confirmed data interface.",
            },
            {
                "bucket": "generic_technical_formulas",
                "reason": "Already covered by technical-bank candidates unless a short-line source/context makes them distinct.",
            },
        ],
    }

    meta = data.setdefault("meta", {})
    batches = meta.setdefault("candidate_batches", [])
    if BATCH not in batches:
        batches.append(BATCH)
    meta["updated"] = TODAY
    meta["latest_candidate_batch"] = BATCH
    meta["all_channel_expansion_20260518"] = {
        "added_count": len(DETAIL),
        "id_range": [DETAIL[0]["factor_id"], DETAIL[-1]["factor_id"]],
        "priority_counts": dict(Counter(row["priority"] for row in DETAIL)),
        "family_counts": dict(Counter(row["family"] for row in DETAIL)),
        "t_plus_1_only_or_unless_timestamped": ["C417", "C418", "C419", "C420", "C421", "C423", "C424", "C425"],
        "cutoff_capable_after_pipeline": ["C422"],
    }

    all_rows = iter_candidate_rows(data)
    all_ids = [row["factor_id"] for row in all_rows]
    numeric_ids = sorted(int(fid[1:]) for fid in all_ids if fid.startswith("C") and fid[1:].isdigit())
    missing = [f"C{i:03d}" for i in range(1, max(numeric_ids) + 1) if i not in numeric_ids]
    duplicates = sorted(fid for fid, count in Counter(all_ids).items() if count > 1)
    unsafe_status_count = 0
    for row in all_rows:
        unsafe_status_count += int(bool(row.get("is_passed")))
        unsafe_status_count += int(bool(row.get("is_final_unseen")))
        unsafe_status_count += int(bool(row.get("is_frozen_modified")))

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
