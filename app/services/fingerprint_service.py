from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.fingerprinting.comparator import compare_fingerprints
from app.fingerprinting.metrics import compute_fingerprint_metrics
from app.models.fingerprint import Fingerprint
from app.models.probe_session import ProbeSession
from app.schemas.fingerprint import ComparisonResult


def create_fingerprint(db: Session, session_id: str) -> Fingerprint:
    """
    Compute and store a fingerprint for a completed probe session.

    Raises:
        404: If session_id doesn't exist
        422: If the probe session is not yet complete
        400: If a fingerprint already exists for this session
    """

    # ── Fetch the probe session ───────────────────────────────────────────────
    session = db.query(ProbeSession).filter(ProbeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Probe session not found")

    if session.status != "done":
        raise HTTPException(
            status_code=422,
            detail=f"Probe session status is '{session.status}', must be 'done'"
        )

    # ── Check for existing fingerprint ────────────────────────────────────────
    existing = (
        db.query(Fingerprint)
        .filter(Fingerprint.session_id == session_id)
        .first()
    )
    if existing:
        return existing   # idempotent: return existing fingerprint

    # ── Compute metrics ───────────────────────────────────────────────────────
    try:
        metrics = compute_fingerprint_metrics(db, session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fingerprint computation failed: {e}")

    # ── Store fingerprint ─────────────────────────────────────────────────────
    fingerprint = Fingerprint(
        session_id=session_id,
        model_id=session.model_id,
        **metrics,
    )
    db.add(fingerprint)
    db.commit()
    db.refresh(fingerprint)
    return fingerprint


def get_fingerprint(db: Session, fingerprint_id: str) -> Fingerprint:
    """Retrieve a fingerprint by ID."""
    fp = db.query(Fingerprint).filter(Fingerprint.id == fingerprint_id).first()
    if not fp:
        raise HTTPException(status_code=404, detail="Fingerprint not found")
    return fp


def get_fingerprints_for_model(db: Session, model_id: str) -> list[Fingerprint]:
    """List all fingerprints for a model, newest first."""
    return (
        db.query(Fingerprint)
        .filter(Fingerprint.model_id == model_id)
        .order_by(Fingerprint.created_at.desc())
        .all()
    )


def compare(db: Session, fp_a_id: str, fp_b_id: str) -> dict:
    """
    Compare two fingerprints and return similarity metrics.

    Raises:
        404: If either fingerprint doesn't exist
        400: If comparing a fingerprint with itself
    """
    if fp_a_id == fp_b_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare a fingerprint with itself"
        )

    fp_a = get_fingerprint(db, fp_a_id)
    fp_b = get_fingerprint(db, fp_b_id)
    return compare_fingerprints(fp_a, fp_b)
