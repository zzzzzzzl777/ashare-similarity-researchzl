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
    fs = a.get("feature_selection", {})
    sm = a.get("split_manifest", {})
    sel = set(fs.get("selected_features", []))
    all_f = set(a.get("features", []))

    c009_in = "tushare_main_force_divergence" in all_f
    c009_sel = "tushare_main_force_divergence" in sel
    c004_in = "tushare_ff_adjusted_flow" in all_f
    c004_sel = "tushare_ff_adjusted_flow" in sel
    c011_in = "tushare_auction_open_vwap_ratio" in all_f
    c011_sel = "tushare_auction_open_vwap_ratio" in sel

    print(f"=== {label} ({rid}) ===")
    print(f"  model: {a.get('model_name', a.get('model', ''))}")
    print(f"  feature_set: {a.get('feature_set', '')}")
    print(f"  features_in: {len(all_f)}, selected: {fs.get('selected_feature_count', len(sel))}")
    print(f"  feature_hash: {a.get('feature_hash', '')}")
    print(f"  data_hash: {a.get('data_hash', '')}")
    print(f"  train_end: {sm.get('train_end', '')}, test_start: {sm.get('test_start', '')}, end: {sm.get('end', '')}")
    print(f"  train_rows: {sm.get('train_window_rows', '')}, test_lockbox_rows: {sm.get('test_lockbox_rows', '')}")
    print(f"  min_phase_days_3: {a.get('min_phase_days_3', '')}")
    print(f"  exclude_event_limit_up: {a.get('exclude_event_limit_up', '')}")
    print(f"  C009 in={c009_in} sel={c009_sel}, C004 in={c004_in} sel={c004_sel}, C011 in={c011_in} sel={c011_sel}")
    top_keys = sorted(k for k in a.keys() if k not in ("features", "feature_selection", "split_manifest"))
    print(f"  top_keys: {top_keys}")
    print()
