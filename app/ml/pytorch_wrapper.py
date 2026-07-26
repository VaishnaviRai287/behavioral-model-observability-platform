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
        """Run standard inference."""
        result, _ = self.predict_with_activations(input_array)
        return result

    def predict_with_activations(self, input_array: np.ndarray) -> tuple[PredictionResult, np.ndarray]:
        """Run inference, returning the prediction plus the penultimate layer's activation vector."""
        tensor = torch.tensor(input_array, dtype=torch.float32)

        # Leaf modules (no children, e.g. nn.Linear/nn.ReLU) — the second-to-last
        # one is treated as the model's latent representation.
        leaf_modules = [m for m in self._model.modules() if len(list(m.children())) == 0]
        if len(leaf_modules) >= 2:
            target_layer = leaf_modules[-2]
        else:
            target_layer = leaf_modules[-1]

        activations = []
        def hook_fn(module, input_val, output_val):
            t = output_val.detach().cpu().numpy()
            if len(t.shape) > 2:
                t = t.reshape(t.shape[0], -1)
            elif len(t.shape) == 1:
                t = t.reshape(1, -1)
            activations.append(t)

        handle = target_layer.register_forward_hook(hook_fn)

        try:
            with torch.no_grad():
                logits = self._model(tensor)

            probs = F.softmax(logits, dim=1)[0]
            predicted_class = int(torch.argmax(probs).item())
            confidence = float(probs[predicted_class].item())
            raw_output = probs.tolist()

            if activations:
                activation_vector = np.vstack(activations)
            else:
                activation_vector = np.empty((input_array.shape[0], 0))

            result = PredictionResult(
                predicted_class=predicted_class,
                confidence=confidence,
                raw_output=raw_output,
            )
            return result, activation_vector
        finally:
            handle.remove()
