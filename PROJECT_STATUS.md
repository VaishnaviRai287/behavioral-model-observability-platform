# ModelMesh — Project Status & Handoff

_Last updated: 2026-07-26. Written for any agent or human picking this project up next._

> **Nothing described below is committed yet.** Every change from this session is sitting
> uncommitted in the working tree (`git status` shows ~17 modified files + ~9 new
> files/directories). Review and commit in logical chunks before doing anything else —
> see [Uncommitted changes](#uncommitted-changes-in-this-working-tree) at the bottom for the exact file list.

---

## 1. What ModelMesh is

ModelMesh is a **self-hosted behavioral observability platform for ML models**. The
pitch: most ML monitoring tools watch the wrapper around a model (latency, HTTP error
rate, raw feature distributions). ModelMesh watches the model itself — it builds a
geometric fingerprint of a model's decision boundary at registration time, then uses
that fingerprint to detect when live traffic drifts into territory the model never
confidently handled.

**Core pipeline:** upload a trained model → auto-detect framework + extract
architecture → run a Latin Hypercube Sampling (LHS) probe sweep across the input
space → compile a behavioral fingerprint (confidence histogram, entropy, uncertainty
regions, FAISS index of latent activations) → every live prediction after that is
scored for latent-space novelty (FAISS k-NN distance) and, periodically, for
feature/output drift (KS statistic, PSI) against that baseline. SHAP gives global and
per-prediction explainability on top.

**Stack:** FastAPI + SQLAlchemy + Alembic + Postgres backend, Celery + Redis for async
drift processing, Next.js 14 (App Router) + Tailwind frontend, Docker Compose for
orchestration, PyTorch/TensorFlow/scikit-learn/ONNX support for ingested models.

---

## 2. What's done — pre-existing (before this session)

This was already built and working when this session started:

- **V1**: multi-framework ingestion (sklearn/PyTorch/TF-Keras/ONNX), framework
  auto-detection, architecture extraction, deterministic model signature, LHS probing
  engine, behavioral fingerprint compilation, uncertainty region extraction (decision
  tree over probe results).
- **V2-A**: FAISS latent-space indexing at probe time; novelty scoring at inference
  time (`faiss_distance` / `novelty_flag` on every prediction log).
- **V2-B**: KS/PSI drift detection (`app/monitoring/drift_detector.py`), alert engine
  (`app/monitoring/alert_engine.py`) producing `LATENT_NOVELTY` / `FEATURE_DRIFT`
  alerts, health/alerts endpoints, dataset health analysis, performance profiling,
  drift analysis, SHAP explainability (global + local).
- Full Next.js dashboard for all of the above (before this session's redesign): model
  registry, per-model dashboard with tabs, fingerprint viewer.
- Pytest suite covering ingestion, probing, fingerprinting, drift/alerting,
  explainability, model runtime, production readiness (89 tests passing at session
  start).

Per the project's own `docs/v2-phases.md` roadmap, **V2-C (Celery async tasks +
Prometheus + Grafana) had not been started** at session start. That roadmap doc is the
best source of the project's own intended next steps beyond what's captured here.

---

## 3. What was done in this session

### 3.1 Frontend visual redesign (went through several iterations)

The dashboard started as a generic dark-teal-glassmorphism SaaS look. Redesigned
through multiple rounds, ending on a **white-and-pink editorial theme** (final state):

- `frontend/tailwind.config.js` — color tokens are named `ink` / `paper` / `panel` /
  `line` / `mute` / `accent`, but **the names no longer describe their original
  dark-theme meaning** — see the comment block in that file. Short version: `ink` =
  white (page bg), `paper` = near-black (primary text), `panel` = pink (card bg),
  `line` = near-black (borders), `accent` = deep rose-pink (CTAs/active states). This
  was a deliberate value-swap so class names in JSX didn't need renaming everywhere —
  **read the comment in `tailwind.config.js` before changing colors again**, it's
  easy to get confused by the names.
- `frontend/src/app/globals.css` — `.panel`, `.label-mono`, `.stat-huge`,
  `.explainer`, `.grid-texture` / `.grid-texture-light` (dot-grid card texture),
  `.btn-notch` (chamfered-corner CTA buttons), `.section-label` (eyebrow dividers),
  `.full-bleed` (escapes the centered `<main>` container for full-width sections).
- Fonts: `Anton` (condensed, used for the nav wordmark, footer wordmark, and
  dashboard stat numbers), `Playfair Display` (serif, used for marketing headlines —
  hero, "Platform at a Glance", "Model Registry" title), `JetBrains Mono` (all
  uppercase micro-labels, IDs, code).
- **Landing page** (`frontend/src/app/page.tsx`) is now a proper marketing page: pink
  hero panel with a serif headline and a CSS/SVG "novelty radar" illustration
  (`frontend/src/components/CornerBrackets.tsx` is the reusable corner-bracket frame
  component used there and on the feature cards), a "Platform at a Glance" section
  with **live** registry stats (real `useModels()` data, not fabricated numbers), a
  motivation section, a 4-card features section (one card in the deep accent pink),
  and the ingestion pipeline diagram.
- **Model registry moved to `/registry`** (`frontend/src/app/registry/page.tsx`) —
  `/` is now the marketing landing page, not the registry. Nav/footer links and every
  "Back to Registry" link across the app point at `/registry`.
- **Model dashboard** (`frontend/src/app/models/[id]/page.tsx`): the "Architecture
  Graph" tab was removed entirely (dead code — `renderArchitectureGraph`,
  `selectedLayer` state, the tab entry — all deleted; the layer table on the
  Monitoring tab still shows architecture info and was untouched). The "Behavioral
  Fingerprint" link was upgraded from a small corner pill into a full-width
  accent-bordered feature banner between the title and the quick-stats row.
- All severity/alert badges (critical/warning/healthy chips, verdict badges) were
  retuned from dark-theme colors (`-400` text, `-900` borders — illegible on a light
  background) to light-theme-appropriate ones (`-600`/`-700` text, `-300` borders,
  `-50` background tints). All hardcoded recharts hex constants (`GRID_STROKE`,
  `AXIS_STROKE`, `TOOLTIP_STYLE`, `PAPER`/`MUTE`/`ROSE`/`AMBER`/`EMERALD`) in both
  `models/[id]/page.tsx` and `models/[id]/fingerprint/page.tsx` were updated to match.

**If asked to touch visual design again**: the reference aesthetic the user pointed at
was a pink/white/black editorial SaaS site (serif display headline, dot-grid textured
cards, corner-bracket frames around illustrations, chamfered-corner buttons). Check
`tailwind.config.js`'s comment block first so color changes land in the right token.

### 3.2 Backend: Celery (async drift processing)

Drift detection used to run **synchronously inline** inside `predict()` on every 50th
prediction, blocking that request. Now:

- `app/tasks/celery_app.py` — Celery app, Redis broker/backend. Runs
  `task_always_eager=True` whenever `TEST_DATABASE_URL` is set in the environment, so
  `.delay()` calls execute synchronously in-process during `pytest` — no broker
  needed for tests.
- `app/tasks/drift_task.py` — `run_drift_check(model_id)` task body: opens its own
  `SessionLocal()`, calls the same `detect_drift()` / `process_feature_drift()`
  functions as before (unchanged), closes the session.
- `app/services/prediction_service.py` — the inline drift block now just does
  `run_drift_check.delay(model_id)` instead of calling the monitoring functions
  directly. Same `% 50 == 0` trigger.
- `app/config.py` — added `redis_url`.
- `docker-compose.yml` — added `redis` (redis:7-alpine, healthcheck via
  `redis-cli ping`) and `celery-worker` (same image as `api`, runs
  `celery -A app.tasks.celery_app worker`) services.
- `requirements.txt` — added `celery`, `redis`.

**Explicitly not done**: Prometheus + Grafana. The user confirmed this is
intentionally skipped — the custom dashboard already covers that visualization need,
and standing up a second metrics stack for a single-operator self-hosted tool wasn't
judged worth the operational overhead. If this decision is ever revisited, a bare
`/metrics` endpoint is the cheap first step, not a full Grafana instance.

### 3.3 Backend: API-key authentication

There was **zero auth** anywhere before this session (`allow_origins=["*"]`, every
endpoint open). This was the blocker for "let people connect their own models to this
as a real API." Added a simple bearer-token API key — deliberately **not** a full
user/account system, since this is a self-hosted single-operator tool:

- `app/models/api_key.py` — `ApiKey` model (id, name, `key_hash` unique, `key_prefix`
  for display, `created_at`, `last_used_at`, `revoked_at`).
- `app/schemas/api_key.py`, `app/routers/api_keys.py` — `POST /api/v1/api-keys`
  (bootstrap rule: allowed with **no** auth only if zero non-revoked keys exist yet;
  otherwise requires a valid existing key), `GET /api/v1/api-keys` (list, masked),
  `DELETE /api/v1/api-keys/{id}` (revoke).
- `app/utils/auth.py` — key generation (`mmk_<32 hex>` format, SHA-256 hashed at
  rest, plaintext shown exactly once at creation), `require_api_key` FastAPI
  dependency.
- `alembic/versions/0011_add_api_keys_table.py` — **must be applied** on any existing
  deployment (`alembic upgrade head`).
- `app/main.py` — every router except `health` and `api_keys` now has
  `dependencies=[Depends(require_api_key)]` on its `include_router()` call. CORS
  tightened to `settings.cors_origins` (env-configurable, defaults to
  `http://localhost:3000`).
- `app/config.py` — added `cors_origins`, and `disable_auth` which defaults to `True`
  whenever `TEST_DATABASE_URL` is set in the environment. **This is the key testing
  decision to be aware of**: it lets all the pre-existing test files keep passing
  unchanged (they already set `TEST_DATABASE_URL` before importing the app) instead of
  needing every test's HTTP call updated with an `Authorization` header.
  `tests/test_api_keys.py` is the **only** test file that explicitly overrides
  `disable_auth` back to `False` to verify the actual 401/200 enforcement and the
  bootstrap rule.
- `app/middleware/__init__.py` — emptied out; it was a byte-for-byte duplicate of
  `app/middleware/logging.py`'s `RequestLoggingMiddleware` (dead code, `main.py`
  already imported from the other file).

**Frontend wiring:**
- `frontend/src/lib/api.ts` — reads a key from `localStorage`
  (`modelmesh_api_key`), attaches `Authorization: Bearer <key>` on every request.
- `frontend/src/app/registry/page.tsx` — `ApiKeyPanel` component: shows a bootstrap
  "Generate API Key" card if no key is stored, reveals the plaintext key once with a
  copy button, then shows a masked "API Key Active" + "Regenerate" control
  thereafter. `useModels()` (in `frontend/src/hooks/useModelHealth.ts`) got a
  `refetch` added so the panel can force an immediate model-list retry right after a
  key is created/regenerated instead of waiting up to 10s for the next poll.
- `frontend/src/app/models/[id]/page.tsx` — the `handleSimulateTraffic` direct
  `fetch()` calls now also attach the stored key.
- `demo/run_demo.py`, `demo/simulate_traffic.py` — bootstrap a key at script start
  and send it on every request.

**Bugs found and fixed during this work** (worth knowing about if similar symptoms
resurface):
1. Registry page showed a stale "Connection Failed / Invalid or revoked API key"
   message even after successfully generating a new key — because nothing told the
   already-failed `useModels()` poll to retry. Fixed by adding `refetch` to the hook
   and calling it from `ApiKeyPanel` right after key creation/regeneration.
2. The key-reveal-once panel didn't survive the registry's error→success remount
   (React remounts the whole tree when the connection error clears) — fixed by
   persisting the "pending reveal" in `sessionStorage` so a fresh component instance
   picks it back up.
3. Generate/Regenerate occasionally double-fired (observed as a spurious 401
   "Missing API key" appearing right after a successful key creation, or 3 requests
   logged for 1 click). Root cause wasn't fully isolated — `busy` state alone doesn't
   block a near-simultaneous second invocation since React state updates aren't
   synchronous. Fixed defensively with a `useRef` re-entrancy guard
   (`inFlightRef`) in `handleGenerate`/`handleRegenerate` that blocks re-entrant calls
   regardless of root cause. **This was verified fixed in this session's final test
   pass, but only with a handful of manual clicks — if it resurfaces, that ref guard
   is the place to look, and it'd be worth adding an automated test that fires the
   handler twice in the same tick.**

### 3.4 Test suite

97 tests passing (`TEST_DATABASE_URL=sqlite:///./test.db .venv/bin/pytest -q`) — the
original 89 plus 8 new ones in `tests/test_api_keys.py`.

---

## 4. What's explicitly NOT done / deferred

Confirmed out of scope with the user during this session:
- **Prometheus + Grafana** (V2-C's other half) — intentionally skipped, see §3.2.
- **Full user accounts / multi-tenancy** — API keys are a single shared bearer-token
  model, not per-user/per-account. Anyone with a valid key can see/manage all models.
- **Rate limiting, RBAC, CI/CD pipeline** — not discussed as explicit asks, not built.

## 5. Known gaps / good next steps for whoever picks this up

Roughly in priority order:

1. **Verify the full Docker Compose stack together.** This session tested the backend
   (via `.venv` + `uvicorn` directly against the `modelmesh-db` container) and
   frontend (via `npm run dev`) locally, and exercised Celery/Redis, but **never ran
   `docker-compose up --build` for the complete stack** (db + redis + api +
   celery-worker + frontend) at once. That's the highest-value next verification step
   — confirm the Dockerfile/compose networking actually works end-to-end, especially
   the celery-worker's connection to Redis and Postgres from inside its container.
2. **API key management UX is minimal.** There's no page listing all issued keys with
   names/creation dates for an admin to audit — only "your browser's current key"
   status. Every key is named `"dashboard"` regardless of who/what created it. If
   multiple people or scripts need distinct keys, the create-key flow needs a name
   input exposed in the UI (the backend schema already supports arbitrary names).
3. **No rate limiting anywhere**, including `/predict` — worth adding before this is
   exposed on a real network.
4. **README.md is stale.** It still describes the old dark-theme UI, the old
   single-container quickstart, and doesn't mention that Redis/Celery are now required
   for drift detection to actually run, or that an API key is required for every
   non-dashboard request. Update the Quickstart section and API endpoint list.
5. **Alert delivery has no push mechanism** — alerts sit in the DB, visible only by
   polling the UI/API. No Slack/email/webhook integration. Natural to add now that
   Celery exists (a task could deliver on alert creation).
6. **No `tests/conftest.py`** — each test file duplicates its own DB-fixture
   boilerplate (`TEST_DATABASE_URL` handling, `override_get_db`, etc.). Minor tech
   debt, not urgent, but flagged in case someone wants to consolidate it.
7. ~~**Two stray duplicate doc files**: `docs/version 2` and `docs/version2 phases`
   (no file extension) appear to be accidental duplicates of `docs/v2-spec.md` and
   `docs/v2-phases.md`. Safe to delete after confirming they're not referenced
   anywhere.~~ **Done**: All `docs/` files except `README.md` and `PROJECT_STATUS.md`
   have been deleted (`v1-phases.md`, `v1-prd.md`, `v2-phases.md`, `v2-spec.md`,
   `version 2`, `version2 phases`).
8. **Frontend responsiveness of the new theme** was checked at a couple of
   breakpoints (desktop, one narrow width) but not exhaustively across mobile sizes.
9. **ONNX ingestion path** exists in code but wasn't exercised/tested in this session
   — worth a smoke test if it's actually used, or consider trimming if it's dead
   weight (flagged as a possible-trim candidate earlier in this project's life, never
   acted on).
10. **Per-request CPU/memory instrumentation** (`resource.getrusage` in
    `prediction_service.predict()`) adds overhead to the hot path for a metric that's
    only ever viewed in aggregate on the Performance tab — candidate for sampling
    instead of measuring every single request, if `/predict` latency ever matters.

## 6. How to run everything

**Backend (local, without Docker):**
```bash
docker compose up -d db redis
DATABASE_URL="postgresql://modelmesh:modelmesh123@localhost:5433/modelmesh" \
  REDIS_URL="redis://localhost:6379/0" \
  .venv/bin/uvicorn app.main:app --reload --port 8000
```
Run a worker in another terminal to actually process drift checks:
```bash
DATABASE_URL="postgresql://modelmesh:modelmesh123@localhost:5433/modelmesh" \
  REDIS_URL="redis://localhost:6379/0" \
  .venv/bin/celery -A app.tasks.celery_app worker --loglevel=info
```

**Frontend:** `cd frontend && npm run dev` (proxies `/api/*` to `localhost:8000`).

**First run**: hit `/registry`, click "Generate API Key" (bootstrap works with zero
existing keys), save the key — it's stored in the browser and used for all
subsequent dashboard requests automatically.

**Tests:** `TEST_DATABASE_URL=sqlite:///./test.db .venv/bin/pytest -q`

**Full Docker stack** (not verified together this session — see gap #1 above):
```bash
docker compose up --build
```

---

## Uncommitted changes in this working tree

Nothing from this session has been committed. `git status` at time of writing:

**Modified:**
`app/config.py`, `app/database.py`, `app/main.py`, `app/middleware/__init__.py`,
`app/services/prediction_service.py`, `demo/run_demo.py`, `demo/simulate_traffic.py`,
`docker-compose.yml`, `frontend/src/app/globals.css`, `frontend/src/app/layout.tsx`,
`frontend/src/app/models/[id]/fingerprint/page.tsx`,
`frontend/src/app/models/[id]/page.tsx`, `frontend/src/app/page.tsx`,
`frontend/src/hooks/useModelHealth.ts`, `frontend/src/lib/api.ts`,
`frontend/tailwind.config.js`, `requirements.txt`

**New (untracked):**
`alembic/versions/0011_add_api_keys_table.py`, `app/models/api_key.py`,
`app/routers/api_keys.py`, `app/schemas/api_key.py`, `app/tasks/`,
`app/utils/auth.py`, `frontend/src/app/registry/`, `frontend/src/components/`,
`tests/test_api_keys.py`

Recommend committing in a few logical chunks (e.g. "Celery async drift processing",
"API key authentication", "White/pink landing + dashboard redesign") rather than one
giant commit, to keep the history reviewable.
