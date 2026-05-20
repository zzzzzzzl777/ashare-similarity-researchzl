import json, os

runs = {
    "C": "gpu_probe_20260504T031602Z_43170e0b",
    "F": "gpu_probe_20260504T033043Z_080a9ce1",
    "G": "gpu_probe_20260504T033857Z_074fe9ea",
}
base = os.path.join("E:", os.sep, "ashare_similarity_runtime", "data", "reports", "prediction", "runs")

for label, rid in runs.items():
    path = os.path.join(base, rid, "artifact.json")
    with open(path, encoding="utf-8") as f:
        a = json.load(f)
    r = a.get("result", {})
    fs = r.get("feature_selection", {})
    sm = r.get("split_manifest", {})
    sel_features = set(fs.get("selected_features", []))
    all_features = set(r.get("features", []))
    sf = r.get("short_filter", {})

    c009_in = "tushare_main_force_divergence" in all_features
    c009_sel = "tushare_main_force_divergence" in sel_features
    c004_in = "tushare_ff_adjusted_flow" in all_features
    c004_sel = "tushare_ff_adjusted_flow" in sel_features
    c011_in = "tushare_auction_open_vwap_ratio" in all_features
    c011_sel = "tushare_auction_open_vwap_ratio" in sel_features

    print(f"=== {label} ({rid}) ===")
    print(f"  model: {r.get('model', '')}")
    print(f"  model_kind: {r.get('model_kind', '')}")
    print(f"  feature_set: {r.get('feature_set', '')}")
    print(f"  features_in: {len(all_features)}, selected: {fs.get('selected_feature_count', len(sel_features))}")
    print(f"  feature_hash: {r.get('feature_hash', a.get('feature_hash', ''))}")
    print(f"  data_hash: {r.get('data_hash', a.get('data_hash', ''))}")
    print(f"  split_hash: {r.get('split_hash', a.get('split_hash', ''))}")
    print(f"  train_end: {sm.get('train_end', '')}")
    print(f"  test_start: {sm.get('test_start', '')}")
    print(f"  end: {sm.get('end', '')}")
    print(f"  train_rows: {sm.get('train_window_rows', '')}")
    print(f"  fit_rows: {sm.get('fit_rows', '')}")
    print(f"  validation_rows: {sm.get('validation_rows', '')}")
    print(f"  test_lockbox_rows: {sm.get('test_lockbox_rows', '')}")
    print(f"  test_start_actual: {r.get('test_start', '')}")
    print(f"  test_end_actual: {r.get('test_end', '')}")
    print(f"  test_predictions_rows: {r.get('test_predictions_rows', '')}")
    print(f"  min_phase_days_3: {sf.get('min_phase_days_3', '')}")
    print(f"  exclude_event_limit_up: {r.get('exclude_event_limit_up', '')}")
    print(f"  lockbox_role: {r.get('lockbox_role', '')}")
    print(f"  C009 in={c009_in} sel={c009_sel}")
    print(f"  C004 in={c004_in} sel={c004_sel}")
    print(f"  C011 in={c011_in} sel={c011_sel}")

    # Count tushare features
    tushare_sel = [f for f in sel_features if f.startswith("tushare_") and not f.endswith("_available")]
    print(f"  tushare_selected: {len(tushare_sel)} {sorted(tushare_sel)}")
    print()
