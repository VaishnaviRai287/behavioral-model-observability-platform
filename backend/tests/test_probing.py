import pytest
import os
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_probing_and_fingerprint_workflow(client: AsyncClient):
    # 1. Register a test model (pointing to mock Sklearn artifact)
    artifact_path = os.path.abspath("test_artifacts/test_sklearn.joblib")
    payload = {
        "name": "probing_sklearn_model",
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
    assert register_res.status_code == 201
    model_id = register_res.json()["id"]

    # 2. Trigger synthetic probing (num_samples=100)
    probe_res = await client.post(f"/api/v1/models/{model_id}/probe?num_samples=100")
    assert probe_res.status_code == 200
    fingerprint = probe_res.json()
    
    assert fingerprint["model_id"] == model_id
    assert fingerprint["num_samples"] == 100
    assert "class_distribution" in fingerprint
    assert "confidence_distribution" in fingerprint
    assert "high_uncertainty_regions" in fingerprint
    assert "boundary_samples" in fingerprint
    
    # 3. Retrieve latest fingerprint
    get_res = await client.get(f"/api/v1/models/{model_id}/fingerprint")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == fingerprint["id"]
