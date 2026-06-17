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
from app.fingerprinting.metrics import compute_fingerprint_metrics
from app.fingerprinting.comparator import compare_fingerprints

# ── Test DB ───────────────────────────────────────────────────────────────────

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
def probe_session_id(client, sklearn_model_bytes):
    """Upload a model and run a probe session, return session_id."""
    upload = client.post(
        "/api/v1/models",
        data={"name": "fp_test", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    model_id = upload.json()["id"]
    probe = client.post(
        f"/api/v1/models/{model_id}/probe",
        json={"n_probes": 50},
    )
    return probe.json()["id"]


@pytest.fixture
def fingerprint_id(client, probe_session_id):
    """Create a fingerprint from a probe session, return fingerprint_id."""
    resp = client.post(f"/api/v1/probes/{probe_session_id}/fingerprint")
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Fingerprint creation tests ────────────────────────────────────────────────

def test_create_fingerprint_returns_201(client, probe_session_id):
    """POST /probes/{id}/fingerprint returns 201."""
    response = client.post(f"/api/v1/probes/{probe_session_id}/fingerprint")
    assert response.status_code == 201


def test_fingerprint_has_histogram(client, probe_session_id):
    """Fingerprint response includes a 10-element confidence_histogram."""
    response = client.post(f"/api/v1/probes/{probe_session_id}/fingerprint")
    hist = response.json()["confidence_histogram"]
    assert isinstance(hist, list)
    assert len(hist) == 10


def test_histogram_sums_to_one(client, probe_session_id):
    """Confidence histogram fractions must sum to approximately 1.0."""
    response = client.post(f"/api/v1/probes/{probe_session_id}/fingerprint")
    hist = response.json()["confidence_histogram"]
    assert abs(sum(hist) - 1.0) < 1e-5


def test_fingerprint_entropy_in_range(client, probe_session_id):
    """Entropy must be in [0, 1]."""
    response = client.post(f"/api/v1/probes/{probe_session_id}/fingerprint")
    entropy = response.json()["entropy"]
    assert 0.0 <= entropy <= 1.0


def test_fingerprint_uncertainty_rate_in_range(client, probe_session_id):
    """Uncertainty rate must be in [0, 1]."""
    response = client.post(f"/api/v1/probes/{probe_session_id}/fingerprint")
    rate = response.json()["uncertainty_rate"]
    assert 0.0 <= rate <= 1.0


def test_fingerprint_class_bias_in_range(client, probe_session_id):
    """Class bias must be in [0, 1]."""
    response = client.post(f"/api/v1/probes/{probe_session_id}/fingerprint")
    bias = response.json()["class_bias"]
    assert 0.0 <= bias <= 1.0


def test_create_fingerprint_is_idempotent(client, probe_session_id):
    """Creating fingerprint twice returns the same fingerprint_id."""
    r1 = client.post(f"/api/v1/probes/{probe_session_id}/fingerprint")
    r2 = client.post(f"/api/v1/probes/{probe_session_id}/fingerprint")
    assert r1.json()["id"] == r2.json()["id"]


def test_get_fingerprint(client, fingerprint_id):
    """GET /fingerprints/{id} returns the fingerprint."""
    response = client.get(f"/api/v1/fingerprints/{fingerprint_id}")
    assert response.status_code == 200
    assert response.json()["id"] == fingerprint_id


def test_get_nonexistent_fingerprint(client):
    """GET /fingerprints/does-not-exist returns 404."""
    response = client.get("/api/v1/fingerprints/does-not-exist")
    assert response.status_code == 404


# ── Comparison tests ──────────────────────────────────────────────────────────

@pytest.fixture
def two_fingerprint_ids(client, sklearn_model_bytes):
    """Create two separate probe sessions and fingerprints for comparison."""
    upload = client.post(
        "/api/v1/models",
        data={"name": "cmp_model", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    model_id = upload.json()["id"]

    session_a = client.post(f"/api/v1/models/{model_id}/probe", json={"n_probes": 50}).json()["id"]
    session_b = client.post(f"/api/v1/models/{model_id}/probe", json={"n_probes": 50}).json()["id"]

    fp_a = client.post(f"/api/v1/probes/{session_a}/fingerprint").json()["id"]
    fp_b = client.post(f"/api/v1/probes/{session_b}/fingerprint").json()["id"]
    return fp_a, fp_b


def test_compare_returns_200(client, two_fingerprint_ids):
    """GET /fingerprints/{a}/compare/{b} returns 200."""
    fp_a, fp_b = two_fingerprint_ids
    response = client.get(f"/api/v1/fingerprints/{fp_a}/compare/{fp_b}")
    assert response.status_code == 200


def test_compare_similarity_score_in_range(client, two_fingerprint_ids):
    """similarity_score must be in [0, 1]."""
    fp_a, fp_b = two_fingerprint_ids
    response = client.get(f"/api/v1/fingerprints/{fp_a}/compare/{fp_b}")
    score = response.json()["similarity_score"]
    assert 0.0 <= score <= 1.0


def test_compare_same_model_is_stable(client, two_fingerprint_ids):
    """Two fingerprints from the same model (same inputs) should be 'stable'."""
    fp_a, fp_b = two_fingerprint_ids
    response = client.get(f"/api/v1/fingerprints/{fp_a}/compare/{fp_b}")
    # Same model + same sampler seed → identical behavior → stable
    verdict = response.json()["verdict"]
    assert verdict == "stable"


def test_compare_verdict_is_valid(client, two_fingerprint_ids):
    """Verdict must be one of the three valid strings."""
    fp_a, fp_b = two_fingerprint_ids
    response = client.get(f"/api/v1/fingerprints/{fp_a}/compare/{fp_b}")
    verdict = response.json()["verdict"]
    assert verdict in ("stable", "drifted", "severely_drifted")


def test_compare_self_returns_400(client, fingerprint_id):
    """Comparing a fingerprint with itself should return 400."""
    response = client.get(f"/api/v1/fingerprints/{fingerprint_id}/compare/{fingerprint_id}")
    assert response.status_code == 400


def test_get_uncertainty_regions(client, fingerprint_id):
    """GET /fingerprints/{id}/uncertainty-regions returns a list of detected regions."""
    response = client.get(f"/api/v1/fingerprints/{fingerprint_id}/uncertainty-regions")
    assert response.status_code == 200
    regions = response.json()
    assert isinstance(regions, list)
    assert len(regions) > 0  # It should fallback to returning top 2 if no low confidence regions
    for r in regions:
        assert "feature_bounds" in r
        assert "mean_confidence" in r
        assert "sample_density" in r
        assert "variance" in r

