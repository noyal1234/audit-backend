from src.database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class AuditAreaSchema(Base):
    """Snapshot of an area at audit creation."""

    __tablename__ = "audit_area"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    audit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audit.id", ondelete="CASCADE"), nullable=False, index=True
    )
    area_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    audit: Mapped["AuditSchema"] = relationship("AuditSchema", back_populates="audit_areas")
    sub_areas: Mapped[list["AuditSubAreaSchema"]] = relationship(
        "AuditSubAreaSchema", back_populates="audit_area", cascade="all, delete-orphan"
    )
