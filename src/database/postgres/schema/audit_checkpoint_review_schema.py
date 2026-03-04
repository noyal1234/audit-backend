from datetime import datetime

from src.database.base import Base
from sqlalchemy import Boolean, Float, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class AuditCheckpointReviewSchema(Base):
    """Append-only review per checkpoint (AI / MANUAL / SUPERVISOR). Effective = latest by created_at."""

    __tablename__ = "audit_checkpoint_review"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    audit_checkpoint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audit_checkpoint.id", ondelete="CASCADE"), nullable=False, index=True
    )
    review_type: Mapped[str] = mapped_column(String(30), nullable=False)
    compliant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    media_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("media_evidence.id", ondelete="SET NULL"),
        nullable=True,
    )

    audit_checkpoint: Mapped["AuditCheckpointSchema"] = relationship(
        "AuditCheckpointSchema", back_populates="reviews"
    )
    media: Mapped["MediaEvidenceSchema | None"] = relationship(
        "MediaEvidenceSchema",
        foreign_keys=[media_id],
        lazy="joined",
    )
