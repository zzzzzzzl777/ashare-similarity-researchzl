from __future__ import annotations

from typing import Any

import numpy as np


def apply_candidate_agreement(
    model_predictions: dict[str, np.ndarray],
    best_model_pred: np.ndarray,
    *,
    member_models: list[str],
    model_thresholds: dict[str, float],
    best_model_threshold: float,
    agreement_threshold: float,
    margin_threshold: float,
    side_match_required: bool,
) -> np.ndarray:
    n = len(best_model_pred)
    missing_preds = [m for m in member_models if m not in model_predictions]
    if missing_preds:
        raise RuntimeError(
            f"candidate_agreement: missing model predictions for: {missing_preds}"
        )
    missing_thresholds = [m for m in member_models if m not in model_thresholds]
    if missing_thresholds:
        raise RuntimeError(
            f"candidate_agreement: missing thresholds for: {missing_thresholds}"
        )

    best_pred_binary = (best_model_pred >= best_model_threshold).astype(np.float32)

    k = len(member_models)
    vote_pos = np.zeros(n, dtype=np.float32)
    margin_sum = np.zeros(n, dtype=np.float32)
    for model_name in member_models:
        probs = model_predictions[model_name]
        t = model_thresholds[model_name]
        vote_pos += (probs >= t).astype(np.float32)
        margin_sum += np.abs(probs - t)

    vote_frac = vote_pos / k
    agreement = np.maximum(vote_frac, 1.0 - vote_frac)
    margin = margin_sum / k
    majority_pred = (vote_frac >= 0.5).astype(np.float32)
    side_match = majority_pred == best_pred_binary

    mask = (agreement >= agreement_threshold) & (margin >= margin_threshold)
    if side_match_required:
        mask = mask & side_match
    return mask


def apply_regime_probability_gate(
    feature_values_standardized: np.ndarray,
    best_model_prob: np.ndarray,
    *,
    feature_side: str,
    feature_threshold_standardized: float,
    probability_side: str,
    probability_margin: float,
    classification_threshold: float,
) -> np.ndarray:
    threshold = feature_threshold_standardized
    if feature_side == "low":
        feature_mask = feature_values_standardized < threshold
    elif feature_side == "high":
        feature_mask = feature_values_standardized > threshold
    else:
        feature_mask = np.ones(len(feature_values_standardized), dtype=bool)

    low = max(classification_threshold - probability_margin, 0.02)
    high = min(classification_threshold + probability_margin, 0.98)
    if probability_side == "long":
        prob_mask = best_model_prob >= high
    elif probability_side == "short":
        prob_mask = best_model_prob <= low
    elif probability_side == "both":
        prob_mask = (best_model_prob <= low) | (best_model_prob >= high)
    elif probability_side == "all":
        prob_mask = np.ones(len(best_model_prob), dtype=bool)
    else:
        prob_mask = np.ones(len(best_model_prob), dtype=bool)

    return feature_mask & prob_mask
