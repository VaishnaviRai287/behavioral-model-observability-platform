from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.ml_model import MLModel
from app.models.probe_session import ProbeSession
from app.probing.engine import run_probe_session


def start_probe(db: Session, model_id: str, n_probes: int) -> ProbeSession:
    """
    Start a probe session for a given model.

    Creates a ProbeSession record, runs the probe engine,
    and returns the completed session.

    Raises:
        404: If model_id does not exist
        422: If model file is missing from disk
    """

    # ── Fetch the model ───────────────────────────────────────────────────────
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # ── Create the session record ─────────────────────────────────────────────
    session = ProbeSession(
        model_id=model_id,
        n_probes=n_probes,
        status="running",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # ── Run the probe engine ──────────────────────────────────────────────────
    try:
        run_probe_session(
            db=db,
            session=session,
            file_path=model.file_path,
            schema=model.input_schema,
        )
    except Exception as e:
        # If the engine fails, mark the session as failed
        session.status = "failed"
        session.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Probe failed: {e}")

    db.refresh(session)
    return session


def get_probe_session(db: Session, session_id: str) -> ProbeSession:
    """Retrieve a probe session by ID."""
    session = db.query(ProbeSession).filter(ProbeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Probe session not found")
    return session


def list_probe_sessions(db: Session, model_id: str) -> list[ProbeSession]:
    """List all probe sessions for a given model."""
    return (
        db.query(ProbeSession)
        .filter(ProbeSession.model_id == model_id)
        .order_by(ProbeSession.created_at.desc())
        .all()
    )
