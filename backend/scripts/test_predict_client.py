import httpx
import sys

def main():
    client = httpx.Client(base_url="http://localhost:8000")
    
    # 1. Register scikit-learn model
    payload = {
        "name": "production_sklearn_lr",
        "version": "1.0.0",
        "framework": "scikit-learn",
        "task_type": "tabular_classification",
        "artifact_uri": "model_artifacts/sklearn_logistic.joblib",
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
    
    print("Registering scikit-learn model...")
    res = client.post("/api/v1/models/", json=payload)
    if res.status_code == 400:
        print("Model already registered. Listing models to fetch ID...")
        models = client.get("/api/v1/models/").json()
        model_id = [m["id"] for m in models if m["name"] == "production_sklearn_lr"][0]
    else:
        model_id = res.json()["id"]
        
    print(f"Model ID: {model_id}")

    # 2. Run manual predictions
    predict_payload = {
        "inputs": [
            {"tenure": 12, "monthly_charges": 70.5},
            {"tenure": 3, "monthly_charges": 22.0}
        ]
    }
    print("Executing manual prediction queries...")
    pred_res = client.post(f"/api/v1/models/{model_id}/predict", json=predict_payload)
    
    print("Prediction status code:", pred_res.status_code)
    print("Response JSON:")
    print(pred_res.json())

if __name__ == "__main__":
    main()