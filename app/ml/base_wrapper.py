from abc import ABC, abstractmethod

import numpy as np

from app.ml.prediction_result import PredictionResult


class BaseModelWrapper(ABC):
    """
    Abstract base class for all model wrappers.

    Every framework-specific wrapper (sklearn, PyTorch, ONNX) must:
    1. Inherit from this class
    2. Implement load() to load the model from disk
    3. Implement predict() to run inference

    This class defines the CONTRACT — what any wrapper must provide.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self._model = None
        self.load()

    @abstractmethod
    def load(self) -> None:
        """Load the model artifact from disk into memory."""
        ...

    @abstractmethod
    def predict(self, input_array: np.ndarray) -> PredictionResult:
        """
        Run inference on a single input.

        Args:
            input_array: A 2D numpy array of shape (1, n_features).
                         Always 2D even for a single sample.

        Returns:
            PredictionResult with predicted_class, confidence, raw_output.
        """
        ...
