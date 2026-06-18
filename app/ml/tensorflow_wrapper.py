import os
import shutil
import zipfile
import numpy as np
from pathlib import Path
from app.ml.base_wrapper import BaseModelWrapper
from app.ml.prediction_result import PredictionResult

class TensorFlowWrapper(BaseModelWrapper):
    """
    Wrapper for TensorFlow models saved as .h5, .keras, or SavedModel directories.
    """

    def load(self) -> None:
        """Load the TensorFlow model into memory."""
        import tensorflow as tf
        
        path = Path(self.file_path)
        suffix = path.suffix.lower()
        
        if suffix in (".zip", ".tar.gz", ".tgz"):
            # It's an extracted archive
            extract_dir = path.with_name(f"{path.stem}_extracted")
            if not extract_dir.exists():
                raise FileNotFoundError(f"Extracted directory {extract_dir} does not exist.")
            
            # Find the directory containing saved_model.pb
            try:
                model_dir = self._find_saved_model_dir(extract_dir)
                # Load the SavedModel
                self._model = tf.saved_model.load(str(model_dir))
            except Exception:
                # Fallback: try loading as keras model
                model_dir = self._find_saved_model_dir(extract_dir)
                self._model = tf.keras.models.load_model(str(model_dir))
        else:
            # Load as keras model (.h5 or .keras)
            self._model = tf.keras.models.load_model(self.file_path)

    def _find_saved_model_dir(self, base_dir: Path) -> Path:
        if (base_dir / "saved_model.pb").exists():
            return base_dir
        for p in base_dir.rglob("saved_model.pb"):
            return p.parent
        raise FileNotFoundError("Could not find saved_model.pb in the extracted directory.")

    def predict(self, input_array: np.ndarray) -> PredictionResult:
        result, _ = self.predict_with_activations(input_array)
        return result

    def predict_with_activations(self, input_array: np.ndarray) -> tuple[PredictionResult, np.ndarray]:
        import tensorflow as tf
        
        # Convert inputs to float32
        input_tensor = tf.convert_to_tensor(input_array, dtype=tf.float32)
        
        # Check if model has standard call or is a Keras model
        if hasattr(self._model, "predict") or hasattr(self._model, "layers"):
            # Keras model
            preds = self._model(input_tensor, training=False)
        else:
            # SavedModel (might need signature)
            if hasattr(self._model, "signatures") and "serving_default" in self._model.signatures:
                func = self._model.signatures["serving_default"]
                # Get the first input key
                input_key = list(func.structured_input_signature[1].keys())[0]
                outputs = func(**{input_key: input_tensor})
                # Get the first output key
                output_key = list(outputs.keys())[0]
                preds = outputs[output_key]
            else:
                preds = self._model(input_tensor)
                
        # Convert to numpy
        if hasattr(preds, "numpy"):
            preds_np = preds.numpy()
        else:
            preds_np = np.array(preds)
            
        probs = preds_np[0]
        
        # Normalize if not probabilities
        if abs(probs.sum() - 1.0) > 0.01:
            # Softmax normalization
            probs = np.exp(probs) / np.exp(probs).sum()
            
        predicted_class = int(np.argmax(probs))
        confidence = float(probs[predicted_class])
        raw_output = probs.tolist()
        
        result = PredictionResult(
            predicted_class=predicted_class,
            confidence=confidence,
            raw_output=raw_output,
        )
        
        # Extract activations
        activations = None
        try:
            # If it's a Keras model, try to use the penultimate layer output
            if hasattr(self._model, "layers") and len(self._model.layers) >= 2:
                feat_extractor = tf.keras.Model(inputs=self._model.inputs, outputs=self._model.layers[-2].output)
                feat_out = feat_extractor(input_tensor, training=False)
                activations = feat_out.numpy()
        except Exception:
            pass
            
        if activations is None:
            activations = np.array([raw_output] * len(input_array))
            
        if len(activations.shape) == 1:
            activations = activations.reshape(-1, 1)
            
        return result, activations
