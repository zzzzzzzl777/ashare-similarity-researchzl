from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from ashare_similarity.prediction.factor_cache_manager import FactorFrame


LIMIT_POOL_SOURCES: dict[str, str] = {
    "zt_pool": "stock_zt_pool_em",
    "zt_pool_previous": "stock_zt_pool_previous_em",
    "zbgc_pool": "stock_zt_pool_zbgc_em",
    "dtgc_pool": "stock_zt_pool_dtgc_em",
    "strong_pool": "stock_zt_pool_strong_em",
}

NORMALIZED_COLUMNS: tuple[str, ...] = (
    "kind",
    "trade_date",
    "captured_at",
    "source_function",
    "source_hash",
    "symbol",
    "name",
    "close",
    "pct_change",
    "amount",
    "turnover",
    "float_market_cap",
    "total_market_cap",
    "seal_amount",
    "first_seal_time",
    "last_seal_time",
    "first_seal_minutes",
    "last_seal_minutes",
    "open_board_count",
    "board_count",
    "board_type",
    "industry",
    "reason",
)

LIMIT_POOL_SYMBOL_FACTOR_COLUMNS: tuple[str, ...] = (
    "real_in_zt_pool",
    "real_in_prev_zt_pool",
    "real_in_zbgc_pool",
    "real_in_dtgc_pool",
    "real_in_strong_pool",
    "real_seal_time_minutes",
    "seal_time_score",
    "real_seal_time_rank",
    "real_first_seal_rank_pct",
    "real_last_seal_delay_minutes",
    "last_seal_delay",
    "real_open_board_count",
    "board_height_real",
    "real_board_count",
    "seal_money_to_float_mv",
    "real_seal_amount_to_float_mv",
    "seal_money_to_amount",
    "real_seal_amount_to_amount",
    "real_one_word_board",
    "real_early_seal",
    "seal_before_1030",
    "real_turnover_board",
    "real_failed_board",
    "real_limit_down_pressure",
    "real_seal_stability_score",
    "seal_strength",
    "real_reseal_strength",
    "real_board_volume_acceptance",
    "real_prev_zt_pct_change",
    "real_prev_zt_red",
)

LIMIT_POOL_MARKET_FACTOR_COLUMNS: tuple[str, ...] = (
    "market_real_zt_count",
    "real_limit_up_count",
    "market_real_zbgc_count",
    "market_real_dtgc_count",
    "market_real_strong_count",
    "market_real_attempt_count",
    "market_true_limit_ratio",
    "market_real_broken_board_rate",
    "market_real_limit_down_pressure",
    "market_real_one_word_count",
    "market_real_early_seal_count",
    "market_real_avg_open_board_count",
    "market_real_mean_seal_time_minutes",
    "market_prev_zt_count",
    "market_prev_zt_red_rate",
    "prev_limit_pool_red_rate",
    "market_prev_zt_mean_pct_change",
    "yesterday_zt_premium",
)

_KIND_SYMBOL_FLAG_COLUMNS: dict[str, str] = {
    "zt_pool": "real_in_zt_pool",
    "zt_pool_previous": "real_in_prev_zt_pool",
    "zbgc_pool": "real_in_zbgc_pool",
    "dtgc_pool": "real_in_dtgc_pool",
    "strong_pool": "real_in_strong_pool",
}

_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "symbol": ("代码", "股票代码", "证券代码", "symbol"),
    "name": ("名称", "股票简称", "证券简称", "name"),
    "close": ("最新价", "收盘价", "价格", "close"),
    "pct_change": ("涨跌幅", "涨幅", "今日涨跌幅", "pct_change"),
    "amount": ("成交额", "成交金额", "amount"),
    "turnover": ("换手率", "turnover"),
    "float_market_cap": ("流通市值", "流通股本", "float_market_cap"),
    "total_market_cap": ("总市值", "total_market_cap"),
    "seal_amount": ("封板资金", "封单资金", "封单额", "seal_amount"),
    "first_seal_time": ("首次封板时间", "首次涨停时间", "first_seal_time"),
    "last_seal_time": ("最后封板时间", "最终封板时间", "last_seal_time"),
    "open_board_count": ("炸板次数", "开板次数", "open_board_count"),
    "board_count": ("连板数", "连续涨停", "涨停统计", "board_count"),
    "board_type": ("板型", "涨停类型", "涨停统计", "board_type"),
    "industry": ("所属行业", "行业", "板块", "industry"),
    "reason": ("涨停原因", "入选理由", "原因", "reason"),
}


def fetch_limit_pool_snapshots(
    trade_date: str | date,
    *,
    kinds: Iterable[str] | None = None,
    ak_module: Any | None = None,
) -> dict[str, pd.DataFrame]:
    if ak_module is None:
        import akshare as ak_module

    date_text = _compact_trade_date(trade_date)
    selected = tuple(kinds or LIMIT_POOL_SOURCES.keys())
    frames: dict[str, pd.DataFrame] = {}
    for kind in selected:
        function_name = LIMIT_POOL_SOURCES[kind]
        loader = getattr(ak_module, function_name)
        raw = loader(date=date_text)
        frames[kind] = normalize_limit_pool_snapshot(
            raw,
            kind=kind,
            trade_date=date_text,
            source_function=function_name,
        )
    return frames


def normalize_limit_pool_snapshot(
    raw: pd.DataFrame,
    *,
    kind: str,
    trade_date: str | date,
    source_function: str,
    captured_at: datetime | None = None,
) -> pd.DataFrame:
    captured_at = captured_at or datetime.now(timezone.utc)
    date_text = _compact_trade_date(trade_date)
    source_hash = _frame_hash(raw)
    frame = pd.DataFrame(index=raw.index.copy())
    for target, aliases in _COLUMN_ALIASES.items():
        source = _first_present(raw, aliases)
        frame[target] = raw[source] if source is not None else np.nan
    frame["symbol"] = frame["symbol"].astype(str).str.extract(r"(\d{6})", expand=False).fillna("").str.zfill(6)
    frame["kind"] = kind
    frame["trade_date"] = pd.to_datetime(date_text, format="%Y%m%d", errors="coerce")
    frame["captured_at"] = pd.Timestamp(captured_at)
    frame["source_function"] = source_function
    frame["source_hash"] = source_hash
    for column in (
        "close",
        "pct_change",
        "amount",
        "turnover",
        "float_market_cap",
        "total_market_cap",
        "seal_amount",
        "open_board_count",
        "board_count",
    ):
        frame[column] = frame[column].map(_parse_numeric)
    frame["first_seal_time"] = frame["first_seal_time"].map(_clean_time_text)
    frame["last_seal_time"] = frame["last_seal_time"].map(_clean_time_text)
    frame["first_seal_minutes"] = frame["first_seal_time"].map(_minutes_from_open)
    frame["last_seal_minutes"] = frame["last_seal_time"].map(_minutes_from_open)
    frame["board_count"] = frame["board_count"].fillna(_board_count_from_stat(frame["board_type"]))
    frame["name"] = frame["name"].astype(str).replace({"nan": ""})
    frame["industry"] = frame["industry"].astype(str).replace({"nan": ""})
    frame["reason"] = frame["reason"].astype(str).replace({"nan": ""})
    out = frame.loc[frame["symbol"].str.fullmatch(r"\d{6}").fillna(False), list(NORMALIZED_COLUMNS)].copy()
    return out.reset_index(drop=True)


def write_snapshot_bundle(
    frames: Mapping[str, pd.DataFrame],
    *,
    output_dir: str | Path,
    trade_date: str | date,
) -> dict[str, Any]:
    root = Path(output_dir)
    date_text = _compact_trade_date(trade_date)
    bundle_dir = root / f"trade_date={date_text}"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trade_date": date_text,
        "kinds": {},
    }
    for kind, frame in frames.items():
        path = bundle_dir / f"{kind}.parquet"
        _atomic_write_parquet(path, frame)
        manifest["kinds"][kind] = {
            "path": str(path),
            "relative_path": path.name,
            "rows": int(len(frame)),
            "source_function": LIMIT_POOL_SOURCES.get(kind),
            "columns": list(frame.columns),
        }
    manifest_path = bundle_dir / "manifest.json"
    _atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2, default=str))
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def load_snapshot_bundles(root: str | Path) -> dict[str, pd.DataFrame]:
    root_path = Path(root)
    frames: dict[str, list[pd.DataFrame]] = {kind: [] for kind in LIMIT_POOL_SOURCES}
    if not root_path.exists():
        return {}
    for manifest_path in root_path.glob("trade_date=*/manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for kind, payload in (manifest.get("kinds") or {}).items():
            path = _manifest_payload_path(manifest_path, payload)
            if not path.exists():
                continue
            try:
                frames.setdefault(kind, []).append(pd.read_parquet(path))
            except Exception:
                continue
    return {kind: pd.concat(parts, ignore_index=True) for kind, parts in frames.items() if parts}


def build_limit_pool_snapshot_factors(frames: Mapping[str, pd.DataFrame]) -> list[FactorFrame]:
    normalized = {kind: _coerce_snapshot_frame(frame, kind=kind) for kind, frame in frames.items() if frame is not None and not frame.empty}
    if not normalized:
        return []
    symbol_factor = _build_limit_pool_symbol_factor(normalized)
    market_factor = _build_limit_pool_market_factor(normalized)
    return [factor for factor in (symbol_factor, market_factor) if factor is not None]


def _build_limit_pool_symbol_factor(frames: Mapping[str, pd.DataFrame]) -> FactorFrame | None:
    pieces = []
    for kind, frame in frames.items():
        if frame.empty or "symbol" not in frame.columns or "trade_date" not in frame.columns:
            continue
        piece = pd.DataFrame(
            {
                "symbol": frame["symbol"].astype(str).str.zfill(6),
                "date": pd.to_datetime(frame["trade_date"], errors="coerce"),
                _KIND_SYMBOL_FLAG_COLUMNS.get(kind, f"real_in_{kind}"): 1.0,
            }
        )
        if kind == "zt_pool":
            first = pd.to_numeric(frame.get("first_seal_minutes"), errors="coerce")
            last = pd.to_numeric(frame.get("last_seal_minutes"), errors="coerce")
            amount = pd.to_numeric(frame.get("amount"), errors="coerce")
            float_mv = pd.to_numeric(frame.get("float_market_cap"), errors="coerce")
            seal_amount = pd.to_numeric(frame.get("seal_amount"), errors="coerce")
            open_board_count = pd.to_numeric(frame.get("open_board_count"), errors="coerce").fillna(0.0)
            board_count = pd.to_numeric(frame.get("board_count"), errors="coerce").fillna(0.0)
            turnover = pd.to_numeric(frame.get("turnover"), errors="coerce").fillna(0.0)
            seal_to_float = (seal_amount / float_mv.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan)
            seal_to_amount = (seal_amount / amount.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan)
            one_word = ((first <= -4.0) & (open_board_count <= 0.0)).astype(float)
            early_seal = (first <= 30.0).astype(float)
            first_rank = (-first).groupby(piece["date"], sort=False).rank(pct=True).fillna(0.0)
            reseal_strength = ((1.0 - ((last - first).clip(lower=0.0) / 240.0)).clip(lower=0.0, upper=1.0) / (1.0 + open_board_count)).fillna(0.0)
            stability = (
                (1.0 / (1.0 + open_board_count))
                * (1.0 + one_word)
                * (1.0 + seal_to_amount.clip(lower=0.0, upper=1.0).fillna(0.0))
            )
            piece["real_seal_time_minutes"] = first
            piece["seal_time_score"] = (1.0 - (first.clip(lower=0.0, upper=240.0) / 240.0)).fillna(0.0)
            piece["real_seal_time_rank"] = first_rank
            piece["real_first_seal_rank_pct"] = first_rank
            piece["real_last_seal_delay_minutes"] = (last - first).clip(lower=0.0)
            piece["last_seal_delay"] = piece["real_last_seal_delay_minutes"]
            piece["real_open_board_count"] = open_board_count
            piece["board_height_real"] = board_count
            piece["real_board_count"] = board_count
            piece["seal_money_to_float_mv"] = seal_to_float
            piece["real_seal_amount_to_float_mv"] = seal_to_float
            piece["seal_money_to_amount"] = seal_to_amount
            piece["real_seal_amount_to_amount"] = seal_to_amount
            piece["real_one_word_board"] = one_word
            piece["real_early_seal"] = early_seal
            piece["seal_before_1030"] = (first <= 60.0).astype(float)
            piece["real_turnover_board"] = ((first > -4.0) & (turnover >= 3.0)).astype(float)
            piece["real_seal_stability_score"] = stability
            piece["seal_strength"] = stability
            piece["real_reseal_strength"] = reseal_strength
            piece["real_board_volume_acceptance"] = seal_to_amount.fillna(0.0) * turnover.clip(lower=0.0)
        if kind == "zt_pool_previous":
            pct_change = pd.to_numeric(frame.get("pct_change"), errors="coerce").fillna(0.0)
            piece["real_prev_zt_pct_change"] = pct_change
            piece["real_prev_zt_red"] = (pct_change > 0.0).astype(float)
        if kind == "zbgc_pool":
            piece["real_failed_board"] = 1.0
        if kind == "dtgc_pool":
            piece["real_limit_down_pressure"] = 1.0
        pieces.append(piece)
    if not pieces:
        return None
    merged = pieces[0]
    for piece in pieces[1:]:
        merged = merged.merge(piece, how="outer", on=["symbol", "date"])
    for column in LIMIT_POOL_SYMBOL_FACTOR_COLUMNS:
        if column not in merged.columns:
            merged[column] = 0.0
        merged[column] = pd.to_numeric(merged[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return FactorFrame(
        name="real_limit_pool_symbol_snapshot",
        frame=merged[["symbol", "date", *LIMIT_POOL_SYMBOL_FACTOR_COLUMNS]].copy(),
        columns=LIMIT_POOL_SYMBOL_FACTOR_COLUMNS,
        source="akshare_limit_pool_snapshot",
        asof_time="snapshot_or_after_close",
        lag_rule="Snapshot data is usable only at or after captured_at; after-close pools are for T+1 prediction.",
        join_keys=("symbol", "date"),
    )


def _build_limit_pool_market_factor(frames: Mapping[str, pd.DataFrame]) -> FactorFrame | None:
    dates = sorted({pd.Timestamp(value).normalize() for frame in frames.values() for value in pd.to_datetime(frame["trade_date"], errors="coerce").dropna()})
    if not dates:
        return None
    out = pd.DataFrame({"date": dates})
    counts: dict[str, pd.Series] = {}
    for kind, frame in frames.items():
        grouped = frame.groupby(pd.to_datetime(frame["trade_date"], errors="coerce").dt.normalize(), dropna=True)["symbol"].count()
        counts[kind] = grouped
    zt = frames.get("zt_pool", pd.DataFrame())
    if not zt.empty:
        zt_dates = pd.to_datetime(zt["trade_date"], errors="coerce").dt.normalize()
        first = pd.to_numeric(zt.get("first_seal_minutes"), errors="coerce")
        open_board_count = pd.to_numeric(zt.get("open_board_count"), errors="coerce").fillna(0.0)
        one_word = ((first <= -4.0) & (open_board_count <= 0.0)).astype(float)
        early = (first <= 30.0).astype(float)
        one_word_by_date = one_word.groupby(zt_dates, dropna=True).sum()
        early_by_date = early.groupby(zt_dates, dropna=True).sum()
        open_board_by_date = open_board_count.groupby(zt_dates, dropna=True).mean()
        mean_first_by_date = first.groupby(zt_dates, dropna=True).mean()
    else:
        one_word_by_date = pd.Series(dtype=float)
        early_by_date = pd.Series(dtype=float)
        open_board_by_date = pd.Series(dtype=float)
        mean_first_by_date = pd.Series(dtype=float)
    prev = frames.get("zt_pool_previous", pd.DataFrame())
    if not prev.empty:
        prev_dates = pd.to_datetime(prev["trade_date"], errors="coerce").dt.normalize()
        prev_pct = pd.to_numeric(prev.get("pct_change"), errors="coerce")
        prev_red_rate_by_date = prev_pct.gt(0.0).astype(float).groupby(prev_dates, dropna=True).mean()
        prev_mean_pct_by_date = prev_pct.groupby(prev_dates, dropna=True).mean()
    else:
        prev_red_rate_by_date = pd.Series(dtype=float)
        prev_mean_pct_by_date = pd.Series(dtype=float)
    out["market_real_zt_count"] = out["date"].map(counts.get("zt_pool", pd.Series(dtype=float))).fillna(0.0).astype(float)
    out["real_limit_up_count"] = out["market_real_zt_count"]
    out["market_real_zbgc_count"] = out["date"].map(counts.get("zbgc_pool", pd.Series(dtype=float))).fillna(0.0).astype(float)
    out["market_real_dtgc_count"] = out["date"].map(counts.get("dtgc_pool", pd.Series(dtype=float))).fillna(0.0).astype(float)
    out["market_real_strong_count"] = out["date"].map(counts.get("strong_pool", pd.Series(dtype=float))).fillna(0.0).astype(float)
    attempts = out["market_real_zt_count"] + out["market_real_zbgc_count"]
    out["market_real_attempt_count"] = attempts
    out["market_true_limit_ratio"] = (out["market_real_zt_count"] / attempts.replace(0.0, np.nan)).fillna(0.0)
    out["market_real_broken_board_rate"] = (out["market_real_zbgc_count"] / attempts.replace(0.0, np.nan)).fillna(0.0)
    out["market_real_limit_down_pressure"] = out["market_real_dtgc_count"] / np.maximum(out["market_real_zt_count"], 1.0)
    out["market_real_one_word_count"] = out["date"].map(one_word_by_date).fillna(0.0).astype(float)
    out["market_real_early_seal_count"] = out["date"].map(early_by_date).fillna(0.0).astype(float)
    out["market_real_avg_open_board_count"] = out["date"].map(open_board_by_date).fillna(0.0).astype(float)
    out["market_real_mean_seal_time_minutes"] = out["date"].map(mean_first_by_date).fillna(0.0).astype(float)
    out["market_prev_zt_count"] = out["date"].map(counts.get("zt_pool_previous", pd.Series(dtype=float))).fillna(0.0).astype(float)
    out["market_prev_zt_red_rate"] = out["date"].map(prev_red_rate_by_date).fillna(0.0).astype(float)
    out["prev_limit_pool_red_rate"] = out["market_prev_zt_red_rate"]
    out["market_prev_zt_mean_pct_change"] = out["date"].map(prev_mean_pct_by_date).fillna(0.0).astype(float)
    out["yesterday_zt_premium"] = out["market_prev_zt_mean_pct_change"]
    return FactorFrame(
        name="real_limit_pool_market_snapshot",
        frame=out[["date", *LIMIT_POOL_MARKET_FACTOR_COLUMNS]].copy(),
        columns=LIMIT_POOL_MARKET_FACTOR_COLUMNS,
        source="akshare_limit_pool_snapshot",
        asof_time="snapshot_or_after_close",
        lag_rule="Snapshot data is usable only at or after captured_at; after-close pools are for T+1 prediction.",
        join_keys=("date",),
    )


def _coerce_snapshot_frame(frame: pd.DataFrame, *, kind: str) -> pd.DataFrame:
    if set(NORMALIZED_COLUMNS).issubset(frame.columns):
        out = frame.copy()
    else:
        trade_date = _infer_trade_date(frame) or date.today()
        out = normalize_limit_pool_snapshot(frame, kind=kind, trade_date=trade_date, source_function=LIMIT_POOL_SOURCES.get(kind, kind))
    out["symbol"] = out["symbol"].astype(str).str.zfill(6)
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce")
    return out.dropna(subset=["trade_date"]).reset_index(drop=True)


def _manifest_payload_path(manifest_path: Path, payload: Any) -> Path:
    if not isinstance(payload, Mapping):
        return Path("")
    relative = str(payload.get("relative_path") or "")
    if relative:
        return manifest_path.parent / relative
    raw_path = str(payload.get("path") or "")
    if not raw_path:
        return Path("")
    path = Path(raw_path)
    if path.exists():
        return path
    if not path.is_absolute():
        return manifest_path.parent / path
    return manifest_path.parent / path.name


def _infer_trade_date(frame: pd.DataFrame) -> str | date | None:
    for column in ("trade_date", "date", "日期"):
        if column not in frame.columns:
            continue
        values = frame[column].dropna()
        if values.empty:
            continue
        value = values.iloc[0]
        timestamp = pd.to_datetime(value, errors="coerce")
        if pd.notna(timestamp):
            return timestamp.date()
        try:
            return _compact_trade_date(str(value))
        except ValueError:
            continue
    return None


def _compact_trade_date(value: str | date) -> str:
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    text = str(value).strip().replace("-", "")
    if not re.fullmatch(r"\d{8}", text):
        raise ValueError("trade_date must be YYYYMMDD or YYYY-MM-DD.")
    return text


def _first_present(frame: pd.DataFrame, aliases: Iterable[str]) -> str | None:
    columns = {str(column).strip(): column for column in frame.columns}
    for alias in aliases:
        if alias in columns:
            return columns[alias]
    return None


def _parse_numeric(value: Any) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return float("nan")
    if isinstance(value, (int, float, np.number)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "").replace("元", "")
    if not text or text.lower() in {"nan", "none", "-"}:
        return float("nan")
    multiplier = 1.0
    unit_multipliers = (("亿", 100_000_000.0), ("万", 10_000.0), ("千", 1_000.0), ("百", 100.0))
    for unit, value_multiplier in unit_multipliers:
        if text.endswith(unit):
            multiplier = value_multiplier
            text = text[: -len(unit)]
            break
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) * multiplier if match else float("nan")


def _clean_time_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "-"}:
        return ""
    digits = re.sub(r"\D", "", text)
    if len(digits) == 6:
        return f"{digits[:2]}:{digits[2:4]}:{digits[4:6]}"
    if len(digits) == 4:
        return f"{digits[:2]}:{digits[2:4]}:00"
    return text


def _minutes_from_open(value: str) -> float:
    if not value:
        return float("nan")
    try:
        parts = [int(part) for part in value.split(":")[:3]]
        current = time(parts[0], parts[1], parts[2] if len(parts) > 2 else 0)
    except (ValueError, TypeError):
        return float("nan")
    return (current.hour * 60 + current.minute + current.second / 60.0) - (9 * 60 + 30)


def _board_count_from_stat(values: pd.Series) -> pd.Series:
    text = values.astype(str)
    extracted = text.str.extract(r"(\d+)\s*(?:连板|天|板|Ìì|°å|Á¬°å)", expand=False)
    return pd.to_numeric(extracted, errors="coerce")


def _frame_hash(frame: pd.DataFrame) -> str:
    schema = {
        "columns": [str(column) for column in frame.columns],
        "rows": int(len(frame)),
        "sample": frame.head(20).astype(str).to_dict(orient="records"),
    }
    raw = json.dumps(schema, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _atomic_write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(tmp_path, index=False)
    tmp_path.replace(path)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture AKShare limit-pool snapshots for replayable short-line factors.")
    parser.add_argument("--date", help="Single trade date, YYYYMMDD or YYYY-MM-DD.")
    parser.add_argument("--start-date", help="Start trade date for business-day range capture.")
    parser.add_argument("--end-date", help="End trade date for business-day range capture.")
    parser.add_argument("--output-dir", required=True, help="Snapshot output directory.")
    parser.add_argument("--kinds", nargs="*", choices=sorted(LIMIT_POOL_SOURCES), default=sorted(LIMIT_POOL_SOURCES))
    parser.add_argument("--overwrite", action="store_true", help="Replace existing trade_date bundles.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue capturing later dates after a date fails.")
    args = parser.parse_args(argv)
    dates = _capture_dates(date_text=args.date, start_date=args.start_date, end_date=args.end_date)
    root = Path(args.output_dir)
    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requested_dates": dates,
        "captured": [],
        "skipped_existing": [],
        "failed": [],
    }
    for date_text in dates:
        manifest_path = root / f"trade_date={date_text}" / "manifest.json"
        if manifest_path.exists() and not args.overwrite:
            summary["skipped_existing"].append(date_text)
            continue
        try:
            frames: dict[str, pd.DataFrame] = {}
            kind_errors: list[dict[str, str]] = []
            for kind in args.kinds:
                try:
                    frames.update(fetch_limit_pool_snapshots(date_text, kinds=[kind]))
                except Exception as exc:
                    kind_errors.append({"kind": kind, "error": str(exc)})
                    if not args.continue_on_error:
                        raise
            if not frames:
                raise RuntimeError(f"no snapshot kinds captured: {kind_errors}")
            manifest = write_snapshot_bundle(frames, output_dir=root, trade_date=date_text)
            summary["captured"].append(
                {
                    "trade_date": date_text,
                    "manifest_path": manifest["manifest_path"],
                    "rows": {kind: payload["rows"] for kind, payload in manifest["kinds"].items()},
                    "kind_errors": kind_errors,
                }
            )
        except Exception as exc:
            summary["failed"].append({"trade_date": date_text, "error": str(exc)})
            if not args.continue_on_error:
                print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
                return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


def _capture_dates(*, date_text: str | None, start_date: str | None, end_date: str | None) -> list[str]:
    if date_text:
        if start_date or end_date:
            raise ValueError("--date cannot be combined with --start-date/--end-date.")
        return [_compact_trade_date(date_text)]
    if not start_date or not end_date:
        raise ValueError("Provide either --date or both --start-date and --end-date.")
    start = pd.to_datetime(_compact_trade_date(start_date), format="%Y%m%d")
    end = pd.to_datetime(_compact_trade_date(end_date), format="%Y%m%d")
    if start > end:
        raise ValueError("--start-date must be on or before --end-date.")
    return [value.strftime("%Y%m%d") for value in pd.bdate_range(start, end)]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
