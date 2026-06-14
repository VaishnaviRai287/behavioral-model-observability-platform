from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.fingerprint import ComparisonResult, FingerprintResponse
from app.services import fingerprint_service, drift_service

router = APIRouter(tags=["Fingerprinting"])


@router.post(
    "/probes/{session_id}/fingerprint",
    response_model=FingerprintResponse,
    status_code=201,
)
def create_fingerprint(session_id: str, db: Session = Depends(get_db)):
    """
    Compute and store a behavioral fingerprint for a completed probe session.

    Idempotent: if a fingerprint already exists for this session, returns it.
    """
    return fingerprint_service.create_fingerprint(db, session_id)


@router.get(
    "/fingerprints/{fingerprint_id}",
    response_model=FingerprintResponse,
)
def get_fingerprint(fingerprint_id: str, db: Session = Depends(get_db)):
    """Retrieve a fingerprint by ID."""
    return fingerprint_service.get_fingerprint(db, fingerprint_id)


@router.get(
    "/models/{model_id}/fingerprints",
    response_model=list[FingerprintResponse],
)
def list_fingerprints(model_id: str, db: Session = Depends(get_db)):
    """List all fingerprints for a model, newest first."""
    return fingerprint_service.get_fingerprints_for_model(db, model_id)


@router.get(
    "/fingerprints/{fp_a_id}/compare/{fp_b_id}",
    response_model=ComparisonResult,
)
def compare_fingerprints(fp_a_id: str, fp_b_id: str, db: Session = Depends(get_db)):
    """
    Compare two fingerprints.

    Returns similarity score and verdict: 'stable', 'drifted', or 'severely_drifted'.
    """
    return fingerprint_service.compare(db, fp_a_id, fp_b_id)


@router.get("/models/{model_id}/drift-status")
def get_drift_status(
    model_id: str,
    n_recent: int = Query(default=100, ge=10, le=1000),
    db: Session = Depends(get_db),
):
    """
    Compare recent live prediction behavior to the stored baseline fingerprint.

    Returns a drift verdict: 'stable', 'drifted', or 'severely_drifted'.
    Requires at least 10 prediction logs and one stored fingerprint.
    """
    return drift_service.get_drift_status(db, model_id, n_recent)
