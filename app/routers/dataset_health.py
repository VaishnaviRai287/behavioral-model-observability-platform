from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.dataset_health_service import analyze_dataset_health

router = APIRouter(prefix="/models", tags=["Dataset Health"])

@router.get("/{model_id}/dataset-health")
def get_dataset_health(model_id: str, db: Session = Depends(get_db)):
    """
    Get dataset health metrics (missing values, class imbalance, outliers, duplicates) 
    calculated from model prediction logs.
    """
    return analyze_dataset_health(db, model_id)
