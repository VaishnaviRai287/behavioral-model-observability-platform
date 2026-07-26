import numpy as np
from scipy.stats import wasserstein_distance

from app.models.fingerprint import Fingerprint

# Bin centers for 10 bins in [0, 1]: [0.05, 0.15, ..., 0.95]
BIN_CENTERS = np.arange(0.05, 1.0, 0.1)

STABLE_THRESHOLD = 0.90
DRIFTED_THRESHOLD = 0.70


def compare_fingerprints(fp_a: Fingerprint, fp_b: Fingerprint) -> dict:
    """Compare two fingerprints and return a weighted similarity score with a stable/drifted/severely_drifted verdict."""
    hist_a = np.array(fp_a.confidence_histogram)
    hist_b = np.array(fp_b.confidence_histogram)

    # Earth Mover's Distance between the two confidence histograms, treated as
    # weighted distributions over bin centers — how far mass must shift to
    # turn hist_a into hist_b, in units of bin width (max possible = 1.0).
    if hist_a.sum() > 0 and hist_b.sum() > 0:
        hist_dist = float(wasserstein_distance(
            BIN_CENTERS, BIN_CENTERS,
            u_weights=hist_a,
            v_weights=hist_b,
        ))
    else:
        hist_dist = 0.0

    bias_delta = float(abs(fp_a.class_bias - fp_b.class_bias))
    entropy_delta = float(abs(fp_a.entropy - fp_b.entropy))

    # All three deltas are already in [0, 1]; weight histogram shift heaviest
    # since it captures the fullest picture of the confidence distribution.
    hist_similarity = max(0.0, 1.0 - hist_dist)
    bias_similarity = max(0.0, 1.0 - bias_delta)
    entropy_similarity = max(0.0, 1.0 - entropy_delta)

    similarity = (
        0.5 * hist_similarity
        + 0.3 * bias_similarity
        + 0.2 * entropy_similarity
    )
    similarity = float(np.clip(similarity, 0.0, 1.0))

    if similarity >= STABLE_THRESHOLD:
        verdict = "stable"
    elif similarity >= DRIFTED_THRESHOLD:
        verdict = "drifted"
    else:
        verdict = "severely_drifted"

    return {
        "fingerprint_a_id": fp_a.id,
        "fingerprint_b_id": fp_b.id,
        "histogram_distance": hist_dist,
        "class_bias_delta": bias_delta,
        "entropy_delta": entropy_delta,
        "similarity_score": similarity,
        "verdict": verdict,
    }
