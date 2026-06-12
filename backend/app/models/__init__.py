from app.core.database import Base
from app.models.model_registry import RegisteredModel
from app.models.fingerprint import BehavioralFingerprint
from app.models.observability import InferenceLog, Alert

# Exporting models for Alembic autogenerate tracking
__all__ = ["Base", "RegisteredModel", "BehavioralFingerprint", "InferenceLog", "Alert"]