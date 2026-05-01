from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from ashare_similarity.prediction.limit_pool_snapshots import (
    LIMIT_POOL_MARKET_FACTOR_COLUMNS,
    LIMIT_POOL_SYMBOL_FACTOR_COLUMNS,
    _capture_dates,
    build_limit_pool_snapshot_factors,
    fetch_limit_pool_snapshots,
    load_snapshot_bundles,
    normalize_limit_pool_snapshot,
    write_snapshot_bundle,
)


def test_normalize_limit_pool_snapshot_maps_eastmoney_columns():
    raw = pd.DataFrame(
        {
            "代码": ["600001"],
            "名称": ["短线测试"],
            "最新价": [11.2],
            "涨跌幅": ["10.01%"],
            "成交额": ["3.5亿"],
            "换手率": ["8.2%"],
            "流通市值": ["48亿"],
            "封板资金": ["1.2亿"],
            "首次封板时间": ["09:31:00"],
            "最后封板时间": ["10:15:00"],
            "炸板次数": [2],
            "连板数": [3],
            "所属行业": ["机器人"],
            "涨停原因": ["题材发酵"],
        }
    )

    out = normalize_limit_pool_snapshot(
        raw,
        kind="zt_pool",
        trade_date="20260430",
        source_function="stock_zt_pool_em",
        captured_at=datetime(2026, 4, 30, 8, 0, tzinfo=timezone.utc),
    )

    row = out.iloc[0]
    assert row["symbol"] == "600001"
    assert row["amount"] == 350_000_000.0
    assert row["seal_amount"] == 120_000_000.0
    assert row["first_seal_minutes"] == 1.0
    assert row["last_seal_minutes"] == 45.0
    assert row["board_count"] == 3.0
    assert row["kind"] == "zt_pool"


def test_fetch_limit_pool_snapshots_uses_selected_akshare_functions():
    raw = pd.DataFrame({"代码": ["600001"], "名称": ["短线测试"]})
    calls: list[tuple[str, str]] = []

    def zt(date: str):
        calls.append(("zt", date))
        return raw

    ak = SimpleNamespace(stock_zt_pool_em=zt)

    frames = fetch_limit_pool_snapshots("2026-04-30", kinds=["zt_pool"], ak_module=ak)

    assert calls == [("zt", "20260430")]
    assert frames["zt_pool"]["symbol"].tolist() == ["600001"]


def test_write_snapshot_bundle_creates_manifest_and_parquet(tmp_path: Path):
    frame = pd.DataFrame(
        {
            "kind": ["zt_pool"],
            "trade_date": [pd.Timestamp("2026-04-30")],
            "captured_at": [pd.Timestamp("2026-04-30T08:00:00Z")],
            "source_function": ["stock_zt_pool_em"],
            "source_hash": ["hash"],
            "symbol": ["600001"],
            "name": ["短线测试"],
            "close": [11.2],
            "pct_change": [10.0],
            "amount": [1.0],
            "turnover": [2.0],
            "float_market_cap": [3.0],
            "total_market_cap": [4.0],
            "seal_amount": [5.0],
            "first_seal_time": ["09:31:00"],
            "last_seal_time": ["10:15:00"],
            "first_seal_minutes": [1.0],
            "last_seal_minutes": [45.0],
            "open_board_count": [0.0],
            "board_count": [1.0],
            "board_type": [""],
            "industry": ["机器人"],
            "reason": ["题材发酵"],
        }
    )

    manifest = write_snapshot_bundle({"zt_pool": frame}, output_dir=tmp_path, trade_date="20260430")

    path = Path(manifest["kinds"]["zt_pool"]["path"])
    assert path.exists()
    assert Path(manifest["manifest_path"]).exists()
    assert pd.read_parquet(path)["symbol"].tolist() == ["600001"]
    assert manifest["kinds"]["zt_pool"]["relative_path"] == "zt_pool.parquet"


def test_load_snapshot_bundles_resolves_relative_and_moved_manifest_paths(tmp_path: Path):
    source = pd.DataFrame(
        {
            "kind": ["zt_pool"],
            "trade_date": [pd.Timestamp("2026-04-30")],
            "captured_at": [pd.Timestamp("2026-04-30T08:00:00Z")],
            "source_function": ["stock_zt_pool_em"],
            "source_hash": ["hash"],
            "symbol": ["600001"],
            "name": ["短线测试"],
            "close": [11.2],
            "pct_change": [10.0],
            "amount": [1.0],
            "turnover": [2.0],
            "float_market_cap": [3.0],
            "total_market_cap": [4.0],
            "seal_amount": [5.0],
            "first_seal_time": ["09:31:00"],
            "last_seal_time": ["10:15:00"],
            "first_seal_minutes": [1.0],
            "last_seal_minutes": [45.0],
            "open_board_count": [0.0],
            "board_count": [1.0],
            "board_type": [""],
            "industry": ["机器人"],
            "reason": ["题材发酵"],
        }
    )
    bundle_dir = tmp_path / "trade_date=20260430"
    bundle_dir.mkdir(parents=True)
    source.to_parquet(bundle_dir / "zt_pool.parquet", index=False)
    (bundle_dir / "manifest.json").write_text(
        """
{
  "trade_date": "20260430",
  "kinds": {
    "zt_pool": {
      "path": "C:/old/location/zt_pool.parquet",
      "relative_path": "zt_pool.parquet",
      "rows": 1
    }
  }
}
""".strip(),
        encoding="utf-8",
    )

    frames = load_snapshot_bundles(tmp_path)

    assert frames["zt_pool"]["symbol"].tolist() == ["600001"]


def test_capture_dates_supports_business_day_ranges():
    assert _capture_dates(date_text="2026-04-30", start_date=None, end_date=None) == ["20260430"]
    assert _capture_dates(date_text=None, start_date="2026-04-30", end_date="2026-05-04") == [
        "20260430",
        "20260501",
        "20260504",
    ]


def test_build_limit_pool_snapshot_factors_creates_symbol_and_market_frames():
    raw = pd.DataFrame(
        {
            "代码": ["600001", "600002"],
            "名称": ["短线测试A", "短线测试B"],
            "成交额": ["3亿", "2亿"],
            "封板资金": ["6000万", "1000万"],
            "流通市值": ["30亿", "20亿"],
            "换手率": ["8%", "12%"],
            "首次封板时间": ["09:25:00", "10:10:00"],
            "最后封板时间": ["09:25:00", "10:40:00"],
            "炸板次数": [0, 2],
            "连板数": [2, 1],
        }
    )
    failed = pd.DataFrame(
        {
            "代码": ["600003"],
            "名称": ["炸板测试"],
            "成交额": ["1亿"],
            "首次封板时间": ["10:00:00"],
            "炸板次数": [1],
        }
    )
    previous = pd.DataFrame(
        {
            "代码": ["600004", "600005"],
            "名称": ["昨日涨停A", "昨日涨停B"],
            "涨跌幅": ["5%", "-2%"],
        }
    )
    zt = normalize_limit_pool_snapshot(raw, kind="zt_pool", trade_date="20260430", source_function="stock_zt_pool_em")
    zbgc = normalize_limit_pool_snapshot(failed, kind="zbgc_pool", trade_date="20260430", source_function="stock_zt_pool_zbgc_em")
    prev = normalize_limit_pool_snapshot(
        previous,
        kind="zt_pool_previous",
        trade_date="20260430",
        source_function="stock_zt_pool_previous_em",
    )

    factors = build_limit_pool_snapshot_factors({"zt_pool": zt, "zbgc_pool": zbgc, "zt_pool_previous": prev})
    by_name = {factor.name: factor for factor in factors}

    symbol_factor = by_name["real_limit_pool_symbol_snapshot"]
    market_factor = by_name["real_limit_pool_market_snapshot"]
    assert set(LIMIT_POOL_SYMBOL_FACTOR_COLUMNS).issubset(symbol_factor.frame.columns)
    assert set(LIMIT_POOL_MARKET_FACTOR_COLUMNS).issubset(market_factor.frame.columns)
    first_row = symbol_factor.frame.sort_values("symbol").iloc[0]
    assert first_row["real_one_word_board"] == 1.0
    assert first_row["real_first_seal_rank_pct"] == 1.0
    assert first_row["real_seal_time_rank"] == 1.0
    assert first_row["seal_time_score"] == 1.0
    assert first_row["seal_before_1030"] == 1.0
    assert first_row["board_height_real"] == 2.0
    assert first_row["seal_money_to_float_mv"] == first_row["real_seal_amount_to_float_mv"]
    assert first_row["seal_money_to_amount"] == first_row["real_seal_amount_to_amount"]
    assert first_row["real_seal_stability_score"] > 1.0
    assert first_row["seal_strength"] == first_row["real_seal_stability_score"]
    prev_row = symbol_factor.frame.loc[symbol_factor.frame["symbol"] == "600004"].iloc[0]
    assert prev_row["real_in_prev_zt_pool"] == 1.0
    assert prev_row["real_prev_zt_red"] == 1.0
    assert market_factor.frame.loc[0, "market_real_zt_count"] == 2.0
    assert market_factor.frame.loc[0, "real_limit_up_count"] == 2.0
    assert market_factor.frame.loc[0, "market_real_zbgc_count"] == 1.0
    assert market_factor.frame.loc[0, "market_real_attempt_count"] == 3.0
    assert market_factor.frame.loc[0, "market_true_limit_ratio"] == 2.0 / 3.0
    assert market_factor.frame.loc[0, "market_real_one_word_count"] == 1.0
    assert market_factor.frame.loc[0, "market_prev_zt_count"] == 2.0
    assert market_factor.frame.loc[0, "market_prev_zt_red_rate"] == 0.5
    assert market_factor.frame.loc[0, "prev_limit_pool_red_rate"] == 0.5
    assert market_factor.frame.loc[0, "market_prev_zt_mean_pct_change"] == 1.5
    assert market_factor.frame.loc[0, "yesterday_zt_premium"] == 1.5


def test_raw_snapshot_factor_build_uses_source_trade_date_and_board_text():
    raw = pd.DataFrame(
        {
            "日期": ["2026-04-30"],
            "代码": ["600001"],
            "名称": ["短线测试"],
            "首次封板时间": ["09:31:00"],
            "最后封板时间": ["09:31:00"],
            "板型": ["3连板"],
        }
    )

    factors = build_limit_pool_snapshot_factors({"zt_pool": raw})
    symbol_factor = {factor.name: factor for factor in factors}["real_limit_pool_symbol_snapshot"]

    row = symbol_factor.frame.iloc[0]
    assert row["date"] == pd.Timestamp("2026-04-30")
    assert row["real_board_count"] == 3.0
