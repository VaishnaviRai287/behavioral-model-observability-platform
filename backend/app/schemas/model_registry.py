from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional

class ModelSchemaDefinition(BaseModel):
    """
    Defines the shape and datatype specifications of model inputs or outputs.
    E.g. features: [{ "name": "age", "type": "float" }]
    """
    features: List[Dict[str, Any]] = Field(
        ..., 
        description="List of features/tensors with name, data type, and shape constraints."
    )

class ModelRegisterCreate(BaseModel):
    name: str = Field(..., max_length=255, json_schema_extra={"example": "churn_model"})
    version: str = Field(..., max_length=50, json_schema_extra={"example": "1.0.0"})
    framework: str = Field(..., json_schema_extra={"example": "scikit-learn"})
    task_type: str = Field(..., json_schema_extra={"example": "tabular_classification"})
    artifact_uri: str = Field(..., json_schema_extra={"example": "/models/churn_v1.joblib"})
    input_schema: ModelSchemaDefinition
    output_schema: ModelSchemaDefinition
    status: Optional[str] = Field("registered", json_schema_extra={"example": "registered"})

class ModelRegisterResponse(BaseModel):
    id: UUID
    name: str
    version: str
    framework: str
    task_type: str
    artifact_uri: str
    input_schema: ModelSchemaDefinition
    output_schema: ModelSchemaDefinition
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Prediction schemas ---

class PredictionPayload(BaseModel):
    """
    Inputs sent to the predict API route.
    """
    inputs: List[Dict[str, Any]] = Field(
        ...,
        json_schema_extra={
            "example": [
                {"tenure": 12, "monthly_charges": 70.5}
            ]
        }
    )

class PredictionResponse(BaseModel):
    """
    Outputs returned by the predict API route.
    """
    predictions: List[Any] = Field(..., description="Array of prediction outcomes (classes/integers).")
    probabilities: Optional[List[List[float]]] = Field(None, description="2D array of class probabilities.")