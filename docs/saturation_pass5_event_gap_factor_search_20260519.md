# Saturation Pass 5 Event-Gap Factor Search 2026-05-19

Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.

This pass expanded search across broker-report/event ideas, local raw pool, Tushare official API coverage, and prior saturation docs. Literal whole-web exhaustion is impossible, so this report records a reproducible saturation pass and strict non-add reasons.

Added candidates: 6 (C460 to C465)

| ID | Name | Priority | Family | Frequency | Data Need | Asof / Caveat |
|---|---|---:|---|---|---|---|
| C460 | buyback_plan_strength | P1 | buyback_event | event_daily | repurchase announcement rows, daily close, float market value | Use ann_date/rec_time if available; otherwise treat announcement rows as after-close and use from next tradable session only. |
| C461 | buyback_execution_pressure | P1 | buyback_event | event_daily | repurchase implementation/completion rows and daily amount | Use only implementation/completion announcements whose ann_date or rec_time is <= cutoff; no same-day use without timestamp. |
| C462 | buyback_price_support_gap | P2 | buyback_event | daily | active repurchase plan high_limit/exp_date and daily close | Only active plans announced before cutoff may be used; expire at exp_date or completion announcement. |
| C463 | esop_discount_incentive_gap | P2 | employee_stock_ownership | event_daily | announcement title/pdf extraction for employee stock ownership plan, purchase price, amount, lock-up; daily close and float_mv | Use ann_date/rec_time; if PDF parsing is post-close only, use T+1. Never use completion details before announcement time. |
| C464 | private_placement_break_repair_gap | P2 | private_placement_event | event_daily | private placement announcement or issuance details, placement price/amount, daily close, float_mv | Use only placement terms announced before cutoff; if parsed from announcements after close, use next tradable session. |
| C465 | ma_restructure_announcement_surprise | P2 | ma_restructure_event | event_daily | announcement title/pdf extraction, optional suspend/resume flag, deal size, industry relation, daily close/float_mv | Use only announcements and suspend/resume records available by cutoff; resumption-day gap features must use open/observed minute data only. |

## Search Surfaces Checked

- Local registry C001-C459 keyword scan: buyback/repurchase/esop/private placement/MA/restructuring had no registered candidate coverage.
- Local raw pool: buyback RAW000612/RAW002576/RAW002577, ESOP RAW000613, private placement RAW000610/RAW000614/RAW001130/RAW002674, M&A RAW000611/RAW001129/RAW002673.
- Web/API evidence: Tushare `repurchase`, `anns_d`, and `suspend_d` provide the minimum fields or source documents needed to engineer the event families.
- Prior minute, limit-pool, LHB, option, ETF, theme, social, and high-frequency surfaces were rechecked as duplicate-heavy, so no extra C466+ was added from those families in this pass.

## Non-Adds After Ten Checks

1. Generic low-open/high-open wording: already covered by auction/gap families such as weak-to-strong, gap fill, opening premium, and auction breadth.
2. Generic seal-order/board wording: already covered by seal amount/time/open-count/board-height families, or requires true L2 order book.
3. Generic minute HCVP/LCVP/VPIN/jump wording: already covered by C356-C387 and C437-C445/C455-C456.
4. Generic LHB/hot-money wording: already covered by C042/C229/C328/C345-C346/C412-C414/C444-C445.
5. Unlock/holdertrade/block-trade wording: already covered by C198-C205, C221, C329-C332, C347-C348, C370.
6. Options/ETF/convertible-bond tails: already covered by C417-C459 unless new data fields are confirmed.
7. Announcement concepts without formula or parseable fields: deferred, not registered.
8. Pure strategy rules without scalar feature definition: rejected.
9. Future-return/next-day-outcome labels: rejected unless recast as point-in-time state variables.
10. Raw aliases that only rename implemented columns: rejected as duplicates.

## Validation

- Total candidates after write: 465
- Missing IDs: []
- Duplicate IDs: []
- Unsafe status count: 0
