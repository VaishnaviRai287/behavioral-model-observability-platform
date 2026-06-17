#!/usr/bin/env python3
"""
ModelMesh Demo Script
---------------------
Uploads a sample sklearn model, runs the full ingestion pipeline
(probe + fingerprint), sends 30 normal predictions followed by
45 drifted predictions, then prints the live health status.

Watch the novelty timeline at http://localhost:3000 as you run this.
"""
import io
import json
import pickle
import time
import urllib.request
import urllib.error

import numpy as np
from sklearn.linear_model import LogisticRegression

BASE_URL = "http://localhost:8000"


def banner(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}") as r:
        return json.loads(r.read())


def upload_model(model_bytes: bytes, name: str, schema: dict) -> dict:
    """Multipart POST to /api/v1/models"""
    import email.mime.multipart
    import email.mime.base
    import email.encoders

    boundary = "----ModelMeshBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="name"\r\n\r\n'
        f"{name}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="schema"\r\n\r\n'
        f"{json.dumps(schema)}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="model.pkl"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + model_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/models",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main() -> None:
    print("🚀  ModelMesh Demo — full ingestion → drift simulation")

    # ── 1. Train model ──────────────────────────────────────────────────────
    banner("Step 1 · Train a Logistic Regression model")
    X = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float)
    y = np.array([0, 0, 0, 1])
    clf = LogisticRegression()
    clf.fit(X, y)

    buf = io.BytesIO()
    pickle.dump(clf, buf)
    model_bytes = buf.getvalue()
    print(f"  ✅  Trained. Serialised size: {len(model_bytes)} bytes")

    schema = {
        "features": [
            {"name": "x1", "type": "float", "min": 0.0, "max": 1.0},
            {"name": "x2", "type": "float", "min": 0.0, "max": 1.0},
        ]
    }

    # ── 2. Register model ────────────────────────────────────────────────────
    banner("Step 2 · Register model  POST /api/v1/models")
    model = upload_model(model_bytes, "demo_lr_model", schema)
    model_id = model["id"]
    print(f"  ✅  Registered  id={model_id}  framework={model['framework']}")

    # ── 3. Probe ─────────────────────────────────────────────────────────────
    banner("Step 3 · LHS probe sweep  POST /api/v1/models/{id}/probe")
    session = post_json(f"/api/v1/models/{model_id}/probe", {"n_probes": 100})
    session_id = session["id"]
    print(f"  ✅  Probe done  mean_conf={session['mean_confidence']:.4f}  dominant_class={session['dominant_class']}")

    # ── 4. Fingerprint ───────────────────────────────────────────────────────
    banner("Step 4 · Build fingerprint  POST /api/v1/probes/{id}/fingerprint")
    fp = post_json(f"/api/v1/probes/{session_id}/fingerprint", {})
    print(f"  ✅  Fingerprint  entropy={fp['entropy']:.4f}  uncertainty_rate={fp['uncertainty_rate']:.4f}")

    # ── 5. Normal traffic ────────────────────────────────────────────────────
    banner("Step 5 · Send 30 normal predictions (low-value region [0.05–0.35])")
    for i in range(30):
        x1 = round(np.random.uniform(0.05, 0.35), 3)
        x2 = round(np.random.uniform(0.05, 0.35), 3)
        res = post_json(f"/api/v1/models/{model_id}/predict", {"features": {"x1": x1, "x2": x2}})
        print(f"  [{i+1:02d}/30] class={res['predicted_class']}  conf={res['confidence']:.4f}  novel={res['novelty_flag']}")
        time.sleep(0.05)

    # ── 6. Drifted traffic ───────────────────────────────────────────────────
    banner("Step 6 · Inject 45 drifted predictions (high-value region [0.75–0.98])")
    for i in range(45):
        x1 = round(np.random.uniform(0.75, 0.98), 3)
        x2 = round(np.random.uniform(0.75, 0.98), 3)
        res = post_json(f"/api/v1/models/{model_id}/predict", {"features": {"x1": x1, "x2": x2}})
        print(f"  [{i+1:02d}/45] class={res['predicted_class']}  conf={res['confidence']:.4f}  novel={res['novelty_flag']}")
        time.sleep(0.05)

    # ── 7. Health check ──────────────────────────────────────────────────────
    banner("Step 7 · Live health summary  GET /api/v1/models/{id}/health")
    health = get_json(f"/api/v1/models/{model_id}/health")
    print(f"  novelty_rate : {health['novelty_rate'] * 100:.1f}%")
    print(f"  active_alerts: {health['active_alerts']}")
    print(f"  drift_scores : {health['drift_scores']}")

    print(f"\n✅  Done. Open http://localhost:3000/models/{model_id} to see the dashboard.\n")


if __name__ == "__main__":
    main()
