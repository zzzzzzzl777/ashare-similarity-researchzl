from __future__ import annotations

import pytest

from ashare_similarity.prediction.signals.metrics import assign_split_layer


@pytest.mark.parametrize(
    "date_str,expected",
    [
        ("2025-07-01", "dev_valid"),
        ("2025-12-31", "dev_valid"),
        ("2025-08-15", "dev_valid"),
        ("2026-01-01", "seen_research"),
        ("2026-04-23", "seen_research"),
        ("2026-02-10", "seen_research"),
    ],
)
def test_assign_split_layer(date_str: str, expected: str) -> None:
    assert assign_split_layer(date_str) == expected


def test_dev_valid_boundary() -> None:
    assert assign_split_layer("2025-12-31") == "dev_valid"
    assert assign_split_layer("2026-01-01") == "seen_research"
