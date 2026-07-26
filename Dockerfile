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

ENV UPLOAD_DIR=uploads
RUN mkdir -p uploads

# Run as a non-root user. DATABASE_URL/REDIS_URL are provided by the
# environment (docker-compose.yml, or your own orchestration) — see
# app/config.py for local-dev fallback defaults.
RUN useradd --create-home --uid 1000 modelmesh && chown -R modelmesh:modelmesh /app
USER modelmesh

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
