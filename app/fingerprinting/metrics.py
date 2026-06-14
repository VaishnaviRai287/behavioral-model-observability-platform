import math

import numpy as np
from sqlalchemy.orm import Session

from app.models.probe_result import ProbeResult
from app.models.probe_session import ProbeSession

UNCERTAINTY_THRESHOLD = 0.6   # probes below this confidence count as "uncertain"
N_HISTOGRAM_BINS = 10         # confidence range [0,1] split into 10 bins


def compute_fingerprint_metrics(db: Session, session: ProbeSession) -> dict:
    """
    Compute all fingerprint metrics from a completed probe session.

    Reads all ProbeResult rows for the session and computes:
    - confidence_histogram: normalized 10-bin distribution of confidence values
    - entropy: average prediction entropy across all probes
    - uncertainty_rate: fraction of probes with confidence < UNCERTAINTY_THRESHOLD
    - class_bias: fraction of probes that predicted the dominant class

    Args:
        db:      Active database session
        session: A completed ProbeSession (status == "done")

    Returns:
        Dict of metric values ready to pass to Fingerprint ORM constructor.
    """

    # ── Load all individual probe results ─────────────────────────────────────
    results = (
        db.query(ProbeResult)
        .filter(ProbeResult.session_id == session.id)
        .all()
    )

    if not results:
        raise ValueError(f"No probe results found for session {session.id}")

    confidences = np.array([r.confidence for r in results])
    raw_outputs = [r.raw_output for r in results]

    # ── Metric 1: Confidence Histogram ────────────────────────────────────────
    counts, _ = np.histogram(confidences, bins=N_HISTOGRAM_BINS, range=(0.0, 1.0))
    # Normalize: convert raw counts to fractions summing to 1.0
    total = counts.sum()
    histogram = (counts / total).tolist() if total > 0 else [0.0] * N_HISTOGRAM_BINS

    # ── Metric 2: Average Prediction Entropy ──────────────────────────────────
    # For each prediction, compute Shannon entropy of the output distribution
    # H = -Σ p * log2(p) for each class probability p > 0
    # Normalize by log2(n_classes) so entropy is in [0, 1]
    entropies = []
    for raw_output in raw_outputs:
        probs = np.array(raw_output, dtype=float)
        n_classes = len(probs)
        if n_classes <= 1:
            entropies.append(0.0)
            continue
        max_entropy = math.log2(n_classes)   # entropy of uniform distribution
        h = -sum(p * math.log2(p) for p in probs if p > 0)
        entropies.append(h / max_entropy)    # normalize to [0, 1]

    avg_entropy = float(np.mean(entropies))

    # ── Metric 3: Uncertainty Rate ────────────────────────────────────────────
    uncertain_count = int(np.sum(confidences < UNCERTAINTY_THRESHOLD))
    uncertainty_rate = uncertain_count / len(confidences)

    # ── Metric 4: Class Bias ──────────────────────────────────────────────────
    # Fraction of probes that predicted the single most common class
    class_dist = session.class_distribution or {}
    if class_dist:
        max_class_count = max(class_dist.values())
        class_bias = max_class_count / len(results)
    else:
        class_bias = 1.0   # fallback: no distribution info = assume fully biased

    return {
        "confidence_histogram": histogram,
        "entropy": avg_entropy,
        "uncertainty_rate": uncertainty_rate,
        "class_bias": class_bias,
        "mean_confidence": session.mean_confidence,
        "confidence_std": session.confidence_std,
    }
