"""
Live API test: upload a longitudinal dataset and verify classification.
Run: python test_longitudinal_api.py
"""
import sys, io, csv
sys.path.insert(0, ".")
import httpx

BASE = "http://localhost:8000/api"

# ── Build a small longitudinal CSV in-memory ──────────────────────────────────
rows = [
    ["patient_id", "visit_date", "patient_name", "age", "diabetes", "systolic_bp", "diastolic_bp", "pain_score"],
    ["P001", "2024-01-01", "John Doe",   45, True,  140, 90, 3.0],
    ["P001", "2024-02-01", "John Doe",   45, True,  138, 88, 2.5],
    ["P001", "2024-03-01", "John Doe",   45, True,  135, 85, 2.0],
    ["P002", "2024-01-01", "Jane Smith", 62, False, 125, 80, 1.0],
    ["P002", "2024-02-01", "Jane Smith", 62, False, 122, 78, 1.5],
    ["P003", "2024-01-01", "Bob Jones",  38, True,  150, 95, 5.0],
    ["P003", "2024-02-01", "Bob Jones",  38, True,  147, 92, 4.5],
    ["P003", "2024-03-01", "Bob Jones",  38, True,  144, 90, 4.0],
    ["P003", "2024-04-01", "Bob Jones",  38, True,  141, 88, 3.5],
    ["P004", "2024-01-01", "Alice Wu",   55, False, 118, 75, 0.5],
]
buf = io.StringIO()
csv.writer(buf).writerows(rows)
csv_bytes = buf.getvalue().encode()

print("=== Longitudinal Dataset API Test ===\n")
print(f"Dataset: {len(rows)-1} rows, columns: {rows[0]}")

# Upload
client = httpx.Client(base_url=BASE, timeout=30)
r = client.post("/dataset/upload",
    files={"file": ("longitudinal_test.csv", csv_bytes, "text/csv")})
assert r.status_code == 200, f"Upload failed: {r.status_code} {r.text}"
j = r.json()

pc  = j["privacy_classification"]
lon = j["longitudinal_info"]

print(f"\ndirect_identifiers:        {pc['direct_identifiers']}")
print(f"longitudinal_linkage_keys: {pc['longitudinal_linkage_keys']}")
print(f"temporal_columns:          {pc['temporal_columns']}")
print(f"quasi_identifiers:         {pc['quasi_identifiers']}")
print(f"sensitive_health_attributes: {pc['sensitive_health_attributes']}")
print(f"excluded_from_modeling:    {pc['excluded_from_modeling']}")

print(f"\nis_longitudinal:   {lon['is_longitudinal']}")
print(f"dataset_type:      {lon['dataset_type']}")
print(f"linkage_key:       {lon['linkage_key']}")
print(f"temporal_column:   {lon['temporal_column']}")
print(f"unique_subjects:   {lon['unique_subjects']}")
print(f"repeated_subjects: {lon['repeated_subjects']}")
print(f"avg_obs/subject:   {lon['avg_obs_per_subject']}")

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

print("\n--- Assertions ---")
check("patient_name in direct_identifiers",    "patient_name" in pc["direct_identifiers"])
check("patient_id in longitudinal_linkage_keys", "patient_id" in pc["longitudinal_linkage_keys"])
check("patient_id NOT in direct_identifiers",  "patient_id" not in pc["direct_identifiers"])
check("visit_date in temporal_columns",        "visit_date" in pc["temporal_columns"])
check("age in quasi_identifiers",              "age" in pc["quasi_identifiers"])
check("diabetes in sensitive_health",          "diabetes" in pc["sensitive_health_attributes"])
check("systolic_bp in sensitive_health",       "systolic_bp" in pc["sensitive_health_attributes"])
check("pain_score in sensitive_health",        "pain_score" in pc["sensitive_health_attributes"])
check("is_longitudinal = True",                lon["is_longitudinal"] is True)
check("dataset_type = longitudinal",           lon["dataset_type"] == "longitudinal")
check("linkage_key = patient_id",              lon["linkage_key"] == "patient_id")
check("temporal_column = visit_date",          lon["temporal_column"] == "visit_date")
check("unique_subjects = 4",                   lon["unique_subjects"] == 4)
check("repeated_subjects = 3",                 lon["repeated_subjects"] == 3)

print(f"\n{'='*40}")
print(f"  {PASS} passed,  {FAIL} failed")
if FAIL == 0:
    print("  ALL API ASSERTIONS PASSED")
else:
    sys.exit(1)
