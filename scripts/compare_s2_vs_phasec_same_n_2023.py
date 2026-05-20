"""Same-N comparison: 2023 Feb-Apr, both models rank by RAW probability, take identical top-N."""
import math, pickle, sys, numpy as np, pandas as pd, pyarrow.parquet as pq, torch
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\Users\zzzzzzl\Desktop\subagent\src")))

S2_BUNDLE = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T002433Z_a0ec8105\model_bundle.pt")
PHASEC_BUNDLE = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\runs\gpu_probe_20260509T105830Z_12605e2b\model_bundle.pt")
CACHE = Path(r"E:\ashare_similarity_runtime\data\reports\prediction\feature_cache\gpu_probe_features_64ba73ab6db5f833.parquet")

def wilson(n, p):
    if n == 0 or p == 0: return 0.0
    z = 1.96
    denom = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (center - margin) / denom

def load_bundle(path):
    b = torch.load(str(path), map_location="cpu", weights_only=False)
    members = [pickle.loads(m["model_bytes"]) for m in b["members"]]
    iso = pickle.loads(b["iso_model_bytes"]) if b.get("iso_model_bytes") else None
    return {"members": members, "mean": b["mean"], "std": b["std"],
            "selected_indices": b["selected_indices"],
            "feature_names": list(b["feature_names"]), "iso_model": iso,
            "calibration_used": b["calibration_used"]}

def run_inference(bundle, df):
    fnames = bundle["feature_names"]
    raw = np.zeros((len(df), len(fnames)), dtype=np.float32)
    for i, f in enumerate(fnames):
        if f in df.columns:
            raw[:, i] = df[f].fillna(0).values.astype(np.float32)
    x = torch.as_tensor(raw, dtype=torch.float32)
    std = bundle["std"].clone(); std[std == 0] = 1.0
    x = (x - bundle["mean"]) / std
    if bundle["selected_indices"] is not None:
        x = x[:, bundle["selected_indices"]]
    x_np = x.numpy()
    probs = np.stack([m.predict_proba(x_np)[:, 1].astype(np.float32) for m in bundle["members"]], axis=0)
    return probs.mean(axis=0)

s2 = load_bundle(S2_BUNDLE)
pc = load_bundle(PHASEC_BUNDLE)

all_f = set(s2["feature_names"]) | set(pc["feature_names"]) | {"symbol","date","close","actual","limit_up_like","short_phase_days_3"}
schema_cols = set(pq.read_schema(str(CACHE)).names)
data = pd.read_parquet(str(CACHE), columns=[c for c in all_f if c in schema_cols])
window = data[(data["date"] >= "2023-02-01") & (data["date"] <= "2023-04-30")].copy()
window = window[(window["limit_up_like"] != 1) & (window["short_phase_days_3"] >= 1)]

print(f"2023 Feb-Apr: {len(window):,} rows, {window['date'].nunique()} days, pos_rate={window['actual'].mean():.4f}")

s2_raw = run_inference(s2, window)
pc_raw = run_inference(pc, window)
actual = window["actual"].values
dates = window["date"].values

print(f"\n{'=' * 75}")
print("METHOD 1: GLOBAL TOP-N (raw prob ranking, same N from both models)")
print("=" * 75)
print(f"\n  {'N':>6}  {'S2_Acc':>7} {'S2_W95':>7}  {'PC_Acc':>7} {'PC_W95':>7}  {'Delta_Acc':>9} {'Winner':>7}")
print(f"  {'-'*62}")

for n in [100, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000]:
    if n > len(actual):
        continue
    s2_idx = np.argsort(-s2_raw)[:n]
    pc_idx = np.argsort(-pc_raw)[:n]
    s2_acc = actual[s2_idx].mean()
    pc_acc = actual[pc_idx].mean()
    s2_w = wilson(n, s2_acc)
    pc_w = wilson(n, pc_acc)
    delta = pc_acc - s2_acc
    w = "S2" if s2_acc > pc_acc else ("PC" if pc_acc > s2_acc else "tie")
    print(f"  {n:>6}  {s2_acc:>7.4f} {s2_w:>7.4f}  {pc_acc:>7.4f} {pc_w:>7.4f}  {delta:>+9.4f} {w:>7}")

print(f"\n{'=' * 75}")
print("METHOD 2: DAILY TOP-K (raw prob ranking, same K per day)")
print("=" * 75)

df = pd.DataFrame({"date": dates, "actual": actual, "s2_raw": s2_raw, "pc_raw": pc_raw})

print(f"\n  {'K':>4} {'Total':>6}  {'S2_Acc':>7} {'S2_W95':>7}  {'PC_Acc':>7} {'PC_W95':>7}  {'Delta':>7} {'Winner':>7}")
print(f"  {'-'*62}")

for k in [3, 5, 6, 8, 10, 15, 20, 30, 50]:
    s2_sel = df.groupby("date").apply(lambda g: g.nlargest(k, "s2_raw"), include_groups=False).reset_index(drop=True)
    pc_sel = df.groupby("date").apply(lambda g: g.nlargest(k, "pc_raw"), include_groups=False).reset_index(drop=True)
    s2_acc = s2_sel["actual"].mean()
    pc_acc = pc_sel["actual"].mean()
    n = len(s2_sel)
    s2_w = wilson(n, s2_acc)
    pc_w = wilson(n, pc_acc)
    delta = pc_acc - s2_acc
    w = "S2" if s2_acc > pc_acc else ("PC" if pc_acc > s2_acc else "tie")
    print(f"  {k:>4} {n:>6}  {s2_acc:>7.4f} {s2_w:>7.4f}  {pc_acc:>7.4f} {pc_w:>7.4f}  {delta:>+7.4f} {w:>7}")

print(f"\n{'=' * 75}")
print("OVERLAP ANALYSIS (raw prob, global top-500)")
print("=" * 75)
s2_top500 = set(np.argsort(-s2_raw)[:500])
pc_top500 = set(np.argsort(-pc_raw)[:500])
both = s2_top500 & pc_top500
s2_only = s2_top500 - pc_top500
pc_only = pc_top500 - s2_top500

both_idx = np.array(list(both))
s2only_idx = np.array(list(s2_only))
pconly_idx = np.array(list(pc_only))

print(f"\n  Both top-500:     {len(both):>4} tickets, acc={actual[both_idx].mean():.4f}")
print(f"  S2-only top-500:  {len(s2_only):>4} tickets, acc={actual[s2only_idx].mean():.4f}")
print(f"  PC-only top-500:  {len(pc_only):>4} tickets, acc={actual[pconly_idx].mean():.4f}")
print(f"  Overlap rate:     {len(both)/500:.1%}")

for topn in [100, 200, 300]:
    s2_set = set(np.argsort(-s2_raw)[:topn])
    pc_set = set(np.argsort(-pc_raw)[:topn])
    ovlp = s2_set & pc_set
    print(f"  Top-{topn} overlap:   {len(ovlp):>4}/{topn} = {len(ovlp)/topn:.1%}")

print("\nDone.")
