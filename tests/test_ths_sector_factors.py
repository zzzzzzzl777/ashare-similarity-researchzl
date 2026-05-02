"""Unit tests for THS sector factors."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ashare_similarity.prediction.ths_sector_factors import (
    THS_SECTOR_COLUMNS,
    _compute_concept_streak,
    _compute_sector_factors,
    build_ths_sector_factors,
)


def _make_members() -> pd.DataFrame:
    return pd.DataFrame({
        "symbol": ["000001", "000001", "000002", "000002", "000003"],
        "concept_code": ["C001", "C002", "C001", "C003", "C002"],
    })


def _make_ths_daily() -> pd.DataFrame:
    dates = ["20240102", "20240103", "20240104"]
    rows = []
    for d in dates:
        rows.append({"concept_code": "C001", "trade_date": d, "pct_change": 2.0 + float(dates.index(d))})
        rows.append({"concept_code": "C002", "trade_date": d, "pct_change": -1.0 + float(dates.index(d))})
        rows.append({"concept_code": "C003", "trade_date": d, "pct_change": 0.5})
    return pd.DataFrame(rows)


def _make_limit_events() -> pd.DataFrame:
    return pd.DataFrame({
        "trade_date": ["20240102", "20240102", "20240103"],
        "symbol": ["000001", "000002", "000001"],
    })


class TestConceptStreak:
    def test_consecutive_ups(self):
        df = pd.DataFrame({
            "concept_code": ["C1", "C1", "C1", "C1"],
            "trade_date": ["20240101", "20240102", "20240103", "20240104"],
            "pct_change": [1.0, 2.0, -0.5, 1.0],
        })
        result = _compute_concept_streak(df)
        assert result["streak_days"].tolist() == [1.0, 2.0, 0.0, 1.0]

    def test_multiple_concepts(self):
        df = pd.DataFrame({
            "concept_code": ["C1", "C1", "C2", "C2"],
            "trade_date": ["20240101", "20240102", "20240101", "20240102"],
            "pct_change": [1.0, 1.0, -1.0, 1.0],
        })
        result = _compute_concept_streak(df)
        assert result["streak_days"].tolist() == [1.0, 2.0, 0.0, 1.0]


class TestComputeSectorFactors:
    def test_produces_all_columns(self):
        members = _make_members()
        ths_daily = _make_ths_daily()
        limit_events = _make_limit_events()
        result = _compute_sector_factors(members, ths_daily, limit_events)
        for col in THS_SECTOR_COLUMNS:
            assert col in result.columns, f"Missing: {col}"

    def test_best_concept_selected(self):
        members = _make_members()
        ths_daily = _make_ths_daily()
        result = _compute_sector_factors(members, ths_daily, pd.DataFrame(columns=["trade_date", "symbol"]))
        s1_day1 = result[(result["symbol"] == "000001") & (result["date"].dt.strftime("%Y%m%d") == "20240102")]
        assert len(s1_day1) == 1
        assert s1_day1.iloc[0]["sector_pct_change_best"] == pytest.approx(2.0)

    def test_strength_rank_range(self):
        members = _make_members()
        ths_daily = _make_ths_daily()
        result = _compute_sector_factors(members, ths_daily, pd.DataFrame(columns=["trade_date", "symbol"]))
        assert result["sector_strength_rank"].min() >= 0.0
        assert result["sector_strength_rank"].max() <= 1.0

    def test_divergence_nonzero_for_multi_concept(self):
        members = _make_members()
        ths_daily = _make_ths_daily()
        result = _compute_sector_factors(members, ths_daily, pd.DataFrame(columns=["trade_date", "symbol"]))
        s1 = result[result["symbol"] == "000001"]
        assert (s1["sector_divergence"] > 0).any()

    def test_empty_limit_events_works(self):
        members = _make_members()
        ths_daily = _make_ths_daily()
        result = _compute_sector_factors(members, ths_daily, pd.DataFrame(columns=["trade_date", "symbol"]))
        assert (result["sector_limit_up_count"] == 0).all()

    def test_limit_up_count_positive(self):
        members = _make_members()
        ths_daily = _make_ths_daily()
        limit_events = _make_limit_events()
        result = _compute_sector_factors(members, ths_daily, limit_events)
        s1_day1 = result[(result["symbol"] == "000001") & (result["date"].dt.strftime("%Y%m%d") == "20240102")]
        assert s1_day1.iloc[0]["sector_limit_up_count"] >= 1


class TestBuildThsSectorFactors:
    def test_from_real_cache(self):
        """Smoke test with actual cached data (skip if not available)."""
        from pathlib import Path
        tushare_dir = Path(r"E:\ashare_similarity_runtime\data\cache\prediction\tushare")
        if not (tushare_dir / "ths_member" / "all_members.parquet").exists():
            pytest.skip("No cached THS data")
        factor = build_ths_sector_factors(tushare_dir)
        assert factor.name == "ths_sector_daily"
        assert factor.join_keys == ("symbol", "date")
        assert len(factor.frame) > 0
        for col in THS_SECTOR_COLUMNS:
            assert col in factor.columns
        assert factor.frame[list(THS_SECTOR_COLUMNS)].isna().sum().sum() == 0
        print(f"Rows: {len(factor.frame)}")
        print(f"Date range: {factor.frame['date'].min()} to {factor.frame['date'].max()}")
        print(f"Unique symbols: {factor.frame['symbol'].nunique()}")
        print(factor.frame.describe().to_string())
