from __future__ import annotations

import math

import numpy as np


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) == 0:
        return 0.0
    return float((y_true == y_pred).mean())


def confident_accuracy(correct: np.ndarray, confident_mask: np.ndarray) -> float:
    if confident_mask.sum() == 0:
        return 0.0
    return float(correct[confident_mask].mean())


def coverage(confident_mask: np.ndarray, total: int) -> float:
    if total == 0:
        return 0.0
    return float(confident_mask.sum() / total)


def wilson_lower_95(successes: int, total: int) -> float:
    if total == 0:
        return 0.0
    z = 1.96
    p_hat = successes / total
    denominator = 1 + z * z / total
    center = p_hat + z * z / (2 * total)
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * total)) / total)
    return max(0.0, (center - spread) / denominator)


def brier_score(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    if len(y_true) == 0:
        return 1.0
    return float(np.mean((probabilities - y_true) ** 2))


def baseline_brier(y_true: np.ndarray) -> float:
    if len(y_true) == 0:
        return 1.0
    p = float(y_true.mean())
    return float(np.mean((p - y_true) ** 2))


def assign_split_layer(date_str: str) -> str:
    if date_str < "2026-01-01":
        return "dev_valid"
    return "seen_research"
