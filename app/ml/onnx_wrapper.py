import numpy as np
import onnxruntime as ort

from app.ml.base_wrapper import BaseModelWrapper
from app.ml.prediction_result import PredictionResult


class ONNXWrapper(BaseModelWrapper):
    """
    Wrapper for ONNX models saved as .onnx files.

    ONNX (Open Neural Network Exchange) is a framework-agnostic model format.
    Models from sklearn, PyTorch, TensorFlow, etc. can all be exported to ONNX.
    """

    def load(self) -> None:
        """Create an ONNX Runtime inference session from the model file."""
        # InferenceSession loads and optimizes the model for the current hardware
        self._session = ort.InferenceSession(
            self.file_path,
            providers=["CPUExecutionProvider"],  # use CPU (no GPU assumption)
        )
        # Get the name of the input node — needed when calling run()
        self._input_name = self._session.get_inputs()[0].name

    def predict(self, input_array: np.ndarray) -> PredictionResult:
        """Run standard inference."""
        result, _ = self.predict_with_activations(input_array)
        return result

    def predict_with_activations(self, input_array: np.ndarray) -> tuple[PredictionResult, np.ndarray]:
        """Run inference and return prediction + proxy activation vector."""
        onnx_input = {self._input_name: input_array.astype(np.float32)}
        outputs = self._session.run(None, onnx_input)
        probs = outputs[0][0]

        if abs(probs.sum() - 1.0) > 0.01:
            probs = np.exp(probs) / np.exp(probs).sum()

        predicted_class = int(np.argmax(probs))
        confidence = float(probs[predicted_class])
        raw_output = probs.tolist()

        result = PredictionResult(
            predicted_class=predicted_class,
            confidence=confidence,
            raw_output=raw_output,
        )
        # Use full class probability list as proxy activation representation
        activations = np.array([raw_output] * len(input_array))
        return result, activations
