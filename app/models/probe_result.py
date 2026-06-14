import uuid

from sqlalchemy import String, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProbeResult(Base):
    """
    One individual prediction from a probe session.

    Each probe session generates N of these records.
    For 1000 probes, 1000 rows are written to this table.
    """
    __tablename__ = "probe_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("probe_sessions.id", ondelete="CASCADE"), nullable=False
    )

    # The synthetic input vector (e.g., [0.43, 0.91])
    input_vector: Mapped[list] = mapped_column(JSON, nullable=False)

    # The model's prediction for this input
    predicted_class: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Full probability distribution (e.g., [0.09, 0.91])
    raw_output: Mapped[list] = mapped_column(JSON, nullable=False)
