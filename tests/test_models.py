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
    """Replace the real Postgres session with a test SQLite session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test, drop them after."""
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
    """Create a real sklearn model and return its bytes."""
    X = np.array([[0, 0], [1, 0], [0, 1], [1, 1]])
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


def test_upload_model_success(client, sklearn_model_bytes):
    response = client.post(
        "/api/v1/models",
        data={"name": "test_model", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["framework"] == "sklearn"
    assert data["status"] == "ready"
    assert data["name"] == "test_model"


def test_list_models(client, sklearn_model_bytes):
    # Upload one model
    client.post(
        "/api/v1/models",
        data={"name": "model_a", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_model(client, sklearn_model_bytes):
    upload = client.post(
        "/api/v1/models",
        data={"name": "model_b", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    model_id = upload.json()["id"]
    response = client.get(f"/api/v1/models/{model_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "model_b"


def test_delete_model(client, sklearn_model_bytes):
    upload = client.post(
        "/api/v1/models",
        data={"name": "model_c", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    model_id = upload.json()["id"]
    delete_resp = client.delete(f"/api/v1/models/{model_id}")
    assert delete_resp.status_code == 200
    # Verify it's gone
    get_resp = client.get(f"/api/v1/models/{model_id}")
    assert get_resp.status_code == 404


def test_get_nonexistent_model(client):
    response = client.get("/api/v1/models/does-not-exist")
    assert response.status_code == 404
