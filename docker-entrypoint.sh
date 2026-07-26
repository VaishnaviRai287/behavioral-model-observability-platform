#!/bin/sh
set -e

# UPLOAD_DIR may be a freshly-mounted persistent volume (e.g. Railway) that
# doesn't exist yet on first boot, or is owned by a different user than the
# one baked into the image at build time — ensure it's there before anything
# tries to write into it.
mkdir -p "$UPLOAD_DIR"

# No args (the `api` service): run migrations then start the API server.
# Args given (the `celery-worker` service's `command:` override): run that
# instead, so this same entrypoint works for both services in docker-compose.
if [ "$#" -eq 0 ]; then
  alembic upgrade head
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
  exec "$@"
fi
