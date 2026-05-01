from __future__ import annotations

from datetime import date

import pandas as pd

from ashare_similarity.prediction.rule_miner import (
    RuleCondition,
    condition_mask,
    evaluate_rule,
    mine_high_confidence_rules,
)
from ashare_similarity.prediction.split_protocol import SplitProtocolConfig


def test_evaluate_rule_reports_accuracy_and_date_stability():
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-02", "2026-01-02", "2026-01-05"]),
            "label_date": pd.to_datetime(["2026-01-05", "2026-01-05", "2026-01-06"]),
            "actual": [1, 1, 0],
            "fear_signal": [2.0, 3.0, 0.1],
        }
    )
    condition = RuleCondition("fear_signal", ">=", 1.0)

    mask = condition_mask(frame, condition)
    stats = evaluate_rule(frame, [condition], prediction=1, mask=mask)

    assert stats.rows == 2
    assert stats.correct_count == 2
    assert stats.accuracy == 1.0
    assert stats.date_count == 1
    assert stats.wilson_lower_95 > 0.0


def test_mine_high_confidence_rules_uses_validation_selected_rules():
    dates = pd.bdate_range("2026-01-01", periods=14)
    rows = []
    for day_index, day in enumerate(dates):
        for row_index in range(8):
            signal = 10.0 if row_index < 4 else 0.0
            actual = 1 if signal > 0 and day_index not in {2, 7} else 0
            rows.append(
                {
                    "symbol": f"600{row_index:03d}",
                    "date": day,
                    "label_date": day + pd.Timedelta(days=1),
                    "actual": actual,
                    "fear_signal": signal,
                    "noise": float(row_index),
                }
            )
    frame = pd.DataFrame(rows)

    report = mine_high_confidence_rules(
        frame,
        SplitProtocolConfig(
            train_end=date(2026, 1, 14),
            test_start=date(2026, 1, 15),
            end=date(2026, 1, 25),
            validation_fraction=0.30,
            embargo_trading_days=0,
            max_fit_rows=None,
            seed=42,
        ),
        max_rules=5,
        min_fit_rows=8,
        min_validation_rows=4,
        min_fit_accuracy=0.55,
        min_validation_accuracy=0.55,
        min_fit_dates=2,
        min_validation_dates=1,
    )

    assert report["selection_protocol"] == "fit_proposes_validation_selects_test_reports"
    assert report["rules"]
    top = report["rules"][0]
    assert top["selected_by"] == "validation_only"
    assert top["validation"]["rows"] >= 4
    assert top["test"]["rows"] >= 0
