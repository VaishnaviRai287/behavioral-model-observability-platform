import abc
import os
from uuid import UUID
import joblib
import numpy as np
import torch
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional

from app.crud.model_registry import model_registry_crud
from app.services.pytorch_models import StandardTabularClassifier

class BaseModelRunner(abc.ABC):
    """
    Abstract interface for executing model inferences.
    """
    @abc.abstractmethod
    def predict(self, inputs: np.ndarray) -> Dict[str, Any]:
        pass

class ScikitLearnRunner(BaseModelRunner):
    """
    Loads and executes inferences for Scikit-Learn models.
    """
    def __init__(self, artifact_path: str):
        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"Model weight not found at {artifact_path}")
        self.model = joblib.load(artifact_path)

    def predict(self, inputs: np.ndarray) -> Dict[str, Any]:
        predictions = self.model.predict(inputs)
        
        # Get class probabilities if supported, else default to nulls
        probabilities = None
        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(inputs).tolist()
            
        return {
            "predictions": predictions.tolist(),
            "probabilities": probabilities
        }

class PyTorchRunner(BaseModelRunner):
    """
    Loads and executes inferences for PyTorch state-dicts.
    """
    def __init__(self, artifact_path: str, input_dim: int):
        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"Model weight not found at {artifact_path}")
            
        # Instantiate standard architecture
        self.model = StandardTabularClassifier(input_dim=input_dim)
        
        # Load state dict safely using weights_only=True
        state_dict = torch.load(artifact_path, map_location=torch.device('cpu'), weights_only=True)
        self.model.load_state_dict(state_dict)
        self.model.eval()  # Put in evaluation mode

    def predict(self, inputs: np.ndarray) -> Dict[str, Any]:
        # Convert numpy array input to torch float tensor
        tensor_inputs = torch.tensor(inputs, dtype=torch.float32)
        
        with torch.no_grad():
            logits = self.model(tensor_inputs)
            probabilities = torch.softmax(logits, dim=1)
            predictions = torch.argmax(logits, dim=1)
            
        return {
            "predictions": predictions.numpy().tolist(),
            "probabilities": probabilities.numpy().tolist()
        }

class PredictionService:
    """
    Coordinates model lookups, loading, caching, and inference executions.
    """
    def __init__(self):
        # Global loaded model cache mapping: model_id -> BaseModelRunner
        self._model_cache: Dict[UUID, BaseModelRunner] = {}

    def clear_cache(self):
        self._model_cache.clear()

    async def get_or_load_model(self, model_id: UUID, framework: str, artifact_path: str, input_dim: int) -> BaseModelRunner:
        if model_id in self._model_cache:
            return self._model_cache[model_id]
            
        if framework.lower() == "scikit-learn":
            runner = ScikitLearnRunner(artifact_path)
        elif framework.lower() == "pytorch":
            runner = PyTorchRunner(artifact_path, input_dim=input_dim)
        else:
            raise ValueError(f"Unsupported model framework: '{framework}'")
            
        self._model_cache[model_id] = runner
        return runner

    async def predict(self, db: AsyncSession, model_id: UUID, raw_inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        # 1. Fetch Model from Database Registry
        model = await model_registry_crud.get(db, model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model with ID '{model_id}' is not registered."
            )

        # 2. Validate inputs against Schema
        features = model.input_schema.get("features", [])
        input_dim = len(features)
        
        if not raw_inputs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input records cannot be empty."
            )

        # Flatten records into a 2D numpy array matching schema order
        processed_inputs = []
        for idx, record in enumerate(raw_inputs):
            row = []
            for feature in features:
                name = feature["name"]
                expected_type = feature.get("type", "float")
                
                if name not in record:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Record {idx} is missing required feature '{name}'."
                    )
                
                val = record[name]
                # Cast value types
                try:
                    if expected_type == "int":
                        row.append(int(val))
                    else:
                        row.append(float(val))
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Failed to cast feature '{name}' to type '{expected_type}' for record {idx}."
                    )
            processed_inputs.append(row)

        input_array = np.array(processed_inputs, dtype=np.float32)

        # 3. Retrieve model from cache or load it
        try:
            runner = await self.get_or_load_model(
                model_id=model.id,
                framework=model.framework,
                artifact_path=model.artifact_uri,
                input_dim=input_dim
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load model weights binary: {str(e)}"
            )

        # 4. Run Inference
        try:
            return runner.predict(input_array)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error running inference during model execution: {str(e)}"
            )

prediction_service = PredictionService()