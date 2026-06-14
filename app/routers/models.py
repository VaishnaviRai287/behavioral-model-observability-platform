from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
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
