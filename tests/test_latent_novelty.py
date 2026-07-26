import io
import json
import pickle
import os

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.ml import model_cache
from app.models.faiss_index import FAISSIndex
from app.models.prediction_log import PredictionLog

# Test Database Configuration

SQLALCHEMY_TEST_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///./test.db"
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
    # Simple binary dataset where x1 and x2 determine outcome
    X = np.array([[0.1, 0.1], [0.2, 0.2], [0.8, 0.8], [0.9, 0.9]], dtype=float)
    y = np.array([0, 0, 1, 1])
    model = LogisticRegression()
    model.fit(X, y)
    buf = io.BytesIO()
    pickle.dump(model, buf)
    buf.seek(0)
    return buf


SCHEMA = json.dumps({
    "features": [
        {"name": "x1", "type": "float", "min": 0.0, "max": 1.0},
        {"name": "x2", "type": "float", "min": 0.0, "max": 1.0},
    ]
})


@pytest.fixture
def uploaded_model_id(client, sklearn_model_bytes):
    response = client.post(
        "/api/v1/models",
        data={"name": "latent_test_model", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    assert response.status_code == 201
    return response.json()["id"]


# Latent Monitoring Tests

def test_probe_generates_faiss_index(client, uploaded_model_id):
    """Probing the model creates a FAISS index record and stores it on disk."""
    # Trigger probe session (creates LHS inputs and builds index)
    response = client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 20},
    )
    assert response.status_code == 201

    # Verify database record exists
    db = TestingSessionLocal()
    idx_record = db.query(FAISSIndex).filter(FAISSIndex.model_id == uploaded_model_id).first()
    assert idx_record is not None
    assert idx_record.vector_dim == 1
    assert idx_record.vector_count == 20
    assert idx_record.baseline_mean_distance >= 0.0
    assert idx_record.baseline_std_distance >= 0.0
    assert os.path.exists(idx_record.index_file_path)
    db.close()


def test_predict_logs_faiss_distance(client, uploaded_model_id):
    """Live predictions correctly compute and store FAISS distances."""
    # Build index first via probe
    client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 20},
    )

    # Perform normal prediction
    resp = client.post(
        f"/api/v1/models/{uploaded_model_id}/predict",
        json={"features": {"x1": 0.5, "x2": 0.5}}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "faiss_distance" in data
    assert data["faiss_distance"] is not None
    assert data["novelty_flag"] is False

    # Check database persistence
    db = TestingSessionLocal()
    log = db.query(PredictionLog).filter(PredictionLog.model_id == uploaded_model_id).first()
    assert log is not None
    assert log.faiss_distance is not None
    assert log.novelty_flag is False
    db.close()


def test_predict_flags_novelty_on_out_of_distribution(client, uploaded_model_id):
    """OOD inputs trigger the novelty_flag = True."""
    # Build index first via probe
    client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 20},
    )

    # Modify the database record to make the threshold extremely low
    # so that any subsequent prediction distance will exceed it and trigger novelty
    db = TestingSessionLocal()
    idx_record = db.query(FAISSIndex).filter(FAISSIndex.model_id == uploaded_model_id).first()
    assert idx_record is not None
    idx_record.baseline_mean_distance = 0.00001
    idx_record.baseline_std_distance = 0.00001
    db.commit()
    db.close()

    # Perform prediction — it will calculate a non-zero distance which exceeds the tiny threshold
    resp = client.post(
        f"/api/v1/models/{uploaded_model_id}/predict",
        json={"features": {"x1": 0.9, "x2": 0.9}}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["novelty_flag"] is True
