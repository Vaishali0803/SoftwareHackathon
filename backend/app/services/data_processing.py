"""
Data ingestion, profiling, privacy-aware column classification, and preprocessing.

Column classification uses four distinct categories:

  A. DIRECT PERSONAL IDENTIFIERS
     Directly identify a person (name, email, phone, SSN, MRN …).
     Excluded from modeling and flagged to the user.

  B. LONGITUDINAL LINKAGE KEYS
     Internal grouping keys that connect multiple observations to the same
     patient/subject (patient_id, subject_id, participant_id …).
     NOT a direct personal identifier — must NOT appear in the direct-identifier
     warning. Excluded from modeling features but retained before longitudinal
     analysis. Original values are never exposed in synthetic output.

  C. TEMPORAL COLUMNS
     Date/time fields used for ordering observations (visit_date, date,
     observation_date …). Excluded from generative modeling as raw strings;
     converted to ordinal integers internally.

  D. QUASI-IDENTIFIERS / SENSITIVE HEALTH ATTRIBUTES / CLINICAL COLUMNS
     Everything else — classified as before.
"""
import os
import json
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.database import DatasetRecord


# ── Normalisation helper ──────────────────────────────────────────────────────

def _normalise(col: str) -> str:
    """Lower-case, collapse non-alphanumeric runs → single underscore, strip edges."""
    s = col.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


# ─────────────────────────────────────────────────────────────────────────────
# A.  DIRECT PERSONAL IDENTIFIERS
#     People-facing identity information. Never used in modeling.
# ─────────────────────────────────────────────────────────────────────────────

_DIRECT_ID_EXACT: set = {
    # Names
    "name", "patient_name", "patientname", "full_name", "fullname",
    "first_name", "firstname", "last_name", "lastname",
    "patient_full_name", "patient_first_name", "patient_last_name",
    # Government / legal IDs
    "aadhaar", "aadhaar_number", "ssn", "social_security_number",
    "social_security", "passport_number", "passport",
    "driver_license", "drivers_license", "driver_s_license",
    "driving_license", "license_number",
    "national_id", "nationalid",
    # Healthcare record IDs (the physical record, not a grouping key)
    "medical_record_number", "mrn", "medical_record_no",
    "hospital_id", "hospitalid",
    # Contact
    "email", "email_address", "e_mail",
    "phone", "phone_number", "mobile", "mobile_number",
    "telephone", "telephone_number", "fax", "fax_number",
    # Address
    "address", "home_address", "street_address", "postal_address",
    "street", "street_name",
    # Financial
    "credit_card", "creditcard", "bank_account", "bankaccount",
    "insurance_id", "insuranceid", "nhs_number", "nhs",
    "health_id", "healthid",
    # Device / network
    "ip_address", "ip", "mac_address", "mac",
    # Biometric / media
    "photo", "photo_url", "image", "face_image",
    # Exact geolocation
    "latitude", "longitude", "gps",
}

# ─────────────────────────────────────────────────────────────────────────────
# B.  LONGITUDINAL LINKAGE KEYS
#     Internal grouping keys only. Checked BEFORE direct-identifier patterns
#     so "patient_id" is never mis-classified as a direct identifier.
# ─────────────────────────────────────────────────────────────────────────────

_LONGITUDINAL_KEY_EXACT: set = {
    # Patient / subject
    "patient_id", "patientid", "patient_identifier", "patientidentifier",
    "patient_key", "patientkey",
    "subject_id", "subjectid", "subject_key", "subjectkey",
    "participant_id", "participantid", "participant_key", "participantkey",
    "person_id", "personid", "person_key", "personkey",
    # Study / encounter grouping
    "study_id", "studyid", "study_subject_id",
    "encounter_subject_id", "encounter_id", "encounterid",
    "case_id", "caseid", "case_number",
    "cohort_id", "cohortid",
    "member_id", "memberid",
    "client_id", "clientid",
    "respondent_id", "respondentid",
    "record_id", "recordid",          # generic row-level grouping key
}

# Regex patterns also matched as longitudinal keys (applied only when the
# column does NOT already match a direct-identifier exact token).
_LONGITUDINAL_KEY_PATTERNS: List[str] = [
    r"^patient_?id$",
    r"^subject_?id$",
    r"^participant_?id$",
    r"^person_?id$",
    r"^case_?id$",
    r"^cohort_?id$",
    r"^encounter_?id$",
    r"^study_?id$",
    r"^member_?id$",
    r"^client_?id$",
    r".*_key$",          # anything ending in _key is likely a grouping key
]

# ─────────────────────────────────────────────────────────────────────────────
# C.  TEMPORAL COLUMNS
# ─────────────────────────────────────────────────────────────────────────────

_TEMPORAL_EXACT: set = {
    "date", "time", "datetime", "timestamp",
    "visit_date", "visitdate", "visit_time",
    "observation_date", "observationdate",
    "measurement_date", "measurementdate",
    "recorded_at", "recordedat",
    "encounter_date", "encounterdate",
    "admission_date", "admissiondate",
    "discharge_date", "dischargedate",
    "event_date", "eventdate",
    "appointment_date", "appointmentdate",
    "test_date", "testdate",
    "collection_date", "collectiondate",
    "sample_date", "sampledate",
    "created_at", "createdat", "updated_at", "updatedat",
    "entry_date", "entrydate",
}

_TEMPORAL_PATTERNS: List[str] = [
    r".*_date$",
    r".*_time$",
    r".*_at$",
    r"^date_.*",
    r"^time_.*",
]

# ─────────────────────────────────────────────────────────────────────────────
# D.  QUASI-IDENTIFIERS
# ─────────────────────────────────────────────────────────────────────────────

_QUASI_ID_EXACT: set = {
    "age", "exact_age",
    "gender", "sex",
    "date_of_birth", "dob", "birth_date", "birthdate", "dateofbirth",
    "zip_code", "zipcode", "zip", "postal_code", "postalcode", "postcode",
    "city", "county", "region", "state",
    "precise_geolocation", "geolocation",
    "race", "ethnicity",
}

# ─────────────────────────────────────────────────────────────────────────────
# E.  SENSITIVE HEALTH ATTRIBUTES ALLOWLIST
#     These must NEVER be mis-classified as identifiers.
#     Checked before any partial-pattern matching.
# ─────────────────────────────────────────────────────────────────────────────

_HEALTH_ALLOWLIST: set = {
    # Conditions
    "diabetes", "diagnosis", "disease", "condition", "medical_condition",
    "cancer", "hypertension", "obesity", "depression",
    # Vitals
    "blood_pressure", "systolic_bp", "diastolic_bp", "bp_systolic", "bp_diastolic",
    "bloodpressure", "systolicbp", "diastolicbp",
    "blood_pressure_systolic", "blood_pressure_diastolic",
    "bloodpressuresystolic", "bloodpressurediastolic",
    "heart_rate", "pulse", "temperature", "respiratory_rate",
    "glucose", "blood_glucose", "fasting_glucose",
    "bmi", "body_mass_index", "weight", "height",
    "cholesterol", "hdl", "ldl", "triglycerides", "a1c", "hba1c",
    "oxygen_saturation", "spo2",
    # Activity
    "activity_level", "activitylevel",
    "physical_activity", "physical_activity_minutes_week",
    "sedentary_minutes_day", "sedentary_hours",
    "exercise", "steps",
    # Medications
    "medication", "medications",
    "medication_adherence", "medicationadherence",
    "prescription_medication", "prescriptionmedication",
    "num_prescription_medications", "num_medications",
    "prescription", "prescriptions",
    "drug", "drugs", "treatment",
    "insulin", "dosage", "dose",
    # Pain / function
    "pain_score", "painscore", "pain",
    "functional_score", "disability_score",
    # Labs
    "lab_result", "lab_value", "test_result",
    "clinical_notes", "notes",
    # Scores
    "risk_score", "severity_score",
    # Lifestyle
    "smoking", "smoking_status", "smokingstatus", "alcohol", "substance_use",
    # Admin (non-identifying, non-temporal — temporal ones handled by temporal check)
    "encounter_type", "visit_type",
    "payer", "insurance_type",
}


# ─────────────────────────────────────────────────────────────────────────────
# Core classifier
# ─────────────────────────────────────────────────────────────────────────────

def _classify_column(col: str, series: pd.Series) -> str:
    """
    Classify a single column into one of:
      'longitudinal_key' | 'temporal' | 'direct_identifier' |
      'quasi_identifier' | 'sensitive_health' | 'clinical'

    Precedence (first match wins):
      1. Longitudinal key exact/pat → longitudinal_key  (before everything)
      2. Temporal exact/pattern     → temporal           (before health allowlist)
      3. Health allowlist           → sensitive_health   (prevent false positives)
      4. Direct identifier exact    → direct_identifier
      5. Quasi-identifier exact     → quasi_identifier
      6. Direct-identifier partial  → direct_identifier
      7. Email heuristic            → direct_identifier
      8. Default                    → clinical
    """
    norm = _normalise(col)

    # 1. Longitudinal linkage key — highest priority, must come before direct-id patterns
    if norm in _LONGITUDINAL_KEY_EXACT:
        return "longitudinal_key"
    for pat in _LONGITUDINAL_KEY_PATTERNS:
        if re.search(pat, norm):
            return "longitudinal_key"

    # 2. Temporal column — checked before health allowlist so visit_date, admission_date
    #    etc. are not incorrectly captured by the health allowlist
    if norm in _TEMPORAL_EXACT:
        return "temporal"
    for pat in _TEMPORAL_PATTERNS:
        if re.search(pat, norm):
            return "temporal"

    # 3. Health allowlist — never classify health data as an identifier
    if norm in _HEALTH_ALLOWLIST:
        return "sensitive_health"

    # 4. Direct identifier — exact
    if norm in _DIRECT_ID_EXACT:
        return "direct_identifier"

    # 5. Quasi-identifier — exact
    if norm in _QUASI_ID_EXACT:
        return "quasi_identifier"

    # 6. Partial-pattern direct identifiers (residual _number columns, patient names)
    _PARTIAL_DIRECT = [
        r"_?number$",
        r"^patient_?name$",
        r"^patient_?identifier$",
    ]
    for pat in _PARTIAL_DIRECT:
        if re.search(pat, norm):
            return "direct_identifier"

    # 7. High-cardinality email heuristic
    if series.dtype == object:
        n = len(series.dropna())
        if n > 0 and series.nunique() / n > 0.8:
            sample = series.dropna().head(10).astype(str).tolist()
            if any("@" in v for v in sample):
                return "direct_identifier"

    return "clinical"


# ─────────────────────────────────────────────────────────────────────────────
# Public classification API
# ─────────────────────────────────────────────────────────────────────────────

def classify_all_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Classify every column in *df* and return a structured dict:

    {
        "direct_identifiers":          [...],   # flagged as personal identifiers
        "longitudinal_linkage_keys":   [...],   # grouping keys; excluded from modeling
        "temporal_columns":            [...],   # date/time fields
        "quasi_identifiers":           [...],   # informational; not auto-excluded
        "sensitive_health_attributes": [...],   # medical; included in modeling
        "clinical":                    [...],   # normal variables
        "excluded_from_modeling":      [...],   # direct_identifiers + linkage_keys
    }
    """
    result: Dict[str, List[str]] = {
        "direct_identifiers":          [],
        "longitudinal_linkage_keys":   [],
        "temporal_columns":            [],
        "quasi_identifiers":           [],
        "sensitive_health_attributes": [],
        "clinical":                    [],
    }

    for col in df.columns:
        cat = _classify_column(col, df[col])
        mapping = {
            "direct_identifier": "direct_identifiers",
            "longitudinal_key":  "longitudinal_linkage_keys",
            "temporal":          "temporal_columns",
            "quasi_identifier":  "quasi_identifiers",
            "sensitive_health":  "sensitive_health_attributes",
            "clinical":          "clinical",
        }
        result[mapping[cat]].append(col)

    # Columns that must never enter the generative model
    result["excluded_from_modeling"] = (
        result["direct_identifiers"] + result["longitudinal_linkage_keys"]
    )
    return result


def detect_sensitive_columns(df: pd.DataFrame) -> List[str]:
    """
    Backward-compatible wrapper.
    Returns ONLY direct personal identifiers.
    Longitudinal linkage keys are NOT included.
    """
    return classify_all_columns(df)["direct_identifiers"]


# ─────────────────────────────────────────────────────────────────────────────
# Longitudinal structure detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_longitudinal_structure(
    df: pd.DataFrame,
    classification: Dict[str, List[str]],
) -> Dict:
    """
    Determine whether the dataset is longitudinal (multiple observations per
    subject over time) or cross-sectional (one observation per subject).

    Rules:
      1. A longitudinal linkage key must exist.
      2. A temporal column must exist (or at least repeated linkage-key values).
      3. At least one linkage-key value must appear more than once.

    Returns a dict with:
      is_longitudinal:      bool
      dataset_type:         "longitudinal" | "cross_sectional" | "unknown"
      linkage_key:          str | None    — the primary linkage column used
      temporal_column:      str | None    — the primary date/time column used
      unique_subjects:      int           — number of unique linkage-key values
      total_observations:   int
      avg_obs_per_subject:  float
      max_obs_per_subject:  int
      repeated_subjects:    int           — subjects with > 1 observation
    """
    info: Dict = {
        "is_longitudinal":     False,
        "dataset_type":        "unknown",
        "linkage_key":         None,
        "temporal_column":     None,
        "unique_subjects":     0,
        "total_observations":  len(df),
        "avg_obs_per_subject": 0.0,
        "max_obs_per_subject": 0,
        "repeated_subjects":   0,
    }

    linkage_keys = classification.get("longitudinal_linkage_keys", [])
    temporal_cols = classification.get("temporal_columns", [])

    if not linkage_keys:
        info["dataset_type"] = "cross_sectional"
        return info

    # Use first detected linkage key
    key_col = linkage_keys[0]
    info["linkage_key"] = key_col

    key_values = df[key_col].dropna()
    if len(key_values) == 0:
        info["dataset_type"] = "cross_sectional"
        return info

    counts = key_values.value_counts()
    unique_subjects   = int(len(counts))
    repeated_subjects = int((counts > 1).sum())
    max_obs           = int(counts.max())
    avg_obs           = round(float(counts.mean()), 2)

    info["unique_subjects"]     = unique_subjects
    info["avg_obs_per_subject"] = avg_obs
    info["max_obs_per_subject"] = max_obs
    info["repeated_subjects"]   = repeated_subjects

    if repeated_subjects > 0:
        info["is_longitudinal"] = True
        info["dataset_type"]    = "longitudinal"
        # Pick primary temporal column if any
        if temporal_cols:
            info["temporal_column"] = temporal_cols[0]
    else:
        info["dataset_type"] = "cross_sectional"

    return info


# ─────────────────────────────────────────────────────────────────────────────
# Column type inference
# ─────────────────────────────────────────────────────────────────────────────

def infer_column_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if series.dtype == object:
        sample = series.dropna().head(20).astype(str)
        try:
            parsed = pd.to_datetime(sample, errors="coerce")
            if parsed.notna().mean() > 0.8:
                return "datetime"
        except Exception:
            pass
    return "categorical"


# ─────────────────────────────────────────────────────────────────────────────
# File loading
# ─────────────────────────────────────────────────────────────────────────────

def load_file(filepath: str) -> pd.DataFrame:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        return pd.read_csv(filepath, low_memory=False)
    elif ext in (".xlsx", ".xls"):
        return pd.read_excel(filepath, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported file format: {ext}")


# ─────────────────────────────────────────────────────────────────────────────
# Dataset profiling
# ─────────────────────────────────────────────────────────────────────────────

def profile_dataset(df: pd.DataFrame) -> List[Dict]:
    columns = []
    for col in df.columns:
        series = df[col]
        missing = int(series.isna().sum())
        total   = len(series)
        unique  = int(series.nunique(dropna=True))
        dtype   = infer_column_type(series)
        samples = series.dropna().head(5).tolist()
        samples = [str(s) if not isinstance(s, (int, float, bool)) else s for s in samples]
        columns.append({
            "name":          col,
            "dtype":         dtype,
            "missing_count": missing,
            "missing_pct":   round(missing / total * 100, 2) if total else 0,
            "unique_count":  unique,
            "sample_values": samples,
            "is_sensitive":  False,   # filled in after classification
        })
    return columns


# ─────────────────────────────────────────────────────────────────────────────
# Upload helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_upload(file_bytes: bytes, original_filename: str) -> Tuple[str, str]:
    ds_id      = str(uuid.uuid4())
    ext        = os.path.splitext(original_filename)[1].lower()
    saved_name = f"{ds_id}{ext}"
    saved_path = os.path.join(settings.UPLOAD_DIR, saved_name)
    with open(saved_path, "wb") as f:
        f.write(file_bytes)
    return ds_id, saved_path


def create_dataset_record(
    db: Session,
    ds_id: str,
    original_filename: str,
    saved_path: str,
    df: pd.DataFrame,
) -> DatasetRecord:
    col_profiles   = profile_dataset(df)
    classification = classify_all_columns(df)
    direct_ids     = classification["direct_identifiers"]

    # is_sensitive = direct identifier only (linkage keys get their own badge)
    for cp in col_profiles:
        cp["is_sensitive"] = cp["name"] in direct_ids

    record = DatasetRecord(
        id=ds_id,
        filename=os.path.basename(saved_path),
        original_filename=original_filename,
        num_rows=len(df),
        num_columns=len(df.columns),
        column_names=json.dumps(list(df.columns)),
        column_types=json.dumps({cp["name"]: cp["dtype"] for cp in col_profiles}),
        missing_counts=json.dumps({cp["name"]: cp["missing_count"] for cp in col_profiles}),
        unique_counts=json.dumps({cp["name"]: cp["unique_count"] for cp in col_profiles}),
        sensitive_columns=json.dumps(direct_ids),   # direct identifiers only
        approved_columns=json.dumps([]),
        status="uploaded",
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessing
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_dataset(
    df: pd.DataFrame,
    approved_columns: List[str],
    column_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Clean and prepare the dataset for synthetic generation.
    approved_columns must already exclude direct_identifiers and
    longitudinal_linkage_keys (caller's responsibility).
    Returns (cleaned_df, summary).
    """
    summary: Dict = {}
    rows_before = len(df)

    df      = df[approved_columns].copy()
    excluded = [c for c in df.columns if c not in approved_columns]

    if column_mapping:
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    dupes_before = df.duplicated().sum()
    df = df.drop_duplicates()
    summary["duplicates_removed"] = int(dupes_before)

    missing_handled: Dict[str, int] = {}

    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        if n_missing == 0:
            continue
        missing_handled[col] = n_missing

        dtype = infer_column_type(df[col])
        if dtype in ("integer", "float"):
            df[col] = df[col].fillna(df[col].median())
        elif dtype == "datetime":
            df[col] = df[col].ffill().bfill()
        else:
            mode_vals = df[col].mode()
            fill_val  = mode_vals.iloc[0] if not mode_vals.empty else "Unknown"
            df[col] = df[col].fillna(fill_val)

    # Cast boolean-like object columns
    for col in df.columns:
        if df[col].dtype == object:
            lower_vals = df[col].astype(str).str.lower().unique()
            if set(lower_vals).issubset({"true", "false", "yes", "no", "1", "0", "nan"}):
                df[col] = df[col].astype(str).str.lower().map(
                    {"true": True, "false": False,
                     "yes":  True, "no":   False,
                     "1":    True, "0":    False}
                )

    # Parse date-like string columns
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna().head(30).astype(str)
            try:
                parsed = pd.to_datetime(sample, errors="coerce")
                if parsed.notna().mean() > 0.9:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                pass

    rows_after = len(df)
    summary["rows_before"]       = rows_before
    summary["rows_after"]        = rows_after
    summary["missing_handled"]   = missing_handled
    summary["columns_excluded"]  = excluded
    summary["columns_included"]  = list(df.columns)
    summary["duplicates_removed"] = int(dupes_before)

    return df, summary


def save_preprocessed(df: pd.DataFrame, dataset_id: str) -> str:
    path = os.path.join(settings.UPLOAD_DIR, f"{dataset_id}_preprocessed.csv")
    df.to_csv(path, index=False)
    return path
