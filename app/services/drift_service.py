import math
from collections import Counter

import numpy as np
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.fingerprinting.comparator import compare_fingerprints
from app.models.fingerprint import Fingerprint
from app.models.prediction_log import PredictionLog

UNCERTAINTY_THRESHOLD = 0.6
N_HISTOGRAM_BINS = 10


def _compute_live_metrics(logs: list[PredictionLog]) -> dict:
    """Compute the same fingerprint-style metrics as compute_fingerprint_metrics(), from prediction logs instead of probe results."""
    confidences = np.array([log.confidence for log in logs])
    raw_outputs = [log.raw_output for log in logs]

    counts, _ = np.histogram(confidences, bins=N_HISTOGRAM_BINS, range=(0.0, 1.0))
    total = counts.sum()
    histogram = (counts / total).tolist() if total > 0 else [0.0] * N_HISTOGRAM_BINS

    entropies = []
    for raw_output in raw_outputs:
        probs = np.array(raw_output, dtype=float)
        n_classes = len(probs)
        if n_classes <= 1:
            entropies.append(0.0)
            continue
        max_entropy = math.log2(n_classes)
        h = -sum(p * math.log2(p) for p in probs if p > 0)
        entropies.append(h / max_entropy)
    avg_entropy = float(np.mean(entropies))

    uncertain_count = int(np.sum(confidences < UNCERTAINTY_THRESHOLD))
    uncertainty_rate = uncertain_count / len(confidences)

    class_counts = Counter(log.predicted_class for log in logs)
    max_class_count = max(class_counts.values())
    class_bias = max_class_count / len(logs)

    return {
        "confidence_histogram": histogram,
        "entropy": avg_entropy,
        "uncertainty_rate": uncertainty_rate,
        "class_bias": class_bias,
        "mean_confidence": float(np.mean(confidences)),
        "confidence_std": float(np.std(confidences)),
    }


def get_drift_status(db: Session, model_id: str, n_recent: int = 100) -> dict:
    """Compare a live-traffic fingerprint against the model's stored baseline fingerprint."""
    reference_fp = (
        db.query(Fingerprint)
        .filter(Fingerprint.model_id == model_id)
        .order_by(Fingerprint.created_at.desc())
        .first()
    )
    if not reference_fp:
        raise HTTPException(
            status_code=404,
            detail="No fingerprint found for this model. Run a probe first."
        )

    logs = (
        db.query(PredictionLog)
        .filter(PredictionLog.model_id == model_id)
        .order_by(PredictionLog.created_at.desc())
        .limit(n_recent)
        .all()
    )
    if len(logs) < 10:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 10 prediction logs for drift detection, found {len(logs)}"
        )

    live_metrics = _compute_live_metrics(logs)

    # Not persisted — only exists to hand a Fingerprint-shaped object to the comparator.
    live_fp = Fingerprint(
        id="live",
        session_id="live",
        model_id=model_id,
        **live_metrics,
    )

    comparison = compare_fingerprints(reference_fp, live_fp)

    return {
        "model_id": model_id,
        "reference_fingerprint_id": reference_fp.id,
        "n_recent_predictions": len(logs),
        "similarity_score": comparison["similarity_score"],
        "verdict": comparison["verdict"],
        "details": {
            "histogram_distance": comparison["histogram_distance"],
            "class_bias_delta": comparison["class_bias_delta"],
            "entropy_delta": comparison["entropy_delta"],
        },
    }
