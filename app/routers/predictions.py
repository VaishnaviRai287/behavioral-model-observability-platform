from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.prediction import PredictRequest, PredictionLogResponse, PredictionResponse
from app.services import prediction_service

router = APIRouter(tags=["Predictions"])


@router.post(
    "/models/{model_id}/predict",
    response_model=PredictionResponse,
    status_code=200,
)
def predict(
    model_id: str,
    request: PredictRequest,
    db: Session = Depends(get_db),
):
    """
    Run a live prediction on a registered model.

    Validates input against the model's declared schema,
    runs inference, logs the result, and returns the prediction.
    """
    return prediction_service.predict(db, model_id, request.features)


@router.get(
    "/models/{model_id}/predictions",
    response_model=list[PredictionLogResponse],
)
def list_predictions(
    model_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Retrieve the most recent prediction logs for a model.

    Results are ordered newest-first. Use the `limit` parameter to control
    how many records are returned (default 100, max 1000).
    """
    return prediction_service.list_prediction_logs(db, model_id, limit)

