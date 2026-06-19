from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.performance_service import analyze_performance_profile

router = APIRouter(prefix="/models", tags=["Performance Profiling"])

@router.get("/{model_id}/performance")
def get_performance_profile(model_id: str, db: Session = Depends(get_db)):
    """
    Get latency percentiles, throughput (RPS), CPU, and memory utilization statistics
    for inference queries.
    """
    return analyze_performance_profile(db, model_id)
