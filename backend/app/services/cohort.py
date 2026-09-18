"""
Post-generation cohort resampling to satisfy researcher-specified cohort targets.
Does NOT simply overwrite values — it resamples from generated data while
preserving learned relationships.
"""
from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np


def _col_exists(df: pd.DataFrame, col: Optional[str]) -> Optional[str]:
    if col is None:
        return None
    if col in df.columns:
        return col
    lower_map = {c.lower(): c for c in df.columns}
    return lower_map.get(col.lower())


def apply_cohort_requirements(
    synth_df: pd.DataFrame,
    source_df: pd.DataFrame,
    num_records: int,
    cohort_config: Dict,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Resample synthetic records to approximate the requested cohort distribution.

    Strategy:
    1. Partition synthetic pool by cohort criteria.
    2. Calculate desired counts per stratum.
    3. Sample with replacement from each stratum.
    4. Shuffle and return.

    Returns (resampled_df, results_summary).
    """
    results = {}
    rng = np.random.default_rng(42)

    older_pct = cohort_config.get("older_patients_pct")
    diabetic_pct = cohort_config.get("diabetic_pct")
    activity_dist = cohort_config.get("activity_distribution")
    age_col = _col_exists(synth_df, cohort_config.get("age_column", "Age"))
    diabetes_col = _col_exists(synth_df, cohort_config.get("diabetes_column", "Diabetes"))
    activity_col = _col_exists(synth_df, cohort_config.get("activity_column", "ActivityLevel"))

    # If no valid cohort spec, just sample num_records from synthetic pool
    has_spec = any([
        older_pct is not None and age_col is not None,
        diabetic_pct is not None and diabetes_col is not None,
        activity_dist is not None and activity_col is not None,
    ])

    if not has_spec:
        df = synth_df.sample(n=min(num_records, len(synth_df)), replace=True, random_state=42)
        return df.reset_index(drop=True), {"note": "No cohort constraints applied"}

    pool = synth_df.copy()

    # ── Age cohort ─────────────────────────────────────────────────────────────
    if older_pct is not None and age_col is not None:
        age_threshold = 60
        pool["__is_older__"] = pool[age_col] >= age_threshold

    # ── Diabetes cohort ────────────────────────────────────────────────────────
    if diabetic_pct is not None and diabetes_col is not None:
        col_vals = pool[diabetes_col].astype(str).str.lower()
        pool["__is_diabetic__"] = col_vals.isin(["1", "true", "yes", "1.0"])

    # Build composite strata
    strata_cols = []
    if "__is_older__" in pool.columns:
        strata_cols.append("__is_older__")
    if "__is_diabetic__" in pool.columns:
        strata_cols.append("__is_diabetic__")

    if strata_cols:
        # Desired proportions matrix
        desired = {}
        if "__is_older__" in strata_cols and "__is_diabetic__" in strata_cols:
            op = (older_pct or 0) / 100
            dp = (diabetic_pct or 0) / 100
            desired[(True, True)]   = op * dp
            desired[(True, False)]  = op * (1 - dp)
            desired[(False, True)]  = (1 - op) * dp
            desired[(False, False)] = (1 - op) * (1 - dp)
        elif "__is_older__" in strata_cols:
            op = (older_pct or 0) / 100
            desired[(True,)]  = op
            desired[(False,)] = 1 - op
        elif "__is_diabetic__" in strata_cols:
            dp = (diabetic_pct or 0) / 100
            desired[(True,)]  = dp
            desired[(False,)] = 1 - dp

        frames = []
        for key, proportion in desired.items():
            n_desired = max(1, int(round(proportion * num_records)))
            # Filter stratum
            mask = pd.Series([True] * len(pool), index=pool.index)
            for i, sc in enumerate(strata_cols):
                mask = mask & (pool[sc] == key[i])
            stratum = pool[mask]
            if len(stratum) == 0:
                # Fall back to full pool for this stratum
                stratum = pool
            sampled = stratum.sample(n=n_desired, replace=True,
                                     random_state=int(rng.integers(0, 10000)))
            frames.append(sampled)

        result = pd.concat(frames, ignore_index=True)
        # Trim/pad to exactly num_records
        if len(result) > num_records:
            result = result.sample(n=num_records, random_state=42)
        elif len(result) < num_records:
            extra = pool.sample(n=num_records - len(result), replace=True, random_state=42)
            result = pd.concat([result, extra], ignore_index=True)

        # Drop helper columns
        for sc in ["__is_older__", "__is_diabetic__"]:
            if sc in result.columns:
                result = result.drop(columns=[sc])
        result = result.sample(frac=1, random_state=42).reset_index(drop=True)
    else:
        result = pool.sample(n=num_records, replace=True, random_state=42).reset_index(drop=True)

    # ── Activity distribution resampling ──────────────────────────────────────
    if activity_dist is not None and activity_col is not None:
        # Normalize
        total_pct = sum(activity_dist.values())
        norm_dist = {k: v / total_pct for k, v in activity_dist.items()}
        frames2 = []
        for act_val, proportion in norm_dist.items():
            n_desired = max(1, int(round(proportion * len(result))))
            stratum = result[result[activity_col].astype(str).str.lower() == act_val.lower()]
            if len(stratum) == 0:
                stratum = result
            sampled = stratum.sample(n=n_desired, replace=True, random_state=42)
            frames2.append(sampled)
        result = pd.concat(frames2, ignore_index=True)
        if len(result) > num_records:
            result = result.sample(n=num_records, random_state=42)
        result = result.sample(frac=1, random_state=42).reset_index(drop=True)

    # ── Measure actual cohort ──────────────────────────────────────────────────
    actual = {}
    if older_pct is not None and age_col is not None and age_col in result.columns:
        n_older = (result[age_col] >= 60).sum()
        actual["older_pct_requested"] = older_pct
        actual["older_pct_actual"] = round(n_older / len(result) * 100, 2)
        actual["older_pct_diff"] = round(abs(older_pct - actual["older_pct_actual"]), 2)

    if diabetic_pct is not None and diabetes_col is not None and diabetes_col in result.columns:
        col_vals = result[diabetes_col].astype(str).str.lower()
        n_diab = col_vals.isin(["1", "true", "yes", "1.0"]).sum()
        actual["diabetic_pct_requested"] = diabetic_pct
        actual["diabetic_pct_actual"] = round(n_diab / len(result) * 100, 2)
        actual["diabetic_pct_diff"] = round(abs(diabetic_pct - actual["diabetic_pct_actual"]), 2)

    if activity_dist is not None and activity_col is not None and activity_col in result.columns:
        actual["activity_requested"] = activity_dist
        vc = result[activity_col].value_counts(normalize=True) * 100
        actual["activity_actual"] = {k: round(v, 2) for k, v in vc.to_dict().items()}

    results = actual
    return result.reset_index(drop=True), results
