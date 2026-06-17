import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FAISSIndex(Base):
    """
    Holds metadata and baseline similarity statistics for a model's FAISS index.
    The actual binary index file is stored under uploads/.
    """
    __tablename__ = "faiss_indexes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("models.id", ondelete="CASCADE"), nullable=False
    )
    index_file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    vector_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_count: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_mean_distance: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_std_distance: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
