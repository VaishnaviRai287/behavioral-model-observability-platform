import pickle
from pathlib import Path


def detect_framework(file_path: str) -> str:
    """
    Inspect a saved model file and return its framework.

    Returns one of: "sklearn", "pytorch", "tensorflow"
    Raises ValueError if the file cannot be identified.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    # PyTorch files use .pt or .pth extension
    if suffix in (".pt", ".pth"):
        return "pytorch"

    # TensorFlow Keras files use .h5 or .keras extension
    if suffix in (".h5", ".keras"):
        return "tensorflow"

    # TensorFlow SavedModel zipped archives or directories
    if suffix in (".zip", ".tar.gz", ".tgz"):
        import zipfile
        import tarfile

        is_tf_saved_model = False
        if suffix == ".zip":
            try:
                with zipfile.ZipFile(file_path, 'r') as zf:
                    names = zf.namelist()
                    if any("saved_model.pb" in name for name in names):
                        is_tf_saved_model = True
            except Exception as e:
                raise ValueError(f"Failed to inspect zip archive: {e}")
        else:
            try:
                with tarfile.open(file_path, 'r:*') as tf:
                    names = tf.getnames()
                    if any("saved_model.pb" in name for name in names):
                        is_tf_saved_model = True
            except Exception as e:
                raise ValueError(f"Failed to inspect tar archive: {e}")

        if is_tf_saved_model:
            return "tensorflow"
        raise ValueError("Archive does not contain a valid TensorFlow SavedModel (missing saved_model.pb).")

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
        f"Accepted: .pkl, .joblib, .pt, .pth, .h5, .keras, .zip, .tar.gz"
    )
