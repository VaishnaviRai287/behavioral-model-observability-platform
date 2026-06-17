from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """
    Request body for a live prediction.

    features: dict mapping feature name → value.
    Must match the model's declared input schema.

    Example:
        {"features": {"x1": 0.8, "x2": 0.9}}
    """
    features: dict[str, Any]


class PredictionResponse(BaseModel):
    """Response from a live prediction."""
    model_id: str
    predicted_class: int
    confidence: float
    raw_output: list[float]
    latency_ms: float
    faiss_distance: float | None = None
    novelty_flag: bool | None = None


class PredictionLogResponse(BaseModel):
    """Full prediction log record (for audit trail endpoint)."""
    log_id: str = Field(alias="id")
    model_id: str
    input_features: dict[str, Any]
    predicted_class: int
    output_class: int = Field(validation_alias="predicted_class")
    confidence: float
    raw_output: list[float]
    latency_ms: float
    faiss_distance: float | None = None
    novelty_flag: bool | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}

