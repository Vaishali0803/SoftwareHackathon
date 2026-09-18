"""
Diagnostic: find exactly why KS pass rate = 0%.
Run: python diagnose_ks.py
"""
import sys, os
sys.path.insert(0, ".")

import pandas as pd
import numpy as np
from scipy import stats
from app.database import SessionLocal, create_tables, GenerationRecord, DatasetRecord

create_tables()
db = SessionLocal()

# Get most recent done generation
gen = (db.query(GenerationRecord)
       .filter(GenerationRecord.status == "done")
       .order_by(GenerationRecord.created_at.desc())
       .first())

if not gen:
    print("No completed generation found — run a generation first.")
    sys.exit(1)

dataset = db.get(DatasetRecord, gen.dataset_id)
db.close()

print(f"Generation: {gen.id[:16]}  model={gen.model_used}  records={gen.num_generated}")
print(f"Synthetic path:             {gen.output_path}")

# Use source_for_validation_path if available (generation-ready, same dtype space)
source_for_val = getattr(gen, "source_for_validation_path", None)
if source_for_val and os.path.exists(source_for_val):
    source_csv = source_for_val
    print(f"Source path (gen-ready):    {source_csv}  ← CORRECT")
else:
    source_csv = dataset.preprocessed_path
    print(f"Source path (preprocessed): {source_csv}  ← FALLBACK (re-run generation for accurate KS)")
print()

src = pd.read_csv(source_csv)
syn = pd.read_csv(gen.output_path)

print(f"Source shape:    {src.shape}")
print(f"Synthetic shape: {syn.shape}")
print()

common = [c for c in src.columns if c in syn.columns]
missing_in_syn = [c for c in src.columns if c not in syn.columns]
extra_in_syn   = [c for c in syn.columns if c not in src.columns]
print(f"Common columns ({len(common)}): {common}")
if missing_in_syn:
    print(f"  Columns in source but NOT in synthetic: {missing_in_syn}")
if extra_in_syn:
    print(f"  Columns in synthetic but NOT in source: {extra_in_syn}")
print()

# Per-column dtype and KS test analysis
print("=" * 100)
print(f"{'Column':<35} {'src_dtype':<12} {'syn_dtype':<12} {'comparable':<12} "
      f"{'ks_stat':>8} {'p_value':>12} {'pass':>5} {'src_n':>6} {'syn_n':>6}")
print("-" * 100)

ks_passes = 0
ks_total  = 0
skipped   = []

for col in common:
    s_ser = src[col]
    y_ser = syn[col]

    src_dtype = str(s_ser.dtype)
    syn_dtype = str(y_ser.dtype)

    src_num = pd.api.types.is_numeric_dtype(s_ser)
    syn_num = pd.api.types.is_numeric_dtype(y_ser)

    if src_num and syn_num:
        s_c = s_ser.dropna().astype(float)
        y_c = y_ser.dropna().astype(float)
        if len(s_c) < 2 or len(y_c) < 2:
            skipped.append((col, "too few non-null values"))
            print(f"{col:<35} {src_dtype:<12} {syn_dtype:<12} {'numeric':<12} "
                  f"{'SKIP: too few':>8}")
            continue
        ks_stat, ks_p = stats.ks_2samp(s_c, y_c)
        passed = ks_p > 0.05
        ks_total += 1
        if passed:
            ks_passes += 1
        print(f"{col:<35} {src_dtype:<12} {syn_dtype:<12} {'numeric':<12} "
              f"{ks_stat:>8.4f} {ks_p:>12.6f} {'PASS' if passed else 'FAIL':>5} "
              f"{len(s_c):>6} {len(y_c):>6}")

        # Extra: show src vs syn stats
        print(f"  src: mean={s_c.mean():.3f}  std={s_c.std():.3f}  "
              f"min={s_c.min():.3f}  max={s_c.max():.3f}")
        print(f"  syn: mean={y_c.mean():.3f}  std={y_c.std():.3f}  "
              f"min={y_c.min():.3f}  max={y_c.max():.3f}")
    else:
        skipped.append((col, f"dtype mismatch: src={src_dtype} syn={syn_dtype}"))
        print(f"{col:<35} {src_dtype:<12} {syn_dtype:<12} {'NOT numeric':<12} "
              f"{'skipped':>8}")

print("=" * 100)
print(f"\nKS results:  {ks_passes}/{ks_total} pass  →  pass rate = "
      f"{ks_passes/ks_total*100:.1f}%" if ks_total else "No KS tests ran.")
if skipped:
    print(f"\nSkipped columns ({len(skipped)}):")
    for col, reason in skipped:
        print(f"  {col}: {reason}")
