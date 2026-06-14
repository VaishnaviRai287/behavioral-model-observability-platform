from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProbeRequest(BaseModel):
    """Request body for starting a probe session."""
    n_probes: int = Field(default=1000, ge=10, le=10000)
    # ge=10: minimum 10 probes (too few is statistically meaningless)
    # le=10000: maximum 10000 probes (more = very slow synchronous request)


class ProbeSessionResponse(BaseModel):
    """Response after a probe session completes."""
    session_id: str = Field(alias="id")
    model_id: str
    n_probes: int
    status: str
    mean_confidence: float | None
    confidence_std: float | None
    dominant_class: int | None
    class_distribution: dict[str, Any] | None
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
