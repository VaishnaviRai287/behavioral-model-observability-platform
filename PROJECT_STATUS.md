# ModelMesh — Project Status & Handoff

_Last updated: 2026-07-26. Written for any agent or human picking this project up next._

> **Commit status**: the Celery/API-key/redesign work described in §3 below is already
> committed (`78f8a8b Adding celery and redis and UI`). The **production-readiness and
> AI-trace cleanup pass** described in §4 is **not committed yet** — it's sitting
> uncommitted in the working tree. See [Uncommitted changes](#uncommitted-changes-in-this-working-tree)
> at the bottom for the exact file list before doing anything else.

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

## 2. What's done — pre-existing (before any of this work)

- **V1**: multi-framework ingestion (sklearn/PyTorch/TF-Keras/ONNX), framework
  auto-detection, architecture extraction, deterministic model signature, LHS probing
  engine, behavioral fingerprint compilation, uncertainty region extraction (decision
  tree over probe results).
- **V2-A**: FAISS latent-space indexing at probe time; novelty scoring at inference
  time (`faiss_distance` / `novelty_flag` on every prediction log).
- **V2-B**: KS/PSI drift detection, alert engine producing `LATENT_NOVELTY` /
  `FEATURE_DRIFT` alerts, health/alerts endpoints, dataset health analysis,
  performance profiling, drift analysis, SHAP explainability (global + local).
- A working Next.js dashboard for all of the above, and a pytest suite covering
  ingestion, probing, fingerprinting, drift/alerting, explainability, and model
  runtime (89 tests at the time).

Per the project's own `docs/v1-*.md` / `docs/v2-*.md` planning docs (kept locally,
gitignored — see §5), V2-C (Celery + Prometheus/Grafana) had not been started.

---

## 3. What was done — Celery, API-key auth, and the UI redesign (committed: `78f8a8b`)

### 3.1 Frontend visual redesign
Went through several iterations, ending on a white-and-pink editorial theme (pink
panels, black serif headlines, corner-bracket illustration frames, chamfered-corner
buttons) before the user did their own further pass on top of it. Key structural
points still true today:
- `frontend/tailwind.config.js` — color tokens (`ink`/`paper`/`panel`/`line`/`mute`/`accent`)
  are named after their *original* dark-theme roles but hold light-theme values now —
  read the comment block in that file before changing colors, the names are easy to
  misread.
- Landing page (`frontend/src/app/page.tsx`) is a marketing page; the model registry
  lives at `/registry` (`frontend/src/app/registry/page.tsx`), not `/`.
- Model dashboard (`frontend/src/app/models/[id]/page.tsx`): "Architecture Graph" tab
  was removed; "Behavioral Fingerprint" is a full-width feature banner, not a small
  corner pill.

### 3.2 Backend: Celery (async drift processing)
Drift detection used to run synchronously inline inside `predict()` on every 50th
prediction, blocking that request.
- `app/tasks/celery_app.py` / `app/tasks/drift_task.py` — `run_drift_check(model_id)`
  task, dispatched via `.delay()` from `app/services/prediction_service.py` instead of
  calling `detect_drift()`/`process_feature_drift()` inline.
- Runs `task_always_eager=True` whenever `TEST_DATABASE_URL` is set, so tests exercise
  the same code path synchronously with no broker required.
- `docker-compose.yml` gained `redis` and `celery-worker` services.
- **Explicitly not done**: Prometheus + Grafana — confirmed with the user as
  intentionally skipped (redundant with the existing custom dashboard).

### 3.3 Backend: API-key authentication
There was zero auth before this (`allow_origins=["*"]`, every endpoint open).
- `app/models/api_key.py`, `app/schemas/api_key.py`, `app/routers/api_keys.py`,
  `app/utils/auth.py` — a single-tenant bearer-token API key (`mmk_<32 hex>`, SHA-256
  hashed at rest, shown once at creation). Bootstrap rule: `POST /api/v1/api-keys`
  allows unauthenticated creation only while zero non-revoked keys exist.
- `app/main.py` — every router except `health` and `api_keys` requires
  `Depends(require_api_key)`.
- `app/config.py` — `disable_auth` defaults to `True` whenever `TEST_DATABASE_URL` is
  set, so the pre-existing test suite needed no changes; `tests/test_api_keys.py` is
  the one file that flips it back to exercise the real gate.
- Frontend: `lib/api.ts` attaches the stored key as `Authorization: Bearer <key>`;
  `registry/page.tsx`'s `ApiKeyPanel` handles bootstrap/reveal-once/regenerate.
- **Bugs found and fixed along the way**: a stale "Connection Failed" message that
  didn't clear after generating a valid key (fixed by adding `refetch` to `useModels()`
  and calling it from `ApiKeyPanel`); a possible double-fire on
  Generate/Regenerate (fixed with a `useRef` re-entrancy guard, since `busy` state
  alone doesn't block a near-simultaneous second call).

---

## 4. What was done — production-readiness & AI-trace audit (this session, uncommitted)

The user cleaned up the UI further themselves, then asked for a full audit: make the
project production-ready and remove signs of AI-assisted generation. Full test suite
(97 tests) verified passing after every step below.

### 4.1 AI-trace cleanup
- Removed the `# ── Section ──────` box-drawing comment style throughout the backend
  (10 `app/` files, 10 `tests/` files) — a strong AI-generated-code tell. Simplified
  numbered docstrings ("Steps: 1. 2. 3." / "Args:/Returns:" restating the signature)
  to single-line docstrings that say what the function does, not how.
- Fixed a real bug surfaced during this pass: `tests/test_model_runtime.py`'s
  TensorFlow wrapper test caught `except (ImportError, Exception): pass` — i.e. it
  silently passed regardless of outcome, giving zero real coverage. Replaced with
  `pytest.importorskip("tensorflow")` so it either genuinely runs or visibly skips.
- Deduplicated a 3x-repeated empty-result dict in
  `app/monitoring/drift_detector.py` into `_empty_drift_analysis()`, and factored
  duplicated severity-threshold logic into `_severity()`.
- Cleaned the same box-comment style out of `.gitignore`; removed the accidentally
  committed `frontend/tsconfig.tsbuildinfo` build artifact and added it to
  `.gitignore`.

### 4.2 Backend production-readiness
- **`requirements.txt` was completely unpinned** — now pinned to the exact versions
  verified installed and passing (`pip freeze` against the working `.venv`). Added
  `scipy` explicitly (was an unpinned transitive dependency of code that imports it
  directly). Split test-only deps (`pytest`, `httpx`) into `requirements-dev.txt`.
  **Known gap**: TensorFlow has no wheel for Python 3.14 — it's pinned to a
  Python-3.10-compatible range (`>=2.15,<2.17`) but was **not actually verified
  installable in this environment**; test it explicitly under the Docker image
  (`python:3.10-slim`) before relying on TF ingestion in production.
- **Hardcoded default DB credentials** (`modelmesh`/`modelmesh123`) existed in three
  places (`app/config.py`, `Dockerfile`, `docker-compose.yml`). `docker-compose.yml`
  now reads `POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD`/`CORS_ORIGINS` from a
  `.env` file (see new `.env.example`), with the old values kept only as fallback
  defaults so nothing breaks for people who don't set one up.
- **Fixed a real crash-on-startup bug**: `cors_origins` was typed `list[str]` in
  pydantic-settings, which tries to JSON-decode list-typed env vars *before* any
  validator runs — setting `CORS_ORIGINS=http://localhost:3000` (a plain string, the
  natural way to set it via docker-compose/shell) crashed the app at import time.
  Fixed by keeping it a plain `str` field with a `.cors_origins_list` property that
  splits on commas — this is the standard workaround for this exact pydantic-settings
  gotcha.
- **Both Dockerfiles now run as non-root** (`modelmesh` uid 1000 for the backend,
  the built-in `node` user for the frontend), and both gained a `.dockerignore`.
  Frontend Dockerfile switched `npm install`/`npm install --omit=dev` to
  `npm ci`/`npm ci --omit=dev` for reproducible builds.
- Cleaned up dead/redundant blank lines and comments in `app/main.py`.

### 4.3 Frontend production-readiness
- **Fixed a real deployment bug**: the "API Docs" link was hardcoded to
  `http://localhost:8000/docs` in both `layout.tsx` and `page.tsx` — would 404 (or
  point at the wrong place) on any real deployment. Now reads
  `process.env.NEXT_PUBLIC_API_URL`.
- **Fixed a subtler, related bug**: `docker-compose.yml` set
  `NEXT_PUBLIC_API_URL=http://api:8000` (the Docker-internal hostname) — but
  `NEXT_PUBLIC_*` vars get inlined into the client bundle at **build time**, not read
  from the container at runtime, and `http://api:8000` is not reachable from a
  browser running outside the Docker network at all. Fixed by threading
  `NEXT_PUBLIC_API_URL` through as a Docker build ARG (see `frontend/Dockerfile` and
  the `frontend.build.args` block in `docker-compose.yml`), defaulting to
  `http://localhost:8000` (the published host port — correct for local
  docker-compose use; override via `.env` for a real deployment).
- Added `frontend/.eslintrc.json` (`next/core-web-vitals`) and installed
  `eslint`/`eslint-config-next` as dev dependencies — `npm run lint` previously
  couldn't run at all (ESLint wasn't installed). Lint is now clean except one
  pre-existing warning (see gap below).
- Added `poweredByHeader: false` to `next.config.js` (drops the `X-Powered-By:
  Next.js` response header).
- **Known gap, not fixed — flagging prominently**: `npm audit` reports **16 high
  severity vulnerabilities in `next@14.2.35`** (the latest available 14.x release),
  including SSRF via rewrites (this app uses rewrites), cache poisoning, and DoS via
  Server Components. The only fix path `npm audit` offers is `next@16.2.12`, a
  breaking two-major-version jump — **deliberately not done here** without explicit
  sign-off, since it needs real regression testing (App Router / rewrites / React
  version behavior can all shift across two majors). This is the single most
  important open item in this document if "production ready" includes the actual
  web framework's known CVEs.
- **Known gaps, not fixed**: no `public/` folder or favicon at all (cosmetic, but a
  common "unfinished project" tell); custom fonts are loaded via a `<link>` tag in
  `layout.tsx` rather than `next/font/google`, which ESLint flags as discouraged
  (performance/layout-shift best practice, not a bug — left alone to avoid an
  unreviewed visual regression risk this session didn't have time to verify in-browser).

### 4.4 Things noticed but deliberately left alone
- **In-process caches won't survive multi-worker scaling**: `app/ml/model_cache.py`'s
  `_cache` dict and `app/services/fingerprint_service.py`'s
  `_uncertainty_regions_cache` are per-process. If anyone adds `--workers N` to the
  uvicorn command for scaling, these caches silently stop being shared across
  workers (not wrong, just surprising) — moving them to Redis would be the fix, but
  wasn't in scope here.
- **Internal planning docs aren't tracked in git** (`docs/v1-*.md`, `docs/v2-*.md`
  exist locally but `.gitignore` excludes `./docs` entirely, and `git ls-files docs/`
  confirms nothing in there was ever committed). Left as-is rather than force-adding
  them, since that's a call about what ships in the public repo history, not a bug.
- Several legitimate `except Exception:` fallbacks in `app/utils/architecture_extractor.py`,
  `app/ml/sklearn_wrapper.py`, `app/ml/tensorflow_wrapper.py`, and
  `app/monitoring/novelty_scorer.py` were reviewed and left alone — they're
  intentional best-effort fallbacks (e.g. novelty scoring degrading to "not novel"
  rather than failing the whole prediction request), not bugs.

---

## 5. What's explicitly NOT done / deferred

- **Prometheus + Grafana** — intentionally skipped (§3.2).
- **Full user accounts / multi-tenancy** — API keys are a single shared bearer-token
  model, not per-user/per-account.
- **Rate limiting, RBAC, CI/CD pipeline** — not built.
- **The Next.js 14→16 security upgrade** — see §4.3, needs explicit sign-off.

## 6. Good next steps, in priority order

1. **Decide on the Next.js CVE situation** (§4.3) — this is the biggest open item.
2. **Verify the full Docker Compose stack together** — this work was tested via
   `.venv`/`uvicorn` directly and `npm run dev` locally, never via a complete
   `docker compose up --build` of all five services at once. Confirm the
   celery-worker can actually reach Redis/Postgres from inside its container, and
   that the new `frontend.build.args` wiring produces a working "API Docs" link.
3. **API key management UX is minimal** — no page listing all issued keys with
   names; every key is named `"dashboard"` regardless of who/what created it.
4. **No rate limiting anywhere**, including `/predict`.
5. **README.md is stale** — still describes the old UI and doesn't mention that
   Redis/Celery are required for drift detection, or that an API key is required
   for every non-dashboard request.
6. **Alert delivery has no push mechanism** — alerts sit in the DB, polled only.
7. **No `tests/conftest.py`** — each test file duplicates its own DB-fixture setup.
8. **TensorFlow ingestion is unverified** in this exact environment (§4.2) — test it
   for real under the Docker image before relying on it.

## 7. How to run everything

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
(dev-only deps: `pip install -r requirements-dev.txt`)

**Full Docker stack** (not verified together this session — see gap #2 above):
```bash
docker compose up --build
```

---

## Uncommitted changes in this working tree

Everything in §3 is already committed (`78f8a8b`). The §4 audit/hardening pass is
**not** — `git status` at time of writing:

**Modified:** `.gitignore`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`,
`app/config.py`, `app/main.py`, `app/ml/base_wrapper.py`, `app/ml/loader.py`,
`app/ml/model_cache.py`, `app/ml/pytorch_wrapper.py`,
`app/monitoring/drift_detector.py`, `app/monitoring/faiss_indexer.py`,
`app/monitoring/novelty_scorer.py`, `app/probing/engine.py`, `app/probing/sampler.py`,
`app/routers/models.py`, `app/services/*.py` (dataset_health, drift, fingerprint,
performance, prediction, probe, shap), `app/utils/architecture_extractor.py`,
`app/fingerprinting/comparator.py`, `app/fingerprinting/metrics.py`,
`frontend/Dockerfile`, `frontend/next.config.js`, `frontend/package.json`,
`frontend/package-lock.json`, `frontend/src/app/layout.tsx`,
`frontend/src/app/page.tsx`, 10 files under `tests/`

**New:** `.dockerignore`, `.env.example`, `frontend/.dockerignore`,
`frontend/.eslintrc.json`, `requirements-dev.txt`

**Deleted (untracked from git, file itself untouched):** `frontend/tsconfig.tsbuildinfo`

Recommend committing this as its own commit (e.g. "Production-readiness hardening +
AI-trace cleanup") separate from any further UI work, so the security-relevant fixes
(CORS crash, hardcoded creds, NEXT_PUBLIC_API_URL bug) are easy to find in history.
