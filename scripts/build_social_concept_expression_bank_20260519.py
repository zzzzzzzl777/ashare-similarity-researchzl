"""Build a concept-expression bank for social short-line language.

This is registry-support material only:
- no training
- no gpu_probe
- no model or frozen config changes
- no formal Cxxx registry mutation
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(r"C:\Users\zzzzzzl\Desktop\subagent")
REPORT_DIR = ROOT / "docs"
RUNTIME_DIR = Path(r"E:\ashare_similarity_runtime\data\reports\prediction")
MD_PATH = REPORT_DIR / "social_concept_expression_bank_20260519.md"
JSON_PATH = RUNTIME_DIR / "social_concept_expression_bank_20260519.json"


SOURCES = {
    "local_raw_pool": str(RUNTIME_DIR / "raw_factor_pool_index.json"),
    "registry": str(RUNTIME_DIR / "factor_registry.json"),
    "tgb_research_doc": str(REPORT_DIR / "tgb_factor_research.md"),
    "social_search_doc": str(REPORT_DIR / "social_media_factor_search_20260518.md"),
    "shortline_expansion_doc": str(REPORT_DIR / "shortline_factor_expansion_20260515.md"),
    "public_tgb_limit_timing": "https://www.tgb.cn/a/2r0quFL61AP-1",
    "public_tgb_leader_system": "https://m.tgb.cn/a/22WTZ9li7eP?type=new",
    "public_tgb_leader_switch": "https://www.tgb.cn/a/26R2UPyruwj",
    "public_tgb_reseal": "https://www.tgb.cn/a/1J2ESG6yyho",
}


def e(
    concept: str,
    name: str,
    formula: str,
    data: str,
    asof: str,
    relation: str,
    action: str,
    note: str,
):
    return {
        "concept": concept,
        "name": name,
        "formula": formula,
        "data_need": data,
        "asof_rule": asof,
        "registry_relation": relation,
        "suggested_action": action,
        "note": note,
    }


EXPRESSIONS = [
    e("weak_to_strong", "prior_weakness_context", "z(prev_day_intraday_drawdown) + I(prev_broken_board) + I(prev_close_below_vwap_or_ma5)", "daily OHLCV, prior 1min/5min bars, limit_pool broken-board flags", "Uses only T-1 and older data before next open.", "covered_by_or_related: C400, C396, C261", "use_as_component", "把'弱'先拆清楚: 昨日炸板、尾盘走弱、放量滞涨、首阴等不是同一种弱。"),
    e("weak_to_strong", "weak_open_prev_close_reclaim_speed", "I(open_gap <= 0) * 1/(minutes_to_reclaim_prev_close + 1) * volume_confirm_z", "auction/open, 1min bars, prev_close, minute volume", "Live-safe only after reclaim has occurred before cutoff.", "covered_by_or_related: C317, C318; raw prev_close_reclaim_speed", "candidate_component", "弱开后快速收复昨收, 是口语'超预期'最直接的分钟表达。"),
    e("weak_to_strong", "weak_open_vwap_reclaim_speed", "I(first5_return < 0) * 1/(minutes_to_reclaim_vwap + 1) * up_volume_ratio_after_reclaim", "1min bars, intraday VWAP, minute volume", "Live-safe after VWAP reclaim; full-day version T+1.", "covered_by_or_related: C048, C313, C317", "candidate_component", "比收复昨收更偏盘口承接, 适合和 C048/C313 对照。"),
    e("weak_to_strong", "low_open_no_new_low_hold", "I(open_gap < 0) * I(no_new_low_after_first_10m) * (close_30m - low_10m)/abs(open_gap)", "1min bars", "Live-safe after observation window, e.g. 10:30 or 11:30.", "new_expression_material", "review_for_registry", "真弱通常继续破低; 假弱会低开后不再杀。"),
    e("weak_to_strong", "weak_to_strong_volume_efficiency", "(price_at_reclaim / intraday_low - 1) / log1p(amount_until_reclaim)", "1min bars, minute amount", "Live-safe after reclaim; no future bars after cutoff.", "raw_material: weak_to_strong_volume_efficiency", "review_for_registry", "同样收复, 少花成交额完成更强; 可避免只奖励暴量。"),
    e("weak_to_strong", "morning_false_weak_score", "I(first15_return < 0) * z(return_15_60m) * I(price_above_vwap_by_1030)", "1min bars, VWAP", "Use cutoff >=10:30; earlier cutoff needs partial formula.", "raw_material: false_weak_classification", "review_for_registry", "把'假弱'从主观描述变成上午路径。"),
    e("weak_to_strong", "gap_fill_speed_with_volume", "I(open_gap < 0) * 1/(minutes_to_fill_gap + 1) * z(volume_during_fill/avg_20d_firstN_volume)", "auction/open, 1min bars, 20d minute baselines", "Live-safe after gap filled.", "covered_by_or_related: C084, C318", "use_as_component", "低开缺口被快速回补, 对应'低开高走超预期'。"),
    e("weak_to_strong", "weak_open_sector_relative_reclaim", "stock_reclaim_score - median(theme_member_reclaim_score)", "theme membership, 1min bars", "Theme membership must be known by cutoff; otherwise T+1.", "covered_by_or_related: C433, C434", "candidate_component", "个股弱转强若领先板块, 比跟随板块被动修复更有价值。"),
    e("weak_to_strong", "yesterday_broken_today_reseal", "I(T-1 broken_board) * 1/(today_reseal_minutes + 1) * reseal_strength", "limit_pool, 1min bars, limit price", "Live-safe after reseal; T+1 if using full-day stats.", "covered_by_or_related: C066, C193, C246", "candidate_component", "炸板后的次日修复, 是短线常说'弱转强接力'核心场景。"),
    e("weak_to_strong", "large_volume_weak_open_acceptance", "I(T-1 volume_z > threshold) * I(open_gap < 0) * intraday_repair_score", "daily volume, auction/open, 1min bars", "Open part live; repair part live after window.", "covered_by_or_related: C400", "use_as_component", "爆量分歧后低开不崩, 更像换手承接。"),
    e("weak_to_strong", "first_divergence_to_consensus", "I(first_divergence_day_Tminus1) * today_repair_strength * theme_breadth_confirm", "limit_pool, theme membership, daily/minute returns", "Use only confirmed previous divergence plus current observed repair.", "covered_by_or_related: C396", "use_as_component", "分歧转一致不只是涨, 要有题材宽度确认。"),
    e("weak_to_strong", "weak_open_limit_attempt_quality", "I(open_gap <= 0) * limit_attempt_count * max_return_before_1030 / log1p(amount_before_attempt)", "1min bars, limit price", "Live-safe after attempts before cutoff.", "covered_by_or_related: C321, C366, C367", "candidate_component", "弱开后主动攻击涨停价, 能把'抢筹'和'被动拉升'区分开。"),

    e("capital_recognition", "main_force_net_to_float", "net_mf_amount / max(float_mv, eps)", "tushare moneyflow, daily basic/free float", "Tushare moneyflow is after close unless intraday source exists; use T+1.", "covered_by_or_related: C004, C009, C010", "use_as_component", "资金认可的最低层是净流入相对流通盘。"),
    e("capital_recognition", "large_small_order_divergence", "z(elg_net + lg_net) - z(sm_net + md_net)", "moneyflow API", "After-close unless live moneyflow source exists.", "covered_by_or_related: C009, C013, C016, C130", "use_as_component", "大单买、小单卖常被解释为资金承接而非散户接盘。"),
    e("capital_recognition", "moneyflow_persistence_after_limit", "rolling_sum(net_mf_amount, 3d) / rolling_sum(amount, 3d) after recent limit flag", "moneyflow, daily OHLCV, limit_pool", "Use only completed days.", "covered_by_or_related: C002, C003, C068", "candidate_component", "资金认可要看持续性, 不是单日脉冲。"),
    e("capital_recognition", "seal_order_to_float_mv", "seal_order_amount / float_mv", "limit_pool seal order amount, daily basic/free float", "Use only seal snapshot at or before cutoff.", "covered_by_or_related: C039, C327", "use_as_component", "封单强度用流通市值归一化, 避免大盘股天然封单大。"),
    e("capital_recognition", "board_volume_acceptance_split", "volume_near_limit / max(volume_below_limit_after_first_touch, eps)", "1min bars, limit price", "Live-safe after first touch; full-day T+1.", "covered_by_or_related: C252; raw board_volume_acceptance", "use_as_component", "板上放量承接 vs 板下放量出货。"),
    e("capital_recognition", "reseal_strength_after_open_board", "1/(minutes_to_reseal + 1) * reseal_volume / mean(volume_before_reseal)", "1min bars, limit price", "Live-safe after reseal event.", "covered_by_or_related: C193, C246", "use_as_component", "炸板后快速回封是'资金认可'的事件化表达。"),
    e("capital_recognition", "support_absorption_quality", "recovery_return_after_selloff / log1p(amount_during_selloff)", "1min bars, minute amount", "Live-safe after recovery window.", "raw_material: support_absorption_quality; related C085/C302", "review_for_registry", "下杀时成交很大但价格能收回, 表示有承接吸收。"),
    e("capital_recognition", "price_held_during_market_drop", "stock_return_during_market_down_window - beta * index_return_window", "1min bars for stock and index", "Live-safe within completed window.", "covered_by_or_related: C251, C299, C307", "candidate_component", "指数跳水时抗跌, 是盘中资金认可的一种。"),
    e("capital_recognition", "lhb_net_buy_to_amount", "lhb_net_buy_amount / daily_amount", "top_list/top_inst, daily amount", "LHB is after close; use next trading day only.", "covered_by_or_related: C229", "use_as_component", "龙虎榜资金认可, 但严格 T+1。"),
    e("capital_recognition", "multi_hot_seat_buy_strength", "sum(weighted_buy_amount_by_known_seats) / daily_amount", "top_list, seat dictionary, daily amount", "After-close T+1; historical seat weights use only prior events.", "covered_by_or_related: C237, C412, C413", "use_as_component", "多个活跃席位同向买入比单席位更稳。"),
    e("capital_recognition", "institution_hot_money_alignment", "z(institution_net_buy) + z(hot_money_net_buy)", "top_inst/top_list seat classification", "After-close T+1.", "covered_by_or_related: C412, C414", "candidate_component", "机构和游资同向时可视为资金层面合力。"),
    e("capital_recognition", "retail_fomo_vs_big_order_acceptance", "small_order_net_ratio * limit_strength - large_order_sell_pressure", "moneyflow, limit_pool", "After-close unless live order source exists.", "covered_by_or_related: C448", "use_as_component", "识别散户 FOMO 还是大资金接力。"),

    e("leader_temperament", "market_height_rank", "rank(board_count, descending) within market", "limit_pool board_count", "Point-in-time if board_count known; otherwise end-of-day.", "covered_by_or_related: C094, C230, C322, C427", "use_as_component", "龙头气质第一层是全市场高度。"),
    e("leader_temperament", "theme_height_rank", "rank(board_count, descending) within theme", "theme membership, limit_pool", "Theme membership must be cutoff-safe.", "covered_by_or_related: C249, C270, C403", "use_as_component", "板块内最高标更接近'地位'。"),
    e("leader_temperament", "first_seal_rank_in_theme", "rank(first_seal_time, ascending) among theme limit-up names", "limit_pool first seal time, theme membership", "Live-safe only after all compared seal events known; conservative T+1.", "covered_by_or_related: C249", "use_as_component", "同题材最早封板常被解释为主动性。"),
    e("leader_temperament", "leader_pull_effect_intraday", "mean(peer_return_after_leader_seal) * peer_positive_share", "theme membership, leader seal time, 1min bars", "Live-safe after leader seal and peer observation window.", "covered_by_or_related: C144, C422, C433, C434", "use_as_component", "龙头真正的气质要能带动跟风。"),
    e("leader_temperament", "echelon_continuity_gap", "max_gap_between_theme_board_heights or missing_ladder_count", "limit_pool board heights by theme", "End-of-day or live after limit state known.", "covered_by_or_related: C271, C393", "use_as_component", "梯队连续比孤军高标更有持续性。"),
    e("leader_temperament", "position_uniqueness_score", "1 / count(names with same theme, board_height, board_type)", "theme membership, board height, board type", "Point-in-time if inputs known.", "covered_by_or_related: C403", "use_as_component", "辨识度来自稀缺性: 同身位越少越清晰。"),
    e("leader_temperament", "leader_memory_reactivation", "prior_leader_score_same_theme_or_event * exp(-days_since_lead/tau) * current_repair_score", "historical leader labels, theme/event labels, daily/minute returns", "Use only prior leader history; current repair cutoff-bounded.", "covered_by_or_related: C407, C408", "candidate_component", "市场记忆和'老龙回魂'需要历史映射。"),
    e("leader_temperament", "old_leader_decay_vs_new_leader", "old_leader_decay_score * new_leader_emergence_score", "limit_pool, theme membership, prior leader labels", "Use only known old leader state and current observed new leader event.", "covered_by_or_related: C150, C164", "use_as_component", "龙头切换可用老龙衰退+新龙首/二板确认表达。"),
    e("leader_temperament", "substitute_leader_kawei_score", "I(candidate_board_count >= previous_suppression_height) * theme_relation_to_old_leader * seal_rank_score", "limit_pool, theme relation, seal time", "End-of-day or live after candidate reaches board height.", "covered_by_or_related: C270, C393; raw buchang_dragon_kawei", "review_for_registry", "补涨龙卡位要同时看高度压制和同属性关系。"),
    e("leader_temperament", "leader_cap_fit", "abs(log(float_mv) - theme_preferred_cap_center) or float_mv/leader_float_mv", "daily basic/free float, theme membership, leader selection", "Static/daily; no intraday leakage.", "covered_by_or_related: C155, C398", "candidate_component", "短线不是越小越好, 要和题材容量匹配。"),
    e("leader_temperament", "social_recognition_breadth", "unique_authors_or_sources_mentioning_stock / rolling_baseline", "timestamped Taoguba/Guba/Bilibili/Douyin mentions", "Only posts published before cutoff; otherwise T+1.", "covered_by_or_related: C289, C405, C406", "pipeline_dependent", "辨识度的社交表达, 必须有时间戳才安全。"),
    e("leader_temperament", "leader_purity_penalty", "I(active_cb_or_external_anchor) * leader_strength", "convertible bond mapping or external anchor, leader score", "Mapping known before trade; leader score cutoff-bounded.", "covered_by_or_related: C432", "candidate_component", "有转债/外部锚时, 龙头纯度可能被稀释。"),

    e("divergence_acceptance", "intraday_selloff_recovery_efficiency", "(price_after_recovery - low_after_selloff) / log1p(amount_during_selloff)", "1min bars, minute amount", "Live-safe after recovery window.", "covered_by_or_related: C085, C302", "candidate_component", "分歧承接的核心: 跌下去以后能用较少资金修复。"),
    e("divergence_acceptance", "low_price_absorption_repair", "volume_share_low_price_bucket * subsequent_return_from_low", "1min bars, price buckets", "Live-safe after subsequent window; full-day T+1.", "covered_by_or_related: C302, C441", "use_as_component", "低位成交越多且能修复, 承接越强。"),
    e("divergence_acceptance", "vwap_break_reclaim_count", "count(cross below VWAP then reclaim VWAP)", "1min bars, VWAP", "Live-safe up to cutoff.", "covered_by_or_related: C313, C123", "candidate_component", "反复跌破又收回 VWAP, 可量化承接韧性。"),
    e("divergence_acceptance", "tail_reclaim_after_midday_flush", "I(min_return_1300_1430 < -x) * return_1430_close * volume_confirm", "1min bars", "Only use bars before chosen cutoff; close-based version T+1.", "covered_by_or_related: C049, C433", "candidate_component", "午后回流/尾盘回封类语境。"),
    e("divergence_acceptance", "theme_reflow_breadth", "share(theme_members with return_since_intraday_low > threshold)", "theme membership, 1min bars", "Live-safe after observation window.", "covered_by_or_related: C433", "use_as_component", "板块回流不是只看龙头, 要看修复宽度。"),
    e("divergence_acceptance", "leader_follower_repair_spread", "leader_repair_score - median(follower_repair_score)", "theme membership, leader label, 1min bars", "Cutoff-bounded; theme labels safe needed.", "covered_by_or_related: C434; raw leader_follower_repair_spread", "candidate_component", "龙头先修复、跟风滞后, 对应强弱分层。"),
    e("divergence_acceptance", "first_negative_repair_quality", "I(first_negative_after_streak) * next_session_reclaim_score * volume_shrink_flag", "daily OHLCV, 1min bars, board_count history", "First negative uses T-1; repair live after next-session window.", "raw_material; related C396/C430", "review_for_registry", "首阴反包/首阴修复可单独沉淀。"),
    e("divergence_acceptance", "break_board_exhaustion_rebound", "I(prev_broken_board_count_high) * low_open_repair_score * market_emotion_repair", "limit_pool, market emotion, 1min bars", "Use previous broken-board stats plus current observed repair.", "covered_by_or_related: C323, C395", "candidate_component", "炸板潮后第一批修复代表情绪拐点。"),
    e("divergence_acceptance", "support_failure_bearish_mirror", "I(reclaim_attempt) * I(close_or_cutoff_price_below_vwap) * drawdown_after_reclaim", "1min bars, VWAP", "Live-safe at cutoff; close version T+1.", "covered_by_or_related: C123", "use_as_component", "承接失败也要保留, 用于模型识别风险。"),
    e("divergence_acceptance", "one_word_support_breadth", "theme_one_word_limit_count / theme_limit_up_count", "limit_pool, theme membership", "End-of-day or live after one-word status known.", "covered_by_or_related: C146, C262", "use_as_component", "一字助攻越多, 龙头被资金认可的环境越强。"),
    e("divergence_acceptance", "passive_open_board_beta", "stock_open_board_event * market_or_theme_open_board_rate", "limit_pool intraday events, theme/market stats", "Live-safe after open-board events.", "covered_by_or_related: C250, C320", "use_as_component", "区分个股主动走弱和市场被动炸板。"),

    e("consensus_cycle", "divergence_to_consensus_score", "divergence_event_score_Tminus1 * today_limit_breadth * leader_reseal_strength", "limit_pool, theme membership, 1min bars", "Current-day pieces cutoff-bounded; full-day T+1.", "covered_by_or_related: C396, C433", "candidate_component", "把'分歧转一致'拆成昨日分歧、今日宽度、龙头回封。"),
    e("consensus_cycle", "consensus_to_divergence_risk", "crowding_score * premium_decay * broken_board_fear", "limit_pool, premium history, market emotion", "Use completed history and current observed broken-board events.", "covered_by_or_related: C394, C410, C323", "candidate_component", "一致加速后的衰退风险, 和弱转强相反。"),
    e("consensus_cycle", "market_split_extreme", "limit_up_count_z - limit_down_count_z - broken_board_count_z", "market limit stats", "End-of-day or current snapshot if live limit_pool available.", "covered_by_or_related: C401", "use_as_component", "涨停多但炸板/跌停也多, 是分歧极端。"),
    e("consensus_cycle", "ice_point_repair_age", "days_since_market_ice_point * current_repair_breadth", "market emotion history, limit stats", "Uses prior ice point plus current snapshot.", "covered_by_or_related: C395", "use_as_component", "冰点后的第几天修复, 对弱转强成功率有环境影响。"),
    e("consensus_cycle", "high_low_switch_pressure", "high_board_failure_rate - low_board_success_rate", "limit_pool board height, recent premium stats", "Use prior/frozen lookback; no future labels.", "covered_by_or_related: C394", "use_as_component", "高低切换是龙头退潮和新方向试错的桥。"),
    e("consensus_cycle", "theme_capacity_turnover_fit", "theme_turnover_amount / market_amount adjusted by theme_member_count", "theme membership, daily amount, market total amount", "Daily snapshot by cutoff or T+1.", "covered_by_or_related: C398", "candidate_component", "题材容量和成交额匹配, 避免小题材强行大资金承接。"),
    e("consensus_cycle", "theme_cycle_day_position", "cycle_day_index * normalized_theme_breadth * leader_height", "theme membership, limit_pool, leader height", "Theme label and leader height must be known by cutoff.", "covered_by_or_related: C404", "use_as_component", "同样的分歧在周期第1天和第5天含义不同。"),
    e("consensus_cycle", "regulatory_pressure_countdown", "f(board_height, abnormal_move_notice_count, attention_notice_age)", "announcement/event notices, limit_pool", "Use announcements published before cutoff; otherwise T+1.", "covered_by_or_related: C402", "pipeline_dependent", "高标接近监管窗口时, 龙头气质可能变成风险。"),

    e("board_reseal", "first_seal_time_bucket", "bucket(first_seal_time: early/mid/late) with board_count", "limit_pool first seal time", "Live-safe after seal; full-day T+1.", "covered_by_or_related: C244, C254", "use_as_component", "早封主动性强, 尾盘偷袭要打折。"),
    e("board_reseal", "open_board_count_quality", "open_board_count adjusted by reseal_success and time_to_reseal", "limit_pool intraday events, 1min bars", "Live-safe after events up to cutoff.", "covered_by_or_related: C040, C245, C246", "candidate_component", "炸板次数多不一定坏, 关键是是否快速回封。"),
    e("board_reseal", "late_break_risk_after_long_seal", "I(long_sealed_before_1430) * I(open_board_after_1430) * sell_pressure_score", "limit_pool events, 1min bars", "Live-safe after late break; close version T+1.", "covered_by_or_related: C253, C273", "use_as_component", "长封后尾盘炸板是承接衰竭风险。"),
    e("board_reseal", "attack_volume_at_limit", "amount_in_minutes_before_limit / avg_same_minutes_amount_20d", "1min bars, limit touch time", "Live-safe after limit touch.", "covered_by_or_related: C248, C366", "use_as_component", "上板前攻击量是资金主动性。"),
    e("board_reseal", "seal_replenishment_speed", "increase_in_seal_order_after_open_board / minutes_after_reseal", "limit order/seal snapshots if available", "Requires intraday seal snapshots; otherwise unavailable.", "raw_material: seal_replenishment_speed", "pipeline_dependent", "封单被砸后补单速度更接近真实盘口, 但依赖数据。"),
    e("board_reseal", "board_height_ceiling_break", "I(board_count > recent_market_height_ceiling) * seal_quality", "limit_pool, recent max board height", "End-of-day or live after board confirmed.", "covered_by_or_related: C427, C270", "candidate_component", "突破前高空间板, 是龙头气质的重要一环。"),
    e("board_reseal", "turnover_board_real", "I(not one-word) * turnover_at_limit_session * seal_success_flag", "limit_pool, 1min bars", "Live-safe after turnover board observed.", "covered_by_or_related: C272", "use_as_component", "换手板比一字板更能观察资金承接。"),
    e("board_reseal", "t_board_recognition", "I(open==limit_price) * I(intraday_open_board) * I(close_or_cutoff_near_limit)", "daily/open, 1min bars, limit price", "Live-safe at cutoff if near-limit state known; close version T+1.", "raw_material: t_board_recognition; related C247", "review_for_registry", "T字板/开口回封可作为独立板型。"),

    e("social_attention", "cross_platform_attention_consensus", "low_dispersion(z(platform_mentions)) * total_attention_z", "timestamped Taoguba/Guba/Xueqiu/Bilibili/Douyin mentions", "Only records timestamped before cutoff; otherwise T+1.", "covered_by_or_related: C405", "pipeline_dependent", "多平台共振比单平台刷屏更稳。"),
    e("social_attention", "attention_velocity_24h", "mentions_last_24h / rolling_median_mentions_20d", "timestamped social/video posts", "Publish time <= cutoff only.", "covered_by_or_related: C406, C288", "pipeline_dependent", "短视频/社媒扩散速度, 可作为人气加速度。"),
    e("social_attention", "leader_mention_breadth", "unique_author_count_mentioning_leader / rolling_baseline", "timestamped social posts, stock/theme dictionary", "Post timestamp <= cutoff only.", "covered_by_or_related: C289", "pipeline_dependent", "辨识度不能只看热度, 要看不同作者覆盖。"),
    e("social_attention", "sentiment_overtrading_gap", "social_sentiment_z - turnover_or_amount_z", "social sentiment, daily amount/turnover", "Social timestamp safe; turnover snapshot cutoff-bounded or T+1.", "covered_by_or_related: C286, C365", "candidate_component", "只热不成交可能是嘴炮; 成交超热度可能是隐性资金。"),
    e("social_attention", "hot_concept_exposure_count", "count(active_hot_concepts_mapped_to_stock)", "concept/theme mappings, hot list", "Use only hot list published by cutoff.", "covered_by_or_related: C459", "use_as_component", "多热点标签会提升辨识度, 也可能拥挤。"),
    e("social_attention", "consensus_stock_memory", "historical_attention_rank * current_reactivation_event * current_liquidity_confirm", "historical social attention, event/theme labels, liquidity", "Historical only plus current cutoff-safe event/liquidity.", "covered_by_or_related: C408", "candidate_component", "大众情人/市场记忆的量化版本。"),

    e("risk_mirror", "fake_strength_auction_risk", "I(high_auction_gap) * I(first5_return < 0) * I(volume_not_confirmed)", "auction, 1min bars", "Live-safe after first 5min.", "covered_by_or_related: C319", "use_as_component", "强转弱同样要给模型, 避免只喂正向故事。"),
    e("risk_mirror", "support_failure_after_reclaim", "reclaim_flag * drawdown_after_reclaim * I(price_below_vwap)", "1min bars, VWAP", "Live-safe at cutoff.", "covered_by_or_related: C123", "use_as_component", "弱转强失败版。"),
    e("risk_mirror", "leader_faith_decay", "recent_high_board_big_loss_rate + leader_broken_board_loss", "limit_pool, daily returns, high-board universe", "Use completed recent days; current day after event only.", "raw_material: leader_faith_decay; related C410/C457", "review_for_registry", "龙头信仰失效期会压低所有龙头气质因子。"),
    e("risk_mirror", "overheated_consensus_crowding", "theme_attention_z * theme_turnover_z * premium_decay_risk", "theme attention, turnover, premium history", "Cutoff-bounded; social timestamps required.", "covered_by_or_related: C398, C410, C405", "candidate_component", "一致过热时, 资金认可可能反转成兑现压力。"),
]


def escape_md(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def main() -> None:
    rows = []
    for i, item in enumerate(EXPRESSIONS, start=1):
        row = {"expr_id": f"SC{i:03d}", **item}
        rows.append(row)

    counts = Counter(row["concept"] for row in rows)
    actions = Counter(row["suggested_action"] for row in rows)
    relation_counts = Counter(
        "covered" if row["registry_relation"].startswith("covered") else
        "raw_material" if row["registry_relation"].startswith("raw_material") else
        "new_material" if row["registry_relation"].startswith("new_expression") else
        "other"
        for row in rows
    )

    payload = {
        "meta": {
            "created": date.today().isoformat(),
            "purpose": "expression bank for social short-line concepts: weak-to-strong, leader temperament, capital recognition, divergence acceptance",
            "boundary": "material bank only; no formal factor_registry mutation, no training, no gpu_probe",
            "source_files": SOURCES,
            "total_expressions": len(rows),
            "concept_counts": dict(counts),
            "action_counts": dict(actions),
            "relation_counts": dict(relation_counts),
        },
        "expressions": rows,
    }

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Social Concept Expression Bank 2026-05-19",
        "",
        "Boundary: factor-library material only. No training, no gpu_probe, no model/frozen config changes, and no formal Cxxx registry mutation in this pass.",
        "",
        "Purpose: expand vague short-line language such as weak-to-strong, leader temperament, and capital recognition into computable expressions for later factor comparison. Bad or duplicate expressions can be deleted later without polluting the formal registry.",
        "",
        "## Summary",
        "",
        f"- Total expressions: {len(rows)}",
        f"- Concept counts: {dict(counts)}",
        f"- Suggested actions: {dict(actions)}",
        f"- Relation counts: {dict(relation_counts)}",
        "",
        "## Source Anchors",
        "",
    ]
    for key, value in SOURCES.items():
        lines.append(f"- {key}: {value}")

    lines.extend([
        "",
        "## How To Use This Bank",
        "",
        "- `covered_by_or_related` means the idea is already represented by one or more formal C candidates; use it as an interpretation component, not a new ID.",
        "- `review_for_registry` means the expression looks distinct enough to consider promotion after a stricter duplicate/asof check.",
        "- `pipeline_dependent` means the idea is useful but needs timestamped social, seal-order snapshot, or other extra data before training.",
        "- `use_as_component` means it is best used to explain or combine existing factors, not necessarily to add another standalone candidate.",
        "",
        "## Expression Table",
        "",
        "| Expr | Concept | Name | Formula Sketch | Data Need | Asof | Registry Relation | Action | Note |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        lines.append(
            "| {expr_id} | {concept} | {name} | `{formula}` | {data_need} | {asof_rule} | {registry_relation} | {suggested_action} | {note} |".format(
                **{k: escape_md(v) for k, v in row.items()}
            )
        )

    lines.extend([
        "",
        "## Promotion Shortlist",
        "",
        "These are the highest-signal expressions that are not merely slogans and deserve stricter promotion review before any C466+ write:",
        "",
        "1. `weak_to_strong_volume_efficiency`: weak-to-strong repair per unit amount; guards against rewarding brute-force volume only.",
        "2. `support_absorption_quality`: selloff absorption followed by repair; captures divergence acceptance.",
        "3. `substitute_leader_kawei_score`: replacement leader / catch-up leader card-position score.",
        "4. `t_board_recognition`: T-board/open-board-reseal board type, distinct from generic seal time.",
        "5. `leader_faith_decay`: regime risk mirror for leader strategy failure periods.",
        "6. `low_open_no_new_low_hold`: weak open but no follow-through selling; clean false-weak expression.",
        "7. `institution_hot_money_alignment`: LHB institution and hot-money co-buying as capital consensus.",
        "8. `theme_capacity_turnover_fit`: whether theme capacity can absorb current capital.",
        "",
        "## Do Not Promote Without More Data",
        "",
        "- Social/video expressions require reliable timestamps and stock/theme mapping before same-day use.",
        "- Seal replenishment speed requires actual seal-order snapshots, not just final limit_pool rows.",
        "- LHB/dragon-list expressions are after-close and must be T+1 only.",
        "- Full-day close-based versions must not be used for 14:57 live inference unless rewritten as cutoff-time snapshots.",
    ])

    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {MD_PATH}")
    print(f"Wrote {JSON_PATH}")
    print(f"Total expressions: {len(rows)}")
    print(f"Concept counts: {dict(counts)}")
    print(f"Suggested actions: {dict(actions)}")


if __name__ == "__main__":
    main()
