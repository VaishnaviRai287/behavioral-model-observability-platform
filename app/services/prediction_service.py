import time

import numpy as np
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ml.model_cache import get_cached_wrapper
from app.models.ml_model import MLModel
from app.models.prediction_log import PredictionLog


def validate_and_build_vector(features: dict, schema: dict) -> list[float]:
    """
    Validate input features against the model schema and build an ordered input vector.

    Checks:
    1. All declared features are present in the request
    2. Values can be converted to float
    3. Values are within declared min/max bounds (if specified)

    Returns:
        Ordered list of float values matching the schema's feature order.

    Raises:
        HTTPException 422: On any validation failure.
    """
    schema_features = schema.get("features", [])
    input_vector = []

    for feature in schema_features:
        name = feature["name"]
        feat_min = feature.get("min")
        feat_max = feature.get("max")

        # ── Check presence ────────────────────────────────────────────────────
        if name not in features:
            raise HTTPException(
                status_code=422,
                detail=f"Missing required feature: '{name}'"
            )

        # ── Check type ────────────────────────────────────────────────────────
        try:
            value = float(features[name])
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=422,
                detail=f"Feature '{name}' must be a number, got: {features[name]!r}"
            )

        # ── Check bounds ──────────────────────────────────────────────────────
        if feat_min is not None and value < feat_min:
            raise HTTPException(
                status_code=422,
                detail=f"Feature '{name}' value {value} is below minimum {feat_min}"
            )
        if feat_max is not None and value > feat_max:
            raise HTTPException(
                status_code=422,
                detail=f"Feature '{name}' value {value} is above maximum {feat_max}"
            )

        input_vector.append(value)

    return input_vector


def predict(db: Session, model_id: str, features: dict) -> dict:
    """
    Run a live prediction on a registered model.

    Steps:
    1. Fetch model from DB
    2. Validate and order input features
    3. Load model wrapper
    4. Run predict() with latency measurement
    5. Store prediction log
    6. Return prediction result

    Raises:
        404: If model_id doesn't exist
        422: If input validation fails
    """

    # ── Fetch model ────────────────────────────────────────────────────────────
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # ── Validate input and build ordered vector ────────────────────────────────
    input_vector = validate_and_build_vector(features, model.input_schema)

    # ── Load model and run inference (cached) ─────────────────────────────────
    wrapper = get_cached_wrapper(model.file_path)
    input_array = np.array([input_vector])   # shape (1, n_features)

    start_cpu = time.process_time()
    start_time = time.perf_counter()
    result, activation = wrapper.predict_with_activations(input_array)
    end_time = time.perf_counter()
    end_cpu = time.process_time()

    latency_ms = (end_time - start_time) * 1000   # convert seconds → milliseconds
    wall_time = end_time - start_time
    cpu_time = end_cpu - start_cpu
    cpu_utilization = (cpu_time / wall_time * 100) if wall_time > 0 else 0.0

    # Memory usage mapping (Darwin in bytes, Linux in kilobytes)
    import sys
    import resource
    ru_maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == 'darwin':
        memory_mb = ru_maxrss / (1024 * 1024)
    else:
        memory_mb = ru_maxrss / 1024

    # ── Novelty scoring ───────────────────────────────────────────────────────
    from app.monitoring.novelty_scorer import score_novelty
    faiss_distance, novelty_flag = score_novelty(db, model_id, activation)

    # ── Store prediction log ───────────────────────────────────────────────────
    log = PredictionLog(
        model_id=model_id,
        input_features=features,
        input_vector=input_vector,
        predicted_class=result.predicted_class,
        confidence=result.confidence,
        raw_output=result.raw_output,
        latency_ms=latency_ms,
        cpu_utilization=cpu_utilization,
        memory_mb=memory_mb,
        faiss_distance=faiss_distance,
        novelty_flag=novelty_flag,
    )
    db.add(log)
    db.commit()

    # ── Novelty Alert Check ───────────────────────────────────────────────────
    if novelty_flag:
        from app.monitoring.alert_engine import process_latent_novelty
        process_latent_novelty(
            db,
            model_id,
            faiss_distance,
            {"input_features": features}
        )

    # ── Async Drift Check (Every 50th prediction) ────────────────────────────────
    # Dispatched to a Celery worker so drift computation never blocks this response.
    prediction_count = db.query(PredictionLog).filter(PredictionLog.model_id == model_id).count()
    if prediction_count > 0 and prediction_count % 50 == 0:
        from app.tasks.drift_task import run_drift_check

        run_drift_check.delay(model_id)


    return {
        "model_id": model_id,
        "predicted_class": result.predicted_class,
        "confidence": result.confidence,
        "raw_output": result.raw_output,
        "latency_ms": round(latency_ms, 3),
        "faiss_distance": round(faiss_distance, 5) if faiss_distance is not None else None,
        "novelty_flag": novelty_flag,
    }


def list_prediction_logs(db: Session, model_id: str, limit: int = 100) -> list[PredictionLog]:
    """
    Retrieve the most recent prediction logs for a model.

    Args:
        limit: Maximum number of logs to return (default 100, max 1000).
    """
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return (
        db.query(PredictionLog)
        .filter(PredictionLog.model_id == model_id)
        .order_by(PredictionLog.created_at.desc())
        .limit(min(limit, 1000))
        .all()
    )
