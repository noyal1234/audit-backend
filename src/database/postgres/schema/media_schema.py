from src.database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4


class MediaEvidenceSchema(Base):
    """Stored image/evidence for audit checkpoints."""

    __tablename__ = "media_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    audit_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit.id"), nullable=False, index=True)
    checkpoint_id: Mapped[str] = mapped_column(String(36), ForeignKey("checkpoint.id"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
