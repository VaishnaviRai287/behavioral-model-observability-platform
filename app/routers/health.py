from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.model_cache import cache_size

router = APIRouter(tags=["Health"])


@router.get("/health/live")
def health_live():
    """
    Liveness probe.

    Returns 200 if the process is running. Used by load balancers and
    container orchestrators (Kubernetes, Docker) to detect crashed processes.
    No DB check — if the process is alive, this always returns 200.
    """
    return {"status": "alive"}


@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    """
    Readiness probe.

    Returns 200 if the server can handle traffic (DB reachable).
    Returns 503 if the DB is unreachable.

    Load balancers check this before routing traffic. If it returns 503,
    the instance is removed from the pool until it recovers.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "db": "unhealthy",
                "error": str(e),
            },
        )

    return {
        "status": "ready",
        "db": db_status,
        "model_cache_size": cache_size(),
    }
