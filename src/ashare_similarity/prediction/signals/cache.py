from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ashare_similarity.prediction.signals.artifacts import (
    CandidateArtifact,
    hash_selected_features,
    hash_selector_config,
    load_candidate_artifact,
    load_frozen_candidates,
)
from ashare_similarity.prediction.signals.config import SignalConfig
from ashare_similarity.prediction.signals.metrics import (
    assign_split_layer,
    baseline_brier,
    brier_score,
    coverage,
    wilson_lower_95,
)
from ashare_similarity.prediction.signals.selectors import (
    apply_candidate_agreement,
    apply_regime_probability_gate,
)

logger = logging.getLogger(__name__)


def _check_dependencies() -> None:
    missing: list[str] = []
    try:
        import torch  # noqa: F401
    except ImportError:
        missing.append("torch")
    try:
        import xgboost  # noqa: F401
    except ImportError:
        missing.append("xgboost")
    try:
        import lightgbm  # noqa: F401
    except ImportError:
        missing.append("lightgbm")
    try:
        import catboost  # noqa: F401
    except ImportError:
        missing.append("catboost")
    if missing:
        raise RuntimeError(f"build-signals requires: {', '.join(missing)}. Cannot proceed.")


def _check_cuda():
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available. build-signals requires GPU.")
    device = torch.device("cuda")
    logger.info("Using device: %s (%s)", device, torch.cuda.get_device_name(0))
    return device


def build_signal_cache(
    signal_config: SignalConfig,
    *,
    frozen_candidates_path: Path | None = None,
    force_rebuild: bool = False,
) -> dict[str, Any]:
    _check_dependencies()
    device = _check_cuda()

    if frozen_candidates_path is not None:
        signal_config = SignalConfig(
            cache_root=signal_config.cache_root,
            report_dir=signal_config.report_dir,
            frozen_candidates_path=frozen_candidates_path,
            artifact_base_dir=signal_config.artifact_base_dir,
        )

    frozen_candidates = load_frozen_candidates(signal_config)
    build_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + hashlib.md5(
        json.dumps([c["run_id"] for c in frozen_candidates]).encode()
    ).hexdigest()[:8]

    build_dir = signal_config.cache_root / build_id
    if not force_rebuild and (build_dir / "signal_cache.parquet").exists():
        logger.info("Cache already exists at %s, skipping", build_id)
        return {"status": "already_exists", "build_id": build_id}

    build_dir.mkdir(parents=True, exist_ok=True)

    all_frames: list[pd.DataFrame] = []
    candidate_manifests: list[dict[str, Any]] = []

    for frozen_entry in frozen_candidates:
        artifact = load_candidate_artifact(signal_config, frozen_entry)
        logger.info("Processing candidate: %s (run_id=%s, family=%s)", artifact.tag, artifact.run_id, artifact.candidate_family)

        frame, manifest_entry = _process_candidate(artifact, device=device)
        all_frames.append(frame)
        candidate_manifests.append(manifest_entry)

    combined = pd.concat(all_frames, ignore_index=True)
    combined.to_parquet(build_dir / "signal_cache.parquet", index=False, engine="pyarrow")
    logger.info("Signal cache written: %d rows", len(combined))

    dates = sorted(combined["date"].unique())
    symbols = combined["symbol"].unique()
    manifest = {
        "schema_version": 1,
        "build_id": build_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "build_status": "ok",
        "frozen_candidates_source": signal_config.frozen_candidates_path.name,
        "row_count": len(combined),
        "date_count": len(dates),
        "symbol_count": len(symbols),
        "test_date_range": [str(dates[0])[:10], str(dates[-1])[:10]] if len(dates) else [],
        "train_date_range": [
            candidate_manifests[0].get("train_date_range", ["", ""])[0],
            candidate_manifests[0].get("train_date_range", ["", ""])[1],
        ] if candidate_manifests else [],
        "research_only": True,
        "final_acceptance_status": False,
        "candidates": candidate_manifests,
    }
    with open(build_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

    current = {"build_id": build_id}
    signal_config.cache_root.mkdir(parents=True, exist_ok=True)
    with open(signal_config.cache_root / "current.json", "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)

    logger.info("Build complete: %s", build_id)
    _validate_metrics(candidate_manifests)
    return {"status": "ok", "build_id": build_id, "cache_root": str(signal_config.cache_root)}


def _process_candidate(artifact: CandidateArtifact, *, device: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
    import torch

    t0 = time.time()
    logger.info("[%s] Loading feature cache: %s", artifact.tag, artifact.feature_cache_fingerprint)
    fc_path = artifact.feature_cache_path
    if not fc_path.exists():
        raise FileNotFoundError(f"Feature cache not found: {fc_path}")
    data = pd.read_parquet(fc_path)
    logger.info("[%s] Feature cache loaded: %d rows, %d columns", artifact.tag, len(data), len(data.columns))

    train_end = pd.Timestamp(artifact.train_end)
    test_start = pd.Timestamp(artifact.test_start)
    end_date = pd.Timestamp(artifact.end)

    if "label_date" in data.columns:
        train = data[data["label_date"] <= train_end].copy()
        test = data[(data["date"] >= test_start) & (data["label_date"] <= end_date)].copy()
    else:
        train = data[data["date"] <= train_end].copy()
        test = data[(data["date"] >= test_start) & (data["date"] <= end_date)].copy()

    logger.info("[%s] Split: train=%d, test=%d", artifact.tag, len(train), len(test))

    effective_test_rows = artifact.test_rows
    if len(test) > effective_test_rows:
        random_state = artifact.seed + 2
        test = test.sample(n=effective_test_rows, random_state=random_state).sort_values("date")
        logger.info("[%s] Sampled test to %d rows (random_state=%d)", artifact.tag, len(test), random_state)

    selected_features = artifact.selected_features
    available_features = [f for f in selected_features if f in data.columns]
    if len(available_features) < len(selected_features):
        missing = set(selected_features) - set(available_features)
        raise RuntimeError(
            f"[{artifact.tag}] Feature cache is missing {len(missing)} features from artifact: "
            f"{sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}"
        )
    feature_names = tuple(available_features)

    torch.manual_seed(artifact.seed)
    x_train_raw = torch.as_tensor(train[list(feature_names)].to_numpy(dtype=np.float32), device=device)
    x_test_raw = torch.as_tensor(test[list(feature_names)].to_numpy(dtype=np.float32), device=device)
    y_train = torch.as_tensor(train["actual"].to_numpy(dtype=np.float32), device=device).view(-1, 1)
    y_test = torch.as_tensor(test["actual"].to_numpy(dtype=np.float32), device=device).view(-1, 1)

    mean = x_train_raw.mean(dim=0, keepdim=True)
    std = torch.clamp(x_train_raw.std(dim=0, keepdim=True), min=1e-6)
    x_train = (x_train_raw - mean) / std
    x_test = (x_test_raw - mean) / std

    train_return_abs = torch.zeros(len(x_train), 1, device=device)
    if "next_return_pct" in train.columns:
        train_return_abs = torch.as_tensor(
            np.abs(train["next_return_pct"].to_numpy(dtype=np.float32)), device=device
        ).view(-1, 1)

    from ashare_similarity.prediction.gpu_probe import (
        _purged_train_validation_split,
    )

    fit_frame, valid_frame, _ = _purged_train_validation_split(
        train,
        validation_fraction=0.20,
        embargo_label_days=1,
        max_fit_rows=300_000,
        seed=artifact.seed,
    )

    x_fit = torch.as_tensor(fit_frame[list(feature_names)].to_numpy(dtype=np.float32), device=device)
    y_fit = torch.as_tensor(fit_frame["actual"].to_numpy(dtype=np.float32), device=device).view(-1, 1)
    x_valid = torch.as_tensor(valid_frame[list(feature_names)].to_numpy(dtype=np.float32), device=device)
    y_valid = torch.as_tensor(valid_frame["actual"].to_numpy(dtype=np.float32), device=device).view(-1, 1)

    fit_mean = x_fit.mean(dim=0, keepdim=True)
    fit_std = torch.clamp(x_fit.std(dim=0, keepdim=True), min=1e-6)
    x_fit = (x_fit - fit_mean) / fit_std
    x_valid = (x_valid - fit_mean) / fit_std
    x_test_std = (x_test_raw - fit_mean) / fit_std

    fit_return_abs = torch.zeros(len(x_fit), 1, device=device)
    if "next_return_pct" in fit_frame.columns:
        fit_return_abs = torch.as_tensor(
            np.abs(fit_frame["next_return_pct"].to_numpy(dtype=np.float32)), device=device
        ).view(-1, 1)

    pos_rate = torch.clamp(y_fit.mean(), min=1e-4, max=1.0 - 1e-4)
    pos_weight = (1.0 - pos_rate) / pos_rate
    sample_weight = 1.0 + torch.clamp(fit_return_abs, max=5.0) / 5.0

    trained_candidates = _train_all_models(
        x_fit, y_fit, x_valid, y_valid,
        pos_weight=pos_weight,
        sample_weight=sample_weight,
        device=device,
        seed=artifact.seed,
        epochs=160,
        candidate_family=artifact.candidate_family,
        target_accuracy=0.75,
    )

    best_model_name = artifact.best_model
    best_candidate = None
    for c in trained_candidates:
        if c["model_name"] == best_model_name:
            best_candidate = c
            break
    if best_candidate is None:
        trained_names = [c["model_name"] for c in trained_candidates]
        raise RuntimeError(
            f"[{artifact.tag}] Frozen best_model '{best_model_name}' not found among trained candidates: {trained_names}"
        )

    from ashare_similarity.prediction.gpu_probe import (
        _apply_logit_calibration,
        _predict_xgboost_prob,
        _predict_average_ensemble_prob,
        _fit_logit_calibration,
        _fit_isotonic_calibration,
        _apply_isotonic_calibration,
        _brier,
    )

    with torch.no_grad():
        best_test_prob = _get_candidate_test_prob(best_candidate, x_test_std, device=device)
        best_valid_prob = _get_candidate_test_prob(best_candidate, x_valid, device=device)

    iso_model = _fit_isotonic_calibration(best_valid_prob, y_valid.flatten())
    if iso_model is not None:
        iso_valid = _apply_isotonic_calibration(best_valid_prob, iso_model, device=device)
        iso_test = _apply_isotonic_calibration(best_test_prob, iso_model, device=device)
        if _brier(iso_valid, y_valid.flatten()) < _brier(best_valid_prob, y_valid.flatten()):
            best_valid_prob = iso_valid
            best_test_prob = iso_test

    test_prob_np = best_test_prob.detach().cpu().numpy()
    y_test_np = y_test.flatten().detach().cpu().numpy()

    if artifact.selector_method == "candidate_agreement":
        model_preds = {}
        member_models = artifact.selector_params.get("models", [])
        artifact_thresholds = artifact.selector_params.get("model_thresholds", {})
        model_thresholds: dict[str, float] = {}
        trained_names = {c["model_name"] for c in trained_candidates}
        missing_members = [m for m in member_models if m not in trained_names]
        if missing_members:
            raise RuntimeError(
                f"[{artifact.tag}] candidate_agreement requires all {len(member_models)} members, "
                f"but these were not trained: {missing_members}"
            )
        for c in trained_candidates:
            if c["model_name"] in member_models:
                if c["model_name"] in artifact_thresholds:
                    model_thresholds[c["model_name"]] = artifact_thresholds[c["model_name"]]
                else:
                    raise RuntimeError(
                        f"[{artifact.tag}] No artifact threshold for member '{c['model_name']}'; "
                        f"refusing to fall back to retrained threshold"
                    )
                with torch.no_grad():
                    p = _get_candidate_test_prob(c, x_test_std, device=device)
                    model_preds[c["model_name"]] = p.detach().cpu().numpy()

        confident_mask = apply_candidate_agreement(
            model_preds,
            test_prob_np,
            member_models=member_models,
            model_thresholds=model_thresholds,
            best_model_threshold=artifact.classification_threshold,
            agreement_threshold=artifact.selector_params["agreement_threshold"],
            margin_threshold=artifact.selector_params["margin_threshold"],
            side_match_required=artifact.selector_params["side_match_required"],
        )
    elif artifact.selector_method == "regime_probability_gate":
        regime_feature = artifact.selector_params["feature"]
        if regime_feature not in feature_names:
            raise RuntimeError(
                f"[{artifact.tag}] Regime selector feature '{regime_feature}' not found in feature_names; "
                f"artifact and feature cache are inconsistent"
            )
        feat_idx = list(feature_names).index(regime_feature)
        feat_std_values = x_test_std[:, feat_idx].detach().cpu().numpy()

        confident_mask = apply_regime_probability_gate(
            feat_std_values,
            test_prob_np,
            feature_side=artifact.selector_params["feature_side"],
            feature_threshold_standardized=artifact.selector_params["feature_threshold_standardized"],
            probability_side=artifact.selector_params["probability_side"],
            probability_margin=artifact.selector_params["probability_margin"],
            classification_threshold=artifact.selector_params.get("classification_threshold", artifact.classification_threshold),
        )
    else:
        logger.warning("[%s] Unknown selector method: %s", artifact.tag, artifact.selector_method)
        confident_mask = np.zeros(len(test_prob_np), dtype=bool)

    dates_str = test["date"].dt.strftime("%Y-%m-%d").values
    decision_threshold = artifact.classification_threshold
    predicted_positive = (test_prob_np >= decision_threshold)
    correct = (predicted_positive == (y_test_np >= 0.5))

    frame = pd.DataFrame({
        "date": pd.to_datetime(dates_str),
        "symbol": test["symbol"].values,
        "model_tag": artifact.tag,
        "best_model": artifact.best_model,
        "selector_method": artifact.selector_method,
        "probability": test_prob_np.astype(np.float32),
        "confident": confident_mask,
        "actual": y_test_np.astype(np.float32),
        "split_layer": [assign_split_layer(d) for d in dates_str],
        "decision_threshold": np.float32(decision_threshold),
        "predicted_positive": predicted_positive,
        "correct": correct,
    })

    conf_count = int(confident_mask.sum())
    conf_correct = int(correct[confident_mask].sum()) if conf_count > 0 else 0
    conf_acc = conf_correct / conf_count if conf_count > 0 else 0.0
    conf_cov = conf_count / len(test_prob_np) if len(test_prob_np) > 0 else 0.0

    train_dates = train["date"].dt.strftime("%Y-%m-%d")
    manifest_entry = {
        "candidate_tag": artifact.tag,
        "run_id": artifact.run_id,
        "feature_cache_fingerprint": artifact.feature_cache_fingerprint,
        "feature_hash": artifact.feature_hash,
        "data_hash": artifact.data_hash,
        "split_hash": artifact.split_hash,
        "code_hash": artifact.code_hash,
        "selected_features_hash": hash_selected_features(artifact.selected_features),
        "selector_method": artifact.selector_method,
        "selector_config_hash": hash_selector_config(artifact.selector_params),
        "selector_models": artifact.selector_params.get("models", []),
        "best_model": artifact.best_model,
        "candidate_family": artifact.candidate_family,
        "model_type": artifact.best_model,
        "seed": artifact.seed,
        "test_rows_sampled": len(test),
        "source_artifact_path": f"prediction/runs/{artifact.run_id}/artifact.json",
        "train_date_range": [str(train_dates.min())[:10], str(train_dates.max())[:10]] if len(train) else [],
        "artifact_reference": {
            "hc_accuracy": artifact.metrics.get("hc_accuracy"),
            "hc_coverage": artifact.metrics.get("hc_coverage"),
            "hc_count": artifact.metrics.get("hc_count"),
            "hc_wilson_lower_95": artifact.metrics.get("hc_wilson_lower_95"),
            "hc_brier": artifact.metrics.get("hc_brier"),
            "baseline_brier": artifact.metrics.get("baseline_brier"),
        },
        "cache_metrics": {
            "confident_count": conf_count,
            "confident_accuracy": round(conf_acc, 6),
            "confident_coverage": round(conf_cov, 6),
            "confident_wilson_lower_95": round(wilson_lower_95(conf_correct, conf_count), 6),
            "confident_brier": round(float(brier_score(y_test_np[confident_mask], test_prob_np[confident_mask])), 6) if conf_count > 0 else 1.0,
            "confident_baseline_brier": round(float(baseline_brier(y_test_np[confident_mask])), 6) if conf_count > 0 else 1.0,
            "all_brier": round(float(brier_score(y_test_np, test_prob_np)), 6),
            "all_baseline_brier": round(float(baseline_brier(y_test_np)), 6),
        },
    }

    elapsed = time.time() - t0
    logger.info(
        "[%s] Done in %.1fs — confident: %d (%.2f%% acc, %.2f%% cov)",
        artifact.tag, elapsed, conf_count, conf_acc * 100, conf_cov * 100,
    )
    return frame, manifest_entry


def _get_candidate_test_prob(candidate: dict[str, Any], x: Any, *, device: Any) -> Any:
    import torch
    from ashare_similarity.prediction.gpu_probe import (
        _apply_logit_calibration,
        _predict_xgboost_prob,
        _predict_average_ensemble_prob,
    )

    model_kind = candidate.get("model_kind", "torch")
    model = candidate.get("model")

    if model_kind == "ensemble_average":
        return _predict_average_ensemble_prob(candidate.get("members", []), x, device=device)
    if model_kind in {"xgboost", "lightgbm", "catboost"}:
        return _predict_xgboost_prob(model, x, device=device)
    model.eval()
    logits = model(x).flatten() if len(x) else torch.empty(0, device=device)
    return _apply_logit_calibration(logits, candidate.get("calibration") or {"scale": 1.0, "bias": 0.0})


def _train_all_models(
    x_train, y_train, x_valid, y_valid,
    *,
    pos_weight,
    sample_weight,
    device: Any,
    seed: int,
    epochs: int,
    candidate_family: str,
    target_accuracy: float,
) -> list[dict[str, Any]]:
    import torch
    from ashare_similarity.prediction.gpu_probe import (
        _TorchLogistic,
        _TorchMlp,
        _TorchResidualMlp,
        _focal_bce_with_logits,
        _fit_logit_calibration,
        _apply_logit_calibration,
        _best_threshold_and_confidence_band,
        _candidate_selection_score,
        _brier,
        _fit_xgboost_candidate,
        _fit_lightgbm_candidate,
        _fit_catboost_candidate,
        _build_average_ensemble_candidate,
        MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS,
        MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE,
    )

    trained: list[dict[str, Any]] = []
    input_dim = x_train.shape[1]

    torch_candidates = [
        ("gpu_logistic", _TorchLogistic(input_dim).to(device), max(epochs, 80), 0.02),
        ("gpu_mlp_64_32", _TorchMlp(input_dim, hidden=(64, 32)).to(device), max(epochs, 120), 0.005),
        ("gpu_mlp_128_64", _TorchMlp(input_dim, hidden=(128, 64)).to(device), max(epochs, 120), 0.003),
        ("gpu_mlp_256_128_64", _TorchMlp(input_dim, hidden=(256, 128, 64)).to(device), max(epochs, 140), 0.0025),
        ("gpu_residual_mlp_128", _TorchResidualMlp(input_dim, hidden=128).to(device), max(epochs, 140), 0.003),
        ("gpu_residual_mlp_256", _TorchResidualMlp(input_dim, hidden=256).to(device), max(epochs, 160), 0.002),
    ]

    if candidate_family in {"all", "torch"}:
        for name, model, model_epochs, lr in torch_candidates:
            optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
            for _ in range(model_epochs):
                model.train()
                optimizer.zero_grad(set_to_none=True)
                logits = model(x_train)
                loss = _focal_bce_with_logits(logits, y_train, pos_weight=pos_weight, sample_weight=sample_weight)
                loss.backward()
                optimizer.step()
            model.eval()
            with torch.no_grad():
                valid_logits = model(x_valid).flatten() if len(x_valid) else torch.empty(0, device=device)
                valid_y = y_valid.flatten() if len(y_valid) else torch.empty(0, device=device)
            calibration = _fit_logit_calibration(valid_logits, valid_y) if len(valid_y) else {"scale": 1.0, "bias": 0.0}
            with torch.no_grad():
                valid_prob = _apply_logit_calibration(valid_logits, calibration)
                threshold, valid_accuracy, band = _best_threshold_and_confidence_band(
                    valid_prob, valid_y,
                    target_accuracy=target_accuracy,
                    min_count=MIN_GPU_PROBE_VALIDATION_CONFIDENT_ROWS,
                    min_coverage=MIN_GPU_PROBE_VALIDATION_CONFIDENT_COVERAGE,
                )
                valid_brier = _brier(valid_prob, valid_y) if len(valid_y) else 1.0
                score = _candidate_selection_score(valid_accuracy, valid_brier, band, target_accuracy=target_accuracy)
                trained.append({
                    "model_name": name,
                    "model": model,
                    "model_kind": "torch",
                    "selection_score": float(score),
                    "validation_accuracy": float(valid_accuracy),
                    "validation_brier": float(valid_brier),
                    "threshold": float(threshold),
                    "confidence_band": band,
                    "calibration": calibration,
                    "validation_prob": valid_prob.detach(),
                })
            logger.info("  Trained %s: score=%.4f acc=%.4f", name, score, valid_accuracy)

    xgboost_variants = (
        ("baseline", {}),
        ("shallow", {"n_estimators": 500, "max_depth": 3, "learning_rate": 0.025, "min_child_weight": 3.0, "subsample": 0.90, "colsample_bytree": 0.75}),
        ("deep", {"n_estimators": 420, "max_depth": 5, "learning_rate": 0.025, "min_child_weight": 1.5, "subsample": 0.80, "colsample_bytree": 0.90}),
    )
    lightgbm_variants = (
        ("baseline", {}),
        ("compact", {"n_estimators": 600, "learning_rate": 0.020, "num_leaves": 15, "min_child_samples": 120, "reg_lambda": 1.5, "colsample_bytree": 0.75}),
        ("wide", {"n_estimators": 380, "learning_rate": 0.030, "num_leaves": 63, "min_child_samples": 55, "reg_lambda": 1.2, "colsample_bytree": 0.90}),
    )
    catboost_variants = (
        ("baseline", {}),
        ("compact", {"iterations": 550, "depth": 4, "learning_rate": 0.030, "l2_leaf_reg": 8.0}),
        ("expressive", {"iterations": 420, "depth": 8, "learning_rate": 0.018, "l2_leaf_reg": 10.0}),
    )

    if candidate_family in {"all", "tree"}:
        for variant, params in xgboost_variants:
            c = _fit_xgboost_candidate(x_train, y_train, x_valid, y_valid, device=device, seed=seed, target_accuracy=target_accuracy, variant=variant, params=params)
            if c and not c.get("warning"):
                trained.append(c)
                logger.info("  Trained gpu_xgboost_hist_%s: score=%.4f", variant if variant != "baseline" else "", c.get("selection_score", 0))

        for variant, params in lightgbm_variants:
            c = _fit_lightgbm_candidate(x_train, y_train, x_valid, y_valid, device=device, seed=seed, target_accuracy=target_accuracy, variant=variant, params=params)
            if c and not c.get("warning"):
                trained.append(c)
                logger.info("  Trained gpu_lightgbm_%s: score=%.4f", variant if variant != "baseline" else "", c.get("selection_score", 0))

        for variant, params in catboost_variants:
            c = _fit_catboost_candidate(x_train, y_train, x_valid, y_valid, device=device, seed=seed, target_accuracy=target_accuracy, variant=variant, params=params)
            if c and not c.get("warning"):
                trained.append(c)
                logger.info("  Trained gpu_catboost_%s: score=%.4f", variant if variant != "baseline" else "", c.get("selection_score", 0))

    ensemble = _build_average_ensemble_candidate(trained, y_valid.flatten(), target_accuracy=target_accuracy)
    if ensemble:
        trained.append(ensemble)
        logger.info("  Built stacking_average_top3: score=%.4f", ensemble.get("selection_score", 0))

    logger.info("  Total candidates trained: %d", len(trained))
    return trained


def _validate_metrics(candidate_manifests: list[dict[str, Any]]) -> None:
    for entry in candidate_manifests:
        tag = entry["candidate_tag"]
        ref = entry.get("artifact_reference", {})
        cache = entry.get("cache_metrics", {})

        ref_count = ref.get("hc_count", 0)
        cache_count = cache.get("confident_count", 0)
        if ref_count and abs(cache_count - ref_count) / ref_count > 0.05:
            logger.warning(
                "[%s] confident_count mismatch: cache=%d vs artifact=%d (%.1f%%)",
                tag, cache_count, ref_count, (cache_count - ref_count) / ref_count * 100,
            )
        else:
            logger.info("[%s] confident_count OK: cache=%d vs artifact=%d", tag, cache_count, ref_count)

        ref_acc = ref.get("hc_accuracy", 0)
        cache_acc = cache.get("confident_accuracy", 0)
        if ref_acc and abs(cache_acc - ref_acc) > 0.02:
            logger.warning(
                "[%s] confident_accuracy mismatch: cache=%.4f vs artifact=%.4f (diff=%.4f)",
                tag, cache_acc, ref_acc, cache_acc - ref_acc,
            )
        else:
            logger.info("[%s] confident_accuracy OK: cache=%.4f vs artifact=%.4f", tag, cache_acc, ref_acc)

        ref_cov = ref.get("hc_coverage", 0)
        cache_cov = cache.get("confident_coverage", 0)
        if ref_cov and abs(cache_cov - ref_cov) > 0.02:
            logger.warning(
                "[%s] confident_coverage mismatch: cache=%.4f vs artifact=%.4f (diff=%.4f)",
                tag, cache_cov, ref_cov, cache_cov - ref_cov,
            )
        else:
            logger.info("[%s] confident_coverage OK: cache=%.4f vs artifact=%.4f", tag, cache_cov, ref_cov)

        ref_brier = ref.get("hc_brier", 0)
        cache_brier = cache.get("confident_brier", 0)
        if ref_brier and abs(cache_brier - ref_brier) > 0.03:
            logger.warning(
                "[%s] confident_brier mismatch: cache=%.4f vs artifact=%.4f (diff=%.4f)",
                tag, cache_brier, ref_brier, cache_brier - ref_brier,
            )
        else:
            logger.info("[%s] confident_brier OK: cache=%.4f vs artifact=%.4f", tag, cache_brier, ref_brier)
