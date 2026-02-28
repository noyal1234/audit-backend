from src.database.base import Base
from sqlalchemy import String, DateTime, Date, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4


class AuditSchema(Base):
    """Audit run per facility per shift."""

    __tablename__ = "audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facility.id"), nullable=False, index=True)
    shift_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    shift_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    status_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), nullable=False, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    finalized_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditCheckpointResultSchema(Base):
    """Per-checkpoint result within an audit."""

    __tablename__ = "audit_checkpoint_result"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    audit_id: Mapped[str] = mapped_column(String(36), ForeignKey("audit.id"), nullable=False, index=True)
    checkpoint_id: Mapped[str] = mapped_column(String(36), ForeignKey("checkpoint.id"), nullable=False, index=True)
    compliant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ai_status_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
