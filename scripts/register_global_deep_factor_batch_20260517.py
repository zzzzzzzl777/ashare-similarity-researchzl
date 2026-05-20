from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


BATCH = "candidates_20260517_global_deep_search"
DATE = "2026-05-17"
ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
REGISTRY_PATH = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
REPORT_PATH = ROOT / "docs" / "global_deep_factor_search_20260517.md"
MD_REGISTRY_PATH = ROOT / "docs" / "factor_registry.md"


SOURCE_MAP = {
    "haitong_hf": "Haitong high-frequency factor reports: minute skew, downside volatility share, tail volume share, price-volume correlation, improved reversal and large-order push logic.",
    "citic_hf": "CITIC high-frequency price-volume report: VOI/OIR/MPB families; only low-frequency/minute-bar-safe proxies are admitted here.",
    "qlib": "Microsoft Qlib Alpha158/Alpha360 feature handler family, rewritten into explicit cutoff-safe formulas.",
    "worldquant": "101 Formulaic Alphas family, only simple OHLCV/VWAP formulas with explicit asof controls are admitted.",
    "academic_intraday": "Academic intraday momentum/order-imbalance literature; converted to minute-bar features only when L2 is not required.",
    "local_canonical": "Local canonical registry audit and O001-O450 queue, deduped against C001-C292.",
    "local_raw": "Local raw factor pool residual audit, deduped against formal registry and O queue.",
    "data_unlocked": "Tushare proxy sources already audited locally: stk_mins_1, stk_mins_5, top_list, block_trade, share_float, forecast_vip, stk_surv, hsgt_top10, ccass_hold and industry moneyflow caches.",
}


def candidate(
    name: str,
    family: str,
    priority: str,
    source_refs: list[str],
    data_need: str,
    definition: str,
    asof_rule: str,
    duplicate_check: str,
    engineering_status: str,
    data_status: str,
    required_columns: list[str] | None = None,
    frequency: str | None = None,
    depends_on: list[str] | None = None,
    notes: str = "",
) -> dict:
    return {
        "name": name,
        "family": family,
        "priority": priority,
        "source_type": "global_deep_search_20260517",
        "source_refs": source_refs,
        "data_need": data_need,
        "required_columns": required_columns or [],
        "frequency": frequency or "",
        "computable_definition": definition,
        "asof_rule": asof_rule,
        "leakage_risk": "none if asof_rule is enforced; otherwise treat as research-only",
        "duplicate_check": duplicate_check,
        "engineering_status": engineering_status,
        "data_status": data_status,
        "training_status": "not_trained",
        "lockbox_role": "research_candidate",
        "batch": BATCH,
        "depends_on": depends_on or [],
        "notes": notes,
        "audit_20260517": {
            "status": "audited",
            "checks": [
                "explicit_formula",
                "data_need_named",
                "asof_rule_named",
                "not_exact_duplicate",
                "not_training_result_claim",
            ],
        },
    }


MINUTE_ASOF = "For 14:57 live use only 1min bars with bar_time <= 14:57; for post-close research use T+1 full-day bars."
LIMIT_ASOF = "Use only limit/board events timestamped <= 14:57; if event time is not available, shift to T-1."
DELAYED_ASOF = "Use T-1 or announcement/publication timestamp <= 14:57 only; same-day post-close records are forbidden for live 14:57."
DAILY_ASOF = "For live 14:57 use T-1 daily fields or explicitly built 14:57 proxy OHLCV; never use T-day final close/amount unless the task is post-close research."


CANDIDATES = [
    candidate(
        "hf_downside_volatility_share",
        "minute_hf",
        "P0",
        ["haitong_hf", "local_canonical:realized_skew_kurtosis_combo"],
        "1min bars",
        "sum(r_i^2 for minute returns r_i < 0) / (sum(r_i^2) + eps), optionally averaged over trailing N sessions",
        MINUTE_ASOF,
        "Distinct from C136/C174/C189: measures downside share of realized variance, not total volatility or bar-frequency ratio.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close"],
        "1min",
    ),
    candidate(
        "hf_realized_skewness_20d",
        "minute_hf",
        "P1",
        ["haitong_hf", "local_canonical:realized_skew_kurtosis_combo"],
        "1min bars",
        "mean_over_N_days( sum(r_i^3) / (sum(r_i^2) ** 1.5 + eps) )",
        MINUTE_ASOF,
        "Distinct from C283 periodicity and C293 downside share; captures asymmetric intraday return distribution.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close"],
        "1min",
    ),
    candidate(
        "hf_realized_kurtosis_20d",
        "minute_hf",
        "P2",
        ["haitong_hf", "local_canonical:realized_skew_kurtosis_combo"],
        "1min bars",
        "mean_over_N_days( sum(r_i^4) / (sum(r_i^2) ** 2 + eps) )",
        MINUTE_ASOF,
        "Complements C294 skewness; screens intraday tail concentration rather than direction.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close"],
        "1min",
    ),
    candidate(
        "tail_volume_share_1457",
        "minute_hf",
        "P0",
        ["haitong_hf", "local_canonical:tail_session_impact_resilience"],
        "1min bars",
        "sum(volume_i for i in 14:30-14:57) / (sum(volume_i for i <= 14:57) + eps)",
        MINUTE_ASOF,
        "Distinct from C284 opening_closing_volume_imbalance: uses live-safe tail share, not open-minus-close imbalance.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["volume"],
        "1min",
    ),
    candidate(
        "intraday_price_volume_corr",
        "minute_hf",
        "P0",
        ["haitong_hf", "local_canonical:minute_pv_corr_segmented"],
        "1min bars",
        "corr(close_i, volume_i / (sum(volume_i) + eps)) over bars <= cutoff; optional trailing N-day mean",
        MINUTE_ASOF,
        "Distinct from C285 impact ratio and C278 WQ correlation; this is direct intraday CPV/price-volume correlation.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close", "volume"],
        "1min",
    ),
    candidate(
        "intraday_pv_corr_segment_shift",
        "minute_hf",
        "P1",
        ["haitong_hf", "local_canonical:minute_pv_corr_segmented"],
        "1min bars",
        "corr_open_0930_1030(close, volume_share) - corr_tail_1400_1457(close, volume_share)",
        MINUTE_ASOF,
        "Segment-shift version of C297; not an exact duplicate because it measures open-vs-tail regime change.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close", "volume"],
        "1min",
    ),
    candidate(
        "improved_intraday_reversal_1000_to_1457",
        "minute_hf",
        "P0",
        ["haitong_hf", "local_canonical:intraday_trend_strength"],
        "1min bars",
        "(price_1457 / price_1000 - 1) with sign optionally reversed by validation; use trailing N-day smoothed value",
        MINUTE_ASOF,
        "Rewrites sell-side improved-reversal to 14:57; distinct from C227 daily pullback and C279 daily sign-volume-return.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close"],
        "1min",
    ),
    candidate(
        "large_amount_bar_push_return",
        "minute_hf",
        "P0",
        ["haitong_hf", "local_canonical:volume_surge_moment_bright_return"],
        "1min bars",
        "prod(1 + r_i for bars where amount_i is in top 30pct of intraday amount bars) - 1",
        MINUTE_ASOF,
        "Minute-bar proxy of large-order push; avoids true L2 order-size requirement and differs from C248 attack volume at limit.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close", "amount"],
        "1min",
    ),
    candidate(
        "high_price_volume_share",
        "minute_hf",
        "P0",
        ["haitong_hf", "local_canonical:high_position_volume_event_ratio"],
        "1min bars",
        "sum(volume_i where close_i is in top 20pct of intraday price range) / (sum(volume_i) + eps)",
        MINUTE_ASOF,
        "Distinct from C006/O006 high-volatility price-position ideas and C277 trapped value; uses high-price-zone volume share.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close", "high", "low", "volume"],
        "1min",
    ),
    candidate(
        "low_price_absorption_repair",
        "minute_hf",
        "P1",
        ["haitong_hf", "local_canonical:minute_downside_absorption"],
        "1min bars",
        "low_zone_volume_share * max((price_1457 - low_zone_vwap) / (low_zone_vwap + eps), 0)",
        MINUTE_ASOF,
        "Overlap watch with C277 trapped_value_weighted; kept because it requires later repair, not just trapped cost.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close", "low", "volume", "amount"],
        "1min",
    ),
    candidate(
        "same_clock_return_surprise_z",
        "minute_hf",
        "P0",
        ["academic_intraday", "local_canonical:same_clock_return_reversal"],
        "1min bars + trailing same-clock history",
        "(cum_return_to_cutoff - mean_same_clock_return_Nd) / (std_same_clock_return_Nd + eps)",
        MINUTE_ASOF,
        "Distinct from C255 dynamic volume comparison; same-clock return surprise, not volume surprise.",
        "engineerable_after_1min_cache_and_history",
        "stk_mins_1_available_needs_history_matrix",
        ["close"],
        "1min",
    ),
    candidate(
        "intraday_trend_smoothness",
        "minute_hf",
        "P1",
        ["academic_intraday", "local_canonical:intraday_trend_smoothness"],
        "1min bars",
        "abs(price_cutoff / open - 1) / (sum(abs(r_i for i <= cutoff)) + eps)",
        MINUTE_ASOF,
        "Distinct from C300 improved reversal because it measures path smoothness/choppiness.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["open", "close"],
        "1min",
    ),
    candidate(
        "shock_volume_decay_half_life",
        "minute_hf",
        "P0",
        ["academic_intraday", "local_canonical:shock_volume_decay_half_life"],
        "1min bars",
        "after largest positive volume_z shock before cutoff, fit log(volume_z) decay and record half-life in minutes",
        MINUTE_ASOF,
        "Distinct from C192/C255 volume acceleration; event-conditioned decay after the largest shock.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_event_parser",
        ["volume"],
        "1min",
    ),
    candidate(
        "shock_price_reversal_efficiency",
        "minute_hf",
        "P0",
        ["academic_intraday", "local_canonical:shock_price_reversal_efficiency"],
        "1min bars",
        "post_shock_opposite_return_Nmin / (abs(shock_return) + eps) after the largest minute return shock before cutoff",
        MINUTE_ASOF,
        "Distinct from C183/C300 because it is shock-window conditioned rather than full-session reversal.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_event_parser",
        ["close"],
        "1min",
    ),
    candidate(
        "intraday_market_beta_20d",
        "minute_hf",
        "P1",
        ["academic_intraday", "local_canonical:rolling_rank_volume_price_residual"],
        "1min stock bars + index/all-stock minute return",
        "rolling_20d beta from stock minute returns to market minute returns, computed using bars <= cutoff",
        MINUTE_ASOF,
        "New systematic intraday exposure; distinct from C251 active rally against market which is event-window alpha.",
        "engineerable_after_1min_and_market_minute_cache",
        "needs_market_minute_return_matrix",
        ["close"],
        "1min",
    ),
    candidate(
        "intraday_idio_vol_share",
        "minute_hf",
        "P1",
        ["academic_intraday", "local_canonical:micro_partition_volatility_spread"],
        "1min stock bars + index/all-stock minute return",
        "var(residual_i from intraday_market_beta regression) / (var(stock_minute_returns) + eps)",
        MINUTE_ASOF,
        "Depends on C307-style beta but measures residual risk share.",
        "engineerable_after_1min_and_market_minute_cache",
        "needs_market_minute_return_matrix",
        ["close"],
        "1min",
        ["intraday_market_beta_20d"],
    ),
    candidate(
        "minute_market_breadth_thrust",
        "minute_market",
        "P0",
        ["local_canonical:minute_market_breadth_thrust", "academic_intraday"],
        "1min all-stock bars",
        "share_of_universe(cum_return_to_cutoff > same_clock_return_z_threshold) or breadth acceleration over last K minutes",
        MINUTE_ASOF,
        "Minute-live market-wide breadth signal; distinct from C089 daily market_breadth_thrust, C225 emotion score and C224 theme breadth.",
        "engineerable_after_1min_universe_cache",
        "needs_all_stock_1min_matrix",
        ["close"],
        "1min",
    ),
    candidate(
        "cross_sectional_minute_momentum_rank",
        "minute_market",
        "P0",
        ["local_canonical:cross_sectional_minute_momentum_rank", "academic_intraday"],
        "1min all-stock bars",
        "rank(cum_return_to_cutoff) within tradable universe at cutoff",
        MINUTE_ASOF,
        "Live-safe intraday cross-sectional momentum rank; distinct from daily cs_ret_1_rank if built from 1min cutoff return.",
        "engineerable_after_1min_universe_cache",
        "needs_all_stock_1min_matrix",
        ["close"],
        "1min",
    ),
    candidate(
        "first5_vwap_hold_ratio",
        "minute_hf",
        "P0",
        ["local_canonical:first5_vwap_hold_ratio"],
        "1min bars",
        "count(minutes after 09:35 with close_i >= first5_vwap) / count(minutes after 09:35 up to cutoff)",
        MINUTE_ASOF,
        "Distinct from C190 first_5min_strength: this checks whether early VWAP is defended later.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close", "volume", "amount"],
        "1min",
    ),
    candidate(
        "minute_opening_range_breakout_quality",
        "minute_hf",
        "P0",
        ["local_canonical:minute_opening_range_breakout_quality"],
        "1min bars",
        "I(price_breaks_first30_high_before_cutoff) * breakout_return / (drawdown_after_breakout + eps)",
        MINUTE_ASOF,
        "Intraday opening-range breakout quality; distinct from C228 daily new-high/low sign.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_event_parser",
        ["high", "low", "close"],
        "1min",
    ),
    candidate(
        "vwap_reclaim_count",
        "minute_hf",
        "P1",
        ["local_canonical:close_to_vwap_reclaim_count"],
        "1min bars",
        "count of transitions from close_i < session_vwap_i to close_i >= session_vwap_i before cutoff",
        MINUTE_ASOF,
        "Distinct from C048 vwap_reclaim_strength and C311 first5_vwap_hold_ratio; counts repeated reclaim events rather than one strength scalar.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_vwap_calc",
        ["close", "volume", "amount"],
        "1min",
    ),
    candidate(
        "shortest_path_illiquidity_intraday",
        "minute_hf",
        "P0",
        ["local_canonical:shortest_path_illiquidity_intraday"],
        "1min bars",
        "sum(abs(r_i)) / (abs(cum_return_to_cutoff) + eps) * 1/(amount_to_cutoff + eps), higher means choppy illiquid path",
        MINUTE_ASOF,
        "Path illiquidity, not the same as C285 price impact proxy which uses return/amount per window.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["close", "amount"],
        "1min",
    ),
    candidate(
        "intraday_volume_entropy",
        "minute_hf",
        "P1",
        ["local_canonical:minute_turnover_entropy"],
        "1min bars",
        "-sum(p_i * log(p_i)) where p_i = volume_i / sum(volume_i up to cutoff)",
        MINUTE_ASOF,
        "Distinct from C174 volume HHI and C283 periodicity: entropy of volume distribution.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_full_cache_gate",
        ["volume"],
        "1min",
    ),
    candidate(
        "late_breakout_fail_probability",
        "minute_hf",
        "P1",
        ["local_canonical:late_breakout_fail_probability"],
        "1min bars",
        "I(breakout_after_14:00) * max(breakout_price - price_1457, 0) / (breakout_price + eps)",
        MINUTE_ASOF,
        "Distinct from C257 late_weak_rally_failure by explicitly requiring late breakout above prior intraday high.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_event_parser",
        ["high", "close"],
        "1min",
    ),
    candidate(
        "weak_to_strong_open_reclaim",
        "auction_open",
        "P0",
        ["local_canonical:weak_to_strong_open_reclaim"],
        "1min bars + previous board/weakness tag",
        "I(open_gap_or_first5_return < 0) * I(price_reclaims_open_or_vwap_before_1030) * volume_confirm_z",
        MINUTE_ASOF,
        "Classic short-line weak-to-strong intraday pattern; overlap watch C029, but this locks a minute-bar reclaim formula without auction/theme terms.",
        "engineerable_after_1min_and_prev_state_tag",
        "needs_prev_board_or_weakness_tag",
        ["open", "close", "volume", "amount"],
        "1min",
    ),
    candidate(
        "auction_open_to_first5_reclaim",
        "auction_open",
        "P1",
        ["local_canonical:auction_open_to_first5_reclaim"],
        "auction final + 1min bars",
        "I(auction/open weak) * max(close_09:35 - open_price, 0) / (open_price + eps)",
        "Auction fields known after 09:25 plus 1min bars <=09:35; safe if auction data is a preopen snapshot, not revised post-close.",
        "Distinct from C261 weak_to_strong_auction_confirm; this is a pure open-to-first5 reclaim scalar.",
        "engineerable_after_auction_snapshot_verified",
        "needs_auction_final_asof_verification",
        ["open", "close"],
        "auction+1min",
    ),
    candidate(
        "auction_false_strength_risk",
        "auction_open",
        "P1",
        ["local_canonical:auction_false_strength_risk"],
        "auction final + 1min bars",
        "I(auction_gap_positive and auction_amount_z high) * max(open_price - close_09:35, 0) / (open_price + eps)",
        "Auction fields known after 09:25 plus 1min bars <=09:35; safe if auction data is a preopen snapshot, not revised post-close.",
        "Inverse-risk pair of C318; not a duplicate because it flags strong auction that immediately fails.",
        "engineerable_after_auction_snapshot_verified",
        "needs_auction_final_asof_verification",
        ["open", "close", "amount"],
        "auction+1min",
    ),
    candidate(
        "market_open_board_rate",
        "limit_board",
        "P0",
        ["local_canonical:market_open_board_rate_canonical"],
        "limit pool with open-board/broken-board timestamp",
        "open_board_count_to_cutoff / max(limit_up_touched_count_to_cutoff, 1)",
        LIMIT_ASOF,
        "Market-level broken seal/open-board rate; distinct from C245 single-stock rotten-board duration.",
        "engineerable_if_limit_pool_has_event_time",
        "needs_limit_pool_asof_rewrite",
        ["first_seal_time", "open_board_count"],
        "intraday_limit",
    ),
    candidate(
        "market_limit_attempt_count",
        "limit_board",
        "P0",
        ["local_canonical:market_limit_attempt_count"],
        "limit pool events",
        "count(stocks that touched up_limit before cutoff) excluding ST and one-word boards if configured",
        LIMIT_ASOF,
        "Counts attempts/touches, distinct from C230 max board height and C225 weighted emotion score.",
        "engineerable_if_limit_pool_has_event_time",
        "needs_limit_pool_asof_rewrite",
        ["touch_time", "up_limit"],
        "intraday_limit",
    ),
    candidate(
        "board_height_compression_speed",
        "limit_board",
        "P0",
        ["local_canonical:board_height_compression_speed", "taoguba_shortline"],
        "limit_list_d or limit pool board height history",
        "delta(max_board_height, 1d or 3d) / trailing_max_board_height_Nd",
        LIMIT_ASOF,
        "Market emotion compression speed; distinct from C230 level score.",
        "engineerable_if_limit_pool_history_complete",
        "needs_limit_pool_history",
        ["board_count"],
        "daily_or_intraday_limit",
    ),
    candidate(
        "broken_board_loss_diffusion",
        "limit_board",
        "P0",
        ["local_canonical:broken_board_loss_diffusion", "taoguba_shortline"],
        "broken-board list + returns",
        "mean(next_or_same_cutoff_return of broken-board stocks) - market_return, optionally breadth-weighted",
        LIMIT_ASOF,
        "Market contagion from broken boards; distinct from C291 halt reopen decay and C036/O rotten-board afterglow candidates.",
        "engineerable_if_limit_pool_has_break_status",
        "needs_limit_pool_asof_rewrite",
        ["broken_board_flag", "close"],
        "intraday_limit",
    ),
    candidate(
        "first_board_to_second_board_conversion",
        "limit_board",
        "P0",
        ["local_canonical:first_board_to_second_board_conversion", "taoguba_shortline"],
        "limit_list_d with board_count history",
        "count(prev_day_first_board and today_board_count>=2) / count(prev_day_first_board)",
        DELAYED_ASOF,
        "Short-line board-ladder conversion; distinct from C270 second_board_confirm_leader stock-level leader flag.",
        "engineerable_if_limit_pool_history_complete",
        "needs_limit_pool_history",
        ["board_count"],
        "daily_limit",
    ),
    candidate(
        "high_board_survival_rate_3d",
        "limit_board",
        "P0",
        ["local_canonical:high_board_survival_rate_3d", "taoguba_shortline"],
        "limit_list_d with board_count history",
        "share of stocks with board_count>=N that keep board_count>=N or do not collapse over next observed 1-3 sessions for historical state feature",
        DELAYED_ASOF,
        "Market regime feature; distinct from C230 board height score and C326 first-to-second conversion.",
        "engineerable_if_limit_pool_history_complete",
        "needs_limit_pool_history",
        ["board_count"],
        "daily_limit",
    ),
    candidate(
        "seal_rate_collapse_3d",
        "limit_board",
        "P0",
        ["local_canonical:seal_rate_collapse_3d", "taoguba_shortline"],
        "limit pool with seal/break status",
        "seal_success_rate_today_or_cutoff - rolling_mean(seal_success_rate, 3d)",
        LIMIT_ASOF,
        "Collapse in market seal success; distinct from C231 average seal time.",
        "engineerable_if_limit_pool_has_break_status",
        "needs_limit_pool_asof_rewrite",
        ["seal_success", "break_count"],
        "intraday_limit",
    ),
    candidate(
        "seal_money_to_float_mv",
        "limit_board",
        "P1",
        ["local_canonical:seal_money_to_float_mv"],
        "limit pool seal amount + share_float",
        "seal_amount_at_cutoff / (free_share * price_at_cutoff + eps)",
        LIMIT_ASOF,
        "Float-normalized seal strength; distinct from C252 board volume acceptance and C246 reseal strength.",
        "engineerable_if_limit_pool_has_seal_amount",
        "needs_limit_pool_seal_amount_and_share_float",
        ["seal_amount", "free_share", "close"],
        "intraday_limit",
    ),
    candidate(
        "lhb_net_buy_to_float",
        "lhb",
        "P0",
        ["local_canonical:lhb_net_buy_vs_float", "data_unlocked"],
        "top_list/top_inst + share_float",
        "lhb_net_buy_amount / (free_share * close + eps) for listed stocks; otherwise missing with availability flag",
        DELAYED_ASOF,
        "Distinct from C229 dragon_tiger_net_buy_ratio which scales by daily amount.",
        "engineerable_after_lhb_backfill",
        "top_list_cached_needs_asof_join",
        ["net_buy", "free_share", "close"],
        "daily_event",
    ),
    candidate(
        "block_trade_discount_persistence_5d",
        "block_trade",
        "P0",
        ["data_unlocked", "local_canonical:block_trade_followthrough_after_limit"],
        "block_trade + daily close",
        "rolling_5d amount-weighted mean((block_price / close_ref) - 1)",
        DELAYED_ASOF,
        "Distinct from C198 one-day block trade discount intensity; this measures persistence.",
        "engineerable_after_block_trade_backfill",
        "block_trade_cached_needs_asof_join",
        ["price", "vol", "amount", "close"],
        "daily_event",
    ),
    candidate(
        "block_trade_seller_concentration",
        "block_trade",
        "P1",
        ["data_unlocked"],
        "block_trade with seller party if present",
        "HHI of seller-side block_trade amount by seller over trailing N days",
        DELAYED_ASOF,
        "Complements C200 buyer concentration; seller-side concentration is not covered.",
        "engineerable_if_block_trade_party_fields_exist",
        "block_trade_cached_field_check_required",
        ["seller", "amount"],
        "daily_event",
    ),
    candidate(
        "unlock_pressure_to_adv_30d",
        "unlock_float",
        "P1",
        ["data_unlocked", "local_raw"],
        "share_float/unlock schedule + daily volume",
        "upcoming_unlock_shares_30d / (rolling_mean(volume_shares, 20d) + eps)",
        DELAYED_ASOF,
        "Distinct from C202 unlock_pressure_30d which scales by float; this scales by trading capacity.",
        "engineerable_if_unlock_schedule_available",
        "needs_unlock_schedule_source_or_share_float_event_join",
        ["unlock_shares", "volume"],
        "daily_event",
    ),
    candidate(
        "pledge_release_acceleration",
        "pledge",
        "P1",
        ["data_unlocked"],
        "pledge_stat + share_float",
        "-delta(pledged_share_ratio, short_window) - delta(pledged_share_ratio, long_window)",
        DELAYED_ASOF,
        "Complements C204 pledge pressure delta; focuses on release acceleration/improving collateral pressure.",
        "engineerable_after_pledge_backfill",
        "pledge_stat_cached_needs_asof_join",
        ["pledged_share_ratio"],
        "daily_event",
    ),
    candidate(
        "forecast_revision_dispersion_change",
        "forecast_event",
        "P1",
        ["data_unlocked"],
        "forecast_vip/express_vip",
        "delta(width_of_forecast_interval / abs(forecast_midpoint + eps), N days)",
        DELAYED_ASOF,
        "Distinct from C208 forecast midpoint revision; measures uncertainty/dispersion change.",
        "engineerable_after_forecast_backfill",
        "forecast_vip_cached_needs_ann_date_asof",
        ["forecast_low", "forecast_high", "forecast_mid"],
        "daily_event",
    ),
    candidate(
        "research_survey_recency_decay",
        "research_event",
        "P1",
        ["data_unlocked", "local_canonical:research_survey_heat_decay"],
        "stk_surv",
        "sum(exp(-days_since_survey / tau) * survey_weight) over trailing N days",
        DELAYED_ASOF,
        "Distinct from C206 20d survey heat; recency-decay weighting rather than simple count.",
        "engineerable_after_survey_backfill",
        "stk_surv_needs_cache_and_timestamp_check",
        ["ann_date", "org_name"],
        "daily_event",
    ),
    candidate(
        "hsgt_top10_entry_streak",
        "northbound_flow",
        "P1",
        ["data_unlocked"],
        "hsgt_top10",
        "consecutive days stock appears in hsgt_top10 net-buy list or rolling entry count",
        DELAYED_ASOF,
        "Distinct from C210 net-buy intensity; captures persistence/attention streak.",
        "engineerable_after_hsgt_backfill",
        "hsgt_top10_cached_needs_asof_join",
        ["ts_code", "net_amount"],
        "daily_event",
    ),
    candidate(
        "ccass_acceleration_rank",
        "northbound_flow",
        "P1",
        ["data_unlocked"],
        "ccass_hold",
        "cross-sectional rank(delta(holding_ratio, short_window) - delta(holding_ratio, long_window))",
        DELAYED_ASOF,
        "Distinct from C211 5d holding change; captures acceleration and cross-sectional rank.",
        "engineerable_after_ccass_backfill",
        "ccass_hold_cached_from_2020_needs_asof_join",
        ["holding_ratio"],
        "daily_event",
    ),
    candidate(
        "industry_flow_rotation_accel",
        "industry_flow",
        "P1",
        ["data_unlocked", "local_canonical:industry_moneyflow_resonance"],
        "moneyflow_ind_dc or moneyflow_ind_ths",
        "rank(delta(industry_main_net_inflow_rate, 3d) - delta(industry_main_net_inflow_rate, 10d)) mapped to stock industry",
        DELAYED_ASOF,
        "Distinct from C214 industry flow strength and C215 stock-vs-industry divergence; this is rotation acceleration.",
        "engineerable_after_industry_flow_join",
        "industry_moneyflow_cached_needs_stock_industry_mapping",
        ["industry_code", "main_net_inflow"],
        "daily_event",
    ),
    candidate(
        "wq_volume_price_rank_divergence",
        "formulaic_alpha",
        "P1",
        ["worldquant", "local_canonical:rolling_rank_volume_price_residual"],
        "daily OHLCV or 14:57 proxy OHLCV",
        "rank(delta(close, 1)) - rank(delta(volume, 1))",
        DAILY_ASOF,
        "Simple formulaic rank divergence; distinct from C278 decay correlation and C279 sign-volume-return.",
        "engineerable_now_with_daily_or_1457_proxy",
        "daily_ohlcv_available_needs_1457_proxy_for_live",
        ["close", "volume"],
        "daily_or_1457_proxy",
    ),
    candidate(
        "wq_turnover_adjusted_reversal",
        "formulaic_alpha",
        "P1",
        ["worldquant", "local_canonical:reversal_with_volume"],
        "daily OHLCV + turnover/free float",
        "-ret_1 / (log1p(turnover_rate) + eps)",
        DAILY_ASOF,
        "Reversal scaled by turnover, not the same as C279 sign-volume-return or C227 pullback.",
        "engineerable_now_with_daily_or_1457_proxy",
        "daily_ohlcv_available_needs_turnover_or_share_float",
        ["close", "volume", "free_share"],
        "daily_or_1457_proxy",
    ),
    candidate(
        "qlib_alpha360_intraday_shape_moment",
        "formulaic_alpha",
        "P1",
        ["qlib", "local_canonical:alpha360_shape_moment_intraday"],
        "1min bars",
        "shape moments from normalized intraday close sequence: slope, curvature, max drawdown and last-position percentile",
        MINUTE_ASOF,
        "Qlib Alpha360-style sequence feature rewritten to 1min intraday; distinct from C280 single OHLC shape.",
        "engineerable_after_1min_cache",
        "stk_mins_1_available_needs_sequence_feature_builder",
        ["close"],
        "1min",
    ),
    candidate(
        "global_overnight_risk_gap",
        "cross_market",
        "P2",
        ["data_unlocked", "local_raw:a50_night_return"],
        "index_global + A50/overseas index series",
        "zscore(weighted overnight return of A50/HK/US risk basket) * stock_or_theme_beta_to_global_risk",
        "Use only overseas data published before A-share open/14:57; if timestamp is uncertain, shift one trading day.",
        "Distinct from C217 global index dispersion; this is directional overnight risk shock mapped by beta.",
        "engineerable_after_global_calendar_alignment",
        "index_global_cached_needs_symbol_map_and_timestamp_check",
        ["index_close", "index_return"],
        "daily_cross_market",
    ),
]


def walk_factor_objects(obj):
    if isinstance(obj, dict):
        fid = obj.get("factor_id")
        if isinstance(fid, str) and re.fullmatch(r"C\d{3}", fid):
            yield obj
        for value in obj.values():
            yield from walk_factor_objects(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_factor_objects(value)


def remove_existing_batch(data: dict) -> None:
    data.pop(BATCH, None)
    for key, value in list(data.items()):
        if key == "meta":
            continue
        if isinstance(value, dict):
            for subkey, subvalue in list(value.items()):
                if isinstance(subvalue, list):
                    value[subkey] = [
                        item
                        for item in subvalue
                        if not (isinstance(item, dict) and item.get("batch") == BATCH)
                    ]
        elif isinstance(value, list):
            data[key] = [
                item
                for item in value
                if not (isinstance(item, dict) and item.get("batch") == BATCH)
            ]


def assign_ids(data: dict, candidates: list[dict]) -> list[dict]:
    existing_ids = []
    existing_names = set()
    for item in walk_factor_objects(data):
        existing_ids.append(int(item["factor_id"][1:]))
        if item.get("name"):
            existing_names.add(item["name"])
    start = max(existing_ids, default=0) + 1
    seen_names = set()
    assigned = []
    for offset, item in enumerate(candidates):
        if item["name"] in existing_names:
            raise ValueError(f"Candidate name already exists in registry: {item['name']}")
        if item["name"] in seen_names:
            raise ValueError(f"Duplicate candidate name inside batch: {item['name']}")
        seen_names.add(item["name"])
        new_item = dict(item)
        new_item["factor_id"] = f"C{start + offset:03d}"
        assigned.append(new_item)
    return assigned


def update_registry(data: dict, assigned: list[dict]) -> None:
    by_priority = dict(Counter(item["priority"] for item in assigned))
    by_family = dict(Counter(item["family"] for item in assigned))
    data[BATCH] = {
        "search_date": DATE,
        "search_round": "global_deep_exhaustive_round",
        "purpose": "Four-source short-line factor expansion after local raw pool, broker/paper, GitHub/open-source and social/Taoguba review.",
        "scope": "factor-library only; no training, no gpu_probe, no model-code change",
        "source_evidence": SOURCE_MAP,
        "selection_criteria": [
            "explicit computable definition",
            "named data source or data gap",
            "asof rule documented",
            "not exact duplicate of C001-C292",
            "no passed/final_unseen/frozen claim",
        ],
        "total": len(assigned),
        "by_priority": by_priority,
        "by_family": by_family,
        "detail": assigned,
        "deferred_or_rejected_summary": {
            "level2_orderbook": "Rejected/deferred unless a stable L2/orderbook pipeline is added; 1min proxy variants admitted separately.",
            "pure_social_nlp": "Deferred unless timestamped scrape/NLP source is locked; existing C286-C289 already cover broad social families.",
            "formula_unlocked": "Kept out if formula depends on subjective trader language or target/future fields.",
            "duplicate_existing": "Kept out when equivalent to C001-C292, O-queue canonical groups, or implemented baseline columns.",
        },
    }
    meta = data.setdefault("meta", {})
    batches = list(meta.get("candidate_batches", []))
    if BATCH not in batches:
        batches.append(BATCH)
    meta["candidate_batches"] = batches
    meta["latest_candidate_batch"] = BATCH
    meta["updated"] = DATE
    meta["registry_candidate_count"] = sum(1 for _ in walk_factor_objects(data))
    meta["global_deep_search_20260517"] = {
        "new_candidates": len(assigned),
        "id_range": f"{assigned[0]['factor_id']}-{assigned[-1]['factor_id']}",
        "search_sources": list(SOURCE_MAP.keys()),
        "validation": "10 structural checks required after write",
        "training_boundary": "not_trained; research_candidate only",
    }


def render_report(data: dict, assigned: list[dict]) -> str:
    p_counts = Counter(item["priority"] for item in assigned)
    f_counts = Counter(item["family"] for item in assigned)
    lines = [
        "# Global Deep Short-Line Factor Search 2026-05-17",
        "",
        "Scope: factor-library only. No training, no gpu_probe, no model or frozen config changes.",
        "",
        "## Search Surface",
        "",
    ]
    for key, value in SOURCE_MAP.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Added To Registry",
            "",
            f"- Batch: `{BATCH}`",
            f"- Count: {len(assigned)}",
            f"- ID range: `{assigned[0]['factor_id']}-{assigned[-1]['factor_id']}`",
            f"- Priority counts: {dict(p_counts)}",
            f"- Family counts: {dict(f_counts)}",
            "",
            "| ID | Name | Priority | Family | Data Need | Status | Asof |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in assigned:
        lines.append(
            f"| {item['factor_id']} | {item['name']} | {item['priority']} | {item['family']} | "
            f"{item['data_need']} | {item['engineering_status']} | {item['asof_rule']} |"
        )
    lines.extend(
        [
            "",
            "## Deferred / Not Registered",
            "",
            "- True L2/orderbook factors such as bid-ask depth imbalance, cancellation pressure, and OFI are not registered unless a stable L2 pipeline exists.",
            "- Pure social/video/NLP factors are not expanded further because C286-C289 already cover the broad families and timestamped scrape is not locked.",
            "- Same-name or near-trivial formulas such as `price = close`, raw `volume_ratio`, and target/future-return phrases are rejected.",
            "- Daily final-close formulas are admitted only when they can be shifted to T-1 or rewritten to 14:57 proxy OHLCV.",
            "",
            "## Data Handoff",
            "",
            "- P0 minute candidates need full `stk_mins_1` coverage and a same-clock history matrix.",
            "- Limit-board candidates need timestamped limit-pool reconstruction to 14:57 or T-1 fallback.",
            "- Event/data-unlocked candidates need T-1 or announcement-time asof joins.",
            "- Formulaic candidates need explicit 14:57 proxy fields before live model use.",
            "",
            "## Ten Validation Checks",
            "",
        ]
    )
    checks = [
        "JSON loads",
        "C IDs are continuous",
        "No duplicate factor_id",
        "No duplicate factor name",
        "meta registry count matches actual C objects",
        "New batch exists and count matches detail length",
        "All new entries have required fields",
        "All new entries are training_status=not_trained",
        "All new entries are lockbox_role=research_candidate",
        "No new entry claims is_passed/is_final_unseen/is_frozen_modified",
    ]
    for i, check in enumerate(checks, 1):
        lines.append(f"{i}. {check}: PASS")
    lines.append("")
    return "\n".join(lines)


def render_md_registry_section(assigned: list[dict]) -> str:
    lines = [
        "",
        "---",
        "",
        f"## Batch: {BATCH}",
        "",
        "> Purpose: Four-source global short-line factor expansion with strict registry gates.",
        "> Scope: factor-library only; no training, no gpu_probe, no model-code change.",
        '> All: `training_status="not_trained"`, `lockbox_role="research_candidate"`.',
        "> Detailed report: `docs/global_deep_factor_search_20260517.md`",
        "",
        f"### Promoted ({len(assigned)}): {assigned[0]['factor_id']}-{assigned[-1]['factor_id']}",
        "",
        "| ID | Name | Priority | Family | Data Need | Definition | Status |",
        "|----|------|----------|--------|-----------|------------|--------|",
    ]
    for item in assigned:
        definition = item["computable_definition"].replace("|", "/")
        lines.append(
            f"| {item['factor_id']} | {item['name']} | {item['priority']} | {item['family']} | "
            f"{item['data_need']} | {definition} | {item['engineering_status']} |"
        )
    return "\n".join(lines) + "\n"


def append_md_registry(assigned: list[dict]) -> None:
    section = render_md_registry_section(assigned)
    old = MD_REGISTRY_PATH.read_text(encoding="utf-8") if MD_REGISTRY_PATH.exists() else ""
    marker = f"## Batch: {BATCH}"
    if marker in old:
        idx = old.index(marker)
        prefix = old[:idx]
        # Drop the separator immediately before the previous section if present.
        prefix = re.sub(r"\n---\n\n$", "\n", prefix)
        old = prefix.rstrip() + "\n"
    MD_REGISTRY_PATH.write_text(old.rstrip() + section, encoding="utf-8")


def validate(data: dict, assigned: list[dict]) -> list[str]:
    all_items = list(walk_factor_objects(data))
    ids = [item["factor_id"] for item in all_items]
    nums = sorted(int(x[1:]) for x in ids)
    expected = list(range(1, max(nums) + 1))
    required = {
        "factor_id",
        "name",
        "family",
        "priority",
        "source_type",
        "source_refs",
        "data_need",
        "computable_definition",
        "asof_rule",
        "duplicate_check",
        "engineering_status",
        "data_status",
        "training_status",
        "lockbox_role",
        "batch",
    }
    checks = []
    checks.append(("JSON object", isinstance(data, dict)))
    checks.append(("C IDs continuous", nums == expected))
    checks.append(("No duplicate factor_id", len(ids) == len(set(ids))))
    names = [item.get("name") for item in all_items if item.get("name")]
    checks.append(("No duplicate names", len(names) == len(set(names))))
    checks.append(("Meta count matches", data.get("meta", {}).get("registry_candidate_count") == len(all_items)))
    checks.append((f"{BATCH} exists", BATCH in data and len(data[BATCH]["detail"]) == len(assigned)))
    checks.append(("Required fields", all(required <= set(item) for item in assigned)))
    checks.append(("All not_trained", all(item.get("training_status") == "not_trained" for item in assigned)))
    checks.append(("All research_candidate", all(item.get("lockbox_role") == "research_candidate" for item in assigned)))
    checks.append(("No passed/final/frozen claims", all(not any(k in item for k in ("is_passed", "is_final_unseen", "is_frozen_modified")) for item in assigned)))
    failed = [name for name, ok in checks if not ok]
    if failed:
        raise AssertionError(f"Validation failed: {failed}")
    return [name for name, _ in checks]


def main() -> None:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    remove_existing_batch(data)
    assigned = assign_ids(data, CANDIDATES)
    update_registry(data, assigned)
    passed = validate(data, assigned)
    REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(data, assigned), encoding="utf-8")
    append_md_registry(assigned)
    print(f"wrote batch={BATCH}")
    print(f"new_count={len(assigned)}")
    print(f"id_range={assigned[0]['factor_id']}-{assigned[-1]['factor_id']}")
    print(f"registry_count={data['meta']['registry_candidate_count']}")
    print("checks=" + ",".join(passed))
    print(f"registry={REGISTRY_PATH}")
    print(f"report={REPORT_PATH}")
    print(f"md_registry={MD_REGISTRY_PATH}")


if __name__ == "__main__":
    main()
