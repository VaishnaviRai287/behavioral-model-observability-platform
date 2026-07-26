import hashlib
import json
import os
from app.ml.loader import load_model

def compute_file_sha256(file_path: str) -> str:
    """Compute the SHA-256 hash of a file on disk."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_parameter_metadata(file_path: str, framework: str) -> dict:
    """Extract framework-specific parameter/hyperparameter metadata from the model."""
    metadata = {
        "file_sha256": compute_file_sha256(file_path),
        "file_size_bytes": os.path.getsize(file_path)
    }
    
    try:
        wrapper = load_model(file_path)
        wrapper.load()
        model_obj = getattr(wrapper, "_model", None)
        
        if framework == "sklearn" and model_obj:
            if hasattr(model_obj, "get_params"):
                raw_params = model_obj.get_params()
                serializable = {}
                for k, v in raw_params.items():
                    try:
                        json.dumps(v)
                        serializable[k] = v
                    except Exception:
                        serializable[k] = str(v)
                metadata["hyperparameters"] = serializable
                
        elif framework == "pytorch" and model_obj:
            if hasattr(model_obj, "state_dict"):
                state_dict = model_obj.state_dict()
                param_shapes = {}
                for k, v in state_dict.items():
                    param_shapes[k] = list(v.shape)
                metadata["parameter_shapes"] = param_shapes
                metadata["total_parameters"] = sum(v.numel() for v in model_obj.parameters() if hasattr(v, "numel"))
                
        elif framework == "tensorflow" and model_obj:
            if hasattr(model_obj, "count_params"):
                metadata["total_parameters"] = model_obj.count_params()
                layer_params = []
                for layer in model_obj.layers:
                    layer_params.append({
                        "name": layer.name,
                        "trainable": layer.trainable,
                        "parameters": layer.count_params() if hasattr(layer, "count_params") else 0
                    })
                metadata["layers"] = layer_params

    except Exception as e:
        metadata["load_error"] = str(e)
        
    return metadata

def generate_model_signature(file_path: str, framework: str, architecture: dict | None, input_schema: dict) -> str:
    """
    Generate a unique SHA-256 signature based on architecture, parameters metadata, and feature schema.
    """
    features = input_schema.get("features", [])
    # Sort features by name to ensure deterministic output
    sorted_features = sorted(features, key=lambda x: x.get("name", ""))
    
    arch_data = architecture or {}
    param_data = extract_parameter_metadata(file_path, framework)
    
    payload = {
        "features": sorted_features,
        "architecture": arch_data,
        "parameters": param_data
    }
    
    payload_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
