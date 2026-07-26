import math
import numpy as np
from sqlalchemy.orm import Session
from fastapi import HTTPException
from sklearn.linear_model import Ridge

from app.models.ml_model import MLModel
from app.models.prediction_log import PredictionLog
from app.models.probe_session import ProbeSession
from app.models.probe_result import ProbeResult
from app.ml.loader import load_model

def get_background_data(db: Session, model: MLModel) -> np.ndarray:
    """Return a SHAP reference background — the model's baseline probe results, or schema-range samples if none exist."""
    features = model.input_schema.get("features", [])

    session = (
        db.query(ProbeSession)
        .filter(ProbeSession.model_id == model.id, ProbeSession.status == "done")
        .order_by(ProbeSession.created_at.desc())
        .first()
    )
    if session:
        results = db.query(ProbeResult).filter(ProbeResult.session_id == session.id).all()
        if results:
            return np.array([r.input_vector for r in results])

    n_features = len(features)
    dummy_bg = []
    for _ in range(50):
        row = []
        for f in features:
            f_min = f.get("min", 0.0)
            f_max = f.get("max", 1.0)
            if f_min is None: f_min = 0.0
            if f_max is None: f_max = 1.0
            row.append(f_min + np.random.rand() * (f_max - f_min))
        dummy_bg.append(row)

    return np.array(dummy_bg) if dummy_bg else np.zeros((1, n_features))


def compute_kernel_shap(
    model_wrapper,
    input_vector: np.ndarray,
    background_data: np.ndarray,
    predicted_class: int,
    num_samples: int = 120
) -> tuple[float, np.ndarray]:
    """Estimate SHAP values for predicted_class via Kernel SHAP (weighted Ridge regression over coalition samples)."""
    M = len(input_vector)
    if M == 0:
        return 0.0, np.array([])

    background_mean = np.mean(background_data, axis=0)

    # Base value: mean predicted-class probability over a background sample.
    base_outputs = []
    for ref_row in background_data[:20]:
        res = model_wrapper.predict(ref_row.reshape(1, -1))
        if res.raw_output and len(res.raw_output) > predicted_class:
            base_outputs.append(res.raw_output[predicted_class])
        else:
            base_outputs.append(res.confidence)
    base_value = float(np.mean(base_outputs)) if base_outputs else 0.5

    # All-zeros/all-ones coalitions anchor the regression; the rest are random
    # binary feature-inclusion masks.
    coalitions = [np.zeros(M), np.ones(M)]
    for _ in range(min(num_samples - 2, 2**M - 2) if M < 10 else num_samples - 2):
        z = np.random.choice([0, 1], size=M)
        if np.sum(z) == 0 or np.sum(z) == M:
            z = np.random.choice([0, 1], size=M)
        coalitions.append(z)

    coalitions = np.unique(np.array(coalitions), axis=0)

    X_reg = coalitions
    y_reg = []
    weights = []

    for z in coalitions:
        # Hybrid instance: included features take the real value, excluded
        # features take the background mean.
        x_hybrid = z * input_vector + (1 - z) * background_mean
        res = model_wrapper.predict(x_hybrid.reshape(1, -1))
        if res.raw_output and len(res.raw_output) > predicted_class:
            y_val = res.raw_output[predicted_class]
        else:
            y_val = res.confidence
        y_reg.append(y_val)

        k = int(np.sum(z))
        if k == 0 or k == M:
            weights.append(10000.0)  # anchor the boundary coalitions
        else:
            # Shapley kernel weight: (M - 1) / (C(M, k) * k * (M - k))
            comb = math.comb(M, k)
            w = (M - 1) / (comb * k * (M - k))
            weights.append(w)

    reg = Ridge(alpha=1e-5, fit_intercept=True)
    reg.fit(X_reg, y_reg, sample_weight=weights)

    return base_value, reg.coef_


def explain_prediction_log(db: Session, model_id: str, prediction_id: str) -> dict:
    """Compute a per-feature SHAP contribution breakdown for a single logged prediction."""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    log = db.query(PredictionLog).filter(PredictionLog.id == prediction_id, PredictionLog.model_id == model_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Prediction log not found")

    try:
        wrapper = load_model(model.file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model file: {e}")

    background = get_background_data(db, model)
    input_vec = np.array(log.input_vector)

    base_val, shap_vals = compute_kernel_shap(wrapper, input_vec, background, log.predicted_class)

    features = model.input_schema.get("features", [])
    breakdown = []

    for idx, f in enumerate(features):
        feat_name = f["name"]
        feat_val = log.input_features.get(feat_name, None)
        contrib = float(shap_vals[idx]) if idx < len(shap_vals) else 0.0
        breakdown.append({
            "feature": feat_name,
            "value": feat_val,
            "contribution": round(contrib, 4)
        })

    breakdown.sort(key=lambda x: abs(x["contribution"]), reverse=True)

    return {
        "prediction_id": prediction_id,
        "predicted_class": log.predicted_class,
        "base_value": round(base_val, 4),
        "prediction_value": round(log.confidence, 4),
        "breakdown": breakdown
    }


def compute_global_explainability(db: Session, model_id: str) -> dict:
    """Estimate global feature importance as mean absolute SHAP value across representative background samples."""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        wrapper = load_model(model.file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model file: {e}")

    background = get_background_data(db, model)
    features = model.input_schema.get("features", [])

    all_shaps = []
    samples_to_run = background[:15]

    for row in samples_to_run:
        res = wrapper.predict(row.reshape(1, -1))
        _, shap_vals = compute_kernel_shap(wrapper, row, background, res.predicted_class, num_samples=80)
        if len(shap_vals) == len(features):
            all_shaps.append(np.abs(shap_vals))

    if all_shaps:
        mean_abs_shap = np.mean(np.array(all_shaps), axis=0)
    else:
        mean_abs_shap = np.zeros(len(features))

    feature_importance = []
    for idx, f in enumerate(features):
        feat_name = f["name"]
        importance = float(mean_abs_shap[idx]) if idx < len(mean_abs_shap) else 0.0
        feature_importance.append({
            "feature": feat_name,
            "importance": round(importance, 4)
        })

    feature_importance.sort(key=lambda x: x["importance"], reverse=True)

    return {
        "model_id": model_id,
        "feature_importance": feature_importance
    }
