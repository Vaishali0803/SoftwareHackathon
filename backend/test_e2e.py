"""
End-to-end generation test against the live backend.
Run while the server is running: python test_e2e.py

Tests:
  1. Health check — SDV available
  2. Upload demo dataset
  3. Preprocess dataset
  4. Start CTGAN generation (500 records, fast)
  5. Poll until done
  6. Validate source vs synthetic
  7. Privacy check
  8. Export CSV + XLSX
"""
import sys, time, json
import httpx

BASE = "http://localhost:8000/api"
client = httpx.Client(base_url=BASE, timeout=30)

def step(n, msg):
    print(f"\n[STEP {n}] {msg}")

def ok(msg):
    print(f"        ✓  {msg}")

def fail(msg):
    print(f"        ✗  {msg}")
    sys.exit(1)

# ── 1. Health check ───────────────────────────────────────────────────────────
step(1, "Health check")
r = client.get("/health")
assert r.status_code == 200, fail(f"Health returned {r.status_code}")
h = r.json()
deps = h["dependencies"]
print(f"        SDV installed:   {deps['sdv_installed']}  (v{deps.get('sdv_version')})")
print(f"        CTGAN available: {deps['ctgan_available']}")
print(f"        Generation ready:{deps['generation_ready']}")
if not deps["generation_ready"]:
    fail("SDV/CTGAN not ready — install dependencies first")
ok("Backend healthy, SDV ready")

# ── 2. Upload demo dataset ────────────────────────────────────────────────────
step(2, "Upload demo dataset")
r = client.post("/dataset/upload-demo", timeout=30)
assert r.status_code == 200, fail(f"Upload-demo returned {r.status_code}: {r.text}")
ds = r.json()
dataset_id = ds["id"]
ok(f"Dataset ID: {dataset_id}  ({ds['num_rows']} rows × {ds['num_columns']} cols)")

# ── 3. Preprocess ─────────────────────────────────────────────────────────────
step(3, "Preprocess dataset")
approved = [c["name"] for c in ds["columns"] if not c["is_sensitive"]]
r = client.post(f"/dataset/{dataset_id}/preprocess",
                json={"approved_columns": approved, "column_mapping": {}},
                timeout=30)
assert r.status_code == 200, fail(f"Preprocess returned {r.status_code}: {r.text}")
pp = r.json()
ok(f"Rows after preprocessing: {pp['rows_after']}  |  Missing handled: {list(pp['missing_handled'].keys())}")

# ── 4. Start generation (small run for speed) ─────────────────────────────────
step(4, "Start CTGAN generation (500 records, 50 epochs for speed)")
r = client.post("/generate", json={
    "dataset_id": dataset_id,
    "num_records": 500,
    "model": "CTGAN",
    "epochs": 50,
    "cohort": {
        "older_patients_pct": 40,
        "diabetic_pct": 30,
        "age_column": "Age",
        "diabetes_column": "Diabetes",
        "activity_column": "ActivityLevel",
    }
}, timeout=30)
assert r.status_code == 200, fail(f"Generate returned {r.status_code}: {r.text}")
gen_id = r.json()["generation_id"]
ok(f"Generation started: {gen_id}")

# ── 5. Poll until done ────────────────────────────────────────────────────────
step(5, "Polling generation status…")
start = time.time()
timeout_secs = 600  # 10 min max
last_msg = ""
while True:
    r = client.get(f"/generation/{gen_id}/status", timeout=10)
    s = r.json()
    if s["progress_message"] != last_msg:
        print(f"        [{s['progress']:3d}%] {s['progress_message']}")
        last_msg = s["progress_message"]
    if s["status"] == "done":
        elapsed = time.time() - start
        ok(f"Generation complete in {elapsed:.1f}s  |  model={s['model_used']}  |  records={s['num_generated']}")
        generation = s
        break
    if s["status"] == "error":
        fail(f"Generation error: {s['error_message']}")
    if time.time() - start > timeout_secs:
        fail(f"Generation timed out after {timeout_secs}s")
    time.sleep(3)

# ── 6. Validate ───────────────────────────────────────────────────────────────
step(6, "Statistical validation")
r = client.post(f"/validation/{gen_id}", timeout=60)
assert r.status_code == 200, fail(f"Validation returned {r.status_code}: {r.text}")
val = r.json()
scores = val["overall_scores"]
ok(f"Distribution similarity:   {scores['distribution_similarity']:.1f}%")
ok(f"Correlation preservation:  {scores['correlation_preservation']:.1f}%")
ok(f"KS pass rate:              {scores['ks_pass_rate']:.1f}%")
ok(f"Overall quality:           {scores['overall_quality']:.1f}%")

# Cohort accuracy
if generation.get("cohort_results"):
    cr = generation["cohort_results"]
    if "older_pct_requested" in cr:
        ok(f"Cohort: older requested={cr['older_pct_requested']}%  actual={cr['older_pct_actual']}%  diff={cr['older_pct_diff']}%")
    if "diabetic_pct_requested" in cr:
        ok(f"Cohort: diabetic requested={cr['diabetic_pct_requested']}%  actual={cr['diabetic_pct_actual']}%  diff={cr['diabetic_pct_diff']}%")

# ── 7. Privacy check ──────────────────────────────────────────────────────────
step(7, "Privacy risk checks")
r = client.post(f"/privacy/{gen_id}", timeout=60)
assert r.status_code == 200, fail(f"Privacy returned {r.status_code}: {r.text}")
priv = r.json()
ok(f"Exact duplicates:  {priv['exact_duplicates']}")
ok(f"Near duplicates:   {priv['near_duplicates']} (estimated)")
ok(f"Risk level:        {priv['risk_level']}")

# ── 8. Export ─────────────────────────────────────────────────────────────────
step(8, "Export CSV and XLSX")
r_csv = client.get(f"/export/{gen_id}/csv", timeout=30)
assert r_csv.status_code == 200, fail(f"CSV export returned {r_csv.status_code}")
ok(f"CSV: {len(r_csv.content):,} bytes")

r_xlsx = client.get(f"/export/{gen_id}/xlsx", timeout=30)
assert r_xlsx.status_code == 200, fail(f"XLSX export returned {r_xlsx.status_code}")
ok(f"XLSX: {len(r_xlsx.content):,} bytes")

# ── Done ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  END-TO-END TEST PASSED ✓")
print(f"  Generated {generation['num_generated']} synthetic records")
print(f"  Model: {generation['model_used']}")
print(f"  Overall quality score: {scores['overall_quality']:.1f}%")
print(f"  Privacy risk level: {priv['risk_level']}")
print("=" * 60)
