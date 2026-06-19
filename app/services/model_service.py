import json
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.ml.model_cache import invalidate as invalidate_model_cache
from app.models.ml_model import MLModel
from app.utils.framework_detector import detect_framework


def upload_model(
    db: Session,
    name: str,
    schema_str: str,
    file: UploadFile,
) -> MLModel:
    """
    Orchestrates model upload:
    1. Save file to disk
    2. Detect framework
    3. Persist metadata to DB
    """

    # Parse the schema JSON string into a Python dict
    try:
        schema_dict = json.loads(schema_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="schema must be valid JSON")

    # Generate a unique ID for this model
    model_id = str(uuid.uuid4())

    # Determine the file extension and construct the save path
    original_filename = file.filename or "model"
    suffix = Path(original_filename).suffix  # e.g. ".pkl"
    save_path = Path(settings.upload_dir) / f"{model_id}{suffix}"

    # Ensure upload directory exists
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    # Save the uploaded file to disk
    try:
        with open(save_path, "wb") as dest:
            shutil.copyfileobj(file.file, dest)
            
        # If it's a zip/tar archive, extract it
        if suffix == ".zip":
            import zipfile
            extract_dir = save_path.with_name(f"{model_id}_extracted")
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(save_path, 'r') as zf:
                zf.extractall(extract_dir)
        elif suffix in (".tar.gz", ".tgz"):
            import tarfile
            extract_dir = save_path.with_name(f"{model_id}_extracted")
            extract_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(save_path, 'r:*') as tf:
                tf.extractall(extract_dir)
    except Exception as e:
        save_path.unlink(missing_ok=True)
        extracted_dir = save_path.with_name(f"{model_id}_extracted")
        if extracted_dir.exists() and extracted_dir.is_dir():
            shutil.rmtree(extracted_dir)
        raise HTTPException(
            status_code=500, detail=f"Failed to save or extract model file: {e}"
        )

    # Detect the framework by inspecting the saved file
    try:
        framework = detect_framework(str(save_path))
    except ValueError as e:
        # Clean up the file and extracted directory we saved before failing
        save_path.unlink(missing_ok=True)
        extracted_dir = save_path.with_name(f"{model_id}_extracted")
        if extracted_dir.exists() and extracted_dir.is_dir():
            shutil.rmtree(extracted_dir)
        raise HTTPException(status_code=422, detail=str(e))

    # Extract model architecture
    from app.utils.architecture_extractor import extract_architecture
    architecture = extract_architecture(str(save_path), framework)

    # Generate unique signature
    from app.utils.signature_generator import generate_model_signature
    signature = generate_model_signature(str(save_path), framework, architecture, schema_dict)

    # Create the database record
    db_model = MLModel(
        id=model_id,
        name=name,
        framework=framework,
        file_path=str(save_path),
        input_schema=schema_dict,
        architecture=architecture,
        signature=signature,
        status="ready",
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)

    return db_model


def list_models(db: Session) -> list[MLModel]:
    """Return all registered models."""
    return db.query(MLModel).order_by(MLModel.created_at.desc()).all()


from app.models.faiss_index import FAISSIndex


def get_model(db: Session, model_id: str) -> MLModel:
    """Return a single model by ID or raise 404."""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Retrieve FAISS baseline stats if available
    faiss_idx = db.query(FAISSIndex).filter(FAISSIndex.model_id == model_id).first()
    if faiss_idx:
        model.baseline_mean = faiss_idx.baseline_mean_distance
        model.baseline_std = faiss_idx.baseline_std_distance
    else:
        model.baseline_mean = None
        model.baseline_std = None

    return model



def delete_model(db: Session, model_id: str) -> dict:
    """Delete model record and its file from disk."""
    model = get_model(db, model_id)

    # Delete the file from disk
    file_path = Path(model.file_path)
    file_path.unlink(missing_ok=True)

    # Also delete extracted directory if it exists
    extracted_dir = file_path.with_name(f"{model.id}_extracted")
    if extracted_dir.exists() and extracted_dir.is_dir():
        shutil.rmtree(extracted_dir)

    # Evict from model cache so stale wrapper isn't served after deletion
    invalidate_model_cache(model.file_path)

    # Delete the database record
    db.delete(model)
    db.commit()

    return {"message": f"Model {model_id} deleted successfully"}
