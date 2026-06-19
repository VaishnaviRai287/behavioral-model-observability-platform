import numpy as np
from collections import Counter
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.ml_model import MLModel
from app.models.prediction_log import PredictionLog
from app.models.probe_result import ProbeResult
from app.models.probe_session import ProbeSession

def analyze_dataset_health(db: Session, model_id: str) -> dict:
    """
    Run diagnostic dataset health analysis on production logs.
    Includes missing values, class imbalance, outliers (IQR), and duplicates.
    """
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    features = model.input_schema.get("features", [])
    
    # 1. Fetch prediction logs (production data)
    logs = (
        db.query(PredictionLog)
        .filter(PredictionLog.model_id == model_id)
        .order_by(PredictionLog.created_at.desc())
        .limit(1000)
        .all()
    )
    
    if not logs:
        return {
            "missing_values": {"total_missing": 0, "by_feature": {f["name"]: 0 for f in features}, "percentage": 0.0},
            "class_imbalance": {"counts": {}, "percentages": {}, "entropy": 0.0},
            "outliers": {"total_outliers": 0, "by_feature": {f["name"]: 0 for f in features}, "percentage": 0.0},
            "duplicates": {"duplicate_count": 0, "percentage": 0.0},
            "total_records": 0
        }

    total_records = len(logs)
    
    # ── A. Missing Values Analysis ───────────────────────────────────────────
    total_missing = 0
    missing_by_feature = {f["name"]: 0 for f in features}
    
    for log in logs:
        # Check raw input dictionary
        feat_dict = log.input_features or {}
        for f in features:
            name = f["name"]
            if name not in feat_dict or feat_dict[name] is None:
                missing_by_feature[name] += 1
                total_missing += 1
                
    missing_pct = (total_missing / (total_records * len(features))) * 100 if features else 0.0

    # ── B. Class Imbalance Analysis ──────────────────────────────────────────
    predicted_classes = [log.predicted_class for log in logs]
    class_counts = Counter(predicted_classes)
    
    class_percentages = {}
    entropy = 0.0
    if total_records > 0:
        for cls, count in class_counts.items():
            pct = (count / total_records) * 100
            class_percentages[str(cls)] = round(pct, 2)
            
        # Shannon Entropy of predictions class distribution
        probs = [count / total_records for count in class_counts.values()]
        entropy = -sum(p * np.log2(p) for p in probs)

    # ── C. Duplicate Records Analysis ────────────────────────────────────────
    # Serialize the inputs to check duplicates
    input_vectors = [tuple(log.input_vector) for log in logs if log.input_vector]
    total_vectors = len(input_vectors)
    unique_vectors = set(input_vectors)
    duplicate_count = total_vectors - len(unique_vectors)
    duplicate_pct = (duplicate_count / total_vectors) * 100 if total_vectors > 0 else 0.0

    # ── D. Outliers (IQR Method per Feature) ─────────────────────────────────
    # Fetch baseline probe distribution as reference for IQR boundaries
    session = (
        db.query(ProbeSession)
        .filter(ProbeSession.model_id == model_id, ProbeSession.status == "done")
        .order_by(ProbeSession.created_at.desc())
        .first()
    )
    
    # Defaults boundaries
    iqr_bounds = {}
    if session:
        probe_results = db.query(ProbeResult).filter(ProbeResult.session_id == session.id).all()
        if probe_results:
            baseline_matrix = np.array([pr.input_vector for pr in probe_results])
            for idx, f in enumerate(features):
                feat_values = baseline_matrix[:, idx]
                q75, q25 = np.percentile(feat_values, [75, 25])
                iqr = q75 - q25
                iqr_bounds[f["name"]] = (q25 - 1.5 * iqr, q75 + 1.5 * iqr)
                
    # Fallback to current production distribution if no baseline probing has run
    if not iqr_bounds and total_records >= 10:
        production_matrix = np.array([log.input_vector for log in logs if log.input_vector])
        if len(production_matrix) > 0:
            for idx, f in enumerate(features):
                feat_values = production_matrix[:, idx]
                q75, q25 = np.percentile(feat_values, [75, 25])
                iqr = q75 - q25
                iqr_bounds[f["name"]] = (q25 - 1.5 * iqr, q75 + 1.5 * iqr)

    outliers_by_feature = {f["name"]: 0 for f in features}
    total_outliers = 0
    
    for log in logs:
        if not log.input_vector:
            continue
        for idx, f in enumerate(features):
            name = f["name"]
            val = log.input_vector[idx]
            bounds = iqr_bounds.get(name)
            if bounds:
                lower, upper = bounds
                if val < lower or val > upper:
                    outliers_by_feature[name] += 1
                    total_outliers += 1
                    
    outliers_pct = (total_outliers / (total_records * len(features))) * 100 if features else 0.0

    return {
        "missing_values": {
            "total_missing": total_missing,
            "by_feature": missing_by_feature,
            "percentage": round(missing_pct, 2)
        },
        "class_imbalance": {
            "counts": {str(k): v for k, v in class_counts.items()},
            "percentages": class_percentages,
            "entropy": round(float(entropy), 4)
        },
        "outliers": {
            "total_outliers": total_outliers,
            "by_feature": outliers_by_feature,
            "percentage": round(outliers_pct, 2)
        },
        "duplicates": {
            "duplicate_count": duplicate_count,
            "percentage": round(duplicate_pct, 2)
        },
        "total_records": total_records
    }
