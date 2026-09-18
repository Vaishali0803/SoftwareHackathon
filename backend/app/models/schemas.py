from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime


# ── Dataset ──────────────────────────────────────────────────────────────────

class ColumnInfo(BaseModel):
    name: str
    dtype: str
    missing_count: int
    missing_pct: float
    unique_count: int
    sample_values: List[Any]
    is_sensitive: bool = False


class DatasetProfile(BaseModel):
    id: str
    filename: str
    num_rows: int
    num_columns: int
    columns: List[ColumnInfo]
    sensitive_columns: List[str]
    status: str
    created_at: str


class ColumnApprovalRequest(BaseModel):
    dataset_id: str
    approved_columns: List[str]
    column_mapping: Optional[Dict[str, str]] = None  # original_name → semantic_name


class PreprocessRequest(BaseModel):
    dataset_id: str
    approved_columns: List[str]
    column_mapping: Optional[Dict[str, str]] = None


class PreprocessingResult(BaseModel):
    dataset_id: str
    rows_before: int
    rows_after: int
    missing_handled: Dict[str, int]
    duplicates_removed: int
    columns_excluded: List[str]
    columns_included: List[str]
    status: str


# ── Generation ───────────────────────────────────────────────────────────────

class CohortConfig(BaseModel):
    older_patients_pct: Optional[float] = Field(None, ge=0, le=100,
        description="% of patients over age 60")
    diabetic_pct: Optional[float] = Field(None, ge=0, le=100,
        description="% of diabetic patients")
    activity_distribution: Optional[Dict[str, float]] = Field(None,
        description="e.g. {Low: 40, Medium: 40, High: 20}")
    age_column: Optional[str] = "Age"
    diabetes_column: Optional[str] = "Diabetes"
    activity_column: Optional[str] = "ActivityLevel"


class GenerateRequest(BaseModel):
    dataset_id: str
    num_records: int = Field(..., ge=100, le=500000)
    model: str = Field("CTGAN", description="CTGAN | TVAE | GaussianCopula")
    epochs: Optional[int] = Field(None, ge=10, le=2000)
    cohort: Optional[CohortConfig] = None


class GenerationStatusResponse(BaseModel):
    id: str
    dataset_id: str
    status: str
    progress: int
    progress_message: str
    model_used: Optional[str]
    num_requested: int
    num_generated: Optional[int]
    generation_time_seconds: Optional[float]
    cohort_results: Optional[Dict]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]


class PreviewResponse(BaseModel):
    generation_id: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
    page: int
    page_size: int


# ── Validation ───────────────────────────────────────────────────────────────

class NumericalColumnStats(BaseModel):
    column: str
    source_mean: float
    synth_mean: float
    source_std: float
    synth_std: float
    source_median: float
    synth_median: float
    source_min: float
    synth_min: float
    source_max: float
    synth_max: float
    ks_statistic: float
    ks_pvalue: float
    distribution_similarity: float  # 0-100


class CategoricalColumnStats(BaseModel):
    column: str
    source_distribution: Dict[str, float]
    synth_distribution: Dict[str, float]
    chi2_statistic: Optional[float]
    chi2_pvalue: Optional[float]
    tvd: float  # total variation distance 0-1
    similarity_score: float  # 0-100


class CorrelationStat(BaseModel):
    col_a: str
    col_b: str
    source_correlation: float
    synth_correlation: float
    difference: float


class ValidationReport(BaseModel):
    validation_id: str
    generation_id: str
    numerical_stats: List[NumericalColumnStats]
    categorical_stats: List[CategoricalColumnStats]
    correlation_stats: List[CorrelationStat]
    overall_scores: Dict[str, float]
    created_at: str


# ── Privacy ───────────────────────────────────────────────────────────────────

class PrivacyReport(BaseModel):
    privacy_id: str
    generation_id: str
    exact_duplicates: int
    near_duplicates: int
    risk_level: str  # Low | Medium | High
    total_source_records: int
    total_synthetic_records: int
    duplicate_rate_pct: float
    near_duplicate_rate_pct: float
    details: Dict[str, Any]
    created_at: str


# ── Export ────────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    generation_id: str
    format: str = Field("csv", description="csv | xlsx")
    include_columns: Optional[List[str]] = None
