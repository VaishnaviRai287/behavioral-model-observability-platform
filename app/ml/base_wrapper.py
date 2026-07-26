from abc import ABC, abstractmethod

import numpy as np

from app.ml.prediction_result import PredictionResult


class BaseModelWrapper(ABC):
    """Common interface every framework-specific wrapper (sklearn, PyTorch, ONNX) implements."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._model = None
        self.load()

    @abstractmethod
    def load(self) -> None:
        """Load the model artifact from disk into memory."""
        ...

    def predict(self, input_array: np.ndarray) -> PredictionResult:
        """Run inference on a single input (2D array of shape (1, n_features))."""
        result, _ = self.predict_with_activations(input_array)
        return result

    @abstractmethod
    def predict_with_activations(self, input_array: np.ndarray) -> tuple[PredictionResult, np.ndarray]:
        """Run inference, returning the prediction plus its internal activation vector."""
        ...
