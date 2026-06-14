import pickle
from pathlib import Path


def detect_framework(file_path: str) -> str:
    """
    Inspect a saved model file and return its framework.

    Returns one of: "sklearn", "pytorch", "onnx"
    Raises ValueError if the file cannot be identified.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    # ONNX files always have .onnx extension — easy case
    if suffix == ".onnx":
        return "onnx"

    # PyTorch files use .pt extension
    # We import torch lazily to avoid import errors if torch isn't needed
    if suffix == ".pt":
        return "pytorch"

    # .pkl and .joblib are both pickle-based serialization formats
    # sklearn models saved with joblib or pickle both show up this way
    if suffix in (".pkl", ".joblib"):
        try:
            with open(file_path, "rb") as f:
                obj = pickle.load(f)

            # Check for sklearn: all sklearn estimators have these methods
            if hasattr(obj, "predict") and hasattr(obj, "fit"):
                return "sklearn"

            # Fallback: if it's a pickle file but not sklearn, we don't know
            raise ValueError(
                f"File {file_path} is a pickle file but does not appear to be "
                f"a scikit-learn model."
            )
        except Exception as e:
            raise ValueError(f"Failed to inspect model file: {e}") from e

    raise ValueError(
        f"Unsupported file extension: {suffix}. "
        f"Accepted: .pkl, .joblib, .pt, .onnx"
    )
