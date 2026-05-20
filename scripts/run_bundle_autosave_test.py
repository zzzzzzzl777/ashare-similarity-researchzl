"""Run G config once to verify bundle auto-save integration."""
import sys
from pathlib import Path
from datetime import date

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import (
    GPU_PROBE_STABLE_FEATURES,
    GpuProbeConfig,
    run_gpu_next_day_probe,
)
import ashare_similarity.prediction.gpu_probe as gp

TUSHARE_TIER1_BASE = (
    "tushare_net_mf_amount", "tushare_lg_buy_sell_ratio", "tushare_elg_buy_sell_ratio",
    "tushare_mf_strength", "tushare_sm_sell_pressure", "tushare_volume_ratio",
    "tushare_free_share", "tushare_up_limit_distance", "tushare_down_limit_distance",
    "tushare_limit_range",
)
TUSHARE_TIER1_FEATURES = (*TUSHARE_TIER1_BASE, *(f"{c}_available" for c in TUSHARE_TIER1_BASE))
C009_FEATURES = ("tushare_main_force_divergence", "tushare_main_force_divergence_available")
C004_FEATURES = ("tushare_ff_adjusted_flow", "tushare_ff_adjusted_flow_available")
TIER1_PLUS_C009_C004 = (*TUSHARE_TIER1_FEATURES, *C009_FEATURES, *C004_FEATURES)

app_config = get_default_config()
store = LocalDataStore(app_config)

config = GpuProbeConfig(
    start=date(2023, 5, 1),
    train_end=date(2025, 12, 31),
    test_start=date(2026, 1, 1),
    end=date(2026, 4, 30),
    train_rows=300_000,
    test_rows=120_000,
    label_target="next_high_from_close",
    target_high_return_pct=1.0,
    feature_selection_method="stable_tail",
    max_selected_features=260,
    min_phase_days_3=1,
    selector_coverage_weight=0.02,
    candidate_family="all",
    lockbox_role="seen_research",
    exclude_event_limit_up=True,
    exclude_feature_prefix=("cross_",),
    seed=42,
    feature_set="research",
    use_feature_cache=True,
)

custom_features = tuple(dict.fromkeys((*GPU_PROBE_STABLE_FEATURES, *TIER1_PLUS_C009_C004)))

original_fn = gp._feature_names_for_config
call_state = {"count": 0}
def _two_phase(cfg):
    call_state["count"] += 1
    return original_fn(cfg) if call_state["count"] == 1 else custom_features
gp._feature_names_for_config = _two_phase

print("Running pipeline with bundle auto-save...")
result = run_gpu_next_day_probe(store, config)
gp._feature_names_for_config = original_fn

print(f"\nStatus: {result.get('status')}")
print(f"Run ID: {result.get('run_id')}")
print(f"Model: {result.get('model')} ({result.get('model_kind')})")
print(f"Bundle status: {result.get('model_bundle_status')}")
print(f"Bundle validation: {result.get('model_bundle_validation')}")

if result.get("artifacts"):
    print(f"\nArtifacts: {result['artifacts']}")
