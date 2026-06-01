from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np
import pandas as pd

from ashare_similarity.prediction.acceptance import wilson_lower_bound
from ashare_similarity.prediction.split_protocol import SplitProtocolConfig, build_official_splits


META_COLUMNS = {"symbol", "date", "label_date", "actual", "next_return_pct"}
DEFAULT_QUANTILES: tuple[float, ...] = (
    0.01,
    0.02,
    0.03,
    0.05,
    0.08,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.92,
    0.95,
    0.97,
    0.98,
    0.99,
)


@dataclass(frozen=True, slots=True)
class RuleCondition:
    feature: str
    op: str
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RuleStats:
    rows: int
    correct_count: int
    accuracy: float | None
    positive_rate: float | None
    coverage: float
    wilson_lower_95: float
    date_count: int
    min_date_accuracy: float | None
    mean_date_accuracy: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MinedRule:
    conditions: tuple[RuleCondition, ...]
    prediction: int
    fit: RuleStats
    validation: RuleStats
    test: RuleStats
    selected_by: str = "validation_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "conditions": [condition.to_dict() for condition in self.conditions],
            "prediction": int(self.prediction),
            "fit": self.fit.to_dict(),
            "validation": self.validation.to_dict(),
            "test": self.test.to_dict(),
            "selected_by": self.selected_by,
        }


@dataclass(slots=True)
class _Candidate:
    conditions: tuple[RuleCondition, ...]
    prediction: int
    fit_mask: np.ndarray
    valid_mask: np.ndarray
    test_mask: np.ndarray
    fit: RuleStats
    validation: RuleStats
    test: RuleStats

    def to_rule(self) -> MinedRule:
        return MinedRule(
            conditions=self.conditions,
            prediction=self.prediction,
            fit=self.fit,
            validation=self.validation,
            test=self.test,
        )


def condition_mask(frame: pd.DataFrame, condition: RuleCondition) -> pd.Series:
    if condition.feature not in frame.columns:
        return pd.Series(False, index=frame.index)
    values = pd.to_numeric(frame[condition.feature], errors="coerce").replace([np.inf, -np.inf], np.nan)
    if condition.op == ">=":
        return values >= float(condition.threshold)
    if condition.op == "<=":
        return values <= float(condition.threshold)
    raise ValueError("RuleCondition.op must be one of: >=, <=")


def evaluate_rule(
    frame: pd.DataFrame,
    conditions: Iterable[RuleCondition],
    *,
    prediction: int,
    mask: np.ndarray | pd.Series | None = None,
) -> RuleStats:
    if mask is None:
        current = pd.Series(True, index=frame.index)
        for condition in conditions:
            current &= condition_mask(frame, condition)
        selected = current.to_numpy(dtype=bool)
    else:
        selected = np.asarray(mask, dtype=bool)

    total_rows = int(len(frame))
    rows = int(selected.sum())
    if rows <= 0 or "actual" not in frame.columns:
        return RuleStats(
            rows=0,
            correct_count=0,
            accuracy=None,
            positive_rate=None,
            coverage=0.0,
            wilson_lower_95=0.0,
            date_count=0,
            min_date_accuracy=None,
            mean_date_accuracy=None,
        )

    actual = pd.to_numeric(frame.loc[selected, "actual"], errors="coerce").fillna(0.0).astype(int)
    positive_rate = float(actual.mean()) if rows else None
    correct = actual.eq(int(prediction))
    correct_count = int(correct.sum())
    accuracy = correct_count / rows if rows else None
    date_count, min_date_accuracy, mean_date_accuracy = _date_accuracy_stats(
        frame.loc[selected],
        prediction=int(prediction),
    )
    return RuleStats(
        rows=rows,
        correct_count=correct_count,
        accuracy=float(accuracy) if accuracy is not None else None,
        positive_rate=positive_rate,
        coverage=rows / total_rows if total_rows > 0 else 0.0,
        wilson_lower_95=wilson_lower_bound(correct_count, rows),
        date_count=date_count,
        min_date_accuracy=min_date_accuracy,
        mean_date_accuracy=mean_date_accuracy,
    )


def mine_high_confidence_rules(
    frame: pd.DataFrame,
    split_config: SplitProtocolConfig,
    *,
    feature_names: Iterable[str] | None = None,
    quantiles: Iterable[float] = DEFAULT_QUANTILES,
    max_rules: int = 50,
    max_univariate_candidates: int = 180,
    max_conditions: int = 2,
    min_fit_rows: int = 500,
    min_validation_rows: int = 200,
    min_fit_accuracy: float = 0.55,
    min_validation_accuracy: float = 0.60,
    min_fit_dates: int = 2,
    min_validation_dates: int = 2,
) -> dict[str, Any]:
    prepared = _prepare_frame(frame)
    fit, valid, test, manifest = build_official_splits(prepared, split_config)
    features = _feature_names(prepared, feature_names)
    univariate = _mine_univariate_candidates(
        fit,
        valid,
        test,
        features,
        quantiles=tuple(float(value) for value in quantiles),
        min_fit_rows=int(min_fit_rows),
        min_validation_rows=int(min_validation_rows),
        min_fit_accuracy=float(min_fit_accuracy),
        min_validation_accuracy=float(min_validation_accuracy),
        min_fit_dates=int(min_fit_dates),
        min_validation_dates=int(min_validation_dates),
    )
    kept_univariate = _keep_diverse_candidates(univariate, limit=int(max_univariate_candidates))
    candidates = list(kept_univariate)
    if int(max_conditions) >= 2:
        candidates.extend(
            _mine_pair_candidates(
                fit,
                valid,
                test,
                kept_univariate,
                min_fit_rows=int(min_fit_rows),
                min_validation_rows=int(min_validation_rows),
                min_fit_accuracy=float(min_fit_accuracy),
                min_validation_accuracy=float(min_validation_accuracy),
                min_fit_dates=int(min_fit_dates),
                min_validation_dates=int(min_validation_dates),
            )
        )
    candidates = sorted(candidates, key=_candidate_sort_key, reverse=True)
    selected = [candidate.to_rule() for candidate in candidates[: max(1, int(max_rules))]]
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "kind": "high_confidence_rule_mining_report",
        "selection_protocol": "fit_proposes_validation_selects_test_reports",
        "split_manifest": manifest.to_dict(),
        "feature_count": len(features),
        "candidate_count": len(candidates),
        "rules": [rule.to_dict() for rule in selected],
    }


def _prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "label_date", "actual"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"rule mining frame missing columns: {missing}")
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["label_date"] = pd.to_datetime(out["label_date"], errors="coerce")
    out["actual"] = pd.to_numeric(out["actual"], errors="coerce")
    out = out.dropna(subset=["date", "label_date", "actual"]).reset_index(drop=True)
    out["actual"] = out["actual"].astype(int)
    return out


def _feature_names(frame: pd.DataFrame, requested: Iterable[str] | None) -> tuple[str, ...]:
    if requested is not None:
        names = [str(name) for name in requested if str(name) in frame.columns and str(name) not in META_COLUMNS]
    else:
        names = [column for column in frame.columns if column not in META_COLUMNS]
    numeric = []
    for column in names:
        if pd.api.types.is_numeric_dtype(frame[column]):
            numeric.append(column)
    return tuple(dict.fromkeys(numeric))


def _mine_univariate_candidates(
    fit: pd.DataFrame,
    valid: pd.DataFrame,
    test: pd.DataFrame,
    features: tuple[str, ...],
    *,
    quantiles: tuple[float, ...],
    min_fit_rows: int,
    min_validation_rows: int,
    min_fit_accuracy: float,
    min_validation_accuracy: float,
    min_fit_dates: int,
    min_validation_dates: int,
) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    fit_actual = fit["actual"].to_numpy(dtype=int)
    valid_actual = valid["actual"].to_numpy(dtype=int)
    for feature in features:
        values = pd.to_numeric(fit[feature], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(values) < min_fit_rows or values.nunique() <= 1:
            continue
        thresholds = np.unique(np.nanquantile(values.to_numpy(dtype=float), quantiles))
        for threshold in thresholds:
            for op in (">=", "<="):
                condition = RuleCondition(feature=feature, op=op, threshold=float(threshold))
                fit_mask = condition_mask(fit, condition).to_numpy(dtype=bool)
                prediction = _prediction_from_mask(fit, fit_mask)
                if prediction is None:
                    continue
                if not _passes_basic_mask_filters(
                    actual=fit_actual,
                    mask=fit_mask,
                    prediction=prediction,
                    min_rows=min_fit_rows,
                    min_accuracy=min_fit_accuracy,
                ):
                    continue
                valid_mask = condition_mask(valid, condition).to_numpy(dtype=bool)
                if not _passes_basic_mask_filters(
                    actual=valid_actual,
                    mask=valid_mask,
                    prediction=prediction,
                    min_rows=min_validation_rows,
                    min_accuracy=min_validation_accuracy,
                ):
                    continue
                test_mask = condition_mask(test, condition).to_numpy(dtype=bool)
                candidate = _build_candidate(
                    fit,
                    valid,
                    test,
                    conditions=(condition,),
                    prediction=prediction,
                    fit_mask=fit_mask,
                    valid_mask=valid_mask,
                    test_mask=test_mask,
                )
                if _passes_candidate_filters(
                    candidate,
                    min_fit_rows=min_fit_rows,
                    min_validation_rows=min_validation_rows,
                    min_fit_accuracy=min_fit_accuracy,
                    min_validation_accuracy=min_validation_accuracy,
                    min_fit_dates=min_fit_dates,
                    min_validation_dates=min_validation_dates,
                ):
                    candidates.append(candidate)
    return candidates


def _mine_pair_candidates(
    fit: pd.DataFrame,
    valid: pd.DataFrame,
    test: pd.DataFrame,
    univariate: list[_Candidate],
    *,
    min_fit_rows: int,
    min_validation_rows: int,
    min_fit_accuracy: float,
    min_validation_accuracy: float,
    min_fit_dates: int,
    min_validation_dates: int,
) -> list[_Candidate]:
    pairs: list[_Candidate] = []
    fit_actual = fit["actual"].to_numpy(dtype=int)
    valid_actual = valid["actual"].to_numpy(dtype=int)
    for left_index, left in enumerate(univariate):
        for right in univariate[left_index + 1 :]:
            if left.conditions[0].feature == right.conditions[0].feature:
                continue
            fit_mask = left.fit_mask & right.fit_mask
            prediction = _prediction_from_mask(fit, fit_mask)
            if prediction is None:
                continue
            if not _passes_basic_mask_filters(
                actual=fit_actual,
                mask=fit_mask,
                prediction=prediction,
                min_rows=min_fit_rows,
                min_accuracy=min_fit_accuracy,
            ):
                continue
            valid_mask = left.valid_mask & right.valid_mask
            if not _passes_basic_mask_filters(
                actual=valid_actual,
                mask=valid_mask,
                prediction=prediction,
                min_rows=min_validation_rows,
                min_accuracy=min_validation_accuracy,
            ):
                continue
            test_mask = left.test_mask & right.test_mask
            candidate = _build_candidate(
                fit,
                valid,
                test,
                conditions=(*left.conditions, *right.conditions),
                prediction=prediction,
                fit_mask=fit_mask,
                valid_mask=valid_mask,
                test_mask=test_mask,
            )
            if _passes_candidate_filters(
                candidate,
                min_fit_rows=min_fit_rows,
                min_validation_rows=min_validation_rows,
                min_fit_accuracy=min_fit_accuracy,
                min_validation_accuracy=min_validation_accuracy,
                min_fit_dates=min_fit_dates,
                min_validation_dates=min_validation_dates,
            ):
                pairs.append(candidate)
    return pairs


def _build_candidate(
    fit: pd.DataFrame,
    valid: pd.DataFrame,
    test: pd.DataFrame,
    *,
    conditions: tuple[RuleCondition, ...],
    prediction: int,
    fit_mask: np.ndarray,
    valid_mask: np.ndarray,
    test_mask: np.ndarray,
) -> _Candidate:
    return _Candidate(
        conditions=conditions,
        prediction=int(prediction),
        fit_mask=fit_mask,
        valid_mask=valid_mask,
        test_mask=test_mask,
        fit=evaluate_rule(fit, conditions, prediction=int(prediction), mask=fit_mask),
        validation=evaluate_rule(valid, conditions, prediction=int(prediction), mask=valid_mask),
        test=evaluate_rule(test, conditions, prediction=int(prediction), mask=test_mask),
    )


def _prediction_from_mask(frame: pd.DataFrame, mask: np.ndarray) -> int | None:
    selected = np.asarray(mask, dtype=bool)
    if selected.sum() <= 0:
        return None
    positive_rate = float(pd.to_numeric(frame.loc[selected, "actual"], errors="coerce").fillna(0.0).mean())
    return 1 if positive_rate >= 0.5 else 0


def _passes_candidate_filters(
    candidate: _Candidate,
    *,
    min_fit_rows: int,
    min_validation_rows: int,
    min_fit_accuracy: float,
    min_validation_accuracy: float,
    min_fit_dates: int,
    min_validation_dates: int,
) -> bool:
    fit_accuracy = candidate.fit.accuracy or 0.0
    valid_accuracy = candidate.validation.accuracy or 0.0
    return bool(
        candidate.fit.rows >= min_fit_rows
        and candidate.validation.rows >= min_validation_rows
        and fit_accuracy >= min_fit_accuracy
        and valid_accuracy >= min_validation_accuracy
        and candidate.fit.date_count >= min_fit_dates
        and candidate.validation.date_count >= min_validation_dates
    )


def _passes_basic_mask_filters(
    *,
    actual: np.ndarray,
    mask: np.ndarray,
    prediction: int,
    min_rows: int,
    min_accuracy: float,
) -> bool:
    selected = np.asarray(mask, dtype=bool)
    rows = int(selected.sum())
    if rows < int(min_rows):
        return False
    correct = int((actual[selected] == int(prediction)).sum())
    return (correct / rows) >= float(min_accuracy)


def _keep_diverse_candidates(candidates: list[_Candidate], *, limit: int) -> list[_Candidate]:
    sorted_candidates = sorted(candidates, key=_candidate_sort_key, reverse=True)
    kept: list[_Candidate] = []
    per_key: dict[tuple[str, str, int], int] = {}
    for candidate in sorted_candidates:
        condition = candidate.conditions[0]
        key = (condition.feature, condition.op, int(candidate.prediction))
        if per_key.get(key, 0) >= 3:
            continue
        kept.append(candidate)
        per_key[key] = per_key.get(key, 0) + 1
        if len(kept) >= max(1, int(limit)):
            break
    return kept


def _candidate_sort_key(candidate: _Candidate) -> tuple[float, float, float, float, int]:
    validation_accuracy = candidate.validation.accuracy or 0.0
    validation_mean_date = candidate.validation.mean_date_accuracy or 0.0
    return (
        candidate.validation.wilson_lower_95,
        validation_mean_date,
        validation_accuracy,
        candidate.validation.coverage,
        candidate.validation.rows,
    )


def _date_accuracy_stats(frame: pd.DataFrame, *, prediction: int) -> tuple[int, float | None, float | None]:
    if frame.empty or "date" not in frame.columns:
        return 0, None, None
    accuracies: list[float] = []
    for _, group in frame.groupby(frame["date"].dt.normalize(), sort=False):
        actual = pd.to_numeric(group["actual"], errors="coerce").fillna(0.0).astype(int)
        if len(actual) == 0:
            continue
        accuracies.append(float(actual.eq(int(prediction)).mean()))
    if not accuracies:
        return 0, None, None
    return len(accuracies), float(min(accuracies)), float(np.mean(accuracies))
