from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = Path("E:/ashare_similarity_runtime")
REPORT_DIR = RUNTIME_ROOT / "data" / "reports" / "prediction"
CACHE_ROOT = RUNTIME_ROOT / "data" / "cache" / "prediction" / "tushare"
DOCS_DIR = REPO_ROOT / "docs"
OUT_STEM = os.environ.get("FULL_EXPLORATION_OUT_STEM") or datetime.now().strftime("%Y%m%d")

EXTRA_SOURCE_PATHS = {
    "raw_bars_daily": RUNTIME_ROOT / "data" / "raw" / "bars" / "daily",
    "raw_bars_5": RUNTIME_ROOT / "data" / "raw" / "bars" / "5",
}


RELEVANT_DOC_PATTERNS = [
    "1457",
    "14点57",
    "PhaseC",
    "S2",
    "全因子",
    "因子",
    "训练",
    "交接",
    "审计",
    "计划",
]

RELEVANT_SCRIPT_PATTERNS = [
    "1457",
    "phasec",
    "phaseC",
    "factor",
    "feature",
    "u95",
    "optuna",
    "strategy",
    "live",
    "score",
]

CRITICAL_CACHE_DIRS = [
    "stk_mins_1",
    "stk_mins_5",
    "raw_bars_daily",
    "daily_basic",
    "stk_factor_pro",
    "cyq_perf",
    "moneyflow",
    "limit_list_d",
    "top_list",
    "top_inst",
    "block_trade",
    "pledge_stat_perstock",
    "stk_holdertrade",
    "suspend_d",
    "ths_member",
    "ggt_top10",
    "index_weight",
]


ONE_MINUTE_FACTOR_IDS = {
    *range(189, 194),
    *range(244, 262),
    *range(273, 286),
}

FIRST_WAVE_FACTOR_IDS = {
    *range(189, 194),
    229,
    236,
    244,
    246,
    247,
    248,
    252,
    254,
    258,
    259,
    260,
    270,
    272,
    273,
    279,
    280,
}


KNOWN_BUNDLES = {
    "baseline_s2": REPORT_DIR / "runs" / "gpu_probe_20260509T002433Z_a0ec8105" / "model_bundle.pt",
    "baseline_phasec": REPORT_DIR / "runs" / "gpu_probe_20260509T105830Z_12605e2b" / "model_bundle.pt",
    "pre_new_A_freeze_candidate": REPORT_DIR / "runs" / "gpu_probe_20260514T104524Z_ff246329" / "model_bundle.pt",
}


@dataclass
class EvidenceRow:
    category: str
    path: str
    name: str
    size_bytes: int
    mtime: str
    role: str


@dataclass
class CacheRow:
    source: str
    path: str
    file_count: int
    nested_parquet_count: int
    total_bytes: int
    inferred_layout: str
    market_counts: str
    date_min: str
    date_max: str
    sample_rows: int
    sample_symbols: int
    sample_columns: str
    sampled_time_min: str
    sampled_time_max: str
    sampled_has_1457: str
    sampled_has_pre_1457: str
    completeness_status: str
    gate_severity: str
    note: str


@dataclass
class MinuteSymbolRow:
    source: str
    symbol: str
    market: str
    path: str
    rows: int
    date_min: str
    date_max: str
    unique_dates: int
    has_1457: bool
    date_count_1457: int
    has_1455: bool
    date_count_1455: int
    has_1500: bool
    date_count_1500: int
    sampled: bool


@dataclass
class FeatureCacheRow:
    name: str
    path: str
    size_bytes: int
    mtime: str
    rows: int
    columns: int
    date_min: str
    date_max: str
    has_status_column: bool
    has_label_column: bool
    likely_asof_1457: bool
    schema_note: str


@dataclass
class BundleFeatureRow:
    bundle_id: str
    bundle_path: str
    model_name: str
    model_kind: str
    calibration_used: str
    threshold: float
    selected_count: int
    feature: str
    catalog_family: str
    baseline_family: str
    factor_id: str
    catalog_asof_rule: str
    strict_1457_available: str
    approximated_1457_available: str
    post_close_only: str
    bundle_gate_class: str
    gate_severity: str
    reason: str


@dataclass
class BundleSummaryRow:
    bundle_id: str
    bundle_path: str
    model_name: str
    model_kind: str
    calibration_used: str
    threshold: float
    full_feature_count: int
    selected_count: int
    strict_ok: int
    asof_rewrite_required: int
    proxy_required: int
    blocked: int
    available_flag_with_parent: int
    orphan_available_flag: int
    unknown: int
    champion_eligible_now: bool
    recommended_role: str


@dataclass
class FactorFamilySummaryRow:
    family: str
    total: int
    a: int
    a_rewrite_required: int
    a_pending_data: int
    b: int
    c: int
    d: int
    first_wave_candidates: int
    recommended_action: str
    blocker: str


@dataclass
class S2IncrementSummaryRow:
    scope: str
    feature_count: int
    asof_rewrite_required: int
    proxy_required: int
    orphan_available_flag: int
    strict_ok: int
    unknown: int
    recommendation: str


@dataclass
class SourceTemporalSummaryRow:
    source: str
    layout: str
    sample_units: int
    first_month: str
    last_month: str
    months_present: int
    expected_months_between: int
    missing_months_count: int
    missing_months_sample: str
    has_2017_01: bool
    has_2026_04: bool
    note: str


@dataclass
class BundleFamilyGateRow:
    bundle_id: str
    family: str
    selected_count: int
    asof_rewrite_required: int
    proxy_required: int
    available_flag_with_parent: int
    orphan_available_flag: int
    strict_ok: int
    unknown: int
    recommended_action: str


@dataclass
class ReadinessScorecardRow:
    gate: str
    status: str
    severity: str
    evidence: str
    required_fix: str
    acceptance_check: str


@dataclass
class NextTaskRow:
    priority: int
    task: str
    can_run_now: bool
    blocked_by: str
    deliverable: str
    self_audit: str
    exit_criteria: str


@dataclass
class FactorActionRow:
    priority: int
    factor_scope: str
    factor_count: int
    asof_class: str
    action: str
    blocker: str
    experiment_role: str
    acceptance_check: str


@dataclass
class ExperimentProtocolRow:
    stage_order: int
    dimension: str
    variants: str
    objective: str
    allowed_now: bool
    dependency: str
    primary_metrics: str
    hard_no: str
    promotion_rule: str


@dataclass
class SourceAsofPolicyRow:
    source: str
    file_count: int
    source_policy_class: str
    formal_1457_use: str
    cutoff_rule: str
    risk: str
    required_proof: str


def _mtime(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return ""


def _size(path: Path) -> int:
    try:
        if path.is_file():
            return path.stat().st_size
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    except OSError:
        return 0


def _matches_any(text: str, patterns: list[str]) -> bool:
    low = text.lower()
    return any(p.lower() in low for p in patterns)


def _safe_read_parquet(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_parquet(path)
    except Exception:
        return None


def _date_from_name(path: Path) -> str | None:
    m = re.search(r"(20\d{6})", path.stem)
    return m.group(1) if m else None


def _symbol_from_name(path: Path) -> str | None:
    stem = path.stem
    if re.fullmatch(r"\d{6}(?:\.(?:SZ|SH|BJ))?", stem):
        return stem
    return None


def _detect_layout(files: list[Path]) -> str:
    if not files:
        return "empty"
    date_hits = sum(1 for p in files[:200] if _date_from_name(p))
    symbol_hits = sum(1 for p in files[:200] if _symbol_from_name(p))
    if symbol_hits >= max(3, date_hits):
        return "per_symbol"
    if date_hits >= 3:
        return "per_date"
    return "mixed_or_unknown"


def _datetime_series(df: pd.DataFrame) -> pd.Series | None:
    for col in [
        "trade_time",
        "datetime",
        "bar_time",
        "time",
        "quote_time",
        "date_time",
        "timestamp",
    ]:
        if col in df.columns:
            s = pd.to_datetime(df[col], errors="coerce")
            if s.notna().any():
                return s
    if {"trade_date", "trade_time"}.issubset(df.columns):
        s = pd.to_datetime(
            df["trade_date"].astype(str) + " " + df["trade_time"].astype(str),
            errors="coerce",
        )
        if s.notna().any():
            return s
    if "trade_date" in df.columns:
        s = pd.to_datetime(df["trade_date"], errors="coerce")
        if s.notna().any():
            return s
    return None


def _safe_read_parquet_columns(path: Path, columns: list[str]) -> pd.DataFrame | None:
    try:
        return pd.read_parquet(path, columns=columns)
    except Exception:
        try:
            return pd.read_parquet(path)
        except Exception:
            return None


def build_evidence_index() -> pd.DataFrame:
    rows: list[EvidenceRow] = []

    for folder, category, patterns in [
        (DOCS_DIR, "doc", RELEVANT_DOC_PATTERNS),
        (REPO_ROOT / "scripts", "script", RELEVANT_SCRIPT_PATTERNS),
        (REPO_ROOT / "src", "source", RELEVANT_SCRIPT_PATTERNS),
    ]:
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            if not _matches_any(path.name, patterns):
                continue
            rows.append(
                EvidenceRow(
                    category=category,
                    path=str(path),
                    name=path.name,
                    size_bytes=_size(path),
                    mtime=_mtime(path),
                    role="local_project_context",
                )
            )

    if REPORT_DIR.exists():
        for path in REPORT_DIR.rglob("*"):
            if not path.is_file():
                continue
            if not _matches_any(path.name, RELEVANT_DOC_PATTERNS + RELEVANT_SCRIPT_PATTERNS):
                continue
            role = "report_or_model_artifact"
            if "feature_cache" in path.parts:
                role = "feature_cache_artifact"
            elif "bundle" in path.name.lower():
                role = "bundle_or_manifest"
            rows.append(
                EvidenceRow(
                    category="runtime_report",
                    path=str(path),
                    name=path.name,
                    size_bytes=_size(path),
                    mtime=_mtime(path),
                    role=role,
                )
            )

    runs_root = REPORT_DIR / "runs"
    if runs_root.exists():
        run_dirs = sorted(
            [p for p in runs_root.iterdir() if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:40]
        for path in run_dirs:
            rows.append(
                EvidenceRow(
                    category="run_dir",
                    path=str(path),
                    name=path.name,
                    size_bytes=_size(path),
                    mtime=_mtime(path),
                    role="recent_training_or_scoring_run",
                )
            )

    return pd.DataFrame([asdict(r) for r in rows]).sort_values(
        ["category", "mtime", "name"], ascending=[True, False, True]
    )


def audit_cache_source(source: str) -> CacheRow:
    path = EXTRA_SOURCE_PATHS.get(source, CACHE_ROOT / source)
    if not path.exists():
        return CacheRow(
            source=source,
            path=str(path),
            file_count=0,
            nested_parquet_count=0,
            total_bytes=0,
            inferred_layout="missing",
            market_counts="",
            date_min="",
            date_max="",
            sample_rows=0,
            sample_symbols=0,
            sample_columns="",
            sampled_time_min="",
            sampled_time_max="",
            sampled_has_1457="UNKNOWN",
            sampled_has_pre_1457="UNKNOWN",
            completeness_status="missing",
            gate_severity="P1",
            note="Cache directory does not exist.",
        )

    files = sorted([p for p in path.glob("*.parquet") if p.is_file()])
    nested_files = sorted([p for p in path.rglob("*.parquet") if p.is_file()])
    layout = _detect_layout(files)
    total_bytes = sum(p.stat().st_size for p in files)
    dates = sorted(d for d in (_date_from_name(p) for p in files) if d)
    symbols = sorted(s for s in (_symbol_from_name(p) for p in files) if s)
    market_counts = {}
    markets = sorted({s.split(".")[-1] for s in symbols if "." in s})
    if markets:
        market_counts = {
            market: sum(1 for s in set(symbols) if s.endswith(f".{market}"))
            for market in markets
        }

    sample_files = files[:4] + files[-4:] if len(files) > 8 else files
    sample_rows = 0
    sample_cols: list[str] = []
    time_values: list[pd.Timestamp] = []
    has_1457 = False
    has_pre_1457 = False

    for sample in sample_files:
        df = _safe_read_parquet(sample)
        if df is None:
            continue
        sample_rows += int(len(df))
        if not sample_cols:
            sample_cols = list(map(str, df.columns))
        dt = _datetime_series(df)
        if dt is None:
            continue
        valid = dt.dropna()
        if valid.empty:
            continue
        time_values.extend(valid.iloc[[0, -1]].tolist())
        minute_text = valid.dt.strftime("%H:%M")
        has_1457 = has_1457 or bool(minute_text.eq("14:57").any())
        has_pre_1457 = has_pre_1457 or bool((minute_text >= "14:55").any() and (minute_text <= "14:57").any())

    if time_values:
        sampled_time_min = min(time_values).isoformat()
        sampled_time_max = max(time_values).isoformat()
    else:
        sampled_time_min = ""
        sampled_time_max = ""

    completeness_status = "available"
    gate = "OK"
    note = ""
    if source == "stk_mins_1":
        if len(files) < 3000:
            completeness_status = "incomplete_blocks_true_1457_training"
            gate = "P0"
            note = "1min per-symbol cache is far below full A-share coverage; true 14:57 champion training is blocked."
        elif not has_1457:
            completeness_status = "needs_bar_time_verification"
            gate = "P0"
            note = "1min cache has broad file count but sampled files did not show a 14:57 bar."
    elif source == "stk_mins_5":
        if len(files) < 3000:
            completeness_status = "incomplete"
            gate = "P1"
            note = "5min coverage is below broad A-share expectation."
        else:
            note = "5min cache appears broad; exact 14:57 reconstruction still requires 1min for true cutoff."
    elif source == "raw_bars_daily":
        if len(files) < 3000:
            completeness_status = "incomplete"
            gate = "P1"
            note = "Raw daily bars exist but broad symbol coverage was not reached."
        else:
            note = "Raw daily bars are available outside tushare cache and should satisfy daily OHLCV needs."
    elif source in {"stk_holdertrade", "suspend_d", "ggt_top10", "index_weight"} and len(files) == 0:
        completeness_status = "empty_or_not_backfilled"
        gate = "P1"
        note = "Source is empty; related factors must remain D/B pending unless an alternate asof source is documented."
    elif source == "ths_member" and len(files) < 10:
        completeness_status = "sparse"
        gate = "P1"
        note = "Theme/sector membership cache is sparse; live-safe reconstruction needs evidence."

    if not note:
        note = f"Layout={layout}; sampled {len(sample_files)} files."

    return CacheRow(
        source=source,
        path=str(path),
        file_count=len(files),
        nested_parquet_count=len(nested_files),
        total_bytes=total_bytes,
        inferred_layout=layout,
        market_counts=json.dumps(market_counts, ensure_ascii=False, sort_keys=True),
        date_min=dates[0] if dates else "",
        date_max=dates[-1] if dates else "",
        sample_rows=sample_rows,
        sample_symbols=len(set(symbols)),
        sample_columns="|".join(sample_cols[:80]),
        sampled_time_min=sampled_time_min,
        sampled_time_max=sampled_time_max,
        sampled_has_1457="YES" if has_1457 else "NO",
        sampled_has_pre_1457="YES" if has_pre_1457 else "NO",
        completeness_status=completeness_status,
        gate_severity=gate,
        note=note,
    )


def build_cache_audit() -> pd.DataFrame:
    rows = [audit_cache_source(source) for source in CRITICAL_CACHE_DIRS]
    if CACHE_ROOT.exists():
        known = set(CRITICAL_CACHE_DIRS)
        for path in sorted([p for p in CACHE_ROOT.iterdir() if p.is_dir() and p.name not in known]):
            files = list(path.rglob("*.parquet"))
            rows.append(
                CacheRow(
                    source=path.name,
                    path=str(path),
                    file_count=len(files),
                    nested_parquet_count=len(files),
                    total_bytes=sum(p.stat().st_size for p in files),
                    inferred_layout=_detect_layout(sorted(files)),
                    market_counts="",
                    date_min="",
                    date_max="",
                    sample_rows=0,
                    sample_symbols=0,
                    sample_columns="",
                    sampled_time_min="",
                    sampled_time_max="",
                    sampled_has_1457="UNKNOWN",
                    sampled_has_pre_1457="UNKNOWN",
                    completeness_status="unclassified_source",
                    gate_severity="INFO",
                    note="Discovered additional cache source; not yet assigned a factor gate.",
                )
            )
    return pd.DataFrame([asdict(r) for r in rows])


def _sample_file_list(files: list[Path], max_files: int) -> list[Path]:
    if len(files) <= max_files:
        return files
    head = files[: max_files // 3]
    mid_start = max(0, len(files) // 2 - max_files // 6)
    mid = files[mid_start : mid_start + max_files // 3]
    tail = files[-(max_files - len(head) - len(mid)) :]
    dedup = {str(p): p for p in [*head, *mid, *tail]}
    return list(dedup.values())


def build_minute_symbol_audit() -> pd.DataFrame:
    rows: list[MinuteSymbolRow] = []
    for source, max_files in [("stk_mins_1", 24), ("stk_mins_5", 30)]:
        path = CACHE_ROOT / source
        files = sorted([p for p in path.glob("*.parquet") if p.is_file()]) if path.exists() else []
        sample = _sample_file_list(files, max_files)
        for file_path in sample:
            symbol = _symbol_from_name(file_path) or file_path.stem
            market = symbol.split(".")[-1] if "." in symbol else ""
            df = _safe_read_parquet_columns(file_path, ["trade_time"])
            if df is None or "trade_time" not in df.columns:
                rows.append(
                    MinuteSymbolRow(
                        source=source,
                        symbol=symbol,
                        market=market,
                        path=str(file_path),
                        rows=0,
                        date_min="",
                        date_max="",
                        unique_dates=0,
                        has_1457=False,
                        date_count_1457=0,
                        has_1455=False,
                        date_count_1455=0,
                        has_1500=False,
                        date_count_1500=0,
                        sampled=True,
                    )
                )
                continue
            dt = pd.to_datetime(df["trade_time"], errors="coerce").dropna()
            if dt.empty:
                date_min = date_max = ""
                unique_dates = 0
                time_by_date = pd.DataFrame(columns=["date", "time"])
            else:
                date_min = str(dt.min().date())
                date_max = str(dt.max().date())
                time_by_date = pd.DataFrame(
                    {"date": dt.dt.date.astype(str), "time": dt.dt.strftime("%H:%M")}
                )
                unique_dates = int(time_by_date["date"].nunique())

            def date_count(target: str) -> int:
                if time_by_date.empty:
                    return 0
                return int(time_by_date.loc[time_by_date["time"] == target, "date"].nunique())

            c1457 = date_count("14:57")
            c1455 = date_count("14:55")
            c1500 = date_count("15:00")
            rows.append(
                MinuteSymbolRow(
                    source=source,
                    symbol=symbol,
                    market=market,
                    path=str(file_path),
                    rows=int(len(df)),
                    date_min=date_min,
                    date_max=date_max,
                    unique_dates=unique_dates,
                    has_1457=c1457 > 0,
                    date_count_1457=c1457,
                    has_1455=c1455 > 0,
                    date_count_1455=c1455,
                    has_1500=c1500 > 0,
                    date_count_1500=c1500,
                    sampled=True,
                )
            )
    return pd.DataFrame([asdict(r) for r in rows])


def build_feature_cache_audit() -> pd.DataFrame:
    fc_dir = REPORT_DIR / "feature_cache"
    if not fc_dir.exists():
        return pd.DataFrame()
    files = sorted(
        [p for p in fc_dir.glob("*.parquet") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:30]
    rows: list[FeatureCacheRow] = []
    for path in files:
        df = _safe_read_parquet(path)
        if df is None:
            rows.append(
                FeatureCacheRow(
                    name=path.name,
                    path=str(path),
                    size_bytes=_size(path),
                    mtime=_mtime(path),
                    rows=0,
                    columns=0,
                    date_min="",
                    date_max="",
                    has_status_column=False,
                    has_label_column=False,
                    likely_asof_1457=False,
                    schema_note="could_not_read",
                )
            )
            continue
        date_col = None
        for candidate in ["date", "label_date", "trade_date"]:
            if candidate in df.columns:
                date_col = candidate
                break
        if date_col:
            s = pd.to_datetime(df[date_col], errors="coerce")
            date_min = str(s.min().date()) if s.notna().any() else ""
            date_max = str(s.max().date()) if s.notna().any() else ""
        else:
            date_min = date_max = ""
        lower_cols = {str(c).lower() for c in df.columns}
        likely_asof = any("1457" in c or "asof" in c for c in lower_cols)
        rows.append(
            FeatureCacheRow(
                name=path.name,
                path=str(path),
                size_bytes=_size(path),
                mtime=_mtime(path),
                rows=int(len(df)),
                columns=int(len(df.columns)),
                date_min=date_min,
                date_max=date_max,
                has_status_column="status" in lower_cols,
                has_label_column=bool({"label", "target", "y"} & lower_cols),
                likely_asof_1457=likely_asof,
                schema_note="asof_named" if likely_asof else "generic_gpu_probe_cache_probably_not_true_1457",
            )
        )
    return pd.DataFrame([asdict(r) for r in rows])


def _load_feature_catalog_map() -> dict[str, dict[str, Any]]:
    path = REPORT_DIR / "feature_catalog_20260507.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    columns = data.get("columns", []) if isinstance(data, dict) else []
    return {
        str(item.get("feature_name")): item
        for item in columns
        if isinstance(item, dict) and item.get("feature_name")
    }


def classify_bundle_feature(feature: str, meta: dict[str, Any] | None, selected_set: set[str]) -> tuple[str, str, str]:
    lower = feature.lower()
    parent = feature[: -len("_available")] if lower.endswith("_available") else ""
    if parent:
        if parent in selected_set:
            return "available_flag_with_parent", "P1", "Availability flag selected with parent; keep only if parent family parity is proven."
        return "orphan_available_flag", "P1", "Availability flag selected without parent feature; should be removed from champion candidates."

    rewrite_overrides = [
        "minute_",
        "tushare_last_30min_return",
        "tushare_first_15min_volume_ratio",
        "tushare_vwap_deviation",
        "tushare_close_vs_vwap",
        "tushare_high_time_pct",
        "tushare_limit_type",
        "tushare_limit_turnover",
        "tushare_float_relative_impact",
        "tushare_seal_ratio",
        "tushare_open_times",
        "tushare_first_time_minutes",
        "tushare_up_stat_days",
    ]
    if any(k in lower for k in rewrite_overrides):
        return "asof_rewrite_required", "P1", "Old catalog may say post-close, but this feature is a rewrite candidate under true 14:57 snapshot/limit-pool semantics."

    proxy_keywords = [
        "moneyflow",
        "mf_",
        "net_mf",
        "mf_strength",
        "lhb",
        "inst_",
        "hk_",
        "hsgt",
        "rzye",
        "rzmre",
        "rqye",
        "margin",
        "winner_rate",
        "cost_concentration",
        "cyq",
        "elg_buy",
        "lg_buy",
        "sm_sell",
    ]
    if any(k in lower for k in proxy_keywords):
        return "proxy_required", "P1", "Same-day source is delayed or different live semantics; requires delete-vs-T-1/proxy retrain."

    if meta:
        if meta.get("post_close_only") is True or meta.get("blocked_reason"):
            return "blocked", "P0", str(meta.get("blocked_reason") or "Catalog marks feature as post-close-only/blocked.")
        if meta.get("strict_1457_available") is True:
            return "strict_ok", "OK", "Catalog marks feature as strict 14:57 available."
        if meta.get("approximated_1457_available") is True:
            return "asof_rewrite_required", "P1", "Catalog marks old feature as close/full-day proxy; rebuild from true 14:57 snapshot."
        asof_rule = str(meta.get("asof_rule") or "").lower()
        if "t-1" in asof_rule or "lag" in asof_rule:
            return "proxy_required", "P1", "Catalog asof rule implies lagged/proxy treatment."

    rewrite_keywords = [
        "ret_",
        "volume",
        "amount",
        "turnover",
        "range",
        "close_position",
        "intraday",
        "minute",
        "vwap",
        "market_",
        "cs_",
        "limit_",
        "board",
        "emotion",
        "price",
        "ma",
        "rsi",
        "atr",
        "macd",
        "kdj",
    ]
    if any(k in lower for k in rewrite_keywords):
        return "asof_rewrite_required", "P1", "Likely engineerable but old bundle was not trained on audited true 14:57 schema."

    return "unknown", "P1", "Feature is not mapped to the current catalog; suspend from champion until mapped."


def build_bundle_feature_audit() -> tuple[pd.DataFrame, pd.DataFrame]:
    catalog = _load_feature_catalog_map()
    feature_rows: list[BundleFeatureRow] = []
    summary_rows: list[BundleSummaryRow] = []

    try:
        import torch
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

    for bundle_id, bundle_path in KNOWN_BUNDLES.items():
        if not bundle_path.exists():
            continue
        try:
            bundle = torch.load(str(bundle_path), map_location="cpu", weights_only=False)
        except Exception:
            continue
        selected = [str(x) for x in bundle.get("selected_feature_names", [])]
        selected_set = set(selected)
        model_name = str(bundle.get("model_name") or "")
        model_kind = str(bundle.get("model_kind") or "")
        calibration_used = str(bundle.get("calibration_used") or "")
        threshold = float(bundle.get("threshold") or 0.0)
        class_counts: dict[str, int] = {}

        for feature in selected:
            meta = catalog.get(feature)
            gate_class, severity, reason = classify_bundle_feature(feature, meta, selected_set)
            class_counts[gate_class] = class_counts.get(gate_class, 0) + 1
            feature_rows.append(
                BundleFeatureRow(
                    bundle_id=bundle_id,
                    bundle_path=str(bundle_path),
                    model_name=model_name,
                    model_kind=model_kind,
                    calibration_used=calibration_used,
                    threshold=threshold,
                    selected_count=len(selected),
                    feature=feature,
                    catalog_family=str((meta or {}).get("family") or ""),
                    baseline_family=str((meta or {}).get("baseline_family") or ""),
                    factor_id=str((meta or {}).get("factor_id") or ""),
                    catalog_asof_rule=str((meta or {}).get("asof_rule") or ""),
                    strict_1457_available=str((meta or {}).get("strict_1457_available") if meta else ""),
                    approximated_1457_available=str((meta or {}).get("approximated_1457_available") if meta else ""),
                    post_close_only=str((meta or {}).get("post_close_only") if meta else ""),
                    bundle_gate_class=gate_class,
                    gate_severity=severity,
                    reason=reason,
                )
            )

        blocked = class_counts.get("blocked", 0)
        proxy_required = class_counts.get("proxy_required", 0)
        rewrite = class_counts.get("asof_rewrite_required", 0)
        orphan_flags = class_counts.get("orphan_available_flag", 0)
        unknown = class_counts.get("unknown", 0)
        champion_eligible = blocked == 0 and proxy_required == 0 and rewrite == 0 and orphan_flags == 0 and unknown == 0
        if champion_eligible:
            role = "eligible_after_score_replay"
        elif bundle_id == "baseline_phasec":
            role = "legacy_score_only_baseline_rebuild_required"
        elif bundle_id == "baseline_s2":
            role = "rehabilitation_candidate_retrain_required"
        else:
            role = "research_freeze_candidate_rebuild_required"

        summary_rows.append(
            BundleSummaryRow(
                bundle_id=bundle_id,
                bundle_path=str(bundle_path),
                model_name=model_name,
                model_kind=model_kind,
                calibration_used=calibration_used,
                threshold=threshold,
                full_feature_count=len(bundle.get("feature_names", [])),
                selected_count=len(selected),
                strict_ok=class_counts.get("strict_ok", 0),
                asof_rewrite_required=rewrite,
                proxy_required=proxy_required,
                blocked=blocked,
                available_flag_with_parent=class_counts.get("available_flag_with_parent", 0),
                orphan_available_flag=orphan_flags,
                unknown=unknown,
                champion_eligible_now=champion_eligible,
                recommended_role=role,
            )
        )

    return pd.DataFrame([asdict(r) for r in feature_rows]), pd.DataFrame([asdict(r) for r in summary_rows])


def build_factor_family_summary(factors: pd.DataFrame) -> pd.DataFrame:
    rows: list[FactorFamilySummaryRow] = []
    if factors.empty:
        return pd.DataFrame()
    for family, group in factors.fillna({"family": ""}).groupby("family", dropna=False):
        counts = group["asof_class"].value_counts().to_dict()
        first_wave = int(group["first_wave_candidate"].sum()) if "first_wave_candidate" in group else 0
        if counts.get("C", 0):
            action = "exclude_or_rewrite_hard_c_first"
            blocker = "hard C exists"
        elif counts.get("A_pending_data", 0):
            action = "wait_1min_backfill_then_screen"
            blocker = "1min coverage"
        elif counts.get("A_rewrite_required", 0):
            action = "rewrite_to_true_1457_asof_then_screen"
            blocker = "asof rewrite/golden replay"
        elif counts.get("B", 0):
            action = "delete_vs_t1_or_proxy_pair"
            blocker = "proxy policy"
        elif counts.get("A", 0):
            action = "strict_clean_screen_candidate"
            blocker = ""
        else:
            action = "suspend_until_evidence"
            blocker = "insufficient evidence"
        rows.append(
            FactorFamilySummaryRow(
                family=str(family or "unassigned"),
                total=int(len(group)),
                a=int(counts.get("A", 0)),
                a_rewrite_required=int(counts.get("A_rewrite_required", 0)),
                a_pending_data=int(counts.get("A_pending_data", 0)),
                b=int(counts.get("B", 0)),
                c=int(counts.get("C", 0)),
                d=int(counts.get("D", 0)),
                first_wave_candidates=first_wave,
                recommended_action=action,
                blocker=blocker,
            )
        )
    return pd.DataFrame([asdict(r) for r in rows]).sort_values(
        ["first_wave_candidates", "a_pending_data", "a_rewrite_required", "a", "total"],
        ascending=[False, False, False, False, False],
    )


def build_s2_increment_audit(bundle_features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    diff_path = REPORT_DIR / "s2_phasec_feature_diff_20260511.json"
    if not diff_path.exists() or bundle_features.empty:
        return pd.DataFrame(), pd.DataFrame()
    with diff_path.open("r", encoding="utf-8") as f:
        diff = json.load(f)
    s2_only = set(map(str, diff.get("s2_selected_only", [])))
    phasec_only = set(map(str, diff.get("phasec_selected_only", [])))
    rows = bundle_features[
        ((bundle_features["bundle_id"] == "baseline_s2") & (bundle_features["feature"].isin(s2_only)))
        | ((bundle_features["bundle_id"] == "baseline_phasec") & (bundle_features["feature"].isin(phasec_only)))
    ].copy()
    summaries: list[S2IncrementSummaryRow] = []
    for scope, feats in [("s2_selected_only_vs_phasec", s2_only), ("phasec_selected_only_vs_s2", phasec_only)]:
        if not feats:
            summaries.append(
                S2IncrementSummaryRow(
                    scope=scope,
                    feature_count=0,
                    asof_rewrite_required=0,
                    proxy_required=0,
                    orphan_available_flag=0,
                    strict_ok=0,
                    unknown=0,
                    recommendation="empty_by_design",
                )
            )
            continue
        bundle_id = "baseline_s2" if scope.startswith("s2") else "baseline_phasec"
        part = bundle_features[
            (bundle_features["bundle_id"] == bundle_id) & (bundle_features["feature"].isin(feats))
        ]
        counts = part["bundle_gate_class"].value_counts().to_dict()
        if counts.get("proxy_required", 0) or counts.get("orphan_available_flag", 0) or counts.get("unknown", 0):
            recommendation = "split_rewrite_vs_proxy_then_full_rolling"
        else:
            recommendation = "asof_rewrite_family_candidate"
        summaries.append(
            S2IncrementSummaryRow(
                scope=scope,
                feature_count=int(len(part)),
                asof_rewrite_required=int(counts.get("asof_rewrite_required", 0)),
                proxy_required=int(counts.get("proxy_required", 0)),
                orphan_available_flag=int(counts.get("orphan_available_flag", 0)),
                strict_ok=int(counts.get("strict_ok", 0)),
                unknown=int(counts.get("unknown", 0)),
                recommendation=recommendation,
            )
        )
    return rows, pd.DataFrame([asdict(r) for r in summaries])


def _month_range(start: str, end: str) -> list[str]:
    if not start or not end:
        return []
    start_ts = pd.Timestamp(start + "-01")
    end_ts = pd.Timestamp(end + "-01")
    if end_ts < start_ts:
        return []
    return [str(x)[:7] for x in pd.period_range(start=start_ts, end=end_ts, freq="M")]


def _months_from_frame(path: Path) -> set[str]:
    df = None
    for cols in (["trade_time"], ["date"], ["trade_date"], ["end_date"], ["label_date"]):
        try:
            df = pd.read_parquet(path, columns=cols)
            break
        except Exception:
            continue
    if df is None:
        df = _safe_read_parquet(path)
    if df is None or df.empty:
        return set()
    dt = _datetime_series(df)
    if dt is None:
        for col in ["date", "trade_date", "label_date", "end_date"]:
            if col in df.columns:
                dt = pd.to_datetime(df[col], errors="coerce")
                break
    if dt is None:
        return set()
    valid = dt.dropna()
    if valid.empty:
        return set()
    return set(valid.dt.to_period("M").astype(str))


def build_source_temporal_summary(cache: pd.DataFrame) -> pd.DataFrame:
    rows: list[SourceTemporalSummaryRow] = []
    for _, cache_row in cache.iterrows():
        source = str(cache_row["source"])
        path = Path(str(cache_row["path"]))
        layout = str(cache_row["inferred_layout"])
        months: set[str] = set()
        sample_units = 0
        note = ""
        if not path.exists():
            note = "missing_path"
        elif layout == "per_date":
            files = sorted([p for p in path.glob("*.parquet") if p.is_file()])
            for f in files:
                d = _date_from_name(f)
                if d:
                    months.add(f"{d[:4]}-{d[4:6]}")
            sample_units = len(files)
            note = "filename_months_from_per_date_files"
        elif layout == "per_symbol" and source in {"stk_mins_1", "stk_mins_5", "raw_bars_daily", "cyq_perf", "pledge_stat_perstock"}:
            files = sorted([p for p in path.glob("*.parquet") if p.is_file()])
            sample = _sample_file_list(files, 24)
            for f in sample:
                months.update(_months_from_frame(f))
            sample_units = len(sample)
            note = "sampled_per_symbol_file_months"
        else:
            note = "not_temporally_sampled"

        first = min(months) if months else ""
        last = max(months) if months else ""
        expected = set(_month_range(first, last))
        missing = sorted(expected - months)
        rows.append(
            SourceTemporalSummaryRow(
                source=source,
                layout=layout,
                sample_units=sample_units,
                first_month=first,
                last_month=last,
                months_present=len(months),
                expected_months_between=len(expected),
                missing_months_count=len(missing),
                missing_months_sample="|".join(missing[:24]),
                has_2017_01="2017-01" in months,
                has_2026_04="2026-04" in months,
                note=note,
            )
        )
    return pd.DataFrame([asdict(r) for r in rows])


def _source_policy_for(source: str, file_count: int, status: str) -> tuple[str, str, str, str, str]:
    name = source.lower()
    if file_count == 0 or status in {"missing", "empty_or_not_backfilled"}:
        return (
            "D_pending_source",
            "Do not use in champion factors until backfilled or replaced.",
            "none",
            "missing source can create silent sparse/zero-fill artifacts",
            "non-empty cache plus source timing documentation",
        )
    if name == "stk_mins_1":
        klass = "A_pending_data" if file_count < 3000 else "A"
        return (
            klass,
            "Primary T-day 14:57 snapshot source for formal model.",
            "use bars <=14:57 only; never consume later 1min bars",
            "partial breadth blocks champion training",
            "broad SH/SZ coverage and sampled 14:57 bars across old/new listings",
        )
    if name == "stk_mins_5":
        return (
            "A_rewrite_required",
            "Use mature 5min history only with safe cutoff; combine with 1min for exact 14:57.",
            "last fully safe 5min bar is 14:55; never use 15:00 bar",
            "15:00 5min bar leaks 14:56-15:00",
            "feature builder proves cutoff and train/live parity",
        )
    if name == "raw_bars_daily":
        return (
            "A_history_Tminus1",
            "Use for historical lookback, T-1 finalized features and labels; not T-day live close.",
            "T-day full daily OHLCV forbidden for formal 14:57 features",
            "full-day T field would recreate the old close-proxy mistake",
            "T-day values are replaced by synthetic 14:57 snapshot in true-asof cache",
        )
    if name in {"daily_basic", "stk_factor_pro", "adj_factor"}:
        return (
            "B_Tminus1",
            "Use latest data available before 14:57, normally T-1.",
            "shift to T-1 unless vendor provides documented intraday asof timestamp",
            "same-day per-date fields are often settled after close",
            "per-column asof proof and lagged training/live equality",
        )
    if name == "share_float":
        return (
            "B_Tminus1",
            "Use as lagged float-share context or to normalize turnover/impact.",
            "latest known float share before 14:57; normally T-1 or announcement-asof",
            "backfilled share changes can leak corporate-action timing",
            "effective-date/asof audit and lagged train/live parity",
        )
    if name == "shibor":
        return (
            "B_Tminus1_macro",
            "Use as lagged macro/liquidity context only.",
            "T-1 or latest published timestamp before 14:57",
            "publication lag and calendar mismatch",
            "release timestamp proof and date-alignment audit",
        )
    if name == "stk_surv":
        return (
            "A_calendar_filter",
            "Use as listing/delisting survival filter, not as a raw alpha factor unless justified.",
            "status known by decision time; no future delist backfill in historical rows",
            "survivorship-bias leakage",
            "point-in-time listing status replay and ST/delist filter parity",
        )
    if name in {"moneyflow", "cyq_perf", "margin", "margin_detail"} or "moneyflow" in name or "cyq" in name:
        return (
            "B_Tminus1_or_proxy",
            "Use T-1 version or explicitly named live proxy family only.",
            "no same-name overwrite between delayed Tushare fields and live proxy fields",
            "proxy drift and delayed-source leakage",
            "delete-vs-T1/proxy paired ablation and drift report",
        )
    if name in {"limit_list_d", "stk_limit"} or "limit" in name:
        return (
            "A_rewrite_required",
            "Can be valuable only if reconstructed as limit-pool state visible by 14:57.",
            "historical full-day limit list must be truncated to events <=14:57",
            "full-day pool includes late limit events after decision time",
            "captured_at/first_time/open_times parity against live limit pool",
        )
    if "auction" in name:
        return (
            "A_preopen",
            "Can enter formal model if auction fields are known after 09:25 and stable by 14:57.",
            "auction snapshot only; no post-close auction-like aggregates",
            "vendor field may be revised or aggregated after close",
            "sample replay against live 09:25/14:57 capture",
        )
    if name in {"top_list", "top_inst", "block_trade"} or "lhb" in name or "block" in name:
        return (
            "B_delayed_event",
            "Research/T-1 event features only unless announcement timestamp proves pre-14:57 availability.",
            "asof announcement timestamp <=14:57, otherwise T-1",
            "after-close publication leakage",
            "event timestamp audit and delete-vs-T1 ablation",
        )
    if any(k in name for k in ["hsgt", "ggt", "hk_hold", "ccass", "north"]):
        return (
            "B_delayed_cross_market",
            "Use as lagged cross-market/holding context, not same-day live signal by default.",
            "T-1 or documented intraday timestamp only",
            "settlement/publication lag",
            "vendor timestamp proof and lagged parity check",
        )
    if any(k in name for k in ["forecast", "express", "holder", "pledge"]):
        return (
            "B_announcement_asof",
            "Use only records announced before the decision timestamp; otherwise T-1/history.",
            "announcement_time <= 14:57 with trading-day alignment",
            "future announcement leakage",
            "announcement timestamp audit and no backfilled future rows",
        )
    if name.startswith("ths") or name.startswith("index"):
        return (
            "B_or_A_rewrite_required",
            "Use T-1 official daily values, or rebuild live sector/index state from an intraday source.",
            "same-day full daily values forbidden unless intraday feed exists",
            "market/sector context drift between train and live",
            "source-specific asof proof plus cross-sectional replay",
        )
    if name == "suspend_d":
        return (
            "A_calendar_filter_pending_source",
            "Tradability filter if available before open; not a predictive factor until proven.",
            "trade calendar / suspend status known before decision time",
            "missing suspend data lets untradable symbols through",
            "non-empty source and Web/live filter replay",
        )
    return (
        "D_unclassified",
        "Do not use in champion route until owner and asof semantics are documented.",
        "none",
        "unknown timing semantics",
        "source owner, formula users, and train/live timing proof",
    )


def build_source_asof_policy(cache: pd.DataFrame) -> pd.DataFrame:
    rows: list[SourceAsofPolicyRow] = []
    for row in cache.to_dict(orient="records"):
        source = str(row.get("source", ""))
        file_count = int(row.get("file_count") or 0)
        status = str(row.get("completeness_status") or "")
        klass, formal_use, cutoff_rule, risk, proof = _source_policy_for(source, file_count, status)
        rows.append(
            SourceAsofPolicyRow(
                source=source,
                file_count=file_count,
                source_policy_class=klass,
                formal_1457_use=formal_use,
                cutoff_rule=cutoff_rule,
                risk=risk,
                required_proof=proof,
            )
        )
    return pd.DataFrame([asdict(r) for r in rows]).sort_values(["source_policy_class", "source"])


def build_bundle_family_gate(bundle_features: pd.DataFrame) -> pd.DataFrame:
    if bundle_features.empty:
        return pd.DataFrame()
    rows: list[BundleFamilyGateRow] = []
    data = bundle_features.copy()
    data["family"] = data["baseline_family"].fillna("").astype(str)
    data.loc[data["family"] == "", "family"] = data.loc[data["family"] == "", "catalog_family"].fillna("").astype(str)
    data.loc[data["family"] == "", "family"] = "unmapped"
    for (bundle_id, family), group in data.groupby(["bundle_id", "family"]):
        counts = group["bundle_gate_class"].value_counts().to_dict()
        proxy = int(counts.get("proxy_required", 0))
        rewrite = int(counts.get("asof_rewrite_required", 0))
        orphan = int(counts.get("orphan_available_flag", 0))
        unknown = int(counts.get("unknown", 0))
        if proxy:
            action = "delete_vs_t1_or_new_proxy_retrain"
        elif orphan:
            action = "remove_or_pair_available_flags"
        elif rewrite:
            action = "rewrite_family_to_true_1457_asof"
        elif unknown:
            action = "map_before_use"
        else:
            action = "strict_or_reference_ok"
        rows.append(
            BundleFamilyGateRow(
                bundle_id=str(bundle_id),
                family=str(family),
                selected_count=int(len(group)),
                asof_rewrite_required=rewrite,
                proxy_required=proxy,
                available_flag_with_parent=int(counts.get("available_flag_with_parent", 0)),
                orphan_available_flag=orphan,
                strict_ok=int(counts.get("strict_ok", 0)),
                unknown=unknown,
                recommended_action=action,
            )
        )
    return pd.DataFrame([asdict(r) for r in rows]).sort_values(
        ["bundle_id", "proxy_required", "orphan_available_flag", "asof_rewrite_required", "selected_count"],
        ascending=[True, False, False, False, False],
    )


def build_readiness_scorecard(
    cache: pd.DataFrame,
    minute_audit: pd.DataFrame,
    feature_cache_audit: pd.DataFrame,
    factors: pd.DataFrame,
    bundle_summary: pd.DataFrame,
    s2_increment_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[ReadinessScorecardRow] = []

    def add(gate: str, status: str, severity: str, evidence: str, fix: str, check: str) -> None:
        rows.append(ReadinessScorecardRow(gate, status, severity, evidence, fix, check))

    one_min = cache.loc[cache["source"] == "stk_mins_1"]
    one_count = int(one_min.iloc[0]["file_count"]) if not one_min.empty else 0
    one_markets = str(one_min.iloc[0]["market_counts"]) if not one_min.empty else ""
    add(
        "full_market_1min_breadth",
        "BLOCKED",
        "P0",
        f"stk_mins_1 root files={one_count}, markets={one_markets}",
        "finish full-market 1min backfill",
        ">=3000 symbol files with both SH/SZ and sampled monthly 14:57 coverage",
    )
    one_minute_detail = minute_audit.loc[minute_audit["source"] == "stk_mins_1"] if not minute_audit.empty else pd.DataFrame()
    has_1457 = int(one_minute_detail["has_1457"].sum()) if not one_minute_detail.empty else 0
    add(
        "historical_1457_timestamp",
        "PASS_SAMPLE",
        "P1",
        f"{has_1457}/{len(one_minute_detail)} sampled 1min symbols have 14:57 bars",
        "recheck after full backfill",
        "all sampled SH/SZ symbols across old/new listings contain expected 14:57 dates",
    )

    five = cache.loc[cache["source"] == "stk_mins_5"]
    five_count = int(five.iloc[0]["file_count"]) if not five.empty else 0
    add(
        "5min_breadth_and_cutoff",
        "PASS_WITH_LIMITATION",
        "P1",
        f"stk_mins_5 root files={five_count}; sample has 14:55 but no exact 14:57",
        "use 14:55-safe cutoff or combine with 1min 14:57 slice",
        "no training feature may consume the 15:00 5min bar for formal 14:57",
    )

    has_asof_cache = bool(not feature_cache_audit.empty and feature_cache_audit["likely_asof_1457"].any())
    add(
        "true_1457_asof_feature_cache",
        "PASS" if has_asof_cache else "BLOCKED",
        "P0",
        "latest feature caches include true-asof schema" if has_asof_cache else "latest feature caches are generic gpu_probe schemas",
        "build true_1457_asof cache with snapshot_time/cutoff_policy/source coverage",
        "schema/golden replay/train-live mapping all pass",
    )

    pending_1min = int((factors["asof_class"] == "A_pending_data").sum()) if not factors.empty else 0
    rewrite = int((factors["asof_class"] == "A_rewrite_required").sum()) if not factors.empty else 0
    add(
        "factor_registry_champion_eligibility",
        "BLOCKED",
        "P0/P1",
        f"A_pending_data={pending_1min}, A_rewrite_required={rewrite}",
        "complete data and rewrite/proxy catalog before champion training",
        "P0=0, P1=0 for selected feature set",
    )

    direct_eligible = bool(not bundle_summary.empty and bundle_summary["champion_eligible_now"].any())
    add(
        "known_bundles_direct_freeze",
        "PASS" if direct_eligible else "BLOCKED",
        "P1",
        "no known S2/PhaseC/pre_new_A bundle is direct champion-eligible now",
        "use bundles as references; retrain on true 14:57-asof cache",
        "bundle selected features show no rewrite/proxy/orphan issues and score-only replay passes",
    )

    s2_row = s2_increment_summary.loc[s2_increment_summary["scope"] == "s2_selected_only_vs_phasec"] if not s2_increment_summary.empty else pd.DataFrame()
    if not s2_row.empty:
        evidence = (
            f"S2-only selected={int(s2_row.iloc[0]['feature_count'])}, "
            f"rewrite={int(s2_row.iloc[0]['asof_rewrite_required'])}, "
            f"proxy={int(s2_row.iloc[0]['proxy_required'])}"
        )
    else:
        evidence = "missing S2 increment audit"
    add(
        "s2_increment_rehabilitation",
        "READY_AFTER_CACHE",
        "P1",
        evidence,
        "split S2-only rewrite vs proxy and rerun full 23-fold fixed_recent_36m",
        "S2 increments beat/hold stability versus PhaseC/pre_new_A baseline without P0/P1",
    )

    unclassified = cache.loc[cache["completeness_status"] == "unclassified_source"] if not cache.empty else pd.DataFrame()
    sample_sources = ",".join(unclassified["source"].astype(str).head(12).tolist()) if not unclassified.empty else ""
    add(
        "unclassified_cache_source_asof_rules",
        "NEEDS_CLASSIFICATION" if not unclassified.empty else "PASS",
        "P1" if not unclassified.empty else "OK",
        f"unclassified_sources={len(unclassified)} sample={sample_sources}",
        "assign each discovered source to A/B/C/D source timing and factor-family ownership",
        "no source used by champion factors remains unclassified",
    )

    return pd.DataFrame([asdict(r) for r in rows])


def build_next_task_queue(readiness: pd.DataFrame) -> pd.DataFrame:
    unclassified_evidence = "additional sources discovered after full cache scan"
    if not readiness.empty:
        row = readiness.loc[readiness["gate"] == "unclassified_cache_source_asof_rules"]
        if not row.empty:
            unclassified_evidence = str(row.iloc[0]["evidence"])
    tasks = [
        NextTaskRow(
            1,
            "Complete full-market stk_mins_1 backfill",
            False,
            "external data pull still running / incomplete",
            "stk_mins_1 root parquet set covering SH/SZ/BJ if used",
            "rerun full exploration audit and inspect minute symbol coverage",
            ">=3000 symbols, broad SH/SZ, sampled 14:57 dates pass",
        ),
        NextTaskRow(
            2,
            "Classify discovered unassigned cache sources",
            False,
            unclassified_evidence,
            "source timing/asof ownership table for adj_factor, auction, THS, index, margin, hsgt and related caches",
            "each source has A/B/C/D timing, owner factor families, and champion eligibility note",
            "no champion-used source remains unclassified_source",
        ),
        NextTaskRow(
            3,
            "Build true_1457_asof feature cache",
            False,
            "full-market 1min incomplete",
            "versioned feature cache with snapshot_time, cutoff_policy, source coverage",
            "schema parity, no 15:00 leak scan, golden replay",
            "P0=0 for cache, selected feature mapping reproducible",
        ),
        NextTaskRow(
            4,
            "Rehabilitate S2-only 60 selected features",
            False,
            "true_1457_asof cache missing",
            "S2-only rewrite/proxy manifest and family variants",
            "feature-level A/B/C/D gate and orphan flag check",
            "57 rewrite features and 2 proxy features split into proper variants",
        ),
        NextTaskRow(
            5,
            "Run first-wave minute families",
            False,
            "1min data incomplete",
            "C189-C193 and C244-C261/C273-C285 family screen results",
            "coverage, formula lock, no 15:00 leak, family screen only",
            "2-4 shortlisted families ready for full rolling",
        ),
        NextTaskRow(
            6,
            "Run full 23-fold fixed_recent_36m rolling",
            False,
            "shortlist and true-asof cache missing",
            "leaderboard, worst-window rows, P0/P1 audit",
            "same fold set, no Q1/April selection, stable-first metrics",
            "candidate beats stable baseline on mean/min/std Wilson and coverage",
        ),
        NextTaskRow(
            7,
            "Run non-factor matrices",
            False,
            "full rolling finalists missing",
            "window, candidate-pool, selection/budget, model-family matrices",
            "no single-window champion, same objective and fold boundaries",
            "top 2-4 finalists selected for HPO/calibration",
        ),
        NextTaskRow(
            8,
            "Freeze and Web/live gate",
            False,
            "finalists missing",
            "1-3 frozen bundles plus score-only Q1/April and live replay",
            "bundle hash/order/mapping/golden replay/runtime/ST filters",
            "Champion/Challenger/NO_FREEZE decision with P0=0/P1=0",
        ),
    ]
    return pd.DataFrame([asdict(t) for t in tasks])


def _load_factor_registry() -> list[dict[str, Any]]:
    path = REPORT_DIR / "factor_registry.json"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    found: list[dict[str, Any]] = []

    def walk(obj: Any, registry_path: str) -> None:
        if isinstance(obj, dict):
            factor_id = obj.get("factor_id")
            if isinstance(factor_id, str) and re.fullmatch(r"C\d{3}", factor_id):
                item = dict(obj)
                item["_registry_path"] = registry_path
                found.append(item)
                return
            for key, value in obj.items():
                walk(value, f"{registry_path}.{key}" if registry_path else str(key))
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                walk(value, f"{registry_path}[{idx}]")

    walk(data, "")

    # The registry keeps multiple historical candidate batches. Merge by id so the
    # latest encountered batch can update stale fields while preserving older notes.
    merged: dict[str, dict[str, Any]] = {}
    for item in found:
        factor_id = str(item["factor_id"])
        if factor_id in merged:
            combined = {**merged[factor_id], **item}
            combined["_registry_paths"] = (
                str(merged[factor_id].get("_registry_paths") or merged[factor_id].get("_registry_path") or "")
                + ";"
                + str(item.get("_registry_path") or "")
            ).strip(";")
            merged[factor_id] = combined
        else:
            item["_registry_paths"] = str(item.get("_registry_path") or "")
            merged[factor_id] = item

    return sorted(merged.values(), key=lambda x: _factor_number(x.get("factor_id")) or 10_000)


def _factor_number(factor_id: Any) -> int | None:
    m = re.search(r"(\d+)", str(factor_id))
    return int(m.group(1)) if m else None


def classify_factor(entry: dict[str, Any], one_min_ready: bool) -> tuple[str, str, str]:
    text = json.dumps(entry, ensure_ascii=False).lower()
    factor_num = _factor_number(
        entry.get("factor_id")
        or entry.get("id")
        or entry.get("code")
        or entry.get("factor")
        or entry.get("name")
    )

    if factor_num in ONE_MINUTE_FACTOR_IDS:
        if one_min_ready:
            return "A", "needs_full_rolling", "1min-derived and eligible after full 14:57-asof cache/golden replay."
        return "A_pending_data", "P0", "1min-derived but full-market 1min cache is incomplete; cannot enter champion training yet."

    tminus_or_proxy_keywords = [
        "moneyflow",
        "cyq",
        "筹码",
        "龙虎榜",
        "lhb",
        "holder",
        "pledge",
        "northbound",
        "hsgt",
        "block_trade",
        "forecast",
        "express",
        "financial",
        "float",
        "shareholder",
    ]
    if any(k in text for k in tminus_or_proxy_keywords):
        return "B", "needs_delete_vs_proxy", "Likely available only with T-1/asof lag or proxy; needs explicit delete-vs-proxy comparison."

    intraday_keywords = [
        "intraday",
        "minute",
        "min",
        "5min",
        "1min",
        "limit",
        "auction",
        "volume",
        "turnover",
        "range",
        "price",
        "technical",
        "alpha",
        "formula",
        "sector",
        "theme",
        "board",
    ]
    has_intraday_route = any(k in text for k in intraday_keywords)

    hard_forbidden_keywords = [
        "postclose only",
        "after close only",
        "future return",
        "future_data",
        "tomorrow",
        "next day return",
        "label leakage",
        "level-2",
        "order book",
        "not engineerable",
        "cannot be engineered",
        "无法工程化",
        "盘后不可",
        "未来收益",
    ]
    if any(k in text for k in hard_forbidden_keywords):
        return "C", "P0", "Hard forbidden or unavailable at 14:57 unless a new live-safe source is proven."

    rewrite_keywords = [
        "15:00",
        "full day",
        "full-day",
        "t-day close",
        "收盘",
        "盘后",
        "eod",
        "close",
    ]
    if has_intraday_route and any(k in text for k in rewrite_keywords):
        return "A_rewrite_required", "needs_asof_rewrite", "Potentially useful but must be rebuilt from the shared 14:57 snapshot; old 15:00 semantics cannot enter champion."

    unknown_keywords = ["social", "nlp", "news", "sentiment", "unknown", "manual", "research_candidate"]
    if any(k in text for k in unknown_keywords):
        return "D", "P1", "Evidence insufficient or external pipeline not proven live-safe."

    if any(k in text for k in intraday_keywords):
        return "A", "needs_full_rolling", "Appears 14:57-engineerable if built from the shared asof snapshot and source coverage passes."

    return "D", "P1", "No decisive source/asof evidence in registry; keep out of champion until mapped."


def build_factor_audit(cache_audit: pd.DataFrame) -> pd.DataFrame:
    one_min_row = cache_audit.loc[cache_audit["source"] == "stk_mins_1"]
    one_min_ready = bool(
        not one_min_row.empty
        and one_min_row.iloc[0]["gate_severity"] == "OK"
        and int(one_min_row.iloc[0]["file_count"]) >= 3000
    )
    rows: list[dict[str, Any]] = []
    for entry in _load_factor_registry():
        factor_id = (
            entry.get("factor_id")
            or entry.get("id")
            or entry.get("code")
            or entry.get("factor")
            or entry.get("name")
        )
        factor_num = _factor_number(factor_id)
        cls, gate, reason = classify_factor(entry, one_min_ready)
        rows.append(
            {
                "factor_id": factor_id,
                "factor_num": factor_num,
                "name": entry.get("name") or entry.get("name_cn") or entry.get("desc") or "",
                "family": entry.get("family") or entry.get("factor_family") or entry.get("group") or "",
                "priority": entry.get("priority") or "",
                "training_status": entry.get("training_status") or "",
                "lockbox_role": entry.get("lockbox_role") or "",
                "data_source": entry.get("data_source") or entry.get("source") or entry.get("raw_source") or "",
                "asof_class": cls,
                "gate_status": gate,
                "first_wave_candidate": bool(factor_num in FIRST_WAVE_FACTOR_IDS),
                "reason": reason,
                "raw": json.dumps(entry, ensure_ascii=False, sort_keys=True),
            }
        )
    return pd.DataFrame(rows).sort_values(["factor_num", "factor_id"], na_position="last")


def build_factor_action_queue(
    factors: pd.DataFrame,
    bundle_family_gate: pd.DataFrame,
    s2_increment_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[FactorActionRow] = []

    def add(
        priority: int,
        factor_scope: str,
        mask: pd.Series | None,
        asof_class: str,
        action: str,
        blocker: str,
        experiment_role: str,
        acceptance_check: str,
        explicit_count: int | None = None,
    ) -> None:
        count = int(explicit_count if explicit_count is not None else (mask.sum() if mask is not None else 0))
        rows.append(
            FactorActionRow(
                priority=priority,
                factor_scope=factor_scope,
                factor_count=count,
                asof_class=asof_class,
                action=action,
                blocker=blocker,
                experiment_role=experiment_role,
                acceptance_check=acceptance_check,
            )
        )

    if factors.empty:
        return pd.DataFrame([asdict(r) for r in rows])

    add(
        1,
        "C189-C193/C244-C261/C273-C285 minute first-wave",
        factors["factor_num"].isin(sorted(FIRST_WAVE_FACTOR_IDS)),
        "A_pending_data / mixed",
        "wait for full-market stk_mins_1, then formula-lock and golden replay",
        "full-market 1min cache incomplete",
        "first-wave family screen only, then full 23-fold if shortlisted",
        "coverage >= broad SH/SZ target, no 15:00 leak, train/live feature parity",
    )
    add(
        2,
        "S2 selected-only increment over PhaseC",
        None,
        "A_rewrite_required + B proxy",
        "rehabilitate, not discard; split rewrite vs T-1/proxy variants",
        "true_1457_asof cache missing",
        "strong challenger route after asof rebuild",
        "each variant beats or preserves pre_new_A stability baseline on full 23-fold",
        explicit_count=int(s2_increment_summary.iloc[0]["feature_count"]) if not s2_increment_summary.empty else 0,
    )
    add(
        3,
        "All A_rewrite_required factors",
        factors["asof_class"] == "A_rewrite_required",
        "A_rewrite_required",
        "implement/rebuild from shared 14:57 snapshot; no old close-schema reuse",
        "needs asof builder and per-family parity tests",
        "main clean-factor expansion pool",
        "golden replay, source coverage, fold-level P0/P1=0 before champion candidate",
    )
    add(
        4,
        "Current strict A factors",
        factors["asof_class"] == "A",
        "A",
        "keep as baseline clean pool; still rerun on true_1457_asof cache",
        "current cache is generic gpu_probe, not certified asof",
        "PhaseC/S2/pre_new_A reference rebuild component",
        "same feature values in train cache and Web/live replay for sample dates",
    )
    add(
        5,
        "B proxy/T-1 candidates",
        factors["asof_class"] == "B",
        "B",
        "create delete-vs-T1/proxy pairs with explicit new names",
        "same-name overwrite and proxy drift risk",
        "secondary ablation only, never silent inclusion",
        "proxy drift report and paired ablation; no proxy can mask as original T-day field",
    )
    add(
        6,
        "D unknown evidence factors",
        factors["asof_class"] == "D",
        "D",
        "suspend from champion route until source/asof evidence is added",
        "insufficient source or live-safe proof",
        "research backlog",
        "registry row has source, formula, asof rule, implementation path and coverage proof",
    )
    add(
        7,
        "Hard C forbidden factors",
        factors["asof_class"] == "C",
        "C",
        "reject from strict champion unless redefined into a new live-safe factor",
        "post-close/future/unavailable semantics",
        "reject list / rewrite backlog",
        "selected features contain zero C-class columns",
    )

    if not bundle_family_gate.empty:
        blocked_families = bundle_family_gate.loc[
            bundle_family_gate["recommended_action"].isin(
                [
                    "rewrite_family_to_true_1457_asof",
                    "delete_vs_t1_or_new_proxy_retrain",
                    "remove_or_pair_available_flags",
                ]
            )
        ]
        add(
            8,
            "Known bundle selected family gates",
            None,
            "bundle-selected mixed",
            "resolve family gates before using any known bundle as more than reference",
            "selected features still need rewrite/proxy/orphan cleanup",
            "bundle rebuild prerequisite",
            "bundle summary shows blocked=0, proxy decision documented, orphan flags removed",
            explicit_count=int(blocked_families["selected_count"].sum()),
        )

    return pd.DataFrame([asdict(r) for r in rows]).sort_values(["priority", "factor_scope"])


def build_experiment_protocol(gate: dict[str, Any]) -> pd.DataFrame:
    champion_ready = bool(gate.get("allow_champion_training"))

    def row(
        stage_order: int,
        dimension: str,
        variants: str,
        objective: str,
        allowed_now: bool,
        dependency: str,
        primary_metrics: str,
        hard_no: str,
        promotion_rule: str,
    ) -> ExperimentProtocolRow:
        return ExperimentProtocolRow(
            stage_order=stage_order,
            dimension=dimension,
            variants=variants,
            objective=objective,
            allowed_now=allowed_now,
            dependency=dependency,
            primary_metrics=primary_metrics,
            hard_no=hard_no,
            promotion_rule=promotion_rule,
        )

    rows = [
        row(
            1,
            "data_and_asof_gate",
            "1min/5min/daily/per-date sources; schema drift; 14:57 timestamp",
            "prove true 14:57 training is possible before any champion run",
            True,
            "none",
            "coverage, missing months, sampled 14:57 bars, P0/P1",
            "starting champion training while 1min or true-asof cache is incomplete",
            "P0=0/P1=0, then build cache",
        ),
        row(
            2,
            "true_1457_asof_cache",
            "synthetic T-day 14:57 OHLCV + T-1/asof delayed fields",
            "replace 15:00 close-proxy training with strict historical live semantics",
            champion_ready,
            "full-market 1min breadth and source coverage",
            "schema parity, golden replay, no leak scan, mapping hash",
            "using 15:00 same-day fields in formal model",
            "cache is versioned and replay-equivalent to Web/live feature builder",
        ),
        row(
            3,
            "factor_family_screen",
            "PhaseC_asof, S2_rehab, A, A_rewrite, 5min, 1min, proxy pairs",
            "identify promising families without overfitting to one window",
            champion_ready,
            "true_asof cache",
            "4-fold screen mean/min Wilson, candidate count, P0/P1",
            "promoting a 4-fold screen winner directly to champion",
            "2-4 families enter full 23-fold fixed_recent_36m",
        ),
        row(
            4,
            "full_fixed_recent_36m",
            "23 folds, 3m outer, inner_valid, label_date embargo",
            "main champion comparison with stability-first evidence",
            champion_ready,
            "shortlisted families",
            "mean_wilson_95, min_wilson_95, std_wilson_95, accuracy, coverage",
            "using Q1/April for selection or selecting by mean alone",
            "candidate beats pre_new_A stable baseline without weakening tail risk",
        ),
        row(
            5,
            "candidate_pool",
            "turnover/amount/range/active anomaly/main-board filters",
            "find tradable candidate universe and avoid fragile no-candidate days",
            champion_ready,
            "full rolling candidate model",
            "daily candidate count, coverage, topK hit, sector concentration",
            "allowing ST/suspend/delisting/unbuyable limit-up through",
            "stable coverage with P0 filters all clean",
        ),
        row(
            6,
            "selection_and_budget",
            "stable_tail/abs_corr/fold-stability; budgets 120-480",
            "avoid arbitrary feature budget and unstable selected columns",
            champion_ready,
            "family candidates",
            "Wilson stability, feature overlap, drift prune, orphan flag check",
            "keeping orphan _available flags without parent family",
            "selected set stable across folds and no P0/P1 selected",
        ),
        row(
            7,
            "model_family_hpo",
            "Torch, LightGBM, XGBoost, CatBoost, compact/wide/deep",
            "compare model capacity after feature/data gates are clean",
            champion_ready,
            "top 2-4 full-rolling candidates",
            "stability-first Optuna objective, Brier, tie penalty",
            "HPO against Q1/April or a single tail month",
            "multi-fold HPO improves stability without candidate collapse",
        ),
        row(
            8,
            "calibration_selector",
            "raw/Platt/isotonic; p bands; top3/5/6/10; agreement/regime selector",
            "turn probabilities into live candidate decisions without overcompression",
            champion_ready,
            "trained finalists",
            "bucket monotonicity, Brier, candidate count, daily topK",
            "choosing isotonic solely by Brier when it kills candidates",
            "selector improves stable high-confidence hit rate with adequate coverage",
        ),
        row(
            9,
            "seed_ensemble_strategy_regime",
            "seeds 42/7/2026/43/44; rank/avg ensemble; strategy/regime drilldown",
            "separate robust signal from lucky seed/window",
            champion_ready,
            "finalist configs",
            "mean/min/std across seeds, worst windows, drawdown, regime buckets",
            "using strategy PnL alone as champion criterion",
            "Champion/Challenger ranking remains consistent under seeds and regimes",
        ),
        row(
            10,
            "freeze_web_live_gate",
            "bundle hash/order/mapping/replay/runtime; Q1/April score-only; future forward",
            "turn research result into deployable 14:57 model",
            champion_ready,
            "final P0/P1-clean candidate",
            "score-only replay, live parity, runtime, missing feature count",
            "retraining or recalibrating during frozen validation",
            "freeze 1-3 bundles or output NO_FREEZE",
        ),
    ]
    return pd.DataFrame([asdict(r) for r in rows])


def build_execution_gate(
    evidence: pd.DataFrame,
    cache: pd.DataFrame,
    factors: pd.DataFrame,
    minute_audit: pd.DataFrame,
    feature_cache_audit: pd.DataFrame,
    bundle_summary: pd.DataFrame,
) -> dict[str, Any]:
    p0: list[str] = []
    p1: list[str] = []

    one_min = cache.loc[cache["source"] == "stk_mins_1"]
    if one_min.empty or str(one_min.iloc[0]["gate_severity"]) == "P0":
        p0.append("Full-market stk_mins_1 cache is incomplete; true 14:57-asof champion training is blocked.")
    elif not minute_audit.empty:
        one_min_detail = minute_audit.loc[minute_audit["source"] == "stk_mins_1"]
        if not one_min_detail.empty and int(one_min_detail["date_count_1457"].min()) == 0:
            p0.append("stk_mins_1 exists but sampled symbols do not all contain 14:57 bars.")

    feature_cache_hits = evidence[
        evidence["path"].str.contains("feature_cache", case=False, na=False)
        | evidence["name"].str.contains("feature", case=False, na=False)
    ]
    asof_feature_hits = feature_cache_hits[
        feature_cache_hits["name"].str.contains("asof|1457", case=False, na=False)
    ]
    if asof_feature_hits.empty:
        p0.append("No audited true 14:57-asof feature cache/golden replay artifact was found in the evidence index.")
    if not feature_cache_audit.empty and not bool(feature_cache_audit["likely_asof_1457"].any()):
        p0.append("Latest feature caches look like generic gpu_probe caches; no true 14:57-asof schema was found.")
    if not bundle_summary.empty and not bool(bundle_summary["champion_eligible_now"].any()):
        p1.append("Known S2/PhaseC/pre_new_A bundles all require asof rebuild/proxy cleanup; keep them as references, not direct champions.")

    unclassified = cache.loc[cache["completeness_status"] == "unclassified_source"] if not cache.empty else pd.DataFrame()
    if not unclassified.empty:
        sample = ",".join(unclassified["source"].astype(str).head(8).tolist())
        p1.append(f"{len(unclassified)} discovered cache sources are unclassified ({sample}); assign asof/source gates before using related factors.")

    for source in ["stk_holdertrade", "suspend_d", "ggt_top10", "index_weight", "ths_member"]:
        row = cache.loc[cache["source"] == source]
        if not row.empty and str(row.iloc[0]["gate_severity"]) == "P1":
            p1.append(f"{source} is {row.iloc[0]['completeness_status']}; related factors must stay pending/proxy-only.")

    if not factors.empty:
        a_pending = int((factors["asof_class"] == "A_pending_data").sum())
        a_rewrite = int((factors["asof_class"] == "A_rewrite_required").sum())
        d_count = int((factors["asof_class"] == "D").sum())
        c_count = int((factors["asof_class"] == "C").sum())
        if a_pending:
            p0.append(f"{a_pending} registry factors are 1min-derived A_pending_data and cannot enter champion training yet.")
        if a_rewrite:
            p1.append(f"{a_rewrite} factors look engineerable but require explicit 14:57-asof rewrite/golden replay before champion use.")
        if c_count:
            p0.append(f"{c_count} factors are currently C/forbidden until rewritten or removed.")
        if d_count:
            p1.append(f"{d_count} factors have insufficient evidence and are suspended from champion candidates.")

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "allow_phase0_to_phase2_audit": True,
        "allow_true_1457_cache_build": len(p0) == 0,
        "allow_champion_training": len(p0) == 0,
        "allow_family_screen_research_only": True,
        "p0": p0,
        "p1": p1,
        "required_next_actions": [
            "Complete full-market stk_mins_1 backfill and rerun this audit.",
            "Build strict true 14:57-asof feature cache from minute cutoff; do not train champion on 15:00 full-day proxies.",
            "Run S2-only rehabilitation with asof rewritten columns, not old hard-delete assumptions.",
            "After P0/P1 clear, run family screens, then full 23-fold fixed_recent_36m for shortlisted families.",
        ],
    }


def build_training_matrix(gate: dict[str, Any], factors: pd.DataFrame) -> pd.DataFrame:
    one_min_blocked = not gate["allow_champion_training"]

    def row(
        phase: str,
        experiment_group: str,
        variants: str,
        purpose: str,
        dependency: str,
        status: str,
        champion_eligible: bool,
        next_action: str,
        audit_requirement: str,
    ) -> dict[str, Any]:
        return {
            "phase": phase,
            "experiment_group": experiment_group,
            "variants": variants,
            "purpose": purpose,
            "dependency": dependency,
            "status": status,
            "champion_eligible_now": champion_eligible,
            "next_action": next_action,
            "audit_requirement": audit_requirement,
        }

    rows: list[dict[str, Any]] = []
    rows.append(
        row(
            "Phase 3",
            "true_1457_asof_cache",
            "daily + 5min + 1min cutoff snapshot",
            "Build the only feature cache allowed for champion training.",
            "Full-market stk_mins_1 + 5min + daily/asof sources.",
            "blocked_by_p0" if one_min_blocked else "ready_to_build",
            False if one_min_blocked else True,
            "Finish stk_mins_1 backfill, then build schema/parity/golden replay.",
            "No 15:00 same-day fields; feature schema and train/live mapping must match.",
        )
    )
    rows.append(
        row(
            "Phase 4",
            "PhaseC_asof_baseline",
            "old strict PhaseC selected features rebuilt on asof cache",
            "Legacy strict baseline/risk reference only.",
            "True 14:57-asof cache and old bundle feature mapping.",
            "blocked_until_asof_cache",
            False,
            "Rebuild as score-only baseline after cache exists; do not promote as champion route.",
            "P0 selected=0; Q1/April score-only consistency only.",
        )
    )
    rows.append(
        row(
            "Phase 4",
            "S2_rehabilitation",
            "S2_best9_asof_rewrite; S2-only clean groups; delete-vs-rewrite",
            "Recover S2-only factors that were misjudged as unavailable.",
            "A_rewrite_required columns plus 1min pending factors where applicable.",
            "partially_blocked_by_rewrite_and_1min",
            False,
            "Map every S2-only factor to A/B/C/D; rewrite A factors on asof snapshot.",
            "No silent zero fill; train/live semantic parity required before screen.",
        )
    )
    rows.append(
        row(
            "Phase 4",
            "5min_intraday_family",
            "C174-C188 and older 5min groups",
            "Test mature 5min intraday structure factors.",
            "stk_mins_5 complete; strict 14:57 cutoff still needs asof builder.",
            "research_ready_not_champion",
            False,
            "Build cutoff version excluding post-14:57 bars; run family screen after parity.",
            "Worst-window rows and P0/P1 audit; family screen cannot select champion.",
        )
    )
    rows.append(
        row(
            "Phase 4",
            "1min_microstructure_family",
            "C189-C193, C244-C261, C273-C285, selected formulaic alpha",
            "Use true minute-level 14:57 market microstructure.",
            "Full-market stk_mins_1.",
            "blocked_by_p0",
            False,
            "Wait for 1min backfill; audit 14:57 bar coverage month-by-month.",
            "Coverage must be broad by date and symbol; no champion if partial.",
        )
    )
    rows.append(
        row(
            "Phase 4",
            "all_A_engineerable",
            "A + A_rewrite_required after rewrite, excluding A_pending_data until ready",
            "Broad clean factor search without proxy ambiguity.",
            "True asof cache and factor mapping.",
            "blocked_until_rewrite",
            False,
            "After cache, run 4-fold family screen, then 23-fold full rolling for finalists.",
            "Compare against pre_new_A stable baseline; do not pick by mean alone.",
        )
    )
    rows.append(
        row(
            "Phase 4",
            "A_plus_B_proxy",
            "A clean + B T-1/proxy variants",
            "Measure whether lagged/proxy fields add stable signal.",
            "Explicit T-1/proxy naming and delete-vs-proxy pairs.",
            "pending_proxy_design",
            False,
            "Create separate feature names for proxy families and run paired ablations.",
            "Proxy drift report; no same-name Tushare/EastMoney overwrite.",
        )
    )
    rows.append(
        row(
            "Phase 5",
            "full_fixed_recent_36m_rolling",
            "23 folds, 3m outer, fold-inner valid, label_date embargo",
            "Main champion validation protocol.",
            "Shortlisted families from Phase 4 and true asof cache.",
            "blocked_until_shortlist_and_cache",
            False,
            "Run every shortlisted family through full 23-fold fixed_recent_36m.",
            "Leaderboard, stable candidate, worst-window rows, P0/P1 audit.",
        )
    )
    rows.append(
        row(
            "Phase 6",
            "time_window_matrix",
            "24/30/36/48/60/72m; fixed-start 2017-2023; expanding",
            "Confirm 36m choice and diagnose data horizon sensitivity.",
            "At least one stable clean candidate from Phase 5.",
            "pending_after_main_protocol",
            False,
            "Use same factor/model config; compare stability, not Q1/April.",
            "No Q1/April in selection; annual windows only diagnostics.",
        )
    )
    rows.append(
        row(
            "Phase 6",
            "candidate_pool_matrix",
            "turnover/amount/range/active anomaly/main-board-only filters",
            "Find stable, tradable daily candidate universe.",
            "True asof features and ST/suspend/limit filters.",
            "pending_after_cache",
            False,
            "Run filter matrix and track no-candidate days and sector concentration.",
            "ST/suspend/delisting/unbuyable limit-up exclusion is P0.",
        )
    )
    rows.append(
        row(
            "Phase 6",
            "selection_budget_matrix",
            "stable_tail/abs_corr/fold-stability; budgets 120-480",
            "Avoid arbitrary budget and unstable feature picks.",
            "Full rolling candidate families.",
            "pending_after_family_shortlist",
            False,
            "Compare mean/min/std Wilson and feature overlap across folds.",
            "Orphan _available flags cannot survive without parent family.",
        )
    )
    rows.append(
        row(
            "Phase 7",
            "model_hpo_calibration_selector",
            "Torch/LightGBM/XGBoost/CatBoost; Optuna; Platt/isotonic; topK/threshold",
            "Improve finalists without overfitting.",
            "Top 2-4 strict-clean candidates from full rolling.",
            "pending_after_full_rolling",
            False,
            "Optimize stability-first objective; never use Q1/April.",
            "Tie penalty, Brier, candidate count, calibration monotonicity required.",
        )
    )
    rows.append(
        row(
            "Phase 8",
            "seed_ensemble_strategy_regime",
            "seeds 42/7/2026/43/44; average/rank ensemble; strategy/regime drilldown",
            "Separate robust signal from lucky seed/window.",
            "Finalists after HPO/calibration.",
            "pending_after_hpo",
            False,
            "Run multi-seed, ensemble, strategy consistency and weak-window analysis.",
            "Strategy is auxiliary; Wilson/stability remains primary.",
        )
    )
    rows.append(
        row(
            "Phase 9-10",
            "freeze_and_web_live_gate",
            "1-3 bundles; score-only Q1/April; future final_forward; Web/live replay",
            "Decide Champion/Challenger/Research-only/Reject.",
            "Stable finalist bundle and clean engineering audit.",
            "pending_after_no_p0_p1",
            False,
            "Freeze only if P0/P1=0 and future final_forward can be monitored.",
            "Bundle hash, feature order, mapping, golden replay, runtime and filters pass.",
        )
    )

    matrix = pd.DataFrame(rows)
    if not factors.empty:
        factor_summary = factors["asof_class"].value_counts().to_dict()
        matrix["factor_class_snapshot"] = json.dumps(factor_summary, ensure_ascii=False, sort_keys=True)
    return matrix


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def write_outputs(
    evidence: pd.DataFrame,
    cache: pd.DataFrame,
    factors: pd.DataFrame,
    gate: dict[str, Any],
    matrix: pd.DataFrame,
    minute_audit: pd.DataFrame,
    feature_cache_audit: pd.DataFrame,
    bundle_features: pd.DataFrame,
    bundle_summary: pd.DataFrame,
    family_summary: pd.DataFrame,
    s2_increment_features: pd.DataFrame,
    s2_increment_summary: pd.DataFrame,
    source_temporal: pd.DataFrame,
    source_asof_policy: pd.DataFrame,
    bundle_family_gate: pd.DataFrame,
    readiness: pd.DataFrame,
    task_queue: pd.DataFrame,
    factor_action_queue: pd.DataFrame,
    experiment_protocol: pd.DataFrame,
) -> dict[str, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "evidence_csv": REPORT_DIR / f"full_exploration_evidence_index_{OUT_STEM}.csv",
        "evidence_json": REPORT_DIR / f"full_exploration_evidence_index_{OUT_STEM}.json",
        "cache_csv": REPORT_DIR / f"full_exploration_cache_audit_{OUT_STEM}.csv",
        "cache_json": REPORT_DIR / f"full_exploration_cache_audit_{OUT_STEM}.json",
        "factor_csv": REPORT_DIR / f"full_exploration_factor_audit_{OUT_STEM}.csv",
        "factor_json": REPORT_DIR / f"full_exploration_factor_audit_{OUT_STEM}.json",
        "matrix_csv": REPORT_DIR / f"full_exploration_training_matrix_{OUT_STEM}.csv",
        "matrix_json": REPORT_DIR / f"full_exploration_training_matrix_{OUT_STEM}.json",
        "minute_csv": REPORT_DIR / f"full_exploration_minute_symbol_audit_{OUT_STEM}.csv",
        "minute_json": REPORT_DIR / f"full_exploration_minute_symbol_audit_{OUT_STEM}.json",
        "feature_cache_csv": REPORT_DIR / f"full_exploration_feature_cache_audit_{OUT_STEM}.csv",
        "feature_cache_json": REPORT_DIR / f"full_exploration_feature_cache_audit_{OUT_STEM}.json",
        "bundle_feature_csv": REPORT_DIR / f"full_exploration_bundle_feature_audit_{OUT_STEM}.csv",
        "bundle_feature_json": REPORT_DIR / f"full_exploration_bundle_feature_audit_{OUT_STEM}.json",
        "bundle_summary_csv": REPORT_DIR / f"full_exploration_bundle_summary_{OUT_STEM}.csv",
        "bundle_summary_json": REPORT_DIR / f"full_exploration_bundle_summary_{OUT_STEM}.json",
        "family_summary_csv": REPORT_DIR / f"full_exploration_factor_family_summary_{OUT_STEM}.csv",
        "family_summary_json": REPORT_DIR / f"full_exploration_factor_family_summary_{OUT_STEM}.json",
        "s2_increment_csv": REPORT_DIR / f"full_exploration_s2_increment_audit_{OUT_STEM}.csv",
        "s2_increment_json": REPORT_DIR / f"full_exploration_s2_increment_audit_{OUT_STEM}.json",
        "s2_increment_summary_csv": REPORT_DIR / f"full_exploration_s2_increment_summary_{OUT_STEM}.csv",
        "s2_increment_summary_json": REPORT_DIR / f"full_exploration_s2_increment_summary_{OUT_STEM}.json",
        "source_temporal_csv": REPORT_DIR / f"full_exploration_source_temporal_summary_{OUT_STEM}.csv",
        "source_temporal_json": REPORT_DIR / f"full_exploration_source_temporal_summary_{OUT_STEM}.json",
        "source_asof_policy_csv": REPORT_DIR / f"full_exploration_source_asof_policy_{OUT_STEM}.csv",
        "source_asof_policy_json": REPORT_DIR / f"full_exploration_source_asof_policy_{OUT_STEM}.json",
        "bundle_family_csv": REPORT_DIR / f"full_exploration_bundle_family_gate_{OUT_STEM}.csv",
        "bundle_family_json": REPORT_DIR / f"full_exploration_bundle_family_gate_{OUT_STEM}.json",
        "readiness_csv": REPORT_DIR / f"full_exploration_readiness_scorecard_{OUT_STEM}.csv",
        "readiness_json": REPORT_DIR / f"full_exploration_readiness_scorecard_{OUT_STEM}.json",
        "task_queue_csv": REPORT_DIR / f"full_exploration_next_task_queue_{OUT_STEM}.csv",
        "task_queue_json": REPORT_DIR / f"full_exploration_next_task_queue_{OUT_STEM}.json",
        "factor_action_csv": REPORT_DIR / f"full_exploration_factor_action_queue_{OUT_STEM}.csv",
        "factor_action_json": REPORT_DIR / f"full_exploration_factor_action_queue_{OUT_STEM}.json",
        "experiment_protocol_csv": REPORT_DIR / f"full_exploration_experiment_protocol_{OUT_STEM}.csv",
        "experiment_protocol_json": REPORT_DIR / f"full_exploration_experiment_protocol_{OUT_STEM}.json",
        "gate_json": REPORT_DIR / f"full_exploration_execution_gate_{OUT_STEM}.json",
        "doc": DOCS_DIR / f"1457_full_exploration_audit_{OUT_STEM}.md",
    }

    evidence.to_csv(outputs["evidence_csv"], index=False, encoding="utf-8-sig")
    cache.to_csv(outputs["cache_csv"], index=False, encoding="utf-8-sig")
    factors.to_csv(outputs["factor_csv"], index=False, encoding="utf-8-sig")
    matrix.to_csv(outputs["matrix_csv"], index=False, encoding="utf-8-sig")
    minute_audit.to_csv(outputs["minute_csv"], index=False, encoding="utf-8-sig")
    feature_cache_audit.to_csv(outputs["feature_cache_csv"], index=False, encoding="utf-8-sig")
    bundle_features.to_csv(outputs["bundle_feature_csv"], index=False, encoding="utf-8-sig")
    bundle_summary.to_csv(outputs["bundle_summary_csv"], index=False, encoding="utf-8-sig")
    family_summary.to_csv(outputs["family_summary_csv"], index=False, encoding="utf-8-sig")
    s2_increment_features.to_csv(outputs["s2_increment_csv"], index=False, encoding="utf-8-sig")
    s2_increment_summary.to_csv(outputs["s2_increment_summary_csv"], index=False, encoding="utf-8-sig")
    source_temporal.to_csv(outputs["source_temporal_csv"], index=False, encoding="utf-8-sig")
    source_asof_policy.to_csv(outputs["source_asof_policy_csv"], index=False, encoding="utf-8-sig")
    bundle_family_gate.to_csv(outputs["bundle_family_csv"], index=False, encoding="utf-8-sig")
    readiness.to_csv(outputs["readiness_csv"], index=False, encoding="utf-8-sig")
    task_queue.to_csv(outputs["task_queue_csv"], index=False, encoding="utf-8-sig")
    factor_action_queue.to_csv(outputs["factor_action_csv"], index=False, encoding="utf-8-sig")
    experiment_protocol.to_csv(outputs["experiment_protocol_csv"], index=False, encoding="utf-8-sig")

    write_json(outputs["evidence_json"], evidence.to_dict(orient="records"))
    write_json(outputs["cache_json"], cache.to_dict(orient="records"))
    write_json(outputs["factor_json"], factors.to_dict(orient="records"))
    write_json(outputs["matrix_json"], matrix.to_dict(orient="records"))
    write_json(outputs["minute_json"], minute_audit.to_dict(orient="records"))
    write_json(outputs["feature_cache_json"], feature_cache_audit.to_dict(orient="records"))
    write_json(outputs["bundle_feature_json"], bundle_features.to_dict(orient="records"))
    write_json(outputs["bundle_summary_json"], bundle_summary.to_dict(orient="records"))
    write_json(outputs["family_summary_json"], family_summary.to_dict(orient="records"))
    write_json(outputs["s2_increment_json"], s2_increment_features.to_dict(orient="records"))
    write_json(outputs["s2_increment_summary_json"], s2_increment_summary.to_dict(orient="records"))
    write_json(outputs["source_temporal_json"], source_temporal.to_dict(orient="records"))
    write_json(outputs["source_asof_policy_json"], source_asof_policy.to_dict(orient="records"))
    write_json(outputs["bundle_family_json"], bundle_family_gate.to_dict(orient="records"))
    write_json(outputs["readiness_json"], readiness.to_dict(orient="records"))
    write_json(outputs["task_queue_json"], task_queue.to_dict(orient="records"))
    write_json(outputs["factor_action_json"], factor_action_queue.to_dict(orient="records"))
    write_json(outputs["experiment_protocol_json"], experiment_protocol.to_dict(orient="records"))
    write_json(outputs["gate_json"], gate)

    class_counts = factors["asof_class"].value_counts(dropna=False).to_dict() if not factors.empty else {}
    cache_summary = cache.loc[
        cache["source"].isin(["stk_mins_1", "stk_mins_5", "raw_bars_daily", "daily_basic", "stk_factor_pro", "moneyflow", "cyq_perf"]),
        ["source", "file_count", "nested_parquet_count", "market_counts", "completeness_status", "gate_severity", "sampled_has_1457", "note"],
    ]
    minute_summary = pd.DataFrame()
    if not minute_audit.empty:
        minute_summary = (
            minute_audit.groupby("source")
            .agg(
                sampled_symbols=("symbol", "count"),
                markets=("market", lambda x: ",".join(sorted(set(map(str, x))))),
                min_unique_dates=("unique_dates", "min"),
                max_unique_dates=("unique_dates", "max"),
                symbols_with_1457=("has_1457", "sum"),
                min_1457_dates=("date_count_1457", "min"),
                max_1457_dates=("date_count_1457", "max"),
                symbols_with_1455=("has_1455", "sum"),
                min_1455_dates=("date_count_1455", "min"),
                max_1455_dates=("date_count_1455", "max"),
            )
            .reset_index()
        )
    feature_cache_summary = feature_cache_audit[
        ["name", "rows", "columns", "date_min", "date_max", "likely_asof_1457", "schema_note"]
    ].head(10) if not feature_cache_audit.empty else pd.DataFrame()
    bundle_summary_view = bundle_summary[
        [
            "bundle_id",
            "selected_count",
            "asof_rewrite_required",
            "proxy_required",
            "blocked",
            "orphan_available_flag",
            "unknown",
            "champion_eligible_now",
            "recommended_role",
        ]
    ] if not bundle_summary.empty else pd.DataFrame()
    family_summary_view = family_summary[
        [
            "family",
            "total",
            "a",
            "a_rewrite_required",
            "a_pending_data",
            "b",
            "c",
            "d",
            "first_wave_candidates",
            "recommended_action",
        ]
    ].head(25) if not family_summary.empty else pd.DataFrame()
    s2_increment_view = s2_increment_summary if not s2_increment_summary.empty else pd.DataFrame()
    temporal_view = source_temporal[
        [
            "source",
            "layout",
            "sample_units",
            "first_month",
            "last_month",
            "months_present",
            "missing_months_count",
            "has_2017_01",
            "has_2026_04",
            "note",
        ]
    ].head(30) if not source_temporal.empty else pd.DataFrame()
    source_policy_view = source_asof_policy[
        [
            "source",
            "file_count",
            "source_policy_class",
            "formal_1457_use",
            "cutoff_rule",
            "risk",
        ]
    ].head(42) if not source_asof_policy.empty else pd.DataFrame()
    bundle_family_view = bundle_family_gate[
        [
            "bundle_id",
            "family",
            "selected_count",
            "asof_rewrite_required",
            "proxy_required",
            "orphan_available_flag",
            "recommended_action",
        ]
    ].head(35) if not bundle_family_gate.empty else pd.DataFrame()
    readiness_view = readiness if not readiness.empty else pd.DataFrame()
    task_queue_view = task_queue[
        ["priority", "task", "can_run_now", "blocked_by", "deliverable", "exit_criteria"]
    ] if not task_queue.empty else pd.DataFrame()
    factor_action_view = factor_action_queue[
        ["priority", "factor_scope", "factor_count", "asof_class", "action", "experiment_role"]
    ] if not factor_action_queue.empty else pd.DataFrame()
    experiment_protocol_view = experiment_protocol[
        [
            "stage_order",
            "dimension",
            "allowed_now",
            "dependency",
            "primary_metrics",
            "promotion_rule",
        ]
    ] if not experiment_protocol.empty else pd.DataFrame()
    p0_lines = "\n".join(f"- {x}" for x in gate["p0"]) or "- none"
    p1_lines = "\n".join(f"- {x}" for x in gate["p1"]) or "- none"
    one_min_row = cache.loc[cache["source"] == "stk_mins_1"]
    one_min_count = int(one_min_row.iloc[0]["file_count"]) if not one_min_row.empty else 0
    one_min_markets = str(one_min_row.iloc[0]["market_counts"]) if not one_min_row.empty else ""
    one_min_progress = min(100.0, one_min_count / 3000 * 100) if one_min_count else 0.0
    factor_nums = sorted(
        int(x)
        for x in factors["factor_num"].dropna().tolist()
        if pd.notna(x)
    ) if not factors.empty and "factor_num" in factors else []
    factor_scope = (
        f"C001-C{max(factor_nums):03d} ({len(factor_nums)} registry factors)"
        if factor_nums
        else "current factor registry"
    )

    doc = f"""# 14:57 Full Exploration Audit {OUT_STEM}

## Scope

This is the executable Phase 0-2 gate for the next all-round search:

- evidence freeze across docs, scripts, reports, feature caches, bundles and recent runs;
- raw cache/source coverage audit, especially `stk_mins_1` and `stk_mins_5`;
- {factor_scope} factor asof reclassification for strict 14:57 champion eligibility;
- execution gate before true 14:57-asof cache/training.

## Current Gate

- `allow_true_1457_cache_build`: `{gate["allow_true_1457_cache_build"]}`
- `allow_champion_training`: `{gate["allow_champion_training"]}`
- `allow_family_screen_research_only`: `{gate["allow_family_screen_research_only"]}`

### P0

{p0_lines}

### P1

{p1_lines}

## Key Cache Summary

{cache_summary.to_markdown(index=False)}

## Minute Coverage Sample

{minute_summary.to_markdown(index=False) if not minute_summary.empty else "No minute symbol audit rows."}

## Latest Feature Cache Schema Sample

{feature_cache_summary.to_markdown(index=False) if not feature_cache_summary.empty else "No feature cache audit rows."}

## Source Temporal Summary

{temporal_view.to_markdown(index=False) if not temporal_view.empty else "No source temporal summary rows."}

## Source Asof Policy

{source_policy_view.to_markdown(index=False) if not source_policy_view.empty else "No source asof policy rows."}

## Factor Asof Class Counts

{json.dumps(class_counts, ensure_ascii=False, indent=2)}

## Known Bundle Selected Feature Gate

{bundle_summary_view.to_markdown(index=False) if not bundle_summary_view.empty else "No known bundle audit rows."}

## S2 Increment vs PhaseC

{s2_increment_view.to_markdown(index=False) if not s2_increment_view.empty else "No S2 increment audit rows."}

## Bundle Family Gate

{bundle_family_view.to_markdown(index=False) if not bundle_family_view.empty else "No bundle family gate rows."}

## Factor Family Priority Summary

{family_summary_view.to_markdown(index=False) if not family_summary_view.empty else "No factor family summary rows."}

## Deep Interpretation

- `stk_mins_1` is conceptually usable for true 14:57 training: every sampled 1min symbol has 14:57 bars.
  The blocker is breadth, not timestamp availability. Current root coverage is `{one_min_count}` files
  ({one_min_progress:.1f}% of the broad 3000-file minimum gate), markets=`{one_min_markets}`.
- `stk_mins_5` is broad at root level, but 5min bars do not contain an exact 14:57 close. The last fully
  safe 5min bar is 14:55; using the 15:00 bar would leak 14:56-15:00 information into a 14:57 model.
- Existing latest feature caches are generic `gpu_probe_features_*` schemas and are not named or audited
  as true 14:57-asof caches. They cannot be used to certify a champion route.
- Daily OHLCV is not missing: it is present under raw bars, outside the tushare cache directory.
- The factor classification is intentionally conservative in two directions:
  hard C is kept tiny to avoid wasting engineerable factors, while `A_rewrite_required` is kept out of
  champion training until its 14:57 rewrite and golden replay are proven.
- S2, PhaseC, and pre_new_A bundles all remain useful references, but their selected features are not
  currently champion-eligible as-is because they rely on old close/proxy schemas and/or delayed-source
  families. Their value is in the feature ideas and baselines, not direct freeze.
- S2's incremental value over PhaseC is not invalidated: the S2-only selected set should be split into
  rewrite candidates versus proxy/orphan cleanup, then rerun as proper 14:57-asof families.

## Optimized Execution Order

1. Finish `stk_mins_1` backfill to broad SH/SZ coverage, then rerun this audit.
2. Build a strict `true_1457_asof` feature cache with explicit `snapshot_time`, `cutoff_policy`,
   source coverage, and train/live feature mapping.
3. Rebuild S2 best-9 and S2-only 60 columns under asof semantics; compare delete vs rewrite vs T-1 proxy.
4. Rebuild C174-C188 5min factors using safe cutoff semantics. If exact 14:57 is required, combine
   5min history with the 1min 14:56/14:57 slice rather than using the 15:00 bar.
5. After 1min is complete, add C189-C193 and C244-C261/C273-C285 as first-wave minute families.
6. Run family screens only as triage, then promote shortlisted families to full 23-fold
   `fixed_recent_36m` rolling. Do not select champion from screen results.
7. Only after full rolling: run window sensitivity, candidate-pool matrix, feature-selection/budget,
   model-family, HPO, calibration, seed, ensemble, strategy and Web/live gates.

## Readiness Scorecard

{readiness_view.to_markdown(index=False) if not readiness_view.empty else "No readiness scorecard rows."}

## Next Task Queue

{task_queue_view.to_markdown(index=False) if not task_queue_view.empty else "No task queue rows."}

## Factor Action Queue

{factor_action_view.to_markdown(index=False) if not factor_action_view.empty else "No factor action queue rows."}

## Experiment Decision Protocol

{experiment_protocol_view.to_markdown(index=False) if not experiment_protocol_view.empty else "No experiment protocol rows."}

## Required Next Actions

{chr(10).join(f"- {x}" for x in gate["required_next_actions"])}

## Training Matrix Gate

{matrix[["phase", "experiment_group", "status", "champion_eligible_now", "next_action"]].to_markdown(index=False)}

## Output Files

- `{outputs["evidence_csv"]}`
- `{outputs["cache_csv"]}`
- `{outputs["factor_csv"]}`
- `{outputs["matrix_csv"]}`
- `{outputs["minute_csv"]}`
- `{outputs["feature_cache_csv"]}`
- `{outputs["bundle_summary_csv"]}`
- `{outputs["bundle_feature_csv"]}`
- `{outputs["family_summary_csv"]}`
- `{outputs["s2_increment_summary_csv"]}`
- `{outputs["s2_increment_csv"]}`
- `{outputs["source_temporal_csv"]}`
- `{outputs["source_asof_policy_csv"]}`
- `{outputs["bundle_family_csv"]}`
- `{outputs["readiness_csv"]}`
- `{outputs["task_queue_csv"]}`
- `{outputs["factor_action_csv"]}`
- `{outputs["experiment_protocol_csv"]}`
- `{outputs["gate_json"]}`

## Decision

No champion training should start from this audit state. The project can continue evidence/factor
work and research-only screens, but final strict 14:57 training requires a complete 1min cache and
a verified true 14:57-asof feature cache first.
"""
    outputs["doc"].write_text(doc, encoding="utf-8")
    return outputs


def self_audit(
    outputs: dict[str, Path],
    evidence: pd.DataFrame,
    cache: pd.DataFrame,
    factors: pd.DataFrame,
    matrix: pd.DataFrame,
    minute_audit: pd.DataFrame,
    feature_cache_audit: pd.DataFrame,
    bundle_features: pd.DataFrame,
    bundle_summary: pd.DataFrame,
    family_summary: pd.DataFrame,
    s2_increment_features: pd.DataFrame,
    s2_increment_summary: pd.DataFrame,
    source_temporal: pd.DataFrame,
    source_asof_policy: pd.DataFrame,
    bundle_family_gate: pd.DataFrame,
    readiness: pd.DataFrame,
    task_queue: pd.DataFrame,
    factor_action_queue: pd.DataFrame,
    experiment_protocol: pd.DataFrame,
) -> list[str]:
    problems: list[str] = []
    for key, path in outputs.items():
        if not path.exists() or path.stat().st_size == 0:
            problems.append(f"Output missing or empty: {key} -> {path}")
    if evidence.empty:
        problems.append("Evidence index is empty.")
    for source in ["stk_mins_1", "stk_mins_5"]:
        if source not in set(cache["source"]):
            problems.append(f"Cache audit missing {source}.")
    if factors.empty:
        problems.append("Factor registry audit is empty.")
    elif "factor_num" not in factors:
        problems.append("Factor registry audit missing factor_num.")
    else:
        factor_nums = sorted(int(x) for x in factors["factor_num"].dropna().tolist() if pd.notna(x))
        if factor_nums:
            expected = set(range(1, max(factor_nums) + 1))
            actual = set(factor_nums)
            missing = sorted(expected - actual)
            if missing:
                problems.append(
                    "Factor registry IDs are not contiguous: missing "
                    + ", ".join(f"C{x:03d}" for x in missing[:20])
                    + ("..." if len(missing) > 20 else "")
                )
            if len(factor_nums) != len(actual):
                problems.append("Factor registry audit contains duplicate factor_num values.")
    if "A_pending_data" not in set(factors["asof_class"]):
        problems.append("Expected at least one A_pending_data factor while 1min is incomplete.")
    if matrix.empty:
        problems.append("Training matrix is empty.")
    if "full_fixed_recent_36m_rolling" not in set(matrix["experiment_group"]):
        problems.append("Training matrix missing full_fixed_recent_36m_rolling.")
    if minute_audit.empty:
        problems.append("Minute symbol audit is empty.")
    if feature_cache_audit.empty:
        problems.append("Feature cache audit is empty.")
    if bundle_summary.empty or bundle_features.empty:
        problems.append("Known bundle feature audit is empty.")
    if family_summary.empty:
        problems.append("Factor family summary is empty.")
    if s2_increment_summary.empty:
        problems.append("S2 increment summary is empty.")
    if source_temporal.empty:
        problems.append("Source temporal summary is empty.")
    if source_asof_policy.empty:
        problems.append("Source asof policy is empty.")
    if bundle_family_gate.empty:
        problems.append("Bundle family gate is empty.")
    if readiness.empty:
        problems.append("Readiness scorecard is empty.")
    if task_queue.empty:
        problems.append("Next task queue is empty.")
    if factor_action_queue.empty:
        problems.append("Factor action queue is empty.")
    if experiment_protocol.empty:
        problems.append("Experiment protocol is empty.")
    if not experiment_protocol.empty and "full_fixed_recent_36m" not in set(experiment_protocol["dimension"]):
        problems.append("Experiment protocol missing full_fixed_recent_36m dimension.")
    return problems


def main() -> None:
    evidence = build_evidence_index()
    cache = build_cache_audit()
    minute_audit = build_minute_symbol_audit()
    feature_cache_audit = build_feature_cache_audit()
    bundle_features, bundle_summary = build_bundle_feature_audit()
    s2_increment_features, s2_increment_summary = build_s2_increment_audit(bundle_features)
    factors = build_factor_audit(cache)
    family_summary = build_factor_family_summary(factors)
    source_temporal = build_source_temporal_summary(cache)
    source_asof_policy = build_source_asof_policy(cache)
    bundle_family_gate = build_bundle_family_gate(bundle_features)
    readiness = build_readiness_scorecard(
        cache,
        minute_audit,
        feature_cache_audit,
        factors,
        bundle_summary,
        s2_increment_summary,
    )
    task_queue = build_next_task_queue(readiness)
    gate = build_execution_gate(evidence, cache, factors, minute_audit, feature_cache_audit, bundle_summary)
    matrix = build_training_matrix(gate, factors)
    factor_action_queue = build_factor_action_queue(factors, bundle_family_gate, s2_increment_summary)
    experiment_protocol = build_experiment_protocol(gate)
    outputs = write_outputs(
        evidence,
        cache,
        factors,
        gate,
        matrix,
        minute_audit,
        feature_cache_audit,
        bundle_features,
        bundle_summary,
        family_summary,
        s2_increment_features,
        s2_increment_summary,
        source_temporal,
        source_asof_policy,
        bundle_family_gate,
        readiness,
        task_queue,
        factor_action_queue,
        experiment_protocol,
    )
    problems = self_audit(
        outputs,
        evidence,
        cache,
        factors,
        matrix,
        minute_audit,
        feature_cache_audit,
        bundle_features,
        bundle_summary,
        family_summary,
        s2_increment_features,
        s2_increment_summary,
        source_temporal,
        source_asof_policy,
        bundle_family_gate,
        readiness,
        task_queue,
        factor_action_queue,
        experiment_protocol,
    )

    print("full exploration audit complete")
    print(f"evidence_rows={len(evidence)}")
    print(f"cache_rows={len(cache)}")
    print(f"minute_rows={len(minute_audit)}")
    print(f"feature_cache_rows={len(feature_cache_audit)}")
    print(f"bundle_feature_rows={len(bundle_features)}")
    print(f"bundle_summary_rows={len(bundle_summary)}")
    print(f"family_summary_rows={len(family_summary)}")
    print(f"s2_increment_rows={len(s2_increment_features)}")
    print(f"s2_increment_summary_rows={len(s2_increment_summary)}")
    print(f"source_temporal_rows={len(source_temporal)}")
    print(f"source_asof_policy_rows={len(source_asof_policy)}")
    print(f"bundle_family_rows={len(bundle_family_gate)}")
    print(f"readiness_rows={len(readiness)}")
    print(f"task_queue_rows={len(task_queue)}")
    print(f"factor_action_rows={len(factor_action_queue)}")
    print(f"experiment_protocol_rows={len(experiment_protocol)}")
    print(f"factor_rows={len(factors)}")
    print(f"matrix_rows={len(matrix)}")
    print(f"p0={len(gate['p0'])} p1={len(gate['p1'])}")
    print(f"allow_champion_training={gate['allow_champion_training']}")
    for key, path in outputs.items():
        print(f"{key}: {path}")
    if problems:
        print("SELF_AUDIT_FAIL")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(2)
    print("SELF_AUDIT_PASS")


if __name__ == "__main__":
    main()
