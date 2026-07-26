import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.logging import RequestLoggingMiddleware
from app.routers import models, probes, fingerprints, predictions, health, alerts, dataset_health, performance, drift_analysis, explainability, api_keys
from app.utils.auth import require_api_key

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(
    title="ModelMesh",
    description="Behavioral Model Observability Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS: Allow frontend (Next.js) to call this API from a different port
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the routers. Everything except /health and /api-keys (which gates itself,
# to allow first-run bootstrap) requires a valid API key.
_auth = [Depends(require_api_key)]
app.include_router(models.router, prefix="/api/v1", dependencies=_auth)
app.include_router(probes.router, prefix="/api/v1", dependencies=_auth)
app.include_router(fingerprints.router, prefix="/api/v1", dependencies=_auth)
app.include_router(predictions.router, prefix="/api/v1", dependencies=_auth)
app.include_router(alerts.router, prefix="/api/v1", dependencies=_auth)
app.include_router(dataset_health.router, prefix="/api/v1", dependencies=_auth)
app.include_router(performance.router, prefix="/api/v1", dependencies=_auth)
app.include_router(drift_analysis.router, prefix="/api/v1", dependencies=_auth)
app.include_router(explainability.router, prefix="/api/v1", dependencies=_auth)
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(health.router)


@app.get("/health")
def health_check():
    """Health check endpoint for Docker and load balancers."""
    return {"status": "healthy", "service": "modelmesh-api"}
