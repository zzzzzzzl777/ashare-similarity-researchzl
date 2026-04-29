from __future__ import annotations

import pandas as pd

from ashare_similarity.prediction.factor_cache_manager import FactorFrame, merge_factor_frames


def test_merge_factor_frames_adds_availability_and_metadata():
    base = pd.DataFrame(
        {
            "symbol": ["600001", "600002"],
            "date": pd.to_datetime(["2024-01-02", "2024-01-02"]),
            "ret_1": [1.0, -1.0],
        }
    )
    factor = FactorFrame(
        name="northbound_flow",
        frame=pd.DataFrame(
            {
                "symbol": ["600001"],
                "date": pd.to_datetime(["2024-01-02"]),
                "northbound_net_buy": [100.0],
            }
        ),
        columns=("northbound_net_buy",),
        source="akshare",
        asof_time="after_close",
        lag_rule="T+1 for next-day prediction",
    )

    merged, reports = merge_factor_frames(base, [factor])

    assert merged.loc[0, "northbound_net_buy"] == 100.0
    assert merged.loc[0, "northbound_net_buy_available"] == 1.0
    assert merged.loc[1, "northbound_net_buy"] == 0.0
    assert merged.loc[1, "northbound_net_buy_available"] == 0.0
    assert reports[0]["source"] == "akshare"
    assert reports[0]["asof_time"] == "after_close"
    assert reports[0]["lag_rule"] == "T+1 for next-day prediction"
    assert reports[0]["coverage_rate"] == 0.5
