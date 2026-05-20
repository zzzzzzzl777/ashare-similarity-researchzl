# Social Concept Saturation Factor Search 2026-05-19

Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.

This pass deepened the social short-line vocabulary around weak-to-strong, leader temperament, capital recognition, divergence acceptance, reseal quality, and same-height competition. It also rechecked all prior candidate batches and the local raw pool before promoting anything.

Literal whole-internet exhaustion is impossible, so this is a reproducible saturation pass: broad search, local/raw cross-check, strict duplicate/asof screening, then ten validation checks.

## Sources Rechecked

- local_raw_pool: E:\ashare_similarity_runtime\data\reports\prediction\raw_factor_pool_index.json
- expression_bank: E:\ashare_similarity_runtime\data\reports\prediction\social_concept_expression_bank_20260519.json
- local_tgb_factor_research: C:\Users\zzzzzzl\Desktop\subagent\docs\tgb_factor_research.md
- taoguba_weak_to_strong_deep_dive: https://m.tgb.cn/a/2ndkehIFDw7
- taoguba_weak_to_strong_truth_false: https://m.tgb.cn/a/2rH18eikaA2
- taoguba_divergence_to_consensus: https://www.tgb.cn/a/2rlgmUsdvAp-1
- taoguba_leader_terms: https://m.tgb.cn/a/2lsgqb9S9S7
- taoguba_leader_system: https://m.tgb.cn/a/1T0ZCzlrrA9
- xueqiu_weak_to_strong_auction: https://xueqiu.com/1410434827/240516838
- bilibili_call_auction: https://www.bilibili.com/video/BV1qV4y1Z7Ni/
- bigquant_hf_factor_summary: https://bigquant.com/square/paper/8fcfe5cd-cdd0-4c5e-af7c-f97fe0a15fa3
- bigquant_auction_fields: https://mf.bigquant.com/data/datasources/cn_stock_factors_auction
- tushare_minute_data: https://tushare.pro/document/2?doc_id=370

## Added Candidates

Added: 10 (C466 to C475)

| ID | Name | Priority | Family | Frequency | Data Need | Asof / Caveat |
|---|---|---:|---|---|---|---|
| C466 | false_weak_no_new_low_hold | P0 | weak_to_strong_intraday | 1min_or_cutoff | 1min bars, daily prev_close/open, optional auction gap | Live-safe after the chosen observation window (e.g. 10:30 or 14:57). Do not use later lows after cutoff. |
| C467 | weak_to_strong_reclaim_efficiency | P0 | weak_to_strong_intraday | 1min_or_cutoff | 1min bars with minute amount, prev_close or VWAP reclaim event | Live-safe only after the reclaim event has occurred before cutoff. Full-day reclaim version is T+1. |
| C468 | morning_false_weak_reversal_score | P1 | weak_to_strong_intraday | 1min_morning | 1min bars, intraday VWAP | Use cutoff >= 10:30. Earlier live cutoffs must use a shorter locked observation window. |
| C469 | divergence_absorption_efficiency | P0 | divergence_acceptance | 1min_or_cutoff | 1min bars, minute amount, selloff window selector | Live-safe after the selloff and recovery window both end before cutoff. |
| C470 | substitute_leader_kawei_score | P1 | leader_rotation | daily_or_cutoff | limit_pool board_count history, theme membership, prior leader labels, first seal time | Use only board state and seal events known by cutoff; full-day leader rotation version is T+1. |
| C471 | first_negative_repair_quality | P1 | leader_repair | daily_plus_1min | daily OHLCV, board_count history, 1min bars for repair, volume baseline | The first-negative flag uses completed T-1 data; today's repair features must be cutoff-bounded. |
| C472 | t_board_reseal_recognition | P1 | limit_board_type | 1min_or_cutoff | daily open, limit price, 1min bars, limit_pool open-board/reseal state | Live-safe at cutoff if all open-board/reseal state is observed before cutoff; close-based version is T+1. |
| C473 | leader_faith_decay_regime | P1 | market_emotion | daily_history | limit_pool high-board universe, daily returns, broken-board events, next-session open/premium history | Use only completed prior sessions for regime score. If same-day broken-board events are included, they must be cutoff-bounded. |
| C474 | same_height_competition_pressure | P1 | limit_theme | auction_or_cutoff | limit_pool board_count, auction features, first seal time, theme membership | Use auction/limit states known by cutoff. Full-session same-height comparison is T+1. |
| C475 | weak_to_strong_no_gap_fill_followthrough | P1 | weak_to_strong_auction | auction_plus_first30 | prior weak-context flags, auction/open, 1min bars, prev_close | Live-safe after 10:00 or locked first-30-minute cutoff. Do not use later intraday lows. |

## Prior Candidate Review

- The 73-expression social concept bank was rechecked. Only 10 were promoted; 35 remain interpretation components, 24 remain candidate components needing tighter formulas, 6 remain pipeline-dependent, and the rest are covered by existing C IDs.
- Local raw pool was not blindly promoted: pure slogans, trade rules, NLP-only ideas, true L2 queue-only concepts, and aliases of existing C001-C465 were rejected or deferred.
- Existing weak-to-strong, leader, LHB, limit-board, auction, and social candidates were treated as canonical where they already cover the concept.

## Rejected / Deferred Buckets

- Pure slogans: 龙头气质, 资金认可, 合力, 辨识度 without a computable field/time rule.
- Existing coverage: generic seal time, generic board height, generic VWAP reclaim, generic LHB net buy, generic social mention breadth.
- Data/pipeline gaps: seal-order replenishment snapshots, timestamped video/social feeds, true L2 queue/cancel/order-book features.

## Ten Validation Checks

1. JSON parse OK.
2. IDs continuous from C001 to latest.
3. No duplicate factor_id.
4. No duplicate name.
5. Every new item has computable_definition.
6. Every new item has data_need and required_columns.
7. Every new item has asof_rule.
8. Every new item is not_trained.
9. Every new item is research_candidate.
10. No passed/final_unseen/frozen claims.

Validation result before write: missing=[], duplicate_ids=[], duplicate_names=[], unsafe=[]
