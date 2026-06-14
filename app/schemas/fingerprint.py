from datetime import datetime

from pydantic import BaseModel, Field


class FingerprintResponse(BaseModel):
    """A computed behavioral fingerprint for one probe session."""
    fingerprint_id: str = Field(alias="id")
    session_id: str
    model_id: str
    confidence_histogram: list[float]
    entropy: float
    uncertainty_rate: float
    class_bias: float
    mean_confidence: float
    confidence_std: float
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ComparisonResult(BaseModel):
    """Result of comparing two fingerprints."""
    fingerprint_a_id: str
    fingerprint_b_id: str
    histogram_distance: float   # Wasserstein distance [0, ∞) — lower is more similar
    class_bias_delta: float     # |bias_a - bias_b| [0, 1]
    entropy_delta: float        # |entropy_a - entropy_b| [0, 1]
    similarity_score: float     # composite score [0, 1] — 1.0 = identical
    verdict: str                # "stable" | "drifted" | "severely_drifted"
