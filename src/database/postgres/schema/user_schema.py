from src.database.base import Base
from sqlalchemy import Boolean, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4


class UserSchema(Base):
    """Central identity for all login-capable roles. STELLANTIS_ADMIN country-scoped; DEALERSHIP/EMPLOYEE facility-scoped."""

    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_type: Mapped[str] = mapped_column(String(50), nullable=False)
    facility_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("facility.id"), nullable=True, index=True)
    country_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("country.id"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=func.true())
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
