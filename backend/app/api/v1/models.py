from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
from app.api.deps import get_db
from app.crud.model_registry import model_registry_crud
from app.schemas.model_registry import (
    ModelRegisterCreate, 
    ModelRegisterResponse,
    PredictionPayload,
    PredictionResponse
)
from app.schemas.fingerprint import FingerprintResponse
from app.services.prediction import prediction_service
from app.services.probing import probing_engine
from app.crud.fingerprint import fingerprint_crud

router = APIRouter()

@router.post("/", response_model=ModelRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    *,
    db: AsyncSession = Depends(get_db),
    model_in: ModelRegisterCreate
):
    """
    Register a new machine learning model.
    """
    existing = await model_registry_crud.get_by_name_and_version(
        db, name=model_in.name, version=model_in.version
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model with name '{model_in.name}' and version '{model_in.version}' already exists."
        )
    return await model_registry_crud.create(db=db, obj_in=model_in)

@router.get("/", response_model=List[ModelRegisterResponse])
async def list_models(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Retrieve registered models.
    """
    return await model_registry_crud.get_multi(db=db, skip=skip, limit=limit)

@router.get("/{model_id}", response_model=ModelRegisterResponse)
async def get_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed registry information for a specific model.
    """
    model = await model_registry_crud.get(db=db, model_id=model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found."
        )
    return model

@router.delete("/{model_id}", response_model=ModelRegisterResponse)
async def deregister_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a model from the registry.
    """
    model = await model_registry_crud.remove(db=db, model_id=model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found."
        )
    return model

@router.post("/{model_id}/predict", response_model=PredictionResponse)
async def predict_model(
    model_id: UUID,
    *,
    db: AsyncSession = Depends(get_db),
    payload: PredictionPayload
):
    """
    Execute predictions on a registered model artifact.
    """
    return await prediction_service.predict(db=db, model_id=model_id, raw_inputs=payload.inputs)

@router.post("/{model_id}/probe", response_model=FingerprintResponse)
async def probe_model(
    model_id: UUID,
    num_samples: int = 1000,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a behavioral fingerprint baseline using Latin Hypercube Sampling.
    """
    return await probing_engine.run_probing_and_fingerprint(
        db=db, model_id=model_id, num_samples=num_samples
    )

@router.get("/{model_id}/fingerprint", response_model=FingerprintResponse)
async def get_latest_fingerprint(
    model_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the latest generated behavioral fingerprint for a model.
    """
    fingerprint = await fingerprint_crud.get_latest_by_model(db=db, model_id=model_id)
    if not fingerprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No fingerprint found for model ID '{model_id}'."
        )
    return fingerprint