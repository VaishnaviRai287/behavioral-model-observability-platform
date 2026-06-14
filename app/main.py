import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.logging import RequestLoggingMiddleware
from app.routers import models, probes, fingerprints, predictions, health

# Configure logging
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
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the routers
app.include_router(models.router, prefix="/api/v1")
app.include_router(probes.router, prefix="/api/v1")
app.include_router(fingerprints.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(health.router)  # No prefix for health endpoints


@app.get("/health")
def health_check():
    """Health check endpoint for Docker and load balancers."""
    return {"status": "healthy", "service": "modelmesh-api"}
