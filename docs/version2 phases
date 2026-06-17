**V2 broken into 3 phases, each shippable on its own.**

---

**V2-A — Latent Space Foundation**
*FAISS index built at probe time, novelty score computed at inference time. No alerts, no Celery, no Grafana yet. Just the core ML capability working end to end.*

What gets built:
- Alembic migration — add `faiss_distance` FLOAT and `novelty_flag` BOOLEAN to `inference_events`. Create `faiss_indexes` table.
- `app/monitoring/faiss_indexer.py` — builds `IndexFlatL2` from activation vectors, stores index file, computes baseline mean + std distance from probe-time vectors, saves to `faiss_indexes` table.
- `app/monitoring/novelty_scorer.py` — loads FAISS index, runs k-NN query on a single activation vector, returns distance + novelty flag.
- Modify `app/probing/engine.py` — after sweep, extract activation vectors. PyTorch: forward hook on penultimate layer. sklearn: `decision_function` output. Pass to `faiss_indexer.build()`.
- Modify `app/services/prediction_service.py` — after inference, extract activation vector, call `novelty_scorer.score()`, write `faiss_distance` and `novelty_flag` back to the inference event row.
- Tests — probe a model → assert `faiss_indexes` row created with non-zero vector count. Predict → assert `faiss_distance` populated on inference event. Predict with OOD input → assert `novelty_flag` True.

Done when: every prediction has a FAISS distance logged and OOD inputs are correctly flagged. Nothing else.

---

**V2-B — Drift Detection + Alert Engine**
*Statistical drift computed on batches of inference events. Alerts created when thresholds breached. No Celery yet — triggered manually or on a request count threshold checked synchronously.*

What gets built:
- Alembic migration — create `drift_events` table and `alerts` table.
- `app/monitoring/drift_detector.py` — takes last N inference events for a model, computes KS statistic and PSI per feature against the fingerprint's probe distribution baseline. Returns drift score per feature with severity (warning / critical).
- `app/monitoring/alert_engine.py` — consumes output of novelty scorer and drift detector. Creates `alerts` rows. Deduplicates — don't create a new alert if one of the same type is already active for this model.
- Modify `app/services/prediction_service.py` — after every 50th inference event (check `count % 50 == 0`), trigger drift detection synchronously. If thresholds breached, call alert engine. This avoids Celery complexity while keeping the logic correct — Celery comes in V2-C.
- New router `app/routers/alerts.py` — GET /models/{id}/alerts (filterable by type, severity). POST /models/{id}/alerts/{id}/resolve.
- Expand `app/routers/health.py` — GET /models/{id}/health returns novelty rate (% of recent events flagged), drift scores per feature, active alert count.
- Tests — send 50 normal predictions then 50 drifted predictions → assert drift_events created → assert FEATURE_DRIFT alert created. Send OOD inputs → assert LATENT_NOVELTY alert created. GET /health → assert novelty_rate and drift_scores populated.

Done when: alerts fire correctly on drifted traffic and the health endpoint returns meaningful data.

---

**V2-C — Celery + Prometheus + Grafana**
*Move drift detection off the request path into a proper async task. Add observability layer. This is what makes V2 production-grade.*

What gets built:
- `app/tasks/celery_app.py` — Celery config pointing at Redis broker.
- `app/tasks/drift_task.py` — Celery beat task, runs every 50 events via a counter in Redis. Calls `drift_detector.run()` and `alert_engine.process()`. Remove the synchronous trigger added in V2-B.
- `app/metrics.py` — Prometheus custom metrics via `prometheus-fastapi-instrumentator` plus four custom gauges/histograms: `modelmesh_novelty_score`, `modelmesh_boundary_proximity`, `modelmesh_drift_score` (labelled by feature), `modelmesh_alert_total` (labelled by type).
- Update `/metrics` endpoint — expose custom metrics alongside default FastAPI instrumentation.
- `grafana/dashboards/modelmesh.json` — three panels: novelty score distribution over time, per-feature drift score heatmap, alert rate counter. Provisioned automatically.
- `grafana/provisioning/` — datasource config pointing at Prometheus.
- Update `docker-compose.yml` — add `redis`, `celery-worker`, `prometheus`, `grafana` services. Prometheus mounts `prometheus.yml` scraping FastAPI `/metrics`. Grafana mounts provisioning config.
- Tests — assert Celery task fires and produces drift_events. Assert `/metrics` endpoint returns `modelmesh_novelty_score` and `modelmesh_alert_total` metrics.
- Demo script update — `docker-compose up` → send traffic → Grafana opens at `localhost:3000` showing novelty spike.

Done when: `docker-compose up` brings the full stack online, Grafana dashboard loads automatically, and the demo script produces a visible novelty spike on the dashboard.

---

**Summary**

| Phase | Core capability | New infra | Done when |
|---|---|---|---|
| V2-A | FAISS novelty scoring at inference time | None | Every predict call has faiss_distance logged |
| V2-B | KS/PSI drift + alert engine | None | Alerts fire on drifted traffic |
| V2-C | Async tasks + Prometheus + Grafana | Redis, Celery, Prometheus, Grafana | docker-compose up → dashboard shows live metrics |

Start with V2-A. The FAISS indexer and the forward hook extraction are the hardest technical pieces in all of V2 — get those right first and the rest follows cleanly.
