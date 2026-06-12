import pytest
import os
from uuid import UUID, uuid4
from httpx import AsyncClient
from app.crud.observability import observability_crud

@pytest.mark.asyncio
async def test_reasoning_and_changelog_workflow(client: AsyncClient, db_session):
    # 1. Register Model A (v1)
    artifact_path = os.path.abspath("test_artifacts/test_sklearn.joblib")
    payload_a = {
        "name": "reasoning_model",
        "version": "1.0.0",
        "framework": "scikit-learn",
        "task_type": "tabular_classification",
        "artifact_uri": artifact_path,
        "input_schema": {
            "features": [
                {"name": "tenure", "type": "int", "shape": [], "min": 0, "max": 100},
                {"name": "monthly_charges", "type": "float", "shape": [], "min": 0.0, "max": 200.0}
            ]
        },
        "output_schema": {
            "features": [
                {"name": "churn_probability", "type": "float", "shape": []}
            ]
        }
    }
    register_a = await client.post("/api/v1/models/", json=payload_a)
    assert register_a.status_code == 201
    model_id_a = UUID(register_a.json()["id"])

    # 2. Register Model B (v2)
    payload_b = payload_a.copy()
    payload_b["version"] = "2.0.0"
    register_b = await client.post("/api/v1/models/", json=payload_b)
    assert register_b.status_code == 201
    model_id_b = UUID(register_b.json()["id"])

    # 3. Generate fingerprints by probing both models
    probe_a = await client.post(f"/api/v1/models/{model_id_a}/probe?num_samples=50")
    assert probe_a.status_code == 200
    probe_b = await client.post(f"/api/v1/models/{model_id_b}/probe?num_samples=50")
    assert probe_b.status_code == 200

    # 4. Compare models using LLM Reasoning
    compare_res = await client.post(f"/api/v1/observability/compare?model_id_a={model_id_a}&model_id_b={model_id_b}")
    assert compare_res.status_code == 200
    compare_data = compare_res.json()
    assert compare_data["model_id_a"] == str(model_id_a)
    assert compare_data["model_id_b"] == str(model_id_b)
    assert "Behavioral Changelog" in compare_data["changelog"]
    assert "Model Comparison Report" in compare_data["changelog"]

@pytest.mark.asyncio
async def test_alert_explanation_workflow(client: AsyncClient, db_session):
    # 1. Register a model
    artifact_path = os.path.abspath("test_artifacts/test_sklearn.joblib")
    payload = {
        "name": "explainable_model",
        "version": "1.0.0",
        "framework": "scikit-learn",
        "task_type": "tabular_classification",
        "artifact_uri": artifact_path,
        "input_schema": {
            "features": [
                {"name": "tenure", "type": "int", "shape": [], "min": 0, "max": 100},
                {"name": "monthly_charges", "type": "float", "shape": [], "min": 0.0, "max": 200.0}
            ]
        },
        "output_schema": {
            "features": [
                {"name": "churn_probability", "type": "float", "shape": []}
            ]
        }
    }
    register_res = await client.post("/api/v1/models/", json=payload)
    model_id = UUID(register_res.json()["id"])

    # 2. Probe to generate baseline fingerprint
    probe_res = await client.post(f"/api/v1/models/{model_id}/probe?num_samples=50")
    assert probe_res.status_code == 200

    # 3. Create mock alert
    alert = await observability_crud.create_alert(
        db=db_session,
        model_id=model_id,
        alert_type="FEATURE_DRIFT",
        severity="warning",
        message="Test feature drift alert message.",
        metric_value=0.55
    )
    alert_id = alert.id

    # 4. Trigger alert explanation API
    explain_res = await client.post(f"/api/v1/observability/alerts/{alert_id}/explain")
    assert explain_res.status_code == 200
    explain_data = explain_res.json()
    assert explain_data["alert_id"] == str(alert_id)
    assert "Diagnostic Alert Analysis" in explain_data["explanation"]
    assert "Root Cause Evaluation" in explain_data["explanation"]

@pytest.mark.asyncio
async def test_reasoning_validation_errors(client: AsyncClient):
    # Test compare invalid ids
    bad_id_1 = uuid4()
    bad_id_2 = uuid4()
    compare_res = await client.post(f"/api/v1/observability/compare?model_id_a={bad_id_1}&model_id_b={bad_id_2}")
    assert compare_res.status_code == 404

    # Test explain invalid alert id
    bad_alert_id = uuid4()
    explain_res = await client.post(f"/api/v1/observability/alerts/{bad_alert_id}/explain")
    assert explain_res.status_code == 404
