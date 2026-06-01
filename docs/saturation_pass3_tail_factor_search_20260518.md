# Saturation Pass 3 Tail Factor Search 2026-05-18

Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.

Added candidates: 9 (C451 to C459)

| ID | Name | Priority | Family | Frequency | Data Need | Asof / Caveat |
|---|---|---:|---|---|---|---|
| C451 | option_unusual_volume_shock | P2 | option_market | daily | option daily volume by underlying and option type; underlying to stock/ETF mapping | Use after-close opt_daily for T+1 unless intraday option volume is timestamped. |
| C452 | option_iv_rv_spread | P2 | option_market | daily | option implied volatility, underlying realized volatility | Use only IV fields available by date; realized volatility must not include future returns beyond T. |
| C453 | option_iv_term_structure_inversion | P2 | option_market | daily | option IV by maturity and underlying | Use after-close option chain data for T+1 unless timestamped intraday option chain is available. |
| C454 | etf_premium_discount_arbitrage_pressure | P1 | etf_flow | daily_or_intraday_if_iopv | ETF premium/discount or IOPV, ETF holdings weights, constituent stock mapping | Daily ETF premium is T+1; intraday IOPV premium can be same-day only if timestamped before cutoff. |
| C455 | last_5min_return_pressure | P1 | minute_tail | 1min | 1min bars close | At 14:57 use the last observed 5-minute window ending at or before cutoff; never use post-cutoff bars. |
| C456 | intraday_return_curve_shape | P1 | minute_path | 1min | 1min bars close and fixed intraday windows | Only include windows completed by cutoff; missing future windows must be masked for live replay. |
| C457 | t_plus1_limit_sell_pressure | P1 | limit_board | daily_or_1min | limit_pool prior-day limit-up flag and current turnover/auction/minute volume | Use prior-day limit flag and current cutoff-bounded turnover/auction volume. |
| C458 | index_option_expiry_week_gate | P2 | option_market_regime | daily | trading calendar, option expiry calendar, market volatility/PCR state | Expiry calendar is known in advance; market state inputs must obey their own asof rules. |
| C459 | hot_concept_count_exposure | P2 | theme_attention | daily_or_cutoff | stock-theme membership and theme heat score | Use only theme heat available by cutoff; full-day theme heat is T+1. |

## Non-Adds After Tail Review

- Generic technical aliases such as Bollinger position and MA distance remain covered by the technical bank.
- Basic board-count, seal-time, one-word-board, and open-count aliases are already represented by C-series limit-board features.
- L2/tick/orderbook items remain blocked.

## Validation

- Total candidates after write: 459
- Missing IDs: []
- Duplicate IDs: []
- Unsafe status count: 0
