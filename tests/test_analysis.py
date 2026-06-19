import io
import json
import pickle
import os
from datetime import datetime, timezone, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.ml import model_cache
from app.models.ml_model import MLModel
from app.models.prediction_log import PredictionLog
from app.models.probe_session import ProbeSession
from app.models.probe_result import ProbeResult

# ── Test Database Configuration ───────────────────────────────────────────────

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
        data={"name": "observability_test_model", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    assert response.status_code == 201
    return response.json()["id"]


# ── Test Cases ────────────────────────────────────────────────────────────────

def test_dataset_health_empty_logs(client, uploaded_model_id):
    """GET /dataset-health returns empty defaults if no logs exist."""
    response = client.get(f"/api/v1/models/{uploaded_model_id}/dataset-health")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 0
    assert data["missing_values"]["percentage"] == 0.0
    assert data["outliers"]["percentage"] == 0.0
    assert data["duplicates"]["percentage"] == 0.0


def test_dataset_health_nonexistent_model(client):
    """GET /dataset-health returns 404 for missing model."""
    response = client.get("/api/v1/models/non-existent-id/dataset-health")
    assert response.status_code == 404


def test_dataset_health_with_simulated_logs(client, uploaded_model_id):
    """GET /dataset-health calculates missing, duplicate, outlier values correctly."""
    # 1. Run probe session to establish baseline IQR bounds
    probe_resp = client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 10},
    )
    assert probe_resp.status_code == 201

    # 2. Inject prediction logs with missing values, duplicate values, and outliers
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)
    
    log1 = PredictionLog(
        model_id=uploaded_model_id,
        input_features={"x1": 0.5, "x2": 0.5},
        input_vector=[0.5, 0.5],
        predicted_class=0,
        confidence=0.8,
        raw_output=[0.8, 0.2],
        latency_ms=10.0,
        cpu_utilization=12.5,
        memory_mb=150.0,
        created_at=now
    )
    
    log2 = PredictionLog(
        model_id=uploaded_model_id,
        input_features={"x1": None, "x2": 0.5},  # Missing x1
        input_vector=[0.0, 0.5],
        predicted_class=0,
        confidence=0.9,
        raw_output=[0.9, 0.1],
        latency_ms=12.0,
        cpu_utilization=10.0,
        memory_mb=155.0,
        created_at=now - timedelta(seconds=1)
    )

    log3 = PredictionLog(
        model_id=uploaded_model_id,
        input_features={"x1": 0.5, "x2": 0.5},  # Duplicate of log1
        input_vector=[0.5, 0.5],
        predicted_class=1,
        confidence=0.75,
        raw_output=[0.25, 0.75],
        latency_ms=8.0,
        cpu_utilization=15.0,
        memory_mb=148.0,
        created_at=now - timedelta(seconds=2)
    )

    log4 = PredictionLog(
        model_id=uploaded_model_id,
        input_features={"x1": 5.0, "x2": 0.5},  # Outlier on x1 (baseline is in [0, 1])
        input_vector=[5.0, 0.5],
        predicted_class=1,
        confidence=0.6,
        raw_output=[0.4, 0.6],
        latency_ms=15.0,
        cpu_utilization=20.0,
        memory_mb=160.0,
        created_at=now - timedelta(seconds=3)
    )

    db.add_all([log1, log2, log3, log4])
    db.commit()
    db.close()

    # 3. Query dataset-health
    response = client.get(f"/api/v1/models/{uploaded_model_id}/dataset-health")
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 4
    # Missing values: x1 has 1 missing, x2 has 0. Total features evaluated = 4 * 2 = 8.
    # 1 missing out of 8 = 12.5%
    assert data["missing_values"]["total_missing"] == 1
    assert data["missing_values"]["by_feature"]["x1"] == 1
    assert data["missing_values"]["by_feature"]["x2"] == 0
    assert data["missing_values"]["percentage"] == 12.5

    # Duplicates: log1 and log3 are identical input vectors [0.5, 0.5].
    # Total vectors = 4, unique = 3. Duplicate count = 1.
    # 1/4 = 25.0%
    assert data["duplicates"]["duplicate_count"] == 1
    assert data["duplicates"]["percentage"] == 25.0

    # Outliers: log4 value 5.0 is an outlier on x1.
    # Total values = 4 * 2 = 8. Outlier count = 1.
    # 1/8 = 12.5%
    assert data["outliers"]["total_outliers"] == 1
    assert data["outliers"]["by_feature"]["x1"] == 1
    assert data["outliers"]["by_feature"]["x2"] == 0
    assert data["outliers"]["percentage"] == 12.5

    # Class Imbalance:
    # class 0 has 2, class 1 has 2.
    assert data["class_imbalance"]["counts"]["0"] == 2
    assert data["class_imbalance"]["counts"]["1"] == 2
    assert data["class_imbalance"]["percentages"]["0"] == 50.0
    assert data["class_imbalance"]["percentages"]["1"] == 50.0
    # Entropy should be exactly 1.0 for two equally balanced classes
    assert data["class_imbalance"]["entropy"] == 1.0


def test_performance_profile_empty_logs(client, uploaded_model_id):
    """GET /performance returns empty statistics when no logs exist."""
    response = client.get(f"/api/v1/models/{uploaded_model_id}/performance")
    assert response.status_code == 200
    data = response.json()
    assert data["total_predictions"] == 0
    assert data["latency"]["mean"] == 0.0
    assert data["cpu"]["mean_pct"] == 0.0
    assert data["memory"]["mean_mb"] == 0.0


def test_performance_profile_nonexistent_model(client):
    """GET /performance returns 404 for missing model."""
    response = client.get("/api/v1/models/non-existent-id/performance")
    assert response.status_code == 404


def test_performance_profile_with_logs(client, uploaded_model_id):
    """GET /performance computes latency percentiles, throughput, and system resource utilization."""
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)
    
    # Insert logs spread across a time range
    log1 = PredictionLog(
        model_id=uploaded_model_id,
        input_features={"x1": 0.5, "x2": 0.5},
        input_vector=[0.5, 0.5],
        predicted_class=0,
        confidence=0.8,
        raw_output=[0.8, 0.2],
        latency_ms=10.0,
        cpu_utilization=10.0,
        memory_mb=100.0,
        created_at=now
    )

    log2 = PredictionLog(
        model_id=uploaded_model_id,
        input_features={"x1": 0.5, "x2": 0.5},
        input_vector=[0.5, 0.5],
        predicted_class=0,
        confidence=0.8,
        raw_output=[0.8, 0.2],
        latency_ms=20.0,
        cpu_utilization=20.0,
        memory_mb=200.0,
        created_at=now - timedelta(seconds=10)
    )

    log3 = PredictionLog(
        model_id=uploaded_model_id,
        input_features={"x1": 0.5, "x2": 0.5},
        input_vector=[0.5, 0.5],
        predicted_class=0,
        confidence=0.8,
        raw_output=[0.8, 0.2],
        latency_ms=30.0,
        cpu_utilization=30.0,
        memory_mb=300.0,
        created_at=now - timedelta(seconds=20)
    )

    db.add_all([log1, log2, log3])
    db.commit()
    db.close()

    # Query performance endpoint
    response = client.get(f"/api/v1/models/{uploaded_model_id}/performance")
    assert response.status_code == 200
    data = response.json()

    assert data["total_predictions"] == 3
    # Latency: [10, 20, 30] -> mean=20, min=10, max=30, p50=20
    assert data["latency"]["mean"] == 20.0
    assert data["latency"]["min"] == 10.0
    assert data["latency"]["max"] == 30.0
    assert data["latency"]["p50"] == 20.0
    assert data["latency"]["p95"] >= 20.0

    # CPU: [10, 20, 30] -> mean=20, peak=30
    assert data["cpu"]["mean_pct"] == 20.0
    assert data["cpu"]["peak_pct"] == 30.0

    # Memory: [100, 200, 300] -> mean=200, peak=300
    assert data["memory"]["mean_mb"] == 200.0
    assert data["memory"]["peak_mb"] == 300.0

    # Throughput: should have rps metrics
    assert "rps_1m" in data["throughput"]
    assert "rps_5m" in data["throughput"]
    assert "rps_overall" in data["throughput"]


def test_drift_analysis_empty_logs(client, uploaded_model_id):
    """GET /drift-analysis returns defaults if no logs or baseline exists."""
    response = client.get(f"/api/v1/models/{uploaded_model_id}/drift-analysis")
    assert response.status_code == 200
    data = response.json()
    assert data["feature_drift"] == []
    assert data["target_drift"]["class_drift"]["psi_score"] == 0.0
    assert data["target_drift"]["confidence_drift"]["ks_statistic"] == 0.0


def test_drift_analysis_nonexistent_model(client):
    """GET /drift-analysis returns 404 for missing model."""
    response = client.get("/api/v1/models/non-existent-id/drift-analysis")
    assert response.status_code == 404


def test_drift_analysis_with_data(client, uploaded_model_id):
    """GET /drift-analysis yields KS statistic, PSI score, and histograms for features and targets."""
    # 1. Run probe session to establish baseline
    probe_resp = client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 15},
    )
    assert probe_resp.status_code == 201

    # 2. Inject prediction logs
    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)

    # Let's add logs representing predictions
    for i in range(10):
        log = PredictionLog(
            model_id=uploaded_model_id,
            input_features={"x1": 0.8, "x2": 0.8},
            input_vector=[0.8, 0.8],
            predicted_class=1,
            confidence=0.95,
            raw_output=[0.05, 0.95],
            latency_ms=10.0,
            cpu_utilization=10.0,
            memory_mb=100.0,
            created_at=now - timedelta(seconds=i)
        )
        db.add(log)
    db.commit()
    db.close()

    # 3. Query drift-analysis endpoint
    response = client.get(f"/api/v1/models/{uploaded_model_id}/drift-analysis")
    assert response.status_code == 200
    data = response.json()

    # Check features drift
    assert len(data["feature_drift"]) == 2
    f1 = data["feature_drift"][0]
    assert "name" in f1
    assert "ks_statistic" in f1
    assert "psi_score" in f1
    assert "verdict" in f1
    assert "distribution" in f1
    assert "baseline" in f1["distribution"]
    assert "production" in f1["distribution"]
    assert "labels" in f1["distribution"]

    # Check targets class and confidence drift
    class_drift = data["target_drift"]["class_drift"]
    assert "psi_score" in class_drift
    assert "verdict" in class_drift
    assert "baseline" in class_drift
    assert "production" in class_drift

    conf_drift = data["target_drift"]["confidence_drift"]
    assert "ks_statistic" in conf_drift
    assert "psi_score" in conf_drift
    assert "verdict" in conf_drift
    assert "distribution" in conf_drift
    assert "baseline" in conf_drift["distribution"]
    assert "production" in conf_drift["distribution"]
