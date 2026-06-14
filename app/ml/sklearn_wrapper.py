import pickle

import numpy as np

from app.ml.base_wrapper import BaseModelWrapper
from app.ml.prediction_result import PredictionResult


class SklearnWrapper(BaseModelWrapper):
    """Wrapper for scikit-learn models saved as .pkl or .joblib files."""

    def load(self) -> None:
        """Load a pickled sklearn model from disk."""
        with open(self.file_path, "rb") as f:
            self._model = pickle.load(f)

    def predict(self, input_array: np.ndarray) -> PredictionResult:
        """
        Run inference using the sklearn model.

        sklearn models that support predict_proba() return class probabilities.
        Models that don't (e.g., LinearSVC) fall back to hard predictions.
        """
        if hasattr(self._model, "predict_proba"):
            # predict_proba returns shape (n_samples, n_classes)
            # e.g. [[0.13, 0.87]] for a binary classifier
            proba = self._model.predict_proba(input_array)[0]  # take first (only) sample
            predicted_class = int(np.argmax(proba))            # index of highest prob
            confidence = float(proba[predicted_class])          # that probability
            raw_output = proba.tolist()                         # full distribution
        else:
            # Fallback: model doesn't support probabilities
            # predict() returns class label directly
            prediction = self._model.predict(input_array)[0]
            predicted_class = int(prediction)
            confidence = 1.0       # hard prediction = 100% confident (no probability)
            raw_output = [float(predicted_class)]

        return PredictionResult(
            predicted_class=predicted_class,
            confidence=confidence,
            raw_output=raw_output,
        )
