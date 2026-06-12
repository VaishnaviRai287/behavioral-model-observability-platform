import pytest
import os
from httpx import AsyncClient
from app.crud.observability import observability_crud

@pytest.mark.asyncio
async def test_observability_pipeline(client: AsyncClient, db_session):
    # 1. Register model
    artifact_path = os.path.abspath("test_artifacts/test_sklearn.joblib")
    payload = {
        "name": "observability_model",
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
    
    from uuid import UUID
    register_res = await client.post("/api/v1/models/", json=payload)
    model_id = UUID(register_res.json()["id"])


    # 2. Fire predictions (which triggers inference logging)
    predict_payload = {
        "inputs": [
            {"tenure": 12, "monthly_charges": 70.5},
            {"tenure": 4, "monthly_charges": 22.0}
        ]
    }
    pred_res = await client.post(f"/api/v1/models/{model_id}/predict", json=predict_payload)
    assert pred_res.status_code == 200

    # 3. Verify Inference logs are generated in the database
    logs = await observability_crud.get_recent_logs(db_session, model_id)
    assert len(logs) == 2
    assert logs[0].features["tenure"] in [12, 4]

    # 4. Trigger manual mock alert creation and fetch alerts
    await observability_crud.create_alert(
        db=db_session,
        model_id=model_id,
        alert_type="FEATURE_DRIFT",
        severity="warning",
        message="Manual mock drift detection alert.",
        metric_value=0.45
    )

    alert_res = await client.get(f"/api/v1/observability/{model_id}/alerts")
    assert alert_res.status_code == 200
    alerts = alert_res.json()
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "FEATURE_DRIFT"
    assert alerts[0]["metric_value"] == 0.45
