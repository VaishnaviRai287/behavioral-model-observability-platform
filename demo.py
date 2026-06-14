#!/usr/bin/env python3
import io
import json
import pickle
import time
import numpy as np
import httpx
from sklearn.linear_model import LogisticRegression

BASE_URL = "http://localhost:8000"


def print_header(title):
    print("\n" + "=" * 60)
    print(f"👉 {title}")
    print("=" * 60)


def main():
    print("🚀 Starting ModelMesh Interactive Demo...")

    # ──────────────────────────────────────────────────────────────────────────
    # Step 1: Train a model
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Step 1: Training a Logistic Regression Model locally")
    
    # 2 features, simple classification
    X = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float)
    y = np.array([0, 0, 0, 1])
    
    model = LogisticRegression()
    model.fit(X, y)
    
    # Save to a bytes buffer
    model_buffer = io.BytesIO()
    pickle.dump(model, model_buffer)
    model_buffer.seek(0)
    print("✅ Model trained successfully. Pickled size:", len(model_buffer.getvalue()), "bytes")

    # Define features and bounds
    schema = {
        "features": [
            {"name": "x1", "type": "float", "min": 0.0, "max": 1.0},
            {"name": "x2", "type": "float", "min": 0.0, "max": 1.0}
        ]
    }

    # ──────────────────────────────────────────────────────────────────────────
    # Step 2: Register the model
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Step 2: Registering Model with ModelMesh (POST /api/v1/models)")
    
    files = {"file": ("model.pkl", model_buffer, "application/octet-stream")}
    data = {"name": "iris_logistic_regression", "schema": json.dumps(schema)}
    
    try:
        response = httpx.post(f"{BASE_URL}/api/v1/models", data=data, files=files)
        if response.status_code != 201:
            print("❌ Failed to register model:", response.text)
            return
        
        model_info = response.json()
        model_id = model_info["id"]
        print(f"✅ Model registered successfully!")
        print(f"   ID:         {model_info['id']}")
        print(f"   Name:       {model_info['name']}")
        print(f"   Framework:  {model_info['framework']}")
        print(f"   Status:     {model_info['status']}")
    except Exception as e:
        print("❌ Error connecting to ModelMesh API. Is the server running on port 8000?")
        print(e)
        return

    # ──────────────────────────────────────────────────────────────────────────
    # Step 3: Run Probing
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Step 3: Running a Probe Session via LHS (POST /api/v1/models/{id}/probe)")
    
    probe_payload = {"n_probes": 100}
    response = httpx.post(f"{BASE_URL}/api/v1/models/{model_id}/probe", json=probe_payload)
    if response.status_code != 201:
        print("❌ Probing failed:", response.text)
        return
        
    probe_session = response.json()
    session_id = probe_session["id"]
    print(f"✅ Probe session completed!")
    print(f"   Session ID:       {probe_session['id']}")
    print(f"   Probes Generated: {probe_session['n_probes']}")
    print(f"   Mean Confidence:  {probe_session['mean_confidence']:.4f}")
    print(f"   Dominant Class:   {probe_session['dominant_class']}")
    print(f"   Distribution:     {probe_session['class_distribution']}")

    # ──────────────────────────────────────────────────────────────────────────
    # Step 4: Create Baseline Fingerprint
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Step 4: Generating Baseline Fingerprint (POST /probes/{id}/fingerprint)")
    
    response = httpx.post(f"{BASE_URL}/api/v1/probes/{session_id}/fingerprint")
    if response.status_code != 201:
        print("❌ Fingerprinting failed:", response.text)
        return
        
    fingerprint = response.json()
    print(f"✅ Baseline fingerprint generated!")
    print(f"   Fingerprint ID:   {fingerprint['id']}")
    print(f"   Entropy:          {fingerprint['entropy']:.4f}")
    print(f"   Uncertainty Rate: {fingerprint['uncertainty_rate']:.4f}")
    print(f"   Class Bias:       {fingerprint['class_bias']:.4f}")

    # ──────────────────────────────────────────────────────────────────────────
    # Step 5: Simulate Live Traffic Predictions
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Step 5: Simulating Live Traffic (POST /api/v1/models/{id}/predict)")
    print("Serving 15 predictions...")
    
    # We send inputs close to [1.0, 1.0] to test the model's behavior
    for i in range(15):
        pred_payload = {
            "features": {
                "x1": round(np.random.uniform(0.7, 1.0), 3),
                "x2": round(np.random.uniform(0.7, 1.0), 3)
            }
        }
        res = httpx.post(f"{BASE_URL}/api/v1/models/{model_id}/predict", json=pred_payload)
        data = res.json()
        print(f"   Prediction #{i+1:02d}: Class={data['predicted_class']} | Conf={data['confidence']:.4f} | Latency={data['latency_ms']:.2f}ms")
        time.sleep(0.05)

    # ──────────────────────────────────────────────────────────────────────────
    # Step 6: Check Drift Status
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Step 6: Checking Live Drift Verdict (GET /models/{id}/drift-status)")
    
    response = httpx.get(f"{BASE_URL}/api/v1/models/{model_id}/drift-status")
    if response.status_code != 200:
        print("❌ Failed to get drift status:", response.text)
        return
        
    drift_data = response.json()
    print("📊 Live Drift Status:")
    print(f"   Verdict:            {drift_data['verdict'].upper()}")
    print(f"   Similarity Score:   {drift_data['similarity_score']:.4f}")
    print(f"   Recent Predictions: {drift_data['n_recent_predictions']}")
    print(f"   Details:")
    print(f"     - Histogram Distance: {drift_data['details']['histogram_distance']:.4f}")
    print(f"     - Class Bias Delta:   {drift_data['details']['class_bias_delta']:.4f}")
    print(f"     - Entropy Delta:      {drift_data['details']['entropy_delta']:.4f}")

    # ──────────────────────────────────────────────────────────────────────────
    # Step 7: Check Production Health Checks
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Step 7: Production Health Checks (GET /health/ready)")
    
    response = httpx.get(f"{BASE_URL}/health/ready")
    if response.status_code == 200:
        health_data = response.json()
        print("🩺 Server Health:")
        print(f"   Status:           {health_data['status']}")
        print(f"   Database Status:  {health_data['db']}")
        print(f"   Model Cache Size: {health_data['model_cache_size']} model(s) loaded in memory")
    else:
        print("❌ Health check failed:", response.text)

    # ──────────────────────────────────────────────────────────────────────────
    # Step 8: Cleanup
    # ──────────────────────────────────────────────────────────────────────────
    print_header("Step 8: Cleanup (DELETE /models/{id})")
    response = httpx.delete(f"{BASE_URL}/api/v1/models/{model_id}")
    if response.status_code == 200:
        print("✅ Model deleted and cache invalidated successfully!")
    else:
        print("❌ Cleanup failed:", response.text)
        
    print("\n🎉 ModelMesh Demo Finished successfully!")


if __name__ == "__main__":
    main()
