#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
import time
import random

BASE_URL = "http://localhost:8000"

def get_latest_model_id():
    try:
        url = f"{BASE_URL}/api/v1/models"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as response:
            models = json.loads(response.read().decode())
            if not models:
                return None
            # Pick the first one
            return models[0]["id"]
    except Exception as e:
        print(f"Error fetching models: {e}")
        return None

def send_prediction(model_id, x1, x2):
    url = f"{BASE_URL}/api/v1/models/{model_id}/predict"
    payload = {
        "features": {
            "x1": x1,
            "x2": x2
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            return res_data
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode()}")
        return None
    except Exception as e:
        print(f"Connection Error: {e}")
        return None

def main():
    print("🎯 ModelMesh Live Telemetry Simulator")
    print("-------------------------------------")
    
    model_id = get_latest_model_id()
    if not model_id:
        print("❌ No models found registered in the system. Please register a model first.")
        return
        
    print(f"Found latest model ID: {model_id}")
    print("\n🚀 Step 1: Sending 30 Normal Predictions (no drift)...")
    for i in range(30):
        # Normal inputs concentrated around [0.2, 0.2]
        x1 = round(random.uniform(0.05, 0.35), 3)
        x2 = round(random.uniform(0.05, 0.35), 3)
        res = send_prediction(model_id, x1, x2)
        if res:
            print(f"[{i+1}/30] Prediction: Class={res['predicted_class']} | Conf={res['confidence']:.4f} | Novelty={res['novelty_flag']}")
        time.sleep(0.1)

    print("\n🚨 Step 2: Injecting 45 Drifted Predictions (shifted distribution)...")
    for i in range(45):
        # Drifted inputs concentrated around [0.85, 0.85] (OOD/drifted but within schema bounds 0-1)
        x1 = round(random.uniform(0.75, 0.98), 3)
        x2 = round(random.uniform(0.75, 0.98), 3)
        res = send_prediction(model_id, x1, x2)
        if res:
            print(f"[{i+1}/45] Drift Prediction: Class={res['predicted_class']} | Conf={res['confidence']:.4f} | Novelty={res['novelty_flag']}")
        time.sleep(0.1)

    print("\n📊 Simulation finished! Check your dashboard at http://localhost:3000 to see the real-time novelty timeline and feature drift charts.")

if __name__ == "__main__":
    main()
