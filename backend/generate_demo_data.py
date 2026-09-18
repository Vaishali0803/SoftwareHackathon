"""
Generates the demo dataset: data/demo_patient_data.csv
Run once before starting the server: python generate_demo_data.py

This is SYNTHETIC demo data generated for testing purposes.
It does NOT represent real patients or hospital records.
"""
import os
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
N = 2000  # rows — large enough for CTGAN, fast enough locally

os.makedirs("data", exist_ok=True)

# ── Demographics ───────────────────────────────────────────────────────────────
age = rng.integers(18, 90, size=N)
sex = rng.choice(["Male", "Female", "Other"], size=N, p=[0.48, 0.48, 0.04])

# Diabetes: correlated with age
diabetes_prob = np.where(age >= 60, 0.35, np.where(age >= 40, 0.18, 0.06))
diabetes = rng.binomial(1, diabetes_prob).astype(bool)

# ── Activity level: lower for older / diabetic ────────────────────────────────
activity_raw = rng.normal(
    loc=np.where(age >= 60, 1.2, np.where(diabetes, 1.5, 2.2)),
    scale=0.6,
)
activity_bins = np.digitize(activity_raw, bins=[1.0, 1.8]) 
activity_labels = np.array(["Low", "Medium", "High"])
activity_level = activity_labels[np.clip(activity_bins, 0, 2)]

# ── Blood pressure: correlated with age + diabetes ───────────────────────────
bp_systolic = (
    100
    + 0.4 * age
    + 10 * diabetes.astype(int)
    + rng.normal(0, 10, size=N)
).round(1)
bp_systolic = np.clip(bp_systolic, 80, 200)

bp_diastolic = (
    60
    + 0.15 * age
    + 5 * diabetes.astype(int)
    + rng.normal(0, 6, size=N)
).round(1)
bp_diastolic = np.clip(bp_diastolic, 40, 130)

# ── Pain score 0-10: higher for older, diabetic, low activity ─────────────────
pain_base = (
    1.5
    + 0.03 * (age - 18)
    + 1.5 * diabetes.astype(int)
    + np.where(activity_level == "Low", 1.8, np.where(activity_level == "High", -0.8, 0.4))
    + rng.normal(0, 1.2, size=N)
)
pain_score = np.clip(pain_base, 0, 10).round(1)

# ── Medication adherence 0-100% ───────────────────────────────────────────────
med_adherence = (
    80
    - 0.1 * pain_score * 5
    + rng.normal(0, 12, size=N)
).round(1)
med_adherence = np.clip(med_adherence, 0, 100)

# ── BMI ───────────────────────────────────────────────────────────────────────
bmi = (
    22
    + 0.05 * age
    + 3 * diabetes.astype(int)
    + rng.normal(0, 3.5, size=N)
).round(1)
bmi = np.clip(bmi, 14, 55)

# ── Visit dates (2022-01-01 to 2024-12-31) ───────────────────────────────────
start_date = pd.Timestamp("2022-01-01")
end_date = pd.Timestamp("2024-12-31")
days_range = (end_date - start_date).days
visit_dates = [
    (start_date + pd.Timedelta(days=int(d))).strftime("%Y-%m-%d")
    for d in rng.integers(0, days_range, size=N)
]

# ── Smoking status ────────────────────────────────────────────────────────────
smoking_prob = np.where(age >= 50, 0.25, np.where(age >= 30, 0.18, 0.10))
smoking = rng.binomial(1, smoking_prob).astype(bool)
smoking_status = np.where(smoking, "Smoker", "Non-Smoker")

# ── HbA1c (diabetes biomarker) ────────────────────────────────────────────────
hba1c = (
    5.0
    + 1.8 * diabetes.astype(int)
    + 0.01 * age
    + rng.normal(0, 0.5, size=N)
).round(2)
hba1c = np.clip(hba1c, 4.0, 12.0)

# ── Assemble ──────────────────────────────────────────────────────────────────
df = pd.DataFrame({
    "Age": age,
    "Sex": sex,
    "Diabetes": diabetes,
    "BloodPressureSystolic": bp_systolic,
    "BloodPressureDiastolic": bp_diastolic,
    "ActivityLevel": activity_level,
    "MedicationAdherence": med_adherence,
    "PainScore": pain_score,
    "BMI": bmi,
    "HbA1c": hba1c,
    "SmokingStatus": smoking_status,
    "VisitDate": visit_dates,
})

# Introduce ~3% missing values to make preprocessing realistic
for col in ["BloodPressureSystolic", "BloodPressureDiastolic", "MedicationAdherence",
            "PainScore", "BMI", "HbA1c"]:
    mask = rng.random(N) < 0.03
    df.loc[mask, col] = None

out_path = os.path.join("data", "demo_patient_data.csv")
df.to_csv(out_path, index=False)
print(f"Demo dataset written to {out_path}  ({N} rows, {len(df.columns)} columns)")
print("NOTE: This is synthetic demo data and does NOT represent real patient records.")
