import pytest
import os
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_sklearn_prediction_workflow(client: AsyncClient):
    # 1. Register Sklearn model pointing to generated test artifact
    artifact_path = os.path.abspath("test_artifacts/test_sklearn.joblib")
    payload = {
        "name": "sklearn_model",
        "version": "1.0.0",
        "framework": "scikit-learn",
        "task_type": "tabular_classification",
        "artifact_uri": artifact_path,
        "input_schema": {
            "features": [
                {"name": "tenure", "type": "int", "shape": []},
                {"name": "monthly_charges", "type": "float", "shape": []}
            ]
        },
        "output_schema": {
            "features": [
                {"name": "churn_probability", "type": "float", "shape": []}
            ]
        }
    }
    
    register_res = await client.post("/api/v1/models/", json=payload)
    assert register_res.status_code == 201
    model_id = register_res.json()["id"]

    # 2. Run clean predictions
    predict_payload = {
        "inputs": [
            {"tenure": 12, "monthly_charges": 70.5},
            {"tenure": 4, "monthly_charges": 22.0}
        ]
    }
    
    predict_res = await client.post(f"/api/v1/models/{model_id}/predict", json=predict_payload)
    assert predict_res.status_code == 200
    data = predict_res.json()
    assert "predictions" in data
    assert len(data["predictions"]) == 2
    assert "probabilities" in data
    assert len(data["probabilities"]) == 2

@pytest.mark.asyncio
async def test_pytorch_prediction_workflow(client: AsyncClient):
    # 1. Register PyTorch model pointing to test weights
    artifact_path = os.path.abspath("test_artifacts/test_pytorch.pt")
    payload = {
        "name": "pytorch_model",
        "version": "1.0.0",
        "framework": "pytorch",
        "task_type": "tabular_classification",
        "artifact_uri": artifact_path,
        "input_schema": {
            "features": [
                {"name": "f1", "type": "float", "shape": []},
                {"name": "f2", "type": "float", "shape": []}
            ]
        },
        "output_schema": {
            "features": [
                {"name": "class_probability", "type": "float", "shape": []}
            ]
        }
    }
    
    register_res = await client.post("/api/v1/models/", json=payload)
    assert register_res.status_code == 201
    model_id = register_res.json()["id"]

    # 2. Run clean predictions
    predict_payload = {
        "inputs": [
            {"f1": 1.0, "f2": -0.5}
        ]
    }
    
    predict_res = await client.post(f"/api/v1/models/{model_id}/predict", json=predict_payload)
    assert predict_res.status_code == 200
    data = predict_res.json()
    assert "predictions" in data
    assert len(data["predictions"]) == 1

@pytest.mark.asyncio
async def test_prediction_schema_validation_failures(client: AsyncClient):
    # Register Sklearn Model
    artifact_path = os.path.abspath("test_artifacts/test_sklearn.joblib")
    payload = {
        "name": "validation_failure_model",
        "version": "1.0.0",
        "framework": "scikit-learn",
        "task_type": "tabular_classification",
        "artifact_uri": artifact_path,
        "input_schema": {
            "features": [
                {"name": "tenure", "type": "int", "shape": []},
                {"name": "monthly_charges", "type": "float", "shape": []}
            ]
        },
        "output_schema": {
            "features": [
                {"name": "churn_probability", "type": "float", "shape": []}
            ]
        }
    }
    register_res = await client.post("/api/v1/models/", json=payload)
    model_id = register_res.json()["id"]

    # Test missing field validation
    bad_payload_missing = {"inputs": [{"tenure": 12}]}  # missing monthly_charges
    res_missing = await client.post(f"/api/v1/models/{model_id}/predict", json=bad_payload_missing)
    assert res_missing.status_code == 422
    assert "missing required feature" in res_missing.json()["detail"]

    # Test bad type casting validation
    bad_payload_type = {"inputs": [{"tenure": "not_an_int", "monthly_charges": 70.5}]}
    res_type = await client.post(f"/api/v1/models/{model_id}/predict", json=bad_payload_type)
    assert res_type.status_code == 422
    assert "Failed to cast feature" in res_type.json()["detail"]