from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.probe import ProbeRequest, ProbeSessionResponse
from app.services import probe_service

router = APIRouter(tags=["Probing"])


@router.post(
    "/models/{model_id}/probe",
    response_model=ProbeSessionResponse,
    status_code=201,
)
def probe_model(
    model_id: str,
    request: ProbeRequest,
    db: Session = Depends(get_db),
):
    """
    Start a probing session for a model.

    Generates n_probes synthetic inputs, runs predictions on each,
    and returns aggregate behavioral statistics.
    """
    return probe_service.start_probe(db, model_id, request.n_probes)


@router.get(
    "/probes/{session_id}",
    response_model=ProbeSessionResponse,
)
def get_probe_session(session_id: str, db: Session = Depends(get_db)):
    """Retrieve a probe session by ID."""
    return probe_service.get_probe_session(db, session_id)


@router.get(
    "/models/{model_id}/probes",
    response_model=list[ProbeSessionResponse],
)
def list_probe_sessions(model_id: str, db: Session = Depends(get_db)):
    """List all probe sessions for a model."""
    return probe_service.list_probe_sessions(db, model_id)
