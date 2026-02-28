from src.database.base import Base
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class CheckpointCategorySchema(Base):
    """Many-to-many join: checkpoint <-> category."""

    __tablename__ = "checkpoint_category"
    __table_args__ = (
        UniqueConstraint("checkpoint_id", "category_id", name="uq_checkpoint_category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    checkpoint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("checkpoint.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("category.id", ondelete="CASCADE"), nullable=False, index=True
    )

    checkpoint: Mapped["CheckpointSchema"] = relationship("CheckpointSchema", back_populates="category_links")
    category: Mapped["CategorySchema"] = relationship("CategorySchema", back_populates="checkpoint_links")
