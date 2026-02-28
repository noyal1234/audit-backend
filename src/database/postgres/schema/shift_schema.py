from src.database.base import Base
from sqlalchemy import String, DateTime, Time, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4


class ShiftConfigSchema(Base):
    """Shift time configuration (e.g. MORNING 08:00-14:00)."""

    __tablename__ = "shift_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
