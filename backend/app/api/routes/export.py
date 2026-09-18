"""
Export routes — download synthetic data as CSV or Excel.
"""
import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.database import GenerationRecord, ValidationRecord, PrivacyRecord, get_db
from app.services.export import (
    build_validation_report_xlsx,
    export_csv,
    export_xlsx,
    load_synthetic,
)

router = APIRouter()


@router.get("/{generation_id}/csv")
def download_csv(
    generation_id: str,
    db: Session = Depends(get_db),
):
    gen_record = _get_done_generation(generation_id, db)
    df = load_synthetic(gen_record.output_path)
    data = export_csv(df)
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="synthetic_data_{generation_id[:8]}.csv"'},
    )


@router.get("/{generation_id}/xlsx")
def download_xlsx(
    generation_id: str,
    db: Session = Depends(get_db),
):
    gen_record = _get_done_generation(generation_id, db)
    df = load_synthetic(gen_record.output_path)
    data = export_xlsx(df)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="synthetic_data_{generation_id[:8]}.xlsx"'},
    )


@router.get("/{generation_id}/report-xlsx")
def download_report_xlsx(
    generation_id: str,
    db: Session = Depends(get_db),
):
    gen_record = _get_done_generation(generation_id, db)

    val_record = (
        db.query(ValidationRecord)
        .filter(ValidationRecord.generation_id == generation_id)
        .first()
    )
    priv_record = (
        db.query(PrivacyRecord)
        .filter(PrivacyRecord.generation_id == generation_id)
        .first()
    )

    validation_data = {}
    if val_record:
        validation_data = {
            "numerical_stats": json.loads(val_record.numerical_stats or "[]"),
            "categorical_stats": json.loads(val_record.categorical_stats or "[]"),
            "correlation_stats": json.loads(val_record.correlation_stats or "[]"),
            "overall_scores": json.loads(val_record.overall_scores or "{}"),
        }

    privacy_data = {}
    if priv_record:
        privacy_data = {
            "exact_duplicates": priv_record.exact_duplicates,
            "near_duplicates": priv_record.near_duplicates,
            "risk_level": priv_record.risk_level,
            "details": json.loads(priv_record.details or "{}"),
        }

    try:
        data = build_validation_report_xlsx(validation_data, privacy_data)
    except Exception as e:
        raise HTTPException(500, f"Could not build report: {e}")

    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="validation_report_{generation_id[:8]}.xlsx"'},
    )


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_done_generation(generation_id: str, db: Session) -> GenerationRecord:
    record = db.get(GenerationRecord, generation_id)
    if not record:
        raise HTTPException(404, "Generation job not found.")
    if record.status != "done":
        raise HTTPException(400, f"Generation is not complete (status: {record.status}).")
    if not record.output_path or not os.path.exists(record.output_path):
        raise HTTPException(500, "Output file not found on disk.")
    return record
