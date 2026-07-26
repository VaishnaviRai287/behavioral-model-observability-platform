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
from app.models import ml_model, probe_session, probe_result, fingerprint, prediction_log, faiss_index, drift_event, alert  # noqa: F401
from app.models.alert import Alert
from app.models.drift_event import DriftEvent
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
        data={"name": "drift_test_model", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    assert response.status_code == 201
    return response.json()["id"]


# Drift and Alert Engine Tests

def test_drift_and_alerts_flow(client, uploaded_model_id):
    """
    Submitting 50 predictions triggers synchronous drift calculation.
    Submitting shifted distributions triggers alerts.
    """
    # 1. Probe the model to build the baseline (LHS generates inputs in [0, 1])
    probe_resp = client.post(
        f"/api/v1/models/{uploaded_model_id}/probe",
        json={"n_probes": 50},
    )
    assert probe_resp.status_code == 201

    # Set a high standard deviation in the FAISS index baseline to prevent false positive novelty flags
    db = TestingSessionLocal()
    from app.models.faiss_index import FAISSIndex
    idx_rec = db.query(FAISSIndex).filter(FAISSIndex.model_id == uploaded_model_id).first()
    assert idx_rec is not None
    idx_rec.baseline_std_distance = 10.0
    db.commit()
    db.close()

    # 2. Submit 49 normal predictions (drawn from the probe baseline inputs)
    from app.probing.sampler import generate_probe_inputs
    schema_dict = json.loads(SCHEMA)
    baseline_inputs = generate_probe_inputs(schema_dict, 50)

    for i in range(49):
        resp = client.post(
            f"/api/v1/models/{uploaded_model_id}/predict",
            json={"features": {"x1": baseline_inputs[i][0], "x2": baseline_inputs[i][1]}}
        )
        assert resp.status_code == 200

    # Verify no drift events exist yet (only 49 predictions)
    db = TestingSessionLocal()
    drift_count = db.query(DriftEvent).filter(DriftEvent.model_id == uploaded_model_id).count()
    assert drift_count == 0
    db.close()

    # 3. Submit the 50th prediction (triggers synchronous check)
    resp = client.post(
        f"/api/v1/models/{uploaded_model_id}/predict",
        json={"features": {"x1": baseline_inputs[49][0], "x2": baseline_inputs[49][1]}}
    )
    assert resp.status_code == 200

    # Verify drift events were created, but no alerts are active (no major drift)
    db = TestingSessionLocal()
    drift_events = db.query(DriftEvent).filter(DriftEvent.model_id == uploaded_model_id).all()
    assert len(drift_events) == 2  # x1 and x2
    for event in drift_events:
        assert event.severity == "none"

    active_alerts = db.query(Alert).filter(Alert.model_id == uploaded_model_id, Alert.resolved_at == None).count()
    assert active_alerts == 0
    db.close()

    # 4. Submit 50 highly drifted predictions (all clustered at edge 0.99)
    # This will trigger the next sync check at count = 100
    for _ in range(50):
        resp = client.post(
            f"/api/v1/models/{uploaded_model_id}/predict",
            json={"features": {"x1": 0.99, "x2": 0.99}}
        )
        assert resp.status_code == 200

    # Check that FEATURE_DRIFT alert was triggered and logged to the DB
    db = TestingSessionLocal()
    drift_events_after = db.query(DriftEvent).filter(DriftEvent.model_id == uploaded_model_id).all()
    assert len(drift_events_after) == 4  # 2 features * 2 checks (at 50 and 100)
    
    active_drift_alert = db.query(Alert).filter(
        Alert.model_id == uploaded_model_id,
        Alert.alert_type == "FEATURE_DRIFT",
        Alert.resolved_at == None
    ).first()
    assert active_drift_alert is not None
    assert active_drift_alert.severity in ("warning", "critical")
    assert "drifted_features" in active_drift_alert.alert_metadata
    
    # Active alerts query count
    alert_count = db.query(Alert).filter(Alert.model_id == uploaded_model_id, Alert.resolved_at == None).count()
    assert alert_count == 1
    db.close()

    # 5. Query alerts endpoint via API
    alerts_resp = client.get(f"/api/v1/models/{uploaded_model_id}/alerts")
    assert alerts_resp.status_code == 200
    alerts_list = alerts_resp.json()
    assert len(alerts_list) == 1
    alert_id = alerts_list[0]["id"]
    assert alerts_list[0]["alert_type"] == "FEATURE_DRIFT"

    # 6. Resolve alert via API
    resolve_resp = client.post(f"/api/v1/models/{uploaded_model_id}/alerts/{alert_id}/resolve")
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["resolved_at"] is not None

    # Check database status
    db = TestingSessionLocal()
    resolved_alert = db.query(Alert).filter(Alert.id == alert_id).first()
    assert resolved_alert.resolved_at is not None
    db.close()

    # 7. Check health endpoint
    health_resp = client.get(f"/api/v1/models/{uploaded_model_id}/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["active_alerts"] == 0
    assert "x1" in health_data["drift_scores"]
    assert "x2" in health_data["drift_scores"]
    assert health_data["novelty_rate"] == 0.0
