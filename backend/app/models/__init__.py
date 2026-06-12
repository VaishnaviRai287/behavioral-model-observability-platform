from app.core.database import Base
from app.models.model_registry import RegisteredModel

# Exporting models for Alembic autogenerate tracking
__all__ = ["Base", "RegisteredModel"]