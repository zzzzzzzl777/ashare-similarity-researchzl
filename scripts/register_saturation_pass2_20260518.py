"""Register second saturation-pass short-line factor candidates.

This is a factor-library update only. It does not train, run gpu_probe, or
modify model/frozen configuration.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
HUMAN_REGISTRY_PATH = ROOT / "docs" / "factor_registry.md"
REPORT_PATH = ROOT / "docs" / "saturation_pass2_factor_search_20260518.md"
BATCH = "candidates_20260518_saturation_pass2"
TODAY = "2026-05-18"


SOURCES = {
    "raw_pool_index": r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json",
    "raw_queue_500": str(ROOT / "docs" / "raw_to_registry_review_queue_500_20260506.md"),
    "omnibus_addendum3": str(ROOT / "docs" / "four_source_shortline_omnibus_candidate_addendum3_20260517.md"),
    "factor_data_availability_audit": str(ROOT / "docs" / "factor_data_availability_audit.md"),
    "weak_to_strong_tgb": "https://m.tgb.cn/a/2pMJZvpgUtI",
    "weak_to_strong_tgb_2": "https://m.tgb.cn/a/2rlgmUsdvAp-1",
    "auction_xueqiu": "https://xueqiu.com/6215012773/248723272",
    "hf_bigquant": "https://bigquant.com/square/paper/8fcfe5cd-cdd0-4c5e-af7c-f97fe0a15fa3",
    "guba_sentiment_bigquant": "https://bigquant.com/square/paper/86f08052-3aba-4ace-9577-6c6c2ceede7e",
    "guba_crash_risk_cnki": "https://cnki.huanghuai.edu.cn/KCMS/detail/detail.aspx?dbcode=CMFD&dbname=CMFD2022&filename=1022442154.nh",
    "media_sentiment_attention": "https://cdn.ebiotrade.com/newsf/2025-6/20250606140614642.htm",
    "convertible_sina": "https://finance.sina.com.cn/money/bond/market/2020-02-13/doc-iimxyqvz2364173.shtml",
    "convertible_force_redemption_pdf": "https://www.htsec.com/jfimg/colimg/upload/20230830/1693357327325039220.pdf",
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
        "source_type": "saturation_pass2_20260518",
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
                "second_saturation_search",
                "local_raw_pool_review",
                "duplicate_screened_against_C001_C425",
                "computable_definition_present",
                "data_need_present",
                "asof_rule_present",
                "not_training_result_claim",
            ],
        },
    }


DETAIL = [
    factor(
        426,
        "yesterday_limit_open_premium",
        "limit_premium",
        "P1",
        ["omnibus_addendum3", "auction_xueqiu"],
        [],
        "Yesterday's limit-up basket opening premium is a short-line emotion continuation signal.",
        "mean((open_T / close_T_minus_1 - 1) for stocks with is_limit_up_T_minus_1)",
        "limit_pool yesterday basket and daily open/prev close",
        ["trade_date", "ts_code", "is_prev_limit_up", "open", "prev_close"],
        "daily_open",
        "At 09:25/09:30 use open/auction final only for T; do not use T close.",
        "C410 measures decay of the yesterday-limit basket through the day; this is the opening premium anchor.",
        "engineerable_after_limit_pool_and_open_join",
        "requires correct previous-limit basket membership",
    ),
    factor(
        427,
        "board_height_ceiling_proximity",
        "limit_board",
        "P1",
        ["omnibus_addendum3", "weak_to_strong_tgb"],
        [],
        "Short-line attention increases when current board height approaches the recent market ceiling.",
        "current_board_height / (rolling_max_market_board_height_N + eps)",
        "limit_pool board_count history",
        ["trade_date", "ts_code", "board_count", "market_max_board_height"],
        "daily_or_cutoff",
        "Use only board counts known by cutoff; daily full session version is T+1.",
        "C322 measures compression speed of max height; this is stock-level proximity to the recent ceiling.",
        "engineerable_after_limit_pool_history",
        "lock window N before training, suggested 60 trading days",
    ),
    factor(
        428,
        "subnew_limit_board_heat",
        "subnew_board",
        "P2",
        ["omnibus_addendum3", "raw_pool_index"],
        [],
        "Sub-new stocks can form a separate speculative heat cycle in short-line markets.",
        "mean(board_count or limit_up_flag for stocks with listing_age_days <= N)",
        "listing date, limit_pool, daily returns",
        ["trade_date", "ts_code", "listing_date", "listing_age_days", "is_limit_up", "board_count"],
        "daily",
        "Use listing age and limit events available by cutoff; full-day result is T+1.",
        "No current C001-C425 candidate isolates sub-new cohort board heat.",
        "needs_listing_age_limit_pool_join",
        "P2 because sub-new definition and universe filters must be locked",
    ),
    factor(
        429,
        "seal_time_distribution_entropy",
        "limit_board",
        "P1",
        ["omnibus_addendum3", "weak_to_strong_tgb"],
        [],
        "Market-wide seal-time concentration can distinguish unified strength from scattered weak boards.",
        "-sum(p_bucket * log(p_bucket)) over seal-time buckets for today's limit-up stocks",
        "limit_pool first seal time and market calendar",
        ["trade_date", "ts_code", "first_seal_time", "is_limit_up"],
        "daily_or_cutoff",
        "For same-day use include only boards sealed by cutoff; full-day entropy is T+1.",
        "Existing seal-time factors are stock/bucket/average; this is market distribution entropy.",
        "engineerable_if_limit_pool_has_seal_time",
        "bucket definitions should be fixed before training",
    ),
    factor(
        430,
        "reversal_board_quality_score",
        "limit_board",
        "P1",
        ["omnibus_addendum3", "weak_to_strong_tgb_2"],
        [],
        "A reversal board is stronger when prior weakness is repaired with volume and seal quality.",
        "prior_weakness_score * intraday_reclaim_strength * seal_quality_score",
        "daily OHLCV, 1min bars, limit_pool seal/open-board fields",
        ["trade_date", "ts_code", "ret_1d", "open", "close", "vwap", "seal_amount", "open_times"],
        "daily_or_1min",
        "Use only 1min/limit events up to cutoff for live replay; after-close fields are T+1.",
        "C148 detects ground-sky and C382 is generic reversal-with-volume; this is reversal-board quality with seal context.",
        "needs_formula_lock",
        "formula weights must be locked before training",
    ),
    factor(
        431,
        "cb_stock_limit_up_premium_spread",
        "convertible_bond",
        "P2",
        ["omnibus_addendum3", "convertible_sina"],
        ["RAW000476"],
        "After the underlying stock limit-up, convertible premium behavior may reveal cross-asset disagreement.",
        "conversion_premium_rate_cb - median(conversion_premium_rate of comparable CBs) conditional on underlying limit-up",
        "cb_daily, cb_basic stock mapping, conversion premium, underlying limit_pool",
        ["trade_date", "ts_code", "cb_code", "conversion_premium_rate", "is_underlying_limit_up"],
        "daily",
        "Convertible daily data is normally after-close; use for T+1 unless intraday CB quote timestamps exist.",
        "C421 is equity-linkage premium gap for all CB-linked stocks; this is specifically after underlying limit-up.",
        "needs_cb_daily_and_limit_pool_join",
        "P2 until CB coverage and mapping are confirmed",
    ),
    factor(
        432,
        "has_convertible_bond_leader_drag",
        "convertible_bond",
        "P2",
        ["omnibus_addendum3", "raw_pool_index"],
        ["RAW000099", "RAW000309"],
        "Some short-line traders discount leader purity when a stock has a linked convertible or external anchor.",
        "I(stock has active convertible bond) * current_theme_or_leader_strength",
        "active convertible-stock mapping and theme/leader score",
        ["trade_date", "ts_code", "cb_code", "is_active_cb", "leader_strength"],
        "daily",
        "Convertible mapping is known before trade; theme/leader score must be cutoff-bounded.",
        "C420/C421 are CB valuation/trigger factors; this is a binary leader-purity interaction.",
        "needs_cb_active_mapping",
        "direction should be learned; do not hard-code as negative",
    ),
    factor(
        433,
        "intraday_theme_reflow_score",
        "theme_intraday",
        "P1",
        ["omnibus_addendum3", "weak_to_strong_tgb_2"],
        ["RAW001204"],
        "Theme reflow is stronger when a batch of peers returns together, not when only one stock rebounds.",
        "mean(peer_return_since_intraday_low) * peer_positive_share * leader_reclaim_flag",
        "theme membership, 1min bars, leader identity or board_count",
        ["trade_date", "ts_code", "theme_id", "bar_time", "close", "intraday_low", "board_count"],
        "1min",
        "Use only minute bars <= cutoff and theme labels known by cutoff.",
        "C396 is first-divergence repair; this measures broader intraday theme reflow breadth and magnitude.",
        "needs_theme_minute_matrix",
        "P1 once theme labels are stable",
    ),
    factor(
        434,
        "follower_position_confirmation",
        "limit_theme",
        "P1",
        ["omnibus_addendum3", "weak_to_strong_tgb_2"],
        ["RAW001194", "RAW001197"],
        "Leader strength is more reliable when followers recover and confirm the same theme.",
        "count(theme_followers with ret_to_cutoff > threshold or board_count_progress) / theme_member_count",
        "theme membership, leader/follower tag, intraday/daily returns, limit_pool",
        ["trade_date", "ts_code", "theme_id", "is_leader", "ret_to_cutoff", "board_count"],
        "daily_or_1min",
        "Use cutoff-bounded returns and limit events for same-day replay; full-day version is T+1.",
        "C399 measures sector independence ex-leader; this measures follower confirmation with the leader included as anchor.",
        "needs_theme_leader_follower_labels",
        "formula threshold must be locked",
    ),
    factor(
        435,
        "tail20_amount_concentration",
        "minute_amount_shape",
        "P1",
        ["omnibus_addendum3", "hf_bigquant"],
        [],
        "Tail-session amount concentration can identify late-day capital commitment or exit pressure.",
        "sum(amount in last 20 minutes up to cutoff) / (sum(amount up to cutoff) + eps)",
        "1min bars amount",
        ["trade_date", "ts_code", "bar_time", "amount"],
        "1min",
        "Use only bars <= cutoff; at 14:57 use observed tail window within available bars, not post-cutoff bars.",
        "C284 is open-vs-close volume imbalance; C354 is cumulative-curve surprise. This is tail amount share.",
        "engineerable_after_1min_cache",
        "window length can be 20 minutes or cutoff-relative locked variant",
    ),
    factor(
        436,
        "minute_volume_path_roughness",
        "minute_volume_shape",
        "P1",
        ["omnibus_addendum3", "hf_bigquant"],
        [],
        "Rough volume paths capture fragmented or unstable intraday participation.",
        "mean(abs(diff(minute_volume))) / (mean(minute_volume) + eps)",
        "1min bars volume",
        ["trade_date", "ts_code", "bar_time", "volume"],
        "1min",
        "Use only bars <= cutoff.",
        "C384 is amount autocorrelation and C385 is tail kurtosis; this is absolute path roughness.",
        "engineerable_after_1min_cache",
        "winsorize extremely low-volume stocks",
    ),
    factor(
        437,
        "volume_peak_count_factor",
        "minute_volume_peak",
        "P1",
        ["omnibus_addendum3", "hf_bigquant"],
        [],
        "The count of local volume peaks distinguishes smooth accumulation from repeated bursts.",
        "count(local_maxima(volume_t) where volume_t > rolling_intraday_median * threshold)",
        "1min bars volume",
        ["trade_date", "ts_code", "bar_time", "volume"],
        "1min",
        "Use only peaks observable by cutoff; do not use future bars to confirm a peak in live mode.",
        "C377-C380 use peak contribution/persistence/spread; this is a simple peak count.",
        "engineerable_after_1min_cache",
        "peak confirmation must be one-sided for 14:57 replay",
    ),
    factor(
        438,
        "realized_volatility_peak_cluster_count",
        "minute_volatility_shape",
        "P1",
        ["omnibus_addendum3", "hf_bigquant"],
        [],
        "Clustered volatility peaks indicate unstable intraday price discovery.",
        "count(clusters where abs(minute_return) zscore > threshold) up to cutoff",
        "1min close/returns",
        ["trade_date", "ts_code", "bar_time", "close"],
        "1min",
        "Use only returns up to cutoff.",
        "C136/C360 measure volatility level/ratio; this counts volatility peak clusters.",
        "engineerable_after_1min_cache",
        "threshold and cluster gap should be locked",
    ),
    factor(
        439,
        "local_reversal_by_volume_bucket",
        "minute_reversal",
        "P1",
        ["omnibus_addendum3", "hf_bigquant"],
        [],
        "Short-horizon reversal may differ between high-volume and low-volume intraday buckets.",
        "corr_or_slope(return_t, -return_t_minus_1) computed separately in high-volume buckets minus low-volume buckets",
        "1min returns and volume bucket labels",
        ["trade_date", "ts_code", "bar_time", "close", "volume"],
        "1min",
        "Use only minute observations <= cutoff.",
        "C371-C373 are price-volume correlations; this is reversal conditioned on volume buckets.",
        "engineerable_after_1min_cache",
        "requires enough bars before cutoff",
    ),
    factor(
        440,
        "micro_partition_volatility_spread",
        "minute_volatility_shape",
        "P1",
        ["omnibus_addendum3", "hf_bigquant"],
        [],
        "Volatility in high-volume partitions versus low-volume partitions captures microstructure heterogeneity.",
        "realized_volatility(high_volume_minutes) - realized_volatility(low_volume_minutes)",
        "1min returns and volume partition labels",
        ["trade_date", "ts_code", "bar_time", "close", "volume"],
        "1min",
        "Use only bars <= cutoff; partitions must be defined using observed bars only.",
        "C410 in prior omnibus was raw-only; no C001-C425 registry candidate covers this exact spread.",
        "engineerable_after_1min_cache",
        "partition quantiles should be locked",
    ),
    factor(
        441,
        "high_low_price_bucket_momentum",
        "minute_price_bucket",
        "P1",
        ["omnibus_addendum3", "hf_bigquant"],
        [],
        "Momentum may differ when the intraday path is trading near high-price versus low-price zones.",
        "mean(return in high intraday price percentile buckets) - mean(return in low intraday price percentile buckets)",
        "1min close/returns",
        ["trade_date", "ts_code", "bar_time", "close"],
        "1min",
        "Use only observed intraday high/low percentiles up to cutoff.",
        "C371-C373 use price-volume correlation; this is price-zone conditioned momentum.",
        "engineerable_after_1min_cache",
        "avoid using full-day high/low in live mode",
    ),
    factor(
        442,
        "high_low_volume_bucket_reversal",
        "minute_volume_bucket",
        "P1",
        ["omnibus_addendum3", "hf_bigquant"],
        [],
        "High-volume versus low-volume buckets can have different reversal behavior.",
        "reversal_slope(high_volume_bucket) - reversal_slope(low_volume_bucket)",
        "1min close/returns and volume",
        ["trade_date", "ts_code", "bar_time", "close", "volume"],
        "1min",
        "Use only bars <= cutoff.",
        "C439 is local reversal by volume bucket using prior-return relation; C442 is bucket-level reversal spread aggregate.",
        "engineerable_after_1min_cache",
        "may be merged with C439 after implementation if identical",
    ),
    factor(
        443,
        "amount_distribution_asymmetry",
        "minute_amount_shape",
        "P1",
        ["omnibus_addendum3", "hf_bigquant"],
        [],
        "Asymmetry of amount distribution across the session captures front-loaded or tail-loaded capital pressure.",
        "skewness(time_weighted amount distribution up to cutoff)",
        "1min amount",
        ["trade_date", "ts_code", "bar_time", "amount"],
        "1min",
        "Use only bars <= cutoff and normalize by expected intraday curve.",
        "C435 is tail share; this is full-path amount distribution skewness.",
        "engineerable_after_1min_cache",
        "normalize for standard U-shaped intraday volume curve",
    ),
    factor(
        444,
        "dragon_list_reason_type_score",
        "lhb_reason",
        "P1",
        ["omnibus_addendum3"],
        [],
        "LHB reason type can separate first-board, abnormal turnover, and institution-driven events.",
        "score(reason_type) or one-hot reason_type from top_list/dragon list event reason",
        "top_list/LHB reason text, parsed reason categories, stock-date event",
        ["trade_date", "ts_code", "lhb_reason", "reason_type"],
        "after_close_daily",
        "LHB reason is after-close; use for next trading day only.",
        "C412-C414 use seat behavior; this uses LHB event reason classification.",
        "needs_lhb_reason_parser",
        "reason taxonomy must be versioned",
    ),
    factor(
        445,
        "dragon_list_historical_reason_premium",
        "lhb_reason",
        "P1",
        ["omnibus_addendum3"],
        [],
        "Historical premiums differ by LHB reason type and market regime.",
        "mean(forward_return_1d of past events with same reason_type and regime, using only events before T)",
        "top_list/LHB reason type, historical forward returns, market regime labels",
        ["trade_date", "ts_code", "reason_type", "historical_forward_return_1d", "market_regime"],
        "after_close_daily",
        "Use only historical events strictly before the current event date; current LHB reason is T+1.",
        "C363 is seat alpha history; this is reason-type historical premium.",
        "needs_lhb_reason_history_cache",
        "must enforce expanding-window history to avoid leakage",
    ),
    factor(
        446,
        "guba_attention_surge_score",
        "social_attention",
        "P2",
        ["raw_pool_index", "guba_sentiment_bigquant", "guba_crash_risk_cnki"],
        ["RAW002914", "RAW002979"],
        "Stock-bar post volume surges proxy retail attention and discussion heat.",
        "(post_count_t - rolling_mean(post_count,20)) / (rolling_std(post_count,20) + eps)",
        "timestamped Guba/Eastmoney post count by stock",
        ["event_time", "trade_date", "ts_code", "post_count"],
        "event_or_daily",
        "For same-day use include only posts before cutoff; otherwise T+1.",
        "C365 uses sentiment-overtrading gap and C405 cross-platform consensus; this is pure stock-bar attention surge.",
        "needs_timestamped_guba_pipeline",
        "P2 until crawler coverage and symbol mapping are stable",
    ),
    factor(
        447,
        "baidu_search_attention_surge",
        "search_attention",
        "P2",
        ["raw_pool_index", "media_sentiment_attention"],
        ["RAW002428", "RAW002429", "RAW002916", "RAW002917", "RAW002980"],
        "Baidu search volume index can proxy investor attention outside trading apps.",
        "log((search_index_t + 1) / (search_index_t_minus_5 + 1))",
        "Baidu search index by stock name/code and timestamp/date",
        ["trade_date", "ts_code", "search_index"],
        "daily",
        "If search index timestamp is daily after close, use T+1; same-day use requires timestamped intraday search data.",
        "No existing registry candidate explicitly uses Baidu search attention.",
        "needs_baidu_index_pipeline",
        "P2 because access and symbol-name ambiguity must be audited",
    ),
    factor(
        448,
        "retail_fomo_moneyflow_limit_interaction",
        "retail_behavior",
        "P1",
        ["factor_data_availability_audit", "raw_pool_index"],
        ["RAW000065"],
        "Retail FOMO is strongest when small-order moneyflow, turnover, and limit-up pressure align.",
        "rank(small_order_net_flow_ratio) * rank(turnover_rate) * I(limit_up_attempt_or_high_return)",
        "moneyflow small-order fields, turnover, daily/limit_pool state",
        ["trade_date", "ts_code", "small_order_net_flow", "amount", "turnover_rate", "is_limit_up_attempt"],
        "daily_or_cutoff",
        "Use only moneyflow/limit fields available by cutoff; after-close moneyflow is T+1.",
        "C365 is social sentiment overtrading; this is transaction-based retail FOMO.",
        "needs_moneyflow_limit_join",
        "direction should be learned by training",
    ),
    factor(
        449,
        "disposition_effect_pressure_proxy",
        "retail_behavior",
        "P2",
        ["factor_data_availability_audit"],
        [],
        "Profit-taking by recent winners can create disposition-effect pressure.",
        "profit_holder_proxy * small_order_sell_pressure * max(ret_5d, 0)",
        "daily returns, chip/cost proxy or turnover-cost model, small-order moneyflow sell pressure",
        ["trade_date", "ts_code", "ret_5d", "winner_rate", "small_order_sell_amount"],
        "daily",
        "Use T close/cost/moneyflow for next-day prediction unless intraday small-order flow is timestamped.",
        "No C001-C425 candidate explicitly combines profit-holder proxy with retail sell pressure.",
        "needs_chip_or_cost_and_small_order_sell_fields",
        "P2 due to cost/winner proxy dependency",
    ),
    factor(
        450,
        "convertible_clause_game_score",
        "convertible_bond",
        "P2",
        ["raw_pool_index", "convertible_force_redemption_pdf", "convertible_sina"],
        ["RAW001169"],
        "Convertible bond clauses such as forced redemption, putback, and downward revision can affect linked equity behavior.",
        "weighted_score(force_redemption_progress, putback_window, downward_revision_probability_proxy)",
        "cb_basic clause fields, conversion price history, stock close, issuer status",
        ["trade_date", "ts_code", "cb_code", "conversion_price", "force_redemption_progress", "putback_window"],
        "daily",
        "Use clause data known by date; do not use future issuer decisions or future conversion-price revisions.",
        "C420 isolates forced-redemption pressure; this combines multiple clause-game dimensions.",
        "needs_cb_clause_fields",
        "P2 until clause fields are audited",
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
        "## Saturation Pass 2 2026-05-18",
        "",
        "Purpose: second all-channel saturation pass over local raw pool, broker/paper/web sources, TGB/Xueqiu/Bilibili search surfaces, social/search attention, and newly available data directions. Registry only: no training, no gpu_probe, no model/frozen config changes.",
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
            "- C426-C430 use limit/auction/1min/board data and can be cutoff-bounded if source timestamps exist.",
            "- C431-C432 and C450 are convertible-bond candidates; most practical usage is T+1 unless intraday CB data is timestamped.",
            "- C433-C434 require stable theme and leader/follower labels.",
            "- C435-C443 require 1min cache and one-sided live calculations.",
            "- C444-C445 are LHB reason candidates and are after-close/T+1 only.",
            "- C446-C447 require timestamped social/search pipelines; C448-C449 need moneyflow/chip or cost fields.",
        ]
    )
    with HUMAN_REGISTRY_PATH.open("a", encoding="utf-8") as f:
        f.write("\n".join(section) + "\n")


def write_report(validation: dict) -> None:
    lines = [
        "# Saturation Pass 2 Factor Search 2026-05-18",
        "",
        "Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.",
        "",
        "## Search Surface",
        "",
        "- Local raw pool: remaining no-match/ready candidates, especially limit-board, theme, minute-HF, LHB reason, Guba/Baidu, and convertible clauses.",
        "- Social/TGB/Xueqiu/Bilibili/Douyin surfaces: weak-to-strong, auction expectation, follower confirmation, theme reflow, leader/board ceiling rules.",
        "- Broker/research surfaces: high-frequency minute price-volume templates, text sentiment, convertible clauses and premium behavior.",
        "- Data feasibility: no true L2/tick/orderbook factors were registered; these remain blocked until data exists.",
        "",
        "## Result",
        "",
        f"- Added candidates: {len(DETAIL)} ({DETAIL[0]['factor_id']} to {DETAIL[-1]['factor_id']})",
        f"- Priority counts: {dict(Counter(row['priority'] for row in DETAIL))}",
        f"- Family counts: {dict(Counter(row['family'] for row in DETAIL))}",
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
            "- L2/orderbook factors such as bid-ask depth imbalance, cancellation pressure, hidden order detection, and true OFI remain blocked.",
            "- Pure trading slogans and discretionary exit/position rules were not registered.",
            "- Direct aliases of existing features, generic moving-average formulas, and raw `current_price = close` patterns were rejected.",
            "- Untimestamped short-video/social heat was not promoted to same-day trainable factors.",
            "",
            "## Ten Checks",
            "",
        ]
    )
    for i, check in enumerate(
        [
            "C001-C425 duplicate name screen",
            "C001-C425 duplicate formula screen",
            "local raw pool ready/no-match review",
            "TGB/Xueqiu weak-to-strong and auction rule review",
            "Bilibili/Douyin social-surface review with timestamp gate",
            "broker high-frequency minute template review",
            "Guba/Baidu/news attention source review",
            "convertible-bond clause and premium source review",
            "asof/leakage classification: cutoff vs T close vs T+1",
            "post-write registry integrity validation",
        ],
        1,
    ):
        lines.append(f"{i}. {check}")
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
        "search_round": "saturation_pass2",
        "purpose": "second all-channel saturation pass for short-line factor library",
        "scope": "factor-library only; no training; no gpu_probe; no model/frozen config changes",
        "source_evidence": SOURCES,
        "selection_gate": [
            "explicit computable scalar definition",
            "named data need and required columns",
            "asof rule and leakage boundary",
            "non-duplicate against C001-C425",
            "training_status remains not_trained",
            "lockbox_role remains research_candidate",
        ],
        "total": len(DETAIL),
        "by_priority": dict(Counter(row["priority"] for row in DETAIL)),
        "by_family": dict(Counter(row["family"] for row in DETAIL)),
        "detail": DETAIL,
        "deferred_or_rejected": [
            {
                "bucket": "true_l2_tick_orderbook",
                "reason": "Needs stable L2/tick orderbook or trade direction fields. Keep blocked until data exists.",
            },
            {
                "bucket": "pure_social_video_text",
                "reason": "Needs timestamped symbol/theme extraction before same-day or trainable usage.",
            },
            {
                "bucket": "generic_ta_formulas",
                "reason": "Already covered by technical-factor-bank candidates unless distinct short-line context exists.",
            },
        ],
    }

    meta = data.setdefault("meta", {})
    batches = meta.setdefault("candidate_batches", [])
    if BATCH not in batches:
        batches.append(BATCH)
    meta["updated"] = TODAY
    meta["latest_candidate_batch"] = BATCH
    meta["saturation_pass2_20260518"] = {
        "added_count": len(DETAIL),
        "id_range": [DETAIL[0]["factor_id"], DETAIL[-1]["factor_id"]],
        "priority_counts": dict(Counter(row["priority"] for row in DETAIL)),
        "family_counts": dict(Counter(row["family"] for row in DETAIL)),
        "cutoff_capable_if_timestamped": [
            "C426",
            "C427",
            "C429",
            "C430",
            "C433",
            "C434",
            "C435",
            "C436",
            "C437",
            "C438",
            "C439",
            "C440",
            "C441",
            "C442",
            "C443",
        ],
        "t_plus_1_only_or_pipeline_gated": ["C428", "C431", "C432", "C444", "C445", "C446", "C447", "C448", "C449", "C450"],
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
