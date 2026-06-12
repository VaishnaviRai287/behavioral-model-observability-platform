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
from app.crud.observability import observability_crud
from app.services.pytorch_models import StandardTabularClassifier

class BaseModelRunner(abc.ABC):
    """
    Abstract interface for executing model inferences and retrieving embeddings.
    """
    @abc.abstractmethod
    def predict(self, inputs: np.ndarray) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def get_latent_embeddings(self, inputs: np.ndarray) -> Optional[np.ndarray]:
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

    def get_latent_embeddings(self, inputs: np.ndarray) -> Optional[np.ndarray]:
        # Scikit-learn tabular models do not have neural embeddings, return None
        return None

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

    def get_latent_embeddings(self, inputs: np.ndarray) -> Optional[np.ndarray]:
        # Convert numpy array input to torch float tensor
        tensor_inputs = torch.tensor(inputs, dtype=torch.float32)
        activations = []
        
        # Capture the output of the hidden layer (layer 1: ReLU)
        def hook(module, input, output):
            activations.append(output.detach().cpu().numpy())
            
        handle = self.model.network[1].register_forward_hook(hook)
        
        with torch.no_grad():
            self.model(tensor_inputs)
            
        handle.remove()
        return activations[0]

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

    async def predict(self, db: AsyncSession, model_id: UUID, raw_inputs: List[Dict[str, Any]], log_inferences: bool = True) -> Dict[str, Any]:
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
            results = runner.predict(input_array)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error running inference during model execution: {str(e)}"
            )

        # 5. Extract and Log Observability parameters asynchronously
        if log_inferences:
            embeddings = runner.get_latent_embeddings(input_array)
            for i, record in enumerate(raw_inputs):
                emb_list = None
                if embeddings is not None:
                    emb_list = embeddings[i].tolist()
                    
                prob_list = results["probabilities"]
                confidence = max(prob_list[i]) if prob_list is not None else 1.0
                
                await observability_crud.create_log(
                    db=db,
                    model_id=model_id,
                    features=record,
                    prediction=results["predictions"][i],
                    confidence=confidence,
                    latent_embedding=emb_list
                )
                
            # Trigger Celery drift detection task
            try:
                from app.tasks import process_observability_check
                process_observability_check.delay(str(model_id))
            except ImportError:
                pass # Fail silently if celery is not configured (e.g. testing environments)

        return results

prediction_service = PredictionService()