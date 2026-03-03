from src.database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class AuditSubAreaSchema(Base):
    """Snapshot of a sub_area at audit creation."""

    __tablename__ = "audit_sub_area"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    audit_area_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("audit_area.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sub_area_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    audit_area: Mapped["AuditAreaSchema"] = relationship("AuditAreaSchema", back_populates="sub_areas")
    checkpoints: Mapped[list["AuditCheckpointSchema"]] = relationship(
        "AuditCheckpointSchema", back_populates="audit_sub_area", cascade="all, delete-orphan"
    )
