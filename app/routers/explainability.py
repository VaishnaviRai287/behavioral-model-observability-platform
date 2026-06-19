from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.shap_service import explain_prediction_log, compute_global_explainability

router = APIRouter(prefix="/models", tags=["Model Explainability"])

@router.get("/{model_id}/explainability/global")
def get_global_explainability(model_id: str, db: Session = Depends(get_db)):
    """
    Get global feature importances calculated by averaging absolute SHAP values
    across probe/baseline instances.
    """
    return compute_global_explainability(db, model_id)

@router.get("/{model_id}/predictions/{prediction_id}/explain")
def get_prediction_explanation(model_id: str, prediction_id: str, db: Session = Depends(get_db)):
    """
    Get prediction contribution breakdown (local SHAP values) for a specific
    prediction event log. Shows how much each feature contributed to the final prediction.
    """
    return explain_prediction_log(db, model_id, prediction_id)
