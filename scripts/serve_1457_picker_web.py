#!/usr/bin/env python
"""Local one-click web console for the live-strict 14:57 candidate picker.

Three run modes:
  - formal:    14:57 realtime (auto-starts, available from 14:57 onward)
  - postclose: post-close verification (available after 15:00)
  - test:      diagnostic run (available anytime, missing data zero-filled)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_SCRIPT = REPO_ROOT / "scripts" / "run_1457_live_sim.py"
DESKTOP = Path(os.environ.get("ASHARE_REALTIME_DESKTOP", Path.home() / "Desktop")).resolve()
REALTIME_OUTPUT_DIR = DESKTOP / "realtime_1457_outputs"
REALTIME_SEARCH_DIRS = (REALTIME_OUTPUT_DIR, DESKTOP)
LOG_DIR = REPO_ROOT / "run_logs"
LOG_DIR.mkdir(exist_ok=True)
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

DEFAULT_PROB_THRESHOLD = 0.75
DEFAULT_TOPK = 6
DEFAULT_RULE = "probability>=0.75 top6 with ties"
MAX_CANDIDATE_ROWS = 200
MAX_TOP_ROWS = 100
MAX_LOG_LINES = 500
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


class RunRequest(BaseModel):
    today: str | None = None
    target_time: str = Field(default="14:57")
    no_wait: bool = Field(default=True)
    test_mode: bool = Field(default=False)
    prob_threshold: float = Field(default=DEFAULT_PROB_THRESHOLD, ge=0.0, le=1.0)
    topk: int = Field(default=DEFAULT_TOPK, ge=1, le=30)


def _today_str() -> str:
    return date.today().isoformat()


def _validate_today(raw: str | None) -> str:
    value = raw or _today_str()
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="日期必须是 YYYY-MM-DD") from exc
    return value


def _validate_target_time(raw: str) -> str:
    if not re.fullmatch(r"\d{2}:\d{2}", raw or ""):
        raise HTTPException(status_code=400, detail="目标时间必须是 HH:MM")
    hour, minute = [int(x) for x in raw.split(":")]
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise HTTPException(status_code=400, detail="目标时间必须是有效的 HH:MM")
    return raw


def _read_csv_rows(
    path: Path | None, limit: int = 50, *, tradable_only: bool = False
) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if tradable_only:
                if str(row.get("tradable", "")).strip().lower() != "true":
                    continue
            rows.append(dict(row))
            if len(rows) >= limit:
                break
    return rows


def _load_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _bundle_feature_checks(bundle_path: Path | None = None) -> dict[str, Any]:
    path = bundle_path or DEFAULT_BUNDLE
    try:
        import torch

        bundle = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as exc:
        return {"error": str(exc), "bundle_path": str(path)}
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
        "bundle_path": str(path),
    }


def _newest(paths: list[Path], after_ts: float | None = None) -> Path | None:
    existing = [p for p in paths if p.exists()]
    if after_ts is not None:
        existing = [p for p in existing if p.stat().st_mtime >= after_ts - 5]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def _realtime_glob(pattern: str) -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()
    for base in REALTIME_SEARCH_DIRS:
        if not base.exists():
            continue
        for path in base.glob(pattern):
            key = str(path.resolve()).lower()
            if key not in seen:
                seen.add(key)
                files.append(path)
    return files


def _resolve_realtime_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.exists():
        return path
    for base in REALTIME_SEARCH_DIRS:
        candidate = base / path.name
        if candidate.exists():
            return candidate
    return path


def _strict_1430_cache_status(today: str) -> tuple[bool, str]:
    stamp = today.replace("-", "")
    path = _resolve_realtime_path(str(REALTIME_OUTPUT_DIR / f"price_cache_1430_{stamp}.json"))
    if not path or not path.exists():
        return False, "strict_1430_cache_missing"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"strict_1430_cache_unreadable:{exc}"
    if not isinstance(raw, dict):
        return False, "strict_1430_cache_bad_format"
    if raw.get("target_date") != today:
        return False, "strict_1430_target_date_mismatch"
    if raw.get("quote_time_status") != "verified":
        return False, f"strict_1430_quote_time_status_{raw.get('quote_time_status', 'missing')}"
    if raw.get("strict_1430_valid") is not True:
        return False, raw.get("strict_1430_reason") or "strict_1430_invalid"
    try:
        delta_ms = abs(float(raw["capture_start_delta_ms"]))
    except (KeyError, TypeError, ValueError):
        return False, "strict_1430_missing_ms_capture_metadata"
    if delta_ms > STRICT_1430_CAPTURE_MAX_DELTA_MS:
        return False, f"strict_1430_capture_delta_{delta_ms:.1f}ms"
    return True, "strict_1430_verified"


def _collect_outputs(
    today: str,
    after_ts: float | None = None,
    run_mode: str | None = None,
) -> dict[str, Any]:
    stamp = today.replace("-", "")

    # Find timing JSON, optionally filtered by run_mode
    all_timing_jsons = sorted(
        _realtime_glob(f"realtime_1457_m1457_timing_{stamp}_*.json"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
    )
    if after_ts is not None:
        all_timing_jsons = [p for p in all_timing_jsons if p.stat().st_mtime >= after_ts - 5]

    timing_json: Path | None = None
    if run_mode:
        matched_timing_jsons: list[Path] = []
        for p in reversed(all_timing_jsons):
            try:
                t = json.loads(p.read_text(encoding="utf-8"))
                rm = t.get("run_mode")
                tm = t.get("test_mode", False)
                if run_mode == "test" and tm:
                    matched_timing_jsons.append(p)
                elif run_mode == "postclose" and rm == "postclose":
                    matched_timing_jsons.append(p)
                elif run_mode == "formal" and rm in (None, "formal") and not tm:
                    matched_timing_jsons.append(p)
            except Exception:
                continue
        if run_mode == "postclose" and matched_timing_jsons:
            def _postclose_rank(path: Path) -> tuple[int, float]:
                try:
                    timing = json.loads(path.read_text(encoding="utf-8"))
                    live = timing.get("live_results") or {}
                    complete = live.get("is_postclose_complete") is True
                    ok = live.get("status") == "ok"
                    return (1 if complete and ok else 0, path.stat().st_mtime)
                except Exception:
                    return (0, path.stat().st_mtime if path.exists() else 0)

            timing_json = max(matched_timing_jsons, key=_postclose_rank)
        elif matched_timing_jsons:
            timing_json = matched_timing_jsons[0]
    else:
        timing_json = all_timing_jsons[-1] if all_timing_jsons else None

    full_csv = None
    selector_csv = None
    if run_mode is None:
        full_csv = _newest(
            _realtime_glob(f"realtime_1457_m1457_full_{stamp}_*.csv"),
            after_ts,
        )
        selector_csv = _newest(
            _realtime_glob(f"realtime_1457_m1457_selector_top6_{stamp}_*.csv")
            + _realtime_glob(f"realtime_1457_m1457_selector_top5_{stamp}_*.csv"),
            after_ts,
        )

    # If we found a specific timing JSON, use its recorded paths for consistency
    timing = _load_json(timing_json)
    recorded_paths = timing.get("paths") or {}
    if timing_json and recorded_paths:
        rp_full = recorded_paths.get("full_csv")
        rp_sel = recorded_paths.get("selector_csv")
        resolved_full = _resolve_realtime_path(rp_full)
        resolved_sel = _resolve_realtime_path(rp_sel)
        if resolved_full and resolved_full.exists():
            full_csv = resolved_full
        if resolved_sel and resolved_sel.exists():
            selector_csv = resolved_sel

    live = timing.get("live_results") or {}
    live_status = live.get("status")
    if run_mode is not None and live_status != "ok":
        full_csv = None
        selector_csv = None
    warmup = timing.get("warmup_timing") or {}
    live_timing = live.get("timing") or {}
    selector = timing.get("selector") or {}
    p0 = timing.get("feature_p0_check") or {}
    if (
        "hard_moneyflow_selected_count" not in p0
        or "postclose_forbidden_selected_count" not in p0
        or "ths_selected_count" not in p0
    ):
        bundle_path = Path(timing.get("bundle_path") or DEFAULT_BUNDLE)
        p0 = _bundle_feature_checks(bundle_path)

    warmup_sec = sum(float(v) for v in warmup.values() if isinstance(v, (int, float)))
    summary = {
        "target_date": timing.get("target_date") or today,
        "generated_at": timing.get("generated_at"),
        "asof_time": live.get("asof_time"),
        "status": live_status,
        "warmup_sec": warmup_sec if warmup else None,
        "live_sec": live_timing.get("total_live_sec"),
        "within_180s": timing.get("within_180s"),
        "top_probability": live.get("top_probability"),
        "total_stocks": live.get("total_stocks"),
        "candidates_raw": live.get("candidates"),
        "selector_rule": selector.get("selector_rule") or DEFAULT_RULE,
        "selector_count": selector.get("selector_count"),
        "selector_top_probability": selector.get("selector_top_probability"),
        "hard_moneyflow_selected_count": p0.get("hard_moneyflow_selected_count"),
        "postclose_forbidden_selected_count": p0.get("postclose_forbidden_selected_count"),
        "ths_selected_count": p0.get("ths_selected_count"),
        "has_c004": p0.get("has_c004"),
        "has_c009": p0.get("has_c009"),
        "selected_feature_count": p0.get("selected_feature_count"),
        "run_mode": timing.get("run_mode"),
        # formal-valid metadata
        "is_formal_valid": live.get("is_formal_valid"),
        "formal_valid_reason": live.get("formal_valid_reason"),
        "snapshot_time_status": live.get("snapshot_time_status"),
        "snapshot_quote_min": live.get("snapshot_quote_min"),
        "snapshot_quote_max": live.get("snapshot_quote_max"),
        "snapshot_captured_at": live.get("snapshot_captured_at"),
        "limit_pool_time_status": live.get("limit_pool_time_status"),
        "output_grade": live.get("output_grade"),
        "price_cache_1430": live.get("price_cache_1430"),
        "price_cache_1430_strict_valid": live.get("price_cache_1430_strict_valid"),
        "price_cache_1430_strict_reason": live.get("price_cache_1430_strict_reason"),
        "universe_counts": live.get("universe_counts"),
        "market_context_injected": live.get("market_context_injected"),
        "saved_snapshot_used": live.get("snapshot_source") == "saved_parquet",
        # postclose metadata
        "is_postclose_complete": live.get("is_postclose_complete"),
        "postclose_incomplete_reasons": live.get("postclose_incomplete_reasons"),
        "postclose_data_fetch_time": live.get("postclose_data_fetch_time"),
        "postclose_snapshot_source": live.get("postclose_snapshot_source"),
        "postclose_checks": live.get("postclose_checks"),
    }
    if (
        summary.get("run_mode") in (None, "formal")
        and summary.get("is_formal_valid") is True
        and summary.get("price_cache_1430_strict_valid") is not True
    ):
        summary["is_formal_valid"] = False
        summary["formal_valid_reason"] = (
            summary.get("price_cache_1430_strict_reason")
            or "strict_1430_missing_ms_capture_metadata"
        )

    return {
        "paths": {
            "full_csv": str(full_csv) if full_csv else None,
            "selector_csv": str(selector_csv) if selector_csv else None,
            "timing_json": str(timing_json) if timing_json else None,
            "report_md": recorded_paths.get("report_md"),
        },
        "summary": summary,
        "candidates": _read_csv_rows(selector_csv, limit=MAX_CANDIDATE_ROWS),
        "top_rows": _read_csv_rows(full_csv, limit=MAX_TOP_ROWS, tradable_only=True),
        "timing": timing,
    }


def _find_valid_formal_on_disk(today: str) -> dict[str, Any] | None:
    """Scan formal timing JSONs for today, return the TRUE live 14:57 formal result.

    Must satisfy ALL:
      - is_formal_valid == true
      - run_mode in (None, "formal"), test_mode != true
      - snapshot_source != "saved_parquet" (must be live_sina or equivalent)
      - limit_pool_time_status == "verified"
      - asof_time in the real 14:56~14:59 window (not 20:xx)

    If multiple match, returns the first found (scanning newest-first).
    Returns a full outputs dict, or None.
    """
    stamp = today.replace("-", "")
    all_timing_jsons = sorted(
        _realtime_glob(f"realtime_1457_m1457_timing_{stamp}_*.json"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
    )
    for tj in reversed(all_timing_jsons):
        try:
            t = json.loads(tj.read_text(encoding="utf-8"))
            if t.get("run_mode") not in (None, "formal") or t.get("test_mode"):
                continue
            live = t.get("live_results") or {}
            if not live.get("is_formal_valid"):
                continue
            # Must be live-captured, not saved_parquet replay
            if live.get("snapshot_source") == "saved_parquet":
                continue
            # Must have verified limit pool
            if live.get("limit_pool_time_status") != "verified":
                continue
            # Must have strict 14:30 local capture proof (<= 100 ms).
            if live.get("price_cache_1430_strict_valid") is not True:
                continue
            price_cache_1430 = live.get("price_cache_1430") or {}
            try:
                capture_delta_ms = abs(float(price_cache_1430["capture_start_delta_ms"]))
            except (KeyError, TypeError, ValueError):
                continue
            if capture_delta_ms > STRICT_1430_CAPTURE_MAX_DELTA_MS:
                continue
            # asof_time must be in the real 14:56~14:59 window
            asof = live.get("asof_time") or ""
            if asof:
                try:
                    asof_parts = asof.split(" ")[-1].split(":")
                    asof_h, asof_m = int(asof_parts[0]), int(asof_parts[1])
                    if not (asof_h == 14 and 56 <= asof_m <= 59):
                        continue
                except (ValueError, IndexError):
                    continue

            recorded_paths = t.get("paths") or {}
            sel_path = _resolve_realtime_path(recorded_paths.get("selector_csv"))
            full_path = _resolve_realtime_path(recorded_paths.get("full_csv"))
            selector = t.get("selector") or {}
            p0 = t.get("feature_p0_check") or {}
            if (
                "hard_moneyflow_selected_count" not in p0
                or "postclose_forbidden_selected_count" not in p0
                or "ths_selected_count" not in p0
            ):
                bundle_path = Path(t.get("bundle_path") or DEFAULT_BUNDLE)
                p0 = _bundle_feature_checks(bundle_path)
            warmup = t.get("warmup_timing") or {}
            live_timing = live.get("timing") or {}
            warmup_sec = sum(float(v) for v in warmup.values() if isinstance(v, (int, float)))
            summary = {
                "target_date": t.get("target_date") or today,
                "generated_at": t.get("generated_at"),
                "asof_time": live.get("asof_time"),
                "status": live.get("status"),
                "warmup_sec": warmup_sec if warmup else None,
                "live_sec": live_timing.get("total_live_sec"),
                "within_180s": t.get("within_180s"),
                "top_probability": live.get("top_probability"),
                "total_stocks": live.get("total_stocks"),
                "candidates_raw": live.get("candidates"),
                "selector_rule": selector.get("selector_rule") or DEFAULT_RULE,
                "selector_count": selector.get("selector_count"),
                "selector_top_probability": selector.get("selector_top_probability"),
                "hard_moneyflow_selected_count": p0.get("hard_moneyflow_selected_count"),
                "postclose_forbidden_selected_count": p0.get("postclose_forbidden_selected_count"),
                "ths_selected_count": p0.get("ths_selected_count"),
                "has_c004": p0.get("has_c004"),
                "has_c009": p0.get("has_c009"),
                "selected_feature_count": p0.get("selected_feature_count"),
                "run_mode": "formal",
                "is_formal_valid": True,
                "formal_valid_reason": live.get("formal_valid_reason"),
                "snapshot_time_status": live.get("snapshot_time_status"),
                "snapshot_quote_min": live.get("snapshot_quote_min"),
                "snapshot_quote_max": live.get("snapshot_quote_max"),
                "snapshot_captured_at": live.get("snapshot_captured_at"),
                "limit_pool_time_status": live.get("limit_pool_time_status"),
                "output_grade": live.get("output_grade"),
                "price_cache_1430": live.get("price_cache_1430"),
                "price_cache_1430_strict_valid": live.get("price_cache_1430_strict_valid"),
                "price_cache_1430_strict_reason": live.get("price_cache_1430_strict_reason"),
                "universe_counts": live.get("universe_counts"),
                "market_context_injected": live.get("market_context_injected"),
                "saved_snapshot_used": False,
                "is_postclose_complete": live.get("is_postclose_complete"),
                "postclose_incomplete_reasons": live.get("postclose_incomplete_reasons"),
                "postclose_data_fetch_time": live.get("postclose_data_fetch_time"),
                "postclose_snapshot_source": live.get("postclose_snapshot_source"),
                "postclose_checks": live.get("postclose_checks"),
            }
            return {
                "paths": {
                    "full_csv": str(full_path) if full_path and full_path.exists() else recorded_paths.get("full_csv"),
                    "selector_csv": str(sel_path) if sel_path and sel_path.exists() else recorded_paths.get("selector_csv"),
                    "timing_json": str(tj),
                    "report_md": recorded_paths.get("report_md"),
                },
                "summary": summary,
                "candidates": _read_csv_rows(sel_path if sel_path and sel_path.exists() else None, limit=MAX_CANDIDATE_ROWS),
                "top_rows": _read_csv_rows(full_path if full_path and full_path.exists() else None, limit=MAX_TOP_ROWS, tradable_only=True),
                "timing": t,
            }
        except Exception:
            continue
    return None


def _make_empty_state(today: str | None = None) -> dict[str, Any]:
    return {
        "status": "idle",
        "message": "未开始",
        "logs": [],
        "today": today or _today_str(),
        "target_time": "14:57",
        "no_wait": True,
        "prob_threshold": DEFAULT_PROB_THRESHOLD,
        "topk": DEFAULT_TOPK,
        "started_at": None,
        "ended_at": None,
        "returncode": None,
        "cmd": None,
        "outputs": {"paths": {}, "summary": {}, "candidates": [], "top_rows": []},
    }


def _disk_state_for_date(mode: str, today: str) -> dict[str, Any]:
    """Return a read-only, date-scoped state built only from saved outputs."""
    state = _make_empty_state(today)
    if mode == "formal":
        outputs = _find_valid_formal_on_disk(today) or _collect_outputs(today, run_mode="formal")
    else:
        outputs = _collect_outputs(today, run_mode=mode)

    state["outputs"] = outputs
    summary = outputs.get("summary") or {}
    has_timing = bool((outputs.get("paths") or {}).get("timing_json"))
    if not has_timing:
        if mode == "formal":
            state["message"] = "无 14:57 正式冻结结果"
        return state

    if mode == "formal":
        state["status"] = "completed" if summary.get("is_formal_valid") is True else "failed"
        state["message"] = "完成（冻结）" if summary.get("is_formal_valid") is True else "该日正式候选无效"
    elif mode == "postclose":
        state["status"] = "completed" if summary.get("is_postclose_complete") is True else "failed"
        state["message"] = "完成" if summary.get("is_postclose_complete") is True else "该日收盘验证不完整"
    else:
        state["status"] = "completed" if summary.get("status") == "ok" else "failed"
        state["message"] = "完成" if summary.get("status") == "ok" else "该日无有效输出"
    return state


def _parse_running_phase(logs: list[str]) -> str:
    phase = "启动中"
    for line in logs:
        if "WARMUP" in line and "PHASE" in line:
            phase = "预热中"
        elif "WARMUP TOTAL" in line:
            phase = "预热完成"
        elif "Waiting" in line and "14:30" in line:
            phase = "等待 14:30 price cache"
        elif "14:30 price cache" in line and ("symbols" in line or "persisted" in line):
            phase = "14:30 已捕获，等待 14:57"
        elif "Waiting" in line and "14:57" in line:
            phase = "等待 14:57"
        elif "PHASE: LIVE" in line or "[1] Snapshot" in line:
            phase = "14:57 推理中"
        elif "PAPER SELECTOR" in line:
            phase = "Selector 完成"
        elif "Report written" in line or "DONE" in line:
            phase = "完成"
    return phase


def _parse_readiness(logs: list[str]) -> dict[str, Any]:
    r: dict[str, Any] = {
        "bundle_loaded": False,
        "features_total": None,
        "features_selected": None,
        "threshold": None,
        "universe_count": None,
        "p0_hard_moneyflow": None,
        "p0_postclose": None,
        "p0_ths_sector": None,
        "p0_c004": None,
        "p0_c009": None,
        "price_cache_1430": None,
        "snapshot_1457": None,
    }
    for line in logs:
        if "Bundle loaded" in line:
            r["bundle_loaded"] = True
        elif "Features:" in line and "total" in line:
            import re
            m = re.search(r"(\d+) total.*?(\d+) selected", line)
            if m:
                r["features_total"] = int(m.group(1))
                r["features_selected"] = int(m.group(2))
        elif "Threshold:" in line:
            import re
            m = re.search(r"Threshold:\s*([\d.]+)", line)
            if m:
                r["threshold"] = float(m.group(1))
        elif "Universe" in line and "main-board" in line:
            import re
            m = re.search(r"(\d+)/(\d+)", line)
            if m:
                r["universe_count"] = f"{m.group(1)}/{m.group(2)}"
        elif "Feature P0 check" in line:
            import re
            for k, field in [("hard_moneyflow_selected", "p0_hard_moneyflow"),
                             ("postclose_selected", "p0_postclose"),
                             ("ths_selected", "p0_ths_sector")]:
                m2 = re.search(rf"{k}=(\d+)", line)
                if m2:
                    r[field] = int(m2.group(1))
            m2 = re.search(r"C004=(True|False)", line)
            if m2:
                r["p0_c004"] = m2.group(1) == "True"
            m2 = re.search(r"C009=(True|False)", line)
            if m2:
                r["p0_c009"] = m2.group(1) == "True"
        elif "14:30 price cache" in line and ("symbols" in line or "persisted" in line):
            r["price_cache_1430"] = "captured"
        elif "[1] Snapshot" in line and "stocks" in line:
            r["snapshot_1457"] = "captured"
    return r


class LiveRunManager:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.process_formal: subprocess.Popen[str] | None = None
        self.process_postclose: subprocess.Popen[str] | None = None
        self.process_test: subprocess.Popen[str] | None = None
        self.process_replay: subprocess.Popen[str] | None = None

        today = _today_str()
        self.state_formal: dict[str, Any] = _make_empty_state(today)
        # Formal: always prefer the valid frozen result from disk
        valid_formal = _find_valid_formal_on_disk(today)
        if valid_formal:
            self.state_formal["outputs"] = valid_formal
            self.state_formal["status"] = "completed"
            self.state_formal["message"] = "完成（冻结）"
        else:
            self.state_formal["outputs"] = _collect_outputs(today, run_mode="formal")
        self.state_postclose: dict[str, Any] = _make_empty_state(today)
        self.state_postclose["outputs"] = _collect_outputs(today, run_mode="postclose")
        self.state_test: dict[str, Any] = _make_empty_state(today)
        self.state_test["outputs"] = _collect_outputs(today, run_mode="test")
        self.state_replay: dict[str, Any] = _make_empty_state(today)

    def _get_state(self, mode: str) -> dict[str, Any]:
        if mode == "postclose":
            return self.state_postclose
        elif mode == "test":
            return self.state_test
        elif mode == "replay":
            return self.state_replay
        return self.state_formal

    def _get_process(self, mode: str) -> subprocess.Popen[str] | None:
        if mode == "postclose":
            return self.process_postclose
        elif mode == "test":
            return self.process_test
        elif mode == "replay":
            return self.process_replay
        return self.process_formal

    def _set_process(self, mode: str, proc: subprocess.Popen[str] | None) -> None:
        if mode == "postclose":
            self.process_postclose = proc
        elif mode == "test":
            self.process_test = proc
        elif mode == "replay":
            self.process_replay = proc
        else:
            self.process_formal = proc

    def _append_log(self, line: str, mode: str = "formal") -> None:
        with self.lock:
            state = self._get_state(mode)
            logs: list[str] = state.setdefault("logs", [])
            logs.append(line.rstrip("\n"))
            if len(logs) > MAX_LOG_LINES:
                del logs[: len(logs) - MAX_LOG_LINES]

    def start_formal(self, req: RunRequest) -> dict[str, Any]:
        today = _validate_today(req.today)
        if today != _today_str():
            raise HTTPException(
                status_code=400,
                detail=f"正式跑必须使用今天日期 ({_today_str()})，不能指定 {today}",
            )
        # Freeze guard: once today's formal is valid (in memory or on disk),
        # never allow a re-run. Do not let yesterday's frozen state block a
        # new trading day after the long-running web process crosses midnight.
        with self.lock:
            summary = self.state_formal.get("outputs", {}).get("summary", {})
            summary_date = summary.get("target_date") or self.state_formal.get("today")
            if summary.get("is_formal_valid") is True and summary_date == today:
                raise HTTPException(status_code=409, detail="14:57 正式候选已冻结，不可重跑")
        if _find_valid_formal_on_disk(today):
            raise HTTPException(status_code=409, detail="14:57 正式候选已冻结（磁盘已有有效结果），不可重跑")
        target_time = _validate_target_time(req.target_time)
        target_hour, target_minute = [int(x) for x in target_time.split(":")]
        if not req.test_mode and target_hour * 60 + target_minute < 14 * 60 + 57:
            raise HTTPException(
                status_code=400,
                detail="当前 live-strict 模型按 14:57 快照执行；目标时间不能早于 14:57",
            )
        now = datetime.now()
        if not req.test_mode and today == now.date().isoformat():
            target_1430 = now.replace(hour=14, minute=30, second=0, microsecond=0)
            target_1457 = now.replace(hour=14, minute=57, second=0, microsecond=0)
            if now >= target_1457:
                raise HTTPException(
                    status_code=400,
                    detail="严格正式跑必须在 14:57 前启动并等待实时快照；已过 14:57，禁止补跑正式候选",
                )
            if now >= target_1430:
                strict_ok, strict_reason = _strict_1430_cache_status(today)
                if not strict_ok:
                    raise HTTPException(
                        status_code=400,
                        detail=f"已过 14:30 且无严格 14:30 缓存（{strict_reason}），禁止启动正式候选",
                    )
        # After 15:00 formal runs must use saved snapshot with --no-wait
        effective_no_wait = req.no_wait
        if today == now.date().isoformat() and now.hour >= 15:
            effective_no_wait = True
        if (
            effective_no_wait
            and not req.test_mode
            and today == now.date().isoformat()
            and (now.hour, now.minute) < (14, 57)
        ):
            raise HTTPException(
                status_code=400,
                detail="14:57 前不能立即跑；后台已自动预热等待 14:57",
            )
        with self.lock:
            proc = self.process_formal
            if proc is not None and proc.poll() is None:
                raise HTTPException(status_code=409, detail="正式任务正在运行中")

            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            cmd = [
                sys.executable, "-u", str(RUN_SCRIPT),
                "--phase", "all",
                "--today", today,
                "--target-time", target_time,
                "--prob-threshold", f"{req.prob_threshold:.4f}",
                "--topk", str(req.topk),
                "--run-mode", "formal",
            ]
            if effective_no_wait:
                cmd.append("--no-wait")
            if req.test_mode:
                cmd.append("--test-mode")

            start_ts = time.time()
            self.state_formal = {
                "run_id": run_id,
                "status": "running",
                "message": "正式跑运行中",
                "logs": [],
                "today": today,
                "target_time": target_time,
                "no_wait": effective_no_wait,
                "test_mode": req.test_mode,
                "prob_threshold": req.prob_threshold,
                "topk": req.topk,
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "started_ts": start_ts,
                "ended_at": None,
                "returncode": None,
                "cmd": subprocess.list2cmdline(cmd),
                "outputs": {"paths": {}, "summary": {}, "candidates": [], "top_rows": []},
            }

        thread = threading.Thread(
            target=self._run_process,
            args=(cmd, today, start_ts, "formal"),
            daemon=True,
        )
        thread.start()
        return self.status()

    def start_postclose(self, req: RunRequest) -> dict[str, Any]:
        today = _validate_today(req.today)
        now = datetime.now()
        if today != _today_str():
            raise HTTPException(
                status_code=400,
                detail=f"收盘验证只能对今天执行；{today} 只能查看已有结果，今天是 {_today_str()}",
            )
        if today == now.date().isoformat() and now.hour < 15:
            raise HTTPException(status_code=400, detail="收盘验证只能在 15:00 后执行")
        with self.lock:
            proc = self.process_postclose
            if proc is not None and proc.poll() is None:
                raise HTTPException(status_code=409, detail="收盘验证任务正在运行中")

            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            cmd = [
                sys.executable, "-u", str(RUN_SCRIPT),
                "--phase", "all",
                "--today", today,
                "--target-time", "15:00",
                "--prob-threshold", f"{req.prob_threshold:.4f}",
                "--topk", str(req.topk),
                "--run-mode", "postclose",
                "--no-wait",
            ]

            start_ts = time.time()
            self.state_postclose = {
                "run_id": run_id,
                "status": "running",
                "message": "收盘验证运行中",
                "logs": [],
                "today": today,
                "target_time": "15:00",
                "no_wait": True,
                "test_mode": False,
                "prob_threshold": req.prob_threshold,
                "topk": req.topk,
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "started_ts": start_ts,
                "ended_at": None,
                "returncode": None,
                "cmd": subprocess.list2cmdline(cmd),
                "outputs": {"paths": {}, "summary": {}, "candidates": [], "top_rows": []},
            }

        thread = threading.Thread(
            target=self._run_process,
            args=(cmd, today, start_ts, "postclose"),
            daemon=True,
        )
        thread.start()
        return self.status()

    def start_replay(self, req: RunRequest) -> dict[str, Any]:
        """14:57 回放验证 — uses saved 14:57 snapshot + limit pool after close."""
        today = _validate_today(req.today)
        now = datetime.now()
        if today == _today_str() and now.hour < 15:
            raise HTTPException(status_code=400, detail="14:57 回放验证只能在 15:00 后执行")

        stamp = today.replace("-", "")
        snap_path = _resolve_realtime_path(str(REALTIME_OUTPUT_DIR / f"sina_snapshot_1457_{stamp}.parquet"))
        lp_path = _resolve_realtime_path(str(REALTIME_OUTPUT_DIR / f"limit_pool_1457_{stamp}.pkl"))
        missing = []
        if not snap_path or not snap_path.exists():
            missing.append("14:57 快照")
        if not lp_path or not lp_path.exists():
            missing.append("14:57 涨停池")
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"缺少保存的数据：{', '.join(missing)}，无法回放验证",
            )

        with self.lock:
            proc = self.process_replay
            if proc is not None and proc.poll() is None:
                raise HTTPException(status_code=409, detail="回放验证任务正在运行中")

            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            cmd = [
                sys.executable, "-u", str(RUN_SCRIPT),
                "--phase", "all",
                "--today", today,
                "--target-time", "14:57",
                "--prob-threshold", f"{req.prob_threshold:.4f}",
                "--topk", str(req.topk),
                "--run-mode", "formal",
                "--no-wait",
            ]

            start_ts = time.time()
            self.state_replay = {
                "run_id": run_id,
                "status": "running",
                "message": "14:57 回放验证运行中",
                "logs": [],
                "today": today,
                "target_time": "14:57",
                "no_wait": True,
                "test_mode": False,
                "prob_threshold": req.prob_threshold,
                "topk": req.topk,
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "started_ts": start_ts,
                "ended_at": None,
                "returncode": None,
                "cmd": subprocess.list2cmdline(cmd),
                "outputs": {"paths": {}, "summary": {}, "candidates": [], "top_rows": []},
            }

        thread = threading.Thread(
            target=self._run_process,
            args=(cmd, today, start_ts, "replay"),
            daemon=True,
        )
        thread.start()
        return self.status()

    def auto_warmup_today(self) -> None:
        with self.lock:
            running = self.process_formal is not None and self.process_formal.poll() is None
            status = self.state_formal.get("status")
        if running or status == "running":
            return

        now = datetime.now()

        # Check if today's TRUE live formal result exists on disk
        today_str = now.strftime("%Y-%m-%d")
        stamp = now.strftime("%Y%m%d")
        with self.lock:
            stale_formal_day = self.state_formal.get("today") != today_str
        if stale_formal_day:
            fresh_state = _make_empty_state(today_str)
            fresh_state["outputs"] = _collect_outputs(today_str, run_mode="formal")
            with self.lock:
                if self.state_formal.get("today") != today_str:
                    self.state_formal = fresh_state

        valid = _find_valid_formal_on_disk(today_str)
        if valid:
            self._append_log("[web] found existing valid live formal result, loading from disk", "formal")
            with self.lock:
                self.state_formal["run_id"] = stamp + "_restored"
                self.state_formal["status"] = "completed"
                self.state_formal["message"] = "完成（冻结）"
                self.state_formal["today"] = today_str
                self.state_formal["target_time"] = "14:57"
                self.state_formal["no_wait"] = False
                self.state_formal["outputs"] = valid
            return

        target_1430 = now.replace(hour=14, minute=30, second=0, microsecond=0)
        target_1457 = now.replace(hour=14, minute=57, second=0, microsecond=0)
        strict_ok, strict_reason = _strict_1430_cache_status(today_str)
        if now >= target_1457:
            msg = "已过 14:57，且没有严格有效的正式候选；禁止自动补跑正式候选"
            self._append_log(f"[web] {msg}", "formal")
            with self.lock:
                self.state_formal["status"] = "skipped"
                self.state_formal["message"] = msg
            return
        if now >= target_1430 and not strict_ok:
            msg = f"已过 14:30 且无严格 14:30 缓存（{strict_reason}），禁止自动启动正式候选"
            self._append_log(f"[web] {msg}", "formal")
            with self.lock:
                self.state_formal["status"] = "skipped"
                self.state_formal["message"] = msg
            return

        # Don't auto-start after 14:58:30 — too late for warmup+wait to capture 14:57 snapshot
        if now.hour == 14 and now.minute == 58 and now.second > 30:
            msg = "14:58:30 后启动预热太晚，跳过自动正式跑"
            self._append_log(f"[web] {msg}", "formal")
            with self.lock:
                self.state_formal["status"] = "skipped"
                self.state_formal["message"] = msg
            return
        if now.hour == 14 and now.minute >= 59:
            msg = "14:59 后启动预热太晚，跳过自动正式跑"
            self._append_log(f"[web] {msg}", "formal")
            with self.lock:
                self.state_formal["status"] = "skipped"
                self.state_formal["message"] = msg
            return

        if now.hour >= 15:
            stamp = now.strftime("%Y%m%d")
            snap_path = _resolve_realtime_path(str(REALTIME_OUTPUT_DIR / f"sina_snapshot_1457_{stamp}.parquet"))
            if not snap_path or not snap_path.exists():
                msg = "15:00 后无 14:57 快照文件，跳过自动正式跑"
                self._append_log(f"[web] {msg}", "formal")
                with self.lock:
                    self.state_formal["status"] = "skipped"
                    self.state_formal["message"] = msg
                return
            try:
                import pandas as _pd
                _snap = _pd.read_parquet(snap_path)
                _required = ("quote_date", "quote_time", "captured_at", "snapshot_source")
                _missing = [c for c in _required if c not in _snap.columns]
                if _missing:
                    msg = f"15:00 后 14:57 快照缺少 {_missing}，无法验证，跳过自动正式跑"
                    self._append_log(f"[web] {msg}", "formal")
                    with self.lock:
                        self.state_formal["status"] = "skipped"
                        self.state_formal["message"] = msg
                    return
                _qt = _snap["quote_time"].astype(str).str.strip()
                _qt_valid = _qt[_qt.str.fullmatch(r"\d{2}:\d{2}:\d{2}")]
                if len(_qt_valid) == 0:
                    msg = "15:00 后 14:57 快照无有效 quote_time，跳过自动正式跑"
                    self._append_log(f"[web] {msg}", "formal")
                    with self.lock:
                        self.state_formal["status"] = "skipped"
                        self.state_formal["message"] = msg
                    return
                _hh = _qt_valid.str[:2].astype(int)
                _mm = _qt_valid.str[3:5].astype(int)
                _ss = _qt_valid.str[6:8].astype(int)
                _secs = _hh * 3600 + _mm * 60 + _ss
                _in_window = ((_secs >= 14 * 3600 + 56 * 60 + 30) & (_secs <= 14 * 3600 + 58 * 60 + 30))
                _pct = _in_window.sum() / len(_in_window)
                if _pct < 0.9:
                    msg = f"15:00 后 14:57 快照 quote_time 仅 {_pct:.0%} 在窗口内，跳过自动正式跑"
                    self._append_log(f"[web] {msg}", "formal")
                    with self.lock:
                        self.state_formal["status"] = "skipped"
                        self.state_formal["message"] = msg
                    return
            except Exception as exc:
                msg = f"15:00 后验证 14:57 快照失败: {exc}，跳过自动正式跑"
                self._append_log(f"[web] {msg}", "formal")
                with self.lock:
                    self.state_formal["status"] = "skipped"
                    self.state_formal["message"] = msg
                return

        req = RunRequest(
            today=_today_str(),
            target_time="14:57",
            no_wait=False,
            test_mode=False,
            prob_threshold=DEFAULT_PROB_THRESHOLD,
            topk=DEFAULT_TOPK,
        )
        try:
            self.start_formal(req)
        except HTTPException as exc:
            self._append_log(f"[web] auto warmup skipped: {exc.detail}", "formal")
        except Exception as exc:
            self._append_log(f"[web] auto warmup failed: {exc}", "formal")

    def run_test_once(self, req: RunRequest) -> dict[str, Any]:
        today = _validate_today(req.today)
        target_time = _validate_target_time(req.target_time)
        with self.lock:
            proc = self.process_test
            if proc is not None and proc.poll() is None:
                raise HTTPException(status_code=409, detail="测试任务正在运行中")

        cmd = [
            sys.executable, "-u", str(RUN_SCRIPT),
            "--phase", "all",
            "--today", today,
            "--target-time", target_time,
            "--prob-threshold", f"{req.prob_threshold:.4f}",
            "--topk", str(req.topk),
            "--run-mode", "test",
            "--no-wait",
            "--test-mode",
        ]
        start_ts = time.time()
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        with self.lock:
            self.state_test = {
                "run_id": run_id,
                "status": "running",
                "message": "测试运行中",
                "logs": [],
                "today": today,
                "target_time": target_time,
                "no_wait": True,
                "test_mode": True,
                "prob_threshold": req.prob_threshold,
                "topk": req.topk,
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "started_ts": start_ts,
                "ended_at": None,
                "returncode": None,
                "cmd": subprocess.list2cmdline(cmd),
                "outputs": {"paths": {}, "summary": {}, "candidates": [], "top_rows": []},
            }

        thread = threading.Thread(
            target=self._run_process,
            args=(cmd, today, start_ts, "test"),
            daemon=True,
        )
        thread.start()
        return self.status()

    def _run_process(self, cmd: list[str], today: str, start_ts: float, mode: str) -> None:
        log_path = LOG_DIR / f"1457_picker_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        try:
            with log_path.open("w", encoding="utf-8") as log_file:
                self._append_log(f"[web] log: {log_path}", mode)
                self._append_log(f"[web] cmd: {subprocess.list2cmdline(cmd)}", mode)
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(REPO_ROOT),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )
                with self.lock:
                    self._set_process(mode, proc)

                assert proc.stdout is not None
                for line in proc.stdout:
                    log_file.write(line)
                    log_file.flush()
                    self._append_log(line, mode)

                returncode = proc.wait()
                collect_mode = "formal" if mode == "replay" else mode
                outputs = _collect_outputs(today, after_ts=start_ts, run_mode=collect_mode)
                live_status = (outputs.get("summary") or {}).get("status")
                state = self._get_state(mode)
                with self.lock:
                    if state.get("status") in ("stopping", "stopped"):
                        state["status"] = "stopped"
                        state["message"] = "已停止"
                        state["returncode"] = returncode
                        state["ended_at"] = datetime.now().isoformat(timespec="seconds")
                        self._set_process(mode, None)
                        return
                    state["returncode"] = returncode
                    state["ended_at"] = datetime.now().isoformat(timespec="seconds")
                    state["outputs"] = outputs
                    if returncode != 0:
                        state["status"] = "failed"
                        state["message"] = f"失败，退出码 {returncode}"
                    elif live_status != "ok":
                        state["status"] = "failed"
                        state["message"] = f"失败: {live_status or 'unknown'}"
                    elif mode in ("formal", "replay") and not outputs.get("summary", {}).get("is_formal_valid"):
                        state["status"] = "failed"
                        state["message"] = "失败: formal 验证未通过"
                    elif mode == "postclose" and not outputs.get("summary", {}).get("is_postclose_complete"):
                        state["status"] = "failed"
                        reasons = outputs.get("summary", {}).get("postclose_incomplete_reasons", [])
                        state["message"] = f"失败: 数据不完整 ({', '.join(reasons) if reasons else 'unknown'})"
                    else:
                        state["status"] = "completed"
                        state["message"] = "完成"
                    if state["status"] == "failed":
                        state["outputs"]["candidates"] = []
                        state["outputs"]["top_rows"] = []
                    if mode == "replay" and state["status"] == "completed":
                        state["outputs"]["summary"]["display_mode"] = "replay"
                        state["outputs"]["summary"]["validation_channel"] = "replay"
                    self._set_process(mode, None)
                # If formal failed but a valid frozen result exists on disk, restore it
                if mode == "formal" and state["status"] == "failed":
                    valid = _find_valid_formal_on_disk(today)
                    if valid:
                        with self.lock:
                            self.state_formal["outputs"] = valid
                            self.state_formal["status"] = "completed"
                            self.state_formal["message"] = "完成（冻结）"
        except Exception as exc:
            state = self._get_state(mode)
            with self.lock:
                state["status"] = "failed"
                state["message"] = f"异常：{exc}"
                state["ended_at"] = datetime.now().isoformat(timespec="seconds")
                state["outputs"]["candidates"] = []
                state["outputs"]["top_rows"] = []
                self._set_process(mode, None)
            self._append_log(f"[web] exception: {exc}", mode)

    def stop(self, mode: str = "formal") -> dict[str, Any]:
        with self.lock:
            proc = self._get_process(mode)
            if proc is None or proc.poll() is not None:
                raise HTTPException(status_code=409, detail="当前没有正在运行的任务")
            state = self._get_state(mode)
            state["status"] = "stopping"
            state["message"] = "正在停止"
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        with self.lock:
            state = self._get_state(mode)
            state["status"] = "stopped"
            state["message"] = "已停止"
            state["returncode"] = proc.returncode
            state["ended_at"] = datetime.now().isoformat(timespec="seconds")
            self._set_process(mode, None)
        return self.status()

    def status(self, today: str | None = None) -> dict[str, Any]:
        requested_today = _validate_today(today) if today else None
        result = {}
        for mode in ("formal", "postclose", "test", "replay"):
            with self.lock:
                state = self._get_state(mode)
                snap = json.loads(json.dumps(state, ensure_ascii=False, default=str))
                proc = self._get_process(mode) if mode not in ("test",) else None
                running = proc is not None and proc.poll() is None
            if requested_today and requested_today != snap.get("today"):
                result[mode] = _disk_state_for_date(mode, requested_today)
                continue
            if snap.get("status") == "idle" and mode != "replay":
                today_str = requested_today or snap.get("today") or _today_str()
                if mode == "formal":
                    valid = _find_valid_formal_on_disk(today_str)
                    if valid:
                        snap["outputs"] = valid
                        snap["status"] = "completed"
                        snap["message"] = "完成（冻结）"
                    else:
                        snap["outputs"] = _collect_outputs(today_str, run_mode="formal")
                else:
                    snap["outputs"] = _collect_outputs(today_str, run_mode=mode)
            if running and snap.get("started_ts"):
                snap["elapsed_sec"] = max(0.0, time.time() - float(snap["started_ts"]))
                snap["phase"] = _parse_running_phase(snap.get("logs", []))
                snap["readiness"] = _parse_readiness(snap.get("logs", []))
                snap["message"] = snap["phase"]
            result[mode] = snap
        return result

    def latest(self, today: str | None = None) -> dict[str, Any]:
        t = _validate_today(today)
        return {
            mode: _collect_outputs(t, run_mode=mode)
            for mode in ("formal", "postclose", "test")
        }


HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>14:57 实时候选操作台</title>
  <style>
    :root {
      --bg: #F6F7F4;
      --panel: #ffffff;
      --ink: #171A1F;
      --muted: #68707D;
      --line: #DFE3DF;
      --formal: #19735A;
      --formal-bg: #EFF8F4;
      --formal-border: #9FC8BA;
      --postclose: #B47A1B;
      --postclose-bg: #FFF8E8;
      --postclose-border: #E6C788;
      --test-color: #64748B;
      --hist-color: #7C3AED;
      --replay-color: #0D9488;
      --replay-bg: #F0FDFA;
      --replay-border: #99F6E4;
      --test-bg: #F1F5F9;
      --test-border: #CBD5E1;
      --danger: #B83232;
      --danger-bg: #FFF0F0;
      --danger-border: #E7ADAD;
      --running: #2563EB;
      --running-bg: #EFF6FF;
      --running-border: #93C5FD;
      --rail-w: 290px;
      --insp-w: 340px;
      --top-h: 56px;
      --drawer-h: 44px;
      --sans: Inter, "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      --mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; }
    body { background: var(--bg); color: var(--ink); font-family: var(--sans); font-size: 13px; min-width: 1280px; }

    /* ===== TOP STATUS BAR ===== */
    .top-bar {
      height: var(--top-h);
      position: sticky; top: 0; z-index: 100;
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 20px;
      background: rgba(255,255,255,0.94); backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--line);
    }
    .top-bar__left { display: flex; align-items: center; gap: 14px; }
    .top-bar__title { font-size: 16px; font-weight: 750; letter-spacing: -0.01em; white-space: nowrap; }
    .top-bar__model { font-size: 11px; color: var(--muted); background: var(--test-bg); padding: 2px 8px; border-radius: 4px; font-weight: 600; }
    .top-bar__center { display: flex; align-items: center; }
    .top-bar__right { display: flex; align-items: center; gap: 16px; font-size: 12px; color: var(--muted); }
    .top-bar__meta { font-family: var(--mono); }
    .top-bar__clock { font-family: var(--mono); font-size: 13px; font-weight: 700; color: var(--ink); min-width: 60px; }

    /* Gate Badge */
    .gate { display: inline-flex; align-items: center; gap: 6px; padding: 4px 14px; border-radius: 999px; font-size: 13px; font-weight: 700; border: 1.5px solid; white-space: nowrap; }
    .gate--idle { color: var(--muted); border-color: var(--line); background: var(--panel); }
    .gate--running { color: var(--running); border-color: var(--running-border); background: var(--running-bg); }
    .gate--valid { color: var(--formal); border-color: var(--formal-border); background: var(--formal-bg); }
    .gate--invalid { color: var(--danger); border-color: var(--danger-border); background: var(--danger-bg); }
    .gate--postclose { color: var(--postclose); border-color: var(--postclose-border); background: var(--postclose-bg); }
    .gate--test { color: var(--test-color); border-color: var(--test-border); background: var(--test-bg); }
    .gate__dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
    .gate--running .gate__dot { animation: pulse 1.2s ease-in-out infinite; }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

    /* ===== APP LAYOUT ===== */
    .app-body {
      display: grid;
      grid-template-columns: var(--rail-w) 1fr var(--insp-w);
      min-height: calc(100vh - var(--top-h) - var(--drawer-h));
    }
    .app-body.insp-off { grid-template-columns: var(--rail-w) 1fr; }
    .app-body.insp-off .inspector { display: none; }
    @media (max-width: 1400px) {
      .app-body { grid-template-columns: var(--rail-w) 1fr; }
      .app-body .inspector { display: none; }
      .app-body.insp-on { grid-template-columns: var(--rail-w) 1fr var(--insp-w); }
      .app-body.insp-on .inspector { display: flex; }
    }

    /* ===== LEFT CONTROL RAIL ===== */
    .rail {
      background: var(--panel);
      border-right: 1px solid var(--line);
      padding: 14px;
      overflow-y: auto;
      height: calc(100vh - var(--top-h) - var(--drawer-h));
      position: sticky; top: var(--top-h);
      display: flex; flex-direction: column; gap: 12px;
    }
    .rail-label { display: block; font-size: 11px; color: var(--muted); font-weight: 650; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.04em; }
    .rail-input { width: 100%; height: 32px; border: 1px solid var(--line); border-radius: 5px; padding: 0 8px; font: 13px var(--sans); color: var(--ink); background: #fff; }
    .rail-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .rail-actions { display: grid; gap: 6px; }
    .rail-actions .btn-replay { height: 30px; font-size: 12px; }
    .rail-stops { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
    .rail-divider { border-top: 1px solid var(--line); margin: 2px 0; }
    .rail-section-title { font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
    .rail-footer { color: var(--muted); font-size: 11px; line-height: 1.5; margin-top: auto; padding-top: 8px; border-top: 1px solid var(--line); }
    .rail-footer b { color: var(--ink); }

    /* Buttons */
    .btn { height: 34px; border: none; border-radius: 5px; font: 600 13px var(--sans); cursor: pointer; transition: opacity .1s, transform .06s; display: inline-flex; align-items: center; justify-content: center; gap: 5px; }
    .btn:active { transform: translateY(1px); }
    .btn:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-formal { color: #fff; background: var(--formal); }
    .btn-postclose { color: #fff; background: var(--postclose); }
    .btn-test { color: var(--ink); background: #E8EBE8; border: 1px solid var(--line); }
    .btn-replay { color: #fff; background: var(--replay-color); font-size: 12px; }
    .btn-danger { color: #fff; background: var(--danger); font-size: 12px; height: 28px; }
    .btn-sm { font-size: 11px; height: 26px; padding: 0 8px; }
    .btn-ghost { background: none; border: 1px solid var(--line); color: var(--muted); }

    /* Readiness */
    .rd-list { display: flex; flex-direction: column; gap: 4px; }
    .rd-item { display: flex; align-items: center; gap: 6px; font-size: 12px; padding: 3px 0; }
    .rd-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; background: var(--line); }
    .rd-dot.ok { background: var(--formal); }
    .rd-dot.warn { background: var(--postclose); }
    .rd-dot.bad { background: var(--danger); }

    /* P0 pills */
    .p0-row { display: flex; align-items: center; justify-content: space-between; font-size: 12px; padding: 2px 0; }
    .pill { display: inline-flex; align-items: center; justify-content: center; min-width: 42px; height: 20px; border-radius: 999px; font-size: 11px; font-weight: 700; background: var(--formal-bg); color: var(--formal); }
    .pill.bad { background: var(--danger-bg); color: var(--danger); }

    /* ===== WORKSPACE ===== */
    .workspace { padding: 14px 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }

    /* Mode Tabs */
    .mode-tabs { display: flex; gap: 0; border-bottom: 2px solid var(--line); }
    .mode-tab { display: inline-flex; align-items: center; gap: 6px; height: 38px; padding: 0 16px; border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; background: none; font: 600 13px var(--sans); color: var(--muted); cursor: pointer; transition: color .12s, border-color .12s; white-space: nowrap; }
    .mode-tab:hover { color: var(--ink); }
    .mode-tab.active { color: var(--formal); border-bottom-color: var(--formal); }
    .mode-tab.active[data-mode="postclose"] { color: var(--postclose); border-bottom-color: var(--postclose); }
    .mode-tab.active[data-mode="test"] { color: var(--test-color); border-bottom-color: var(--test-color); }
    .mode-tab.active[data-mode="history"] { color: var(--hist-color); border-bottom-color: var(--hist-color); }
    .mode-tab.active[data-mode="replay"] { color: var(--replay-color); border-bottom-color: var(--replay-color); }
    .mode-tab__dot { width: 7px; height: 7px; border-radius: 50%; background: var(--line); }
    .mode-tab__dot.ok { background: var(--formal); }
    .mode-tab__dot.running { background: var(--running); animation: pulse 1.2s ease-in-out infinite; }
    .mode-tab__dot.bad { background: var(--danger); }
    .mode-tab__dot.warn { background: var(--postclose); }
    .mode-tab__dot.test-ok { background: var(--test-color); }
    .mode-tab__dot.replay-ok { background: var(--replay-color); }

    /* Panels */
    .mode-panel { display: none; flex-direction: column; gap: 12px; }
    .mode-panel.active { display: flex; }

    /* KPI Strip */
    .kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
    .kpi { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; transition: box-shadow .15s; }
    .kpi:hover { box-shadow: 0 1px 4px rgba(0,0,0,.06); }
    .kpi__label { font-size: 11px; color: var(--muted); font-weight: 650; margin-bottom: 6px; display: block; }
    .kpi__value { font-size: 20px; font-weight: 750; line-height: 1; display: block; }
    .kpi__sub { font-size: 11px; color: var(--muted); font-family: var(--mono); margin-top: 5px; display: block; }

    /* Provenance Strip */
    .prov-strip { display: flex; gap: 0; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
    .prov-item { flex: 1; padding: 7px 10px; border-right: 1px solid var(--line); font-size: 11px; }
    .prov-item:last-child { border-right: none; }
    .prov-label { display: block; color: var(--muted); font-weight: 600; margin-bottom: 3px; }
    .prov-value { display: block; font-weight: 700; font-family: var(--mono); font-size: 12px; word-break: break-all; }
    .prov-value.ok { color: var(--formal); }
    .prov-value.bad { color: var(--danger); }
    .prov-value.warn { color: var(--postclose); }

    /* Approximate banner */
    .approx-banner { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 6px; background: #FEF3C7; border: 1px solid #F59E0B; color: #92400E; font-size: 12px; font-weight: 600; }
    .hist-banner { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 6px; background: #EDE9FE; border: 1px solid #7C3AED; color: #5B21B6; font-size: 12px; font-weight: 600; }
    .replay-banner { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 6px; background: var(--replay-bg); border: 1px solid var(--replay-color); color: #134E4A; font-size: 12px; font-weight: 600; }
    .count.hist { background: #7C3AED; }
    .count.rp { background: var(--replay-color); }
    .hit-tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; }
    .hit-tag.hit { background: #D1FAE5; color: #065F46; }
    .hit-tag.miss { background: #FEE2E2; color: #991B1B; }
    .postclose-banner { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 6px; background: var(--postclose-bg); border: 1px solid var(--postclose-border); color: #78560D; font-size: 12px; font-weight: 600; }

    /* History navigation */
    .hist-nav { padding: 8px 0; display: flex; align-items: center; gap: 10px; }
    .hist-nav__label { font-size: 13px; font-weight: 600; color: var(--muted); white-space: nowrap; }
    .hist-nav__select { font-size: 13px; padding: 5px 10px; border: 1px solid var(--line); border-radius: 5px; min-width: 140px; background: #fff; color: var(--ink); cursor: pointer; outline: none; transition: border-color .15s; }
    .hist-nav__select:focus { border-color: var(--hist-color); box-shadow: 0 0 0 2px rgba(124,58,237,.12); }
    .hist-nav__btn { padding: 6px 14px; border: 1px solid var(--line); border-radius: 5px; background: #fff; cursor: pointer; font: 600 12px var(--sans); color: var(--ink); transition: all .15s; user-select: none; }
    .hist-nav__btn:hover:not(:disabled) { background: var(--bg); border-color: var(--hist-color); color: var(--hist-color); }
    .hist-nav__btn:active:not(:disabled) { transform: translateY(1px); background: #EDE9FE; }
    .hist-nav__btn:disabled { opacity: 0.35; cursor: not-allowed; background: #F9FAFB; color: var(--muted); }
    .hist-nav__btn.loading { opacity: 0.5; }

    /* Button hover/focus polish */
    .btn:hover:not(:disabled) { opacity: 0.88; }
    .btn:focus-visible { outline: 2px solid var(--running); outline-offset: 2px; }
    .btn-formal:hover:not(:disabled) { background: #15654E; }
    .btn-postclose:hover:not(:disabled) { background: #9A6918; }
    .btn-replay:hover:not(:disabled) { background: #0B8078; }
    .btn-danger:hover:not(:disabled) { background: #9A2A2A; }

    /* Tables */
    .tbl-section { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
    .tbl-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; border-bottom: 1px solid var(--line); }
    .tbl-header h2 { font-size: 14px; font-weight: 700; margin: 0; }
    .tbl-header .count { display: inline-flex; align-items: center; justify-content: center; min-width: 24px; height: 22px; padding: 0 8px; border-radius: 999px; font-size: 11px; font-weight: 700; background: var(--formal-bg); color: var(--formal); }
    .tbl-header .count.pc { background: var(--postclose-bg); color: var(--postclose); }
    .tbl-header .count.tst { background: var(--test-bg); color: var(--test-color); }
    .tbl-scroll { overflow: auto; max-height: 380px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); white-space: nowrap; }
    th { font-size: 11px; color: var(--muted); font-weight: 650; background: #FAFBF9; position: sticky; top: 0; z-index: 1; }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    .tbl-empty { color: var(--muted); padding: 20px 14px; font-size: 13px; }
    tbody tr { cursor: pointer; transition: background .08s; }
    tbody tr:hover { background: #F5F8F5; }
    tbody tr.selected { background: var(--formal-bg); }
    .tbl-toggle { cursor: pointer; user-select: none; }
    .tbl-toggle .chevron { transition: transform .15s; display: inline-block; font-size: 10px; color: var(--muted); margin-left: 6px; }
    .tbl-section.collapsed .tbl-scroll { display: none; }
    .tbl-section.collapsed .tbl-empty { display: none; }
    .tbl-section.collapsed .chevron { transform: rotate(-90deg); }

    /* Status flags in table */
    .flag { display: inline-block; padding: 1px 5px; border-radius: 3px; font-size: 10px; font-weight: 700; }
    .flag-ok { background: var(--formal-bg); color: var(--formal); }
    .flag-limit { background: #FEF3C7; color: #92400E; }
    .flag-halt { background: var(--danger-bg); color: var(--danger); }
    .flag-st { background: #FDE8E8; color: #991B1B; }

    /* ===== INSPECTOR ===== */
    .inspector {
      background: var(--panel);
      border-left: 1px solid var(--line);
      padding: 14px;
      overflow-y: auto;
      height: calc(100vh - var(--top-h) - var(--drawer-h));
      position: sticky; top: var(--top-h);
    }
    .insp-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
    .insp-header h3 { font-size: 13px; font-weight: 700; margin: 0; }
    .insp-close { background: none; border: none; cursor: pointer; color: var(--muted); font-size: 16px; padding: 2px 6px; border-radius: 4px; }
    .insp-close:hover { background: var(--test-bg); }
    .insp-reopen { position: fixed; right: 12px; top: calc(var(--top-h) + 8px); z-index: 5; background: var(--panel); border: 1px solid var(--line); border-radius: 5px; padding: 4px 10px; font: 600 11px var(--sans); color: var(--muted); cursor: pointer; display: none; }
    .app-body.insp-off .insp-reopen { display: block; }
    .insp-section { margin-bottom: 14px; }
    .insp-section-title { font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px solid var(--line); }
    .detail-grid { display: grid; grid-template-columns: auto 1fr; gap: 3px 10px; font-size: 12px; }
    .detail-grid dt { color: var(--muted); font-weight: 600; white-space: nowrap; }
    .detail-grid dd { font-family: var(--mono); font-weight: 600; word-break: break-all; }
    .detail-grid dd.ok { color: var(--formal); }
    .detail-grid dd.bad { color: var(--danger); }
    .detail-grid dd.warn { color: var(--postclose); }
    .risk-tags { display: flex; flex-wrap: wrap; gap: 4px; }

    /* ===== DIAGNOSTICS DRAWER ===== */
    .drawer {
      position: fixed; bottom: 0; left: 0; right: 0; z-index: 80;
      background: var(--panel);
      border-top: 1px solid var(--line);
      display: flex; flex-direction: column;
      transition: height .2s ease;
      height: var(--drawer-h);
    }
    .drawer.expanded { height: 300px; }
    .drawer-bar {
      height: var(--drawer-h);
      min-height: var(--drawer-h);
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 16px;
      cursor: pointer; user-select: none;
      font-size: 12px; font-weight: 650; color: var(--muted);
    }
    .drawer-bar__left { display: flex; align-items: center; gap: 12px; }
    .drawer-tabs { display: flex; gap: 0; }
    .drawer-tab { border: none; background: none; font: 600 11px var(--sans); color: var(--muted); padding: 3px 10px; cursor: pointer; border-radius: 3px; }
    .drawer-tab:hover { color: var(--ink); }
    .drawer-tab.active { color: var(--ink); background: var(--test-bg); }
    .drawer-chevron { transition: transform .15s; font-size: 10px; }
    .drawer.expanded .drawer-chevron { transform: rotate(180deg); }
    .drawer-body { flex: 1; display: none; overflow: hidden; }
    .drawer.expanded .drawer-body { display: flex; }
    .drawer-content { display: flex; flex: 1; overflow: hidden; }
    .drawer-logs { flex: 1; overflow: auto; }
    .drawer-logs pre { margin: 0; padding: 10px 14px; background: #0F1419; color: #D4DFD8; font: 11px/1.5 var(--mono); height: 100%; overflow: auto; }
    .drawer-artifacts { width: 280px; border-left: 1px solid var(--line); padding: 10px 14px; overflow-y: auto; font-size: 11px; }
    .drawer-artifacts h4 { font-size: 11px; font-weight: 700; color: var(--muted); margin: 0 0 8px; text-transform: uppercase; }
    .artifact-row { padding: 4px 6px; border-radius: 4px; background: #F5F6F3; border: 1px solid var(--line); margin-bottom: 4px; font-family: var(--mono); word-break: break-all; cursor: pointer; transition: background .1s; }
    .artifact-row:hover { background: #E8EBE8; }
    .artifact-row .art-label { font-family: var(--sans); font-weight: 600; color: var(--muted); display: block; font-size: 10px; }
    .conn-warn { display: none; position: fixed; top: var(--top-h); left: 50%; transform: translateX(-50%); z-index: 200; background: var(--danger-bg); color: var(--danger); border: 1px solid var(--danger-border); padding: 4px 16px; border-radius: 0 0 6px 6px; font-size: 12px; font-weight: 700; }
    .conn-warn.show { display: block; }
  </style>
</head>
<body>

  <!-- ===== TOP STATUS BAR ===== -->
  <div class="conn-warn" id="connWarn">连接中断 — 数据可能已过期</div>
  <header class="top-bar">
    <div class="top-bar__left">
      <h1 class="top-bar__title">14:57 实时候选操作台</h1>
      <span class="top-bar__model">PhaseC CatBoost</span>
    </div>
    <div class="top-bar__center">
      <div id="formalGate" class="gate gate--idle">
        <span class="gate__dot"></span>
        <span id="formalGateLabel">等待运行</span>
      </div>
    </div>
    <div class="top-bar__right">
      <span class="top-bar__meta" id="topDate">-</span>
      <span class="top-bar__meta" id="topRunId">-</span>
      <span class="top-bar__meta" id="topFeatures">-</span>
      <span class="top-bar__clock" id="topClock">--:--</span>
    </div>
  </header>

  <!-- ===== APP BODY: RAIL + WORKSPACE + INSPECTOR ===== -->
  <div class="app-body" id="appBody">

    <!-- LEFT CONTROL RAIL -->
    <aside class="rail">
      <div>
        <label class="rail-label">交易日</label>
        <input id="today" type="date" class="rail-input">
      </div>
      <div class="rail-row">
        <div><label class="rail-label">Top K</label><input id="topk" type="number" min="1" max="30" value="6" class="rail-input"></div>
        <div><label class="rail-label">阈值</label><input id="threshold" type="number" min="0" max="1" step="0.01" value="0.75" class="rail-input"></div>
      </div>
      <div class="rail-actions">
        <button id="formalRun" class="btn btn-formal" disabled>正式跑</button>
        <button id="postcloseRun" class="btn btn-postclose" disabled>收盘验证</button>
        <button id="testRun" class="btn btn-test">测试跑</button>
        <button id="replayRun" class="btn btn-replay" disabled>回放验证</button>
      </div>
      <div class="rail-stops">
        <button id="stopFormal" class="btn btn-danger btn-sm" disabled>停止正式</button>
        <button id="stopPostclose" class="btn btn-danger btn-sm" disabled>停止验证</button>
      </div>

      <div class="rail-divider"></div>

      <div>
        <div class="rail-section-title">数据准备</div>
        <div class="rd-list">
          <div class="rd-item"><span class="rd-dot" id="rdTrading"></span><span>交易日识别</span></div>
          <div class="rd-item"><span class="rd-dot" id="rdBundle"></span><span>模型包加载</span></div>
          <div class="rd-item"><span class="rd-dot" id="rdFeatureGate"></span><span>特征安全门</span></div>
          <div class="rd-item"><span class="rd-dot" id="rdCache1430"></span><span>14:30 价格缓存</span></div>
          <div class="rd-item"><span class="rd-dot" id="rdSnapshot"></span><span>14:57 快照</span></div>
        </div>
      </div>

      <div class="rail-divider"></div>

      <div>
        <div class="rail-section-title">特征 P0 检查</div>
        <div class="p0-row"><span>hard moneyflow</span><span id="p0Hard" class="pill">-</span></div>
        <div class="p0-row"><span>post-close</span><span id="p0PostClose" class="pill">-</span></div>
        <div class="p0-row"><span>THS sector</span><span id="p0Ths" class="pill">-</span></div>
        <div class="p0-row"><span>C004</span><span id="p0C004" class="pill">-</span></div>
        <div class="p0-row"><span>C009</span><span id="p0C009" class="pill">-</span></div>
      </div>

      <div class="rail-footer">
        <b>正式跑</b> 14:57 后自动或手动执行，使用实时快照。<br>
        <b>收盘验证</b> 15:00 后，使用完整收盘数据，仅复盘。<br>
        <b>测试跑</b> 随时可按，缺失数据补 0，禁止实盘参考。
      </div>
    </aside>

    <!-- MAIN WORKSPACE -->
    <main class="workspace">
      <div class="mode-tabs">
        <button class="mode-tab active" data-mode="formal"><span class="mode-tab__dot" id="dotFormal"></span>14:57 实时候选</button>
        <button class="mode-tab" data-mode="postclose"><span class="mode-tab__dot" id="dotPostclose"></span>收盘候选</button>
        <button class="mode-tab" data-mode="test"><span class="mode-tab__dot" id="dotTest"></span>测试候选</button>
        <button class="mode-tab" data-mode="history"><span class="mode-tab__dot" id="dotHistory"></span>历史验证</button>
        <button class="mode-tab" data-mode="replay"><span class="mode-tab__dot" id="dotReplay"></span>14:57 回放</button>
      </div>

      <!-- FORMAL PANEL -->
      <div id="panel-formal" class="mode-panel active">
        <div class="kpi-strip">
          <div class="kpi"><span class="kpi__label">候选数</span><strong class="kpi__value" id="f-kpiCount">-</strong><small class="kpi__sub" id="f-kpiRule">-</small></div>
          <div class="kpi"><span class="kpi__label">最高概率</span><strong class="kpi__value" id="f-kpiTopProb">-</strong><small class="kpi__sub" id="f-kpiAsof">-</small></div>
          <div class="kpi"><span class="kpi__label">Live 耗时</span><strong class="kpi__value" id="f-kpiLiveSec">-</strong><small class="kpi__sub" id="f-kpiWithin">-</small></div>
          <div class="kpi"><span class="kpi__label">运行状态</span><strong class="kpi__value" id="f-kpiStatus">-</strong><small class="kpi__sub" id="f-kpiElapsed">-</small></div>
        </div>
        <div class="prov-strip" id="f-prov">
          <div class="prov-item"><span class="prov-label">formal_valid</span><span class="prov-value" id="f-provValid">-</span></div>
          <div class="prov-item"><span class="prov-label">output_grade</span><span class="prov-value" id="f-provGrade">-</span></div>
          <div class="prov-item"><span class="prov-label">snapshot</span><span class="prov-value" id="f-provSnap">-</span></div>
          <div class="prov-item"><span class="prov-label">quote_time</span><span class="prov-value" id="f-provQuote">-</span></div>
          <div class="prov-item"><span class="prov-label">limit_pool</span><span class="prov-value" id="f-provLp">-</span></div>
        </div>
        <div class="tbl-section">
          <div class="tbl-header"><h2>候选票</h2><span class="count" id="f-selCount">0</span></div>
          <div class="tbl-scroll" id="f-candidateScroll">
            <table><thead><tr><th>序</th><th>代码</th><th>名称</th><th class="num">概率</th><th class="num">现价</th><th class="num">涨跌%</th><th class="num">换手</th><th>状态</th></tr></thead><tbody id="f-candidateRows"></tbody></table>
            <div id="f-candidateEmpty" class="tbl-empty">暂无候选</div>
          </div>
        </div>
        <div class="tbl-section collapsed" id="f-fullSection">
          <div class="tbl-header tbl-toggle" onclick="toggleCollapse('f-fullSection')"><h2>全量概率前列 <span class="chevron">&#9660;</span></h2><span class="count" id="f-topCount">0</span></div>
          <div class="tbl-scroll">
            <table><thead><tr><th>序</th><th>代码</th><th>名称</th><th class="num">概率</th><th class="num">现价</th><th class="num">涨跌%</th><th class="num">换手</th><th>状态</th></tr></thead><tbody id="f-topRows"></tbody></table>
            <div id="f-topEmpty" class="tbl-empty">暂无全量结果</div>
          </div>
        </div>
      </div>

      <!-- POSTCLOSE PANEL -->
      <div id="panel-postclose" class="mode-panel">
        <div class="postclose-banner">收盘验证结果 — 仅用于复盘参考，不可作为实盘候选</div>
        <div class="kpi-strip">
          <div class="kpi"><span class="kpi__label">候选数</span><strong class="kpi__value" id="pc-kpiCount">-</strong><small class="kpi__sub" id="pc-kpiRule">-</small></div>
          <div class="kpi"><span class="kpi__label">最高概率</span><strong class="kpi__value" id="pc-kpiTopProb">-</strong><small class="kpi__sub" id="pc-kpiAsof">-</small></div>
          <div class="kpi"><span class="kpi__label">Live 耗时</span><strong class="kpi__value" id="pc-kpiLiveSec">-</strong><small class="kpi__sub" id="pc-kpiWithin">-</small></div>
          <div class="kpi"><span class="kpi__label">运行状态</span><strong class="kpi__value" id="pc-kpiStatus">-</strong><small class="kpi__sub" id="pc-kpiElapsed">-</small></div>
        </div>
        <div class="prov-strip" id="pc-prov">
          <div class="prov-item"><span class="prov-label">data_complete</span><span class="prov-value" id="pc-provComplete">-</span></div>
          <div class="prov-item"><span class="prov-label">output_grade</span><span class="prov-value" id="pc-provGrade">-</span></div>
          <div class="prov-item"><span class="prov-label">snapshot</span><span class="prov-value" id="pc-provSnap">-</span></div>
          <div class="prov-item"><span class="prov-label">fetch_time</span><span class="prov-value" id="pc-provFetch">-</span></div>
          <div class="prov-item"><span class="prov-label">coverage</span><span class="prov-value" id="pc-provCov">-</span></div>
        </div>
        <div class="tbl-section">
          <div class="tbl-header"><h2>收盘验证候选</h2><span class="count pc" id="pc-selCount">0</span></div>
          <div class="tbl-scroll" id="pc-candidateScroll">
            <table><thead><tr><th>序</th><th>代码</th><th>名称</th><th class="num">概率</th><th class="num">现价</th><th class="num">涨跌%</th><th class="num">换手</th><th>状态</th></tr></thead><tbody id="pc-candidateRows"></tbody></table>
            <div id="pc-candidateEmpty" class="tbl-empty">暂无收盘候选</div>
          </div>
        </div>
        <div class="tbl-section collapsed" id="pc-fullSection">
          <div class="tbl-header tbl-toggle" onclick="toggleCollapse('pc-fullSection')"><h2>全量概率前列 <span class="chevron">&#9660;</span></h2><span class="count pc" id="pc-topCount">0</span></div>
          <div class="tbl-scroll">
            <table><thead><tr><th>序</th><th>代码</th><th>名称</th><th class="num">概率</th><th class="num">现价</th><th class="num">涨跌%</th><th class="num">换手</th><th>状态</th></tr></thead><tbody id="pc-topRows"></tbody></table>
            <div id="pc-topEmpty" class="tbl-empty">暂无全量结果</div>
          </div>
        </div>
      </div>

      <!-- TEST PANEL -->
      <div id="panel-test" class="mode-panel">
        <div class="approx-banner">测试诊断结果 — 缺失数据已补 0，禁止实盘参考</div>
        <div class="kpi-strip">
          <div class="kpi"><span class="kpi__label">候选数</span><strong class="kpi__value" id="t-kpiCount">-</strong><small class="kpi__sub" id="t-kpiRule">-</small></div>
          <div class="kpi"><span class="kpi__label">最高概率</span><strong class="kpi__value" id="t-kpiTopProb">-</strong><small class="kpi__sub" id="t-kpiAsof">-</small></div>
          <div class="kpi"><span class="kpi__label">Live 耗时</span><strong class="kpi__value" id="t-kpiLiveSec">-</strong><small class="kpi__sub" id="t-kpiWithin">-</small></div>
          <div class="kpi"><span class="kpi__label">运行状态</span><strong class="kpi__value" id="t-kpiStatus">-</strong><small class="kpi__sub" id="t-kpiElapsed">-</small></div>
        </div>
        <div class="tbl-section">
          <div class="tbl-header"><h2>测试候选</h2><span class="count tst" id="t-selCount">0</span></div>
          <div class="tbl-scroll" id="t-candidateScroll">
            <table><thead><tr><th>序</th><th>代码</th><th>名称</th><th class="num">概率</th><th class="num">现价</th><th class="num">涨跌%</th><th class="num">换手</th><th>状态</th></tr></thead><tbody id="t-candidateRows"></tbody></table>
            <div id="t-candidateEmpty" class="tbl-empty">暂无测试候选</div>
          </div>
        </div>
        <div class="tbl-section collapsed" id="t-fullSection">
          <div class="tbl-header tbl-toggle" onclick="toggleCollapse('t-fullSection')"><h2>全量概率前列 <span class="chevron">&#9660;</span></h2><span class="count tst" id="t-topCount">0</span></div>
          <div class="tbl-scroll">
            <table><thead><tr><th>序</th><th>代码</th><th>名称</th><th class="num">概率</th><th class="num">现价</th><th class="num">涨跌%</th><th class="num">换手</th><th>状态</th></tr></thead><tbody id="t-topRows"></tbody></table>
            <div id="t-topEmpty" class="tbl-empty">暂无全量结果</div>
          </div>
        </div>
      </div>

      <!-- REPLAY PANEL -->
      <div id="panel-replay" class="mode-panel">
        <div class="replay-banner">14:57 回放验证 — 使用已保存 14:57 快照 + 14:57 涨停池复核，不改变正式候选</div>
        <div class="kpi-strip">
          <div class="kpi"><span class="kpi__label">候选数</span><strong class="kpi__value" id="rp-kpiCount">-</strong><small class="kpi__sub" id="rp-kpiRule">-</small></div>
          <div class="kpi"><span class="kpi__label">最高概率</span><strong class="kpi__value" id="rp-kpiTopProb">-</strong><small class="kpi__sub" id="rp-kpiAsof">-</small></div>
          <div class="kpi"><span class="kpi__label">Live 耗时</span><strong class="kpi__value" id="rp-kpiLiveSec">-</strong><small class="kpi__sub" id="rp-kpiWithin">-</small></div>
          <div class="kpi"><span class="kpi__label">运行状态</span><strong class="kpi__value" id="rp-kpiStatus">-</strong><small class="kpi__sub" id="rp-kpiElapsed">-</small></div>
        </div>
        <div class="tbl-section">
          <div class="tbl-header"><h2>回放验证候选</h2><span class="count rp" id="rp-selCount">0</span></div>
          <div class="tbl-scroll" id="rp-candidateScroll">
            <table><thead><tr><th>序</th><th>代码</th><th>名称</th><th class="num">概率</th><th class="num">现价</th><th class="num">涨跌%</th><th class="num">换手</th><th>状态</th></tr></thead><tbody id="rp-candidateRows"></tbody></table>
            <div id="rp-candidateEmpty" class="tbl-empty">暂无回放候选</div>
          </div>
        </div>
        <div class="tbl-section collapsed" id="rp-fullSection">
          <div class="tbl-header tbl-toggle" onclick="toggleCollapse('rp-fullSection')"><h2>全量概率前列 <span class="chevron">&#9660;</span></h2><span class="count rp" id="rp-topCount">0</span></div>
          <div class="tbl-scroll">
            <table><thead><tr><th>序</th><th>代码</th><th>名称</th><th class="num">概率</th><th class="num">现价</th><th class="num">涨跌%</th><th class="num">换手</th><th>状态</th></tr></thead><tbody id="rp-topRows"></tbody></table>
            <div id="rp-topEmpty" class="tbl-empty">暂无全量结果</div>
          </div>
        </div>
      </div>

      <!-- HISTORY PANEL -->
      <div id="panel-history" class="mode-panel">
        <div class="hist-banner">历史验证数据 — 批量回测底座 + 每日收盘候选增量；未有次日行情时保持待验证</div>
        <div class="kpi-strip">
          <div class="kpi"><span class="kpi__label">候选数</span><strong class="kpi__value" id="h-kpiCount">-</strong><small class="kpi__sub" id="h-kpiDate">-</small></div>
          <div class="kpi"><span class="kpi__label">命中率</span><strong class="kpi__value" id="h-kpiHitRate">-</strong><small class="kpi__sub" id="h-kpiHits">-</small></div>
          <div class="kpi"><span class="kpi__label">日期范围</span><strong class="kpi__value" id="h-kpiRange">-</strong><small class="kpi__sub" id="h-kpiDays">-</small></div>
          <div class="kpi"><span class="kpi__label">当前日期</span><strong class="kpi__value" id="h-kpiSelected">-</strong><small class="kpi__sub">下方切换日期</small></div>
        </div>
        <div class="hist-nav">
          <label class="hist-nav__label">历史日期:</label>
          <select id="histDateSelect" class="hist-nav__select"></select>
          <button id="histPrev" class="hist-nav__btn" disabled>&#9664; 前一天</button>
          <button id="histNext" class="hist-nav__btn" disabled>后一天 &#9654;</button>
        </div>
        <div class="tbl-section">
          <div class="tbl-header"><h2>历史候选验证</h2><span class="count hist" id="h-selCount">0</span></div>
          <div class="tbl-scroll" id="h-candidateScroll">
            <table><thead><tr><th>序</th><th>代码</th><th>名称</th><th class="num">概率</th><th class="num">命中</th><th class="num">最高收益%</th><th class="num">收盘收益%</th><th class="num">收盘价</th><th class="num">换手</th><th>验证日</th></tr></thead><tbody id="h-candidateRows"></tbody></table>
            <div id="h-candidateEmpty" class="tbl-empty">选择日期查看历史候选</div>
          </div>
        </div>
      </div>
    </main>

    <!-- RIGHT INSPECTOR -->
    <aside class="inspector" id="inspector">
      <div class="insp-header">
        <h3 id="inspTitle">详情</h3>
        <button class="insp-close" id="inspClose" title="收起 Inspector">&times;</button>
      </div>

      <div id="inspProvenance">
        <div class="insp-section">
          <div class="insp-section-title">运行溯源</div>
          <dl class="detail-grid" id="inspRunGrid"></dl>
        </div>
      </div>

      <div id="inspStock" style="display:none">
        <div class="insp-section">
          <div class="insp-section-title" id="inspStockHeader">股票详情</div>
          <dl class="detail-grid" id="inspStockGrid"></dl>
        </div>
        <div class="insp-section">
          <div class="insp-section-title">风险标记</div>
          <div class="risk-tags" id="inspRiskTags"></div>
        </div>
      </div>
    </aside>
    <button class="insp-reopen" id="inspReopen" title="打开 Inspector">Inspector &rarr;</button>
  </div>

  <!-- ===== DIAGNOSTICS DRAWER ===== -->
  <div class="drawer" id="drawer">
    <div class="drawer-bar" id="drawerBar">
      <div class="drawer-bar__left">
        <span>运行日志</span>
        <div class="drawer-tabs">
          <button class="drawer-tab active" data-log="formal">Formal</button>
          <button class="drawer-tab" data-log="postclose">Postclose</button>
          <button class="drawer-tab" data-log="test">Test</button>
          <button class="drawer-tab" data-log="replay">Replay</button>
        </div>
      </div>
      <span class="drawer-chevron" id="drawerChevron">&#9650;</span>
    </div>
    <div class="drawer-body">
      <div class="drawer-content">
        <div class="drawer-logs"><pre id="drawerLogs"></pre></div>
        <div class="drawer-artifacts">
          <h4>Artifacts</h4>
          <div id="drawerArtifacts"></div>
        </div>
      </div>
    </div>
  </div>

<script>
const $ = id => document.getElementById(id);
const fmtPct = v => { const n = Number(v); return Number.isFinite(n) ? (n * 100).toFixed(2) + "%" : "-"; };
const fmtNum = (v, d = 2) => { const n = Number(v); return Number.isFinite(n) ? n.toFixed(d) : "-"; };
const fmtSec = v => { const n = Number(v); return Number.isFinite(n) ? n.toFixed(1) + "s" : "-"; };

let _allData = {};
let _activeLogMode = "formal";
let _selectedRow = null;
let _selectedMode = null;

// --- Init ---
(function init() {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  $("today").value = `${d.getFullYear()}-${m}-${day}`;
})();

// --- Clock ---
function updateClock() {
  const now = new Date();
  $("topClock").textContent = String(now.getHours()).padStart(2,"0") + ":" + String(now.getMinutes()).padStart(2,"0") + ":" + String(now.getSeconds()).padStart(2,"0");
}
updateClock();
setInterval(updateClock, 1000);

// --- Tabs ---
document.querySelectorAll(".mode-tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".mode-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    $("panel-" + btn.dataset.mode).classList.add("active");
    _selectedRow = null;
    _selectedMode = null;
    updateInspector();
    updateDrawer();
  });
});

// --- Toggle collapse ---
function toggleCollapse(id) {
  const el = $(id);
  if (el) el.classList.toggle("collapsed");
}

// --- Drawer ---
$("drawerBar").addEventListener("click", e => {
  if (e.target.closest(".drawer-tab")) return;
  $("drawer").classList.toggle("expanded");
});
document.querySelectorAll(".drawer-tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".drawer-tab").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    _activeLogMode = btn.dataset.log;
    updateDrawer();
  });
});

// --- Inspector toggle ---
$("inspClose").addEventListener("click", () => {
  $("appBody").classList.add("insp-off");
  $("appBody").classList.remove("insp-on");
});
$("inspReopen").addEventListener("click", () => {
  $("appBody").classList.remove("insp-off");
  $("appBody").classList.add("insp-on");
});
// Default: collapse inspector on narrow screens
if (window.innerWidth <= 1400) {
  $("appBody").classList.add("insp-off");
}

// --- Button time control ---
function updateButtonStates() {
  const now = new Date();
  const mod = now.getHours() * 60 + now.getMinutes();
  const todayStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-${String(now.getDate()).padStart(2,"0")}`;
  const selectedDate = $("today").value;
  const formalFrozen = _allData?.formal?.outputs?.summary?.is_formal_valid === true;
  $("formalRun").disabled = formalFrozen || (mod < 14 * 60 + 57 && selectedDate === todayStr);
  $("formalRun").textContent = formalFrozen ? "已冻结" : "正式跑";
  const postcloseDisabled = selectedDate !== todayStr || mod < 15 * 60;
  $("postcloseRun").disabled = postcloseDisabled;
  $("postcloseRun").title = selectedDate !== todayStr ? "收盘验证只能对今天执行；历史日期只能查看已有结果" : (mod < 15 * 60 ? "收盘验证只能在 15:00 后执行" : "");
  $("replayRun").disabled = mod < 15 * 60 && selectedDate === todayStr;
}
updateButtonStates();
setInterval(updateButtonStates, 1000);

// --- API ---
async function postJSON(url, body) {
  const res = await fetch(url, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body || {}) });
  if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || res.statusText); }
  return res.json();
}

async function startRun(mode) {
  const body = { today: $("today").value, prob_threshold: Number($("threshold").value), topk: Number($("topk").value) };
  let endpoint;
  if (mode === "formal") {
    endpoint = "/api/run";
    body.target_time = "14:57";
    const now = new Date();
    const sec = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
    body.no_wait = sec >= 14*3600 + 56*60 + 30;
    if (sec > 14*3600 + 58*60 + 30) body.saved_only = true;
    body.test_mode = false;
  } else if (mode === "postclose") {
    endpoint = "/api/postclose-run";
  } else if (mode === "replay") {
    endpoint = "/api/replay-run";
    body.target_time = "14:57";
    body.no_wait = true;
  } else {
    endpoint = "/api/test-run";
    body.target_time = "14:57";
  }
  try { await postJSON(endpoint, body); } catch (err) { await refresh(); alert(err.message); return; }
  document.querySelectorAll(".mode-tab").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".mode-panel").forEach(p => p.classList.remove("active"));
  document.querySelector(`.mode-tab[data-mode="${mode}"]`).classList.add("active");
  $("panel-" + mode).classList.add("active");
  await refresh();
}

$("formalRun").addEventListener("click", () => startRun("formal"));
$("postcloseRun").addEventListener("click", () => startRun("postclose"));
$("testRun").addEventListener("click", () => startRun("test"));
$("replayRun").addEventListener("click", () => startRun("replay"));
$("stopFormal").addEventListener("click", async () => { try { await postJSON("/api/stop", { mode: "formal" }); await refresh(); } catch (e) { alert(e.message); } });
$("stopPostclose").addEventListener("click", async () => { try { await postJSON("/api/stop", { mode: "postclose" }); await refresh(); } catch (e) { alert(e.message); } });

// --- Rendering ---
function appendCell(tr, value, cls) {
  const td = document.createElement("td");
  if (cls) td.className = cls;
  if (value instanceof Node) td.appendChild(value);
  else td.textContent = value ?? "";
  tr.appendChild(td);
}

function makeFlags(row) {
  const f = document.createDocumentFragment();
  const tradable = String(row.tradable || "").toLowerCase();
  if (tradable === "true") { const s = document.createElement("span"); s.className = "flag flag-ok"; s.textContent = "可买"; f.appendChild(s); }
  if (row.is_limit_up === "True" || row.is_limit_up === true) { const s = document.createElement("span"); s.className = "flag flag-limit"; s.textContent = "涨停"; f.appendChild(s); }
  if (row.is_limit_down === "True" || row.is_limit_down === true) { const s = document.createElement("span"); s.className = "flag flag-limit"; s.textContent = "跌停"; f.appendChild(s); }
  if (row.is_suspended === "True" || row.is_suspended === true) { const s = document.createElement("span"); s.className = "flag flag-halt"; s.textContent = "停牌"; f.appendChild(s); }
  if (String(row.name || "").includes("ST")) { const s = document.createElement("span"); s.className = "flag flag-st"; s.textContent = "ST"; f.appendChild(s); }
  return f;
}

function renderRows(tbodyId, emptyId, rows, mode) {
  const tbody = $(tbodyId);
  const empty = $(emptyId);
  tbody.textContent = "";
  empty.style.display = rows && rows.length ? "none" : "block";
  for (let i = 0; i < (rows || []).length; i++) {
    const row = rows[i];
    const tr = document.createElement("tr");
    tr.dataset.idx = i;
    tr.dataset.mode = mode;
    appendCell(tr, row.selector_rank || row.rank || (i + 1));
    appendCell(tr, row.symbol || "");
    appendCell(tr, row.name || "");
    appendCell(tr, fmtPct(row.probability), "num");
    appendCell(tr, fmtNum(row.latest_price, 2), "num");
    appendCell(tr, fmtNum(row.pct_change, 2), "num");
    appendCell(tr, fmtNum(row.turnover_today, 2), "num");
    appendCell(tr, makeFlags(row));
    tr.addEventListener("click", () => selectStock(row, mode, tr));
    tbody.appendChild(tr);
  }
}

function selectStock(row, mode, trEl) {
  _selectedRow = row;
  _selectedMode = mode;
  document.querySelectorAll("tbody tr.selected").forEach(tr => tr.classList.remove("selected"));
  if (trEl) trEl.classList.add("selected");
  if ($("appBody").classList.contains("insp-off")) $("appBody").classList.remove("insp-off");
  updateInspector();
}

function updateInspector() {
  if (_selectedRow) {
    $("inspProvenance").style.display = "none";
    $("inspStock").style.display = "block";
    $("inspTitle").textContent = `${_selectedRow.symbol || ""} ${_selectedRow.name || ""}`;
    $("inspStockHeader").textContent = `${_selectedRow.name || ""} 详情`;
    const grid = $("inspStockGrid");
    grid.innerHTML = "";
    const fields = [
      ["代码", _selectedRow.symbol],
      ["名称", _selectedRow.name],
      ["概率", fmtPct(_selectedRow.probability)],
      ["现价", fmtNum(_selectedRow.latest_price, 2)],
      ["涨跌%", fmtNum(_selectedRow.pct_change, 2)],
      ["换手", fmtNum(_selectedRow.turnover_today, 2)],
      ["selector_rank", _selectedRow.selector_rank || "-"],
      ["selector_rule", _selectedRow.selector_rule || "-"],
      ["tradable", _selectedRow.tradable || "-"],
    ];
    for (const [k, v] of fields) {
      const dt = document.createElement("dt"); dt.textContent = k;
      const dd = document.createElement("dd"); dd.textContent = v || "-";
      grid.appendChild(dt); grid.appendChild(dd);
    }
    const tags = $("inspRiskTags");
    tags.innerHTML = "";
    tags.appendChild(makeFlags(_selectedRow));
    if (!tags.childNodes.length) { const s = document.createElement("span"); s.className = "flag flag-ok"; s.textContent = "无风险"; tags.appendChild(s); }
  } else {
    $("inspStock").style.display = "none";
    $("inspProvenance").style.display = "block";
    $("inspTitle").textContent = "详情";
    const activeTab = document.querySelector(".mode-tab.active");
    const mode = activeTab ? activeTab.dataset.mode : "formal";
    const data = (_allData[mode] || {});
    const summary = ((data.outputs || {}).summary) || {};
    const grid = $("inspRunGrid");
    grid.innerHTML = "";
    const items = [
      ["run_id", data.run_id || "-"],
      ["run_mode", summary.run_mode || mode],
      ["status", data.status || "-"],
      ["started_at", data.started_at || "-"],
      ["ended_at", data.ended_at || "-"],
      ["target_date", summary.target_date || data.today || "-"],
      ["generated_at", summary.generated_at || "-"],
      ["asof_time", summary.asof_time || "-"],
      ["output_grade", summary.output_grade || "-"],
      ["total_stocks", summary.total_stocks || "-"],
      ["selected_features", summary.selected_feature_count || "-"],
    ];
    if (mode === "formal") {
      items.push(["formal_valid", summary.is_formal_valid === true ? "YES" : summary.is_formal_valid === false ? "NO" : "-"]);
      items.push(["valid_reason", summary.formal_valid_reason || "-"]);
      items.push(["snapshot_status", summary.snapshot_time_status || "-"]);
      items.push(["snapshot_captured", summary.snapshot_captured_at || "-"]);
      items.push(["quote_time", [summary.snapshot_quote_min, summary.snapshot_quote_max].filter(Boolean).join(" - ") || "-"]);
      items.push(["saved_snapshot", summary.saved_snapshot_used ? "YES" : "-"]);
    }
    if (mode === "postclose") {
      items.push(["data_complete", summary.is_postclose_complete === true ? "YES" : summary.is_postclose_complete === false ? "NO" : "-"]);
      items.push(["incomplete_reasons", (summary.postclose_incomplete_reasons || []).join(", ") || "-"]);
      items.push(["snapshot_source", summary.postclose_snapshot_source || "-"]);
      items.push(["fetch_time", summary.postclose_data_fetch_time || "-"]);
    }
    for (const [k, v] of items) {
      const dt = document.createElement("dt"); dt.textContent = k;
      const dd = document.createElement("dd"); dd.textContent = v;
      if (k === "formal_valid") dd.className = v === "YES" ? "ok" : v === "NO" ? "bad" : "";
      if (k === "data_complete") dd.className = v === "YES" ? "ok" : v === "NO" ? "bad" : "";
      if (k === "status" && v === "failed") dd.className = "bad";
      grid.appendChild(dt); grid.appendChild(dd);
    }
  }
}

function updateDrawer() {
  const data = _allData[_activeLogMode] || {};
  $("drawerLogs").textContent = (data.logs || []).join("\n");
  const logPre = $("drawerLogs");
  logPre.scrollTop = logPre.scrollHeight;
  const paths = ((data.outputs || {}).paths) || {};
  const cont = $("drawerArtifacts");
  cont.innerHTML = "";
  const labels = [["selector_csv", "候选 CSV"], ["full_csv", "全量 CSV"], ["timing_json", "耗时 JSON"], ["report_md", "报告"]];
  for (const [key, label] of labels) {
    const val = paths[key] || "-";
    const row = document.createElement("div");
    row.className = "artifact-row";
    const labelSpan = document.createElement("span");
    labelSpan.className = "art-label";
    labelSpan.textContent = label;
    row.appendChild(labelSpan);
    row.appendChild(document.createTextNode(val));
    if (val !== "-") {
      row.title = "点击复制路径";
      row.addEventListener("click", () => { navigator.clipboard.writeText(val).catch(() => {}); row.style.background = "#D1FAE5"; setTimeout(() => { row.style.background = ""; }, 600); });
    }
    cont.appendChild(row);
  }
}

function renderPill(el, value, okWhen) {
  if (value == null) { el.textContent = "-"; el.className = "pill"; return; }
  el.textContent = String(value);
  el.className = okWhen(value) ? "pill" : "pill bad";
}

function modeStatusDot(data) {
  const s = data.status || "idle";
  if (s === "running" || s === "stopping") return "running";
  if (s === "failed" || s === "stopped") return "bad";
  if (s === "completed") return "ok";
  return "";
}

function renderPanel(prefix, data, mode) {
  const o = data.outputs || {};
  const s = o.summary || {};
  const status = data.status || "idle";

  $(prefix + "-kpiCount").textContent = s.selector_count ?? (o.candidates ? o.candidates.length : "-");
  $(prefix + "-kpiRule").textContent = s.selector_rule || "-";
  $(prefix + "-kpiTopProb").textContent = fmtPct(s.top_probability);
  $(prefix + "-kpiAsof").textContent = s.asof_time || s.generated_at || "-";
  $(prefix + "-kpiLiveSec").textContent = fmtSec(s.live_sec);
  $(prefix + "-kpiWithin").textContent = s.within_180s === true ? "within 180s" : (s.within_180s === false ? ">180s" : "-");
  $(prefix + "-kpiStatus").textContent = data.message || status;
  $(prefix + "-kpiElapsed").textContent = data.elapsed_sec ? fmtSec(data.elapsed_sec) : (data.ended_at || "-");

  $(prefix + "-selCount").textContent = s.selector_count ?? (o.candidates ? o.candidates.length : 0);
  $(prefix + "-topCount").textContent = o.top_rows ? o.top_rows.length : 0;

  renderRows(prefix + "-candidateRows", prefix + "-candidateEmpty", o.candidates || [], mode);
  renderRows(prefix + "-topRows", prefix + "-topEmpty", o.top_rows || [], mode);

  // Provenance
  if (mode === "formal") {
    const fv = s.is_formal_valid;
    const fvEl = $(prefix + "-provValid");
    fvEl.textContent = fv === true ? "YES" : fv === false ? "NO" : "-";
    fvEl.className = "prov-value" + (fv === true ? " ok" : fv === false ? " bad" : "");
    $(prefix + "-provGrade").textContent = s.output_grade || "-";
    $(prefix + "-provSnap").textContent = s.snapshot_time_status || "-";
    $(prefix + "-provQuote").textContent = [s.snapshot_quote_min, s.snapshot_quote_max].filter(Boolean).join("-") || "-";
    $(prefix + "-provLp").textContent = s.limit_pool_time_status || "-";
  }
  if (mode === "postclose") {
    const pc = s.is_postclose_complete;
    const pcEl = $(prefix + "-provComplete");
    pcEl.textContent = pc === true ? "YES" : pc === false ? "NO" : "-";
    pcEl.className = "prov-value" + (pc === true ? " ok" : pc === false ? " bad" : "");
    $(prefix + "-provGrade").textContent = s.output_grade || "-";
    $(prefix + "-provSnap").textContent = s.postclose_snapshot_source || s.snapshot_time_status || "-";
    $(prefix + "-provFetch").textContent = s.postclose_data_fetch_time || "-";
    const checks = s.postclose_checks || {};
    $(prefix + "-provCov").textContent = checks.latest_price_coverage != null ? fmtPct(checks.latest_price_coverage) : "-";
  }
}

function render(allData) {
  _allData = allData;
  const formal = allData.formal || {};
  const postclose = allData.postclose || {};
  const test = allData.test || {};
  const fSummary = ((formal.outputs || {}).summary) || {};

  // Top bar
  $("topDate").textContent = fSummary.target_date || formal.today || "-";
  $("topRunId").textContent = formal.run_id ? "run:" + formal.run_id : "";
  $("topFeatures").textContent = fSummary.selected_feature_count ? fSummary.selected_feature_count + " features" : "";

  // Formal gate badge
  const gate = $("formalGate");
  const gateLabel = $("formalGateLabel");
  if (formal.status === "running") {
    gate.className = "gate gate--running"; gateLabel.textContent = "正在运行";
  } else if (formal.status === "completed" && fSummary.is_formal_valid === true) {
    gate.className = "gate gate--valid"; gateLabel.textContent = "正式候选有效";
  } else if (formal.status === "completed" && fSummary.is_formal_valid === false) {
    gate.className = "gate gate--invalid"; gateLabel.textContent = "正式候选无效";
  } else if (formal.status === "failed" || formal.status === "stopped") {
    gate.className = "gate gate--invalid"; gateLabel.textContent = formal.message || "运行失败";
  } else if (postclose.status === "running") {
    gate.className = "gate gate--running"; gateLabel.textContent = "收盘验证中";
  } else if (test.status === "running") {
    gate.className = "gate gate--running"; gateLabel.textContent = "测试运行中";
  } else if (formal.message) {
    gate.className = "gate gate--idle"; gateLabel.textContent = formal.message;
  } else {
    gate.className = "gate gate--idle"; gateLabel.textContent = "等待运行";
  }

  // Tab dots
  const dotF = $("dotFormal"); dotF.className = "mode-tab__dot " + modeStatusDot(formal);
  const dotPC = $("dotPostclose"); dotPC.className = "mode-tab__dot " + (postclose.status === "completed" ? "warn" : modeStatusDot(postclose));
  const dotT = $("dotTest"); dotT.className = "mode-tab__dot " + (test.status === "completed" ? "test-ok" : modeStatusDot(test));
  // History dot is set by loadHistoricalDates()
  const replay = allData.replay || {};
  const dotR = $("dotReplay"); dotR.className = "mode-tab__dot " + (replay.status === "completed" ? "replay-ok" : modeStatusDot(replay));

  // Render panels
  renderPanel("f", formal, "formal");
  renderPanel("pc", postclose, "postclose");
  renderPanel("t", test, "test");
  renderPanel("rp", replay, "replay");

  // Readiness — prefer completed summary, fallback to running readiness from logs
  const rdOk = (el, ok) => { el.className = "rd-dot" + (ok === true ? " ok" : ok === false ? " bad" : ""); };
  const rd = formal.readiness || {};
  const hasSum = fSummary.selected_feature_count != null;

  rdOk($("rdTrading"), fSummary.target_date || formal.today ? true : null);
  rdOk($("rdBundle"), hasSum ? (fSummary.selected_feature_count > 0) : (rd.bundle_loaded || null));
  const featureGateOk = hasSum
    ? (fSummary.hard_moneyflow_selected_count === 0 && fSummary.postclose_forbidden_selected_count === 0 && fSummary.ths_selected_count === 0 && fSummary.has_c004 === false && fSummary.has_c009 === false)
    : (rd.p0_hard_moneyflow === 0 && rd.p0_postclose === 0 && rd.p0_ths_sector === 0 && rd.p0_c004 === false && rd.p0_c009 === false);
  rdOk($("rdFeatureGate"), hasSum ? featureGateOk : (rd.p0_hard_moneyflow != null ? featureGateOk : null));
  rdOk($("rdCache1430"), fSummary.snapshot_captured_at ? true : (rd.price_cache_1430 === "captured" ? true : (formal.status === "running" ? false : null)));
  const snapOk = fSummary.snapshot_time_status === "within_window" || fSummary.snapshot_time_status === "verified";
  rdOk($("rdSnapshot"), snapOk ? true : (rd.snapshot_1457 === "captured" ? true : (fSummary.snapshot_time_status && !snapOk ? false : (formal.status === "running" ? false : null))));

  // P0 pills — fallback to readiness
  renderPill($("p0Hard"), hasSum ? fSummary.hard_moneyflow_selected_count : rd.p0_hard_moneyflow, v => Number(v) === 0);
  renderPill($("p0PostClose"), hasSum ? fSummary.postclose_forbidden_selected_count : rd.p0_postclose, v => Number(v) === 0);
  renderPill($("p0Ths"), hasSum ? fSummary.ths_selected_count : rd.p0_ths_sector, v => Number(v) === 0);
  renderPill($("p0C004"), hasSum ? fSummary.has_c004 : rd.p0_c004, v => v === false || v === "False" || v === "false");
  renderPill($("p0C009"), hasSum ? fSummary.has_c009 : rd.p0_c009, v => v === false || v === "False" || v === "false");

  // Stop buttons
  $("stopFormal").disabled = !(formal.status === "running" || formal.status === "stopping");
  $("stopPostclose").disabled = !(postclose.status === "running" || postclose.status === "stopping");

  // Update drawer and inspector
  updateDrawer();
  updateInspector();
}

async function refresh() {
  const selectedDate = $("today").value;
  const qs = selectedDate ? `?today=${encodeURIComponent(selectedDate)}` : "";
  try { const res = await fetch("/api/status" + qs); render(await res.json()); $("connWarn").classList.remove("show"); } catch (e) { $("connWarn").classList.add("show"); }
}

refresh();
setInterval(refresh, 2000);

$("today").addEventListener("change", async () => {
  updateButtonStates();
  await refresh();
});

// --- History tab ---
let _histDates = [];
let _histData = null;
let _histCurrentIdx = -1;

async function loadHistoricalDates() {
  try {
    const res = await fetch("/api/historical-dates");
    const data = await res.json();
    _histDates = data.dates || [];
    $("dotHistory").className = "mode-tab__dot" + (_histDates.length > 0 ? " ok" : "");
    // Populate date dropdown (newest first — backend already sorted descending)
    const sel = $("histDateSelect");
    sel.innerHTML = "";
    for (let i = 0; i < _histDates.length; i++) {
      const opt = document.createElement("option");
      opt.value = _histDates[i];
      opt.textContent = _histDates[i];
      sel.appendChild(opt);
    }
    const activeTab = document.querySelector(".mode-tab.active");
    if (_histDates.length > 0 && activeTab && activeTab.dataset.mode === "history" && _histCurrentIdx < 0) {
      loadClosestHistorical();
    }
  } catch (e) {}
}

function _parseDateStr(d) {
  const p = d.split("/").map(Number);
  return p.length === 3 ? new Date(p[0], p[1]-1, p[2]) : new Date(0);
}

function findClosestHistDate(dateStr) {
  if (!_histDates.length) return null;
  const parts = dateStr.split("-");
  if (parts.length !== 3) return _histDates[0];
  const target = new Date(parseInt(parts[0]), parseInt(parts[1])-1, parseInt(parts[2]));
  let best = null;
  for (let i = 0; i < _histDates.length; i++) {
    const d = _parseDateStr(_histDates[i]);
    if (d <= target) { best = _histDates[i]; break; }
  }
  return best || _histDates[0];
}

function loadClosestHistorical() {
  if (_histDates.length === 0) return;
  const closest = findClosestHistDate($("today").value);
  if (closest) loadHistorical(closest);
}

let _histLoadId = 0;
const _histCache = {};

async function loadHistorical(csvDate) {
  if (!csvDate) return;
  const myId = ++_histLoadId;
  $("histPrev").disabled = true;
  $("histNext").disabled = true;
  $("histPrev").classList.add("loading");
  $("histNext").classList.add("loading");
  try {
    let data;
    if (_histCache[csvDate]) {
      data = _histCache[csvDate];
    } else {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(`/api/historical?date=${encodeURIComponent(csvDate)}`, {signal: controller.signal});
      clearTimeout(timer);
      data = await res.json();
      _histCache[csvDate] = data;
    }
    if (myId !== _histLoadId) return;
    _histData = data;
    $("histDateSelect").value = csvDate;
    _histCurrentIdx = _histDates.indexOf(csvDate);
    renderHistory(_histData);
    _prefetchNeighbors();
  } catch (e) {
    if (myId !== _histLoadId) return;
    _histData = null;
  } finally {
    if (myId === _histLoadId) {
      $("histPrev").classList.remove("loading");
      $("histNext").classList.remove("loading");
      $("histPrev").disabled = _histCurrentIdx >= _histDates.length - 1;
      $("histNext").disabled = _histCurrentIdx <= 0;
    }
  }
}

function _prefetchNeighbors() {
  const neighbors = [_histCurrentIdx - 1, _histCurrentIdx + 1];
  for (const idx of neighbors) {
    if (idx >= 0 && idx < _histDates.length && !_histCache[_histDates[idx]]) {
      fetch(`/api/historical?date=${encodeURIComponent(_histDates[idx])}`)
        .then(r => r.json())
        .then(d => { _histCache[_histDates[idx]] = d; })
        .catch(() => {});
    }
  }
}

function renderHistory(data) {
  if (!data) return;
  const rows = data.rows || [];
  const stats = data.stats || {};
  $("h-kpiCount").textContent = stats.total || rows.length;
  $("h-kpiDate").textContent = data.date || "-";
  $("h-kpiHitRate").textContent = stats.hit_rate != null ? stats.hit_rate + "%" : "-";
  $("h-kpiHits").textContent = stats.verified ? `${stats.hits}/${stats.verified}` : "-";
  $("h-kpiRange").textContent = _histDates.length > 0 ? `${_histDates[_histDates.length-1]} ~ ${_histDates[0]}` : "-";
  $("h-kpiDays").textContent = _histDates.length ? `${_histDates.length} 个交易日` : "-";
  $("h-kpiSelected").textContent = data.date || "-";
  $("h-selCount").textContent = rows.length;

  const tbody = $("h-candidateRows");
  const empty = $("h-candidateEmpty");
  tbody.textContent = "";
  empty.style.display = rows.length ? "none" : "block";

  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const tr = document.createElement("tr");
    appendCell(tr, i + 1);
    appendCell(tr, row.symbol || "");
    appendCell(tr, row.name || "");
    appendCell(tr, fmtPct(row.probability), "num");
    const hitSpan = document.createElement("span");
    hitSpan.className = "hit-tag " + (row.hit || "");
    hitSpan.textContent = row.hit === "hit" ? "命中" : row.hit === "miss" ? "未中" : "-";
    appendCell(tr, hitSpan, "num");
    appendCell(tr, row.next_high_return_pct || "-", "num");
    appendCell(tr, row.next_close_return_pct || "-", "num");
    appendCell(tr, row.close || "-", "num");
    const turnover = row["换手"] || row["turnover"] || "-";
    appendCell(tr, turnover, "num");
    appendCell(tr, row.label_date || "-");
    tbody.appendChild(tr);
  }
}

// Date dropdown change
$("histDateSelect").addEventListener("change", () => {
  loadHistorical($("histDateSelect").value);
});

// Prev/Next buttons (dates descending: prev=older=idx+1, next=newer=idx-1)
$("histPrev").addEventListener("click", () => {
  if (_histCurrentIdx < _histDates.length - 1) {
    loadHistorical(_histDates[_histCurrentIdx + 1]);
  }
});
$("histNext").addEventListener("click", () => {
  if (_histCurrentIdx > 0) {
    loadHistorical(_histDates[_histCurrentIdx - 1]);
  }
});

// Keyboard arrow navigation for history tab
document.addEventListener("keydown", (e) => {
  const activeTab = document.querySelector(".mode-tab.active");
  if (!activeTab || activeTab.dataset.mode !== "history") return;
  if (document.activeElement && (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "SELECT")) return;
  if (e.key === "ArrowLeft" && _histCurrentIdx < _histDates.length - 1) {
    e.preventDefault();
    loadHistorical(_histDates[_histCurrentIdx + 1]);
  } else if (e.key === "ArrowRight" && _histCurrentIdx > 0) {
    e.preventDefault();
    loadHistorical(_histDates[_histCurrentIdx - 1]);
  }
});

// When clicking the history tab, auto-load closest available date
document.querySelector('.mode-tab[data-mode="history"]').addEventListener("click", () => {
  if (_histDates.length === 0) {
    loadHistoricalDates().then(loadClosestHistorical).catch(() => {});
    return;
  }
  loadClosestHistorical();
});

// When left date picker changes, also update history if that tab is active
$("today").addEventListener("change", () => {
  const activeTab = document.querySelector(".mode-tab.active");
  if (activeTab && activeTab.dataset.mode === "history") {
    loadClosestHistorical();
  }
  updateButtonStates();
});

// Initial load
loadHistoricalDates();
</script>
</body>
</html>
"""


manager = LiveRunManager()
app = FastAPI(title="Live-strict 14:57 candidate picker")


@app.on_event("startup")
def startup_auto_warmup() -> None:
    manager.auto_warmup_today()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    manager.auto_warmup_today()
    return HTML


@app.get("/api/status")
def api_status(today: str | None = None) -> JSONResponse:
    if today in (None, _today_str()):
        manager.auto_warmup_today()
    return JSONResponse(manager.status(today))


@app.post("/api/run")
def api_run(req: RunRequest) -> JSONResponse:
    if not RUN_SCRIPT.exists():
        raise HTTPException(status_code=500, detail=f"脚本不存在：{RUN_SCRIPT}")
    return JSONResponse(manager.start_formal(req))


@app.post("/api/postclose-run")
def api_postclose_run(req: RunRequest) -> JSONResponse:
    if not RUN_SCRIPT.exists():
        raise HTTPException(status_code=500, detail=f"脚本不存在：{RUN_SCRIPT}")
    return JSONResponse(manager.start_postclose(req))


@app.post("/api/test-run")
def api_test_run(req: RunRequest) -> JSONResponse:
    if not RUN_SCRIPT.exists():
        raise HTTPException(status_code=500, detail=f"脚本不存在：{RUN_SCRIPT}")
    req.no_wait = True
    req.test_mode = True
    return JSONResponse(manager.run_test_once(req))


@app.post("/api/replay-run")
def api_replay_run(req: RunRequest) -> JSONResponse:
    if not RUN_SCRIPT.exists():
        raise HTTPException(status_code=500, detail=f"脚本不存在：{RUN_SCRIPT}")
    return JSONResponse(manager.start_replay(req))


class StopRequest(BaseModel):
    mode: str = "formal"


@app.post("/api/stop")
def api_stop(req: StopRequest) -> JSONResponse:
    return JSONResponse(manager.stop(req.mode))


@app.get("/api/latest")
def api_latest(today: str | None = None) -> JSONResponse:
    return JSONResponse(manager.latest(today))


HISTORICAL_ROLLING_CSV = (
    RUNTIME_ROOT / "reports" / "prediction" / "historical_validation" / "phasec_rolling_history.csv"
)
HISTORICAL_CSV = (
    RUNTIME_ROOT / "reports" / "prediction" / "historical_validation" / "phasec_precise_202604_history.csv"
)
HISTORICAL_FALLBACK_CSV = RUNTIME_ROOT / "reports" / "prediction" / "batch_postclose_all_candidates.csv"
HISTORY_UPDATE_SCRIPT = REPO_ROOT / "scripts" / "update_1457_history.py"
HISTORY_REFRESH_INTERVAL_SECONDS = 120.0
_hist_df: Any | None = None
_hist_dates: list[str] = []
_hist_mtime: float = 0.0
_hist_source: str = ""
_hist_refresh_checked_at: float = 0.0
_hist_refresh_lock = threading.Lock()


def _historical_source_path() -> Path:
    if HISTORICAL_ROLLING_CSV.exists():
        return HISTORICAL_ROLLING_CSV
    return HISTORICAL_CSV if HISTORICAL_CSV.exists() else HISTORICAL_FALLBACK_CSV


def _latest_existing_mtime(paths: list[Path]) -> float:
    latest = 0.0
    for path in paths:
        try:
            if path.exists():
                latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
    return latest


def _latest_formal_output_mtime() -> float:
    latest = 0.0
    try:
        paths = list(REALTIME_OUTPUT_DIR.glob("realtime_1457_m1457_timing_*.json"))
    except OSError:
        return latest
    for path in paths:
        try:
            latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
    return latest


def _refresh_rolling_history_if_needed(force: bool = False) -> None:
    global _hist_df, _hist_mtime, _hist_source, _hist_refresh_checked_at
    now = time.time()
    if not force and now - _hist_refresh_checked_at < HISTORY_REFRESH_INTERVAL_SECONDS:
        return
    with _hist_refresh_lock:
        now = time.time()
        if not force and now - _hist_refresh_checked_at < HISTORY_REFRESH_INTERVAL_SECONDS:
            return
        _hist_refresh_checked_at = now
        dependency_mtime = max(
            _latest_existing_mtime([HISTORICAL_CSV, HISTORICAL_FALLBACK_CSV, HISTORY_UPDATE_SCRIPT]),
            _latest_formal_output_mtime(),
        )
        try:
            rolling_mtime = HISTORICAL_ROLLING_CSV.stat().st_mtime
        except OSError:
            rolling_mtime = 0.0
        if rolling_mtime >= dependency_mtime:
            return
        if not HISTORY_UPDATE_SCRIPT.exists():
            return
        try:
            result = subprocess.run(
                [sys.executable, str(HISTORY_UPDATE_SCRIPT)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except Exception as exc:
            print(f"[history] rolling refresh skipped: {exc}", flush=True)
            return
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            reason = detail[-1] if detail else f"exit {result.returncode}"
            print(f"[history] rolling refresh failed: {reason}", flush=True)
            return
        _hist_df = None
        _hist_mtime = 0.0
        _hist_source = ""


def _parse_history_date(value: object) -> datetime | None:
    text = str(value or "").strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def _history_date_key(value: object) -> str:
    dt = _parse_history_date(value)
    return dt.strftime("%Y-%m-%d") if dt else str(value or "")


def _history_date_display(value: object) -> str:
    dt = _parse_history_date(value)
    return f"{dt.year}/{dt.month}/{dt.day}" if dt else str(value or "")


def _load_historical():
    global _hist_df, _hist_dates, _hist_mtime, _hist_source
    _refresh_rolling_history_if_needed()
    source_path = _historical_source_path()
    if not source_path.exists():
        import pandas as pd

        _hist_df = pd.DataFrame()
        _hist_dates = []
        return
    mtime = source_path.stat().st_mtime
    source = str(source_path)
    if _hist_df is not None and mtime == _hist_mtime and source == _hist_source:
        return
    import pandas as pd
    _hist_mtime = mtime
    _hist_source = source
    try:
        _hist_df = pd.read_csv(source_path, encoding="utf-8-sig", dtype=str)
    except Exception:
        _hist_df = pd.DataFrame()
        _hist_dates = []
        return
    if len(_hist_df) > 0 and "date" in _hist_df.columns:
        _hist_df["_history_date_key"] = _hist_df["date"].map(_history_date_key)
        _hist_df["date"] = _hist_df["date"].map(_history_date_display)
        if "symbol" in _hist_df.columns:
            _hist_df["symbol"] = (
                _hist_df["symbol"]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.zfill(6)
            )
            _hist_df["_history_symbol_key"] = _hist_df["symbol"]
        if {"_history_date_key", "_history_symbol_key"}.issubset(_hist_df.columns):
            if "probability" in _hist_df.columns:
                _hist_df["_history_probability_num"] = pd.to_numeric(
                    _hist_df["probability"], errors="coerce"
                )
                _hist_df = _hist_df.sort_values(
                    ["_history_date_key", "_history_probability_num", "_history_symbol_key"],
                    ascending=[True, False, True],
                )
            _hist_df = _hist_df.drop_duplicates(
                subset=["_history_date_key", "_history_symbol_key"],
                keep="first",
            ).drop(columns=["_history_probability_num"], errors="ignore")
        _hist_dates = sorted(
            _hist_df["date"].dropna().unique().tolist(),
            key=lambda d: _parse_history_date(d) or datetime.min,
            reverse=True,
        )
    else:
        _hist_dates = []


@app.get("/api/historical-dates")
def api_historical_dates() -> JSONResponse:
    _load_historical()
    return JSONResponse({"dates": _hist_dates})


@app.get("/api/historical")
def api_historical(date: str | None = None) -> JSONResponse:
    _load_historical()
    if _hist_df is None or len(_hist_df) == 0:
        return JSONResponse({"rows": [], "dates": _hist_dates, "stats": {}})
    if not date:
        date = _hist_dates[0] if _hist_dates else None
    if not date:
        return JSONResponse({"rows": [], "dates": _hist_dates, "stats": {}})
    key = _history_date_key(date)
    if "_history_date_key" in _hist_df.columns:
        day = _hist_df[_hist_df["_history_date_key"] == key].copy()
    else:
        day = _hist_df[_hist_df["date"] == date].copy()
    day = day.drop(columns=["_history_date_key", "_history_symbol_key"], errors="ignore")
    rows = day.where(day.notna(), None).to_dict(orient="records") if len(day) > 0 else []
    verified = [r for r in rows if r.get("hit") in ("hit", "miss")]
    hits = sum(1 for r in verified if r["hit"] == "hit")
    stats = {
        "total": len(rows),
        "verified": len(verified),
        "hits": hits,
        "hit_rate": round(hits / len(verified) * 100, 2) if verified else 0,
    }
    return JSONResponse({"rows": rows, "date": _history_date_display(date), "dates": _hist_dates, "stats": stats})


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the live-strict 14:57 candidate picker web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
