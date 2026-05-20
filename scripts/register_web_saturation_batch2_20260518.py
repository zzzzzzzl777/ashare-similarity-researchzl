"""Register the 2026-05-18 web saturation factor batch.

Scope: factor-library only. This script does not train, run gpu_probe, or
change model/frozen configs.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
HUMAN_REGISTRY_PATH = ROOT / "docs" / "factor_registry.md"
REPORT_PATH = ROOT / "docs" / "web_saturation_factor_search_20260518.md"
BATCH_KEY = "candidates_20260518_web_saturation2"
TODAY = "2026-05-18"


SOURCES = {
    "kaiyuan_volume_peak_ridge_valley": "https://www.fhyanbao.com/rpview/1679996",
    "fangzheng_smart_money": "https://bigquant.com/wiki/doc/4OvIDMRuTH",
    "xingye_volume_distribution_alpha": "https://bigquant.com/wiki/doc/8bghnLBtpA",
    "kaiyuan_single_trade_amount": "https://bigquant.com/square/paper/74353d24-a9cf-4d17-a9fb-c431ece0a52e",
    "chinese_hf_liquidity_ssrn": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4191675",
    "china_limit_order_book_volatility": "https://www.sciencedirect.com/science/article/pii/S0927538X14000183",
    "price_limit_prehit_dynamics": "https://arxiv.org/abs/1503.03548",
    "tushare_stk_factor": "https://www.tushare.pro/document/2?doc_id=296",
}


DETAILS = [
    {
        "name": "hcvp_price_volume_corr",
        "priority": "P0",
        "family": "minute_hf",
        "source_type": "broker_report",
        "source_ids": ["kaiyuan_volume_peak_ridge_valley", "xingye_volume_distribution_alpha"],
        "raw_idea": "High-price-zone price-volume correlation (HCVP-style) from intraday minute bars.",
        "computable_definition": (
            "corr(return_i, volume_share_i) restricted to minutes where close_i is in the top "
            "30pct of the observed intraday price range up to cutoff"
        ),
        "data_need": "1min bars: close, volume/amount; optional trailing N-day smoothing",
        "asof_rule": "For 14:57 live use only bars with bar_time <= 14:57; for post-close research use T+1 full-day bars.",
        "leakage_risk": "none if cutoff-bounded; do not use post-14:57 bars for live replay.",
        "duplicate_check": "Distinct from C297 all-session price-volume corr and C301 high-price volume share; this is correlation within high-price zone.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "lcvp_price_volume_corr",
        "priority": "P1",
        "family": "minute_hf",
        "source_type": "broker_report",
        "source_ids": ["kaiyuan_volume_peak_ridge_valley", "xingye_volume_distribution_alpha"],
        "raw_idea": "Low-price-zone price-volume correlation (LCVP-style) from intraday minute bars.",
        "computable_definition": (
            "corr(return_i, volume_share_i) restricted to minutes where close_i is in the bottom "
            "30pct of the observed intraday price range up to cutoff"
        ),
        "data_need": "1min bars: close, volume/amount; optional trailing N-day smoothing",
        "asof_rule": "For 14:57 live use only bars with bar_time <= 14:57; for post-close research use T+1 full-day bars.",
        "leakage_risk": "none if cutoff-bounded; do not use post-14:57 bars for live replay.",
        "duplicate_check": "Distinct from C302 low-price absorption: this measures correlation, not repair from low-zone VWAP.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "hcvp_lcvp_corr_spread",
        "priority": "P0",
        "family": "minute_hf",
        "source_type": "broker_report",
        "source_ids": ["kaiyuan_volume_peak_ridge_valley", "xingye_volume_distribution_alpha"],
        "raw_idea": "Spread between high-price and low-price volume-price correlation.",
        "computable_definition": "hcvp_price_volume_corr - lcvp_price_volume_corr",
        "data_need": "Derived from C371/C372 once 1min bars are available",
        "asof_rule": "Same cutoff rule as C371/C372.",
        "leakage_risk": "inherits cutoff risk from C371/C372 only.",
        "duplicate_check": "No existing spread between high-price-zone and low-price-zone price-volume correlation.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "intraday_smart_money_q_return",
        "priority": "P0",
        "family": "minute_smart_money",
        "source_type": "broker_report",
        "source_ids": ["fangzheng_smart_money"],
        "raw_idea": "Smart-money minute selection using |return| scaled by sqrt(volume/amount).",
        "computable_definition": (
            "For each minute q_i = abs(return_i) / sqrt(amount_share_i + eps); "
            "factor = volume-weighted return over top-20pct q_i minutes"
        ),
        "data_need": "1min bars: close, amount or volume",
        "asof_rule": "For 14:57 live compute only from minutes <= 14:57; post-close full-day version must be separate.",
        "leakage_risk": "none if top-q threshold is computed only on observed minutes up to cutoff.",
        "duplicate_check": "C013 is an old undefined moneyflow idea; no registered 1min smart-money q-return formula exists.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "intraday_smart_money_q_volume_share",
        "priority": "P1",
        "family": "minute_smart_money",
        "source_type": "broker_report",
        "source_ids": ["fangzheng_smart_money"],
        "raw_idea": "How much intraday volume is concentrated in smart-money q minutes.",
        "computable_definition": "sum(volume_i for top-20pct q_i minutes) / (sum(volume_i up to cutoff) + eps)",
        "data_need": "1min bars: close, amount or volume",
        "asof_rule": "For 14:57 live compute only from minutes <= 14:57.",
        "leakage_risk": "none if cutoff-bounded.",
        "duplicate_check": "Distinct from C374 return component and from C315 entropy; this is smart-money-selected participation share.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "minute_volume_benford_deviation",
        "priority": "P1",
        "family": "minute_volume_shape",
        "source_type": "broker_report",
        "source_ids": ["fangzheng_smart_money"],
        "raw_idea": "Deviation of intraday minute volume leading-digit distribution from Benford-like baseline.",
        "computable_definition": (
            "sum_d abs(freq(first_digit(volume_i)=d) - log10(1 + 1/d)) for d=1..9, "
            "using nonzero minute volumes up to cutoff"
        ),
        "data_need": "1min bars: volume",
        "asof_rule": "For 14:57 live use only minute bars <= 14:57; full-day post-close is a separate feature.",
        "leakage_risk": "none if cutoff-bounded.",
        "duplicate_check": "No existing Benford/leading-digit intraday volume-shape feature.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "volume_peak_return_contribution",
        "priority": "P0",
        "family": "minute_volume_peak",
        "source_type": "broker_report",
        "source_ids": ["kaiyuan_volume_peak_ridge_valley", "xingye_volume_distribution_alpha"],
        "raw_idea": "Return contribution of local volume peaks.",
        "computable_definition": (
            "sum(return_i * volume_share_i for local volume peaks with volume_i >= p90(volume up to cutoff))"
        ),
        "data_need": "1min bars: close, volume/amount",
        "asof_rule": "Local peaks must be identified only with already observed neighbor bars; for live 14:57 do not use future bars.",
        "leakage_risk": "watch local-peak definition; use left/right neighbors only when both are <= cutoff.",
        "duplicate_check": "Distinct from C177 volume clustering and C376/C377 peak density; this weights peak-minute returns.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "volume_ridge_persistence_share",
        "priority": "P1",
        "family": "minute_volume_peak",
        "source_type": "broker_report",
        "source_ids": ["kaiyuan_volume_peak_ridge_valley"],
        "raw_idea": "Persistence of high-volume ridges rather than isolated volume spikes.",
        "computable_definition": "max_consecutive_minutes(volume_i >= p80(volume up to cutoff)) / observed_minute_count",
        "data_need": "1min bars: volume/amount",
        "asof_rule": "For 14:57 live use only bars <= 14:57.",
        "leakage_risk": "none if cutoff-bounded.",
        "duplicate_check": "Distinct from C177 peak/mean clustering and C315 entropy; this is run-length persistence.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "volume_valley_reversal_strength",
        "priority": "P1",
        "family": "minute_volume_peak",
        "source_type": "broker_report",
        "source_ids": ["kaiyuan_volume_peak_ridge_valley"],
        "raw_idea": "Whether price rebounds after local low-volume valleys.",
        "computable_definition": (
            "mean(return_{i+1:i+5}) after local volume valleys where volume_i <= p20(volume up to cutoff), "
            "with horizons clipped to cutoff"
        ),
        "data_need": "1min bars: close, volume/amount",
        "asof_rule": "At 14:57 only compute future-after-valley returns when the future bars are already observed.",
        "leakage_risk": "must not use returns after 14:57 for live; otherwise no leakage.",
        "duplicate_check": "No existing local-volume-valley reversal feature; different from broad pullback/reversal factors.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "volume_peak_valley_price_spread",
        "priority": "P1",
        "family": "minute_volume_peak",
        "source_type": "broker_report",
        "source_ids": ["kaiyuan_volume_peak_ridge_valley"],
        "raw_idea": "Price level difference between high-volume peaks and low-volume valleys.",
        "computable_definition": "vwap(local volume peak minutes) / (vwap(local volume valley minutes) + eps) - 1",
        "data_need": "1min bars: close or vwap, volume/amount",
        "asof_rule": "For 14:57 live use only peak/valley minutes observed by cutoff.",
        "leakage_risk": "none if cutoff-bounded.",
        "duplicate_check": "Distinct from C301 high-price volume share and C302 low-price absorption; compares peak-vs-valley VWAP levels.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "price_jump_peak_density",
        "priority": "P0",
        "family": "minute_price_jump",
        "source_type": "broker_report",
        "source_ids": ["chinese_hf_liquidity_ssrn", "price_limit_prehit_dynamics"],
        "raw_idea": "Density of extreme 1min price jumps during the observed session.",
        "computable_definition": "count(abs(return_i) >= p95(abs(return up to cutoff))) / observed_minute_count",
        "data_need": "1min bars: close",
        "asof_rule": "For 14:57 live use only returns whose end time <= 14:57.",
        "leakage_risk": "none if cutoff-bounded.",
        "duplicate_check": "Distinct from C351 return-state entropy and C293 downside vol share; this counts jump-event density.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "price_jump_ridge_followthrough",
        "priority": "P1",
        "family": "minute_price_jump",
        "source_type": "broker_report",
        "source_ids": ["chinese_hf_liquidity_ssrn", "price_limit_prehit_dynamics"],
        "raw_idea": "Whether consecutive price-jump ridges follow through instead of mean reverting.",
        "computable_definition": (
            "sum(return_i for minutes inside consecutive abs(return)>=p90 jump ridges) "
            "/ (sum(abs(return_i) inside those ridges) + eps)"
        ),
        "data_need": "1min bars: close",
        "asof_rule": "For 14:57 live use only minute returns observed by cutoff.",
        "leakage_risk": "none if cutoff-bounded.",
        "duplicate_check": "Distinct from C304 path smoothness; this isolates clustered jump-ridge directionality.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "price_jump_valley_reversal",
        "priority": "P1",
        "family": "minute_price_jump",
        "source_type": "broker_report",
        "source_ids": ["chinese_hf_liquidity_ssrn"],
        "raw_idea": "Reversal after calm intervals between price-jump clusters.",
        "computable_definition": (
            "mean(next_5min_return after intervals where abs(return_i) <= p20(abs(return up to cutoff)) "
            "and preceding 10min had a jump)"
        ),
        "data_need": "1min bars: close",
        "asof_rule": "At 14:57 only compute next_5min_return if all bars are already observed.",
        "leakage_risk": "must clip next-return horizon to cutoff for live replay.",
        "duplicate_check": "No existing jump-valley reversal feature; broader reversal factors do not condition on jump clusters.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "minute_amount_autocorr_1",
        "priority": "P1",
        "family": "minute_amount_shape",
        "source_type": "broker_report",
        "source_ids": ["kaiyuan_single_trade_amount", "xingye_volume_distribution_alpha"],
        "raw_idea": "Persistence of minute amount flow.",
        "computable_definition": "corr(amount_i, amount_{i-1}) over observed 1min bars",
        "data_need": "1min bars: amount",
        "asof_rule": "For 14:57 live use only amount bars <= 14:57.",
        "leakage_risk": "none if cutoff-bounded.",
        "duplicate_check": "No registered minute amount autocorrelation; C091/C197 are cross-source/daily alignments, not intraday amount persistence.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "minute_amount_tail_kurtosis",
        "priority": "P1",
        "family": "minute_amount_shape",
        "source_type": "broker_report",
        "source_ids": ["kaiyuan_single_trade_amount", "xingye_volume_distribution_alpha"],
        "raw_idea": "Tail heaviness of minute amount distribution.",
        "computable_definition": "standardized fourth moment of amount_i / mean(amount up to cutoff)",
        "data_need": "1min bars: amount",
        "asof_rule": "For 14:57 live use only amount bars <= 14:57.",
        "leakage_risk": "none if cutoff-bounded.",
        "duplicate_check": "Distinct from C295 return kurtosis and C359 unit amount entropy; this is amount-tail shape.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "minute_bipower_jump_ratio",
        "priority": "P0",
        "family": "minute_realized_jump",
        "source_type": "academic_paper",
        "source_ids": ["chinese_hf_liquidity_ssrn"],
        "raw_idea": "Realized jump component using bipower variation proxy.",
        "computable_definition": (
            "RV=sum(r_i^2); BV=(pi/2)*sum(abs(r_i)*abs(r_{i-1})); factor=max(RV-BV,0)/(RV+eps)"
        ),
        "data_need": "1min bars: close",
        "asof_rule": "For 14:57 live use only returns whose end time <= 14:57.",
        "leakage_risk": "none if cutoff-bounded.",
        "duplicate_check": "Distinct from C189 frequency RV ratio and C293 downside variance share; this isolates jump variation.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "bar_vpin_proxy_1min",
        "priority": "P1",
        "family": "minute_orderflow_proxy",
        "source_type": "academic_paper",
        "source_ids": ["china_limit_order_book_volatility", "chinese_hf_liquidity_ssrn"],
        "raw_idea": "Bar-level VPIN proxy without true aggressor-side L2 labels.",
        "computable_definition": (
            "rolling_mean(abs(sum(sign(return_i)*volume_i over volume buckets)) / "
            "(sum(volume_i over buckets)+eps))"
        ),
        "data_need": "1min bars: close, volume; true L2 buy/sell labels optional but not required for this proxy",
        "asof_rule": "For 14:57 live use only bars <= 14:57 and past buckets.",
        "leakage_risk": "none if cutoff-bounded; label clearly as proxy, not true L2 VPIN.",
        "duplicate_check": "Distinct from C178 OFI proxy: C178 is signed-volume average, this is absolute bucket toxicity.",
        "engineering_status": "engineerable_after_1min_cache",
    },
    {
        "name": "hsgt_top10_member_churn",
        "priority": "P1",
        "family": "northbound_flow",
        "source_type": "api_derived",
        "source_ids": ["tushare_stk_factor"],
        "raw_idea": "Turnover of stock membership in northbound top10 active list.",
        "computable_definition": "1 - jaccard(top10_stock_set_Tminus1, top10_stock_set_Tminus2), optionally mapped to stock by membership",
        "data_need": "hsgt_top10 historical stock list",
        "asof_rule": "Use T-1 published top10 list for live 14:57 unless same-day timestamp proves availability before cutoff.",
        "leakage_risk": "same-day top10 can be post-close; default T-1 only.",
        "duplicate_check": "Distinct from C335 entry streak and C368 turnover crowding; this measures list churn/regime instability.",
        "engineering_status": "engineerable_after_hsgt_top10_backfill",
    },
    {
        "name": "ccass_holder_concentration_delta",
        "priority": "P1",
        "family": "northbound_flow",
        "source_type": "api_derived",
        "source_ids": ["tushare_stk_factor"],
        "raw_idea": "Change in CCASS holding concentration across participants.",
        "computable_definition": "HHI(participant_share_t) - HHI(participant_share_{t-5}) for each stock",
        "data_need": "ccass_hold participant-level holdings if available; otherwise stock-level ccass only is insufficient",
        "asof_rule": "Use latest record with publication date <= T-1 for 14:57 live.",
        "leakage_risk": "post-close publication risk; enforce record date/publication date lag.",
        "duplicate_check": "Distinct from C080/C211/C336 which track aggregate foreign holding change/acceleration, not holder concentration.",
        "engineering_status": "engineerable_if_ccass_participant_fields_available",
    },
    {
        "name": "industry_turnover_crowding_score",
        "priority": "P1",
        "family": "industry_crowding",
        "source_type": "api_derived",
        "source_ids": ["tushare_stk_factor"],
        "raw_idea": "Industry-level crowding from turnover, moneyflow and constituent co-movement.",
        "computable_definition": (
            "z(industry_turnover_rate) + z(industry_moneyflow_net_ratio) + z(mean_pairwise_return_corr_20d)"
        ),
        "data_need": "industry constituents, daily turnover/amount, moneyflow_ind_ths or comparable industry flow",
        "asof_rule": "For live 14:57 use T-1 industry flow/turnover unless same-day source timestamp is proven before cutoff.",
        "leakage_risk": "same-day full-industry moneyflow may be post-close; default T-1.",
        "duplicate_check": "Distinct from C337 industry flow rotation acceleration and C369 LHB industry flow; this is crowding/overheating score.",
        "engineering_status": "engineerable_after_industry_flow_backfill",
    },
    {
        "name": "technical_signal_consensus_261",
        "priority": "P2",
        "family": "technical_indicator_bank",
        "source_type": "api_derived",
        "source_ids": ["tushare_stk_factor"],
        "raw_idea": "Consensus breadth across vendor-computed stk_factor_pro indicators.",
        "computable_definition": (
            "mean(sign(z_i) for curated non-duplicate technical columns after orientation normalization), "
            "computed within stock over trailing window"
        ),
        "data_need": "stk_factor_pro indicator bank plus curated column orientation map",
        "asof_rule": "Use T-1 vendor indicators for live unless same-day indicators are locally recomputed before 14:57.",
        "leakage_risk": "vendor same-day daily indicator may include close; default T-1.",
        "duplicate_check": "C194 registers the raw technical bank; this is a derived consensus scalar, not the whole bank.",
        "engineering_status": "engineerable_after_stk_factor_pro_catalog",
    },
    {
        "name": "technical_signal_disagreement_entropy",
        "priority": "P2",
        "family": "technical_indicator_bank",
        "source_type": "api_derived",
        "source_ids": ["tushare_stk_factor"],
        "raw_idea": "Disagreement/dispersion across technical indicator signals.",
        "computable_definition": "entropy of {-1,0,+1} oriented technical signal votes from curated stk_factor_pro columns",
        "data_need": "stk_factor_pro indicator bank plus curated orientation map",
        "asof_rule": "Use T-1 vendor indicators for live unless same-day indicators are locally recomputed before 14:57.",
        "leakage_risk": "vendor same-day daily indicator may include close; default T-1.",
        "duplicate_check": "Distinct from C389 consensus mean; this measures uncertainty/disagreement.",
        "engineering_status": "engineerable_after_stk_factor_pro_catalog",
    },
]


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def iter_candidate_objects(registry: dict):
    for value in registry.values():
        if not isinstance(value, dict):
            continue
        if isinstance(value.get("detail"), list):
            yield from [x for x in value["detail"] if isinstance(x, dict) and x.get("factor_id")]
        for bucket in ("p0", "p1", "p2", "blocked"):
            if isinstance(value.get(bucket), list):
                yield from [x for x in value[bucket] if isinstance(x, dict) and x.get("factor_id")]


def current_max_id(registry: dict) -> int:
    nums = []
    for item in iter_candidate_objects(registry):
        fid = item["factor_id"]
        if fid.startswith("C") and fid[1:].isdigit():
            nums.append(int(fid[1:]))
    return max(nums) if nums else 0


def remove_existing_batch(registry: dict) -> None:
    if BATCH_KEY in registry:
        del registry[BATCH_KEY]
    meta = registry.setdefault("meta", {})
    batches = meta.get("candidate_batches")
    if isinstance(batches, list):
        meta["candidate_batches"] = [x for x in batches if x != BATCH_KEY]


def prepare_details(start_id: int) -> list[dict]:
    details = []
    for offset, spec in enumerate(DETAILS):
        item = dict(spec)
        item["factor_id"] = f"C{start_id + offset:03d}"
        item["training_status"] = "not_trained"
        item["lockbox_role"] = "research_candidate"
        item["is_passed"] = False
        item["is_final_unseen"] = False
        item["is_frozen_modified"] = False
        details.append(item)
    return details


def build_batch(details: list[dict]) -> dict:
    return {
        "search_date": TODAY,
        "search_round": "web_saturation2",
        "scope": "factor-library only; no training; no gpu_probe; no model/frozen config changes",
        "source_evidence": SOURCES,
        "selection_gate": [
            "must have computable scalar formula",
            "must state data_need and asof_rule",
            "must be distinct from existing C001-C370 by name and concept",
            "must be short-line relevant",
            "must be marked not_trained + research_candidate",
        ],
        "detail": details,
        "deferred_or_rejected": [
            {
                "idea": "true L2 limit-order-book slope/depth/cancel factors",
                "reason": "Not registered unless stable L2/tick/orderbook fields exist. Minute-bar proxy VPIN is registered separately as proxy only.",
            },
            {
                "idea": "single-trade amount QUA/MTS/MTE/SR exact factors",
                "reason": "Exact construction needs per-trade count/size series; only minute-bar amount proxies are registered here.",
            },
            {
                "idea": "bulk Alpha101/Alpha191 libraries",
                "reason": "Need formula-by-formula translation, dedup and asof review; not bulk-imported.",
            },
            {
                "idea": "pure social-media text rules",
                "reason": "Not registered unless converted to timestamped stock-level numeric series.",
            },
        ],
    }


def update_meta(registry: dict, details: list[dict]) -> None:
    meta = registry.setdefault("meta", {})
    batches = meta.setdefault("candidate_batches", [])
    if BATCH_KEY not in batches:
        batches.append(BATCH_KEY)
    meta["updated"] = TODAY
    meta["latest_candidate_batch"] = BATCH_KEY
    meta["web_saturation2_20260518"] = {
        "added_count": len(details),
        "id_range": [details[0]["factor_id"], details[-1]["factor_id"]],
        "priority_counts": dict(Counter(x["priority"] for x in details)),
        "family_counts": dict(Counter(x["family"] for x in details)),
    }
    meta["registry_candidate_count"] = len(list(iter_candidate_objects(registry)))


def render_report(batch: dict) -> str:
    details = batch["detail"]
    lines = [
        "# Web Saturation Short-Line Factor Search 2026-05-18",
        "",
        "Scope: factor-library only. No training, no gpu_probe, no model or frozen config changes.",
        "",
        "## Expanded Search Surface",
        "",
        "- Broker high-frequency volume peak/ridge/valley and volume-distribution reports",
        "- Fangzheng smart-money minute-bar research and Benford/leading-digit idea",
        "- Minute price-volume correlation slice family (HCVP/LCVP style)",
        "- Realized jump / bipower variation and bar-level VPIN proxy literature",
        "- Tushare/API feasibility pass for HSGT, CCASS, industry flow, stk_factor_pro",
        "- Local raw pool cross-check against 3,075 prior raw candidates",
        "",
        "## Source Evidence",
        "",
    ]
    for key, url in SOURCES.items():
        lines.append(f"- `{key}`: {url}")
    lines += [
        "",
        "## Added To Registry",
        "",
        f"- Batch: `{BATCH_KEY}`",
        f"- Count: {len(details)}",
        f"- ID range: `{details[0]['factor_id']}-{details[-1]['factor_id']}`",
        f"- Priority counts: {dict(Counter(x['priority'] for x in details))}",
        f"- Family counts: {dict(Counter(x['family'] for x in details))}",
        "",
        "| ID | Name | Priority | Family | Data Need | Engineering | Asof |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in details:
        lines.append(
            f"| {item['factor_id']} | {item['name']} | {item['priority']} | {item['family']} | "
            f"{item['data_need']} | {item['engineering_status']} | {item['asof_rule']} |"
        )
    lines += [
        "",
        "## Deferred / Not Registered",
        "",
    ]
    for item in batch["deferred_or_rejected"]:
        lines.append(f"- `{item['idea']}`: {item['reason']}")
    lines += [
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
    ]
    return "\n".join(lines)


def append_human_registry(batch: dict) -> None:
    details = batch["detail"]
    section = [
        "",
        f"## Web Saturation Search 2 {TODAY}",
        "",
        f"- Batch: `{BATCH_KEY}`",
        f"- Added: {len(details)} candidates (`{details[0]['factor_id']}-{details[-1]['factor_id']}`)",
        "- Scope: factor-library only; no training; no gpu_probe; no model/frozen config changes.",
        "",
        "| ID | Name | Priority | Family | Engineering |",
        "|---|---|---|---|---|",
    ]
    for item in details:
        section.append(
            f"| {item['factor_id']} | {item['name']} | {item['priority']} | {item['family']} | {item['engineering_status']} |"
        )
    section += [
        "",
        f"Full report: `{REPORT_PATH}`",
        "",
    ]
    text = HUMAN_REGISTRY_PATH.read_text(encoding="utf-8")
    marker = f"## Web Saturation Search 2 {TODAY}"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n"
    HUMAN_REGISTRY_PATH.write_text(text.rstrip() + "\n" + "\n".join(section), encoding="utf-8")


def validate(registry: dict, batch: dict) -> None:
    required = {
        "factor_id",
        "name",
        "priority",
        "family",
        "computable_definition",
        "data_need",
        "asof_rule",
        "leakage_risk",
        "duplicate_check",
        "training_status",
        "lockbox_role",
    }
    items = list(iter_candidate_objects(registry))
    ids = [x["factor_id"] for x in items]
    nums = sorted(int(x[1:]) for x in ids if x.startswith("C") and x[1:].isdigit())
    missing = [i for i in range(1, max(nums) + 1) if i not in nums]
    if missing:
        raise AssertionError(f"missing C IDs: {missing[:20]}")
    if len(ids) != len(set(ids)):
        raise AssertionError("duplicate factor_id")
    names = [x.get("name") for x in items if x.get("name")]
    if len(names) != len(set(names)):
        dup = [name for name, count in Counter(names).items() if count > 1][:20]
        raise AssertionError(f"duplicate names: {dup}")
    details = batch["detail"]
    for item in details:
        missing_keys = sorted(required - set(item))
        if missing_keys:
            raise AssertionError(f"{item.get('factor_id')} missing {missing_keys}")
        if item["training_status"] != "not_trained":
            raise AssertionError(f"{item['factor_id']} training_status not not_trained")
        if item["lockbox_role"] != "research_candidate":
            raise AssertionError(f"{item['factor_id']} lockbox_role not research_candidate")
        if item.get("is_passed") or item.get("is_final_unseen") or item.get("is_frozen_modified"):
            raise AssertionError(f"{item['factor_id']} has forbidden final/pass/frozen flag")
    if registry["meta"]["registry_candidate_count"] != len(items):
        raise AssertionError("meta registry_candidate_count mismatch")


def main() -> None:
    registry = load_registry()
    remove_existing_batch(registry)
    start = current_max_id(registry) + 1
    details = prepare_details(start)
    batch = build_batch(details)
    registry[BATCH_KEY] = batch
    update_meta(registry, details)
    validate(registry, batch)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(render_report(batch), encoding="utf-8")
    append_human_registry(batch)
    print(f"Registered {len(details)} candidates {details[0]['factor_id']}-{details[-1]['factor_id']}")
    print(f"Report {REPORT_PATH}")
    print("Validation PASS")


if __name__ == "__main__":
    main()
