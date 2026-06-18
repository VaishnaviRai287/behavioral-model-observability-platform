import json
import zipfile
from pathlib import Path
import torch

def extract_architecture(file_path: str, framework: str) -> dict | None:
    """
    Automatically extracts model architecture details as a JSON-serializable dict.
    Returns:
        A dictionary containing architectural details (e.g. {"layers": [...]}) or None.
    """
    path = Path(file_path)
    
    if framework == "pytorch":
        try:
            # Load PyTorch model
            model = torch.load(file_path, map_location="cpu", weights_only=False)
            layers = []
            
            # Helper to inspect model
            if hasattr(model, "named_modules"):
                for name, module in model.named_modules():
                    # Only include leaf layers or primary layers to avoid huge tree
                    if len(list(module.children())) == 0:
                        layers.append({
                            "name": name,
                            "type": module.__class__.__name__,
                            "details": str(module)
                        })
            elif hasattr(model, "children"):
                for idx, child in enumerate(model.children()):
                    layers.append({
                        "name": f"layer_{idx}",
                        "type": child.__class__.__name__,
                        "details": str(child)
                    })
            else:
                layers.append({
                    "name": "root",
                    "type": model.__class__.__name__,
                    "details": str(model)
                })
            return {"layers": layers}
        except Exception as e:
            return {"error": f"Failed to extract PyTorch architecture: {e}"}

    elif framework == "tensorflow":
        suffix = path.suffix.lower()
        
        # 1. Keras Zip Archive
        if suffix == ".keras":
            try:
                with zipfile.ZipFile(file_path, 'r') as zf:
                    if 'config.json' in zf.namelist():
                        config_bytes = zf.read('config.json')
                        config = json.loads(config_bytes.decode('utf-8'))
                        return parse_keras_config(config)
            except Exception as e:
                return {"error": f"Failed to parse .keras config: {e}"}
                
        # 2. H5 Keras file
        elif suffix == ".h5":
            try:
                # Fallback to search-based JSON extraction to avoid h5py import issues
                config = extract_keras_h5_json_config(file_path)
                if config:
                    return parse_keras_config(config)
                return {"error": "Could not find model configuration inside H5 file"}
            except Exception as e:
                return {"error": f"Failed to extract H5 config: {e}"}
                
        # 3. SavedModel Zip or Directory
        elif suffix in (".zip", ".tar.gz", ".tgz") or path.is_dir():
            try:
                return scan_saved_model_architecture(file_path)
            except Exception as e:
                return {"error": f"Failed to scan SavedModel architecture: {e}"}
                
    return None

def parse_keras_config(config: dict) -> dict:
    layers = []
    keras_layers = []
    
    if isinstance(config, dict):
        if "config" in config:
            sub_config = config["config"]
            if isinstance(sub_config, dict) and "layers" in sub_config:
                keras_layers = sub_config["layers"]
            elif isinstance(sub_config, list):
                keras_layers = sub_config
        elif "layers" in config:
            keras_layers = config["layers"]
            
    for idx, layer in enumerate(keras_layers):
        if not isinstance(layer, dict):
            continue
        class_name = layer.get("class_name", "Unknown")
        layer_config = layer.get("config", {})
        name = layer_config.get("name", layer.get("name", f"layer_{idx}"))
        
        details_list = []
        for key in ["units", "activation", "rate", "filters", "kernel_size", "strides", "pool_size"]:
            if key in layer_config:
                details_list.append(f"{key}={layer_config[key]}")
        details = ", ".join(details_list)
        
        layers.append({
            "name": name,
            "type": class_name,
            "details": details
        })
        
    return {"layers": layers}

def extract_keras_h5_json_config(file_path: str) -> dict | None:
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        
        start_idx = 0
        while True:
            idx = data.find(b'{"class_name"', start_idx)
            if idx == -1:
                break
            
            brace_count = 0
            in_string = False
            escape = False
            end_idx = -1
            for i in range(idx, len(data)):
                char = data[i:i+1]
                if escape:
                    escape = False
                    continue
                if char == b'\\':
                    escape = True
                    continue
                if char == b'"':
                    in_string = not in_string
                    continue
                if not in_string:
                    if char == b'{':
                        brace_count += 1
                    elif char == b'}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
            
            if end_idx != -1:
                try:
                    json_str = data[idx:end_idx].decode("utf-8", errors="ignore")
                    config = json.loads(json_str)
                    if "class_name" in config:
                        return config
                except Exception:
                    pass
            
            start_idx = idx + 1
    except Exception:
        pass
    return None

def scan_saved_model_architecture(file_path: str) -> dict:
    layers = []
    path = Path(file_path)
    
    pb_data = b""
    if path.is_dir():
        pb_path = path / "saved_model.pb"
        if pb_path.exists():
            with open(pb_path, "rb") as f:
                pb_data = f.read()
    else:
        suffix = path.suffix.lower()
        if suffix == ".zip":
            try:
                with zipfile.ZipFile(file_path, 'r') as zf:
                    for name in zf.namelist():
                        if name.endswith("saved_model.pb"):
                            pb_data = zf.read(name)
                            break
            except Exception:
                pass
        elif suffix in (".tar.gz", ".tgz"):
            try:
                import tarfile
                with tarfile.open(file_path, 'r:*') as tf:
                    for member in tf.getmembers():
                        if member.name.endswith("saved_model.pb"):
                            f = tf.extractfile(member)
                            if f:
                                pb_data = f.read()
                                break
                            break
            except Exception:
                pass

    if not pb_data:
        # Check if there is a config.json anywhere in the archive
        config_data = b""
        if not path.is_dir():
            suffix = path.suffix.lower()
            if suffix == ".zip":
                try:
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        for name in zf.namelist():
                            if name.endswith("config.json"):
                                config_data = zf.read(name)
                                break
                except Exception:
                    pass
        if config_data:
            try:
                config = json.loads(config_data.decode("utf-8"))
                return parse_keras_config(config)
            except Exception:
                pass
        return {"layers": [{"name": "Model", "type": "SavedModel", "details": "TensorFlow SavedModel archive"}]}
        
    tf_ops = [
        b"Conv2D", b"DepthwiseConv2dNative", b"MaxPool", b"AvgPool", b"MatMul", b"BiasAdd", 
        b"Relu", b"Softmax", b"Sigmoid", b"BatchNorm", b"FusedBatchNormV3", b"Reshape", 
        b"Squeeze", b"ConcatV2", b"AddV2", b"Identity", b"Placeholder"
    ]
    
    found_ops = []
    for op in tf_ops:
        start = 0
        while True:
            idx = pb_data.find(op, start)
            if idx == -1:
                break
            found_ops.append((idx, op.decode("utf-8")))
            start = idx + 1
            
    found_ops.sort()
    
    prev_op = None
    count = 1
    for idx, op_name in found_ops:
        if op_name in ("Identity", "Placeholder") and len(found_ops) > 5:
            continue
        if op_name != prev_op:
            layers.append({
                "name": f"{op_name.lower()}_{count}",
                "type": op_name,
                "details": f"TensorFlow Graph Node"
            })
            prev_op = op_name
            count += 1
            
    if not layers:
        layers.append({
            "name": "saved_model",
            "type": "TensorFlowGraph",
            "details": f"Serialized SavedModel, size={len(pb_data)} bytes"
        })
        
    return {"layers": layers}
