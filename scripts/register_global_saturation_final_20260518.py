"""Register final global saturation short-line factor batch.

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
REPORT_PATH = ROOT / "docs" / "global_saturation_final_search_20260518.md"
BATCH = "candidates_20260518_global_saturation_final"
TODAY = "2026-05-18"


SOURCES = {
    "local_raw_pool": r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json",
    "raw_queue_500": str(ROOT / "docs" / "raw_to_registry_review_queue_500_20260506.md"),
    "lottery_china_sciencedirect": "https://www.sciencedirect.com/science/article/abs/pii/S1062940820301637",
    "kysec_limit_industry_reversal_bigquant": "https://mf.bigquant.com/square/paper/a6dded73-c8d3-4111-9110-632e73a911a1",
    "kysec_limit_industry_reversal_pdf": "https://bigdata-s3.wmcloud.com/researchreport/2023-12/507a2d79c1b778addb41193fd781efde.pdf",
    "lhb_seat_winrate_cs": "https://www.cs.com.cn/gppd/gsyj/202601/t20260106_6531791.html",
    "lhb_seat_style_sina": "https://k.sina.cn/article_7879922977_1d5ae152101901c1v6.html",
    "stockformer_arxiv": "https://arxiv.org/abs/2401.06139",
    "trading_volume_memory_arxiv": "https://arxiv.org/abs/1106.1415",
}


def item(
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
        "source_type": "global_saturation_final_20260518",
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
                "four_source_saturation_search",
                "local_raw_pool_cross_check",
                "duplicate_screened_against_C001_C406",
                "computable_definition_present",
                "data_need_present",
                "asof_rule_present",
                "not_training_result_claim",
            ],
        },
    }


DETAIL = [
    item(
        407,
        "capital_memory_reactivation_score",
        "capital_memory",
        "P1",
        ["local_raw_pool", "raw_queue_500"],
        ["RAW000128"],
        "A stock that led a previous similar event/theme can reactivate when a comparable event appears again.",
        (
            "prior_leader_strength_same_event_or_theme * current_event_similarity_score "
            "* exp(-days_since_prior_lead / tau) * current_liquidity_confirmation"
        ),
        "event/theme labels, historical event leaders, daily OHLCV, limit_pool; optional social/LHB confirmation",
        ["trade_date", "ts_code", "theme_id", "event_id", "leader_score", "close", "amount"],
        "daily_or_event",
        "Use only event/theme labels and leader history published or known by cutoff; if event timestamp is unknown, shift to T+1.",
        "Not covered by C399 ex-leader independence: this is cross-event historical reactivation, not same-day theme breadth.",
        "needs_event_theme_leader_history",
        "requires canonical event/theme mapping; can run as P1 once labels are timestamped",
    ),
    item(
        408,
        "consensus_hot_stock_memory_score",
        "capital_memory",
        "P2",
        ["local_raw_pool", "raw_queue_500"],
        ["RAW000164"],
        "Widely recognized hot stocks have residual holder/attention memory that can amplify later relay demand.",
        (
            "zscore(prior_120d_social_or_lhb_attention_percentile) "
            "+ zscore(max_prior_board_height_120d) "
            "+ zscore(prior_lhb_appearance_count_120d)"
        ),
        "timestamped social/stock-bar mentions, LHB appearances, limit_pool board height history",
        ["trade_date", "ts_code", "mention_count", "lhb_appearance", "board_height"],
        "daily",
        "For same-day use, only include social posts before cutoff; if social timestamps are missing, shift to T+1.",
        "Distinct from C405 cross-platform consensus: this measures historical memory stock-level familiarity, not current-platform agreement.",
        "needs_timestamped_social_or_lhb_history",
        "P2 until social timestamp pipeline is stable; LHB-only fallback is after-close T+1",
    ),
    item(
        409,
        "lottery_max_ivol_skew_pressure",
        "behavioral_lottery",
        "P1",
        ["local_raw_pool", "lottery_china_sciencedirect"],
        ["RAW002017"],
        "Lottery preference proxies combine extreme maximum return, idiosyncratic volatility, and skewness.",
        "rank(MAX_return_Nd) + rank(idiosyncratic_volatility_Nd) + rank(idiosyncratic_skewness_Nd)",
        "daily returns; market/industry benchmark return for idiosyncratic residuals; optional 1min realized variant",
        ["trade_date", "ts_code", "close", "market_return", "industry_return"],
        "daily",
        "At T close use returns through T; for 14:57 replay use price_1457 proxy and mark proxy version separately.",
        "No C001-C406 candidate captures MAX+IVOL+skew lottery preference as a combined behavioral risk/attention proxy.",
        "engineerable_now_with_daily_history",
        "direction should be learned by training; registry only states the computable exposure",
    ),
    item(
        410,
        "limit_premium_decay_regime",
        "market_emotion",
        "P1",
        ["local_raw_pool", "raw_queue_500"],
        ["RAW001020", "RAW001027"],
        "The premium of yesterday's limit-up basket decays when market emotion rolls over.",
        (
            "zscore(yesterday_limit_avg_return_T) "
            "- zscore(rolling_max(yesterday_limit_avg_return, N)) "
            "- zscore(abs(rolling_slope(yesterday_limit_avg_return, K)))"
        ),
        "limit_pool yesterday-limit basket, daily close or 14:57 proxy close, market calendar",
        ["trade_date", "ts_code", "is_prev_limit_up", "close", "price_1457"],
        "daily_or_1457_proxy",
        "For T+1 training use T close; for 14:57 live use price_1457 proxy and never use final close after cutoff.",
        "C326 is seal-rate collapse and C394 is high-low switch; neither directly measures yesterday-limit premium decay regime.",
        "candidate_ready_after_limit_pool_join",
        "formula window N/K should be locked before training; suggested N=20, K=5",
    ),
    item(
        411,
        "industry_limit_reversal_pressure",
        "industry_rotation",
        "P1",
        ["kysec_limit_industry_reversal_bigquant", "kysec_limit_industry_reversal_pdf"],
        [],
        "Industry-level limit-up/limit-down groups can create short-horizon reversal pressure in the industry.",
        (
            "zscore(industry_limit_up_member_share_Nd) "
            "- zscore(industry_limit_down_member_share_Nd) "
            "+ zscore(industry_limit_group_return_spread_Nd)"
        ),
        "industry membership, limit_pool, daily returns for industry members",
        ["trade_date", "ts_code", "industry_id", "is_limit_up", "is_limit_down", "ret_1d"],
        "daily",
        "Use only limit events and returns available by T close; for T+1 prediction map the T industry score to member stocks.",
        "Distinct from C337 industry flow and C369 LHB industry flow; this is price-limit effect based industry reversal/crowding.",
        "candidate_ready_after_industry_limit_pool_join",
        "short-line daily candidate; report origin is monthly industry rotation but formula can be tested on daily horizon",
    ),
    item(
        412,
        "multi_seat_buy_strength",
        "lhb_seat",
        "P1",
        ["local_raw_pool", "lhb_seat_style_sina", "lhb_seat_winrate_cs"],
        ["RAW000510", "RAW000511", "RAW000512", "RAW000513"],
        "Multiple strong seats buying together can signal coordinated short-line conviction.",
        (
            "count_distinct_buy_seats(amount_i >= seat_amount_threshold) "
            "* sum(top_buy_seat_amount_i) / (daily_amount + eps)"
        ),
        "LHB top buy seats, buy amount by seat, daily amount, optional known-seat catalog",
        ["trade_date", "ts_code", "seat_name", "buy_amount", "daily_amount"],
        "after_close_daily",
        "LHB is normally after-close; only use for T+1 or later unless exact intraday disclosure timestamp proves availability.",
        "C346 is buy-seat concentration HHI and C236 is buy/sell ratio; this measures breadth times amount strength.",
        "engineerable_after_lhb_backfill",
        "not a 14:57 factor; after-close T+1 only",
    ),
    item(
        413,
        "famous_seat_repeat_visit_score",
        "lhb_seat",
        "P1",
        ["local_raw_pool", "lhb_seat_style_sina", "lhb_seat_winrate_cs"],
        ["RAW000160", "RAW001287", "RAW002746"],
        "A seat that previously made money in the same stock/theme may revisit with higher follow-through probability.",
        (
            "sum(net_buy_amount_i * historical_same_stock_or_theme_winrate_i "
            "* exp(-days_since_last_profitable_visit_i / tau)) / (daily_amount + eps)"
        ),
        "LHB seat history, stock/theme mapping, historical post-LHB forward returns for prior events",
        ["trade_date", "ts_code", "seat_name", "net_buy_amount", "theme_id", "forward_return_history"],
        "after_close_daily",
        "Historical forward returns may only be used for past seat events; today's LHB signal is T+1 after disclosure.",
        "C363 is general seat alpha; this is same-stock/theme repeat-visit memory.",
        "engineerable_after_lhb_seat_history_cache",
        "must freeze seat-name normalization before training",
    ),
    item(
        414,
        "active_seat_absence_market_risk",
        "lhb_market",
        "P2",
        ["local_raw_pool", "lhb_seat_winrate_cs"],
        ["RAW000154"],
        "When historically active/profitable seats disappear from the LHB, risk appetite may be lower.",
        (
            "1 - count(active_seats_lookback appearing in today's LHB) "
            "/ max(count(active_seats_lookback), 1)"
        ),
        "market-wide LHB seat appearances and rolling active-seat catalog",
        ["trade_date", "seat_name", "lhb_appearance", "historical_seat_activity"],
        "after_close_daily",
        "After-close market-wide feature; use for next trading day only.",
        "No existing registry candidate measures market-wide absence of active seats; C364 is theme seat crowding conditional on appearances.",
        "engineerable_after_lhb_market_history_cache",
        "market-level feature broadcast to stocks; keep P2 until it proves useful",
    ),
    item(
        415,
        "intraday_wavelet_highfreq_energy_ratio",
        "minute_hf",
        "P2",
        ["stockformer_arxiv"],
        [],
        "Wavelet/time-frequency decomposition can summarize short-horizon high-frequency price-path energy.",
        "sum(detail_coefficients_energy_high_freq) / (total_wavelet_energy + eps) for minute close or return sequence up to cutoff",
        "1min bars: close; optional amount/volume sequence for parallel volume wavelet energy",
        ["trade_date", "ts_code", "bar_time", "close"],
        "1min",
        "Use only bars <= cutoff; post-14:57 bars must not enter live replay features.",
        "C353 is volume spectral residual; this is price-path wavelet high-frequency energy and is not a duplicate.",
        "engineerable_after_1min_cache",
        "P2 because implementation choices (wavelet family/level) must be locked before training",
    ),
    item(
        416,
        "volume_spike_memory_interval",
        "volume_memory",
        "P2",
        ["trading_volume_memory_arxiv"],
        [],
        "Intervals between abnormal volume-volatility spikes can show clustering/memory.",
        (
            "days_or_minutes_since_last_volume_volatility_spike "
            "/ (rolling_mean_inter_spike_interval_N + eps)"
        ),
        "daily volume or 1min volume history; spike threshold based on rolling volume-volatility z-score",
        ["trade_date", "ts_code", "volume", "amount"],
        "daily_or_1min",
        "For 14:57 version, compute intervals only using minute bars <= cutoff; daily version uses T close for T+1.",
        "C305 is single-session shock decay and C378 is intraday ridge persistence; this is cross-session/inter-spike memory.",
        "engineerable_after_volume_history_cache",
        "P2 until daily vs minute variant is selected",
    ),
]


def collect_candidate_ids(data: dict) -> list[str]:
    ids: list[str] = []
    for key in data.get("meta", {}).get("candidate_batches", []):
        batch = data.get(key)
        if not isinstance(batch, dict):
            continue
        entries = []
        if isinstance(batch.get("detail"), list):
            entries.extend(batch["detail"])
        for pkey in ("p0", "p1", "p2", "blocked"):
            if isinstance(batch.get(pkey), list):
                entries.extend(batch[pkey])
        for entry in entries:
            if isinstance(entry, dict) and entry.get("factor_id"):
                ids.append(entry["factor_id"])
    return ids


def append_human_registry() -> None:
    section = [
        "",
        "## Global Saturation Final Search 2026-05-18",
        "",
        "Purpose: expanded web/local/source saturation pass across social/TGB, broker reports, GitHub/open-source, academic papers, and local raw pool leftovers. Registry only: no training, no gpu_probe, no model/frozen config changes.",
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
            "Important asof notes:",
            "- C412-C414 are LHB after-close factors; use for T+1 only unless exact earlier disclosure timestamps are proven.",
            "- C407-C408 require timestamped event/theme/social labels before same-day use.",
            "- C409-C411 can be built from daily/limit/industry histories; C410 can optionally use a 14:57 proxy close.",
            "- C415-C416 need 1min or volume history and must be cutoff-bounded for 14:57 replay.",
        ]
    )
    with HUMAN_REGISTRY_PATH.open("a", encoding="utf-8") as f:
        f.write("\n".join(section) + "\n")


def write_report(summary: dict) -> None:
    priority_counts = Counter(row["priority"] for row in DETAIL)
    family_counts = Counter(row["family"] for row in DETAIL)
    lines = [
        "# Global Saturation Final Factor Search 2026-05-18",
        "",
        "Scope: expanded all-channel short-line factor search and strict registry screening.",
        "",
        "Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.",
        "",
        "## Search Surface",
        "",
        "- Local raw pool: 3075 records from TGB/social, short-line, and exploration documents.",
        "- Social/TGB/short video: Taoguba-style emotion/leader rules, Xueqiu/Guba style discussion, Bilibili/Douyin search surfaces.",
        "- Broker reports: high-frequency price-volume, smart money, price-limit industry reversal, LHB/seat behavior.",
        "- Academic papers: lottery preference/MAX-IVOL-skew, investor sentiment/overtrading, price limit dynamics, wavelet/time-frequency and volume-memory ideas.",
        "- GitHub/open-source: alpha101/alpha191/qlib-style formula libraries were checked; generic duplicates were not re-added.",
        "",
        "## Result",
        "",
        f"- Added candidates: {len(DETAIL)} ({DETAIL[0]['factor_id']} to {DETAIL[-1]['factor_id']})",
        f"- Priority counts: {dict(priority_counts)}",
        f"- Family counts: {dict(family_counts)}",
        "- All additions are `training_status=not_trained` and `lockbox_role=research_candidate`.",
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
            "## Deferred / Rejected Buckets",
            "",
            "- L2/tick/order-book cancellation and queue-depth factors: rejected until stable L2/tick fields exist; minute proxies already exist in C387 and related minute factors.",
            "- Pure slogan / discretionary trading rules: rejected unless they map to a reproducible stock-date scalar.",
            "- Generic technical libraries: not duplicated because C194/C391/C392 already cover the large technical-indicator bank.",
            "- Untimestamped social/video heat: kept as pipeline-only ideas, not same-day trainable signals.",
            "",
            "## Ten Saturation Checks",
            "",
        ]
    )
    checks = [
        "C001-C406 name/formula duplicate screen",
        "local raw pool leftovers (`capital_memory`, `LOTT`, LHB seat variants, limit premium)",
        "TGB/social rule pass",
        "Bilibili/Douyin timestamp feasibility pass",
        "broker report pass: high-frequency, limit board, LHB, industry reversal",
        "academic paper pass: lottery, price limits, sentiment, wavelet, volume memory",
        "GitHub/open-source pass: alpha101/alpha191/qlib technical libraries",
        "data availability pass: daily, limit_pool, LHB, 1min, social, event/theme labels",
        "asof/leakage pass: 14:57 vs T close vs after-close T+1",
        "registry integrity pass: contiguous IDs, no duplicates, not trained/frozen/final",
    ]
    for idx, check in enumerate(checks, 1):
        lines.append(f"{idx}. {check}")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- Registry candidate count after write: {summary['registry_candidate_count']}",
            f"- Missing ID check: {summary['missing_ids']}",
            f"- Duplicate ID check: {summary['duplicate_ids']}",
            f"- Unsafe status check: {summary['unsafe_status_count']}",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if BATCH in data:
        raise SystemExit(f"{BATCH} already exists; refusing to duplicate")

    existing_ids = set(collect_candidate_ids(data))
    new_ids = [row["factor_id"] for row in DETAIL]
    overlap = sorted(existing_ids & set(new_ids))
    if overlap:
        raise SystemExit(f"ID overlap: {overlap}")

    data[BATCH] = {
        "search_date": TODAY,
        "search_round": "global_saturation_final",
        "purpose": "expanded all-channel short-line factor search with strict registry screening",
        "scope": "factor-library only; no training; no gpu_probe; no model/frozen config changes",
        "source_evidence": SOURCES,
        "selection_gate": [
            "must have explicit computable scalar definition",
            "must name data need and required columns",
            "must state asof rule and leakage boundary",
            "must not duplicate existing C001-C406 registry candidates",
            "must remain not_trained and research_candidate",
        ],
        "total": len(DETAIL),
        "by_priority": dict(Counter(row["priority"] for row in DETAIL)),
        "by_family": dict(Counter(row["family"] for row in DETAIL)),
        "detail": DETAIL,
        "deferred_or_rejected": [
            {
                "bucket": "true_l2_tick_orderbook",
                "reason": "Needs stable L2/tick/orderbook fields. Do not register exact queue/cancel factors until data source is confirmed.",
            },
            {
                "bucket": "pure_social_or_video_text",
                "reason": "Requires timestamped symbol/theme extraction. Keep as pipeline candidate only.",
            },
            {
                "bucket": "generic_formula_libraries",
                "reason": "Covered by C194/C391/C392 technical bank unless a distinct short-line formula has a source and asof rule.",
            },
        ],
    }

    meta = data.setdefault("meta", {})
    batches = meta.setdefault("candidate_batches", [])
    if BATCH not in batches:
        batches.append(BATCH)
    meta["updated"] = TODAY
    meta["latest_candidate_batch"] = BATCH
    meta["global_saturation_final_20260518"] = {
        "added_count": len(DETAIL),
        "id_range": [DETAIL[0]["factor_id"], DETAIL[-1]["factor_id"]],
        "priority_counts": dict(Counter(row["priority"] for row in DETAIL)),
        "family_counts": dict(Counter(row["family"] for row in DETAIL)),
        "after_close_only": ["C412", "C413", "C414"],
        "pipeline_gated": ["C407", "C408"],
        "minute_or_1457_capable_after_data": ["C410", "C415", "C416"],
    }

    all_ids = collect_candidate_ids(data)
    numeric_ids = sorted(int(fid[1:]) for fid in all_ids if fid.startswith("C") and fid[1:].isdigit())
    missing = [f"C{i:03d}" for i in range(1, max(numeric_ids) + 1) if i not in numeric_ids]
    duplicates = [fid for fid, count in Counter(all_ids).items() if count > 1]
    unsafe_status_count = 0
    for key in meta.get("candidate_batches", []):
        batch = data.get(key, {})
        detail = batch.get("detail", []) if isinstance(batch, dict) else []
        for row in detail:
            if not isinstance(row, dict):
                continue
            unsafe_status_count += int(bool(row.get("is_passed")))
            unsafe_status_count += int(bool(row.get("is_final_unseen")))
            unsafe_status_count += int(bool(row.get("is_frozen_modified")))

    meta["registry_candidate_count"] = len(set(all_ids))

    REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    append_human_registry()
    write_report(
        {
            "registry_candidate_count": meta["registry_candidate_count"],
            "missing_ids": missing,
            "duplicate_ids": duplicates,
            "unsafe_status_count": unsafe_status_count,
        }
    )
    print(f"Added {len(DETAIL)} candidates: {DETAIL[0]['factor_id']}-{DETAIL[-1]['factor_id']}")
    print(f"Registry candidate count: {meta['registry_candidate_count']}")
    print(f"Missing IDs: {missing}")
    print(f"Duplicate IDs: {duplicates}")
    print(f"Unsafe status count: {unsafe_status_count}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
