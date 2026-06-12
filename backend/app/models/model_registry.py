from datetime import datetime, timezone
import uuid
from sqlalchemy import String, JSON, DateTime, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class RegisteredModel(Base):
    __tablename__ = "registered_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    framework: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    
    # Store schema configurations in PostgreSQL JSONB
    input_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), default="registered", nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )