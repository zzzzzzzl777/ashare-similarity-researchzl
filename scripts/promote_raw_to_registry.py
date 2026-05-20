"""Promote 14 raw pool candidates to factor registry as C139-C152."""
import json
import copy

REGISTRY_PATH = r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json"

NEW_BATCH = "candidates_20260506_raw_review"

PROMOTED = [
    {
        "factor_id": "C139",
        "name": "real_limit_up_premium_gap",
        "family": "limit_up_premium",
        "source_type": "taoguba",
        "raw_factor_id": "RAW001760",
        "raw_source_path": "factor_doc_scan_short_desktop_latest.jsonl",
        "raw_source_line": 1047,
        "raw_idea": "昨日真实涨停股池今日平均收益 - OHLCV代理涨停股今日平均收益",
        "computable_definition": "mean(return_T, real_limit_pool_T-1) - mean(return_T, ohlcv_proxy_limit_pool_T-1); real pool from stock_zt_pool_previous_em, proxy from close==high_limit",
        "data_need": "limit_pool (stock_zt_pool_previous_em) + daily_ohlcv",
        "asof_rule": "T-day close (uses T-1 pool, T-day returns)",
        "leakage_risk": "none",
        "related_existing_features": ["prev_limit_up_premium"],
        "duplicate_check": "prev_limit_up_premium is single-pool premium; this is the GAP between real vs proxy pools — distinct signal",
        "engineering_status": "candidate",
        "priority": "P0",
        "implementation_hint": "stock_zt_pool_previous_em gives real T-1 limit pool; OHLCV proxy = close==high_limit from daily bar; compute cross-sectional avg return gap",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C140",
        "name": "zbgc_sector_pressure",
        "family": "board_quality",
        "source_type": "taoguba",
        "raw_factor_id": "RAW001768",
        "raw_source_path": "factor_doc_scan_short_desktop_latest.jsonl",
        "raw_source_line": 1055,
        "raw_idea": "同行业/同题材炸板股数量 / 该题材涨停尝试数",
        "computable_definition": "count(broken_board, same_sector) / count(limit_attempt, same_sector); broken_board from stock_zt_pool_zbgc_em",
        "data_need": "limit_pool (stock_zt_pool_zbgc_em) + sector_theme membership",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["seal_rate_80_threshold", "sector_limit_up_count"],
        "duplicate_check": "seal_rate_80_threshold is market-level; sector_limit_up_count is raw count; this is sector-level broken-board RATIO — distinct",
        "engineering_status": "candidate",
        "priority": "P0",
        "implementation_hint": "stock_zt_pool_zbgc_em API → broken boards; group by sector; ratio = broken / (broken + sealed in same sector)",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C141",
        "name": "prev_top20_chase_real",
        "family": "market_breadth",
        "source_type": "taoguba",
        "raw_factor_id": "RAW001770",
        "raw_source_path": "factor_doc_scan_short_desktop_latest.jsonl",
        "raw_source_line": 1057,
        "raw_idea": "昨日涨幅前20今日平均收益、红盘率",
        "computable_definition": "mean(pct_change_T, top20_gainers_T-1); red_rate = count(pct_change_T > 0, top20_gainers_T-1) / 20",
        "data_need": "daily_ohlcv",
        "asof_rule": "T-day close (uses T-1 rank, T-day returns)",
        "leakage_risk": "none",
        "related_existing_features": [],
        "duplicate_check": "No existing feature tracks top-N gainer next-day performance. Market-level chase-effectiveness signal.",
        "engineering_status": "candidate",
        "priority": "P0",
        "implementation_hint": "Rank all stocks by T-1 pct_change, take top 20, compute their T-day avg return and positive-return rate",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C142",
        "name": "theme_limit_density",
        "family": "sector_momentum",
        "source_type": "taoguba",
        "raw_factor_id": "RAW001781",
        "raw_source_path": "factor_doc_scan_short_desktop_latest.jsonl",
        "raw_source_line": 1068,
        "raw_idea": "题材内涨停数 / 题材成份数",
        "computable_definition": "count(limit_up, in_theme) / count(members, in_theme)",
        "data_need": "limit_pool + sector_theme membership",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["sector_limit_up_count"],
        "duplicate_check": "sector_limit_up_count is raw count; this normalizes by sector SIZE giving density — distinct",
        "engineering_status": "candidate",
        "priority": "P1",
        "implementation_hint": "Use stock_zt_pool for limit-up list + ths_index_member for sector membership; ratio = limit_count / member_count per theme",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C143",
        "name": "is_volume_sufficient",
        "family": "volume_quality",
        "source_type": "taoguba",
        "raw_factor_id": "RAW000012",
        "raw_source_path": "factor_doc_scan_tgb_desktop_latest.jsonl",
        "raw_source_line": 78,
        "raw_idea": "换手率是否达到前日70%以上",
        "computable_definition": "turnover_rate_T / turnover_rate_T-1 >= 0.7 (binary); or continuous ratio version",
        "data_need": "daily_ohlcv (turnover_rate field)",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["volume_vs_prev", "turnover_rate"],
        "duplicate_check": "volume_vs_prev is volume ratio; turnover_rate is absolute; this is a SUFFICIENCY threshold on relative turnover — distinct as conditional signal",
        "engineering_status": "candidate",
        "priority": "P1",
        "implementation_hint": "turnover_rate from daily bar; compute ratio to T-1; threshold at 0.7 for binary or use continuous ratio",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C144",
        "name": "leader_pull_effect",
        "family": "sector_momentum",
        "source_type": "taoguba",
        "raw_factor_id": "RAW000042",
        "raw_source_path": "factor_doc_scan_tgb_desktop_latest.jsonl",
        "raw_source_line": 123,
        "raw_idea": "个股涨停→同板块平均涨幅",
        "computable_definition": "mean(pct_change, same_sector_peers) on day stock hits limit_up; measures how much the stock 'pulls' its sector",
        "data_need": "daily_ohlcv + limit_pool + sector_theme",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["sector_pct_change_best", "sector_strength_rank"],
        "duplicate_check": "Existing features measure sector return itself; this measures sector response TO a specific stock's limit-up — causal direction differs",
        "engineering_status": "candidate",
        "priority": "P1",
        "implementation_hint": "For each limit-up stock on day T: get its sector, compute mean pct_change of other stocks in that sector on same day T",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C145",
        "name": "theme_height_suppression",
        "family": "sector_cycle",
        "source_type": "taoguba",
        "raw_factor_id": "RAW000063",
        "raw_source_path": "factor_doc_scan_tgb_desktop_latest.jsonl",
        "raw_source_line": 159,
        "raw_idea": "该题材历史最高连板数",
        "computable_definition": "max(board_count, all_stocks_in_same_theme, last_252_trading_days); current stock's board_count / theme_historical_max gives proximity to ceiling",
        "data_need": "daily_ohlcv + limit_pool + sector_theme",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["market_max_board_height", "board_count"],
        "duplicate_check": "market_max_board_height is market-wide; this is THEME-specific historical ceiling — different granularity",
        "engineering_status": "candidate",
        "priority": "P1",
        "implementation_hint": "For each stock's theme: scan last 1Y of limit_pool to find max consecutive boards any stock achieved in that theme; compare current stock's board_count to this ceiling",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C146",
        "name": "support_one_word_count",
        "family": "board_structure",
        "source_type": "taoguba",
        "raw_factor_id": "RAW000075",
        "raw_source_path": "factor_doc_scan_tgb_desktop_latest.jsonl",
        "raw_source_line": 186,
        "raw_idea": "板块内一字板涨停数（非核心，为核心助力）",
        "computable_definition": "count(stocks where open==close==high_limit, same_sector, day_T)",
        "data_need": "daily_ohlcv + sector_theme",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["sector_limit_up_count"],
        "duplicate_check": "sector_limit_up_count counts ALL limit-ups; this counts only ONE-WORD boards (open==close==high_limit) — subset with different meaning (institutional lock-in)",
        "engineering_status": "candidate",
        "priority": "P1",
        "implementation_hint": "Filter daily bars where open==close==high_limit (one-word board); group by sector; count per sector",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C147",
        "name": "eruption_strength",
        "family": "market_breadth",
        "source_type": "taoguba",
        "raw_factor_id": "RAW000131",
        "raw_source_path": "factor_doc_scan_tgb_desktop_latest.jsonl",
        "raw_source_line": 262,
        "raw_idea": "涨停家数+一字板数+买不到程度 综合评分",
        "computable_definition": "zscore(market_limit_up_count) + zscore(market_one_word_count) + zscore(unbuyable_rate); unbuyable_rate = count(seal_money > 5*daily_amount) / total_limit_up",
        "data_need": "daily_ohlcv + limit_pool",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["market_limit_up_count"],
        "duplicate_check": "market_limit_up_count is one component; this is a 3-factor COMPOSITE measuring eruption intensity — distinct",
        "engineering_status": "candidate",
        "priority": "P2",
        "implementation_hint": "Three components: (1) total limit-ups, (2) one-word boards (open==high_limit), (3) unbuyable ratio from seal_money/amount; z-score normalize and sum",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C148",
        "name": "is_ground_sky",
        "family": "extreme_pattern",
        "source_type": "taoguba",
        "raw_factor_id": "RAW001049",
        "raw_source_path": "factor_doc_scan_tgb_desktop_latest.jsonl",
        "raw_source_line": 9304,
        "raw_idea": "地天板: 当日触及跌停后封涨停",
        "computable_definition": "(low == low_limit) AND (close == high_limit); binary flag for ground-sky board",
        "data_need": "daily_ohlcv + limit_pool",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["is_limit_up"],
        "duplicate_check": "is_limit_up only checks close==high_limit; this ALSO requires low==low_limit same day — much rarer extreme reversal pattern",
        "engineering_status": "candidate",
        "priority": "P2",
        "implementation_hint": "Daily bar: low <= low_limit AND close >= high_limit; accounts for 10%/20% limit stocks differently",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C149",
        "name": "seal_trend",
        "family": "board_quality",
        "source_type": "taoguba",
        "raw_factor_id": "RAW001112",
        "raw_source_path": "factor_doc_scan_tgb_desktop_latest.jsonl",
        "raw_source_line": 9698,
        "raw_idea": "封单变化趋势(增/减)",
        "computable_definition": "seal_money_T / seal_money_T-1 - 1 (for multi-board stocks); or slope(seal_money, last_n_limit_days)",
        "data_need": "limit_pool (seal_money from stock_zt_pool)",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["seal_money_to_float_mv"],
        "duplicate_check": "seal_money_to_float_mv is a snapshot ratio; this is the CHANGE/TREND across consecutive limit days — temporal dimension",
        "engineering_status": "candidate",
        "priority": "P2",
        "implementation_hint": "For multi-board stocks: look up seal_money on consecutive limit-up days from stock_zt_pool; compute ratio or log-diff",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C150",
        "name": "old_leader_decay",
        "family": "market_cycle",
        "source_type": "taoguba",
        "raw_factor_id": "RAW002609",
        "raw_source_path": "factor_doc_scan_short_desktop_latest.jsonl",
        "raw_source_line": 10025,
        "raw_idea": "老龙头衰退 + 新龙头崛起 = 切换信号",
        "computable_definition": "(highest_board_stock.broken_board_today) OR (highest_board_stock.volume_T / volume_T-1 < 0.7); binary market-level signal",
        "data_need": "daily_ohlcv + limit_pool",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["market_max_board_height"],
        "duplicate_check": "market_max_board_height is the height value; this is whether the TOP stock is DECAYING (broken or volume collapse) — distinct signal for regime change",
        "engineering_status": "candidate",
        "priority": "P2",
        "implementation_hint": "Identify highest-board stock from limit_pool; check if it broke (not in today's pool) or volume dropped >30% vs yesterday",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C151",
        "name": "anti_drop_strength",
        "family": "relative_strength",
        "source_type": "taoguba",
        "raw_factor_id": "RAW000043",
        "raw_source_path": "factor_doc_scan_tgb_desktop_latest.jsonl",
        "raw_source_line": 124,
        "raw_idea": "大盘下跌时个股跌幅/大盘跌幅",
        "computable_definition": "pct_change_stock / pct_change_index WHERE pct_change_index < -0.5%; NaN or 0 on non-down days",
        "data_need": "daily_ohlcv (stock + index)",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": ["beta_5d"],
        "duplicate_check": "beta_5d is symmetric over all days; this is CONDITIONAL beta only on down days — captures defensive quality specifically",
        "engineering_status": "candidate",
        "priority": "P2",
        "implementation_hint": "Use SH000001 (上证) or SH000300 as benchmark; on days index < -0.5%, compute stock_return / index_return; rolling avg over N days",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    },
    {
        "factor_id": "C152",
        "name": "multi_wave_count",
        "family": "technical_pattern",
        "source_type": "taoguba",
        "raw_factor_id": "RAW000071",
        "raw_source_path": "factor_doc_scan_tgb_desktop_latest.jsonl",
        "raw_source_line": 177,
        "raw_idea": "个股经历的上涨波段数",
        "computable_definition": "count(rising_segments) in last 60 trading days; rising_segment defined as consecutive days where close > close_5d_ago",
        "data_need": "daily_ohlcv",
        "asof_rule": "T-day close",
        "leakage_risk": "none",
        "related_existing_features": [],
        "duplicate_check": "No existing feature counts wave/segment structure. Technical pattern factor for cycle positioning.",
        "engineering_status": "candidate",
        "priority": "P2",
        "implementation_hint": "Simple: rolling 60d window, count transitions from falling to rising (pct_change_5d crosses zero from negative to positive)",
        "training_status": "not_trained",
        "lockbox_role": "research_candidate"
    }
]


def main():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    # Validate C001-C138 intact: count all existing candidates
    existing_ids = set()
    for batch_key in registry["meta"]["candidate_batches"]:
        batch = registry[batch_key]
        if "detail" in batch:
            for entry in batch["detail"]:
                fid = entry.get("factor_id")
                if fid:
                    existing_ids.add(fid)
        else:
            for priority_key in ["p0", "p1", "p2", "blocked"]:
                if priority_key in batch:
                    for entry in batch[priority_key]:
                        fid = entry.get("factor_id")
                        if fid:
                            existing_ids.add(fid)

    print(f"Existing candidate IDs: {len(existing_ids)} (expected >=132)")
    assert "C001" in existing_ids
    assert "C132" in existing_ids
    assert "C138" in existing_ids

    # Verify no overlap
    new_ids = {c["factor_id"] for c in PROMOTED}
    overlap = existing_ids & new_ids
    assert not overlap, f"ID overlap: {overlap}"

    # Add new batch
    new_batch = {
        "search_date": "2026-05-06",
        "purpose": "Promote high-quality raw pool candidates with clear computable definitions to formal registry",
        "source": "raw_to_registry_review_queue_20260506.md (50 candidates, 14 promoted)",
        "selection_criteria": [
            "free_data=True",
            "future_leakage_risk=low",
            "needs_level2=False",
            "Clear computable definition derivable from raw_text",
            "Not duplicate of C001-C138 or existing implemented features",
            "Distinct signal from related_existing_features"
        ],
        "total": 14,
        "by_priority": {
            "P0": 3,
            "P1": 5,
            "P2": 6
        },
        "by_family": {
            "limit_up_premium": 1,
            "board_quality": 2,
            "market_breadth": 2,
            "sector_momentum": 2,
            "sector_cycle": 1,
            "volume_quality": 1,
            "board_structure": 1,
            "extreme_pattern": 1,
            "market_cycle": 1,
            "relative_strength": 1,
            "technical_pattern": 1
        },
        "detail": PROMOTED
    }

    registry[NEW_BATCH] = new_batch

    # Update meta
    registry["meta"]["candidate_batches"].append(NEW_BATCH)
    registry["meta"]["latest_candidate_batch"] = NEW_BATCH
    registry["meta"]["updated"] = "2026-05-06"
    registry["meta"]["registry_raw_mapping_summary"]["registry_candidates_total"] = len(existing_ids) + 14

    # Write
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

    # Validate output
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        check = json.load(f)

    assert NEW_BATCH in check
    assert len(check[NEW_BATCH]["detail"]) == 14
    assert check[NEW_BATCH]["detail"][0]["factor_id"] == "C139"
    assert check[NEW_BATCH]["detail"][-1]["factor_id"] == "C152"
    assert check["meta"]["latest_candidate_batch"] == NEW_BATCH
    assert "candidates" in check  # original batch still exists
    assert "C001" in str(check["candidates"])

    # Verify no passed/final_unseen
    assert check["meta"]["is_passed"] is False
    assert check["meta"]["is_final_unseen"] is False
    assert check["meta"]["is_frozen_modified"] is False

    print(f"Registry updated: {NEW_BATCH} with C139-C152 (14 candidates)")
    print(f"Total batches: {len(check['meta']['candidate_batches'])}")
    print(f"Total candidates: {check['meta']['registry_raw_mapping_summary']['registry_candidates_total']}")
    print("All validations passed.")


if __name__ == "__main__":
    main()
