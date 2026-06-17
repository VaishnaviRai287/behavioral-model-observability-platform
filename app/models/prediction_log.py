import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, DateTime, JSON, ForeignKey, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PredictionLog(Base):
    """
    A record of one live prediction request.

    Written after every POST /models/{id}/predict call.
    Enables audit trails, drift detection against probe fingerprints,
    and debugging.
    """
    __tablename__ = "prediction_logs"

    __table_args__ = (
        Index("ix_prediction_logs_model_id_created_at", "model_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("models.id", ondelete="CASCADE"), nullable=False
    )


    # The raw input dict from the request body (before ordering)
    input_features: Mapped[dict] = mapped_column(JSON, nullable=False)

    # The ordered input list fed to the model (after validation + ordering)
    input_vector: Mapped[list] = mapped_column(JSON, nullable=False)

    # Model output
    predicted_class: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    raw_output: Mapped[list] = mapped_column(JSON, nullable=False)

    # How long the prediction took, in milliseconds
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)

    # V2-A Latent Space Fields
    faiss_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    novelty_flag: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
