import json
import zipfile
import tempfile
from pathlib import Path
import pytest
import torch
import torch.nn as nn

from app.utils.architecture_extractor import extract_architecture

# Define a simple PyTorch model for testing
class TestModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 10, kernel_size=5)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(10, 20)

    def forward(self, x):
        return self.fc1(self.pool(self.conv1(x)))

def test_extract_pytorch_architecture(tmp_path):
    model = TestModel()
    model_path = tmp_path / "model.pt"
    torch.save(model, str(model_path))
    
    arch = extract_architecture(str(model_path), "pytorch")
    assert arch is not None
    assert "layers" in arch
    layers = arch["layers"]
    assert len(layers) == 3
    assert layers[0]["name"] == "conv1"
    assert layers[0]["type"] == "Conv2d"
    assert layers[1]["name"] == "pool"
    assert layers[1]["type"] == "MaxPool2d"
    assert layers[2]["name"] == "fc1"
    assert layers[2]["type"] == "Linear"

def test_extract_keras_zip_architecture(tmp_path):
    keras_path = tmp_path / "model.keras"
    
    # Create a dummy .keras ZIP archive
    config_data = {
        "class_name": "Sequential",
        "config": {
            "name": "sequential",
            "layers": [
                {
                    "class_name": "InputLayer",
                    "config": {"batch_shape": [None, 10], "name": "input_1"}
                },
                {
                    "class_name": "Dense",
                    "config": {"units": 64, "activation": "relu", "name": "dense_1"}
                },
                {
                    "class_name": "Dropout",
                    "config": {"rate": 0.5, "name": "dropout_1"}
                },
                {
                    "class_name": "Dense",
                    "config": {"units": 2, "activation": "softmax", "name": "dense_2"}
                }
            ]
        }
    }
    
    with zipfile.ZipFile(keras_path, "w") as zf:
        zf.writestr("config.json", json.dumps(config_data))
        
    arch = extract_architecture(str(keras_path), "tensorflow")
    assert arch is not None
    assert "layers" in arch
    layers = arch["layers"]
    assert len(layers) == 4
    assert layers[0]["type"] == "InputLayer"
    assert layers[1]["type"] == "Dense"
    assert "units=64" in layers[1]["details"]
    assert "activation=relu" in layers[1]["details"]
    assert layers[2]["type"] == "Dropout"
    assert "rate=0.5" in layers[2]["details"]
    assert layers[3]["type"] == "Dense"
    assert "units=2" in layers[3]["details"]
    assert "activation=softmax" in layers[3]["details"]

def test_extract_keras_h5_architecture(tmp_path):
    h5_path = tmp_path / "model.h5"
    
    config_data = {
        "class_name": "Functional",
        "config": {
            "layers": [
                {
                    "class_name": "Dense",
                    "config": {"units": 32, "activation": "sigmoid", "name": "dense_sig"}
                }
            ]
        }
    }
    
    # Write config JSON surrounded by arbitrary binary bytes (simulating H5)
    binary_content = b"\x89HDF\r\n\x1a\n" + b"\x00" * 100 + b'{"class_name": "Functional", "config": {"layers": [{"class_name": "Dense", "config": {"units": 32, "activation": "sigmoid", "name": "dense_sig"}}]}}' + b"\x00" * 50
    with open(h5_path, "wb") as f:
        f.write(binary_content)
        
    arch = extract_architecture(str(h5_path), "tensorflow")
    assert arch is not None
    assert "layers" in arch
    layers = arch["layers"]
    assert len(layers) == 1
    assert layers[0]["type"] == "Dense"
    assert layers[0]["name"] == "dense_sig"
    assert "units=32" in layers[0]["details"]
    assert "activation=sigmoid" in layers[0]["details"]

def test_extract_saved_model_architecture(tmp_path):
    # Create SavedModel directory structure
    model_dir = tmp_path / "my_saved_model"
    model_dir.mkdir()
    
    # Write dummy saved_model.pb containing binary op tags
    pb_path = model_dir / "saved_model.pb"
    # We write binary contents containing some sequential ops we scan for
    pb_content = b"\n\x0ePlaceholder\x12\nMatMul\x1a\x07BiasAdd\x22\x04Relu\x2a\x07Softmax"
    with open(pb_path, "wb") as f:
        f.write(pb_content)
        
    arch = extract_architecture(str(model_dir), "tensorflow")
    assert arch is not None
    assert "layers" in arch
    layers = arch["layers"]
    
    # Output should identify sequential ops (Placeholder/Identity gets filtered if > 5 ops, 
    # but here we have 5, so let's verify ops are extracted)
    assert len(layers) > 0
    op_types = [layer["type"] for layer in layers]
    assert "MatMul" in op_types
    assert "Relu" in op_types
    assert "Softmax" in op_types
