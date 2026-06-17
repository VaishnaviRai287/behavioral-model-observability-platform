from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alert import Alert
from app.models.drift_event import DriftEvent
from app.models.ml_model import MLModel
from app.schemas.alert import AlertResponse, DriftEventResponse

router = APIRouter(tags=["Alerts"])


@router.get("/models/{model_id}/alerts", response_model=list[AlertResponse])
def list_alerts(
    model_id: str,
    alert_type: str | None = Query(default=None, alias="type"),
    severity: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    List alerts for a specific model, filterable by type and severity.
    """
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    query = db.query(Alert).filter(Alert.model_id == model_id)
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    if severity:
        query = query.filter(Alert.severity == severity)

    return query.order_by(Alert.created_at.desc()).all()


@router.post("/models/{model_id}/alerts/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(model_id: str, alert_id: str, db: Session = Depends(get_db)):
    """
    Resolve an active alert by marking its resolved_at timestamp.
    """
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id, Alert.model_id == model_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/models/{model_id}/drift", response_model=list[DriftEventResponse])
def list_drift_events(model_id: str, db: Session = Depends(get_db)):
    """
    Fetch all drift evaluation events logged for the specified model.
    """
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return (
        db.query(DriftEvent)
        .filter(DriftEvent.model_id == model_id)
        .order_by(DriftEvent.created_at.desc())
        .all()
    )
