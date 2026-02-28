"""Country service (future-ready)."""

from src.business_services.base import BaseBusinessService
from src.database.repositories.country_repository import CountryRepository
from src.database.repositories.schemas.country_schema import CountryCreate, CountryResponse, CountryUpdate
from src.exceptions.domain_exceptions import ConflictError
from src.utils.pagination import PaginatedResponse, PaginationParams


class CountryService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._repo: CountryRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._repo = CountryRepository(factory)
        self.logger.info("[OK] CountryService initialized")

    def _close_service(self) -> None:
        self._repo = None

    async def get_by_id(self, id: str) -> CountryResponse | None:
        if self._repo is None:
            raise RuntimeError("CountryService not initialized")
        return await self._repo.get_by_id(id)

    async def list_countries(self, params: PaginationParams | None = None) -> PaginatedResponse[CountryResponse]:
        if self._repo is None:
            raise RuntimeError("CountryService not initialized")
        params = params or PaginationParams()
        items, total = await self._repo.list_countries(
            offset=params.offset, limit=params.limit, sort=params.sort, order=params.order
        )
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def create(self, data: CountryCreate) -> CountryResponse:
        if self._repo is None:
            raise RuntimeError("CountryService not initialized")
        existing = await self._repo.get_by_code(data.code)
        if existing:
            raise ConflictError("Country code already in use")
        return await self._repo.create(data)

    async def update(self, id: str, data: CountryUpdate) -> CountryResponse | None:
        if self._repo is None:
            raise RuntimeError("CountryService not initialized")
        return await self._repo.update(id, data)

    async def delete(self, id: str) -> bool:
        if self._repo is None:
            raise RuntimeError("CountryService not initialized")
        return await self._repo.delete(id)


_country_service: CountryService | None = None


def get_country_service() -> CountryService:
    global _country_service
    if _country_service is None:
        _country_service = CountryService()
    return _country_service
