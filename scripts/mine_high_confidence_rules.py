from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

from ashare_similarity.prediction.rule_miner import mine_high_confidence_rules
from ashare_similarity.prediction.split_protocol import SplitProtocolConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Mine validation-selected high-confidence factor rules.")
    parser.add_argument("--input", required=True, help="Feature parquet produced by gpu-prediction-probe.")
    parser.add_argument("--output", required=True, help="JSON report path.")
    parser.add_argument("--train-end", default="2025-12-31")
    parser.add_argument("--test-start", default="2026-01-01")
    parser.add_argument("--end", default="2026-04-29")
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--embargo-trading-days", type=int, default=1)
    parser.add_argument("--max-fit-rows", type=int, default=300_000)
    parser.add_argument("--max-rules", type=int, default=60)
    parser.add_argument("--max-univariate-candidates", type=int, default=180)
    parser.add_argument("--max-conditions", type=int, default=2)
    parser.add_argument("--features", nargs="*", help="Optional explicit feature names to scan.")
    parser.add_argument("--features-from-gpu-probe", help="Read selected feature names from a gpu-prediction-probe JSON artifact.")
    parser.add_argument("--min-fit-rows", type=int, default=800)
    parser.add_argument("--min-validation-rows", type=int, default=300)
    parser.add_argument("--min-fit-accuracy", type=float, default=0.55)
    parser.add_argument("--min-validation-accuracy", type=float, default=0.62)
    parser.add_argument("--min-fit-dates", type=int, default=2)
    parser.add_argument("--min-validation-dates", type=int, default=2)
    args = parser.parse_args()

    frame = pd.read_parquet(args.input)
    feature_names = _load_feature_names(args.features, args.features_from_gpu_probe)
    report = mine_high_confidence_rules(
        frame,
        SplitProtocolConfig(
            train_end=_parse_date(args.train_end),
            test_start=_parse_date(args.test_start),
            end=_parse_date(args.end),
            validation_fraction=float(args.validation_fraction),
            embargo_trading_days=int(args.embargo_trading_days),
            max_fit_rows=int(args.max_fit_rows),
            seed=42,
            allow_row_split_fallback=False,
        ),
        feature_names=feature_names,
        max_rules=int(args.max_rules),
        max_univariate_candidates=int(args.max_univariate_candidates),
        max_conditions=int(args.max_conditions),
        min_fit_rows=int(args.min_fit_rows),
        min_validation_rows=int(args.min_validation_rows),
        min_fit_accuracy=float(args.min_fit_accuracy),
        min_validation_accuracy=float(args.min_validation_accuracy),
        min_fit_dates=int(args.min_fit_dates),
        min_validation_dates=int(args.min_validation_dates),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(_summary(report), ensure_ascii=False, indent=2))


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _load_feature_names(features: list[str] | None, artifact_path: str | None) -> list[str] | None:
    names = list(features or [])
    if artifact_path:
        artifact = json.loads(_read_text(Path(artifact_path)))
        payload = artifact.get("feature_selection") or {}
        names.extend(str(name) for name in payload.get("selected_features") or [])
        names.extend(str(name) for name in payload.get("top_features") or [])
    names = [name for name in dict.fromkeys(names) if name]
    return names or None


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    return path.read_text()


def _summary(report: dict) -> dict:
    rules = report.get("rules") or []
    top = rules[0] if rules else {}
    return {
        "candidate_count": report.get("candidate_count"),
        "rule_count": len(rules),
        "top_rule": top,
    }


if __name__ == "__main__":
    main()
