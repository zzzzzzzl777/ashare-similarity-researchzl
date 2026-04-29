from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ashare_similarity.config import SearchWeights
from ashare_similarity.schemas import ScoreBreakdown


@dataclass(slots=True)
class DistanceBreakdown:
    balanced_distance: float
    shape_distance: float
    price_path_distance: float
    candle_geometry_distance: float
    volume_liquidity_distance: float
    environment_distance: float


def dtw_distance(left: np.ndarray, right: np.ndarray) -> float:
    lhs = _trim_padding(np.asarray(left, dtype=np.float32))
    rhs = _trim_padding(np.asarray(right, dtype=np.float32))
    if lhs.size == 0 or rhs.size == 0:
        return float("inf")

    band = max(abs(len(lhs) - len(rhs)), max(len(lhs), len(rhs)) // 4, 2)
    cost = np.full((len(lhs) + 1, len(rhs) + 1), np.inf, dtype=np.float32)
    cost[0, 0] = 0.0
    for left_index in range(1, len(lhs) + 1):
        start = max(1, left_index - band)
        end = min(len(rhs) + 1, left_index + band + 1)
        for right_index in range(start, end):
            point_distance = abs(float(lhs[left_index - 1] - rhs[right_index - 1]))
            cost[left_index, right_index] = point_distance + min(
                cost[left_index - 1, right_index],
                cost[left_index, right_index - 1],
                cost[left_index - 1, right_index - 1],
            )
    return float(cost[len(lhs), len(rhs)] / (len(lhs) + len(rhs)))


def mean_distance(left: np.ndarray, right: np.ndarray) -> float:
    lhs = _trim_padding(np.asarray(left, dtype=np.float32))
    rhs = _trim_padding(np.asarray(right, dtype=np.float32))
    if lhs.size == 0 or rhs.size == 0:
        return float("inf")
    width = max(len(lhs), len(rhs))
    aligned_left = _align_vector(lhs, width)
    aligned_right = _align_vector(rhs, width)
    return float(np.sqrt(np.mean((aligned_left - aligned_right) ** 2, dtype=np.float32)))


def weighted_similarity(weighted_distance: float) -> float:
    if not np.isfinite(weighted_distance):
        return 0.0
    return float(1.0 / (1.0 + max(weighted_distance, 0.0)))


def safe_round(value: float | None, digits: int = 4) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(float(value), digits)


def score_window_pair(
    query_vector: np.ndarray,
    candidate_vector: np.ndarray,
    component_slices: dict[str, tuple[int, int]],
    weights: SearchWeights,
) -> tuple[ScoreBreakdown, DistanceBreakdown]:
    price_path_distance = dtw_distance(
        _close_path(query_vector, component_slices),
        _close_path(candidate_vector, component_slices),
    )
    candle_geometry_distance = mean_distance(
        _slice_component(query_vector, component_slices, "candle_geometry"),
        _slice_component(candidate_vector, component_slices, "candle_geometry"),
    )
    volume_liquidity_distance = mean_distance(
        _slice_component(query_vector, component_slices, "volume_liquidity"),
        _slice_component(candidate_vector, component_slices, "volume_liquidity"),
    )
    environment_distance = mean_distance(
        _slice_component(query_vector, component_slices, "environment"),
        _slice_component(candidate_vector, component_slices, "environment"),
    )

    balanced_distance = _weighted_distance(
        (
            (price_path_distance, weights.price_path),
            (candle_geometry_distance, weights.candle_geometry),
            (volume_liquidity_distance, weights.volume_liquidity),
            (environment_distance, weights.environment),
        )
    )
    shape_distance = _weighted_distance(
        (
            (price_path_distance, weights.price_path),
            (candle_geometry_distance, weights.candle_geometry),
        )
    )

    breakdown = DistanceBreakdown(
        balanced_distance=balanced_distance,
        shape_distance=shape_distance,
        price_path_distance=price_path_distance,
        candle_geometry_distance=candle_geometry_distance,
        volume_liquidity_distance=volume_liquidity_distance,
        environment_distance=environment_distance,
    )
    score = ScoreBreakdown(
        balanced=safe_round(weighted_similarity(balanced_distance), 6) or 0.0,
        shape=safe_round(weighted_similarity(shape_distance), 6) or 0.0,
        price_path_distance=safe_round(price_path_distance, 6) or 0.0,
        candle_geometry_distance=safe_round(candle_geometry_distance, 6) or 0.0,
        volume_liquidity_distance=safe_round(volume_liquidity_distance, 6) or 0.0,
        environment_distance=safe_round(environment_distance, 6) or 0.0,
    )
    return score, breakdown


def _slice_component(
    vector: np.ndarray,
    slices: dict[str, tuple[int, int]],
    name: str,
) -> np.ndarray:
    start, end = slices.get(name, (0, 0))
    return np.asarray(vector, dtype=np.float32)[start:end]


def _close_path(vector: np.ndarray, slices: dict[str, tuple[int, int]]) -> np.ndarray:
    price_path = _slice_component(vector, slices, "price_path")
    half = len(price_path) // 2
    return price_path[:half] if half else price_path


def _weighted_distance(items: tuple[tuple[float, float], ...]) -> float:
    total_weight = 0.0
    total_distance = 0.0
    for distance, weight in items:
        if weight <= 0 or not np.isfinite(distance):
            continue
        total_distance += distance * weight
        total_weight += weight
    if total_weight <= 0:
        return float("inf")
    return total_distance / total_weight


def _trim_padding(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    non_zero_indices = np.nonzero(values)[0]
    if non_zero_indices.size == 0:
        return np.zeros(0, dtype=np.float32)
    return values[: non_zero_indices[-1] + 1]


def _align_vector(values: np.ndarray, width: int) -> np.ndarray:
    if values.size == width:
        return values.astype(np.float32, copy=False)
    aligned = np.zeros(width, dtype=np.float32)
    usable = min(values.size, width)
    if usable:
        aligned[:usable] = values[:usable]
    return aligned
