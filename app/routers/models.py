from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alert import Alert
from app.models.drift_event import DriftEvent
from app.models.ml_model import MLModel
from app.models.prediction_log import PredictionLog
from app.schemas.alert import ModelHealthResponse
from app.schemas.model import ModelCreateResponse, ModelDetailResponse, ModelListItem
from app.services import model_service

router = APIRouter(prefix="/models", tags=["Models"])


@router.post("", response_model=ModelCreateResponse, status_code=201)
async def upload_model(
    name: str = Form(...),
    schema: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a trained model file and its input schema.

    - **name**: Human-readable model name
    - **schema**: JSON string describing feature names, types, and bounds
    - **file**: Model artifact (.pkl, .joblib, .pt, .onnx)
    """
    return model_service.upload_model(db, name, schema, file)


@router.get("", response_model=list[ModelListItem])
def list_models(db: Session = Depends(get_db)):
    """List all registered models."""
    return model_service.list_models(db)


@router.get("/{model_id}", response_model=ModelDetailResponse)
def get_model(model_id: str, db: Session = Depends(get_db)):
    """Retrieve full metadata for a specific model."""
    return model_service.get_model(db, model_id)


@router.delete("/{model_id}")
def delete_model(model_id: str, db: Session = Depends(get_db)):
    """Delete a model and its associated file."""
    return model_service.delete_model(db, model_id)


@router.get("/{model_id}/health", response_model=ModelHealthResponse)
def get_model_health(model_id: str, db: Session = Depends(get_db)):
    """
    Retrieve real-time behavioral health status of a model.
    """
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 1. Compute novelty rate over the last 100 predictions
    recent_logs = (
        db.query(PredictionLog)
        .filter(PredictionLog.model_id == model_id)
        .order_by(PredictionLog.created_at.desc())
        .limit(100)
        .all()
    )
    novel_count = sum(1 for log in recent_logs if log.novelty_flag)
    novelty_rate = novel_count / len(recent_logs) if recent_logs else 0.0

    # 2. Get latest drift scores (KS statistic) per feature
    features = model.input_schema.get("features", [])
    drift_scores = {}
    for feature in features:
        name = feature["name"]
        latest_event = (
            db.query(DriftEvent)
            .filter(DriftEvent.model_id == model_id, DriftEvent.feature_name == name)
            .order_by(DriftEvent.created_at.desc())
            .first()
        )
        drift_scores[name] = latest_event.ks_statistic if latest_event else 0.0

    # 3. Retrieve count of active, unresolved alerts
    active_alerts = (
        db.query(Alert)
        .filter(Alert.model_id == model_id, Alert.resolved_at == None)
        .count()
    )

    return ModelHealthResponse(
        novelty_rate=novelty_rate,
        drift_scores=drift_scores,
        active_alerts=active_alerts,
    )

