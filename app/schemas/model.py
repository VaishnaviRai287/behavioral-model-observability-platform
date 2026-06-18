from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeatureSpec(BaseModel):
    """Describes one feature in the input schema."""
    name: str
    type: str                   # "float", "int", "categorical"
    min: float | None = None    # used by probing engine for sampling bounds
    max: float | None = None
    categories: list[str] | None = None  # for categorical features


class InputSchema(BaseModel):
    """The full input schema: a list of feature specifications."""
    features: list[FeatureSpec]


class ModelCreateResponse(BaseModel):
    """Response returned after a successful model upload."""
    model_id: str = Field(alias="id")
    name: str
    framework: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ModelDetailResponse(BaseModel):
    """Full model detail response."""
    model_id: str = Field(alias="id")
    name: str
    framework: str
    file_path: str
    input_schema: dict[str, Any]
    architecture: dict[str, Any] | None = None
    status: str
    created_at: datetime
    baseline_mean: float | None = None
    baseline_std: float | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}



class ModelListItem(BaseModel):
    """Lightweight model list item."""
    model_id: str = Field(alias="id")
    name: str
    framework: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
