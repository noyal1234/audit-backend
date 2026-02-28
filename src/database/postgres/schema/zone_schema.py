from src.database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class ZoneSchema(Base):
    """Zone in hierarchy (Company level)."""

    __tablename__ = "zone"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("country.id"), nullable=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    facilities: Mapped[list["FacilitySchema"]] = relationship("FacilitySchema", back_populates="zone")
