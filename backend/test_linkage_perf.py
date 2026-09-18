"""
Verify linkage-key detection is fast and correct, and that
_prepare_for_sdv strips patient_id before CTGAN.
"""
import sys, time
sys.path.insert(0, ".")
import pandas as pd
from app.services.synthetic_generation import _is_linkage_key, _prepare_for_sdv

PASS = 0
FAIL = 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  PASS  {label}")
        PASS += 1
    else:
        print(f"  FAIL  {label}  {detail}")
        FAIL += 1

# ── Timing ────────────────────────────────────────────────────────────────────
cols = ["patient_id","subject_id","participant_id","person_id","study_id",
        "age","diabetes","blood_pressure","pain_score","visit_date",
        "patient_name","email","phone"]

t0 = time.perf_counter()
for _ in range(10000):
    [_is_linkage_key(c) for c in cols]
t1 = time.perf_counter()
per_call_ms = (t1 - t0) / 10000 * 1000
print(f"_is_linkage_key x10000: {(t1-t0)*1000:.1f} ms total  ({per_call_ms:.4f} ms per call)")
check("_is_linkage_key < 0.1 ms per call (near-instant)",
      per_call_ms < 0.1,
      f"actual={per_call_ms:.4f} ms")

# ── Correctness ───────────────────────────────────────────────────────────────
print()
for col, expected in [
    ("patient_id",    True),  ("patientid",      True),
    ("subject_id",    True),  ("subjectid",       True),
    ("participant_id",True),  ("participantid",   True),
    ("person_id",     True),  ("personid",        True),
    ("study_id",      True),  ("case_id",         True),
    ("cohort_id",     True),  ("encounter_id",    True),
    ("member_id",     True),  ("patient_key",     True),
    ("subject_key",   True),
    # Must NOT be linkage keys
    ("age",           False), ("diabetes",        False),
    ("blood_pressure",False), ("pain_score",      False),
    ("visit_date",    False), ("patient_name",    False),
    ("email",         False), ("phone",           False),
    ("medication",    False), ("bmi",             False),
]:
    got = _is_linkage_key(col)
    check(f"{col} -> linkage={got} (expected {expected})", got == expected)

# ── _prepare_for_sdv strips linkage keys ─────────────────────────────────────
print()
df_test = pd.DataFrame({
    "patient_id":    ["P001","P001","P002","P002","P003"],
    "visit_date":    ["2024-01-01","2024-02-01","2024-01-01","2024-02-01","2024-01-01"],
    "age":           [45, 45, 62, 62, 38],
    "diabetes":      [True, True, False, False, True],
    "systolic_bp":   [140, 138, 125, 122, 150],
    "pain_score":    [3.0, 2.5, 1.0, 1.5, 5.0],
})

t2 = time.perf_counter()
sdv_df = _prepare_for_sdv(df_test)
t3 = time.perf_counter()
print(f"_prepare_for_sdv on {len(df_test)} rows: {(t3-t2)*1000:.2f} ms")

check("patient_id stripped from SDV input",
      "patient_id" not in sdv_df.columns,
      f"cols={list(sdv_df.columns)}")
check("age retained in SDV input",
      "age" in sdv_df.columns)
check("diabetes retained in SDV input",
      "diabetes" in sdv_df.columns)
check("systolic_bp retained in SDV input",
      "systolic_bp" in sdv_df.columns)
check("pain_score retained in SDV input",
      "pain_score" in sdv_df.columns)

# visit_date is a date string -> should be converted to ordinal int
check("visit_date ordinal conversion: date col removed",
      "visit_date" not in sdv_df.columns or
      str(sdv_df["visit_date"].dtype) in ("float64","int64","Int64"))

print(f"\nSDV-ready columns: {list(sdv_df.columns)}")

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*45}")
print(f"  {PASS} passed,  {FAIL} failed")
print("  ALL PASSED" if FAIL == 0 else "  SOME FAILED")
print("="*45)
if FAIL: sys.exit(1)
