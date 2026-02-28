from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.session import create_session_factory, get_connection_string
from src.infra_services.base import BaseInfraService
from src.logging import get_logger


class PostgresService(BaseInfraService):
    """Manages async PostgreSQL session factory."""

    def __init__(self) -> None:
        self.logger = get_logger()
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def _initialize_service(self) -> None:
        from src.configs.settings import get_instance
        settings = get_instance()
        url = get_connection_string(settings)
        self._session_factory = create_session_factory(url, echo=settings.debug)
        self.logger.info("[OK] PostgresService initialized")

    def _close_service(self) -> None:
        self._session_factory = None
        self.logger.info("[OK] PostgresService closed")

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("PostgresService not initialized")
        return self._session_factory


def get_postgres_service() -> "PostgresService":
    from src.di.container import get_container
    return get_container().get_postgres_service()
