import sys, time
sys.path.insert(0, ".")
import pandas as pd
from app.services.synthetic_generation import _is_linkage_key, _prepare_for_sdv

ok = True

# Timing
cols = ["patient_id","subject_id","age","diabetes","blood_pressure","pain_score"]
t0 = time.perf_counter()
for _ in range(10000):
    [_is_linkage_key(c) for c in cols]
t1 = time.perf_counter()
per_call_ms = (t1 - t0) / 10000 * 1000
sys.stdout.write("TIMING: %.4f ms per call\n" % per_call_ms)
if per_call_ms >= 0.1:
    sys.stdout.write("FAIL: too slow\n"); ok = False
else:
    sys.stdout.write("PASS: near-instant\n")

# Correctness
must_be_linkage = ["patient_id","patientid","subject_id","participant_id",
                   "person_id","study_id","case_id","cohort_id","encounter_id",
                   "member_id","patient_key","subject_key"]
must_not_be_linkage = ["age","diabetes","blood_pressure","pain_score",
                       "visit_date","patient_name","email","phone","medication","bmi"]

for col in must_be_linkage:
    r = _is_linkage_key(col)
    label = "PASS" if r else "FAIL"
    if not r: ok = False
    sys.stdout.write("%s: %s -> linkage=True\n" % (label, col))

for col in must_not_be_linkage:
    r = _is_linkage_key(col)
    label = "PASS" if not r else "FAIL"
    if r: ok = False
    sys.stdout.write("%s: %s -> linkage=False\n" % (label, col))

# _prepare_for_sdv strips patient_id
df = pd.DataFrame({
    "patient_id":  ["P001","P001","P002","P002","P003"],
    "age":         [45,45,62,62,38],
    "diabetes":    [True,True,False,False,True],
    "systolic_bp": [140,138,125,122,150],
    "pain_score":  [3.0,2.5,1.0,1.5,5.0],
})
t2 = time.perf_counter()
sdv_df = _prepare_for_sdv(df)
t3 = time.perf_counter()
sys.stdout.write("_prepare_for_sdv: %.2f ms\n" % ((t3-t2)*1000))
sys.stdout.write("SDV cols: %s\n" % list(sdv_df.columns))

if "patient_id" not in sdv_df.columns:
    sys.stdout.write("PASS: patient_id stripped from CTGAN input\n")
else:
    sys.stdout.write("FAIL: patient_id still in CTGAN input\n"); ok = False

for keep in ["age","diabetes","systolic_bp","pain_score"]:
    if keep in sdv_df.columns:
        sys.stdout.write("PASS: %s retained\n" % keep)
    else:
        sys.stdout.write("FAIL: %s missing\n" % keep); ok = False

sys.stdout.write("\n%s\n" % ("ALL PASSED" if ok else "SOME FAILED"))
sys.exit(0 if ok else 1)
