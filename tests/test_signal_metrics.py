from __future__ import annotations

import numpy as np
import pytest

from ashare_similarity.prediction.signals.metrics import (
    accuracy,
    baseline_brier,
    brier_score,
    confident_accuracy,
    coverage,
    wilson_lower_95,
)


def test_accuracy_perfect() -> None:
    y = np.array([1, 0, 1, 0])
    pred = np.array([1, 0, 1, 0])
    assert accuracy(y, pred) == 1.0


def test_accuracy_half() -> None:
    y = np.array([1, 0, 1, 0])
    pred = np.array([1, 1, 0, 0])
    assert accuracy(y, pred) == 0.5


def test_accuracy_empty() -> None:
    assert accuracy(np.array([]), np.array([])) == 0.0


def test_confident_accuracy() -> None:
    correct = np.array([True, False, True, True, False])
    mask = np.array([True, False, True, True, False])
    assert confident_accuracy(correct, mask) == pytest.approx(1.0)


def test_confident_accuracy_none_confident() -> None:
    correct = np.array([True, False])
    mask = np.array([False, False])
    assert confident_accuracy(correct, mask) == 0.0


def test_coverage_basic() -> None:
    mask = np.array([True, False, True, False, True])
    assert coverage(mask, 5) == pytest.approx(0.6)


def test_coverage_zero() -> None:
    assert coverage(np.array([False, False]), 0) == 0.0


def test_wilson_lower_95_basic() -> None:
    w = wilson_lower_95(80, 100)
    assert 0.70 < w < 0.80


def test_wilson_lower_95_perfect() -> None:
    w = wilson_lower_95(100, 100)
    assert w > 0.95


def test_wilson_lower_95_zero() -> None:
    assert wilson_lower_95(0, 0) == 0.0


def test_brier_score_perfect() -> None:
    y = np.array([1.0, 0.0, 1.0])
    p = np.array([1.0, 0.0, 1.0])
    assert brier_score(y, p) == pytest.approx(0.0)


def test_brier_score_worst() -> None:
    y = np.array([1.0, 0.0])
    p = np.array([0.0, 1.0])
    assert brier_score(y, p) == pytest.approx(1.0)


def test_baseline_brier() -> None:
    y = np.array([1.0, 1.0, 0.0, 0.0])
    b = baseline_brier(y)
    assert b == pytest.approx(0.25)


def test_baseline_brier_empty() -> None:
    assert baseline_brier(np.array([])) == 1.0
