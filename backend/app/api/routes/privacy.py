"""
Privacy risk check routes.
"""
import json
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import DatasetRecord, GenerationRecord, PrivacyRecord, get_db
from app.services.privacy import run_privacy_checks

router = APIRouter()


@router.post("/{generation_id}")
def trigger_privacy_check(generation_id: str, db: Session = Depends(get_db)):
    gen_record = db.get(GenerationRecord, generation_id)
    if not gen_record:
        raise HTTPException(404, "Generation job not found.")
    if gen_record.status != "done":
        raise HTTPException(400, f"Generation must be complete (status: {gen_record.status}).")

    # Return existing if already computed
    existing = (
        db.query(PrivacyRecord)
        .filter(PrivacyRecord.generation_id == generation_id)
        .first()
    )
    if existing:
        return _format_privacy(existing)

    dataset = db.get(DatasetRecord, gen_record.dataset_id)
    if not dataset or not dataset.preprocessed_path:
        raise HTTPException(400, "Source dataset not found.")

    if not os.path.exists(dataset.preprocessed_path):
        raise HTTPException(500, "Preprocessed source file missing.")
    if not os.path.exists(gen_record.output_path):
        raise HTTPException(500, "Synthetic output file missing.")

    try:
        priv_record = run_privacy_checks(
            generation_id=generation_id,
            dataset_id=gen_record.dataset_id,
            source_path=dataset.preprocessed_path,
            synthetic_path=gen_record.output_path,
            db=db,
        )
    except Exception as e:
        raise HTTPException(500, f"Privacy check failed: {e}")

    return _format_privacy(priv_record)


@router.get("/{generation_id}/report")
def get_privacy_report(generation_id: str, db: Session = Depends(get_db)):
    priv_record = (
        db.query(PrivacyRecord)
        .filter(PrivacyRecord.generation_id == generation_id)
        .first()
    )
    if not priv_record:
        raise HTTPException(404, "Privacy report not found. Run privacy check first.")
    return _format_privacy(priv_record)


def _format_privacy(record: PrivacyRecord) -> dict:
    details = {}
    if record.details:
        try:
            details = json.loads(record.details)
        except Exception:
            pass
    return {
        "privacy_id": record.id,
        "generation_id": record.generation_id,
        "exact_duplicates": record.exact_duplicates,
        "near_duplicates": record.near_duplicates,
        "risk_level": record.risk_level,
        "total_source_records": details.get("total_source_records", 0),
        "total_synthetic_records": details.get("total_synthetic_records", 0),
        "duplicate_rate_pct": details.get("exact_duplicate_rate_pct", 0),
        "near_duplicate_rate_pct": details.get("near_duplicate_rate_pct", 0),
        "details": details,
        "created_at": record.created_at.isoformat(),
    }
