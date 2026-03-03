from datetime import datetime

from src.database.base import Base
from sqlalchemy import Boolean, Float, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class MediaEvidenceSchema(Base):
    """Stored image/evidence for an audit checkpoint (with AI analysis). Links to audit_checkpoint."""

    __tablename__ = "media_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    audit_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit.id"), nullable=False, index=True)
    audit_checkpoint_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("audit_checkpoint.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ai_status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="PENDING")
    ai_compliant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    audit_checkpoint: Mapped["AuditCheckpointSchema | None"] = relationship(
        "AuditCheckpointSchema", back_populates="media_items"
    )
