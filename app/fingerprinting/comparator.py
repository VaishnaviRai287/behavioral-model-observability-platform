import numpy as np
from scipy.stats import wasserstein_distance

from app.models.fingerprint import Fingerprint

# Bin centers for 10 bins in [0, 1]
# [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]
BIN_CENTERS = np.arange(0.05, 1.0, 0.1)

STABLE_THRESHOLD = 0.90
DRIFTED_THRESHOLD = 0.70


def compare_fingerprints(fp_a: Fingerprint, fp_b: Fingerprint) -> dict:
    """
    Compare two fingerprints and compute a similarity score.

    Computes:
    - Wasserstein distance between confidence histograms
    - Absolute delta in class_bias
    - Absolute delta in normalized entropy
    - Weighted composite similarity score [0, 1]
    - Verdict: "stable" | "drifted" | "severely_drifted"

    Args:
        fp_a: First fingerprint
        fp_b: Second fingerprint

    Returns:
        Dict with all comparison metrics.
    """

    hist_a = np.array(fp_a.confidence_histogram)
    hist_b = np.array(fp_b.confidence_histogram)

    # ── Wasserstein Distance ──────────────────────────────────────────────────
    # Treats the histogram as a weighted distribution over bin centers.
    # Returns the Earth Mover's Distance — how far mass must shift to transform
    # hist_a into hist_b, measured in units of bin width (max possible = 1.0).
    if hist_a.sum() > 0 and hist_b.sum() > 0:
        hist_dist = float(wasserstein_distance(
            BIN_CENTERS, BIN_CENTERS,
            u_weights=hist_a,
            v_weights=hist_b,
        ))
    else:
        hist_dist = 0.0

    # ── Class Bias Delta ─────────────────────────────────────────────────────
    bias_delta = float(abs(fp_a.class_bias - fp_b.class_bias))

    # ── Entropy Delta ────────────────────────────────────────────────────────
    entropy_delta = float(abs(fp_a.entropy - fp_b.entropy))

    # ── Composite Similarity Score ────────────────────────────────────────────
    # hist_dist is in [0, 1] for normalized histograms over [0, 1] range
    # bias_delta is in [0, 1] (both class_bias values are in [0, 1])
    # entropy_delta is in [0, 1] (both entropy values are in [0, 1])
    hist_similarity = max(0.0, 1.0 - hist_dist)       # 50% weight
    bias_similarity = max(0.0, 1.0 - bias_delta)       # 30% weight
    entropy_similarity = max(0.0, 1.0 - entropy_delta) # 20% weight

    similarity = (
        0.5 * hist_similarity
        + 0.3 * bias_similarity
        + 0.2 * entropy_similarity
    )
    similarity = float(np.clip(similarity, 0.0, 1.0))

    # ── Verdict ───────────────────────────────────────────────────────────────
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
