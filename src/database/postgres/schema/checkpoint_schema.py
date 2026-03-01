from src.database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class CheckpointSchema(Base):
    """Facility-scoped checkpoint (area inside a dealership)."""

    __tablename__ = "checkpoint"
    __table_args__ = (
        UniqueConstraint("facility_id", "name", name="uq_checkpoint_facility_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facility.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category_links: Mapped[list["CheckpointCategorySchema"]] = relationship(
        "CheckpointCategorySchema", back_populates="checkpoint", cascade="all, delete-orphan"
    )
