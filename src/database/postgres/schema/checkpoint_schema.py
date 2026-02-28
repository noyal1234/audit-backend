from src.database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4


class CheckpointSchema(Base):
    """Checkpoint (facility-specific)."""

    __tablename__ = "checkpoint"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    subcategory_id: Mapped[str] = mapped_column(String(36), ForeignKey("subcategory.id"), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facility.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
