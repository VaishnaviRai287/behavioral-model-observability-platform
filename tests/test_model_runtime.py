import io
import pickle
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn as nn
from sklearn.linear_model import LogisticRegression

from app.ml.loader import load_model
from app.ml.prediction_result import PredictionResult
from app.ml.sklearn_wrapper import SklearnWrapper
from app.ml.pytorch_wrapper import PyTorchWrapper


# Fixtures

@pytest.fixture
def sklearn_model_path(tmp_path):
    """Create and save a real sklearn model, return its path."""
    X = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float)
    y = np.array([0, 0, 0, 1])
    model = LogisticRegression()
    model.fit(X, y)
    path = tmp_path / "model.pkl"
    with open(path, "wb") as f:
        pickle.dump(model, f)
    return str(path)


class SimpleMLP(nn.Module):
    """Minimal 2-layer MLP for testing. Input: 2 features, Output: 2 classes."""
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(2, 2)

    def forward(self, x):
        return self.fc(x)


@pytest.fixture
def pytorch_model_path(tmp_path):
    """Create and save a real PyTorch model, return its path."""
    model = SimpleMLP()
    path = tmp_path / "model.pt"
    torch.save(model, str(path))
    return str(path)


@pytest.fixture
def pytorch_pth_model_path(tmp_path):
    """Create and save a real PyTorch model as .pth, return its path."""
    model = SimpleMLP()
    path = tmp_path / "model.pth"
    torch.save(model, str(path))
    return str(path)


SAMPLE_INPUT = np.array([[0.5, 0.5]])   # shape (1, 2) — a single 2-feature sample


# PredictionResult tests

def test_prediction_result_fields():
    """PredictionResult holds the expected fields."""
    result = PredictionResult(predicted_class=1, confidence=0.87, raw_output=[0.13, 0.87])
    assert result.predicted_class == 1
    assert result.confidence == 0.87
    assert result.raw_output == [0.13, 0.87]


# SklearnWrapper tests

def test_sklearn_wrapper_loads(sklearn_model_path):
    """SklearnWrapper loads a model without crashing."""
    wrapper = SklearnWrapper(sklearn_model_path)
    assert wrapper._model is not None


def test_sklearn_wrapper_predict_returns_result(sklearn_model_path):
    """SklearnWrapper.predict() returns a PredictionResult."""
    wrapper = SklearnWrapper(sklearn_model_path)
    result = wrapper.predict(SAMPLE_INPUT)
    assert isinstance(result, PredictionResult)


def test_sklearn_wrapper_confidence_range(sklearn_model_path):
    """Confidence must be between 0 and 1."""
    wrapper = SklearnWrapper(sklearn_model_path)
    result = wrapper.predict(SAMPLE_INPUT)
    assert 0.0 <= result.confidence <= 1.0


def test_sklearn_wrapper_raw_output_sums_to_one(sklearn_model_path):
    """Raw output probabilities must sum to approximately 1.0."""
    wrapper = SklearnWrapper(sklearn_model_path)
    result = wrapper.predict(SAMPLE_INPUT)
    assert abs(sum(result.raw_output) - 1.0) < 1e-5


def test_sklearn_wrapper_predicted_class_is_valid(sklearn_model_path):
    """Predicted class index must be a valid index into raw_output."""
    wrapper = SklearnWrapper(sklearn_model_path)
    result = wrapper.predict(SAMPLE_INPUT)
    assert 0 <= result.predicted_class < len(result.raw_output)


# PyTorchWrapper tests

def test_pytorch_wrapper_loads(pytorch_model_path):
    """PyTorchWrapper loads a model without crashing."""
    wrapper = PyTorchWrapper(pytorch_model_path)
    assert wrapper._model is not None


def test_pytorch_wrapper_predict_returns_result(pytorch_model_path):
    """PyTorchWrapper.predict() returns a PredictionResult."""
    wrapper = PyTorchWrapper(pytorch_model_path)
    result = wrapper.predict(SAMPLE_INPUT)
    assert isinstance(result, PredictionResult)


def test_pytorch_wrapper_confidence_range(pytorch_model_path):
    """Confidence must be between 0 and 1."""
    wrapper = PyTorchWrapper(pytorch_model_path)
    result = wrapper.predict(SAMPLE_INPUT)
    assert 0.0 <= result.confidence <= 1.0


def test_pytorch_wrapper_raw_output_sums_to_one(pytorch_model_path):
    """Raw output probabilities must sum to approximately 1.0 (softmax applied)."""
    wrapper = PyTorchWrapper(pytorch_model_path)
    result = wrapper.predict(SAMPLE_INPUT)
    assert abs(sum(result.raw_output) - 1.0) < 1e-5


# load_model() factory tests

def test_load_model_returns_sklearn_wrapper(sklearn_model_path):
    """load_model() returns a SklearnWrapper for .pkl files."""
    wrapper = load_model(sklearn_model_path)
    assert isinstance(wrapper, SklearnWrapper)


def test_load_model_returns_pytorch_wrapper(pytorch_model_path):
    """load_model() returns a PyTorchWrapper for .pt files."""
    wrapper = load_model(pytorch_model_path)
    assert isinstance(wrapper, PyTorchWrapper)


def test_load_model_returns_pytorch_wrapper_pth(pytorch_pth_model_path):
    """load_model() returns a PyTorchWrapper for .pth files."""
    wrapper = load_model(pytorch_pth_model_path)
    assert isinstance(wrapper, PyTorchWrapper)


def test_load_model_sklearn_can_predict(sklearn_model_path):
    """Full pipeline: load_model → predict → PredictionResult."""
    wrapper = load_model(sklearn_model_path)
    result = wrapper.predict(SAMPLE_INPUT)
    assert isinstance(result, PredictionResult)
    assert 0.0 <= result.confidence <= 1.0


def test_load_model_pytorch_can_predict(pytorch_model_path):
    """Full pipeline: load_model → predict → PredictionResult."""
    wrapper = load_model(pytorch_model_path)
    result = wrapper.predict(SAMPLE_INPUT)
    assert isinstance(result, PredictionResult)
    assert 0.0 <= result.confidence <= 1.0


def test_load_model_returns_tensorflow_wrapper(tmp_path):
    """load_model() returns a TensorFlowWrapper for .keras files, and it can predict."""
    tf = pytest.importorskip("tensorflow")
    from app.ml.tensorflow_wrapper import TensorFlowWrapper

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(2,)),
        tf.keras.layers.Dense(4, activation="relu"),
        tf.keras.layers.Dense(2, activation="softmax"),
    ])
    keras_path = tmp_path / "model.keras"
    model.save(str(keras_path))

    wrapper = load_model(str(keras_path))
    assert isinstance(wrapper, TensorFlowWrapper)

    result = wrapper.predict(SAMPLE_INPUT)
    assert isinstance(result, PredictionResult)
    assert 0.0 <= result.confidence <= 1.0


def test_load_model_unsupported_extension(tmp_path):
    """load_model() raises ValueError for unsupported file types."""
    bad_path = tmp_path / "model.csv"
    bad_path.write_text("fake data")
    with pytest.raises(ValueError):
        load_model(str(bad_path))
