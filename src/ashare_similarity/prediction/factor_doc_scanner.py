from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_BACKTICK_FACTOR_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]{2,})`")
_BACKTICK_ASSIGNMENT_RE = re.compile(r"`\s*([A-Za-z_][A-Za-z0-9_]{2,})\s*=")
_ASSIGNMENT_RE = re.compile(r"^\s*[-*]?\s*`?\s*([A-Za-z_][A-Za-z0-9_]{2,})\s*=")
_BOLD_SNAKE_RE = re.compile(r"\*\*[^*\n]*?\b([a-z][a-z0-9_]{2,})\b[^*\n]*?\*\*")
_SNAKE_TOKEN_RE = re.compile(r"\b([a-z][a-z0-9]+(?:_[a-z0-9]+)+)\b")
_PRIORITY_RE = re.compile(r"\b(P[0-3])\b", re.IGNORECASE)
_IGNORED_FACTOR_TOKENS = frozenset(
    {
        "action",
        "akshare",
        "conditions",
        "decision",
        "factor",
        "Factor",
        "implication",
        "level",
        "mid",
        "phase",
        "position",
        "reason",
        "rules",
        "score",
        "Score",
        "signal",
        "signals",
        "stock_market_activity_legu",
        "stock_zh_a_hist",
        "stock_zh_a_spot_em",
        "strategy",
    }
)

DATA_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("daily_ohlcv", ("日线", "OHLCV", "收盘", "成交额", "换手", "涨跌幅")),
    ("minute", ("分钟线", "分时", "第一分钟", "开盘分钟", "尾盘", "14:30", "VWAP")),
    ("auction", ("竞价", "9:15", "9:20", "9:25", "9:30", "盘前分钟")),
    ("level2", ("Level2", "封单", "买一", "撤单", "逐笔", "十档")),
    ("limit_pool", ("涨停池", "炸板池", "跌停池", "封板时间", "炸板次数", "连板数", "涨停", "炸板", "回封")),
    ("sector_theme", ("板块", "题材", "概念", "成分", "龙头", "小弟", "热点")),
    ("lhb", ("龙虎榜", "席位", "营业部", "机构", "游资")),
    ("hot_rank", ("人气榜", "股吧", "关键词", "热度", "关注度", "发帖量", "搜索")),
    ("announcement", ("公告", "监管", "异动", "重点监控", "风险提示")),
    ("cross_market", ("美股", "港股", "A50", "期货", "外盘", "VIX")),
)

ASOF_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("intraday_snapshot", ("实时", "日内", "快照", "盘中", "9:15", "9:20", "9:25", "9:30")),
    ("after_close", ("盘后", "收盘后", "龙虎榜", "公告", "当日收盘", "T+1")),
    ("source_limited_history", ("只能获取近期", "必须快照", "历史要每日落地", "不能回填")),
)

ENGLISH_DATA_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "daily_ohlcv",
        (
            "ohlcv",
            "open_price",
            "close",
            "volume",
            "amount",
            "turnover",
            "float_mv",
            "float_market_cap",
            "prev_top20_chase",
            "premium_gap",
        ),
    ),
    ("minute", ("minute", "intraday", "30min", "14:30", "last_30min", "late_surge")),
    ("auction", ("auction", "one_word_board")),
    ("level2", ("level2", "best_bid", "best_ask", "order_book", "mega_order")),
    (
        "limit_pool",
        (
            "limit_pool",
            "zt_pool",
            "stock_zt_pool",
            "zbgc",
            "dtgc",
            "seal",
            "open_board",
            "board_count",
            "board_height",
            "broken_board",
            "limit_up",
            "real_limit",
            "last_seal",
        ),
    ),
    ("sector_theme", ("sector", "theme", "concept", "stock_board_concept")),
    ("lhb", ("lhb", "dragon_tiger")),
    ("hot_rank", ("hot_rank", "popularity_rank", "popularity")),
    ("announcement", ("announcement", "disclosure")),
    ("cross_market", ("cross_market", "a50", "vix", "futures")),
)


@dataclass(frozen=True, slots=True)
class FactorDocCandidate:
    factor_name: str
    line_number: int
    section: str
    priority: str
    data_needs: tuple[str, ...]
    asof_time: str
    free_data: bool
    needs_daily: bool
    needs_minute: bool
    needs_level2: bool
    future_leakage_risk: str
    suggested_bucket: str
    raw_text: str
    source_path: str
    source_hash: str
    source_mtime: str
    source_size: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scan_factor_doc(path: str | Path) -> list[FactorDocCandidate]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    source_stat = source.stat()
    source_mtime = datetime.fromtimestamp(source_stat.st_mtime, tz=timezone.utc).isoformat()
    candidates: list[FactorDocCandidate] = []
    section_stack: list[tuple[int, str]] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        heading = _HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            section_stack = [(item_level, item_title) for item_level, item_title in section_stack if item_level < level]
            section_stack.append((level, title))
            section = " > ".join(item_title for _, item_title in section_stack)
            for name in _factor_names_from_line(title, allow_bare_snake=True):
                candidates.append(
                    _build_candidate(
                        factor_name=name,
                        line_number=line_number,
                        section=section,
                        raw_text=title,
                        source_path=str(source),
                        source_hash=source_hash,
                        source_mtime=source_mtime,
                        source_size=source_stat.st_size,
                    )
                )
            continue
        names = _factor_names_from_line(line)
        if not names:
            continue
        section = " > ".join(title for _, title in section_stack)
        for name in names:
            candidates.append(
                _build_candidate(
                    factor_name=name,
                    line_number=line_number,
                    section=section,
                    raw_text=line,
                    source_path=str(source),
                    source_hash=source_hash,
                    source_mtime=source_mtime,
                    source_size=source_stat.st_size,
                )
            )
    return candidates


def write_candidates(candidates: Iterable[FactorDocCandidate], output: str | Path) -> dict[str, Any]:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [candidate.to_dict() for candidate in candidates]
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    summary = _summary(rows)
    summary_path = output_path.with_suffix(output_path.suffix + ".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def _factor_names_from_line(line: str, *, allow_bare_snake: bool = False) -> tuple[str, ...]:
    if not line or line.startswith("```"):
        return tuple()
    names = list(_BACKTICK_ASSIGNMENT_RE.findall(line))
    names.extend(_ASSIGNMENT_RE.findall(line))
    names.extend(_BACKTICK_FACTOR_RE.findall(line))
    names.extend(_BOLD_SNAKE_RE.findall(line))
    if allow_bare_snake:
        names.extend(_SNAKE_TOKEN_RE.findall(line))
    if not names:
        return tuple()
    return tuple(dict.fromkeys(name for name in names if _is_factor_name_candidate(name)))


def _is_factor_name_candidate(name: str) -> bool:
    lowered = name.lower()
    if lowered.startswith("__"):
        return False
    if lowered in _IGNORED_FACTOR_TOKENS:
        return False
    if lowered.startswith("stock_") and lowered.endswith("_em"):
        return False
    return True


def _build_candidate(
    *,
    factor_name: str,
    line_number: int,
    section: str,
    raw_text: str,
    source_path: str,
    source_hash: str,
    source_mtime: str,
    source_size: int,
) -> FactorDocCandidate:
    priority_context = f"{section} {raw_text}"
    priority = _priority(priority_context)
    data_needs = _data_needs(raw_text)
    asof_time = _asof_time(raw_text, data_needs)
    needs_daily = "daily_ohlcv" in data_needs
    needs_minute = "minute" in data_needs or "auction" in data_needs
    needs_level2 = "level2" in data_needs
    free_data = _is_free_data(raw_text, data_needs)
    future_leakage_risk = _future_leakage_risk(raw_text, data_needs, asof_time)
    suggested_bucket = _suggested_bucket(
        priority=priority,
        data_needs=data_needs,
        free_data=free_data,
        future_leakage_risk=future_leakage_risk,
    )
    return FactorDocCandidate(
        factor_name=factor_name,
        line_number=line_number,
        section=section,
        priority=priority,
        data_needs=data_needs,
        asof_time=asof_time,
        free_data=free_data,
        needs_daily=needs_daily,
        needs_minute=needs_minute,
        needs_level2=needs_level2,
        future_leakage_risk=future_leakage_risk,
        suggested_bucket=suggested_bucket,
        raw_text=raw_text,
        source_path=source_path,
        source_hash=source_hash,
        source_mtime=source_mtime,
        source_size=source_size,
    )


def _priority(text: str) -> str:
    match = _PRIORITY_RE.search(text)
    if match:
        return match.group(1).upper()
    if "最高优先级" in text:
        return "P0"
    if "高优先级" in text:
        return "P1"
    if "中优先级" in text:
        return "P2"
    if "低优先级" in text:
        return "P3"
    return "unknown"


def _data_needs(text: str) -> tuple[str, ...]:
    needs: list[str] = []
    lower = text.lower()
    for need, keywords in (*DATA_KEYWORDS, *ENGLISH_DATA_KEYWORDS):
        if any(keyword.lower() in lower for keyword in keywords):
            needs.append(need)
    return tuple(dict.fromkeys(needs or ["unknown"]))


def _asof_time(text: str, data_needs: tuple[str, ...]) -> str:
    lower = text.lower()
    matches: list[str] = []
    for asof, keywords in ASOF_KEYWORDS:
        if any(keyword.lower() in lower for keyword in keywords):
            matches.append(asof)
    if "lhb" in data_needs or "announcement" in data_needs:
        matches.append("after_close")
    if "daily_ohlcv" in data_needs or "limit_pool" in data_needs or "sector_theme" in data_needs:
        matches.append("after_close")
    if "auction" in data_needs or "minute" in data_needs or "hot_rank" in data_needs:
        matches.append("intraday_snapshot")
    if not matches:
        return "unknown"
    return "+".join(dict.fromkeys(matches))


def _is_free_data(text: str, data_needs: tuple[str, ...]) -> bool:
    lower = text.lower()
    if "level2" in data_needs:
        return False
    if "免费" in text:
        return True
    if "akshare" in lower or "免费" in text:
        return True
    return bool({"daily_ohlcv", "limit_pool", "sector_theme", "lhb", "hot_rank", "announcement"} & set(data_needs))


def _future_leakage_risk(text: str, data_needs: tuple[str, ...], asof_time: str) -> str:
    if "不能预测同日" in text or ("不能用" in text and "同日" in text):
        return "high"
    if "level2" in data_needs:
        return "medium"
    if "source_limited_history" in asof_time:
        return "medium"
    if "lhb" in data_needs or "announcement" in data_needs:
        return "medium"
    if "intraday_snapshot" in asof_time:
        return "medium"
    return "low"


def _suggested_bucket(
    *,
    priority: str,
    data_needs: tuple[str, ...],
    free_data: bool,
    future_leakage_risk: str,
) -> str:
    if future_leakage_risk == "high":
        return "blocked"
    if "level2" in data_needs and not free_data:
        return "blocked"
    if priority in {"P0", "P1"} and free_data and future_leakage_risk == "low":
        return "expanded"
    return "research"


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def count_by(key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in rows:
            value = str(row.get(key) or "unknown")
            out[value] = out.get(value, 0) + 1
        return dict(sorted(out.items()))

    needs: dict[str, int] = {}
    for row in rows:
        for need in row.get("data_needs") or ["unknown"]:
            needs[str(need)] = needs.get(str(need), 0) + 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(rows),
        "by_priority": count_by("priority"),
        "by_bucket": count_by("suggested_bucket"),
        "by_future_leakage_risk": count_by("future_leakage_risk"),
        "by_data_need": dict(sorted(needs.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan a short-line factor Markdown document into JSONL candidates.")
    parser.add_argument("--input", required=True, help="Markdown factor document path.")
    parser.add_argument("--output", required=True, help="Output JSONL path.")
    args = parser.parse_args(argv)
    candidates = scan_factor_doc(args.input)
    summary = write_candidates(candidates, args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
