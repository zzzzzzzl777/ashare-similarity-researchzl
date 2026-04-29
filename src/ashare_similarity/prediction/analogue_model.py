from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ashare_similarity.prediction.factor_builder import FACTOR_COLUMNS
from ashare_similarity.prediction.label_builder import ForwardLabel


@dataclass(slots=True)
class AnalogueSample:
    symbol: str
    name: str | None
    window_size: int
    start_date: str
    end_date: str
    similarity: float
    factors: dict[str, float]
    labels: dict[int, ForwardLabel]


@dataclass(slots=True)
class AnaloguePrediction:
    horizon: int
    sample_count: int
    up_probability: float | None
    expected_return_pct: float | None
    quantiles_pct: dict[str, float | None]
    max_drawdown_risk_pct: float | None
    scenarios: dict[str, float]


def predict_from_analogues(
    samples: list[AnalogueSample],
    horizons: list[int],
    *,
    query_vector: dict[str, float] | None = None,
) -> dict[int, AnaloguePrediction]:
    return {horizon: _predict_horizon(samples, horizon, query_vector=query_vector) for horizon in horizons}


def _predict_horizon(
    samples: list[AnalogueSample],
    horizon: int,
    *,
    query_vector: dict[str, float] | None = None,
) -> AnaloguePrediction:
    usable = [sample for sample in samples if _label_return(sample, horizon) is not None]
    if not usable:
        return AnaloguePrediction(
            horizon=horizon,
            sample_count=0,
            up_probability=None,
            expected_return_pct=None,
            quantiles_pct={"p10": None, "p50": None, "p90": None},
            max_drawdown_risk_pct=None,
            scenarios={},
        )

    weights = np.asarray(
        [
            max(float(sample.similarity), 0.001) ** 2 * _factor_similarity(query_vector, sample.factors)
            for sample in usable
        ],
        dtype=float,
    )
    weights = weights / weights.sum() if weights.sum() > 0 else np.ones(len(usable), dtype=float) / len(usable)
    returns = np.asarray([float(_label_return(sample, horizon) or 0.0) for sample in usable], dtype=float)
    mdds = np.asarray(
        [
            float(sample.labels[horizon].max_drawdown_pct)
            for sample in usable
            if sample.labels[horizon].max_drawdown_pct is not None
        ],
        dtype=float,
    )
    scenario_weights: defaultdict[str, float] = defaultdict(float)
    for sample, weight in zip(usable, weights, strict=False):
        scenario = sample.labels[horizon].scenario or "unknown"
        scenario_weights[scenario] += float(weight)

    return AnaloguePrediction(
        horizon=horizon,
        sample_count=len(usable),
        up_probability=round(float(np.sum(weights * (returns > 0))), 4),
        expected_return_pct=round(float(np.sum(weights * returns)), 4),
        quantiles_pct={
            "p10": round(float(np.quantile(returns, 0.10)), 4),
            "p50": round(float(np.quantile(returns, 0.50)), 4),
            "p90": round(float(np.quantile(returns, 0.90)), 4),
        },
        max_drawdown_risk_pct=round(float(np.mean(mdds)), 4) if mdds.size else None,
        scenarios={key: round(value, 4) for key, value in sorted(scenario_weights.items())},
    )


def _label_return(sample: AnalogueSample, horizon: int) -> float | None:
    label = sample.labels.get(horizon)
    return None if label is None else label.return_pct


def _factor_similarity(query_vector: dict[str, float] | None, sample_vector: dict[str, float]) -> float:
    if query_vector is None:
        return 1.0
    distances: list[float] = []
    for column in FACTOR_COLUMNS:
        query_value = _safe_float(query_vector.get(column))
        sample_value = _safe_float(sample_vector.get(column))
        scale = max(abs(query_value), abs(sample_value), 1.0)
        distances.append(abs(query_value - sample_value) / scale)
    if not distances:
        return 1.0
    distance = float(np.mean(distances))
    return float(np.clip(np.exp(-1.5 * distance), 0.2, 1.0))


def _safe_float(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if np.isfinite(number) else 0.0
