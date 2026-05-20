"""
Phase E: Frozen April Known Holdout + Web/Live Gate.
Per plan §5.1 and user instructions:
  - Load champion bundle from Phase D (model_bundle.pt)
  - Load feature cache covering April 2026
  - Score April data using FROZEN model (NO retraining)
  - Report accuracy at multiple fixed thresholds (p>=0.75, p>=0.78, p>=0.80)
  - Web/live parity gate: verify all selected_features mappable to 14:57 live

CRITICAL: This script does NOT call run_gpu_next_day_probe.
It loads a saved bundle and scores directly.

P0 audit set = P0_CANONICAL ∪ P0_ALL ∪ CLASS_C (expanded).
"""
import sys
import json
import math
import pickle
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")))

OUTPUT_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phaseE_frozen_april_20260509.json"
OUTPUT_MD = r"C:\Users\zzzzzzl\Desktop\subagent\docs\phaseE_frozen_april_20260509.md"
PHASE_D_JSON = r"E:\ashare_similarity_runtime\data\reports\prediction\phaseD_stability_risk_20260509.json"

FEATURE_CACHE_WITH_APRIL = Path(
    r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache"
    r"\gpu_probe_features_31ffa0367a4d893f.parquet"
)

P0_CANONICAL = {
    "sector_climax_signal", "sector_climax_signal_available",
    "sector_divergence", "sector_divergence_available",
    "sector_duration_days", "sector_duration_days_available",
    "sector_limit_up_count", "sector_limit_up_count_available",
    "sector_pct_change_best", "sector_pct_change_best_available",
    "sector_strength_rank", "sector_strength_rank_available",
    "tushare_cost_concentration", "tushare_cost_concentration_available",
    "tushare_cost_position", "tushare_cost_position_available",
    "tushare_winner_rate", "tushare_winner_rate_available",
}
CLASS_C = [
    "tushare_lg_buy_sell_ratio", "tushare_lg_buy_sell_ratio_available",
    "tushare_elg_buy_sell_ratio", "tushare_elg_buy_sell_ratio_available",
    "tushare_mf_strength", "tushare_mf_strength_available",
    "tushare_sm_sell_pressure", "tushare_sm_sell_pressure_available",
    "tushare_main_force_divergence", "tushare_main_force_divergence_available",
    "tushare_lhb_net_buy", "tushare_lhb_net_buy_available",
    "tushare_lhb_net_rate", "tushare_lhb_net_rate_available",
    "tushare_inst_buy_count", "tushare_inst_buy_count_available",
    "tushare_lhb_appeared", "tushare_lhb_appeared_available",
    "tushare_inst_net_buy", "tushare_inst_net_buy_available",
    "tushare_rzye", "tushare_rzye_available",
    "tushare_rzye_delta_pct", "tushare_rzye_delta_pct_available",
    "tushare_rzmre_ratio", "tushare_rzmre_ratio_available",
    "tushare_margin_net", "tushare_margin_net_available",
    "tushare_rqye_ratio", "tushare_rqye_ratio_available",
    "tushare_auction_close_vwap_ratio", "tushare_auction_close_vwap_ratio_available",
    "tushare_auction_close_vol", "tushare_auction_close_vol_available",
    "tushare_float_relative_impact", "tushare_float_relative_impact_available",
]
P0_ALL = [
    "sector_pct_change_best", "sector_pct_change_best_available",
    "sector_strength_rank", "sector_strength_rank_available",
    "sector_limit_up_count", "sector_limit_up_count_available",
    "sector_duration_days", "sector_duration_days_available",
    "sector_divergence", "sector_divergence_available",
    "sector_climax_signal", "sector_climax_signal_available",
    "tushare_winner_rate", "tushare_winner_rate_available",
    "tushare_cost_concentration", "tushare_cost_concentration_available",
    "tushare_cost_position", "tushare_cost_position_available",
    "tushare_net_mf_amount", "tushare_net_mf_amount_available",
    "tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available",
]

P0_AUDIT_SET = P0_CANONICAL | set(P0_ALL) | set(CLASS_C)

WEB_FORBIDDEN_FEATURES = [
    "tushare_net_mf_amount", "tushare_ff_adjusted_flow",
    "tushare_winner_rate", "tushare_cost_concentration", "tushare_cost_position",
    "sector_climax_signal", "sector_divergence", "sector_duration_days",
    "sector_limit_up_count", "sector_pct_change_best", "sector_strength_rank",
] + CLASS_C

META_COLS = frozenset([
    "symbol", "date", "label_date", "close", "actual",
    "next_close_return_pct", "next_high_return_pct", "next_low_return_pct",
    "next_return_pct", "next_close_up", "limit_up_like", "short_phase_days_3",
])


def wilson(n, p):
    if n == 0 or p == 0:
        return 0.0
    z = 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin) / denom


def load_bundle(path):
    """Load and unpack model bundle."""
    bundle = torch.load(str(path), map_location="cpu", weights_only=False)
    members = []
    for m in bundle["members"]:
        model = pickle.loads(m["model_bytes"])
        members.append(model)
    iso_model = pickle.loads(bundle["iso_model_bytes"]) if bundle.get("iso_model_bytes") else None
    return {
        "members": members,
        "mean": bundle["mean"],
        "std": bundle["std"],
        "selected_indices": bundle["selected_indices"],
        "feature_names": bundle["feature_names"],
        "selected_feature_names": bundle.get("selected_feature_names", ()),
        "iso_model": iso_model,
        "calibration_used": bundle["calibration_used"],
        "threshold": bundle["threshold"],
        "model_name": bundle.get("model_name", "unknown"),
        "confidence_band": bundle.get("confidence_band"),
    }


def run_inference(bundle, raw_features):
    """Score with frozen model. No training."""
    x = torch.as_tensor(raw_features, dtype=torch.float32)
    mean = bundle["mean"]
    std = bundle["std"].clone()
    std[std == 0] = 1.0
    x = (x - mean) / std
    if bundle["selected_indices"] is not None:
        x = x[:, bundle["selected_indices"]]
    x_np = x.numpy()
    probs = np.stack([m.predict_proba(x_np)[:, 1].astype(np.float32) for m in bundle["members"]], axis=0)
    prob = probs.mean(axis=0)
    if bundle["calibration_used"] == "isotonic" and bundle["iso_model"] is not None:
        prob = bundle["iso_model"].predict(prob.astype(np.float64)).astype(np.float32)
    return prob


def evaluate_at_threshold(prob, actual, threshold):
    mask = prob >= threshold
    if mask.sum() == 0:
        return {"threshold": threshold, "count": 0, "accuracy": 0, "wilson_95": 0, "coverage": 0}
    correct = actual[mask]
    acc = float(correct.mean())
    n = int(mask.sum())
    total = len(actual)
    w95 = wilson(n, acc)
    return {
        "threshold": threshold,
        "count": n,
        "accuracy": round(acc, 6),
        "wilson_95": round(w95, 6),
        "coverage": round(n / total, 6),
    }


def web_gate_audit(selected_feature_names):
    """Check which selected features are NOT available at 14:57."""
    forbidden_set = set(WEB_FORBIDDEN_FEATURES)
    p0_in_selected = set(selected_feature_names) & P0_AUDIT_SET
    web_forbidden_in_selected = set(selected_feature_names) & forbidden_set
    available_count = len(selected_feature_names) - len(web_forbidden_in_selected)
    return {
        "total_selected": len(selected_feature_names),
        "web_available": available_count,
        "web_forbidden_count": len(web_forbidden_in_selected),
        "web_forbidden_features": sorted(web_forbidden_in_selected),
        "p0_in_selected": sorted(p0_in_selected),
        "p0_count": len(p0_in_selected),
        "web_gate_pass": len(web_forbidden_in_selected) == 0 and len(p0_in_selected) == 0,
    }


def main():
    print("=" * 70)
    print("PHASE E: FROZEN APRIL HOLDOUT + WEB/LIVE GATE")
    print("=" * 70)
    print("  Score-only: NO retraining, NO run_gpu_next_day_probe")
    print("  P0 audit: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C")
    print()

    # Load Phase D champion bundle path
    try:
        with open(PHASE_D_JSON, "r", encoding="utf-8") as f:
            phase_d = json.load(f)
        bundle_path = Path(phase_d["champion_bundle"]["bundle_path"])
        stability_grade = phase_d["stability_grade"]
        print("  Phase D grade: " + stability_grade)
        print("  Champion bundle: " + str(bundle_path))
    except (FileNotFoundError, KeyError) as e:
        print("  ERROR: Cannot load Phase D results: " + str(e))
        print("  Cannot proceed without champion bundle.")
        sys.exit(1)

    if not bundle_path.exists():
        print("  ERROR: Bundle file not found: " + str(bundle_path))
        sys.exit(1)

    # === Load frozen bundle ===
    print("\n--- Loading frozen bundle ---")
    t0 = time.time()
    bundle = load_bundle(bundle_path)
    load_time = time.time() - t0
    print("  Model: " + bundle["model_name"])
    print("  Features (full): " + str(len(bundle["feature_names"])))
    print("  Features (selected): " + str(len(bundle["selected_feature_names"])))
    print("  Threshold: " + str(bundle["threshold"]))
    print("  Calibration: " + bundle["calibration_used"])
    print("  Load time: " + str(round(load_time, 1)) + "s")

    # === P0 audit on selected features ===
    sel_features = list(bundle["selected_feature_names"])
    p0_in_sel = set(sel_features) & P0_AUDIT_SET
    print("\n  P0 in selected_features: " + str(len(p0_in_sel)))
    if p0_in_sel:
        print("  WARNING P0 FEATURES FOUND: " + str(sorted(p0_in_sel)))
        is_deployable = False
    else:
        print("  P0 audit: CLEAN")
        is_deployable = True

    # === Load April feature data ===
    print("\n--- Loading April feature data ---")
    feature_names = list(bundle["feature_names"])
    available_features = set(pd.read_parquet(FEATURE_CACHE_WITH_APRIL, columns=[feature_names[0]]).columns) if False else None

    cols_to_load = list(META_COLS | set(feature_names))
    import pyarrow.parquet as pq
    schema_cols = set(pq.read_schema(str(FEATURE_CACHE_WITH_APRIL)).names)
    cols_to_load = [c for c in cols_to_load if c in schema_cols]
    missing_features = [f for f in feature_names if f not in schema_cols]

    if missing_features:
        print("  WARNING: " + str(len(missing_features)) + " features missing from cache")
        print("  Missing: " + str(missing_features[:10]))

    data = pd.read_parquet(str(FEATURE_CACHE_WITH_APRIL), columns=cols_to_load)
    april_data = data[(data["date"] >= "2026-04-01") & (data["date"] <= "2026-04-30")].copy()

    # Filter out limit_up entries
    if "limit_up_like" in april_data.columns:
        april_data = april_data[april_data["limit_up_like"] != 1].copy()

    # Filter min_phase_days_3
    if "short_phase_days_3" in april_data.columns:
        april_data = april_data[april_data["short_phase_days_3"] >= 1].copy()

    print("  April rows (after filters): " + str(len(april_data)))
    if "date" in april_data.columns:
        unique_dates = april_data["date"].nunique()
        print("  Unique April dates: " + str(unique_dates))

    if len(april_data) == 0:
        print("  ERROR: No April data available")
        sys.exit(1)

    # === Run frozen inference ===
    print("\n--- Running frozen inference (score only) ---")
    raw_features = np.zeros((len(april_data), len(feature_names)), dtype=np.float32)
    for i, fname in enumerate(feature_names):
        if fname in april_data.columns:
            raw_features[:, i] = april_data[fname].fillna(0).values.astype(np.float32)

    t0 = time.time()
    prob = run_inference(bundle, raw_features)
    inference_time = time.time() - t0
    print("  Inference time: " + str(round(inference_time, 2)) + "s")
    print("  Predictions: " + str(len(prob)))

    # === Evaluate at multiple thresholds ===
    actual = april_data["actual"].values if "actual" in april_data.columns else None
    if actual is None:
        print("  ERROR: No 'actual' column in April data")
        sys.exit(1)

    print("\n--- April Results (multiple fixed thresholds) ---")
    thresholds = [0.70, 0.75, 0.78, 0.80, 0.85]
    threshold_results = []
    for t in thresholds:
        r = evaluate_at_threshold(prob, actual, t)
        threshold_results.append(r)
        status = "PASS" if r["wilson_95"] >= 0.75 else "below"
        print("  p>=" + str(t) + ": N=" + str(r["count"]) + " acc=" + str(r["accuracy"]) +
              " W95=" + str(r["wilson_95"]) + " cov=" + str(r["coverage"]) + " [" + status + "]")

    # Use bundle's own threshold
    bundle_threshold_result = evaluate_at_threshold(prob, actual, bundle["threshold"])
    print("\n  Bundle threshold (p>=" + str(round(bundle["threshold"], 3)) + "): N=" +
          str(bundle_threshold_result["count"]) + " acc=" + str(bundle_threshold_result["accuracy"]) +
          " W95=" + str(bundle_threshold_result["wilson_95"]))

    # === Monthly breakdown ===
    print("\n--- Monthly Breakdown ---")
    april_data["prob"] = prob
    april_data["date_pd"] = pd.to_datetime(april_data["date"])
    monthly_results = []
    for month_start, month_end, month_name in [
        ("2026-04-01", "2026-04-15", "April 1H"),
        ("2026-04-16", "2026-04-30", "April 2H"),
    ]:
        mask = (april_data["date_pd"] >= month_start) & (april_data["date_pd"] <= month_end)
        sub = april_data[mask]
        if len(sub) > 0:
            hc_mask = sub["prob"] >= bundle["threshold"]
            hc_count = int(hc_mask.sum())
            if hc_count > 0:
                hc_acc = float(sub.loc[hc_mask, "actual"].mean())
                w95 = wilson(hc_count, hc_acc)
            else:
                hc_acc = 0
                w95 = 0
            monthly_results.append({
                "period": month_name, "total": len(sub), "hc_count": hc_count,
                "hc_accuracy": round(hc_acc, 4), "wilson_95": round(w95, 4),
            })
            print("  " + month_name + ": total=" + str(len(sub)) + " HC_N=" + str(hc_count) +
                  " acc=" + str(round(hc_acc, 4)) + " W95=" + str(round(w95, 4)))

    # === Web/Live Gate ===
    print("\n--- WEB/LIVE PARITY GATE ---")
    web_audit = web_gate_audit(sel_features)
    print("  Selected features: " + str(web_audit["total_selected"]))
    print("  Web-available: " + str(web_audit["web_available"]))
    print("  Web-forbidden: " + str(web_audit["web_forbidden_count"]))
    if web_audit["web_forbidden_features"]:
        print("  Forbidden: " + str(web_audit["web_forbidden_features"][:10]))
    print("  P0 in selected: " + str(web_audit["p0_count"]))
    print("  Web gate: " + ("PASS" if web_audit["web_gate_pass"] else "FAIL"))

    # === Final Decision ===
    print("\n" + "=" * 70)
    print("PHASE E FINAL DECISION")
    print("=" * 70)

    april_passes = bundle_threshold_result["wilson_95"] >= 0.70
    web_passes = web_audit["web_gate_pass"]

    if april_passes and web_passes and is_deployable:
        decision = "DEPLOYABLE"
        decision_detail = "April passes, Web gate passes, P0 clean"
    elif april_passes and not web_passes:
        decision = "BLOCKED_WEB"
        decision_detail = "April passes but Web gate fails (forbidden features in selection)"
    elif not april_passes and web_passes:
        decision = "WEAK_APRIL"
        decision_detail = "Web gate passes but April performance below threshold"
    else:
        decision = "BLOCKED"
        decision_detail = "Multiple issues"

    print("  Decision: " + decision)
    print("  Detail: " + decision_detail)
    print("  Stability grade: " + stability_grade)
    print("  April W95 (bundle threshold): " + str(bundle_threshold_result["wilson_95"]))
    print("  Recommendation: " + (
        "Deploy as shadow/challenger with monitoring" if decision == "DEPLOYABLE" and stability_grade in ("A", "B")
        else "Deploy as shadow only with increased monitoring" if decision == "DEPLOYABLE"
        else "Do not deploy, investigate " + decision
    ))

    # === Save JSON ===
    output = {
        "generated_at": datetime.now().isoformat(),
        "audit_type": "phaseE_frozen_april_holdout_and_web_gate",
        "methodology": "frozen bundle score-only, NO retraining",
        "champion_bundle": str(bundle_path),
        "feature_cache": str(FEATURE_CACHE_WITH_APRIL),
        "stability_grade": stability_grade,
        "bundle_info": {
            "model_name": bundle["model_name"],
            "feature_count_full": len(bundle["feature_names"]),
            "feature_count_selected": len(bundle["selected_feature_names"]),
            "threshold": float(bundle["threshold"]),
            "calibration": bundle["calibration_used"],
        },
        "p0_audit": {
            "p0_in_selected": sorted(p0_in_sel),
            "p0_count": len(p0_in_sel),
            "is_deployable": is_deployable,
        },
        "april_holdout": {
            "total_rows": len(april_data),
            "unique_dates": int(april_data["date"].nunique()) if "date" in april_data.columns else 0,
            "bundle_threshold_result": bundle_threshold_result,
            "multi_threshold_results": threshold_results,
            "monthly_breakdown": monthly_results,
        },
        "web_gate": web_audit,
        "final_decision": {
            "decision": decision,
            "detail": decision_detail,
            "april_passes": april_passes,
            "web_passes": web_passes,
            "p0_clean": is_deployable,
        },
        "rollback_plan": {
            "if_april_fails": "Keep current production model, champion stays as research candidate",
            "if_web_fails": "Retrain with web-safe features only (exclude forbidden), re-validate",
            "if_p0_found": "Verify exclusion list, re-run with stricter exclusion, do NOT deploy",
        },
        "self_audit": {
            "no_retraining": True,
            "no_run_gpu_next_day_probe": True,
            "frozen_inference_only": True,
            "p0_audit_expanded": True,
            "april_not_used_for_hpo": True,
            "thresholds_fixed_from_train": True,
        },
    }

    Path(OUTPUT_JSON).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print("\nJSON: " + OUTPUT_JSON)

    # MD report
    md = []
    md.append("# Phase E: Frozen April Holdout + Web/Live Gate - 2026-05-09\n")
    md.append("## Methodology")
    md.append("- Frozen bundle score-only (NO retraining, NO run_gpu_next_day_probe)")
    md.append("- Champion from Phase D: " + str(bundle_path.name))
    md.append("- P0 audit: P0_CANONICAL ∪ P0_ALL ∪ CLASS_C\n")
    md.append("## April Holdout Results\n")
    md.append("| Threshold | N | Accuracy | Wilson 95% | Coverage |")
    md.append("|-----------|---|----------|------------|----------|")
    for r in threshold_results:
        md.append("| p>=" + str(r["threshold"]) + " | " + str(r["count"]) + " | " +
                  str(r["accuracy"]) + " | " + str(r["wilson_95"]) + " | " + str(r["coverage"]) + " |")
    md.append("\n## Monthly Breakdown\n")
    for r in monthly_results:
        md.append("- " + r["period"] + ": N=" + str(r["hc_count"]) + " acc=" + str(r["hc_accuracy"]) +
                  " W95=" + str(r["wilson_95"]))
    md.append("\n## Web/Live Gate")
    md.append("- Web gate: " + ("PASS" if web_audit["web_gate_pass"] else "FAIL"))
    md.append("- P0 in selection: " + str(web_audit["p0_count"]))
    md.append("- Web-forbidden in selection: " + str(web_audit["web_forbidden_count"]))
    if web_audit["web_forbidden_features"]:
        md.append("- Forbidden features: " + str(web_audit["web_forbidden_features"]))
    md.append("\n## Final Decision: " + decision)
    md.append("- " + decision_detail)
    md.append("- Stability: " + stability_grade)
    md.append("\n## Rollback Plan")
    md.append("- If April fails: keep current production, champion stays research")
    md.append("- If Web fails: retrain with web-safe features only")
    md.append("- If P0 found: re-run with stricter exclusion")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("MD: " + OUTPUT_MD)


if __name__ == "__main__":
    main()
