from src.database.base import Base
from sqlalchemy import String, DateTime, Date, ForeignKey, Boolean, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4

from src.database.postgres.schema.media_schema import MediaEvidenceSchema


class AuditSchema(Base):
    """Audit run per facility per shift."""

    __tablename__ = "audit"
    __table_args__ = (
        UniqueConstraint("facility_id", "shift_type", "shift_date", name="uq_audit_facility_shift"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facility.id"), nullable=False, index=True)
    shift_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    shift_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    status_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), nullable=False, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    finalized_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    audit_checkpoints: Mapped[list["AuditCheckpointSchema"]] = relationship(
        "AuditCheckpointSchema", back_populates="audit", cascade="all, delete-orphan"
    )


class AuditCheckpointSchema(Base):
    """Snapshot of a checkpoint at audit creation time."""

    __tablename__ = "audit_checkpoint"
    __table_args__ = (
        UniqueConstraint("audit_id", "checkpoint_id", name="uq_audit_checkpoint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    audit_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit.id", ondelete="CASCADE"), nullable=False, index=True)
    checkpoint_id: Mapped[str] = mapped_column(String(36), ForeignKey("checkpoint.id"), nullable=False)
    checkpoint_name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False, server_default="")
    status_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="PENDING")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    audit: Mapped["AuditSchema"] = relationship("AuditSchema", back_populates="audit_checkpoints")
    categories: Mapped[list["AuditCheckpointCategorySchema"]] = relationship(
        "AuditCheckpointCategorySchema", back_populates="audit_checkpoint", cascade="all, delete-orphan"
    )


class AuditCheckpointCategorySchema(Base):
    """Tracks category-level completion within an audit checkpoint."""

    __tablename__ = "audit_checkpoint_category"
    __table_args__ = (
        UniqueConstraint("audit_checkpoint_id", "category_id", name="uq_audit_checkpoint_category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    audit_checkpoint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audit_checkpoint.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("category.id"), nullable=False)
    category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    completed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("user.id"), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Category-level AI snapshot (latest media result; no media lookup needed for UI)
    ai_latest_media_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("media_evidence.id", ondelete="SET NULL"),
        nullable=True,
    )
    ai_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_compliant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    audit_checkpoint: Mapped["AuditCheckpointSchema"] = relationship(
        "AuditCheckpointSchema", back_populates="categories"
    )
    media_items: Mapped[list["MediaEvidenceSchema"]] = relationship(
        "MediaEvidenceSchema",
        back_populates="audit_checkpoint_category",
        cascade="all, delete-orphan",
        foreign_keys=[MediaEvidenceSchema.audit_checkpoint_category_id],
    )
    latest_media: Mapped["MediaEvidenceSchema | None"] = relationship(
        "MediaEvidenceSchema",
        foreign_keys=[ai_latest_media_id],
    )
