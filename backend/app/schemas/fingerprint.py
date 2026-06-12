from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, List

class FingerprintResponse(BaseModel):
    id: UUID
    model_id: UUID
    num_samples: int
    class_distribution: Dict[str, Any]
    confidence_distribution: Dict[str, Any]
    high_uncertainty_regions: Dict[str, Any]
    boundary_samples: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
