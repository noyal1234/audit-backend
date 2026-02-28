from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.base import Base


def get_connection_string(settings: Any) -> str:
    """Build async PostgreSQL connection string from settings."""
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def create_session_factory(connection_string: str, echo: bool = False) -> async_sessionmaker[AsyncSession]:
    """Create async engine and session factory."""
    engine = create_async_engine(
        connection_string,
        echo=echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async session."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
