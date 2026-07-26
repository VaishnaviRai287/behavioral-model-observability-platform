import math

import numpy as np
from sqlalchemy.orm import Session

from app.models.probe_result import ProbeResult
from app.models.probe_session import ProbeSession

UNCERTAINTY_THRESHOLD = 0.6   # probes below this confidence count as "uncertain"
N_HISTOGRAM_BINS = 10         # confidence range [0,1] split into 10 bins


def compute_fingerprint_metrics(db: Session, session: ProbeSession) -> dict:
    """Compute confidence histogram, entropy, uncertainty rate, and class bias for a completed probe session."""
    results = (
        db.query(ProbeResult)
        .filter(ProbeResult.session_id == session.id)
        .all()
    )

    if not results:
        raise ValueError(f"No probe results found for session {session.id}")

    confidences = np.array([r.confidence for r in results])
    raw_outputs = [r.raw_output for r in results]

    counts, _ = np.histogram(confidences, bins=N_HISTOGRAM_BINS, range=(0.0, 1.0))
    total = counts.sum()
    histogram = (counts / total).tolist() if total > 0 else [0.0] * N_HISTOGRAM_BINS

    # Shannon entropy of each output distribution, normalized by log2(n_classes)
    # so the result stays in [0, 1] regardless of class count.
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

    # Fraction of probes predicting the single most common class.
    class_dist = session.class_distribution or {}
    if class_dist:
        max_class_count = max(class_dist.values())
        class_bias = max_class_count / len(results)
    else:
        class_bias = 1.0

    return {
        "confidence_histogram": histogram,
        "entropy": avg_entropy,
        "uncertainty_rate": uncertainty_rate,
        "class_bias": class_bias,
        "mean_confidence": session.mean_confidence,
        "confidence_std": session.confidence_std,
    }
