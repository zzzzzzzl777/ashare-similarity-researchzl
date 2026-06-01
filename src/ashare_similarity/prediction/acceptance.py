from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt
from typing import Any


WILSON_95_Z = 1.959963984540054


@dataclass(frozen=True, slots=True)
class AcceptanceThresholds:
    target_accuracy: float = 0.75
    legacy_default_test_rows: int = 50_000
    high_confidence_min_rows: int = 10_000
    high_confidence_min_coverage: float = 0.10
    statistical_min_rows: int = 1_000
    confidence_level: float = 0.95


def wilson_lower_bound(successes: int, total: int, *, z: float = WILSON_95_Z) -> float:
    """Return the lower Wilson score interval bound for a binomial proportion."""
    successes = int(successes)
    total = int(total)
    if total <= 0:
        return 0.0
    successes = min(max(successes, 0), total)
    phat = successes / total
    z2 = z * z
    denominator = 1.0 + z2 / total
    centre = phat + z2 / (2.0 * total)
    margin = z * sqrt((phat * (1.0 - phat) + z2 / (4.0 * total)) / total)
    return max(0.0, min(1.0, (centre - margin) / denominator))


def confidence_successes(accuracy: float | None, count: int) -> int:
    if accuracy is None or count <= 0:
        return 0
    return int(round(float(accuracy) * int(count)))


def build_prediction_acceptance(
    result: dict[str, Any],
    *,
    test_rows: int,
    required_test_rows: int,
    target_accuracy: float,
    future_label_filter_used: bool = False,
    thresholds: AcceptanceThresholds | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or AcceptanceThresholds(target_accuracy=float(target_accuracy))
    target = max(float(target_accuracy), float(thresholds.target_accuracy))
    test_rows = int(test_rows)
    required_test_rows = int(required_test_rows)

    all_accuracy = _optional_float(result.get("accuracy"), default=0.0)
    all_brier = _optional_float(result.get("brier"), default=1.0)
    baseline_brier = _optional_float(result.get("baseline_brier"), default=0.0)
    all_correct = int(result.get("correct_count") or confidence_successes(all_accuracy, test_rows))

    confident_accuracy = _optional_float(result.get("confident_accuracy"), default=None)
    confident_brier = _optional_float(result.get("confident_brier"), default=None)
    confident_count = int(result.get("confident_count") or 0)
    confident_coverage = _optional_float(
        result.get("confident_coverage"),
        default=(confident_count / test_rows if test_rows > 0 else 0.0),
    )
    confident_correct = int(
        result.get("confident_correct_count") or confidence_successes(confident_accuracy, confident_count)
    )
    wilson_lower = wilson_lower_bound(confident_correct, confident_count)

    sample_target_met = test_rows >= required_test_rows
    all_accuracy_met = all_accuracy >= target
    all_brier_met = baseline_brier > 0.0 and all_brier < baseline_brier
    high_accuracy_met = confident_accuracy is not None and confident_accuracy >= target
    high_brier_met = (
        confident_brier is not None
        and baseline_brier > 0.0
        and float(confident_brier) < baseline_brier
    )
    wilson_met = wilson_lower >= target
    coverage_gate_met = (
        confident_count >= int(thresholds.high_confidence_min_rows)
        and confident_coverage >= float(thresholds.high_confidence_min_coverage)
    )
    statistical_rows_met = confident_count >= int(thresholds.statistical_min_rows)
    count_consistent = 0 <= confident_count <= test_rows
    future_filter_allowed = False

    min_implied = ceil(int(thresholds.high_confidence_min_rows) / float(thresholds.high_confidence_min_coverage))

    passed = bool(
        high_accuracy_met
        and high_brier_met
        and wilson_met
        and coverage_gate_met
        and statistical_rows_met
        and count_consistent
        and not future_label_filter_used
    )

    return {
        "passed": passed,
        "status": "passed" if passed else "failed",
        "target_accuracy": float(target),
        "legacy_default_test_rows": int(thresholds.legacy_default_test_rows),
        "minimum_test_rows_implied_by_hc_gate": int(min_implied),
        "required_test_rows": int(required_test_rows),
        "actual_test_rows": int(test_rows),
        "test_rows_met": bool(sample_target_met),
        "sample_size_target_met": bool(sample_target_met),
        "sample_size_required_for_pass": False,
        "all_active": {
            "rows": int(test_rows),
            "correct_count": int(all_correct),
            "accuracy": float(all_accuracy),
            "accuracy_met": bool(all_accuracy_met),
            "brier": float(all_brier),
            "baseline_brier": float(baseline_brier),
            "brier_beats_baseline": bool(all_brier_met),
        },
        "high_confidence": {
            "rows": int(confident_count),
            "correct_count": int(confident_correct),
            "coverage": float(confident_coverage),
            "accuracy": confident_accuracy,
            "accuracy_met": bool(high_accuracy_met),
            "brier": confident_brier,
            "baseline_brier": float(baseline_brier),
            "brier_beats_baseline": bool(high_brier_met),
            "wilson_lower_95": float(wilson_lower),
            "wilson_lower_met": bool(wilson_met),
            "min_rows": int(thresholds.high_confidence_min_rows),
            "min_coverage": float(thresholds.high_confidence_min_coverage),
            "coverage_gate_met": bool(coverage_gate_met),
            "statistical_min_rows": int(thresholds.statistical_min_rows),
            "statistical_rows_met": bool(statistical_rows_met),
            "count_consistent_with_lockbox": bool(count_consistent),
        },
        "accuracy": float(all_accuracy),
        "accuracy_met": bool(all_accuracy_met),
        "brier": float(all_brier),
        "baseline_brier": float(baseline_brier),
        "brier_beats_baseline": bool(all_brier_met),
        "future_label_filter_used": bool(future_label_filter_used),
        "future_label_filter_allowed": future_filter_allowed,
        "rule": (
            "Pass only on the validation-selected high-confidence lockbox subset: "
            "accuracy >= target, Brier beats baseline, Wilson 95% lower bound >= target, "
            "sample/coverage gate met, no future-label filter, and lockbox counts are consistent. "
            "All active-phase metrics are reported but do not by themselves approve release."
        ),
    }


def _optional_float(value: Any, *, default: float | None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
