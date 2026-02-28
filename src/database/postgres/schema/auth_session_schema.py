from src.database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4


class AuthSessionSchema(Base):
    """Auth session for JWT refresh and logout."""

    __tablename__ = "auth_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user.id"), nullable=False, index=True)
    token_jti: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
