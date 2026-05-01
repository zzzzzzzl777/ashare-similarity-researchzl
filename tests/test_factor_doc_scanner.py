from __future__ import annotations

import json
from pathlib import Path

from ashare_similarity.prediction.factor_doc_scanner import scan_factor_doc, write_candidates


def test_scan_factor_doc_extracts_candidates_and_classifies_data_needs(tmp_path: Path):
    doc = tmp_path / "taoguba.md"
    doc.write_text(
        """
# 淘股吧短线因子
### P0 - 最高优先级

| P0 | `real_seal_time_rank` | 当日涨停股按首次封板时间排序 | AKShare `stock_zt_pool_em` 涨停池 |

### P1 - 高优先级

**二封/三封分级确认 seal_grade_confirmation**：分钟线 + 封单数据，部分个股需要三封。

### P2 - 中优先级

| P2 | `lhb_net_buy_to_amount` | 龙虎榜净买额 / 当日成交额 | 龙虎榜盘后披露，只能预测次日 |
""".strip(),
        encoding="utf-8",
    )

    candidates = scan_factor_doc(doc)
    by_name = {candidate.factor_name: candidate for candidate in candidates}

    assert "real_seal_time_rank" in by_name
    assert by_name["real_seal_time_rank"].priority == "P0"
    assert "limit_pool" in by_name["real_seal_time_rank"].data_needs
    assert by_name["real_seal_time_rank"].suggested_bucket == "expanded"
    assert "seal_grade_confirmation" in by_name
    assert by_name["seal_grade_confirmation"].needs_minute is True
    assert by_name["seal_grade_confirmation"].needs_level2 is True
    assert by_name["seal_grade_confirmation"].future_leakage_risk == "medium"
    assert "lhb_net_buy_to_amount" in by_name
    assert by_name["lhb_net_buy_to_amount"].asof_time == "after_close"
    assert by_name["lhb_net_buy_to_amount"].suggested_bucket == "research"


def test_scan_factor_doc_extracts_heading_and_formula_names(tmp_path: Path):
    doc = tmp_path / "taoguba_new.md"
    doc.write_text(
        """
# 新增短线因子

#### 突破首板形态因子 breakout_first_board

- `late_surge_ratio = (close - price_1430) / (close - open)`
""".strip(),
        encoding="utf-8",
    )

    candidates = scan_factor_doc(doc)
    by_name = {candidate.factor_name: candidate for candidate in candidates}

    assert "breakout_first_board" in by_name
    assert "late_surge_ratio" in by_name
    assert "price_1430" not in by_name


def test_scan_factor_doc_filters_source_functions_and_understands_english_source_hints(tmp_path: Path):
    doc = tmp_path / "short_line.md"
    doc.write_text(
        """
### P0 source aligned factors

| P0 | `real_seal_time_rank` | AKShare `stock_zt_pool_em` limit_pool seal time |
| P0 | `seal_money_to_float_mv` | `stock_zt_pool_em` seal_amount / float_market_cap |
""".strip(),
        encoding="utf-8",
    )

    candidates = scan_factor_doc(doc)
    by_name = {candidate.factor_name: candidate for candidate in candidates}

    assert "stock_zt_pool_em" not in by_name
    assert "real_seal_time_rank" in by_name
    assert "limit_pool" in by_name["real_seal_time_rank"].data_needs
    assert by_name["real_seal_time_rank"].asof_time == "after_close"
    assert by_name["real_seal_time_rank"].suggested_bucket == "expanded"
    assert set(by_name["seal_money_to_float_mv"].data_needs) == {"daily_ohlcv", "limit_pool"}


def test_scan_factor_doc_filters_generic_code_tokens_from_jsonl_candidate_pool(tmp_path: Path):
    doc = tmp_path / "noisy.md"
    doc.write_text(
        """
# P0 factor table

| P0 | `real_seal_time_rank` | source score signal action |
- score = base_weights + signal
""".strip(),
        encoding="utf-8",
    )

    candidates = scan_factor_doc(doc)
    names = {candidate.factor_name for candidate in candidates}

    assert "real_seal_time_rank" in names
    assert "score" not in names
    assert "signal" not in names
    assert "action" not in names


def test_write_candidates_emits_jsonl_and_summary(tmp_path: Path):
    doc = tmp_path / "taoguba.md"
    doc.write_text("### P0\n| P0 | `emotion_phase` | 日线 情绪周期 |", encoding="utf-8")
    output = tmp_path / "candidates.jsonl"

    summary = write_candidates(scan_factor_doc(doc), output)

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["factor_name"] == "emotion_phase"
    assert summary["candidate_count"] == 1
    assert (tmp_path / "candidates.jsonl.summary.json").exists()
