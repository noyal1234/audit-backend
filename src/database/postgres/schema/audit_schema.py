from src.database.base import Base
from sqlalchemy import String, DateTime, Date, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


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

    audit_areas: Mapped[list["AuditAreaSchema"]] = relationship(
        "AuditAreaSchema", back_populates="audit", cascade="all, delete-orphan"
    )
