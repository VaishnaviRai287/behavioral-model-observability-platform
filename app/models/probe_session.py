import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProbeSession(Base):
    """
    Represents one probing run against a model.

    A probe session holds the aggregate statistics from N individual predictions.
    The individual predictions are stored in the probe_results table.
    """
    __tablename__ = "probe_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("models.id", ondelete="CASCADE"), nullable=False
    )
    n_probes: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
        # Values: "pending" | "running" | "done" | "failed"
    )

    # Summary statistics — populated after the run completes
    mean_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_std: Mapped[float | None] = mapped_column(Float, nullable=True)
    dominant_class: Mapped[int | None] = mapped_column(Integer, nullable=True)
    class_distribution: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # If status == "failed", the error message is stored here
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
