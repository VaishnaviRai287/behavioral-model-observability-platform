import io
import json
import pickle

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.ml import model_cache

# ── Test DB ───────────────────────────────────────────────────────────────────

SQLALCHEMY_TEST_URL = "sqlite:///./test_predictions.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    model_cache.clear_all()
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()
    model_cache.clear_all()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sklearn_model_bytes():
    X = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float)
    y = np.array([0, 0, 0, 1])
    model = LogisticRegression()
    model.fit(X, y)
    buf = io.BytesIO()
    pickle.dump(model, buf)
    buf.seek(0)
    return buf


SCHEMA = json.dumps({
    "features": [
        {"name": "x1", "type": "float", "min": 0, "max": 1},
        {"name": "x2", "type": "float", "min": 0, "max": 1},
    ]
})


@pytest.fixture
def model_id(client, sklearn_model_bytes):
    """Upload a model and return its ID."""
    response = client.post(
        "/api/v1/models",
        data={"name": "predict_test", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    assert response.status_code == 201
    return response.json()["id"]


# ── Prediction tests ──────────────────────────────────────────────────────────

def test_predict_returns_200(client, model_id):
    """POST /models/{id}/predict returns 200."""
    response = client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.5, "x2": 0.5}},
    )
    assert response.status_code == 200


def test_predict_response_shape(client, model_id):
    """Prediction response includes all required fields."""
    response = client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.5, "x2": 0.5}},
    )
    data = response.json()
    assert "predicted_class" in data
    assert "confidence" in data
    assert "raw_output" in data
    assert "latency_ms" in data


def test_predict_confidence_in_range(client, model_id):
    """Confidence must be in [0, 1]."""
    response = client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.5, "x2": 0.5}},
    )
    assert 0.0 <= response.json()["confidence"] <= 1.0


def test_predict_latency_is_positive(client, model_id):
    """latency_ms must be a positive number."""
    response = client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.5, "x2": 0.5}},
    )
    assert response.json()["latency_ms"] > 0


def test_predict_missing_feature_returns_422(client, model_id):
    """Missing a required feature returns 422."""
    response = client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.5}},   # x2 missing
    )
    assert response.status_code == 422
    assert "x2" in response.json()["detail"]


def test_predict_non_numeric_feature_returns_422(client, model_id):
    """Non-numeric feature value returns 422."""
    response = client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": "hello", "x2": 0.5}},
    )
    assert response.status_code == 422


def test_predict_out_of_bounds_returns_422(client, model_id):
    """Value outside declared min/max bounds returns 422."""
    response = client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 1.5, "x2": 0.5}},   # x1 > max (1.0)
    )
    assert response.status_code == 422
    assert "above maximum" in response.json()["detail"]


def test_predict_nonexistent_model_returns_404(client):
    """Predicting on non-existent model returns 404."""
    response = client.post(
        "/api/v1/models/does-not-exist/predict",
        json={"features": {"x1": 0.5, "x2": 0.5}},
    )
    assert response.status_code == 404


def test_predict_is_logged(client, model_id):
    """After a prediction, it appears in the prediction log."""
    client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.8, "x2": 0.9}},
    )
    logs = client.get(f"/api/v1/models/{model_id}/predictions").json()
    assert len(logs) == 1
    assert logs[0]["input_features"]["x1"] == 0.8


def test_multiple_predictions_are_all_logged(client, model_id):
    """Multiple predictions each get their own log entry."""
    for _ in range(3):
        client.post(
            f"/api/v1/models/{model_id}/predict",
            json={"features": {"x1": 0.5, "x2": 0.5}},
        )
    logs = client.get(f"/api/v1/models/{model_id}/predictions").json()
    assert len(logs) == 3


def test_predictions_ordered_newest_first(client, model_id):
    """Prediction logs are returned newest-first."""
    client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.1, "x2": 0.1}},
    )
    client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.9, "x2": 0.9}},
    )
    logs = client.get(f"/api/v1/models/{model_id}/predictions").json()
    # Most recent prediction (x1=0.9) should be first
    assert logs[0]["input_features"]["x1"] == 0.9


def test_limit_parameter(client, model_id):
    """?limit=1 returns at most 1 prediction log."""
    for _ in range(5):
        client.post(
            f"/api/v1/models/{model_id}/predict",
            json={"features": {"x1": 0.5, "x2": 0.5}},
        )
    logs = client.get(f"/api/v1/models/{model_id}/predictions?limit=2").json()
    assert len(logs) == 2
