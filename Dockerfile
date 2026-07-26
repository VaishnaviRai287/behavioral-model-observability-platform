FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

ENV UPLOAD_DIR=uploads
RUN mkdir -p uploads

# DATABASE_URL/REDIS_URL are provided by the environment (docker-compose.yml,
# or your own orchestration) — see app/config.py for local-dev fallback
# defaults.
#
# Runs as root rather than a dedicated user: on platforms like Railway,
# UPLOAD_DIR is a persistent volume mounted fresh at container start (owned
# by root, not whatever uid was baked into the image at build time), so a
# non-root process can't write to it. The entrypoint's `mkdir -p` handles a
# volume that doesn't exist yet on first boot.
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
