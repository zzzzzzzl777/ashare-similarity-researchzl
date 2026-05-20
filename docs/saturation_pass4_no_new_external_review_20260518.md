# Saturation Pass 4 No-New External Review 2026-05-18

Purpose: continue the all-channel short-line factor search after C426-C459 and verify whether newly searched or newly available API directions expose additional registry-ready factors.

Scope: registry management only. No training, no `gpu_probe`, no model code changes, no `frozen_forward_config` changes.

## Result

No new factor IDs were added in this pass.

Current registry remains C001-C459, with the latest registered batch:

- `candidates_20260518_saturation_pass3_tail`
- Added in the immediately preceding two passes: C426-C459, 34 candidates

## External Search Surfaces Rechecked

The pass rechecked four source groups:

| Surface | Search focus | Outcome |
|---|---|---|
| Broker / academic / paper-style reports | high-frequency price-volume, microstructure, CPV/HCVP/LCVP, ETF/option/convertible/financing channels | Incremental ideas were duplicates of existing registry families or required Level-2 order book / tick-order fields. |
| Open-source / GitHub style factor libraries | Qlib/Alpha158/Alpha360 style OHLCV operators, technical indicator banks, formulaic alphas | Existing registry already covers the usable route via C194-C197, C340, C391-C392 and many daily/minute price-volume variants. |
| Social / community trading language | Taoguba, Xueqiu, Bilibili/Douyin-style dragon-head, weak-to-strong, auction, re-seal, theme reflow | Most new terms normalize to existing limit/auction/theme/social candidates; vague slogan-only items were rejected. |
| Newly available Tushare API channels | block_trade, stk_holdertrade, pledge_stat, forecast_vip, hsgt_top10, ccass_hold, ggt_daily, moneyflow_ind, index_global, shibor, stk_factor_pro | Already represented by existing registered candidate families. |

## API Coverage Check

The newly highlighted APIs are not empty gaps in the factor library. They already map to existing candidate families:

| API / data channel | Existing registry coverage |
|---|---|
| `block_trade` | C198-C201, C221, C329-C330, C370 |
| `stk_holdertrade` | C205, C347-C348 |
| `pledge_stat` | C204, C332 |
| `forecast_vip` | C081, C208, C333, C350 |
| `hsgt_top10` | C061, C210, C335, C368, C388 |
| `ccass_hold` | C080, C211, C336, C389 |
| `moneyflow_ind_dc` / `moneyflow_ind_ths` | C053, C088, C120, C214-C215, C337, C390 |
| `index_global` | C128, C217, C341 |
| `shibor` | C079, C218 |
| `stk_factor_pro` | C194-C197, C391-C392 |

## Rejection / Defer Rules Reconfirmed

Do not register candidates that need one of these unavailable or unsafe inputs:

- Level-2 order book depth, bid/ask queue position, quote imbalance, cancellation rate, hidden order inference.
- True tick-by-tick order flow or per-order aggressor side unless a timestamped data source is actually landed.
- Same-day post-close LHB, top-list, hsgt_top10, option daily, ETF premium, or convertible fields for 14:57 live replay unless source timestamps prove availability before cutoff.
- Slogan-only social concepts without a formula, stock-date key, and data source.
- Direct aliases of existing candidate families, especially auction gap, re-seal speed, board height, high/low price bucket, volume spike, and technical indicator consensus variants.

## Validation Snapshot

After rebuilding the raw pool index:

| Check | Result |
|---|---|
| Registry candidate count | 459 |
| Max ID | C459 |
| ID continuity | C001-C459 continuous |
| Duplicate factor_id | 0 |
| Unsafe true passed/final/frozen flags | 0 |
| C426-C459 required fields | complete |
| Raw pool records | 3,075 |
| Raw records not mapped to registry | 2,536, mostly duplicates, vague concepts, Level-2/tick/order-book dependencies, or unreviewed low-confidence text |

## Practical Next Step

Do not add C460 just for coverage. The next useful action is data/engineering work for already-registered candidates:

1. Prioritize 1min candidates C371-C388, C435-C443, C455-C456 now that 1min cache exists.
2. Backfill and timestamp-check option / ETF / convertible candidates C431-C432, C450-C454, C458.
3. Continue social/search pipeline only if timestamped Guba/Baidu/news data is available for C423, C446-C447.
4. Keep raw-only backlog as evidence, not registry, until a computable formula and asof rule are clear.
