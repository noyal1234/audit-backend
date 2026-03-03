from src.database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class SubAreaSchema(Base):
    """Sub-area under an area (second level)."""

    __tablename__ = "sub_area"
    __table_args__ = (UniqueConstraint("area_id", "name", name="uq_sub_area_area_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    area_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("area.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    area: Mapped["AreaSchema"] = relationship("AreaSchema", back_populates="sub_areas")
    checkpoints: Mapped[list["CheckpointSchema"]] = relationship(
        "CheckpointSchema", back_populates="sub_area", cascade="all, delete-orphan"
    )
