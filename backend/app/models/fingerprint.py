from datetime import datetime, timezone
import uuid
from sqlalchemy import String, JSON, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class BehavioralFingerprint(Base):
    __tablename__ = "behavioral_fingerprints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("registered_models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    num_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    
    # Store schema configurations and metric outputs in JSONB
    class_distribution: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence_distribution: Mapped[dict] = mapped_column(JSON, nullable=False)
    high_uncertainty_regions: Mapped[dict] = mapped_column(JSON, nullable=False)
    boundary_samples: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    
    model = relationship("RegisteredModel", backref="fingerprints")
