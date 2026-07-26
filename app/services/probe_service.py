from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.ml_model import MLModel
from app.models.probe_session import ProbeSession
from app.probing.engine import run_probe_session


def start_probe(db: Session, model_id: str, n_probes: int) -> ProbeSession:
    """Run a probe session for a model and return it once complete (or failed)."""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    session = ProbeSession(
        model_id=model_id,
        n_probes=n_probes,
        status="running",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        run_probe_session(
            db=db,
            session=session,
            file_path=model.file_path,
            schema=model.input_schema,
        )
    except Exception as e:
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
