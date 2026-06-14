import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Fingerprint(Base):
    """
    A behavioral fingerprint computed from one probe session.

    Represents the behavioral signature of a model at a specific point in time.
    Compare two fingerprints to detect drift.
    """
    __tablename__ = "fingerprints"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("probe_sessions.id", ondelete="CASCADE"), nullable=False
    )
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("models.id", ondelete="CASCADE"), nullable=False
    )

    # Behavioral metrics
    confidence_histogram: Mapped[list] = mapped_column(
        JSON, nullable=False
        # 10-element list of floats, normalized (sums to 1.0)
        # bins: [0.0-0.1, 0.1-0.2, ..., 0.9-1.0]
    )
    entropy: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty_rate: Mapped[float] = mapped_column(Float, nullable=False)
    class_bias: Mapped[float] = mapped_column(Float, nullable=False)

    # Copied from probe session for convenience
    mean_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_std: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
