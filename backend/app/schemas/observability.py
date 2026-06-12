from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, List, Optional

class AlertResponse(BaseModel):
    id: UUID
    model_id: UUID
    alert_type: str
    severity: str
    message: str
    metric_value: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MetricStatusResponse(BaseModel):
    model_id: UUID
    recent_inferences_count: int
    latest_latent_distance: Optional[float] = None
    max_ks_statistic: float
    max_psi_value: float

class ChangelogResponse(BaseModel):
    model_id_a: UUID
    model_id_b: UUID
    changelog: str

class AlertExplanationResponse(BaseModel):
    alert_id: UUID
    explanation: str
