from datetime import datetime, timezone
import uuid
from sqlalchemy import String, JSON, DateTime, ForeignKey, Integer, Float, Boolean, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class InferenceLog(Base):
    __tablename__ = "inference_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("registered_models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Stores inputs features dictionary
    features: Mapped[dict] = mapped_column(JSON, nullable=False)
    prediction: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Store latent activation vector (optional, nullable)
    latent_embedding: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    model = relationship("RegisteredModel")

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("registered_models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. FEATURE_DRIFT, LATENT_NOVELTY
    severity: Mapped[str] = mapped_column(String(20), nullable=False)   # info, warning, critical
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    model = relationship("RegisteredModel")
