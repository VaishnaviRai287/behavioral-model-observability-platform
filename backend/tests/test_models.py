import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_and_retrieve_model(client: AsyncClient):
    # Setup model registry schema payloads matching Pydantic validator format
    payload = {
        "name": "churn_classifier",
        "version": "1.0.0",
        "framework": "scikit-learn",
        "task_type": "tabular_classification",
        "artifact_uri": "/models/churn.joblib",
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

    # 1. Register a model
    create_response = await client.post("/api/v1/models/", json=payload)
    assert create_response.status_code == 201
    data = create_response.json()
    assert data["name"] == "churn_classifier"
    model_id = data["id"]

    # 2. Get registered model details
    get_response = await client.get(f"/api/v1/models/{model_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "churn_classifier"

    # 3. List all models
    list_response = await client.get("/api/v1/models/")
    assert list_response.status_code == 200
    assert len(list_response.json()) > 0

    # 4. Deregister model
    delete_response = await client.delete(f"/api/v1/models/{model_id}")
    assert delete_response.status_code == 200