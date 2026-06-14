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
from app.probing.sampler import generate_probe_inputs

# ── Test DB setup (same pattern as test_models.py) ───────────────────────────

SQLALCHEMY_TEST_URL = "sqlite:///./test_probing.db"

engine = create_engine(
    SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False}
)
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

SCHEMA_DICT = {
    "features": [
        {"name": "x1", "type": "float", "min": 0, "max": 1},
        {"name": "x2", "type": "float", "min": 0, "max": 1},
    ]
}


# ── Sampler tests ─────────────────────────────────────────────────────────────

def test_sampler_output_shape():
    """generate_probe_inputs returns the correct number of vectors."""
    inputs = generate_probe_inputs(SCHEMA_DICT, n_probes=50)
    assert len(inputs) == 50
    assert len(inputs[0]) == 2   # 2 features


def test_sampler_respects_bounds():
    """All generated values are within declared feature bounds."""
    inputs = generate_probe_inputs(SCHEMA_DICT, n_probes=100)
    for vector in inputs:
        assert 0.0 <= vector[0] <= 1.0, f"x1 out of bounds: {vector[0]}"
        assert 0.0 <= vector[1] <= 1.0, f"x2 out of bounds: {vector[1]}"


def test_sampler_is_deterministic():
    """Same schema + n_probes always produces the same samples (seed=42)."""
    inputs_a = generate_probe_inputs(SCHEMA_DICT, n_probes=10)
    inputs_b = generate_probe_inputs(SCHEMA_DICT, n_probes=10)
    assert inputs_a == inputs_b


def test_sampler_default_bounds():
    """Features without min/max declared use -3.0 to 3.0 defaults."""
    schema = {"features": [{"name": "x1", "type": "float"}]}
    inputs = generate_probe_inputs(schema, n_probes=20)
    for vector in inputs:
        assert -3.0 <= vector[0] <= 3.0


# ── Probe API tests ───────────────────────────────────────────────────────────

@pytest.fixture
def uploaded_model_id(client, sklearn_model_bytes):
    """Upload a model and return its ID."""
    response = client.post(
        "/api/v1/models",
        data={"name": "probe_test_model", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_probe_returns_201(client, uploaded_model_id):
    """POST /models/{id}/probe returns 201."""
    response = client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 50},
    )
    assert response.status_code == 201


def test_probe_status_is_done(client, uploaded_model_id):
    """After a successful probe, status is 'done'."""
    response = client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 50},
    )
    assert response.json()["status"] == "done"


def test_probe_returns_statistics(client, uploaded_model_id):
    """Probe response includes mean_confidence, confidence_std, dominant_class."""
    response = client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 50},
    )
    data = response.json()
    assert data["mean_confidence"] is not None
    assert data["confidence_std"] is not None
    assert data["dominant_class"] is not None
    assert data["class_distribution"] is not None


def test_probe_confidence_in_range(client, uploaded_model_id):
    """mean_confidence must be between 0 and 1."""
    response = client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 50},
    )
    mean_conf = response.json()["mean_confidence"]
    assert 0.0 <= mean_conf <= 1.0


def test_probe_class_distribution_sums_to_n_probes(client, uploaded_model_id):
    """class_distribution counts must sum to n_probes."""
    n = 50
    response = client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": n},
    )
    dist = response.json()["class_distribution"]
    assert sum(dist.values()) == n


def test_probe_nonexistent_model(client):
    """Probing a non-existent model returns 404."""
    response = client.post(
        "/api/v1/models/does-not-exist/probe",
        json={"n_probes": 50},
    )
    assert response.status_code == 404


def test_get_probe_session(client, uploaded_model_id):
    """GET /probes/{session_id} returns the probe session."""
    probe_resp = client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 50},
    )
    session_id = probe_resp.json()["id"]
    get_resp = client.get(f"/api/v1/probes/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id


def test_list_probe_sessions(client, uploaded_model_id):
    """GET /models/{id}/probes returns list of sessions."""
    client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 50},
    )
    client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 50},
    )
    list_resp = client.get(f"/api/v1/models/{uploaded_model_id}/probes")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2
