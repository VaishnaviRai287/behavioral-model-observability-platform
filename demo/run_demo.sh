#!/usr/bin/env bash

# Exit immediately if any command fails
set -e

BASE_URL="http://localhost:8000"

echo "============================================================"
echo "🚀 Starting ModelMesh Churn Model Observability Demo"
echo "============================================================"

# Check if the server is running
if ! curl -s "${BASE_URL}/health/live" >/dev/null; then
  echo "❌ Error: ModelMesh API server is not running at ${BASE_URL}."
  echo "Please start the server first using: uvicorn app.main:app --reload"
  exit 1
fi

# 1. Upload & Register the Churn Model
echo -e "\n👉 Step 1: Uploading and Registering Churn Model..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/models" \
  -F "name=customer_churn" \
  -F "schema=<demo/schema.json" \
  -F "file=@demo/churn_model.pkl")

# Parse Model ID using sed/grep
MODEL_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*' | head -n 1 | cut -d'"' -f4 || true)

if [ -z "$MODEL_ID" ]; then
  echo "❌ Error: Failed to register model. Server response:"
  echo "$RESPONSE"
  exit 1
fi

echo "✅ Model Registered successfully! Model ID: ${MODEL_ID}"

# 2. Run Probing
echo -e "\n👉 Step 2: Triggering Latin Hypercube Sampling (LHS) Probe Session..."
PROBE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/models/${MODEL_ID}/probe" \
  -H "Content-Type: application/json" \
  -d '{"n_probes": 100}')

SESSION_ID=$(echo "$PROBE_RESPONSE" | grep -o '"id":"[^"]*' | head -n 1 | cut -d'"' -f4 || true)

if [ -z "$SESSION_ID" ]; then
  echo "❌ Error: Probing failed. Server response:"
  echo "$PROBE_RESPONSE"
  exit 1
fi

echo "✅ Probe Session Completed! Session ID: ${SESSION_ID}"

# 3. Create Baseline Fingerprint
echo -e "\n👉 Step 3: Generating Behavioral Baseline Fingerprint..."
FP_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/probes/${SESSION_ID}/fingerprint")
FP_ID=$(echo "$FP_RESPONSE" | grep -o '"id":"[^"]*' | head -n 1 | cut -d'"' -f4 || true)

if [ -z "$FP_ID" ]; then
  echo "❌ Error: Fingerprinting failed. Server response:"
  echo "$FP_RESPONSE"
  exit 1
fi

echo "✅ Baseline Fingerprint Generated! Fingerprint ID: ${FP_ID}"

# 4. Simulate Live Predictions
echo -e "\n👉 Step 4: Simulating Live Traffic Predictions..."
echo "Sending 15 live predictions matching high-risk churners..."
for i in {1..15}; do
  curl -s -X POST "${BASE_URL}/api/v1/models/${MODEL_ID}/predict" \
    -H "Content-Type: application/json" \
    -d "{\"features\": {\"tenure\": $((1 + RANDOM % 10)), \"monthly_charges\": $((80 + RANDOM % 40)), \"total_charges\": $((200 + RANDOM % 300))}}" > /dev/null
done
echo "✅ Traffic logs saved to database."

# 5. Check Drift Status
echo -e "\n👉 Step 5: Querying Live Observability Drift Status..."
curl -s "${BASE_URL}/api/v1/models/${MODEL_ID}/drift-status" | python3 -m json.tool

# 6. Check Ready Status and Cache
echo -e "\n👉 Step 6: Verifying Production readiness & Cache..."
curl -s "${BASE_URL}/health/ready" | python3 -m json.tool

# 7. Cleanup
echo -e "\n👉 Step 7: Cleaning up (Deleting model)..."
curl -s -X DELETE "${BASE_URL}/api/v1/models/${MODEL_ID}" >/dev/null
echo "✅ Model record, files, and cache entries purged."

echo -e "\n🎉 Observability Demo Completed Successfully!"
