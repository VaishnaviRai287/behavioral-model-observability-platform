import os

from celery import Celery

from app.config import settings

celery_app = Celery(
    "modelmesh",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Under pytest every test file sets TEST_DATABASE_URL before importing the app.
# Reuse that same signal so `.delay()` runs synchronously in-process during tests
# instead of requiring a running broker/worker.
if os.getenv("TEST_DATABASE_URL"):
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

import app.tasks.drift_task  # noqa: E402,F401 — registers @celery_app.task in worker processes
