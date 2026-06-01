# Global Saturation Final Factor Search 2026-05-18

Scope: expanded all-channel short-line factor search and strict registry screening.

Boundary: factor-library management only. No training, no gpu_probe, no model/frozen config changes.

## Search Surface

- Local raw pool: 3075 records from TGB/social, short-line, and exploration documents.
- Social/TGB/short video: Taoguba-style emotion/leader rules, Xueqiu/Guba style discussion, Bilibili/Douyin search surfaces.
- Broker reports: high-frequency price-volume, smart money, price-limit industry reversal, LHB/seat behavior.
- Academic papers: lottery preference/MAX-IVOL-skew, investor sentiment/overtrading, price limit dynamics, wavelet/time-frequency and volume-memory ideas.
- GitHub/open-source: alpha101/alpha191/qlib-style formula libraries were checked; generic duplicates were not re-added.

## Result

- Added candidates: 10 (C407 to C416)
- Priority counts: {'P1': 6, 'P2': 4}
- Family counts: {'capital_memory': 2, 'behavioral_lottery': 1, 'market_emotion': 1, 'industry_rotation': 1, 'lhb_seat': 2, 'lhb_market': 1, 'minute_hf': 1, 'volume_memory': 1}
- All additions are `training_status=not_trained` and `lockbox_role=research_candidate`.

## Added Candidates

| ID | Name | Priority | Family | Frequency | Data Need | Asof / Caveat |
|---|---|---:|---|---|---|---|
| C407 | capital_memory_reactivation_score | P1 | capital_memory | daily_or_event | event/theme labels, historical event leaders, daily OHLCV, limit_pool; optional social/LHB confirmation | Use only event/theme labels and leader history published or known by cutoff; if event timestamp is unknown, shift to T+1. |
| C408 | consensus_hot_stock_memory_score | P2 | capital_memory | daily | timestamped social/stock-bar mentions, LHB appearances, limit_pool board height history | For same-day use, only include social posts before cutoff; if social timestamps are missing, shift to T+1. |
| C409 | lottery_max_ivol_skew_pressure | P1 | behavioral_lottery | daily | daily returns; market/industry benchmark return for idiosyncratic residuals; optional 1min realized variant | At T close use returns through T; for 14:57 replay use price_1457 proxy and mark proxy version separately. |
| C410 | limit_premium_decay_regime | P1 | market_emotion | daily_or_1457_proxy | limit_pool yesterday-limit basket, daily close or 14:57 proxy close, market calendar | For T+1 training use T close; for 14:57 live use price_1457 proxy and never use final close after cutoff. |
| C411 | industry_limit_reversal_pressure | P1 | industry_rotation | daily | industry membership, limit_pool, daily returns for industry members | Use only limit events and returns available by T close; for T+1 prediction map the T industry score to member stocks. |
| C412 | multi_seat_buy_strength | P1 | lhb_seat | after_close_daily | LHB top buy seats, buy amount by seat, daily amount, optional known-seat catalog | LHB is normally after-close; only use for T+1 or later unless exact intraday disclosure timestamp proves availability. |
| C413 | famous_seat_repeat_visit_score | P1 | lhb_seat | after_close_daily | LHB seat history, stock/theme mapping, historical post-LHB forward returns for prior events | Historical forward returns may only be used for past seat events; today's LHB signal is T+1 after disclosure. |
| C414 | active_seat_absence_market_risk | P2 | lhb_market | after_close_daily | market-wide LHB seat appearances and rolling active-seat catalog | After-close market-wide feature; use for next trading day only. |
| C415 | intraday_wavelet_highfreq_energy_ratio | P2 | minute_hf | 1min | 1min bars: close; optional amount/volume sequence for parallel volume wavelet energy | Use only bars <= cutoff; post-14:57 bars must not enter live replay features. |
| C416 | volume_spike_memory_interval | P2 | volume_memory | daily_or_1min | daily volume or 1min volume history; spike threshold based on rolling volume-volatility z-score | For 14:57 version, compute intervals only using minute bars <= cutoff; daily version uses T close for T+1. |

## Deferred / Rejected Buckets

- L2/tick/order-book cancellation and queue-depth factors: rejected until stable L2/tick fields exist; minute proxies already exist in C387 and related minute factors.
- Pure slogan / discretionary trading rules: rejected unless they map to a reproducible stock-date scalar.
- Generic technical libraries: not duplicated because C194/C391/C392 already cover the large technical-indicator bank.
- Untimestamped social/video heat: kept as pipeline-only ideas, not same-day trainable signals.

## Ten Saturation Checks

1. C001-C406 name/formula duplicate screen
2. local raw pool leftovers (`capital_memory`, `LOTT`, LHB seat variants, limit premium)
3. TGB/social rule pass
4. Bilibili/Douyin timestamp feasibility pass
5. broker report pass: high-frequency, limit board, LHB, industry reversal
6. academic paper pass: lottery, price limits, sentiment, wavelet, volume memory
7. GitHub/open-source pass: alpha101/alpha191/qlib technical libraries
8. data availability pass: daily, limit_pool, LHB, 1min, social, event/theme labels
9. asof/leakage pass: 14:57 vs T close vs after-close T+1
10. registry integrity pass: contiguous IDs, no duplicates, not trained/frozen/final

## Validation

- Registry candidate count after write: 416
- Missing ID check: []
- Duplicate ID check: []
- Unsafe status check: 0
