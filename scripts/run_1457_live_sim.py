#!/usr/bin/env python
"""Run the 14:57 engineering live simulation with the live-strict 14:57 bundle.

This is a thin wrapper around realtime_1457_today_probe.py so the original
diagnostic script stays intact. It patches date/bundle/output paths, keeps the
warmup state in memory while waiting for a target time, then writes:

- Full realtime scoring CSV
- Paper-trading selector v1 CSV: probability > 0.75, tradable, top 6 with ties
- Timing JSON

Example:
  python scripts/run_1457_live_sim.py --phase all --target-time 14:57
  python scripts/run_1457_live_sim.py --phase all --no-wait --test-mode
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import torch

import realtime_1457_today_probe as live


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = Path(
    os.environ.get(
        "ASHARE_SIMILARITY_RUNTIME_DATA",
        os.environ.get("ASHARE_SIMILARITY_DATA", "E:/ashare_similarity_runtime/data"),
    )
).resolve()
DEFAULT_BUNDLE = (
    RUNTIME_ROOT
    / "reports" / "prediction" / "runs"
    / "gpu_probe_20260509T105830Z_12605e2b" / "model_bundle.pt"
)
DESKTOP = Path(os.environ.get("ASHARE_REALTIME_DESKTOP", Path.home() / "Desktop")).resolve()
REALTIME_OUTPUT_DIR = DESKTOP / "realtime_1457_outputs"
REPORT_DIR = Path(os.environ.get("ASHARE_1457_REPORT_DIR", REPO_ROOT / "docs")).resolve()
STRICT_1430_CAPTURE_MAX_DELTA_MS = 100.0

HARD_MONEYFLOW_FEATURES = {
    "tushare_net_mf_amount",
    "tushare_net_mf_amount_available",
    "tushare_lg_buy_sell_ratio",
    "tushare_lg_buy_sell_ratio_available",
    "tushare_elg_buy_sell_ratio",
    "tushare_elg_buy_sell_ratio_available",
    "tushare_mf_strength",
    "tushare_mf_strength_available",
    "tushare_sm_sell_pressure",
    "tushare_sm_sell_pressure_available",
    "tushare_main_force_divergence",
    "tushare_main_force_divergence_available",
    "tushare_ff_adjusted_flow",
    "tushare_ff_adjusted_flow_available",
}
POST_CLOSE_FORBIDDEN_FEATURES = {
    "tushare_lhb_net_buy",
    "tushare_lhb_net_rate",
    "tushare_inst_buy_count",
    "tushare_lhb_appeared",
    "tushare_inst_net_buy",
    "tushare_rzye_delta_pct",
    "tushare_rzye",
    "tushare_rzmre_ratio",
    "tushare_margin_net",
    "tushare_rqye_ratio",
    "tushare_auction_close_vwap_ratio",
    "tushare_auction_close_vol",
    "tushare_float_relative_impact",
}
POST_CLOSE_FORBIDDEN_FEATURES |= {f"{col}_available" for col in list(POST_CLOSE_FORBIDDEN_FEATURES)}
THS_FORBIDDEN_FEATURES = {
    "sector_pct_change_best",
    "sector_strength_rank",
    "sector_limit_up_count",
    "sector_divergence",
    "sector_duration_days",
    "sector_climax_signal",
}
THS_FORBIDDEN_FEATURES |= {f"{col}_available" for col in list(THS_FORBIDDEN_FEATURES)}


def _parse_date(raw: str | None) -> date:
    if not raw:
        return date.today()
    return datetime.strptime(raw, "%Y-%m-%d").date()



def _fmt_ms(value: datetime) -> str:
    return value.isoformat(sep=" ", timespec="milliseconds")


def _validate_price_cache_1430_payload(raw: dict, target_date: date) -> tuple[bool, str]:
    if raw.get("target_date") != target_date.isoformat():
        return False, "strict_1430_target_date_mismatch"
    if raw.get("quote_time_status") != "verified":
        return False, f"strict_1430_quote_time_status_{raw.get('quote_time_status', 'missing')}"
    if "capture_start_delta_ms" not in raw:
        return False, "strict_1430_missing_ms_capture_metadata"
    try:
        delta_ms = abs(float(raw["capture_start_delta_ms"]))
    except (TypeError, ValueError):
        return False, "strict_1430_bad_capture_delta"
    if delta_ms > STRICT_1430_CAPTURE_MAX_DELTA_MS:
        return False, f"strict_1430_capture_delta_{delta_ms:.1f}ms"
    return True, "strict_1430_verified"


def _load_price_cache_1430_payload(target_date: date) -> dict | None:
    stamp = target_date.strftime("%Y%m%d")
    path = REALTIME_OUTPUT_DIR / f"price_cache_1430_{stamp}.json"
    if not path.exists():
        legacy_path = DESKTOP / f"price_cache_1430_{stamp}.json"
        if legacy_path.exists():
            path = legacy_path
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return raw if isinstance(raw, dict) else None


def _save_price_cache_1430(
    target_date: date,
    cache: dict[str, float],
    *,
    snapshot: pd.DataFrame | None = None,
    capture_target_at: datetime | None = None,
    capture_started_at: datetime | None = None,
    capture_finished_at: datetime | None = None,
) -> None:
    stamp = target_date.strftime("%Y%m%d")
    REALTIME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = REALTIME_OUTPUT_DIR / f"price_cache_1430_{stamp}.json"
    now = datetime.now()
    capture_target_at = capture_target_at or now.replace(hour=14, minute=30, second=0, microsecond=0)
    capture_started_at = capture_started_at or now
    capture_finished_at = capture_finished_at or now
    capture_start_delta_ms = (capture_started_at - capture_target_at).total_seconds() * 1000.0
    capture_duration_ms = (capture_finished_at - capture_started_at).total_seconds() * 1000.0
    payload = {
        "target_date": target_date.isoformat(),
        "captured_at": _fmt_ms(capture_started_at),
        "capture_target_at": _fmt_ms(capture_target_at),
        "capture_started_at": _fmt_ms(capture_started_at),
        "capture_finished_at": _fmt_ms(capture_finished_at),
        "capture_start_delta_ms": round(capture_start_delta_ms, 3),
        "capture_duration_ms": round(capture_duration_ms, 3),
        "strict_capture_window_ms": STRICT_1430_CAPTURE_MAX_DELTA_MS,
        "count": len(cache),
        "ok_symbols": len(cache),
        "total_symbols": len(snapshot) if snapshot is not None else len(cache),
        "prices": cache,
    }
    if snapshot is not None and "quote_time" in snapshot.columns:
        qt = snapshot["quote_time"].astype(str).str.strip()
        qt_valid = qt[qt.str.fullmatch(r"\d{2}:\d{2}:\d{2}")]
        if len(qt_valid) > 0:
            qt_min = qt_valid.min()
            qt_max = qt_valid.max()
            payload["quote_time_min"] = qt_min
            payload["quote_time_max"] = qt_max
            # Validate quote_time is actually near 14:30 (14:29:00-14:31:00)
            def _qt_sec(t: str) -> int:
                return int(t[:2]) * 3600 + int(t[3:5]) * 60 + int(t[6:8])
            min_sec = _qt_sec(qt_min)
            max_sec = _qt_sec(qt_max)
            window_start = 14 * 3600 + 29 * 60  # 14:29:00
            window_end = 14 * 3600 + 31 * 60    # 14:31:00
            if window_start <= min_sec <= window_end and window_start <= max_sec <= window_end:
                payload["quote_time_status"] = "verified"
            else:
                payload["quote_time_status"] = "outside_1430_window"
        else:
            payload["quote_time_status"] = "no_valid_quote_time"
    else:
        payload["quote_time_status"] = "not_available"
    strict_ok, strict_reason = _validate_price_cache_1430_payload(payload, target_date)
    payload["strict_1430_valid"] = strict_ok
    payload["strict_1430_reason"] = strict_reason
    payload["quote_time_precision"] = "seconds"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    print(
        f"  14:30 price cache persisted: {path} "
        f"({len(cache)} symbols, qt_status={payload['quote_time_status']}, "
        f"strict={strict_ok}, delta_ms={payload['capture_start_delta_ms']})"
    )


def _load_price_cache_1430(target_date: date, *, run_mode: str = "formal") -> dict[str, float] | None:
    stamp = target_date.strftime("%Y%m%d")
    path = REALTIME_OUTPUT_DIR / f"price_cache_1430_{stamp}.json"
    if not path.exists():
        legacy_path = DESKTOP / f"price_cache_1430_{stamp}.json"
        if legacy_path.exists():
            path = legacy_path
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict) and "prices" in raw:
            cache = raw["prices"]
            captured = raw.get("captured_at", "unknown")
            qt_status = raw.get("quote_time_status", "not_available")
            strict_ok, strict_reason = _validate_price_cache_1430_payload(raw, target_date)
            print(
                f"  14:30 price cache loaded: {len(cache)} symbols "
                f"(captured_at={captured}, qt_status={qt_status}, "
                f"strict={strict_ok}, reason={strict_reason})"
            )
            if run_mode == "formal":
                if not strict_ok:
                    print(f"  REJECTED: formal mode requires strict 14:30 cache ({strict_reason})")
                    return None
            return cache
        else:
            # Legacy format (plain dict without metadata)
            if run_mode == "formal":
                print(f"  REJECTED: formal mode rejects legacy format 14:30 cache (no metadata)")
                return None
            cache = raw
            print(f"  14:30 price cache loaded (legacy, approximate): {len(cache)} symbols")
            return cache
    return None


def _sleep_until_precise(target: datetime) -> datetime:
    while True:
        now = datetime.now()
        remaining = (target - now).total_seconds()
        if remaining <= 0:
            return datetime.now()
        if remaining > 5:
            time.sleep(min(remaining - 1.0, 60.0))
        elif remaining > 0.5:
            time.sleep(max(remaining - 0.1, 0.05))
        elif remaining > 0.02:
            time.sleep(max(remaining - 0.005, 0.001))
        else:
            # Short spin for sub-100ms scheduling accuracy on Windows.
            pass


def _patch_live_module(target_date: date, bundle_path: Path, run_tag: str) -> dict[str, Path]:
    stamp = target_date.strftime("%Y%m%d")
    REALTIME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    full_csv = REALTIME_OUTPUT_DIR / f"realtime_1457_m1457_full_{stamp}_{run_tag}.csv"
    selector_csv = REALTIME_OUTPUT_DIR / f"realtime_1457_m1457_selector_top6_{stamp}_{run_tag}.csv"
    timing_json = REALTIME_OUTPUT_DIR / f"realtime_1457_m1457_timing_{stamp}_{run_tag}.json"
    report_md = REPORT_DIR / f"realtime_1457_m1457_live_sim_{stamp}_{run_tag}.md"

    live.TODAY = target_date
    live.TODAY_STR = target_date.isoformat()
    live.BUNDLE_PATH = bundle_path
    live.OUTPUT_CSV = full_csv
    live.REPORT_PATH = report_md

    return {
        "full_csv": full_csv,
        "selector_csv": selector_csv,
        "timing_json": timing_json,
        "report_md": report_md,
    }


def _wait_until(target_hhmm: str, state: live.WarmupState | None = None, *, target_date: date | None = None) -> None:
    hh, mm = target_hhmm.split(":")
    now = datetime.now()
    target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    if now >= target:
        print(f"Target time {target_hhmm} already passed; running immediately.")
        return

    # Capture price snapshot at 14:30 for last_30min_return computation.
    capture_time = now.replace(hour=14, minute=30, second=0, microsecond=0)
    if state and state.all_main_board and now < capture_time < target:
        wait_to_capture = (capture_time - now).total_seconds()
        print(f"Waiting {wait_to_capture:.0f}s until 14:30 for price cache...")
        capture_started_at = _sleep_until_precise(capture_time)
        print("Capturing 14:30 price snapshot for last_30min_return (all main-board)...")
        fetch_started_at = capture_started_at
        raw_snap = live.fetch_realtime_snapshot(universe=state.all_main_board)
        fetch_finished_at = datetime.now()
        state.price_cache_1430 = {}
        for _, row in raw_snap.iterrows():
            sym = str(row["symbol"]).zfill(6)
            price = row.get("latest_price")
            if pd.notna(price) and float(price) > 0:
                state.price_cache_1430[sym] = float(price)
        print(f"  14:30 price cache: {len(state.price_cache_1430)} symbols")
        if target_date:
            _save_price_cache_1430(
                target_date,
                state.price_cache_1430,
                snapshot=raw_snap,
                capture_target_at=capture_time,
                capture_started_at=fetch_started_at,
                capture_finished_at=fetch_finished_at,
            )
        now = datetime.now()

    remaining = (target - now).total_seconds()
    if remaining > 0:
        print(f"Waiting {remaining:.0f}s until {target_hhmm}...")
        time.sleep(remaining)


def _reject_no_wait_before_target(target_date: date, target_hhmm: str, *, test_mode: bool) -> None:
    if test_mode:
        print(
            "TEST MODE: running before the formal target is allowed. "
            "Do not use candidates as formal 14:57 output."
        )
        return
    now = datetime.now()
    if target_date != now.date():
        return
    hh, mm = target_hhmm.split(":")
    target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    if now < target:
        raise SystemExit(
            f"Refusing --no-wait before target time {target_hhmm}; "
            "use warmup-and-wait for the live 14:57 snapshot."
        )


def _write_selector(full_csv: Path, selector_csv: Path, prob_threshold: float, topk: int) -> dict:
    df = pd.read_csv(full_csv, dtype={"symbol": "string"})
    if "symbol" in df.columns:
        symbol_text = df["symbol"].astype("string").str.strip()
        numeric_symbol = symbol_text.str.fullmatch(r"\d+").fillna(False)
        df.loc[numeric_symbol, "symbol"] = symbol_text[numeric_symbol].str.zfill(6)
    if "tradable" in df.columns:
        mask = df["tradable"].astype(bool)
    else:
        mask = pd.Series([True] * len(df), index=df.index)

    candidates = df[mask & (df["probability"] >= prob_threshold)].copy()
    candidates = candidates.sort_values(["probability", "symbol"], ascending=[False, True]).copy()
    if len(candidates) > topk:
        cutoff_probability = candidates.iloc[topk - 1]["probability"]
        candidates = candidates[candidates["probability"] >= cutoff_probability].copy()
    candidates.insert(0, "selector_rank", range(1, len(candidates) + 1))
    candidates["selector_rule"] = f"probability>={prob_threshold:.2f}_top{topk}_ties"
    candidates.to_csv(selector_csv, index=False, encoding="utf-8-sig")

    return {
        "selector_rule": f"probability>={prob_threshold:.2f}_top{topk}_ties",
        "selector_count": int(len(candidates)),
        "selector_top_probability": (
            float(candidates["probability"].max()) if len(candidates) else None
        ),
        "selector_min_probability": (
            float(candidates["probability"].min()) if len(candidates) else None
        ),
        "selector_csv": str(selector_csv),
    }


def _bundle_feature_checks(bundle_path: Path) -> dict:
    bundle = torch.load(bundle_path, map_location="cpu", weights_only=False)
    selected = list(bundle.get("selected_feature_names", []))
    hard_selected = [f for f in selected if f in HARD_MONEYFLOW_FEATURES]
    postclose_selected = [f for f in selected if f in POST_CLOSE_FORBIDDEN_FEATURES]
    ths_selected = [f for f in selected if f in THS_FORBIDDEN_FEATURES]
    return {
        "selected_feature_count": len(selected),
        "hard_moneyflow_selected_count": len(hard_selected),
        "hard_moneyflow_selected": hard_selected,
        "postclose_forbidden_selected_count": len(postclose_selected),
        "postclose_forbidden_selected": postclose_selected,
        "ths_selected_count": len(ths_selected),
        "ths_selected": ths_selected,
        "has_c004": any(f.startswith("tushare_ff_adjusted_flow") for f in selected),
        "has_c009": any(f.startswith("tushare_main_force_divergence") for f in selected),
    }


def _append_m1457_report(
    report_path: Path,
    feature_checks: dict,
    selector_summary: dict,
    live_results: dict,
    paths: dict[str, Path],
) -> None:
    timing = live_results.get("timing", {})
    total_live = timing.get("total_live_sec")
    total_live_text = f"{total_live:.2f}" if isinstance(total_live, (int, float)) else "N/A"
    top_prob = live_results.get("top_probability")
    section = f"""

---

## M1457 Wrapper Verification

This section is added by `run_1457_live_sim.py` for the M1457 no-hard-moneyflow test.
The base realtime script may still print generic `approximated_1457` wording for
T-1 daily Tushare context features. The hard moneyflow exclusion check below is
the relevant P0 gate for this run.

| Check | Value |
|---|---:|
| Selected feature count | {feature_checks.get('selected_feature_count')} |
| Hard moneyflow selected count | {feature_checks.get('hard_moneyflow_selected_count')} |
| Post-close forbidden selected count | {feature_checks.get('postclose_forbidden_selected_count')} |
| THS selected count | {feature_checks.get('ths_selected_count')} |
| C004 selected | {feature_checks.get('has_c004')} |
| C009 selected | {feature_checks.get('has_c009')} |
| Live total seconds | {total_live_text} |
| Within 180 seconds | {live_results.get('within_180s')} |
| Top probability | {top_prob if top_prob is not None else 'N/A'} |

Hard moneyflow selected features:

```text
{chr(10).join(feature_checks.get('hard_moneyflow_selected') or ['NONE'])}
```

Paper selector:

| Field | Value |
|---|---|
| Rule | {selector_summary.get('selector_rule', 'N/A')} |
| Count | {selector_summary.get('selector_count', 'N/A')} |
| Top probability | {selector_summary.get('selector_top_probability', 'N/A')} |
| Min probability | {selector_summary.get('selector_min_probability', 'N/A')} |
| Selector CSV | `{paths['selector_csv']}` |
| Full CSV | `{paths['full_csv']}` |

"""
    with open(report_path, "a", encoding="utf-8") as f:
        f.write(section)


def main() -> None:
    parser = argparse.ArgumentParser(description="Live-strict 14:57 candidate picker wrapper")
    parser.add_argument("--phase", choices=["warmup", "live", "all"], default="all")
    parser.add_argument("--today", help="Target trading date, YYYY-MM-DD. Defaults to OS today.")
    parser.add_argument("--bundle-path", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--target-time", default="14:57", help="HH:MM to run live phase in --phase all")
    parser.add_argument("--no-wait", action="store_true", help="Run live phase immediately")
    parser.add_argument("--test-mode", action="store_true", help="Allow an early diagnostic run before target time")
    parser.add_argument("--prob-threshold", type=float, default=0.75)
    parser.add_argument("--topk", type=int, default=6)
    parser.add_argument(
        "--run-mode",
        choices=["formal", "postclose", "test"],
        default="formal",
        help="Run mode: formal (14:57 realtime), postclose (after 15:00), test (anytime)",
    )
    args = parser.parse_args()

    target_hh, target_mm = [int(x) for x in args.target_time.split(":")]
    if args.run_mode == "postclose":
        pass
    elif not args.test_mode and target_hh * 60 + target_mm < 14 * 60 + 57:
        raise SystemExit("Formal live-strict runs must target 14:57 or later; use --test-mode for early diagnostics.")

    target_date = _parse_date(args.today)
    run_tag = datetime.now().strftime("%H%M%S")
    paths = _patch_live_module(target_date, args.bundle_path, run_tag)

    print("=" * 72)
    print("Live-strict 14:57 simulation")
    print(f"Date: {target_date.isoformat()}")
    print(f"Bundle: {args.bundle_path}")
    print(f"Full CSV: {paths['full_csv']}")
    print(f"Selector CSV: {paths['selector_csv']}")
    print("=" * 72)
    feature_checks = _bundle_feature_checks(args.bundle_path)
    print(
        "Feature P0 check: "
        f"hard_moneyflow_selected={feature_checks['hard_moneyflow_selected_count']}, "
        f"postclose_selected={feature_checks['postclose_forbidden_selected_count']}, "
        f"ths_selected={feature_checks['ths_selected_count']}, "
        f"C004={feature_checks['has_c004']}, C009={feature_checks['has_c009']}"
    )
    if (
        feature_checks["hard_moneyflow_selected_count"]
        or feature_checks["postclose_forbidden_selected_count"]
        or feature_checks["ths_selected_count"]
        or feature_checks["has_c004"]
        or feature_checks["has_c009"]
    ):
        raise SystemExit("P0 feature check failed; refusing to run live picker.")

    state = live.WarmupState()
    warmup_timing: dict = {}
    live_results: dict = {}

    if args.phase in ("warmup", "all"):
        warmup_timing = live.phase_warmup(state)

    if args.phase in ("live", "all"):
        if args.phase == "live":
            # Live-only cannot reuse an earlier process's in-memory warmup state,
            # so do a minimal warmup in this process.
            warmup_timing = live.phase_warmup(state)
        elif not args.no_wait:
            _wait_until(args.target_time, state=state, target_date=target_date)
        else:
            _reject_no_wait_before_target(target_date, args.target_time, test_mode=args.test_mode)

        # Load/validate 14:30 price cache. Formal requires millisecond-level
        # local capture proof: fetch start must be within +/-100ms of 14:30:00.
        if args.run_mode == "formal":
            validated_cache = _load_price_cache_1430(target_date, run_mode=args.run_mode)
            if not validated_cache:
                raise SystemExit("Formal run rejected: strict 14:30 price cache is missing or invalid.")
            state.price_cache_1430 = validated_cache
        elif not state.price_cache_1430:
            state.price_cache_1430 = _load_price_cache_1430(target_date, run_mode=args.run_mode)

        live_start = time.perf_counter()
        live_results = live.phase_live(state, run_mode=args.run_mode)
        wrapper_live_sec = time.perf_counter() - live_start
        price_cache_payload = _load_price_cache_1430_payload(target_date) or {}
        strict_ok, strict_reason = (
            _validate_price_cache_1430_payload(price_cache_payload, target_date)
            if price_cache_payload
            else (False, "strict_1430_missing_cache")
        )
        live_results["price_cache_1430"] = {
            k: price_cache_payload.get(k)
            for k in (
                "target_date",
                "captured_at",
                "capture_target_at",
                "capture_started_at",
                "capture_finished_at",
                "capture_start_delta_ms",
                "capture_duration_ms",
                "strict_capture_window_ms",
                "quote_time_min",
                "quote_time_max",
                "quote_time_status",
                "quote_time_precision",
                "count",
                "ok_symbols",
                "total_symbols",
            )
        }
        live_results["price_cache_1430_strict_valid"] = strict_ok
        live_results["price_cache_1430_strict_reason"] = strict_reason
        if args.run_mode == "formal" and not strict_ok:
            live_results["is_formal_valid"] = False
            live_results["formal_valid_reason"] = strict_reason

        selector_summary = {}
        if paths["full_csv"].exists():
            selector_summary = _write_selector(
                paths["full_csv"], paths["selector_csv"], args.prob_threshold, args.topk
            )
            print("\n=== PAPER SELECTOR V1 ===")
            print(f"  Rule: {selector_summary['selector_rule']}")
            print(f"  Count: {selector_summary['selector_count']}")
            print(f"  Top probability: {selector_summary['selector_top_probability']}")
            print(f"  Min probability: {selector_summary['selector_min_probability']}")
            print(f"  CSV: {paths['selector_csv']}")

        live.write_report(warmup_timing, live_results, state)
        _append_m1457_report(
            paths["report_md"], feature_checks, selector_summary, live_results, paths
        )

        timing_payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "target_date": target_date.isoformat(),
            "bundle_path": str(args.bundle_path),
            "phase": args.phase,
            "target_time": args.target_time,
            "no_wait": args.no_wait,
            "test_mode": args.test_mode,
            "run_mode": args.run_mode,
            "warmup_timing": warmup_timing,
            "live_results": live_results,
            "wrapper_live_sec": wrapper_live_sec,
            "within_180s": bool(live_results.get("within_180s", False)),
            "paths": {k: str(v) for k, v in paths.items()},
            "selector": selector_summary,
            "feature_p0_check": feature_checks,
        }
        with open(paths["timing_json"], "w", encoding="utf-8") as f:
            json.dump(timing_payload, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nTiming JSON saved: {paths['timing_json']}")
    else:
        print("\nWarmup complete in this process. Use --phase all with --target-time to keep it warm until test time.")


if __name__ == "__main__":
    main()
