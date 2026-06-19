from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.monitoring.drift_detector import analyze_drift_and_distributions

router = APIRouter(prefix="/models", tags=["Drift Analysis"])

@router.get("/{model_id}/drift-analysis")
def get_drift_analysis(
    model_id: str,
    n_recent: int = Query(default=100, ge=10, le=1000),
    db: Session = Depends(get_db)
):
    """
    Retrieve statistical drift analysis comparing training (baseline LHS probe data)
    against production (live prediction logs) for both features and targets (predictions/confidences).
    """
    return analyze_drift_and_distributions(db, model_id, n_recent)
