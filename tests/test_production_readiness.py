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

# Test DB

import os

SQLALCHEMY_TEST_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://modelmesh:modelmesh123@localhost:5433/modelmesh"
)

if SQLALCHEMY_TEST_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_TEST_URL)
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
    model_cache.clear_all()     # ← critical: clear cache between tests
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
    response = client.post(
        "/api/v1/models",
        data={"name": "phase6_test", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    assert response.status_code == 201
    return response.json()["id"]


# Health checks

def test_health_live_returns_200(client):
    """GET /health/live returns 200 with status alive."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_health_ready_returns_200(client):
    """GET /health/ready returns 200 when DB is reachable."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["db"] == "healthy"


def test_health_ready_reports_cache_size(client, model_id):
    """GET /health/ready includes model_cache_size."""
    # Warm the cache with one prediction
    client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.5, "x2": 0.5}},
    )
    response = client.get("/health/ready")
    assert "model_cache_size" in response.json()
    assert response.json()["model_cache_size"] >= 1


# Model caching

def test_cache_grows_after_prediction(client, model_id):
    """Cache should have 1 entry after the first prediction."""
    assert model_cache.cache_size() == 0
    client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.5, "x2": 0.5}},
    )
    assert model_cache.cache_size() == 1


def test_cache_invalidated_on_delete(client, model_id):
    """Deleting a model evicts it from cache."""
    # Warm the cache
    client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.5, "x2": 0.5}},
    )
    assert model_cache.cache_size() == 1

    # Delete the model
    client.delete(f"/api/v1/models/{model_id}")
    assert model_cache.cache_size() == 0


# Drift alerting

def test_drift_status_no_fingerprint_returns_404(client, model_id):
    """Drift status with no fingerprint returns 404."""
    response = client.get(f"/api/v1/models/{model_id}/drift-status")
    assert response.status_code == 404


def test_drift_status_too_few_predictions_returns_422(client, model_id):
    """Drift status with < 10 predictions returns 422."""
    # Create a fingerprint first
    probe = client.post(
        f"/api/v1/models/{model_id}/probe",
        json={"n_probes": 50},
    )
    client.post(f"/api/v1/probes/{probe.json()['id']}/fingerprint")

    # Only 5 predictions — not enough
    for _ in range(5):
        client.post(
            f"/api/v1/models/{model_id}/predict",
            json={"features": {"x1": 0.5, "x2": 0.5}},
        )
    response = client.get(f"/api/v1/models/{model_id}/drift-status")
    assert response.status_code == 422


def test_drift_status_returns_verdict(client, model_id):
    """Drift status with enough data returns a verdict."""
    # Create fingerprint
    probe = client.post(
        f"/api/v1/models/{model_id}/probe",
        json={"n_probes": 50},
    )
    client.post(f"/api/v1/probes/{probe.json()['id']}/fingerprint")

    # 15 predictions
    for _ in range(15):
        client.post(
            f"/api/v1/models/{model_id}/predict",
            json={"features": {"x1": 0.5, "x2": 0.5}},
        )
    response = client.get(f"/api/v1/models/{model_id}/drift-status")
    assert response.status_code == 200
    data = response.json()
    assert "verdict" in data
    assert data["verdict"] in ("stable", "drifted", "severely_drifted")
    assert 0.0 <= data["similarity_score"] <= 1.0
