Phase 1 -> Upload works
Phase 2 -> Probe works
Phase 3 -> Fingerprint works
Phase 4 -> Predict works
Phase 5 -> Productionize

Each phase ends with a demoable artifact.
---

# Phase 1 — Model Registry Foundation

## Goal

Get models into the system and persist metadata.

---

## Deliverables

### Database

Create:

```sql
models
fingerprints
probe_results
inference_events
```

using Alembic.

---

### Model Upload API

```http
POST /models
```

Accept:

* .pkl
* .joblib
* .pt
* .onnx

Store model on disk.

Store metadata in DB.

---

### Schema Storage

Persist:

```json
{
  "features": [
    {
      "name": "age",
      "type": "float",
      "min": 0,
      "max": 100
    }
  ]
}
```

---

### Framework Detection

Detect:

```text
sklearn
pytorch
onnx
```

and store it.

---

### Status Lifecycle

```text
uploaded
ready
failed
```

---

## APIs

```http
POST /models
GET /models
GET /models/{id}
DELETE /models/{id}
```

---

## Demo

```bash
curl -F file=@model.pkl ...
```

returns:

```json
{
  "model_id":"abc123",
  "framework":"sklearn",
  "status":"ready"
}
```

---

## Milestone

You can upload models and retrieve metadata.

Nothing ML-specific yet.

---

# Phase 2 — Unified Model Runtime

## Goal

Build framework-independent inference.

---

## Deliverables

### ModelWrapper

Single interface:

```python
predict(input_array)
```

for:

* sklearn
* PyTorch
* ONNX

---

### PredictionResult

```python
PredictionResult(
    predicted_class,
    confidence,
    raw_output
)
```

---

### Loader System

```python
load_model(path)
```

returns:

```python
ModelWrapper
```

---

### Unit Tests

Verify identical interface across:

* sklearn
* PyTorch
* ONNX

---

## Demo

```python
wrapper.predict(sample)
```

works regardless of framework.

---

## Milestone

ModelMesh can run inference on any supported model.

---

# Phase 3 — Probing Engine

## Goal

Systematically explore model behavior.

---

## Deliverables

### Latin Hypercube Sampling

Generate:

```text
1000 synthetic inputs
```

from schema bounds.

---

### Probe Runner

For each probe:

```text
input
prediction
confidence
```

stored in DB.

---

### Probe Results Table

Populate:

```sql
probe_results
```

---

### Configurable Parameters

```python
PROBE_COUNT=1000
```

---

## Tests

Verify:

* correct sample count
* confidence range
* DB persistence

---

## Demo

```text
1000 probes generated
1000 probe_results stored
```

---

## Milestone

You now have raw behavioral data.

---

# Phase 4 — Fingerprint Engine

## Goal

Convert probe data into a reusable artifact.

---

## Deliverables

### Confidence Histogram

Compute:

```text
0.0-0.1
...
0.9-1.0
```

---

### Prediction Distribution

```text
Class A: 53%
Class B: 47%
```

---

### Uncertainty Region Detection

Rules:

```text
variance > p75
AND
confidence < 0.65
```

Generate:

```json
{
  "feature_bounds": {}
}
```

---

### Decision Samples

Store representative samples.

---

### Fingerprint Serialization

Create:

```json
{
  "fingerprint_hash": "...",
  "probe_count": 1000,
  ...
}
```

---

### Endpoint

```http
GET /models/{id}/fingerprint
```

---

## Demo

```bash
curl /models/id/fingerprint
```

returns fingerprint.

---

## Milestone

ModelMesh now produces its core artifact.

---

# Phase 5 — Prediction Service

## Goal

Serve real predictions.

---

## Deliverables

### Predict Endpoint

```http
POST /models/{id}/predict
```

---

### Pydantic Validation

Validate against stored schema.

---

### Latency Measurement

Return:

```json
{
  "prediction":1,
  "confidence":0.91,
  "latency_ms":4.2
}
```

---

### Inference Logging

Write:

```sql
inference_events
```

---

## Demo

Send request.

Receive prediction.

Inference logged.

---

## Milestone

End-to-end serving works.

---

# Phase 6 — Production Readiness

## Goal

Make V1 cloneable and resume-ready.

---

## Deliverables

### Docker Compose

Services:

```text
api
postgres
```

---

### Dockerfile

Single container build.

---

### GitHub Actions

Run:

```text
ruff
pytest
```

---

### README

Include:

* architecture diagram
* quickstart
* API examples

---

### Demo Script

```bash
./demo/run_demo.sh
```

Runs:

```text
upload
fingerprint
predict
```

---

## Final Demo

```text
Upload Model
      ↓
Framework Detection
      ↓
1000 Probe Sweep
      ↓
Fingerprint Generated
      ↓
Retrieve Fingerprint
      ↓
Run Prediction
```

At the end of Phase 6, V1 is genuinely complete and V2 can start immediately by consuming the existing `fingerprints` and `inference_events` tables for FAISS monitoring and drift detection.
