from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.api.deps import get_db
from app.crud.observability import observability_crud
from app.crud.fingerprint import fingerprint_crud
from app.crud.model_registry import model_registry_crud
from app.schemas.observability import (
    AlertResponse, 
    MetricStatusResponse, 
    ChangelogResponse, 
    AlertExplanationResponse
)
from app.services.llm import llm_service

router = APIRouter()

@router.get("/{model_id}/alerts", response_model=List[AlertResponse])
async def list_alerts(
    model_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve generated drift and novelty alerts for a model.
    """
    return await observability_crud.get_alerts_by_model(db=db, model_id=model_id)

@router.get("/{model_id}/metrics", response_model=MetricStatusResponse)
async def get_metrics_status(
    model_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary parameters and drift state computations.
    """
    logs = await observability_crud.get_recent_logs(db=db, model_id=model_id, limit=50)
    alerts = await observability_crud.get_alerts_by_model(db=db, model_id=model_id)
    
    max_ks = 0.0
    max_psi = 0.0
    for a in alerts:
        if a.alert_type == "FEATURE_DRIFT":
            max_ks = max(max_ks, a.metric_value)
            
    return MetricStatusResponse(
        model_id=model_id,
        recent_inferences_count=len(logs),
        max_ks_statistic=max_ks,
        max_psi_value=max_psi
    )

@router.post("/compare", response_model=ChangelogResponse)
async def compare_models(
    model_id_a: UUID,
    model_id_b: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Compare two model versions using their behavioral fingerprints and generate a semantic changelog.
    """
    model_a = await model_registry_crud.get(db, model_id_a)
    model_b = await model_registry_crud.get(db, model_id_b)
    if not model_a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model A not found.")
    if not model_b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model B not found.")
        
    fingerprint_a = await fingerprint_crud.get_latest_by_model(db, model_id_a)
    fingerprint_b = await fingerprint_crud.get_latest_by_model(db, model_id_b)
    if not fingerprint_a:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Model A (v{model_a.version}) does not have a generated baseline fingerprint. Run probing first."
        )
    if not fingerprint_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Model B (v{model_b.version}) does not have a generated baseline fingerprint. Run probing first."
        )
        
    model_a_info = {
        "name": model_a.name,
        "version": model_a.version,
        "framework": model_a.framework,
        "task_type": model_a.task_type,
        "input_schema": model_a.input_schema,
        "output_schema": model_a.output_schema
    }
    model_b_info = {
        "name": model_b.name,
        "version": model_b.version,
        "framework": model_b.framework,
        "task_type": model_b.task_type,
        "input_schema": model_b.input_schema,
        "output_schema": model_b.output_schema
    }
    
    fp_a_info = {
        "class_distribution": fingerprint_a.class_distribution,
        "confidence_distribution": fingerprint_a.confidence_distribution,
        "high_uncertainty_regions": fingerprint_a.high_uncertainty_regions
    }
    fp_b_info = {
        "class_distribution": fingerprint_b.class_distribution,
        "confidence_distribution": fingerprint_b.confidence_distribution,
        "high_uncertainty_regions": fingerprint_b.high_uncertainty_regions
    }

    changelog = await llm_service.generate_changelog(model_a_info, fp_a_info, model_b_info, fp_b_info)
    return ChangelogResponse(
        model_id_a=model_id_a,
        model_id_b=model_id_b,
        changelog=changelog
    )

@router.post("/alerts/{alert_id}/explain", response_model=AlertExplanationResponse)
async def explain_drift_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an LLM-grounded natural language explanation for an observability drift/novelty alert.
    """
    alert = await observability_crud.get_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
        
    model = await model_registry_crud.get(db, alert.model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model associated with the alert not found.")
        
    fingerprint = await fingerprint_crud.get_latest_by_model(db, alert.model_id)
    if not fingerprint:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No baseline fingerprint exists for this model.")
        
    logs = await observability_crud.get_recent_logs(db, alert.model_id, limit=20)
    
    alert_info = {
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "metric_value": alert.metric_value
    }
    model_info = {
        "name": model.name,
        "version": model.version
    }
    fp_info = {
        "high_uncertainty_regions": fingerprint.high_uncertainty_regions,
        "boundary_samples": fingerprint.boundary_samples
    }
    logs_info = [
        {
            "features": l.features,
            "prediction": l.prediction,
            "confidence": l.confidence
        }
        for l in logs
    ]
    
    explanation = await llm_service.explain_alert(alert_info, model_info, fp_info, logs_info)
    return AlertExplanationResponse(
        alert_id=alert_id,
        explanation=explanation
    )
