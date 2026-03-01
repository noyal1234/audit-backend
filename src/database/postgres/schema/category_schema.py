from src.database.base import Base
from sqlalchemy import String, DateTime, Text, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class CategorySchema(Base):
    """Facility-scoped audit category."""

    __tablename__ = "category"
    __table_args__ = (
        UniqueConstraint("facility_id", "name", name="uq_category_facility_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    facility_id: Mapped[str] = mapped_column(String(36), ForeignKey("facility.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    checkpoint_links: Mapped[list["CheckpointCategorySchema"]] = relationship(
        "CheckpointCategorySchema", back_populates="category", cascade="all, delete-orphan"
    )
