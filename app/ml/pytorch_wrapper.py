import numpy as np
import torch
import torch.nn.functional as F

from app.ml.base_wrapper import BaseModelWrapper
from app.ml.prediction_result import PredictionResult


class PyTorchWrapper(BaseModelWrapper):
    """
    Wrapper for PyTorch models saved as .pt files.

    Expects the file to contain a complete saved model (torch.save(model, path)),
    not just a state_dict (torch.save(model.state_dict(), path)).
    """

    def load(self) -> None:
        """Load a PyTorch model from disk and set it to evaluation mode."""
        self._model = torch.load(
            self.file_path,
            map_location="cpu",       # always load to CPU (no GPU assumption)
            weights_only=False,        # allow loading full model objects
        )
        self._model.eval()             # critical: disable dropout, batchnorm training behavior

    def predict(self, input_array: np.ndarray) -> PredictionResult:
        """
        Run inference using the PyTorch model.

        Converts numpy input → torch tensor → runs forward pass → applies softmax.
        """
        # Convert numpy array to PyTorch tensor
        # float32 is the standard dtype for neural network inputs
        tensor = torch.tensor(input_array, dtype=torch.float32)

        # Disable gradient computation — we're doing inference, not training
        # This saves memory and speeds up computation
        with torch.no_grad():
            logits = self._model(tensor)   # raw model output (not probabilities yet)

        # Apply softmax to convert logits → probabilities that sum to 1.0
        # dim=1 means "apply softmax across the class dimension"
        probs = F.softmax(logits, dim=1)[0]   # shape: (n_classes,)

        predicted_class = int(torch.argmax(probs).item())
        confidence = float(probs[predicted_class].item())
        raw_output = probs.tolist()

        return PredictionResult(
            predicted_class=predicted_class,
            confidence=confidence,
            raw_output=raw_output,
        )
