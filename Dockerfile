FROM python:3.10-slim

# Install system dependencies required for building python extension modules if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Expose port
EXPOSE 8000

# Set environment variable defaults
ENV UPLOAD_DIR=uploads
ENV DATABASE_URL=postgresql://modelmesh:modelmesh123@db:5432/modelmesh

# Create uploads directory
RUN mkdir -p uploads

# Start the application, applying database migrations on startup
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
