# All-Channel Factor Expansion 2026-05-18

Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.

## Search Surface

- Local raw pool and raw-to-registry queues: ETF flow, PCR/OI, IV skew, convertible forced redemption, margin intensity, news surge.
- Broker/report direction: price-limit industry/network spillover, ETF flow, option sentiment, convertible-bond short-line pressure, margin/short-selling behavior.
- Academic/open-source direction: social/news sentiment, qlib/alpha technical libraries, price-limit network ideas.
- Social/TGB direction: no extra pure-text idea was registered unless it could be reduced to a stock-date scalar with data and asof fields.

## Result

- Added candidates: 9 (C417 to C425)
- Priority counts: {'P1': 4, 'P2': 5}
- Family counts: {'etf_flow': 1, 'option_market': 2, 'convertible_bond': 2, 'limit_network': 1, 'news_attention': 1, 'margin_derivative': 2}
- All additions remain `training_status=not_trained` and `lockbox_role=research_candidate`.

## Added Candidates

| ID | Name | Priority | Family | Frequency | Data Need | Asof / Caveat |
|---|---|---:|---|---|---|---|
| C417 | etf_constituent_flow_pressure | P1 | etf_flow | daily | ETF constituent weights, ETF net flow or share change, ETF NAV/close, stock float market value | Use after-close ETF/fund data for T+1 unless constituent flow timestamps prove same-day availability. |
| C418 | option_pcr_market_sentiment | P2 | option_market | daily | option daily volume/open-interest by underlying, option basic mapping, market or ETF underlying mapping | Use opt_daily after close for next-day prediction; intraday option data must be separately timestamped before same-day use. |
| C419 | option_iv_skew_risk | P2 | option_market | daily | option implied volatility or fields sufficient to compute IV, option delta/moneyness, underlying mapping | Use only option fields published by cutoff; if IV is computed after close, this is T+1 only. |
| C420 | convertible_forced_redemption_pressure | P1 | convertible_bond | daily | convertible-stock mapping, conversion price, stock daily close, convertible status | Use stock close and conversion-price information known by T close; for intraday use, replace close with cutoff price and mark proxy. |
| C421 | convertible_equity_linkage_premium_gap | P2 | convertible_bond | daily | convertible daily price, conversion value/premium, underlying stock return | Use after-close convertible daily data for next-day prediction unless intraday convertible quotes are timestamped. |
| C422 | limit_spillover_network_traction | P1 | limit_network | daily_or_1457_proxy | limit_pool, industry/theme membership, co-limit/correlation network, daily returns | Use only peer limit events known by cutoff; for full T close signals use next-day prediction. |
| C423 | news_surge_sentiment_event_factor | P2 | news_attention | event_or_daily | timestamped stock news count, NLP sentiment, stock-symbol mapping | For same-day use, include only news items whose event_time is <= cutoff; otherwise shift to T+1. |
| C424 | margin_buy_intensity_relative | P1 | margin_derivative | daily | margin_detail financing buy amount, daily amount, stock identifier mapping | Margin data is normally after-close; use for next-day prediction unless same-day timestamp is proven. |
| C425 | short_selling_pressure_ratio | P2 | margin_derivative | daily | margin short-selling volume/amount fields and daily volume/amount | Use after-close margin data for next-day prediction; same-day use requires timestamped margin updates. |

## Explicit Non-Adds

- Pure generic Alpha101/Alpha191 formulas were not re-added because the registry already has technical-indicator bank coverage unless a formula has distinct short-line context.
- Untimestamped social/video slogans were not registered as same-day factors.
- True L2/tick order-book queue and cancellation factors remain outside the registry until stable data fields exist.
- Any factor whose only definition was `current_price = close` or a direct alias of an existing feature was rejected as duplicate/non-factor.

## Ten Checks

1. existing C001-C416 duplicate-name screen
2. existing C001-C416 duplicate-formula screen
3. raw pool no-match review
4. ETF source and data-field feasibility check
5. option PCR/OI/IV data-field feasibility check
6. convertible-bond source and stock mapping check
7. margin/short-selling field feasibility check
8. news/social timestamp and asof check
9. 14:57 vs T close vs T+1 leakage classification
10. registry integrity check after write

## Validation

- Total candidates after write: 425
- Missing IDs: []
- Duplicate IDs: []
- Unsafe status count: 0
