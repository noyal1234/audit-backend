from src.database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class CheckpointSchema(Base):
    """Checkpoint under a sub_area (leaf of facility hierarchy)."""

    __tablename__ = "checkpoint"
    __table_args__ = (UniqueConstraint("sub_area_id", "name", name="uq_checkpoint_sub_area_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    sub_area_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sub_area.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_image_path: Mapped[str] = mapped_column(String(512), nullable=False, server_default="")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sub_area: Mapped["SubAreaSchema"] = relationship(
        "SubAreaSchema", back_populates="checkpoints"
    )
