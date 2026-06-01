"""Register final web-saturation short-line factor candidates.

Scope: factor-library metadata only.
No training, no gpu_probe, no model/frozen config changes.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
REPORT_PATH = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\web_saturation_factor_search_20260517.md")
HUMAN_REGISTRY_PATH = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\factor_registry.md")
BATCH_KEY = "candidates_20260517_web_saturation"
SEARCH_DATE = "2026-05-17"


SOURCE_EVIDENCE = {
    "gf_hf_factorization_46": "https://bigquant.com/square/paper/aaa3e0c6-4bc0-4ea3-9077-2a4976789c88",
    "cj_high_position_volume": "https://asset.quant-wiki.com/pdf/20200916-%E9%95%BF%E6%B1%9F%E8%AF%81%E5%88%B8-%E5%9F%BA%E7%A1%80%E5%9B%A0%E5%AD%90%E7%A0%94%E7%A9%B6%EF%BC%88%E5%8D%81%E4%B8%89%EF%BC%89%EF%BC%9A%E9%AB%98%E9%A2%91%E5%9B%A0%E5%AD%90%EF%BC%88%E5%85%AB%EF%BC%89%EF%BC%8C%E9%AB%98%E4%BD%8D%E6%88%90%E4%BA%A4%E5%9B%A0%E5%AD%90%EF%BC%8C%E4%BB%8E%E9%87%8F%E4%BB%B7%E5%8C%B9%E9%85%8D%E8%AF%B4%E8%B5%B7.pdf",
    "df_cpv_shift": "https://bigquant.com/square/paper/775b5485-2ec7-443f-a1d0-48aaceb94eb8",
    "kaiyuan_single_trade_amount": "https://bigquant.com/square/paper/74353d24-a9cf-4d17-a9fb-c431ece0a52e",
    "lhb_fund_structure": "https://bigquant.com/square/paper/07dff3c0-e071-4985-969d-2a7c263aefe3",
    "lhb_industry_rotation": "https://bigquant.com/square/paper/db9c2003-d043-4704-988e-fedf18b4e882",
    "taoguba_emotion_cycle": "https://www.tgb.cn/talk/talkSeq/179928",
    "internet_sentiment_overtrading": "https://arxiv.org/abs/2404.12001",
    "price_limit_prehit_dynamics": "https://arxiv.org/abs/1503.03548",
    "tushare_stk_factor": "https://www.tushare.pro/document/2?doc_id=296",
}

MINUTE_ASOF = (
    "For 14:57 live use only 1min bars with bar_time <= 14:57; "
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
        "name": "volume_lagged_return_corr_1457",
        "family": "minute_hf",
        "priority": "P0",
        "source_type": "web_saturation_20260517",
        "source_refs": ["df_cpv_shift", "gf_hf_factorization_46"],
        "data_need": "1min bars",
        "required_columns": ["close", "volume"],
        "frequency": "1min",
        "computable_definition": "corr(volume_t, return_{t+1}) for all t where t+1 <= 14:57, using 1min returns",
        "asof_rule": MINUTE_ASOF,
        "leakage_risk": "low if the shifted pair never crosses the live cutoff",
        "duplicate_check": "Distinct from C297/C298: focuses volume leading next-minute return, not same-time price-volume correlation or broad segment shift.",
        "engineering_status": "engineerable_after_1min_cache",
        "data_status": "stk_mins_1_available_needs_full_cache_gate",
    },
    {
        "name": "large_volume_lagged_return_corr",
        "family": "minute_hf",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["gf_hf_factorization_46", "df_cpv_shift"],
        "data_need": "1min bars",
        "required_columns": ["close", "volume", "amount"],
        "frequency": "1min",
        "computable_definition": "corr(volume_t, return_{t+1}) restricted to top-20pct amount minutes within the observed session",
        "asof_rule": MINUTE_ASOF,
        "leakage_risk": "low if top-amount minutes are selected only inside the observed cutoff window",
        "duplicate_check": "Large-volume subsample version; distinct from C300 large_amount_bar_push_return and C356 full-sample lagged correlation.",
        "engineering_status": "engineerable_after_1min_cache",
        "data_status": "stk_mins_1_available_needs_full_cache_gate",
    },
    {
        "name": "volume_weighted_price_skewness",
        "family": "minute_hf",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["cj_high_position_volume"],
        "data_need": "1min bars",
        "required_columns": ["close", "volume"],
        "frequency": "1min",
        "computable_definition": "sum((volume_t / sum(volume)) * ((close_t - mean(close)) / std(close))^3)",
        "asof_rule": MINUTE_ASOF,
        "leakage_risk": "low if computed only from observed bars",
        "duplicate_check": "Price-distribution skew weighted by volume; distinct from C294 return skew and C301 high-price volume share.",
        "engineering_status": "engineerable_after_1min_cache",
        "data_status": "stk_mins_1_available_needs_full_cache_gate",
    },
    {
        "name": "unit_amount_entropy",
        "family": "minute_hf",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["cj_high_position_volume"],
        "data_need": "1min bars",
        "required_columns": ["close", "volume", "amount"],
        "frequency": "1min",
        "computable_definition": "entropy(p_t), p_t = (volume_t / sum(volume)) * (close_t / mean(close)), normalized to sum(p)=1",
        "asof_rule": MINUTE_ASOF,
        "leakage_risk": "low if computed only from observed bars",
        "duplicate_check": "Joint price-volume entropy; distinct from C315 plain volume entropy and C353 spectral residual.",
        "engineering_status": "engineerable_after_1min_cache",
        "data_status": "stk_mins_1_available_needs_full_cache_gate",
    },
    {
        "name": "intraday_amihud_tail_ratio",
        "family": "minute_hf",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["gf_hf_factorization_46"],
        "data_need": "1min bars",
        "required_columns": ["close", "amount"],
        "frequency": "1min",
        "computable_definition": "mean(abs(1min_return)/(amount+eps) over last observed 30min) / mean(abs(1min_return)/(amount+eps) before that)",
        "asof_rule": MINUTE_ASOF,
        "leakage_risk": "low if last observed window ends at or before 14:57",
        "duplicate_check": "Tail-window Amihud ratio; distinct from C023 daily Amihud and C314 shortest-path illiquidity.",
        "engineering_status": "engineerable_after_1min_cache",
        "data_status": "stk_mins_1_available_needs_full_cache_gate",
    },
    {
        "name": "auction_turnover_jump_20d",
        "family": "auction_open",
        "priority": "P0",
        "source_type": "web_saturation_20260517",
        "source_refs": ["bigquant_auction_fields", "tushare_stk_factor"],
        "data_need": "opening auction turnover + trailing history",
        "required_columns": ["open_auction_turnover"],
        "frequency": "auction_daily",
        "computable_definition": "open_auction_turnover / (mean(open_auction_turnover, 20d) + eps)",
        "asof_rule": AUCTION_ASOF,
        "leakage_risk": "low if auction turnover is the 09:25 snapshot",
        "duplicate_check": "Turnover jump over history, not raw auction amount or VWAP ratio.",
        "engineering_status": "engineerable_after_auction_history_cache",
        "data_status": "needs_auction_turnover_field_mapping",
    },
    {
        "name": "auction_gap_positive_breadth",
        "family": "auction_market",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["bigquant_auction_fields", "taoguba_emotion_cycle"],
        "data_need": "opening auction price + prev_close for universe",
        "required_columns": ["auction_open_price", "prev_close"],
        "frequency": "auction_daily_market",
        "computable_definition": "count_stocks((auction_open_price - prev_close)/(prev_close+eps) > threshold) / universe_count",
        "asof_rule": AUCTION_ASOF,
        "leakage_risk": "low if computed only from 09:25 snapshot",
        "duplicate_check": "Positive auction breadth, distinct from C343 participation breadth and C344 gap dispersion.",
        "engineering_status": "engineerable_after_auction_universe_cache",
        "data_status": "needs_auction_universe_cache",
    },
    {
        "name": "lhb_seat_alpha_score_60d",
        "family": "lhb",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["lhb_fund_structure", "lhb_industry_rotation"],
        "data_need": "top_list/top_inst seat names + post-event return history",
        "required_columns": ["seat_name", "buy_amount", "sell_amount", "future_return_for_historical_scoring"],
        "frequency": "event_daily",
        "computable_definition": "amount_weighted average historical 1-5d excess win rate of today's net-buy seats over trailing 60 eligible LHB events",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium; historical seat scoring must use only events before current date",
        "duplicate_check": "Seat skill/history score, distinct from C345 institution net amount and C346 concentration.",
        "engineering_status": "engineerable_after_lhb_seat_history_cache",
        "data_status": "needs_lhb_seat_identity_history",
    },
    {
        "name": "lhb_theme_seat_crowding",
        "family": "lhb",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["lhb_industry_rotation", "taoguba_emotion_cycle"],
        "data_need": "top_list seat names + theme/industry mapping",
        "required_columns": ["seat_name", "buy_amount", "industry_or_theme"],
        "frequency": "event_daily",
        "computable_definition": "HHI of net-buy LHB seat exposure within the stock's active theme or industry on the latest available day",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium; use T-1 or publication timestamp",
        "duplicate_check": "Theme-level seat crowding, not single-stock buy-seat concentration.",
        "engineering_status": "engineerable_after_lhb_theme_join",
        "data_status": "needs_lhb_and_theme_join",
    },
    {
        "name": "guba_sentiment_overtrading_gap",
        "family": "social_attention",
        "priority": "P2",
        "source_type": "web_saturation_20260517",
        "source_refs": ["internet_sentiment_overtrading"],
        "data_need": "timestamped guba/taoguba sentiment + intraday turnover",
        "required_columns": ["sentiment_score_asof", "turnover_intraday"],
        "frequency": "intraday_social",
        "computable_definition": "zscore(sentiment_score_asof) * zscore(intraday_turnover_until_1457 - expected_turnover_until_1457)",
        "asof_rule": "Use only posts/comments timestamped <= 14:57 and minute turnover <= 14:57; otherwise shift to T-1.",
        "leakage_risk": "high unless timestamped social scrape and entity mapping are locked",
        "duplicate_check": "Formulaic sentiment-overtrading interaction; distinct from C286-C289 broad social attention families.",
        "engineering_status": "needs_timestamped_social_pipeline",
        "data_status": "needs_guba_taoguba_timestamped_sentiment",
    },
    {
        "name": "limit_pre_hit_volume_acceleration",
        "family": "limit_board",
        "priority": "P0",
        "source_type": "web_saturation_20260517",
        "source_refs": ["price_limit_prehit_dynamics"],
        "data_need": "1min bars + first limit-hit timestamp",
        "required_columns": ["bar_time", "close", "volume", "up_limit"],
        "frequency": "1min_limit_event",
        "computable_definition": "slope of log(volume+1) over the N minutes before the first observed limit-up touch",
        "asof_rule": "Use only limit touches and bars timestamped <= 14:57; if first-hit timestamp is unavailable, do not use for live.",
        "leakage_risk": "low if first-hit timestamp is locked before cutoff",
        "duplicate_check": "Pre-hit dynamic slope, distinct from C321 limit attempt count and C327 seal money scale.",
        "engineering_status": "engineerable_if_limit_hit_timestamp_available",
        "data_status": "needs_limit_pool_event_time_join",
    },
    {
        "name": "limit_pre_hit_return_curvature",
        "family": "limit_board",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["price_limit_prehit_dynamics"],
        "data_need": "1min bars + first limit-hit timestamp",
        "required_columns": ["bar_time", "close", "up_limit"],
        "frequency": "1min_limit_event",
        "computable_definition": "second-difference curvature of cumulative 1min returns over the N minutes before first limit-up touch",
        "asof_rule": "Use only limit touches and bars timestamped <= 14:57; if first-hit timestamp is unavailable, do not use for live.",
        "leakage_risk": "low if first-hit timestamp is locked before cutoff",
        "duplicate_check": "Acceleration/curvature into limit touch, not generic approach velocity C006 or board count features.",
        "engineering_status": "engineerable_if_limit_hit_timestamp_available",
        "data_status": "needs_limit_pool_event_time_join",
    },
    {
        "name": "northbound_top10_turnover_crowding",
        "family": "northbound_flow",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["data_unlocked:hsgt_top10", "lhb_fund_structure"],
        "data_need": "hsgt_top10 turnover/buy/sell + stock float or amount",
        "required_columns": ["hsgt_top10_amount", "hsgt_top10_net_buy", "free_share", "close"],
        "frequency": "event_daily",
        "computable_definition": "abs(hsgt_top10_net_buy) / (free_share * close + eps), winsorized and ranked cross-sectionally",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium; hsgt_top10 publication time must be T-1 or timestamp-locked",
        "duplicate_check": "Crowding magnitude of top10 northbound trades, distinct from C335 entry streak and C336 CCASS holding acceleration.",
        "engineering_status": "engineerable_after_hsgt_top10_backfill",
        "data_status": "needs_hsgt_top10_cache",
    },
    {
        "name": "industry_lhb_flow_rotation_strength",
        "family": "industry_flow",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["lhb_industry_rotation", "lhb_fund_structure"],
        "data_need": "LHB net buy by industry/theme + industry member map",
        "required_columns": ["industry_or_theme", "lhb_net_buy_amount", "industry_float_mv"],
        "frequency": "event_daily_industry",
        "computable_definition": "rank(industry_lhb_net_buy_to_float) - rank(mean(industry_lhb_net_buy_to_float, 5d))",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium; use only latest published LHB records",
        "duplicate_check": "Industry-level LHB rotation, distinct from C337 general industry moneyflow and C369 single-stock theme seat crowding.",
        "engineering_status": "engineerable_after_lhb_industry_aggregation",
        "data_status": "needs_lhb_industry_cache",
    },
    {
        "name": "block_trade_discount_volume_pressure",
        "family": "block_trade",
        "priority": "P1",
        "source_type": "web_saturation_20260517",
        "source_refs": ["data_unlocked:block_trade", "kaiyuan_single_trade_amount"],
        "data_need": "block_trade price/amount + daily close/ADV",
        "required_columns": ["block_price", "close", "block_amount", "adv_20d"],
        "frequency": "event_daily",
        "computable_definition": "amount_weighted((block_price / close) - 1) * log1p(block_amount / (adv_20d + eps))",
        "asof_rule": EVENT_ASOF,
        "leakage_risk": "medium; use T-1 block trades unless same-day publication timestamp is locked",
        "duplicate_check": "Discount depth scaled by trade size, distinct from C329 discount persistence and C330 seller concentration.",
        "engineering_status": "engineerable_after_block_trade_backfill",
        "data_status": "needs_block_trade_cache",
    },
]


def walk_factors(obj):
    if isinstance(obj, dict):
        if str(obj.get("factor_id", "")).startswith("C"):
            yield obj
        for value in obj.values():
            yield from walk_factors(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_factors(value)


def remove_existing_batch(registry):
    registry.pop(BATCH_KEY, None)
    batches = registry.get("meta", {}).get("candidate_batches", [])
    registry.setdefault("meta", {})["candidate_batches"] = [b for b in batches if b != BATCH_KEY]


def next_id(registry):
    nums = []
    for item in walk_factors(registry):
        fid = item.get("factor_id", "")
        if fid.startswith("C") and fid[1:].isdigit():
            nums.append(int(fid[1:]))
    return max(nums, default=0) + 1


def prepare_details(start):
    names = set()
    prepared = []
    for idx, item in enumerate(DETAILS):
        d = dict(item)
        if d["name"] in names:
            raise ValueError(f"duplicate new name {d['name']}")
        names.add(d["name"])
        d["factor_id"] = f"C{start + idx:03d}"
        d["batch"] = BATCH_KEY
        d["training_status"] = "not_trained"
        d["lockbox_role"] = "research_candidate"
        d["depends_on"] = d.get("depends_on", [])
        d["notes"] = d.get("notes", "")
        d["audit_20260517"] = {
            "status": "audited",
            "checks": [
                "explicit_formula",
                "data_need_named",
                "asof_rule_named",
                "not_exact_duplicate",
                "not_training_result_claim",
            ],
        }
        prepared.append(d)
    return prepared


def make_batch(details):
    return {
        "search_date": SEARCH_DATE,
        "search_round": "web_saturation_after_expanded_surface",
        "purpose": "Final widened web search pass after four-source and expanded-surface scans; register only non-duplicate computable short-line candidates.",
        "scope": "factor-library only; no training, no gpu_probe, no model or frozen config edits",
        "source_evidence": SOURCE_EVIDENCE,
        "selection_criteria": [
            "must be a single computable feature or clearly broadcast market/industry feature",
            "must have explicit data_need and required_columns",
            "must have explicit 14:57/asof rule",
            "must not duplicate C001-C355 by name or formula intent",
            "must not claim training pass, final_unseen, or frozen status",
        ],
        "saturation_checks": [
            "Chinese high-frequency price-volume reports",
            "high-position volume and entropy factor reports",
            "CPV/lagged price-volume correlation family",
            "single-trade amount / L2 behavior reports",
            "auction factor data and reports",
            "LHB fund structure and industry rotation reports",
            "Taoguba emotion-cycle rules",
            "social sentiment / intraday overtrading papers",
            "price-limit pre-hit dynamics papers",
            "Tushare/API data-field feasibility pass",
        ],
        "total": len(details),
        "by_priority": dict(Counter(d["priority"] for d in details)),
        "by_family": dict(Counter(d["family"] for d in details)),
        "detail": details,
        "deferred_or_rejected_summary": {
            "full_alpha191_alpha101_formula_libraries": "Not bulk-registered. They need per-formula translation, C-ID dedup, and asof review.",
            "true_l2_orderbook_cancel_depth_ofi": "Still blocked until stable L2/tick/orderbook pipeline exists.",
            "pure_text_social_rules": "Rejected unless converted into timestamped entity-level numeric series.",
            "generic_technical_indicators": "Rejected when already present in baseline/research features or too broad without short-line novelty.",
            "duplicate_limit_emotion_metrics": "Rejected if already represented by board height, open-board, break-board, seal, or emotion-score families.",
        },
    }


def render_report(batch):
    details = batch["detail"]
    lines = [
        "# Web Saturation Short-Line Factor Search 2026-05-17",
        "",
        "Scope: factor-library only. No training, no gpu_probe, no model or frozen config changes.",
        "",
        "## Saturation Surface",
        "",
    ]
    for item in batch["saturation_checks"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Source Evidence", ""])
    for k, v in SOURCE_EVIDENCE.items():
        lines.append(f"- `{k}`: {v}")
    lines.extend([
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
    ])
    for d in details:
        lines.append(
            f"| {d['factor_id']} | {d['name']} | {d['priority']} | {d['family']} | "
            f"{d['data_need']} | {d['engineering_status']} | {d['asof_rule']} |"
        )
    lines.extend(["", "## Deferred / Not Registered", ""])
    for k, v in batch["deferred_or_rejected_summary"].items():
        lines.append(f"- `{k}`: {v}")
    lines.extend([
        "",
        "## Ten Validation Checks",
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
    ])
    return "\n".join(lines)


def validate(registry, batch):
    factors = list(walk_factors(registry))
    ids = [f["factor_id"] for f in factors]
    nums = sorted(int(fid[1:]) for fid in ids)
    names = [f.get("name") or f.get("column") for f in factors if f.get("name") or f.get("column")]
    assert len(ids) == len(set(ids)), "duplicate factor_id"
    assert len(names) == len(set(names)), "duplicate factor name"
    assert nums == list(range(1, max(nums) + 1)), "non-continuous ids"
    assert registry["meta"]["registry_candidate_count"] == len(factors), "meta count mismatch"
    assert BATCH_KEY in registry, "missing batch"
    assert len(registry[BATCH_KEY]["detail"]) == batch["total"], "batch size mismatch"
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
            assert d.get(field), f"missing {field} in {d.get('factor_id')}"
        assert d["training_status"] == "not_trained"
        assert d["lockbox_role"] == "research_candidate"
        assert not d.get("is_passed")
        assert not d.get("is_final_unseen")
        assert not d.get("is_frozen_modified")


def main():
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    remove_existing_batch(registry)
    start = next_id(registry)
    details = prepare_details(start)
    batch = make_batch(details)
    registry[BATCH_KEY] = batch
    meta = registry.setdefault("meta", {})
    meta["updated"] = SEARCH_DATE
    meta["latest_candidate_batch"] = BATCH_KEY
    batches = list(meta.get("candidate_batches", []))
    if BATCH_KEY not in batches:
        batches.append(BATCH_KEY)
    meta["candidate_batches"] = batches
    meta["web_saturation_20260517"] = {
        "new_candidates": len(details),
        "id_range": f"{details[0]['factor_id']}-{details[-1]['factor_id']}",
        "search_sources": list(SOURCE_EVIDENCE.keys()),
        "saturation_checks": batch["saturation_checks"],
        "deferred": list(batch["deferred_or_rejected_summary"].keys()),
        "training_boundary": "not_trained; research_candidate only",
    }
    meta["registry_candidate_count"] = len(list(walk_factors(registry)))
    validate(registry, batch)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(render_report(batch), encoding="utf-8")

    section = [
        "",
        "---",
        "",
        f"## Web Saturation Search {SEARCH_DATE}",
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
    section.extend([
        "",
        f"Full detail: [web_saturation_factor_search_20260517.md](web_saturation_factor_search_20260517.md)",
        "",
    ])
    text = HUMAN_REGISTRY_PATH.read_text(encoding="utf-8").rstrip()
    marker = f"## Web Saturation Search {SEARCH_DATE}"
    if marker not in text:
        HUMAN_REGISTRY_PATH.write_text(text + "\n" + "\n".join(section), encoding="utf-8")

    print(f"Registered {len(details)} candidates {details[0]['factor_id']}-{details[-1]['factor_id']}")
    print(f"Report {REPORT_PATH}")
    print("Validation PASS")


if __name__ == "__main__":
    main()
