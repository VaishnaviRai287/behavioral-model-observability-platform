from app.ml.base_wrapper import BaseModelWrapper
from app.ml.onnx_wrapper import ONNXWrapper
from app.ml.pytorch_wrapper import PyTorchWrapper
from app.ml.sklearn_wrapper import SklearnWrapper
from app.utils.framework_detector import detect_framework


def load_model(file_path: str) -> BaseModelWrapper:
    """Detect the model's framework and return the matching wrapper."""
    framework = detect_framework(file_path)

    if framework == "sklearn":
        return SklearnWrapper(file_path)
    elif framework == "pytorch":
        return PyTorchWrapper(file_path)
    elif framework == "onnx":
        return ONNXWrapper(file_path)
    elif framework == "tensorflow":
        from app.ml.tensorflow_wrapper import TensorFlowWrapper
        return TensorFlowWrapper(file_path)
    else:
        raise ValueError(f"Unsupported framework: {framework}")
