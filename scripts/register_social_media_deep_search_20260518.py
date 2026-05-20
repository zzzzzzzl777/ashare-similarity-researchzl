"""Register social-media/TGB short-line rule factors.

This is a registry-only update. It does not train, probe, or change model code.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


RUNTIME_REGISTRY = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\factor_registry.json")
DOC_REGISTRY = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\factor_registry.md")
REPORT_PATH = Path(r"C:\Users\zzzzzzl\Desktop\subagent\docs\social_media_factor_search_20260518.md")

BATCH = "candidates_20260518_social_media_deep_search"


def candidate(fid: int, name: str, family: str, priority: str, source_refs: list[str],
              raw_ids: list[str], raw_idea: str, computable_definition: str,
              data_need: str, asof_rule: str, duplicate_check: str,
              engineering_status: str, data_status: str, notes: str = "") -> dict:
    return {
        "factor_id": f"C{fid:03d}",
        "name": name,
        "family": family,
        "priority": priority,
        "source_type": "social_media_deep_search_20260518",
        "source_refs": source_refs,
        "raw_factor_ids": raw_ids,
        "raw_idea": raw_idea,
        "computable_definition": computable_definition,
        "data_need": data_need,
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
                "social_rule_mapped_to_formula",
                "data_need_named",
                "asof_rule_named",
                "duplicate_screened_against_registry_and_code",
                "not_training_result_claim",
            ],
        },
    }


DETAIL = [
    candidate(
        393,
        "tgb_echelon_continuity_gap",
        "limit_theme",
        "P1",
        ["local_tgb_raw_pool", "taoguba_emotion_cycle"],
        ["RAW000022"],
        "Short-line traders use ladder completeness: a clean 1-board to max-board structure is healthier than a broken ladder.",
        "1 - missing_board_heights_count(1..market_max_board_height) / max(market_max_board_height, 1)",
        "limit_pool daily board height by stock; market-wide max_board_height",
        "T-day close for T+1 prediction; for live replay only use board state known before cutoff.",
        "C271 is theme cluster strength; this is market-wide ladder gap/continuity, not theme clustering.",
        "candidate_ready_after_limit_pool_join",
        "limit_pool cache exists; needs canonical board-height join",
    ),
    candidate(
        394,
        "tgb_high_low_switch_pressure",
        "market_cycle",
        "P0",
        ["local_tgb_raw_pool", "taoguba_leader_cycle"],
        ["RAW000133", "RAW000240"],
        "When high boards face break/regulatory pressure and low-position boards broaden, traders describe a high-low switch.",
        "zscore(high_board_fail_rate_3d) + zscore(low_position_limit_breadth_1d) - zscore(high_board_next_day_premium_3d)",
        "limit_pool, board height, next-day premium history, low-position first/second board counts",
        "T-day close using only histories up to T; predicts T+1.",
        "Distinct from C145 theme_height_suppression and C322 compression speed: combines high-board failure with low-position breadth.",
        "candidate_ready_after_limit_pool_join",
        "daily limit_pool data available; needs consistent high/low board bucket definition",
    ),
    candidate(
        395,
        "tgb_ice_point_repair_age",
        "market_emotion",
        "P1",
        ["local_tgb_raw_pool", "taoguba_emotion_cycle"],
        ["RAW000036", "RAW000035"],
        "After consecutive ice-point days, repair probability and participation style change.",
        "consecutive_days(emotion_score <= 0 or (limit_up_count_z < -1 and limit_down_count_z > 1))",
        "daily market limit_up_count, limit_down_count, broken_board_count, emotion_score",
        "T-day close for T+1 prediction.",
        "C119 tracks losing-effect persistence; this tracks ice-point age/reversal setup from market emotion breadth.",
        "candidate_ready_after_market_emotion_join",
        "market emotion fields exist; needs single canonical ice-point threshold",
    ),
    candidate(
        396,
        "tgb_first_divergence_repair_strength",
        "limit_theme",
        "P1",
        ["local_tgb_raw_pool", "taoguba_leader_cycle"],
        ["RAW000072", "RAW000135"],
        "The first divergence day matters only if it repairs strongly instead of expanding into退潮.",
        "first_divergence_flag * close_position * log1p(theme_followup_limit_count)",
        "daily OHLCV, first_divergence_flag, theme membership, same-theme limit-up count",
        "T-day close for T+1 prediction.",
        "first_divergence_flag exists as a raw/code concept; this adds repair strength and theme follow-up intensity.",
        "candidate_ready_after_theme_join",
        "depends on canonical theme membership and first-divergence definition",
    ),
    candidate(
        397,
        "tgb_solo_guide_theme_signal",
        "limit_theme",
        "P2",
        ["local_tgb_raw_pool", "taoguba_leader_cycle"],
        ["RAW000074", "RAW000244"],
        "A lone independent limit-up can hint at a new theme before the theme fully diffuses.",
        "is_singleton_theme_limit_up * novelty_score(theme_or_name_tokens, trailing_20d) * next_day_theme_watch_flag",
        "limit_pool, theme/name token map, recent theme occurrence counts",
        "T-day close; no use of next-day realized returns in feature construction.",
        "Different from C269 sector_first_board_attribute: focuses singleton/novel guide signal rather than first-board category.",
        "needs_theme_text_pipeline",
        "requires reliable theme/name token normalization; keep P2 until pipeline is stable",
    ),
    candidate(
        398,
        "tgb_theme_capacity_turnover_fit",
        "sector_structure",
        "P1",
        ["local_tgb_raw_pool", "taoguba_leader_cycle"],
        ["RAW000110", "RAW000378"],
        "A theme must be large enough to absorb the current market turnover; small themes are more likely to one-day-trip.",
        "theme_turnover_amount / (market_total_amount + eps) divided by sqrt(theme_member_count + eps)",
        "theme membership, per-stock amount, market total amount",
        "T-day close for T+1 prediction.",
        "C232 measures theme uniqueness/concentration; this measures capacity fit relative to market turnover.",
        "candidate_ready_after_theme_join",
        "needs canonical theme membership and per-theme amount aggregation",
    ),
    candidate(
        399,
        "tgb_sector_independence_ex_leader",
        "sector_structure",
        "P1",
        ["local_tgb_raw_pool", "taoguba_leader_cycle"],
        ["RAW000242", "RAW000080"],
        "A theme is healthier if followers can advance without only relying on the leader.",
        "mean(ret_1d of theme_members excluding leader) + log1p(limit_up_count_ex_leader) - abs(leader_ret_1d)",
        "theme membership, leader identification, daily OHLCV, limit_pool",
        "T-day close for T+1 prediction.",
        "Distinct from C144 leader_pull_effect: this is ex-leader independent strength rather than leader pulling followers.",
        "candidate_ready_after_theme_join",
        "needs deterministic leader selection per theme/day",
    ),
    candidate(
        400,
        "tgb_explosive_volume_weak_open",
        "volume_structure",
        "P0",
        ["local_tgb_raw_pool", "xueqiu_shortline_rules"],
        ["RAW000093"],
        "A record-volume day followed by a weak open is treated as failed渡劫/failed acceptance.",
        "is_highest_volume_Nd * max(0, 0.01 - open_gap) * max(0, -first_bar_return)",
        "daily volume, daily open/prev_close, optional first 5min or 1min bar return",
        "T-day 09:35 if first_bar_return is used; otherwise T-day open after 09:25.",
        "Distinct from C118 volume_price_stagnation and C104 breakout: this uses previous record volume plus next-session weak open acceptance.",
        "candidate_ready_after_daily_and_minute_join",
        "needs lookback N lock, suggested N=120; can degrade to open_gap-only if minute bar unavailable",
    ),
    candidate(
        401,
        "tgb_market_split_extreme_divergence",
        "market_emotion",
        "P1",
        ["local_tgb_raw_pool", "taoguba_emotion_cycle"],
        ["RAW000106"],
        "Extreme split: limit-up and核按钮/limit-down coexist, a common ice-point/divergence description.",
        "zscore(limit_up_count) * zscore(limit_down_count + broken_board_count) with positive-part clipping",
        "market limit_up_count, limit_down_count, broken_board_count",
        "T-day close for T+1 prediction.",
        "Code has market_split_signal as a concept; registry did not have a dedicated candidate. This records the audited formula.",
        "code_existing_or_candidate_ready",
        "verify whether existing market_split_signal column should be mapped instead of re-implemented",
    ),
    candidate(
        402,
        "tgb_regulatory_pressure_countdown",
        "announcement_event",
        "P1",
        ["local_tgb_raw_pool", "taoguba_leader_cycle"],
        ["RAW000069", "RAW000070"],
        "Short-line traders discount leaders near abnormal-move/regulatory attention windows.",
        "board_height * recent_abnormal_move_flag_3d + consecutive_limit_days_near_rule_threshold",
        "limit_pool board height, abnormal movement announcements, exchange attention/监管公告 if available",
        "T-day close after公告 publication timestamp; if timestamp not known, shift announcement to T+1.",
        "C233 uses abnormal 200 buy/sell imbalance; this is regulatory timing pressure tied to board height.",
        "needs_announcement_timestamp_pipeline",
        "do not train until announcement timestamps and exchange rule mapping are validated",
    ),
    candidate(
        403,
        "tgb_position_uniqueness_score",
        "limit_theme",
        "P1",
        ["local_tgb_raw_pool", "taoguba_leader_cycle"],
        ["RAW000127"],
        "Unique position in a theme, e.g. sole 20cm second board or sole high-board, often receives scarce attention.",
        "1 / count_same_theme_same_board_height_or_board_type, clipped to [0,1]",
        "theme membership, board height, board type (10cm/20cm/ST), limit_pool",
        "T-day close for T+1 prediction.",
        "Distinct from C270 second_board_confirm_leader: measures scarcity/uniqueness within a theme, not confirmation strength.",
        "candidate_ready_after_theme_join",
        "requires board type classification and theme membership",
    ),
    candidate(
        404,
        "tgb_theme_cycle_day_position",
        "market_cycle",
        "P1",
        ["local_tgb_raw_pool", "taoguba_emotion_cycle"],
        ["RAW000103", "RAW000104"],
        "Cycle day and divergence day have different meanings when breadth/leader height are high vs low.",
        "theme_cycle_day_count * zscore(theme_limit_breadth) / (1 + divergence_day_count)",
        "theme membership, theme limit breadth, leader board height, divergence day counter",
        "T-day close for T+1 prediction.",
        "cycle_day_count/divergence_day_count exist as raw/code ideas; this is their normalized theme-position interaction.",
        "candidate_ready_after_theme_join",
        "needs deterministic main-theme selection",
    ),
    candidate(
        405,
        "social_cross_platform_attention_consensus",
        "social_attention",
        "P2",
        ["taoguba", "xueqiu", "guba", "bilibili_search", "douyin_search"],
        ["RAW001467"],
        "When multiple retail/social platforms mention the same stock or theme together, attention is more durable than a single-platform spike.",
        "mean_rank_zscore(mentions_or_heat across available platforms) - std_rank_zscore(mentions_or_heat across platforms)",
        "timestamped mention/heat counts from taoguba, guba/xueqiu, and optional Bilibili/Douyin video/comment mentions",
        "Use only posts/videos/comments with publish_time <= feature cutoff; otherwise shift to next trading day.",
        "C288 is short-video shock and C289 is leader mention breadth; this is cross-platform consensus/dispersion.",
        "needs_timestamped_social_pipeline",
        "keep P2 until Bilibili/Douyin publish timestamps and symbol/theme extraction are reproducible",
    ),
    candidate(
        406,
        "short_video_theme_velocity_24h",
        "social_attention",
        "P2",
        ["bilibili_search", "douyin_search", "local_social_raw_pool"],
        [],
        "Short-video/live clips can accelerate a theme before broad forum discussion catches up.",
        "delta_24h(video_count_or_comment_count mentioning theme_or_stock) / (rolling_mean_7d + eps)",
        "Bilibili/Douyin video metadata, comments or captions, symbol/theme dictionary, publish timestamps",
        "Use only content published before cutoff; if only crawl time is known, shift to next trading day.",
        "C288 is stock-level attention shock; this is theme-level 24h velocity from short-video channels.",
        "needs_timestamped_social_pipeline",
        "not trainable until short-video crawler produces stable timestamps and de-duplicated theme mentions",
    ),
]


def collect_candidate_ids(data: dict) -> list[str]:
    ids: list[str] = []
    for batch, payload in data.items():
        if not (str(batch).startswith("candidates") and isinstance(payload, dict)):
            continue
        for list_key in ("detail", "p0", "p1", "p2", "blocked", "trainable_this_round", "blocked_this_round"):
            values = payload.get(list_key)
            if isinstance(values, list):
                for item in values:
                    if isinstance(item, dict) and item.get("factor_id"):
                        ids.append(item["factor_id"])
    return ids


def write_report(summary: dict) -> None:
    priority_counts = Counter(item["priority"] for item in DETAIL)
    family_counts = Counter(item["family"] for item in DETAIL)
    lines = [
        "# Social Media Factor Deep Search 2026-05-18",
        "",
        "Scope: Taoguba, local TGB raw pool, Xueqiu/Guba style public discussions, Bilibili/Douyin short-video search surfaces, and prior local social raw records.",
        "",
        "Important boundary: this is registry work only. No training, no gpu_probe, no model config changes.",
        "",
        "## Result",
        "",
        f"- Added candidates: {len(DETAIL)} ({DETAIL[0]['factor_id']} to {DETAIL[-1]['factor_id']})",
        f"- Priority counts: {dict(priority_counts)}",
        f"- Family counts: {dict(family_counts)}",
        "- All new candidates are research_candidate + not_trained.",
        "",
        "## Social Channels Searched",
        "",
        "- Taoguba/TGB local raw pool: 1618 social/TGB records were present in raw_factor_pool_index.",
        "- Taoguba web: emotion cycle, leader cycle, weak-to-strong, divergence/ice-point/retreat concepts.",
        "- Xueqiu/Guba style public discussion: short-line tactics and popularity/attention concepts.",
        "- Bilibili/Douyin search surfaces: repeated the same leader/emotion/auction vocabulary, but stable factorization requires timestamped video/comment metadata.",
        "",
        "## Already Covered / Not Duplicated",
        "",
        "- Existing code or registry concepts cover: board_count, max_board_height, limit_up_count, limit_down_count, broken_board_count, emotion_score, advance_decline_ratio, volume_vs_prev, weak_to_strong auction variants, seal_rate_80_threshold, short_video_attention_shock, social_leader_mention_breadth.",
        "- These were not re-added with new IDs just because a social source mentioned them again.",
        "",
        "## Added Candidates",
        "",
        "| ID | Name | Priority | Family | Data Need | Status |",
        "|---|---|---:|---|---|---|",
    ]
    for item in DETAIL:
        lines.append(
            f"| {item['factor_id']} | {item['name']} | {item['priority']} | {item['family']} | {item['data_need']} | {item['engineering_status']} |"
        )
    lines.extend(
        [
            "",
            "## Data / Pipeline Gaps",
            "",
            "- C405 and C406 need a timestamped social/video pipeline before training.",
            "- C397 needs reliable theme/name token normalization.",
            "- C402 needs announcement timestamps and exchange-rule mapping; otherwise shift announcements to T+1.",
            "- The other candidates can be derived from daily OHLCV, limit_pool, theme membership, auction/minute bars, or already cached market emotion fields once canonical joins are available.",
            "",
            "## Validation",
            "",
            f"- Registry candidate count after write: {summary['registry_candidate_count']}",
            f"- Missing ID check: {summary['missing_ids']}",
            f"- Duplicate ID check: {summary['duplicate_ids']}",
            "- No new candidate is marked passed, final_unseen, or frozen.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_doc_section() -> None:
    section = [
        "",
        "## Social Media Deep Search 2026-05-18",
        "",
        "Purpose: explicitly audit Taoguba, Xueqiu/Guba-style discussion, Bilibili/Douyin short-video surfaces, and the local TGB raw pool for short-line factors without training or model changes.",
        "",
        f"Batch: `{BATCH}`",
        "",
        "| ID | Name | Priority | Family | Status |",
        "|---|---|---:|---|---|",
    ]
    for item in DETAIL:
        section.append(
            f"| {item['factor_id']} | `{item['name']}` | {item['priority']} | {item['family']} | {item['engineering_status']} |"
        )
    section.extend(
        [
            "",
            "Notes:",
            "- Already-covered social/TGB basics were not duplicated: board counts, market emotion counts, weak-to-strong auction variants, and existing short-video/social attention factors.",
            "- C405/C406 are social-pipeline candidates only; do not train until timestamped Bilibili/Douyin/Guba/TGB mention data is reproducible.",
        ]
    )
    with DOC_REGISTRY.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(section) + "\n")


def main() -> None:
    data = json.loads(RUNTIME_REGISTRY.read_text(encoding="utf-8"))
    if BATCH in data:
        raise SystemExit(f"{BATCH} already exists; refusing to duplicate")
    existing_ids = set(collect_candidate_ids(data))
    new_ids = [item["factor_id"] for item in DETAIL]
    overlap = sorted(existing_ids & set(new_ids))
    if overlap:
        raise SystemExit(f"ID overlap: {overlap}")

    data[BATCH] = {
        "search_date": "2026-05-18",
        "search_round": "social_media_deep_search",
        "scope": [
            "taoguba",
            "local_tgb_raw_pool",
            "xueqiu_guba_public_discussion",
            "bilibili_short_video_search",
            "douyin_short_video_search",
        ],
        "source_evidence": {
            "local_tgb_raw_pool": r"E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json",
            "taoguba_emotion_cycle": "https://www.tgb.cn/talk/talkSeq/101",
            "taoguba_market_emotion": "https://m.tgb.cn/a/2iGj9oXK5Ro",
            "taoguba_leader_cycle": "https://m.tgb.cn/a/1R8S13VHpIk",
            "xueqiu_shortline_rules": "https://xueqiu.com/9454304489/327889059",
            "sina_weak_to_strong": "https://finance.sina.cn/2025-02-20/detail-inemcpfi9152101.d.html?from=wap",
            "bilibili_search": "searched: A股 短线 龙头战法 情绪周期 集合竞价 弱转强 打板",
            "douyin_search": "searched: A股短线 龙头战法 情绪周期 打板 竞价",
        },
        "selection_gate": [
            "social idea must map to explicit formula",
            "must name data need and asof rule",
            "must not duplicate existing registry or code-level factor",
            "if social/video data is needed, mark as pipeline candidate, not ready-to-train",
        ],
        "total": len(DETAIL),
        "by_priority": dict(Counter(item["priority"] for item in DETAIL)),
        "by_family": dict(Counter(item["family"] for item in DETAIL)),
        "detail": DETAIL,
        "deferred_or_rejected": [
            {
                "idea": "raw board_count/max_board_height/limit_up_count/emotion_score",
                "reason": "already covered by code or existing market emotion columns; not duplicated",
            },
            {
                "idea": "pure trader slogan/position management rules",
                "reason": "cannot be mapped to stock-date scalar without adding subjective NLP labels",
            },
            {
                "idea": "generic Bilibili/Douyin popularity without timestamps",
                "reason": "kept as pipeline-only C405/C406 until publish timestamps and mention extraction are stable",
            },
        ],
    }

    meta = data.setdefault("meta", {})
    batches = meta.setdefault("candidate_batches", [])
    if BATCH not in batches:
        batches.append(BATCH)
    meta["updated"] = "2026-05-18"
    meta["latest_candidate_batch"] = BATCH
    all_ids = collect_candidate_ids(data)
    numeric_ids = sorted(int(fid[1:]) for fid in all_ids if isinstance(fid, str) and fid.startswith("C") and fid[1:].isdigit())
    missing = [f"C{i:03d}" for i in range(1, max(numeric_ids) + 1) if i not in numeric_ids]
    duplicates = [fid for fid, count in Counter(all_ids).items() if count > 1]
    meta["registry_candidate_count"] = len(set(all_ids))
    meta["social_media_deep_search_20260518"] = {
        "added_count": len(DETAIL),
        "id_range": [DETAIL[0]["factor_id"], DETAIL[-1]["factor_id"]],
        "priority_counts": dict(Counter(item["priority"] for item in DETAIL)),
        "family_counts": dict(Counter(item["family"] for item in DETAIL)),
        "social_channels": ["taoguba", "xueqiu/guba", "bilibili", "douyin", "local_tgb_raw_pool"],
        "pipeline_only": ["C405", "C406"],
    }

    RUNTIME_REGISTRY.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    append_doc_section()
    write_report(
        {
            "registry_candidate_count": meta["registry_candidate_count"],
            "missing_ids": missing,
            "duplicate_ids": duplicates,
        }
    )

    print(f"added {len(DETAIL)} candidates: {DETAIL[0]['factor_id']}-{DETAIL[-1]['factor_id']}")
    print(f"registry_candidate_count={meta['registry_candidate_count']}")
    print(f"missing_ids={missing}")
    print(f"duplicate_ids={duplicates}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
