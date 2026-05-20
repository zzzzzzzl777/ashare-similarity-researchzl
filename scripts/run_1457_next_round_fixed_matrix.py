"""Run the next-round 14:57 fixed-config model matrix.

This runner is intentionally conservative:

* It consumes the protocol artifacts produced by ``run_1457_next_round_protocol.py``.
* It can force a known feature cache path so source-code hash changes do not
  accidentally trigger a rebuild.
* It excludes C/D factors from deployable variants and treats B factors as
  policy-gated unless the variant explicitly asks for them.
* It writes every fold result immediately so a long run can be resumed safely.
"""
from __future__ import annotations

import argparse
import ast
import csv
import gc
import json
import math
import sys
import time
import traceback
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import ashare_similarity.prediction.gpu_probe as gp
from ashare_similarity.config import get_default_config
from ashare_similarity.data.storage import LocalDataStore
from ashare_similarity.prediction.gpu_probe import GpuProbeConfig, run_gpu_next_day_probe

try:
    import torch
except Exception:  # pragma: no cover - optional in lightweight environments
    torch = None


P0_CANONICAL_COLUMNS = {
    "sector_climax_signal",
    "sector_climax_signal_available",
    "sector_divergence",
    "sector_divergence_available",
    "sector_duration_days",
    "sector_duration_days_available",
    "sector_limit_up_count",
    "sector_limit_up_count_available",
    "sector_pct_change_best",
    "sector_pct_change_best_available",
    "sector_strength_rank",
    "sector_strength_rank_available",
    "tushare_cost_concentration",
    "tushare_cost_concentration_available",
    "tushare_cost_position",
    "tushare_cost_position_available",
    "tushare_winner_rate",
    "tushare_winner_rate_available",
    "tushare_net_mf_amount",
    "tushare_net_mf_amount_available",
    "tushare_ff_adjusted_flow",
    "tushare_ff_adjusted_flow_available",
    "tushare_lg_buy_sell_ratio",
    "tushare_lg_buy_sell_ratio_available",
    "tushare_elg_buy_sell_ratio",
    "tushare_elg_buy_sell_ratio_available",
    "tushare_mf_strength",
    "tushare_mf_strength_available",
    "tushare_sm_sell_pressure",
    "tushare_sm_sell_pressure_available",
    "tushare_main_force_divergence",
    "tushare_main_force_divergence_available",
    "tushare_lhb_net_buy",
    "tushare_lhb_net_buy_available",
    "tushare_lhb_net_rate",
    "tushare_lhb_net_rate_available",
    "tushare_inst_buy_count",
    "tushare_inst_buy_count_available",
    "tushare_lhb_appeared",
    "tushare_lhb_appeared_available",
    "tushare_inst_net_buy",
    "tushare_inst_net_buy_available",
    "tushare_rzye",
    "tushare_rzye_available",
    "tushare_rzye_delta_pct",
    "tushare_rzye_delta_pct_available",
    "tushare_rzmre_ratio",
    "tushare_rzmre_ratio_available",
    "tushare_margin_net",
    "tushare_margin_net_available",
    "tushare_rqye_ratio",
    "tushare_rqye_ratio_available",
    "tushare_auction_close_vwap_ratio",
    "tushare_auction_close_vwap_ratio_available",
    "tushare_auction_close_vol",
    "tushare_auction_close_vol_available",
    "tushare_float_relative_impact",
    "tushare_float_relative_impact_available",
}

B_POLICY_BLOCK_ISSUES = {
    "td_moneyflow_requires_proxy_name",
    "td_cyq_requires_t1",
}


def parse_args() -> argparse.Namespace:
    cfg = get_default_config()
    report_dir = cfg.storage.report_dir / "prediction"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asof-date", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--feature-cache", type=Path)
    parser.add_argument(
        "--factor-csv",
        type=Path,
        default=report_dir / "next_round_1457_factor_source_discovery_20260513.csv",
    )
    parser.add_argument(
        "--matrix-csv",
        type=Path,
        default=report_dir / "next_round_1457_model_matrix_manifest_20260513.csv",
    )
    parser.add_argument(
        "--time-window-csv",
        type=Path,
        default=report_dir / "next_round_1457_time_window_manifest_20260513.csv",
    )
    parser.add_argument("--variant-id", action="append", default=[], help="Run only these variant ids.")
    parser.add_argument(
        "--stage",
        action="append",
        default=[],
        help="Model-matrix stages to run. Defaults to fixed_config_first.",
    )
    parser.add_argument(
        "--scheme",
        action="append",
        default=[],
        help="Run only these time-window schemes. Defaults to the primary fixed/expanding comparison set.",
    )
    parser.add_argument("--outer-fold", action="append", type=int, default=[], help="Run only these outer fold ids.")
    parser.add_argument("--max-folds-per-scheme", type=int, default=0, help="0 means all eligible primary folds.")
    parser.add_argument("--max-variants", type=int, default=0, help="0 means all selected variants.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budget", type=int, default=260)
    parser.add_argument("--train-rows", type=int, default=300_000)
    parser.add_argument("--test-rows", type=int, default=120_000)
    parser.add_argument("--force-cpu", action="store_true", help="Run torch/tree candidates on CPU for stable long matrices.")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def json_default(value: Any) -> Any:
    if isinstance(value, (date, datetime, Path)):
        return str(value)
    raise TypeError(type(value).__name__)


def wilson_lower(p: float | None, n: int, z: float = 1.959963984540054) -> float:
    if p is None or n <= 0:
        return 0.0
    z2 = z * z
    denom = 1.0 + z2 / float(n)
    centre = float(p) + z2 / (2.0 * float(n))
    margin = z * math.sqrt((float(p) * (1.0 - float(p)) + z2 / (4.0 * float(n))) / float(n))
    return max(0.0, min(1.0, (centre - margin) / denom))


def parse_list_cell(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text or text == "nan":
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, (list, tuple, set)):
            return [str(item) for item in parsed if str(item)]
    except Exception:
        pass
    return [part.strip() for part in text.split(",") if part.strip()]


def companion_columns(columns: list[str]) -> set[str]:
    out: set[str] = set()
    for column in columns:
        out.add(column)
        if not column.endswith("_available"):
            out.add(f"{column}_available")
    return out


def factor_column_map(factor_df: pd.DataFrame) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for row in factor_df.to_dict("records"):
        fid = str(row.get("factor_id") or "")
        columns = set(parse_list_cell(row.get("cache_columns_found"))) | set(parse_list_cell(row.get("code_columns_found")))
        if not fid or not columns:
            continue
        mapping.setdefault(fid, set()).update(companion_columns(sorted(columns)))
    return mapping


def build_exclusion(
    *,
    factor_df: pd.DataFrame,
    include_factor_ids: set[str],
    include_b_policy: bool,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    by_factor = factor_column_map(factor_df)
    exclude: set[str] = set(P0_CANONICAL_COLUMNS)
    class_counts = factor_df["availability_class"].value_counts(dropna=False).to_dict()
    excluded_factors: list[str] = []
    blocked_b_factors: list[str] = []

    for row in factor_df.to_dict("records"):
        fid = str(row.get("factor_id") or "")
        klass = str(row.get("availability_class") or "")
        issue_code = str(row.get("issue_code") or "")
        cols = by_factor.get(fid, set())
        if not cols:
            continue
        should_exclude = False
        if klass in {"C", "D"}:
            should_exclude = True
        elif klass == "B":
            if not include_b_policy or issue_code in B_POLICY_BLOCK_ISSUES:
                should_exclude = True
                if issue_code in B_POLICY_BLOCK_ISSUES:
                    blocked_b_factors.append(fid)
        elif klass == "A":
            should_exclude = fid not in include_factor_ids

        if should_exclude:
            excluded_factors.append(fid)
            exclude.update(cols)

    audit = {
        "include_factor_ids": sorted(include_factor_ids),
        "include_b_policy": bool(include_b_policy),
        "availability_class_counts": class_counts,
        "excluded_factor_ids": sorted(set(excluded_factors)),
        "blocked_b_factor_ids": sorted(set(blocked_b_factors)),
        "excluded_feature_count": len(exclude),
    }
    return tuple(sorted(exclude)), audit


def choose_default_schemes(window_df: pd.DataFrame) -> list[str]:
    preferred = [
        "fixed_recent_24m",
        "fixed_recent_30m",
        "fixed_recent_36m",
        "fixed_recent_48m",
        "fixed_recent_60m",
        "fixed_recent_72m",
        "fixed_start_2018",
        "fixed_start_2019",
        "fixed_start_2020",
        "fixed_start_2021",
        "fixed_start_2022",
        "fixed_start_2023",
        "expanding_from_fair_start",
    ]
    available = set(window_df["scheme"].astype(str))
    return [scheme for scheme in preferred if scheme in available]


def selected_variants(
    matrix_df: pd.DataFrame,
    variant_ids: list[str],
    max_variants: int,
    stages: list[str] | None = None,
) -> pd.DataFrame:
    chosen_stages = stages or ["fixed_config_first"]
    fixed = matrix_df[matrix_df["stage"].astype(str).isin(chosen_stages)].copy()
    if variant_ids:
        fixed = fixed[fixed["variant_id"].isin(variant_ids)].copy()
    if max_variants > 0:
        fixed = fixed.head(max_variants).copy()
    return fixed.reset_index(drop=True)


def declared_factor_ids(row: dict[str, Any]) -> set[str]:
    include_ids = set(str(row.get("include_factor_ids") or "").split(","))
    return {fid.strip() for fid in include_ids if fid.strip()}


def effective_include_factor_ids(variant: dict[str, Any], matrix_df: pd.DataFrame) -> tuple[set[str], dict[str, Any]]:
    variant_id = str(variant.get("variant_id") or "")
    stage = str(variant.get("stage") or "")
    added_ids = declared_factor_ids(variant)
    base_variant_id = str(variant.get("base_variant") or "").strip()
    if (
        not base_variant_id
        and stage == "family_ablation"
        and (variant_id.startswith("family_add_") or variant_id.startswith("family_drop_"))
    ):
        base_variant_id = "pre_new_A_engineerable_control"

    base_ids: set[str] = set()
    if base_variant_id:
        base_rows = matrix_df[matrix_df["variant_id"].astype(str).eq(base_variant_id)]
        if base_rows.empty:
            raise ValueError(f"base_variant not found for {variant_id}: {base_variant_id}")
        base_ids = declared_factor_ids(base_rows.iloc[0].to_dict())
    dropped_ids: set[str] = set()
    if stage == "family_ablation" and variant_id.startswith("family_drop_"):
        dropped_ids = added_ids & base_ids
        effective_ids = base_ids - dropped_ids
    else:
        effective_ids = base_ids | added_ids

    audit = {
        "base_variant_id": base_variant_id or None,
        "base_factor_ids": sorted(base_ids),
        "declared_added_factor_ids": sorted(added_ids),
        "declared_dropped_factor_ids": sorted(dropped_ids),
        "effective_include_factor_ids": sorted(effective_ids),
        "effective_include_factor_count": len(effective_ids),
    }
    return effective_ids, audit


def selected_windows(
    window_df: pd.DataFrame,
    schemes: list[str],
    max_folds_per_scheme: int,
    outer_folds: list[int] | None = None,
) -> pd.DataFrame:
    chosen_schemes = schemes or choose_default_schemes(window_df)
    train_window_valid = pd.to_datetime(window_df["fit_train_start"], errors="coerce").le(
        pd.to_datetime(window_df["fit_train_end"], errors="coerce")
    )
    if "train_window_valid" in window_df.columns:
        train_window_valid = train_window_valid & window_df["train_window_valid"].astype(bool)
    mask = (
        window_df["scheme"].isin(chosen_schemes)
        & window_df["primary_outer_unit"].astype(bool)
        & window_df["eligible_after_rebuild"].astype(bool)
        & ~window_df["train_uses_seen_research"].astype(bool)
        & train_window_valid
    )
    selected = window_df.loc[mask].copy()
    if outer_folds:
        selected = selected[selected["outer_fold"].astype(int).isin({int(fold) for fold in outer_folds})].copy()
    selected = selected.sort_values(["scheme", "outer_valid_start", "outer_fold"])
    if max_folds_per_scheme > 0:
        selected = pd.concat(
            [_sample_evenly(group, max_folds_per_scheme) for _, group in selected.groupby("scheme", sort=False)],
            ignore_index=True,
        )
    return selected.reset_index(drop=True)


def _sample_evenly(group: pd.DataFrame, count: int) -> pd.DataFrame:
    if count <= 0 or len(group) <= count:
        return group
    if count == 1:
        return group.iloc[[-1]]
    positions = sorted({round(i * (len(group) - 1) / (count - 1)) for i in range(count)})
    return group.iloc[positions]


def force_feature_cache(path: Path | None) -> None:
    if path is None:
        return
    original_descriptor = gp._feature_cache_descriptor

    def _forced_cache_descriptor(store_arg, config_arg, *, symbols, context_symbols=None):
        descriptor = original_descriptor(store_arg, config_arg, symbols=symbols, context_symbols=context_symbols)
        descriptor.update(
            {
                "enabled": True,
                "hit": True,
                "refresh": False,
                "path": str(path),
                "metadata_path": str(path.with_suffix(".json")),
                "fingerprint": path.stem.removeprefix("gpu_probe_features_"),
            }
        )
        meta_path = path.with_suffix(".json")
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                descriptor["rows"] = meta.get("rows")
                descriptor["symbol_frames_kept"] = meta.get("symbol_frames_kept")
                descriptor["created_at"] = meta.get("created_at")
                descriptor["factor_reports"] = meta.get("factor_reports") or []
            except Exception:
                pass
        print(f"[fixed_matrix] forced feature cache: {path}", file=sys.stderr, flush=True)
        return descriptor

    gp._feature_cache_descriptor = _forced_cache_descriptor


def run_one_fold(
    *,
    store: LocalDataStore,
    variant: dict[str, Any],
    window: dict[str, Any],
    exclude_features: tuple[str, ...],
    args: argparse.Namespace,
) -> dict[str, Any]:
    train_start = date.fromisoformat(str(window["fit_train_start"])[:10])
    train_end = date.fromisoformat(str(window["fit_train_end"])[:10])
    test_start = date.fromisoformat(str(window["outer_valid_start"])[:10])
    test_end = date.fromisoformat(str(window["outer_valid_end"])[:10])
    config = GpuProbeConfig(
        start=train_start,
        train_end=train_end,
        test_start=test_start,
        end=test_end,
        train_rows=args.train_rows,
        test_rows=args.test_rows,
        seed=args.seed,
        feature_set="research",
        label_target="next_high_from_close",
        target_high_return_pct=1.0,
        feature_selection_method="stable_tail",
        max_selected_features=args.budget,
        min_phase_days_3=1,
        selector_coverage_weight=0.02,
        candidate_family="all",
        lockbox_role="seen_research",
        exclude_event_limit_up=True,
        exclude_feature_prefix=("cross_",),
        exclude_feature_names=exclude_features,
        use_feature_cache=True,
        refresh_feature_cache=False,
        force_cpu=bool(args.force_cpu),
    )
    started = time.perf_counter()
    result = run_gpu_next_day_probe(store, config)
    elapsed = time.perf_counter() - started
    fs = result.get("feature_selection") or {}
    selected = list(fs.get("selected_features") or [])
    p0_selected = sorted(set(selected) & set(exclude_features))
    confident_acc = result.get("confident_accuracy")
    confident_count = int(result.get("confident_count") or 0)
    artifacts = result.get("artifacts") or {}
    bundle_validation = result.get("model_bundle_validation") or {}
    force_cpu = bool(result.get("force_cpu") or args.force_cpu)
    device = str(result.get("device") or ("cpu" if force_cpu else "unknown"))
    compute_backend = "cpu" if force_cpu or device == "cpu" else "gpu"
    return {
        "variant_id": variant["variant_id"],
        "scheme": window["scheme"],
        "outer_fold": int(window["outer_fold"]),
        "fit_train_start": str(window["fit_train_start"]),
        "fit_train_end": str(window["fit_train_end"]),
        "outer_valid_start": str(window["outer_valid_start"]),
        "outer_valid_end": str(window["outer_valid_end"]),
        "seed": int(args.seed),
        "budget": int(args.budget),
        "elapsed_s": round(elapsed, 3),
        "status": result.get("status", "ok"),
        "model": result.get("model", "unknown"),
        "compute_backend": compute_backend,
        "device": device,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "gpu_scope": result.get("gpu_scope"),
        "gpu_enabled": bool(result.get("gpu_enabled")),
        "force_cpu": force_cpu,
        "run_id": result.get("run_id"),
        "run_dir": artifacts.get("run_dir"),
        "artifact_path": artifacts.get("artifact"),
        "test_predictions_path": artifacts.get("test_predictions"),
        "model_bundle_path": str(Path(artifacts["run_dir"]) / "model_bundle.pt") if artifacts.get("run_dir") else None,
        "model_bundle_status": result.get("model_bundle_status"),
        "model_bundle_validation_passed": bool(bundle_validation.get("passed")),
        "confident_accuracy": confident_acc,
        "confident_count": confident_count,
        "confident_coverage": result.get("confident_coverage"),
        "wilson_95": wilson_lower(confident_acc, confident_count),
        "selected_feature_count": len(selected),
        "p0_selected_count": len(p0_selected),
        "p0_selected": p0_selected,
        "feature_cache": (result.get("feature_cache") or {}).get("path"),
        "selected_features": selected,
    }


def cleanup_runtime() -> None:
    gc.collect()
    if torch is not None:
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass


def result_key(row: dict[str, Any]) -> tuple[str, str, int, int, int]:
    return (
        str(row.get("variant_id")),
        str(row.get("scheme")),
        int(row.get("outer_fold") or 0),
        int(row.get("seed") or 0),
        int(row.get("budget") or 0),
    )


def load_completed(jsonl_path: Path) -> set[tuple[str, str, int, int, int]]:
    completed: set[tuple[str, str, int, int, int]] = set()
    if not jsonl_path.exists():
        return completed
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if str(row.get("status")) == "ERROR":
                    continue
                completed.add(result_key(row))
            except Exception:
                continue
    return completed


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=json_default) + "\n")


def write_summary(
    jsonl_path: Path,
    out_csv: Path,
    out_json: Path,
    *,
    active_variant_ids: set[str] | None = None,
) -> None:
    raw_rows: list[dict[str, Any]] = []
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                raw_rows.append(json.loads(line))
    deduped: dict[tuple[str, str, int, int, int], dict[str, Any]] = {}
    for row in raw_rows:
        if active_variant_ids is not None and str(row.get("variant_id")) not in active_variant_ids:
            continue
        deduped[result_key(row)] = row
    rows = list(deduped.values())
    completed_rows = [row for row in rows if str(row.get("status")) != "ERROR"]
    error_rows = [row for row in rows if str(row.get("status")) == "ERROR"]
    flat_rows = []
    for row in completed_rows:
        flat = {k: v for k, v in row.items() if k not in {"selected_features", "p0_selected", "variant_audit"}}
        flat["selected_features_json"] = json.dumps(row.get("selected_features") or [], ensure_ascii=False)
        flat["p0_selected_json"] = json.dumps(row.get("p0_selected") or [], ensure_ascii=False)
        flat_rows.append(flat)
    if flat_rows:
        pd.DataFrame(flat_rows).to_csv(out_csv, index=False, encoding="utf-8-sig")
    df = pd.DataFrame(flat_rows)
    leaderboard: list[dict[str, Any]] = []
    if not df.empty:
        group_cols = ["variant_id", "scheme"]
        agg = df.groupby(group_cols, dropna=False).agg(
            folds=("outer_fold", "count"),
            mean_wilson_95=("wilson_95", "mean"),
            min_wilson_95=("wilson_95", "min"),
            mean_accuracy=("confident_accuracy", "mean"),
            total_candidates=("confident_count", "sum"),
            p0_selected_total=("p0_selected_count", "sum"),
        )
        agg = agg.reset_index().sort_values(["mean_wilson_95", "min_wilson_95"], ascending=False)
        leaderboard = agg.to_dict("records")
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fold_rows": len(completed_rows),
        "error_rows": len(error_rows),
        "leaderboard": leaderboard,
        "jsonl": str(jsonl_path),
        "csv": str(out_csv),
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")


def main() -> int:
    args = parse_args()
    cfg = get_default_config()
    cfg.ensure_directories()
    out_dir = cfg.storage.report_dir / "prediction"
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / f"next_round_1457_fixed_matrix_results_{args.asof_date}.jsonl"
    csv_path = out_dir / f"next_round_1457_fixed_matrix_results_{args.asof_date}.csv"
    summary_path = out_dir / f"next_round_1457_fixed_matrix_summary_{args.asof_date}.json"

    factor_df = pd.read_csv(args.factor_csv)
    matrix_df = pd.read_csv(args.matrix_csv)
    window_df = pd.read_csv(args.time_window_csv)
    variants = selected_variants(matrix_df, args.variant_id, args.max_variants, args.stage)
    windows = selected_windows(window_df, args.scheme, args.max_folds_per_scheme, args.outer_fold)
    if variants.empty or windows.empty:
        raise SystemExit("No variants or windows selected.")

    completed = load_completed(jsonl_path) if args.resume else set()
    force_feature_cache(args.feature_cache)
    store = LocalDataStore(cfg)

    plan_rows = len(variants) * len(windows)
    print(
        json.dumps(
            {
                "variants": variants["variant_id"].tolist(),
                "schemes": sorted(set(windows["scheme"].astype(str))),
                "windows": len(windows),
                "planned_fold_runs": plan_rows,
                "already_completed": len(completed),
                "feature_cache": str(args.feature_cache) if args.feature_cache else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    if args.dry_run:
        return 0

    for variant in variants.to_dict("records"):
        include_ids, variant_resolution_audit = effective_include_factor_ids(variant, matrix_df)
        include_b_policy = str(variant["variant_id"]) == "all_A_plus_B_t1_proxy_policy"
        exclude_features, audit = build_exclusion(
            factor_df=factor_df,
            include_factor_ids=include_ids,
            include_b_policy=include_b_policy,
        )
        audit.update(variant_resolution_audit)
        for window in windows.to_dict("records"):
            key = (
                str(variant["variant_id"]),
                str(window["scheme"]),
                int(window["outer_fold"]),
                int(args.seed),
                int(args.budget),
            )
            if key in completed:
                continue
            print(
                f"[fixed_matrix] run variant={key[0]} scheme={key[1]} fold={key[2]} "
                f"train={window['fit_train_start']}..{window['fit_train_end']} "
                f"valid={window['outer_valid_start']}..{window['outer_valid_end']} "
                f"exclude={len(exclude_features)}",
                flush=True,
            )
            try:
                row = run_one_fold(
                    store=store,
                    variant=variant,
                    window=window,
                    exclude_features=exclude_features,
                    args=args,
                )
                row["variant_audit"] = audit
            except MemoryError as exc:
                cleanup_runtime()
                print(f"[fixed_matrix] memory error, retrying once after cleanup: {repr(exc)}", flush=True)
                try:
                    row = run_one_fold(
                        store=store,
                        variant=variant,
                        window=window,
                        exclude_features=exclude_features,
                        args=args,
                    )
                    row["variant_audit"] = audit
                    row["retry_note"] = f"retried_after_memory_error: {repr(exc)}"
                except Exception as retry_exc:
                    row = {
                        "variant_id": variant["variant_id"],
                        "scheme": window["scheme"],
                        "outer_fold": int(window["outer_fold"]),
                        "seed": int(args.seed),
                        "budget": int(args.budget),
                        "status": "ERROR",
                        "error": repr(retry_exc),
                        "first_error": repr(exc),
                        "traceback": traceback.format_exc(),
                        "variant_audit": audit,
                    }
            except Exception as exc:
                row = {
                    "variant_id": variant["variant_id"],
                    "scheme": window["scheme"],
                    "outer_fold": int(window["outer_fold"]),
                    "seed": int(args.seed),
                    "budget": int(args.budget),
                    "status": "ERROR",
                    "error": repr(exc),
                    "traceback": traceback.format_exc(),
                    "variant_audit": audit,
                }
            append_jsonl(jsonl_path, row)
            write_summary(jsonl_path, csv_path, summary_path, active_variant_ids=set(variants["variant_id"].astype(str)))
            completed.add(result_key(row))
            cleanup_runtime()
            print(
                f"[fixed_matrix] done status={row.get('status')} w95={row.get('wilson_95')} "
                f"acc={row.get('confident_accuracy')} n={row.get('confident_count')} "
                f"p0={row.get('p0_selected_count')}",
                flush=True,
            )

    write_summary(jsonl_path, csv_path, summary_path, active_variant_ids=set(variants["variant_id"].astype(str)))
    print(f"[fixed_matrix] summary: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
