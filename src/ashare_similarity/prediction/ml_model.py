from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ashare_similarity.prediction.analogue_model import AnalogueSample
from ashare_similarity.prediction.factor_builder import FACTOR_COLUMNS, vector_to_array


@dataclass(slots=True)
class MLPrediction:
    horizon: int
    status: str
    sample_count: int
    up_probability: float | None = None
    expected_return_pct: float | None = None
    validation_metrics: dict[str, float | None] = field(default_factory=dict)
    passed_validation: bool = False


def predict_with_ml(
    samples: list[AnalogueSample],
    query_vector: dict[str, float],
    horizons: list[int],
) -> dict[int, MLPrediction]:
    return {horizon: _predict_horizon(samples, query_vector, horizon) for horizon in horizons}


def _predict_horizon(samples: list[AnalogueSample], query_vector: dict[str, float], horizon: int) -> MLPrediction:
    usable = [sample for sample in samples if sample.labels.get(horizon) and sample.labels[horizon].return_pct is not None]
    if len(usable) < 40:
        return MLPrediction(horizon=horizon, status="insufficient_samples", sample_count=len(usable))

    usable = sorted(usable, key=lambda sample: sample.end_date)
    y_return = np.asarray([float(sample.labels[horizon].return_pct or 0.0) for sample in usable], dtype=float)
    y = (y_return > 0).astype(int)
    if len(set(y.tolist())) < 2:
        return MLPrediction(horizon=horizon, status="single_class", sample_count=len(usable))

    x = np.asarray([vector_to_array(sample.factors) for sample in usable], dtype=float)
    query_x = np.asarray([vector_to_array(query_vector)], dtype=float)
    split = max(int(len(usable) * 0.7), 10)
    if split >= len(usable) - 5:
        split = len(usable) - 5
    if split <= 0:
        return MLPrediction(horizon=horizon, status="insufficient_validation", sample_count=len(usable))

    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception as exc:  # pragma: no cover - depends on optional runtime install state
        return MLPrediction(
            horizon=horizon,
            status=f"sklearn_unavailable: {exc}",
            sample_count=len(usable),
        )

    train_x, valid_x = x[:split], x[split:]
    train_y, valid_y = y[:split], y[split:]
    if len(set(train_y.tolist())) < 2 or len(valid_y) == 0:
        return MLPrediction(horizon=horizon, status="insufficient_class_balance", sample_count=len(usable))

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=500, class_weight="balanced", random_state=42),
    )
    model.fit(train_x, train_y)
    valid_prob = model.predict_proba(valid_x)[:, 1]
    baseline_prob = np.full_like(valid_prob, float(train_y.mean()), dtype=float)
    brier = float(np.mean((valid_prob - valid_y) ** 2))
    baseline_brier = float(np.mean((baseline_prob - valid_y) ** 2))
    accuracy = float(np.mean((valid_prob >= 0.5) == valid_y))
    baseline_accuracy = float(max(valid_y.mean(), 1.0 - valid_y.mean()))
    passed = bool(brier <= baseline_brier and accuracy >= baseline_accuracy)

    model.fit(x, y)
    probability = float(model.predict_proba(query_x)[0, 1])
    positive_mean = float(np.mean(y_return[y == 1])) if np.any(y == 1) else 0.0
    negative_mean = float(np.mean(y_return[y == 0])) if np.any(y == 0) else 0.0
    expected_return = probability * positive_mean + (1.0 - probability) * negative_mean
    return MLPrediction(
        horizon=horizon,
        status="validated" if passed else "validation_not_better_than_baseline",
        sample_count=len(usable),
        up_probability=round(probability, 4),
        expected_return_pct=round(float(expected_return), 4),
        validation_metrics={
            "brier": round(brier, 6),
            "baseline_brier": round(baseline_brier, 6),
            "accuracy": round(accuracy, 6),
            "baseline_accuracy": round(baseline_accuracy, 6),
            "feature_count": float(len(FACTOR_COLUMNS)),
        },
        passed_validation=passed,
    )
