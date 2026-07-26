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

# Test DB

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
    # Make a simple classifier
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
        {"name": "x1", "type": "float", "min": 0.0, "max": 1.0},
        {"name": "x2", "type": "float", "min": 0.0, "max": 1.0},
    ]
})


def test_model_signature_generation(client, sklearn_model_bytes):
    """Verify unique model signature is generated and remains deterministic."""
    # 1. Upload model
    upload_res_1 = client.post(
        "/api/v1/models",
        data={"name": "sig_test_1", "schema": SCHEMA},
        files={"file": ("model1.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    assert upload_res_1.status_code == 201
    model_id_1 = upload_res_1.json()["id"]

    # Retrieve model detail to inspect signature
    detail_res_1 = client.get(f"/api/v1/models/{model_id_1}")
    assert detail_res_1.status_code == 200
    sig_1 = detail_res_1.json().get("signature")
    assert sig_1 is not None
    assert len(sig_1) == 64  # SHA-256 hash length

    # 2. Upload identical model and verify same signature
    sklearn_model_bytes.seek(0)
    upload_res_2 = client.post(
        "/api/v1/models",
        data={"name": "sig_test_2", "schema": SCHEMA},
        files={"file": ("model2.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    assert upload_res_2.status_code == 201
    model_id_2 = upload_res_2.json()["id"]

    detail_res_2 = client.get(f"/api/v1/models/{model_id_2}")
    sig_2 = detail_res_2.json().get("signature")
    assert sig_2 == sig_1


def test_global_explainability(client, sklearn_model_bytes):
    """Verify global feature importances are calculated and returned correctly."""
    # Upload model
    upload_res = client.post(
        "/api/v1/models",
        data={"name": "global_explain_test", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    model_id = upload_res.json()["id"]

    # Get global explainability
    explain_res = client.get(f"/api/v1/models/{model_id}/explainability/global")
    assert explain_res.status_code == 200
    
    data = explain_res.json()
    assert data["model_id"] == model_id
    assert "feature_importance" in data
    
    importances = data["feature_importance"]
    assert len(importances) == 2
    
    features = [item["feature"] for item in importances]
    assert "x1" in features
    assert "x2" in features
    
    # Importances should be sorted in descending order
    assert importances[0]["importance"] >= importances[1]["importance"]


def test_local_prediction_explainability(client, sklearn_model_bytes):
    """Verify prediction local SHAP values add up to predicted class output probability."""
    # Upload model
    upload_res = client.post(
        "/api/v1/models",
        data={"name": "local_explain_test", "schema": SCHEMA},
        files={"file": ("model.pkl", sklearn_model_bytes, "application/octet-stream")},
    )
    model_id = upload_res.json()["id"]

    # Make a prediction prediction log
    predict_res = client.post(
        f"/api/v1/models/{model_id}/predict",
        json={"features": {"x1": 0.8, "x2": 0.2}},
    )
    # Fetch prediction ID from prediction logs
    logs_res = client.get(f"/api/v1/models/{model_id}/predictions")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) == 1
    prediction_id = logs[0]["id"]

    # Fetch explanation
    explain_res = client.get(f"/api/v1/models/{model_id}/predictions/{prediction_id}/explain")
    assert explain_res.status_code == 200
    
    explanation = explain_res.json()
    assert explanation["prediction_id"] == prediction_id
    assert "base_value" in explanation
    assert "prediction_value" in explanation
    assert "breakdown" in explanation
    
    breakdown = explanation["breakdown"]
    assert len(breakdown) == 2
    
    # Verify SHAP Efficiency property: base_value + sum(contributions) == prediction_value
    base_val = explanation["base_value"]
    pred_val = explanation["prediction_value"]
    contrib_sum = sum(item["contribution"] for item in breakdown)
    
    # The sum should match the predicted value within mathematical tolerance
    assert abs(base_val + contrib_sum - pred_val) < 0.03
