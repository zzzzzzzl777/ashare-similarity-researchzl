# Factor Training Matrix — All Factors — 2026-05-07

**Source**: `factor_registry.json` (auto-generated, not hand-written)  
**Total factors**: 173  
**Trainable now**: 8  
**Blocked**: 165  

---

## 1. Currently Trainable Factors (8)

| Factor ID | Name | Column | Family | 14:57 Tag | Round Status |
|-----------|------|--------|--------|-----------|--------------|
| C004 | ff_adjusted_flow | `tushare_ff_adjusted_flow` | moneyflow_derivative | post_close_only | round5_current |
| C009 | main_force_divergence | `tushare_main_force_divergence` | moneyflow_derivative | post_close_only | round5_current |
| C011 | auction_open_vwap_ratio | `tushare_auction_open_vwap_ratio` | stk_auction_tier1b | realtime_1457_safe | round5_current |
| C133 | last_30min_return | `tushare_last_30min_return` | minute_bar | close_proxy_required | round4_tested_no_freeze |
| C134 | first_15min_volume_concentration | `tushare_first_15min_volume_ratio` | minute_bar | close_proxy_required | round4_tested_no_freeze |
| C136 | intraday_volatility | `tushare_intraday_volatility` | minute_bar | close_proxy_required | round4_tested_no_freeze |
| C137 | up_volume_ratio | `tushare_up_volume_ratio` | minute_bar | close_proxy_required | round4_tested_no_freeze |
| C138 | high_time_position | `tushare_high_time_pct` | minute_bar | close_proxy_required | round4_tested_no_freeze |

### Training Notes

- **C004/C009**: Already in baseline as part of Tushare moneyflow tier. These are the control factors.
- **C011**: Auction data available at 9:25, clean for 14:57 real-time use.
- **C133-C138**: Round 4 tested all combinations, concluded NO_FREEZE. Including in this round's matrix for completeness but not expecting different results unless pipeline changes.

---

## 2. Blocked Factors — Summary by Reason

| Blocked Reason | Count | Action Required |
|----------------|:-----:|-----------------|
| candidate_not_engineered | 133 | Must implement feature column first |
| unknown_status | 11 | Needs status classification |
| needs_validation | 10 | Needs coverage/asof validation |
| needs_formula_correction | 3 | C005/C006/C008 — need real close |
| needs_engineering | 3 | Engineering work required |
| implementation_mismatch | 2 | C001/C010 — formula vs code mismatch |
| needs_data_check | 2 | C013/C015 — data availability check |
| blocked_until_outlier_guard | 1 | C135 — max=109.6 unguarded |

---

## 3. Priority Engineering Group (Daily OHLCV)

These factors should be engineered first for Round 5 training:

| Factor ID | Name | Data Source | Complexity | Recommended |
|-----------|------|-------------|:----------:|:-----------:|
| C154 | price_vs_cost | daily OHLCV + MA | Low | YES |
| C156 | abnormal_3d_deviation | daily OHLCV | Low | YES |
| C157 | VOL_GAIN | daily volume | Low | YES |
| C158 | INV_t | daily volume/turnover | Low | YES |
| C159 | ASR | daily price structure | Low | YES |
| C161 | ILLIQ_classic | daily price + volume | Low | YES |
| C162 | ATO | daily open/close volume | Low | YES |

---

## 4. Formula-Lock Group (Cannot Train Until Locked)

| Factor ID | Name | Blocking Issue |
|-----------|------|----------------|
| C155 | cap_ratio | sector leader definition not locked |
| C160 | chip_weight | rolling window/turnover unit not locked |
| C163 | TAM | beta estimation method not locked |
| C168 | vol_premium | sector volume source not locked |
| C169 | max_theme_weight | theme weight source not locked |
| C170 | hhi_theme_concentration | theme weight source not locked |

---

## 5. Limit-Pool / Market-Breadth Group (Needs API/AsOf Verification)

| Factor ID | Name | Dependency |
|-----------|------|------------|
| C153 | nuclear_ratio | limit_pool |
| C164 | new_leader_emerge | limit_pool |
| C165 | need_second_seal | limit_pool + intraday |
| C166 | late_seal_ratio | seal timestamp |
| C167 | early_seal_ratio | seal timestamp |
| C171 | new_high_strength | historical API |
| C172 | recent_limit_frequency | historical API |
| C173 | true_limit_up_ratio | historical API |

---

## 6. Spot-Check Verification

Random 20 factors verified against registry:

| Factor | Matrix Status | Registry Status | Match |
|--------|:------------:|:---------------:|:-----:|
| C001 | blocked (impl_mismatch) | implementation_mismatch | YES |
| C004 | trainable | verified_engineerable | YES |
| C009 | trainable | verified_engineerable | YES |
| C011 | trainable | existing_engineered | YES |
| C023 | blocked (candidate) | candidate | YES |
| C042 | blocked (blocked) | blocked | YES |
| C065 | blocked (candidate) | candidate_ready | YES |
| C089 | blocked (candidate) | candidate_ready | YES |
| C105 | blocked (candidate) | candidate_ready | YES |
| C121 | blocked (candidate) | candidate_ready | YES |
| C133 | trainable | existing_engineered | YES |
| C135 | blocked (outlier) | blocked_until_outlier_guard | YES |
| C138 | trainable | existing_engineered | YES |
| C142 | blocked (candidate) | candidate | YES |
| C154 | blocked (candidate) | candidate | YES |
| C156 | blocked (candidate) | candidate | YES |
| C161 | blocked (candidate) | candidate | YES |
| C165 | blocked (candidate) | candidate | YES |
| C170 | blocked (candidate) | candidate | YES |
| C173 | blocked (candidate) | candidate | YES |

**All 20 spot-checks PASS.**

---

## 7. Self-Audit

| Check | Result |
|-------|:------:|
| All 173 factors from registry accounted for | PASS |
| No hand-written factors (all from registry JSON) | PASS |
| Blocked factors cannot enter training | PASS |
| C001/C005/C006/C008/C010/C135 correctly blocked | PASS |
| C133-C138 correctly marked as round4_tested | PASS |
| No factor without factor_id included | PASS |
| P0/P1 blockers | **NONE** |

---

**Phase 1 COMPLETE. No P0/P1. Proceeding to Phase 2 (Engineering Gate).**
