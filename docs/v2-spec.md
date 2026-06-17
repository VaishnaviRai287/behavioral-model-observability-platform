**V2 — Behavioral Monitoring Platform**

The thesis shift from V1: V1 *understands* the model at registration time. V2 *watches* it at inference time. The fingerprint built in V1 becomes the baseline everything in V2 is measured against.

---

**What V2 adds — the three pillars**

**Pillar 1 — Latent Space Monitor (FAISS)**
The core new ML capability. At inference time, extract the model's internal activation vector for each prediction request and measure how far it lands from the training-time distribution indexed in FAISS. This catches combinatorial novelty — inputs that look normal feature by feature but land in territory the model has never seen. Standard KS/PSI can't catch this.

Two things happen at fingerprint build time that didn't in V1: the probing engine now also extracts activation vectors via PyTorch forward hooks (or sklearn proxy embeddings), and builds a FAISS `IndexFlatL2` over them. This index is stored alongside the fingerprint.

At inference time: extract activation → query FAISS for k-NN distance → if mean distance exceeds the baseline threshold computed from probe-time distances, tag the inference event as `NOVEL`.

**Pillar 2 — Drift Detection (KS + PSI)**
A Celery beat task runs every 50 inference events. For each feature dimension, it computes the KS statistic and PSI against the probe-sweep baseline distribution stored in the fingerprint. Writes a drift score per feature to a `drift_events` table. Two thresholds: warning and critical.

This is the feature-level complement to the latent space monitor. KS/PSI catches marginal distribution shift on individual features. FAISS catches combinatorial novelty. Together they cover the full drift detection surface.

**Pillar 3 — Alert Engine + Prometheus + Grafana**
Two alert types produced by the above: `LATENT_NOVELTY` (FAISS distance spike) and `FEATURE_DRIFT` (KS/PSI breach). Stored in an `alerts` table. GET /models/{id}/alerts and GET /models/{id}/health endpoints.

Prometheus scrapes `/metrics` from FastAPI via `prometheus-fastapi-instrumentator` plus four custom metrics: `modelmesh_novelty_score` histogram, `modelmesh_boundary_proximity` gauge, `modelmesh_drift_score` gauge per feature, `modelmesh_alert_total` counter by alert type.

Grafana provisioned via JSON in the repo — three panels: novelty score distribution over time, per-feature drift score heatmap, alert rate counter. Loads automatically on `docker-compose up`. No manual setup.

---

**New tables**

`faiss_indexes` — model_id FK, index_file_path, vector_dim, vector_count, baseline_mean_distance, baseline_std_distance, created_at

`drift_events` — id, model_id FK, feature_name, ks_statistic, psi_score, severity (warning/critical), window_start, window_end, created_at

`alerts` — id, model_id FK, alert_type (LATENT_NOVELTY / FEATURE_DRIFT / BOUNDARY_APPROACH), severity, metadata JSONB, resolved_at, created_at

`inference_events` gets two new columns: `faiss_distance` FLOAT, `novelty_flag` BOOLEAN — add via Alembic migration, don't touch the existing table definition.

**Changes to existing V1 code**

`app/probing/engine.py` — after running the probe sweep, also extract activation vectors. For PyTorch: register a forward hook on the penultimate layer before the sweep, collect hook outputs. For sklearn: use `decision_function` output or leaf node embeddings as proxy. Pass vectors to `faiss_indexer.py` to build the index.

`app/services/prediction_service.py` — after running inference, call `novelty_scorer.novelty_score(activation_vector)` and write `faiss_distance` and `novelty_flag` back to the inference event row. This is a single additional function call — the rest of the predict flow is unchanged.

`docker-compose.yml` — add four new services: `redis`, `celery-worker`, `prometheus`, `grafana`. Prometheus config mounts a `prometheus.yml` pointing at the FastAPI `/metrics` endpoint. Grafana mounts `grafana/dashboards/modelmesh.json` and `grafana/provisioning/`.

---

**API surface — new endpoints**

| Endpoint | Purpose |
|---|---|
| GET /models/{id}/alerts | List all alerts, filterable by type and severity |
| GET /models/{id}/health | Novelty rate, drift scores per feature, alert count |
| GET /models/{id}/drift | Full drift event history with KS/PSI per feature |
| POST /models/{id}/alerts/{alert_id}/resolve | Mark alert resolved |

---

**Updated docker-compose services**

```
api          # FastAPI — unchanged
db           # PostgreSQL — unchanged
redis        # new — Celery broker
celery       # new — runs drift_task beat
prometheus   # new — scrapes /metrics
grafana      # new — behavioral dashboard
```

---

**V2 demo**

```bash
# Send normal traffic
for i in {1..100}; do curl -X POST /models/abc123/predict -d '{"age": 35, "tenure": 24}'; done

# Send drifted traffic
for i in {1..50}; do curl -X POST /models/abc123/predict -d '{"age": 68, "tenure": 2}'; done

# Check alerts
curl /models/abc123/alerts
→ [{"type": "LATENT_NOVELTY", "severity": "critical"},
   {"type": "FEATURE_DRIFT", "feature": "tenure", "ks_statistic": 0.71}]

# Check health
curl /models/abc123/health
→ {"novelty_rate": 0.46, "drift_scores": {"age": 0.23, "tenure": 0.71},
   "active_alerts": 2}
```

Grafana opens at `localhost:3000` showing the novelty score spike mid-demo. That's the V2 visual proof.

---

**Build order within V2**

Do these in sequence — each one is a dependency for the next:

1. Alembic migration for new columns and tables first — nothing else can run without the schema
2. FAISS indexer — modify probing engine to extract activations and build the index at fingerprint time
3. Novelty scorer — wire into prediction_service, test that faiss_distance populates on every predict call
4. KS + PSI drift detector — unit test this in isolation with synthetic distributions before wiring into Celery
5. Celery beat task — wire drift_detector into the task, test that it fires every 50 events
6. Alert engine — consumes output of novelty scorer and drift detector, writes to alerts table
7. New endpoints — alerts, health, drift
8. Prometheus metrics — instrument after the logic is working, not before
9. Grafana dashboard — last, once metrics are flowing

**The hardest part is step 2** — PyTorch forward hooks need to work correctly both at probe time (batch, building the index) and at inference time (single input, querying the index). Get this right before touching anything else in V2.
