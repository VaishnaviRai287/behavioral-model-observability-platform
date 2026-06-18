from app.ml.base_wrapper import BaseModelWrapper
from app.ml.onnx_wrapper import ONNXWrapper
from app.ml.pytorch_wrapper import PyTorchWrapper
from app.ml.sklearn_wrapper import SklearnWrapper
from app.utils.framework_detector import detect_framework


def load_model(file_path: str) -> BaseModelWrapper:
    """
    Factory function: inspect a model file and return the correct wrapper.

    This is the only function the rest of the codebase needs to call.
    The caller doesn't need to know which framework the model uses.

    Args:
        file_path: Path to the saved model file.

    Returns:
        A wrapper instance that implements BaseModelWrapper.

    Raises:
        ValueError: If the file format is not supported.
    """
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
