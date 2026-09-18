"""
Privacy classification + longitudinal detection tests.
Run: python test_privacy.py

Tests cover:
  - All four column categories
  - Longitudinal linkage keys NEVER appear in direct_identifiers
  - Longitudinal structure detection (is_longitudinal / cross-sectional)
  - Regression: existing cross-sectional demo columns unaffected
"""
import sys
sys.path.insert(0, ".")

import pandas as pd
import numpy as np
from app.services.data_processing import classify_all_columns, detect_longitudinal_structure

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        print(f"  PASS  {label}")
        PASS += 1
    else:
        print(f"  FAIL  {label}  {detail}")
        FAIL += 1


# =============================================================================
# TEST 1 — patient_name is a direct identifier; prescription_medication is not
# =============================================================================
print("\nTEST 1: patient_name + age + diabetes + prescription_medication")
df1 = pd.DataFrame(columns=["patient_name", "age", "diabetes", "prescription_medication"])
c1 = classify_all_columns(df1)

check("patient_name -> direct_identifier",
      "patient_name" in c1["direct_identifiers"])
check("age -> quasi_identifier",
      "age" in c1["quasi_identifiers"])
check("diabetes -> sensitive_health",
      "diabetes" in c1["sensitive_health_attributes"])
check("prescription_medication -> sensitive_health",
      "prescription_medication" in c1["sensitive_health_attributes"])
check("prescription_medication NOT in direct_identifiers",
      "prescription_medication" not in c1["direct_identifiers"])
check("prescription_medication NOT in excluded_from_modeling",
      "prescription_medication" not in c1["excluded_from_modeling"])

# =============================================================================
# TEST 2 — patient_id, email, phone are identifiers; glucose, BP, medication are not
# =============================================================================
print("\nTEST 2: patient_id + email + phone + glucose + blood_pressure + medication")
df2 = pd.DataFrame(columns=["patient_id", "email", "phone", "glucose", "blood_pressure", "medication"])
c2 = classify_all_columns(df2)

# patient_id is a LONGITUDINAL LINKAGE KEY — not a direct identifier
check("patient_id -> longitudinal_linkage_key",
      "patient_id" in c2["longitudinal_linkage_keys"])
check("patient_id NOT in direct_identifiers",
      "patient_id" not in c2["direct_identifiers"])
check("patient_id in excluded_from_modeling (linkage keys are excluded)",
      "patient_id" in c2["excluded_from_modeling"])

# Real direct identifiers
check("email -> direct_identifier",
      "email" in c2["direct_identifiers"])
check("phone -> direct_identifier",
      "phone" in c2["direct_identifiers"])

# Clinical fields must NOT be identifiers
check("glucose NOT in direct_identifiers",
      "glucose" not in c2["direct_identifiers"])
check("blood_pressure NOT in direct_identifiers",
      "blood_pressure" not in c2["direct_identifiers"])
check("medication NOT in direct_identifiers",
      "medication" not in c2["direct_identifiers"])
check("glucose -> sensitive_health",
      "glucose" in c2["sensitive_health_attributes"])
check("medication -> sensitive_health",
      "medication" in c2["sensitive_health_attributes"])

# =============================================================================
# TEST 3 — current healthcare dataset: no direct identifiers expected
# =============================================================================
print("\nTEST 3: Current healthcare dataset (age, gender, diabetes, systolic_bp ...)")
cols3 = [
    "age", "gender", "diabetes", "systolic_bp", "diastolic_bp",
    "physical_activity_minutes_week", "sedentary_minutes_day",
    "prescription_medication", "num_prescription_medications",
]
df3 = pd.DataFrame(columns=cols3)
c3 = classify_all_columns(df3)

check("direct_identifiers is EMPTY",
      c3["direct_identifiers"] == [],
      f"got: {c3['direct_identifiers']}")
check("prescription_medication NOT in direct_identifiers",
      "prescription_medication" not in c3["direct_identifiers"])
check("num_prescription_medications NOT in direct_identifiers",
      "num_prescription_medications" not in c3["direct_identifiers"])
check("prescription_medication -> sensitive_health",
      "prescription_medication" in c3["sensitive_health_attributes"])
check("num_prescription_medications -> sensitive_health",
      "num_prescription_medications" in c3["sensitive_health_attributes"])
check("diabetes -> sensitive_health",
      "diabetes" in c3["sensitive_health_attributes"])
check("systolic_bp -> sensitive_health",
      "systolic_bp" in c3["sensitive_health_attributes"])
check("diastolic_bp -> sensitive_health",
      "diastolic_bp" in c3["sensitive_health_attributes"])
check("age -> quasi_identifier",
      "age" in c3["quasi_identifiers"])
check("gender -> quasi_identifier",
      "gender" in c3["quasi_identifiers"])
check("excluded_from_modeling is EMPTY",
      c3["excluded_from_modeling"] == [],
      f"got: {c3['excluded_from_modeling']}")

# =============================================================================
# TEST 4 — longitudinal detection: patient_id + date + clinical cols
# =============================================================================
print("\nTEST 4: Longitudinal detection — patient_id, date, bp, pain_score, diabetes")
cols4 = ["patient_id", "date", "age", "diabetes", "blood_pressure", "pain_score"]
df4 = pd.DataFrame(columns=cols4)
c4 = classify_all_columns(df4)

check("patient_id -> longitudinal_linkage_key",
      "patient_id" in c4["longitudinal_linkage_keys"])
check("patient_id NOT in direct_identifiers",
      "patient_id" not in c4["direct_identifiers"])
check("date -> temporal_column",
      "date" in c4["temporal_columns"])
check("age -> quasi_identifier",
      "age" in c4["quasi_identifiers"])
check("diabetes -> sensitive_health",
      "diabetes" in c4["sensitive_health_attributes"])
check("blood_pressure -> sensitive_health",
      "blood_pressure" in c4["sensitive_health_attributes"])
check("pain_score -> sensitive_health",
      "pain_score" in c4["sensitive_health_attributes"])
check("direct_identifiers is EMPTY (no real PII)",
      c4["direct_identifiers"] == [],
      f"got: {c4['direct_identifiers']}")

# Build data for longitudinal structure detection
rows_longitudinal = {
    "patient_id": ["P001","P001","P001","P002","P002"],
    "date":       ["2025-01-01","2025-02-01","2025-03-01","2025-01-01","2025-02-01"],
    "blood_pressure": [145,142,138,130,128],
}
df4_data = pd.DataFrame(rows_longitudinal)
c4_data  = classify_all_columns(df4_data)
lon4     = detect_longitudinal_structure(df4_data, c4_data)

check("is_longitudinal = True (repeated patient_id values)",
      lon4["is_longitudinal"] is True)
check("dataset_type = longitudinal",
      lon4["dataset_type"] == "longitudinal")
check("linkage_key = patient_id",
      lon4["linkage_key"] == "patient_id")
check("temporal_column = date",
      lon4["temporal_column"] == "date")
check("unique_subjects = 2",
      lon4["unique_subjects"] == 2)
check("repeated_subjects = 2 (both patients have >1 obs)",
      lon4["repeated_subjects"] == 2)

# =============================================================================
# TEST 5 — cross-sectional: patient_id exists but each appears only once
# =============================================================================
print("\nTEST 5: Cross-sectional — patient_id present but no repeated observations")
df5_cross = pd.DataFrame({
    "patient_id": ["P001", "P002", "P003"],
    "date":       ["2025-01-01", "2025-01-02", "2025-01-03"],
    "age":        [45, 62, 38],
    "diabetes":   [True, False, True],
})
c5   = classify_all_columns(df5_cross)
lon5 = detect_longitudinal_structure(df5_cross, c5)

check("patient_id -> longitudinal_linkage_key (not direct identifier)",
      "patient_id" in c5["longitudinal_linkage_keys"])
check("is_longitudinal = False (each patient appears once)",
      lon5["is_longitudinal"] is False)
check("dataset_type = cross_sectional",
      lon5["dataset_type"] == "cross_sectional")
check("unique_subjects = 3",
      lon5["unique_subjects"] == 3)
check("repeated_subjects = 0",
      lon5["repeated_subjects"] == 0)

# =============================================================================
# TEST 6 — patient_name (direct identifier) + patient_id (linkage key) coexist
# =============================================================================
print("\nTEST 6: patient_name + patient_id + date + diabetes + blood_pressure")
df6 = pd.DataFrame(columns=["patient_name", "patient_id", "date", "diabetes", "blood_pressure"])
c6  = classify_all_columns(df6)

check("patient_name -> direct_identifier",
      "patient_name" in c6["direct_identifiers"])
check("patient_id -> longitudinal_linkage_key (NOT direct_identifier)",
      "patient_id" in c6["longitudinal_linkage_keys"])
check("patient_id NOT in direct_identifiers",
      "patient_id" not in c6["direct_identifiers"])
check("date -> temporal_column",
      "date" in c6["temporal_columns"])
check("diabetes -> sensitive_health",
      "diabetes" in c6["sensitive_health_attributes"])
check("blood_pressure -> sensitive_health",
      "blood_pressure" in c6["sensitive_health_attributes"])
check("Only patient_name in direct_identifiers",
      set(c6["direct_identifiers"]) == {"patient_name"})
check("excluded_from_modeling contains patient_name AND patient_id",
      "patient_name" in c6["excluded_from_modeling"] and
      "patient_id"   in c6["excluded_from_modeling"])

# =============================================================================
# TEST 7 — demo dataset columns (regression: no false positives)
# =============================================================================
print("\nTEST 7: Demo dataset columns — regression")
demo_cols = [
    "Age", "Sex", "Diabetes", "BloodPressureSystolic", "BloodPressureDiastolic",
    "ActivityLevel", "MedicationAdherence", "PainScore", "BMI", "HbA1c",
    "SmokingStatus", "VisitDate",
]
df7 = pd.DataFrame(columns=demo_cols)
c7  = classify_all_columns(df7)

check("No direct identifiers in demo dataset",
      c7["direct_identifiers"] == [],
      f"got: {c7['direct_identifiers']}")
check("No longitudinal linkage keys in demo dataset",
      c7["longitudinal_linkage_keys"] == [],
      f"got: {c7['longitudinal_linkage_keys']}")
check("MedicationAdherence -> sensitive_health",
      "MedicationAdherence" in c7["sensitive_health_attributes"])
check("Diabetes -> sensitive_health",
      "Diabetes" in c7["sensitive_health_attributes"])
check("PainScore -> sensitive_health",
      "PainScore" in c7["sensitive_health_attributes"])
check("excluded_from_modeling is EMPTY",
      c7["excluded_from_modeling"] == [],
      f"got: {c7['excluded_from_modeling']}")

# =============================================================================
# TEST 8 — various linkage key spellings
# =============================================================================
print("\nTEST 8: Linkage key spelling variants")
variants = [
    "subject_id", "subjectid", "participant_id", "participantid",
    "person_id", "personid", "study_id", "case_id", "cohort_id",
    "encounter_id", "member_id", "client_id",
]
df8 = pd.DataFrame(columns=variants)
c8  = classify_all_columns(df8)

for v in variants:
    check(f"{v} -> longitudinal_linkage_key",
          v in c8["longitudinal_linkage_keys"])
check("None of the variants in direct_identifiers",
      all(v not in c8["direct_identifiers"] for v in variants),
      f"unexpected: {[v for v in variants if v in c8['direct_identifiers']]}")

# =============================================================================
# Summary
# =============================================================================
print(f"\n{'='*50}")
print(f"  Results:  {PASS} passed,  {FAIL} failed")
if FAIL == 0:
    print("  ALL TESTS PASSED")
else:
    print("  SOME TESTS FAILED")
    sys.exit(1)
print("="*50)
