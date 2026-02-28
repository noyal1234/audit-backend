from src.database.base import Base
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4


class CountrySchema(Base):
    """Country (future-ready)."""

    __tablename__ = "country"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
