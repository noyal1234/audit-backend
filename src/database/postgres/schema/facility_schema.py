from src.database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4


class FacilitySchema(Base):
    """Facility (Dealership) in hierarchy. Dealership login via user (user_id)."""

    __tablename__ = "facility"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    zone_id: Mapped[str] = mapped_column(String(36), ForeignKey("zone.id"), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("user.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    dealer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dealer_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dealer_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    dealer_designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    zone: Mapped["ZoneSchema"] = relationship("ZoneSchema", back_populates="facilities")
