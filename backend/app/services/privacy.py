"""
Prototype-level privacy risk checks.

IMPORTANT: These checks are heuristic indicators for a research prototype.
They do NOT constitute a formal privacy audit or guarantee of anonymity.
Synthetic data privacy depends on the generation method, source data,
model configuration, and evaluation methodology.
"""
import json
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sqlalchemy.orm import Session

from app.database import PrivacyRecord
from app.utils.ids import new_id

DISCLAIMER = (
    "These checks are prototype-level risk indicators only. "
    "Synthetic data privacy depends on the generation method, source data, "
    "model configuration, and evaluation methodology. "
    "This report does NOT constitute a formal privacy audit or guarantee of anonymity."
)


def _encode_for_distance(df: pd.DataFrame) -> np.ndarray:
    """Encode mixed-type DataFrame to numeric matrix for distance computation."""
    encoded = pd.DataFrame(index=df.index)
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            s = df[col].fillna(df[col].median() if df[col].notna().any() else 0)
            rng = s.max() - s.min()
            encoded[col] = (s - s.min()) / rng if rng > 0 else 0.0
        else:
            le = LabelEncoder()
            s = df[col].fillna("__missing__").astype(str)
            enc = le.fit_transform(s).astype(float)
            n_classes = len(le.classes_)
            encoded[col] = enc / n_classes if n_classes > 0 else 0.0
    return encoded.values.astype(np.float32)


def check_exact_duplicates(source_df: pd.DataFrame, synth_df: pd.DataFrame) -> int:
    """Count synthetic rows that are exact duplicates of source rows."""
    common = [c for c in source_df.columns if c in synth_df.columns]
    if not common:
        return 0
    src_set = set(source_df[common].astype(str).apply(tuple, axis=1))
    syn_tuples = synth_df[common].astype(str).apply(tuple, axis=1)
    return int(syn_tuples.isin(src_set).sum())


def check_near_duplicates(
    source_df: pd.DataFrame,
    synth_df: pd.DataFrame,
    threshold: float = 0.05,
    sample_size: int = 500,
) -> Tuple[int, List[Dict]]:
    """
    Approximate near-duplicate check using L2 distance on encoded features.
    Samples up to `sample_size` rows from each df to keep runtime manageable.

    Returns (count_of_near_duplicates, sample_details).
    """
    common = [c for c in source_df.columns if c in synth_df.columns]
    if not common or len(source_df) == 0 or len(synth_df) == 0:
        return 0, []

    src_sample = source_df[common].sample(
        n=min(sample_size, len(source_df)), random_state=42
    ).reset_index(drop=True)
    syn_sample = synth_df[common].sample(
        n=min(sample_size, len(synth_df)), random_state=42
    ).reset_index(drop=True)

    try:
        src_enc = _encode_for_distance(src_sample)
        syn_enc = _encode_for_distance(syn_sample)
        n_features = src_enc.shape[1]
    except Exception:
        return 0, []

    near_dup_count = 0
    details = []

    # For each synthetic record find nearest source record
    for i, syn_row in enumerate(syn_enc):
        diffs = src_enc - syn_row
        dists = np.sqrt((diffs ** 2).sum(axis=1))
        min_dist = float(dists.min())
        if min_dist < threshold:
            near_dup_count += 1
            if len(details) < 10:  # only keep first 10 for report
                details.append({
                    "synth_idx": i,
                    "nearest_source_idx": int(dists.argmin()),
                    "distance": round(min_dist, 4),
                })

    # Scale to full synthetic size
    sample_ratio = len(synth_df) / len(syn_sample) if len(syn_sample) > 0 else 1
    estimated_total = int(round(near_dup_count * sample_ratio))
    return estimated_total, details


def assess_risk_level(
    exact_count: int,
    near_count: int,
    total_synthetic: int,
    total_source: int,
) -> str:
    if total_synthetic == 0:
        return "Unknown"
    exact_rate = exact_count / total_synthetic
    near_rate = near_count / total_synthetic

    if exact_rate > 0.01 or near_rate > 0.05:
        return "High"
    elif exact_rate > 0.001 or near_rate > 0.02:
        return "Medium"
    else:
        return "Low"


def run_privacy_checks(
    generation_id: str,
    dataset_id: str,
    source_path: str,
    synthetic_path: str,
    db: Session,
) -> PrivacyRecord:
    source_df = pd.read_csv(source_path)
    synth_df = pd.read_csv(synthetic_path)

    exact = check_exact_duplicates(source_df, synth_df)
    near, near_details = check_near_duplicates(source_df, synth_df)

    risk = assess_risk_level(exact, near, len(synth_df), len(source_df))

    exact_rate = round(exact / len(synth_df) * 100, 4) if len(synth_df) else 0
    near_rate = round(near / len(synth_df) * 100, 4) if len(synth_df) else 0

    details = {
        "disclaimer": DISCLAIMER,
        "exact_duplicate_rate_pct": exact_rate,
        "near_duplicate_rate_pct": near_rate,
        "near_duplicate_threshold": 0.05,
        "near_duplicate_sample_details": near_details,
        "total_source_records": len(source_df),
        "total_synthetic_records": len(synth_df),
        "risk_interpretation": {
            "Low": "Exact and near-duplicate rates are within acceptable prototype thresholds.",
            "Medium": "Some similarity detected. Review generation parameters and source data carefully.",
            "High": "High similarity detected. The synthesizer may be memorising source records. "
                    "Review with a privacy expert before using this data.",
        }.get(risk, ""),
        "note": (
            "Near-duplicate detection uses a sampled L2 distance heuristic on normalised features. "
            "It is not a formal re-identification risk assessment."
        ),
    }

    priv_id = new_id()
    record = PrivacyRecord(
        id=priv_id,
        generation_id=generation_id,
        dataset_id=dataset_id,
        exact_duplicates=exact,
        near_duplicates=near,
        risk_level=risk,
        details=json.dumps(details),
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
