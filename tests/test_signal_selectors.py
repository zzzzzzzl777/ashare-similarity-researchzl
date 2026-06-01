from __future__ import annotations

import numpy as np
import pytest

from ashare_similarity.prediction.signals.selectors import (
    apply_candidate_agreement,
    apply_regime_probability_gate,
)


def test_candidate_agreement_basic() -> None:
    n = 100
    np.random.seed(42)
    model_preds = {
        "m1": np.random.uniform(0.3, 0.8, n).astype(np.float32),
        "m2": np.random.uniform(0.3, 0.8, n).astype(np.float32),
        "m3": np.random.uniform(0.3, 0.8, n).astype(np.float32),
    }
    best = model_preds["m1"]
    mask = apply_candidate_agreement(
        model_preds,
        best,
        member_models=["m1", "m2", "m3"],
        model_thresholds={"m1": 0.5, "m2": 0.5, "m3": 0.5},
        best_model_threshold=0.5,
        agreement_threshold=0.6,
        margin_threshold=0.1,
        side_match_required=True,
    )
    assert mask.dtype == bool
    assert mask.shape == (n,)
    assert mask.sum() > 0


def test_candidate_agreement_per_model_threshold() -> None:
    probs_m1 = np.array([0.4, 0.6, 0.3, 0.7, 0.5], dtype=np.float32)
    probs_m2 = np.array([0.55, 0.55, 0.55, 0.55, 0.55], dtype=np.float32)
    model_preds = {"m1": probs_m1, "m2": probs_m2}
    best = probs_m1.copy()

    mask_same = apply_candidate_agreement(
        model_preds, best,
        member_models=["m1", "m2"],
        model_thresholds={"m1": 0.5, "m2": 0.5},
        best_model_threshold=0.5,
        agreement_threshold=0.6, margin_threshold=0.0, side_match_required=False,
    )
    mask_diff = apply_candidate_agreement(
        model_preds, best,
        member_models=["m1", "m2"],
        model_thresholds={"m1": 0.35, "m2": 0.6},
        best_model_threshold=0.35,
        agreement_threshold=0.6, margin_threshold=0.0, side_match_required=False,
    )
    assert not np.array_equal(mask_same, mask_diff)


def test_candidate_agreement_insufficient_models() -> None:
    n = 10
    with pytest.raises(RuntimeError, match="missing model predictions"):
        apply_candidate_agreement(
            {"m1": np.ones(n)},
            np.ones(n),
            member_models=["m1", "m2", "m3"],
            model_thresholds={"m1": 0.5, "m2": 0.5, "m3": 0.5},
            best_model_threshold=0.5,
            agreement_threshold=0.6,
            margin_threshold=0.1,
            side_match_required=True,
        )


def test_candidate_agreement_missing_threshold() -> None:
    n = 10
    preds = {
        "m1": np.ones(n, dtype=np.float32),
        "m2": np.ones(n, dtype=np.float32),
    }
    with pytest.raises(RuntimeError, match="missing thresholds"):
        apply_candidate_agreement(
            preds,
            np.ones(n),
            member_models=["m1", "m2"],
            model_thresholds={"m1": 0.5},
            best_model_threshold=0.5,
            agreement_threshold=0.6,
            margin_threshold=0.1,
            side_match_required=True,
        )


def test_regime_probability_gate_long() -> None:
    feat_z = np.array([-0.5, -0.1, 0.0, 0.3, -0.3], dtype=np.float32)
    probs = np.array([0.80, 0.60, 0.74, 0.90, 0.80], dtype=np.float32)
    mask = apply_regime_probability_gate(
        feat_z, probs,
        feature_side="low",
        feature_threshold_standardized=-0.2,
        probability_side="long",
        probability_margin=0.09,
        classification_threshold=0.64,
    )
    assert mask[0] == True
    assert mask[1] == False
    assert mask[4] == True


def test_regime_probability_gate_uses_classification_threshold() -> None:
    probs = np.array([0.60, 0.70, 0.80], dtype=np.float32)
    feat_z = np.array([-1.0, -1.0, -1.0], dtype=np.float32)

    mask_low_ct = apply_regime_probability_gate(
        feat_z, probs,
        feature_side="low", feature_threshold_standardized=0.0,
        probability_side="long", probability_margin=0.09,
        classification_threshold=0.50,
    )
    mask_high_ct = apply_regime_probability_gate(
        feat_z, probs,
        feature_side="low", feature_threshold_standardized=0.0,
        probability_side="long", probability_margin=0.09,
        classification_threshold=0.64,
    )
    assert mask_low_ct.sum() >= mask_high_ct.sum()


def test_regime_probability_gate_short() -> None:
    feat_z = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    probs = np.array([0.20, 0.50, 0.10], dtype=np.float32)
    mask = apply_regime_probability_gate(
        feat_z, probs,
        feature_side="high",
        feature_threshold_standardized=0.5,
        probability_side="short",
        probability_margin=0.1,
        classification_threshold=0.5,
    )
    assert mask[0] == True
    assert mask[1] == False
    assert mask[2] == True


def test_regime_missing_feature_raises_in_cache() -> None:
    """Verify cache.py raises RuntimeError when regime feature is absent.

    _process_candidate requires GPU, so we test the guard logic directly
    by checking the source enforces the contract.
    """
    import ast, inspect
    from ashare_similarity.prediction.signals import cache as cache_mod

    source = inspect.getsource(cache_mod._process_candidate)
    tree = ast.parse(source)
    found_raise = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.exc is not None:
            if hasattr(node.exc, "args") and node.exc.args:
                for arg in node.exc.args:
                    if isinstance(arg, ast.JoinedStr):
                        for val in arg.values:
                            if isinstance(val, ast.Constant) and "Regime selector feature" in str(val.value):
                                found_raise = True
                    elif isinstance(arg, ast.Constant) and "Regime selector feature" in str(arg.value):
                        found_raise = True
    assert found_raise, (
        "_process_candidate must raise RuntimeError when regime feature is missing from feature_names"
    )
