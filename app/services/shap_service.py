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
    """
    Retrieve or generate background dataset for SHAP reference.
    Prefers baseline probe results, falls back to schema-generated midpoints.
    """
    features = model.input_schema.get("features", [])
    
    # 1. Try to fetch the latest successful probe session
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
            
    # 2. Fallback: generate a dummy reference background using schema ranges
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
    """
    Calculates SHAP values using Kernel SHAP.
    Explains the model output probability (confidence) for the predicted_class.
    """
    M = len(input_vector)
    if M == 0:
        return 0.0, np.array([])
        
    # Calculate feature-wise background average
    background_mean = np.mean(background_data, axis=0)
    
    # Calculate expected base output (base value)
    base_outputs = []
    for ref_row in background_data[:20]:  # sample 20 for speed
        res = model_wrapper.predict(ref_row.reshape(1, -1))
        # Use probability of predicted_class if output is multiclass, else fallback
        if res.raw_output and len(res.raw_output) > predicted_class:
            base_outputs.append(res.raw_output[predicted_class])
        else:
            base_outputs.append(res.confidence)
    base_value = float(np.mean(base_outputs)) if base_outputs else 0.5

    # Generate coalition samples
    coalitions = []
    # Always include all-zeros and all-ones coalitions for stability
    coalitions.append(np.zeros(M))
    coalitions.append(np.ones(M))
    
    # Generate random binary coalitions
    for _ in range(min(num_samples - 2, 2**M - 2) if M < 10 else num_samples - 2):
        z = np.random.choice([0, 1], size=M)
        # Avoid duplicate all-zeros or all-ones
        if np.sum(z) == 0 or np.sum(z) == M:
            z = np.random.choice([0, 1], size=M)
        coalitions.append(z)
        
    # Remove duplicates
    coalitions = np.unique(np.array(coalitions), axis=0)
    S = len(coalitions)
    
    # Construct hybrid instances and record output
    X_reg = coalitions
    y_reg = []
    weights = []
    
    for z in coalitions:
        # Build hybrid instance: x_hybrid = z * x + (1 - z) * background_mean
        x_hybrid = z * input_vector + (1 - z) * background_mean
        
        # Predict on hybrid instance
        res = model_wrapper.predict(x_hybrid.reshape(1, -1))
        if res.raw_output and len(res.raw_output) > predicted_class:
            y_val = res.raw_output[predicted_class]
        else:
            y_val = res.confidence
        y_reg.append(y_val)
        
        # Calculate Shapley Kernel Weight
        k = int(np.sum(z))
        if k == 0 or k == M:
            # Assign huge weight to boundary constraints
            weights.append(10000.0)
        else:
            # Standard Shapley Kernel Weight formula: (M - 1) / ( (M choose k) * k * (M - k) )
            comb = math.comb(M, k)
            w = (M - 1) / (comb * k * (M - k))
            weights.append(w)
            
    # Fit weighted Ridge regression (SHAP linear model solver)
    reg = Ridge(alpha=1e-5, fit_intercept=True)
    reg.fit(X_reg, y_reg, sample_weight=weights)
    
    # Coefficients are the estimated SHAP values
    shap_values = reg.coef_
    return base_value, shap_values


def explain_prediction_log(db: Session, model_id: str, prediction_id: str) -> dict:
    """
    Computes a prediction breakdown explanation for a specific prediction log.
    """
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
        
    log = db.query(PredictionLog).filter(PredictionLog.id == prediction_id, PredictionLog.model_id == model_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Prediction log not found")
        
    # Load model wrapper
    try:
        wrapper = load_model(model.file_path)
        wrapper.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model file: {e}")
        
    background = get_background_data(db, model)
    input_vec = np.array(log.input_vector)
    
    # Run Kernel SHAP
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
        
    # Sort contributions by absolute value descending
    breakdown.sort(key=lambda x: abs(x["contribution"]), reverse=True)
    
    # Calculate output prediction confidence/probability
    prediction_value = log.confidence
    
    return {
        "prediction_id": prediction_id,
        "predicted_class": log.predicted_class,
        "base_value": round(base_val, 4),
        "prediction_value": round(prediction_value, 4),
        "breakdown": breakdown
    }


def compute_global_explainability(db: Session, model_id: str) -> dict:
    """
    Calculate global feature importances by averaging absolute SHAP values 
    across background baseline sample sweeps.
    """
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
        
    # Load model wrapper
    try:
        wrapper = load_model(model.file_path)
        wrapper.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model file: {e}")
        
    background = get_background_data(db, model)
    features = model.input_schema.get("features", [])
    
    # Calculate SHAP values on up to 15 representative background samples
    all_shaps = []
    samples_to_run = background[:15]
    
    for row in samples_to_run:
        # Predict class
        res = wrapper.predict(row.reshape(1, -1))
        # Run SHAP
        _, shap_vals = compute_kernel_shap(wrapper, row, background, res.predicted_class, num_samples=80)
        if len(shap_vals) == len(features):
            all_shaps.append(np.abs(shap_vals))
            
    if all_shaps:
        mean_abs_shap = np.mean(np.array(all_shaps), axis=0)
    else:
        mean_abs_shap = np.zeros(len(features))
        
    # Format results
    feature_importance = []
    for idx, f in enumerate(features):
        feat_name = f["name"]
        importance = float(mean_abs_shap[idx]) if idx < len(mean_abs_shap) else 0.0
        feature_importance.append({
            "feature": feat_name,
            "importance": round(importance, 4)
        })
        
    # Sort by importance descending
    feature_importance.sort(key=lambda x: x["importance"], reverse=True)
    
    return {
        "model_id": model_id,
        "feature_importance": feature_importance
    }
