from fastapi import APIRouter
from app.api.v1 import models
from app.api.v1 import observability

api_router = APIRouter()
api_router.include_router(models.router, prefix="/models", tags=["Models"])
api_router.include_router(observability.router, prefix="/observability", tags=["Observability"])