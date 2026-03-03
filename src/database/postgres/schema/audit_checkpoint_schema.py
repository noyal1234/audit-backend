from src.database.base import Base
from sqlalchemy import Boolean, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class AuditCheckpointSchema(Base):
    """Snapshot of a checkpoint at audit creation. No AI fields; reviews are in audit_checkpoint_review."""

    __tablename__ = "audit_checkpoint"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    audit_sub_area_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audit_sub_area.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checkpoint_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    audit_sub_area: Mapped["AuditSubAreaSchema"] = relationship(
        "AuditSubAreaSchema", back_populates="checkpoints"
    )
    reviews: Mapped[list["AuditCheckpointReviewSchema"]] = relationship(
        "AuditCheckpointReviewSchema", back_populates="audit_checkpoint", cascade="all, delete-orphan"
    )
    media_items: Mapped[list["MediaEvidenceSchema"]] = relationship(
        "MediaEvidenceSchema",
        back_populates="audit_checkpoint",
        cascade="all, delete-orphan",
    )
