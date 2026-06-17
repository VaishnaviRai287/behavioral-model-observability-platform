from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: str
    model_id: str
    alert_type: str
    severity: str
    metadata: dict[str, Any] = Field(validation_alias="alert_metadata")
    resolved_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class DriftEventResponse(BaseModel):
    id: str
    model_id: str
    feature_name: str
    ks_statistic: float
    psi_score: float
    severity: str
    window_start: datetime
    window_end: datetime
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ModelHealthResponse(BaseModel):
    novelty_rate: float
    drift_scores: dict[str, float]
    active_alerts: int
