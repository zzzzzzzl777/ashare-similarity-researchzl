from __future__ import annotations

from ashare_similarity.prediction.analogue_model import AnaloguePrediction
from ashare_similarity.prediction.ml_model import MLPrediction
from ashare_similarity.schemas import PredictionHorizonResult


def build_horizon_prediction(
    analogue: AnaloguePrediction,
    ml: MLPrediction,
) -> PredictionHorizonResult:
    use_ml = bool(ml.passed_validation and ml.up_probability is not None and ml.expected_return_pct is not None)
    weights = {"analogue": 0.6, "ml": 0.4} if use_ml else {"analogue": 1.0, "ml": 0.0}
    up_probability = _blend(analogue.up_probability, ml.up_probability, weights)
    expected_return = _blend(analogue.expected_return_pct, ml.expected_return_pct, weights)
    confidence, reasons = _confidence(analogue.sample_count, use_ml, up_probability)
    selected_model = "ensemble" if use_ml else "analogue"
    if analogue.sample_count < 20:
        selected_model = "insufficient_evidence"

    return PredictionHorizonResult(
        horizon=analogue.horizon,
        up_probability=up_probability,
        expected_return_pct=expected_return,
        return_quantiles_pct=analogue.quantiles_pct,
        max_drawdown_risk_pct=analogue.max_drawdown_risk_pct,
        kline_scenarios=analogue.scenarios,
        confidence=confidence,
        confidence_reasons=reasons,
        sample_count=analogue.sample_count,
        selected_model=selected_model,
        model_weights=weights,
        analogue_up_probability=analogue.up_probability,
        ml_up_probability=ml.up_probability,
    )


def _blend(analogue_value: float | None, ml_value: float | None, weights: dict[str, float]) -> float | None:
    if analogue_value is None and ml_value is None:
        return None
    if weights["ml"] <= 0 or ml_value is None:
        return round(float(analogue_value), 4) if analogue_value is not None else None
    if analogue_value is None:
        return round(float(ml_value), 4)
    return round(float(analogue_value) * weights["analogue"] + float(ml_value) * weights["ml"], 4)


def _confidence(sample_count: int, use_ml: bool, probability: float | None) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if sample_count < 20:
        return "不足样本", [f"可用历史样本仅 {sample_count} 条，低于最低解释门槛。"]
    if sample_count < 60:
        reasons.append(f"可用历史样本 {sample_count} 条，样本量偏低。")
        return "低", reasons
    if not use_ml:
        reasons.append("监督学习对照未通过或样本不足，当前仅使用相似历史样本。")
    if probability is not None and 0.45 <= probability <= 0.55:
        reasons.append("上涨概率接近 50%，方向优势不明显。")
        return "低", reasons
    if use_ml and sample_count >= 100:
        reasons.append("相似样本充足且 ML 对照通过 walk-forward 验证。")
        return "高", reasons
    reasons.append("相似样本充足，但模型仍应作为研究信号使用。")
    return "中", reasons
