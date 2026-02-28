from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.auth_session_schema import AuthSessionSchema
from src.database.postgres.schema.user_schema import UserSchema


class AuthRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_session(
        self,
        user_id: str,
        token_jti: str | None,
        refresh_token: str | None,
        expires_at: datetime,
    ) -> AuthSessionSchema:
        async with self._session_factory() as session:
            row = AuthSessionSchema(
                id=str(uuid4()),
                user_id=user_id,
                token_jti=token_jti,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def get_user_by_email(self, email: str) -> UserSchema | None:
        async with self._session_factory() as session:
            result = await session.execute(select(UserSchema).where(UserSchema.email == email))
            return result.scalar_one_or_none()

    async def invalidate_sessions_by_user(self, user_id: str) -> None:
        async with self._session_factory() as session:
            result = await session.execute(select(AuthSessionSchema).where(AuthSessionSchema.user_id == user_id))
            for row in result.scalars().all():
                await session.delete(row)
            await session.commit()

    async def find_session_by_refresh_token(self, refresh_token: str) -> AuthSessionSchema | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuthSessionSchema).where(AuthSessionSchema.refresh_token == refresh_token)
            )
            return result.scalar_one_or_none()
