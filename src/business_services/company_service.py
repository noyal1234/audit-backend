"""Zone (company) business service. Enforces hierarchy for non-super-admin."""

from src.api.dependencies import require_country_access
from src.business_services.base import BaseBusinessService
from src.database.repositories.country_repository import CountryRepository
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.schemas.company_schema import ZoneCreate, ZoneResponse, ZoneUpdate
from src.database.repositories.zone_repository import ZoneRepository
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginatedResponse, PaginationParams


class CompanyService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._zone_repo: ZoneRepository | None = None
        self._facility_repo: FacilityRepository | None = None
        self._country_repo: CountryRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._zone_repo = ZoneRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self._country_repo = CountryRepository(factory)
        self.logger.info("[OK] CompanyService initialized")

    def _close_service(self) -> None:
        self._zone_repo = None
        self._facility_repo = None
        self._country_repo = None

    async def get_by_id(self, id: str, payload: dict) -> ZoneResponse | None:
        if self._zone_repo is None:
            raise RuntimeError("CompanyService not initialized")
        zone = await self._zone_repo.get_by_id(id)
        if not zone:
            return None
        require_country_access(zone.country_id or "", payload)
        return zone

    async def list_zones(
        self,
        payload: dict,
        country_id: str | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[ZoneResponse]:
        if self._zone_repo is None:
            raise RuntimeError("CompanyService not initialized")
        params = params or PaginationParams()
        scope_country_id = None if payload.get("role_type") == "SUPER_ADMIN" else payload.get("country_id")
        effective_country = country_id or scope_country_id
        items, total = await self._zone_repo.list_zones(
            country_id=effective_country,
            zone_id=None,
            offset=params.offset,
            limit=params.limit,
            sort=params.sort,
            order=params.order,
        )
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def create(self, data: ZoneCreate, payload: dict) -> ZoneResponse:
        if self._zone_repo is None:
            raise RuntimeError("CompanyService not initialized")
        if data.country_id and self._country_repo:
            country = await self._country_repo.get_by_id(data.country_id)
            if not country:
                raise NotFoundError("Country", data.country_id)
            require_country_access(data.country_id, payload)
        return await self._zone_repo.create(data)

    async def update(self, id: str, data: ZoneUpdate, payload: dict) -> ZoneResponse | None:
        if self._zone_repo is None:
            raise RuntimeError("CompanyService not initialized")
        zone = await self._zone_repo.get_by_id(id)
        if not zone:
            return None
        require_country_access(zone.country_id or "", payload)
        return await self._zone_repo.update(id, data)

    async def delete(self, id: str, payload: dict) -> bool:
        if self._zone_repo is None:
            raise RuntimeError("CompanyService not initialized")
        zone = await self._zone_repo.get_by_id(id)
        if not zone:
            return False
        require_country_access(zone.country_id or "", payload)
        return await self._zone_repo.delete(id)


_company_service: CompanyService | None = None


def get_company_service() -> CompanyService:
    global _company_service
    if _company_service is None:
        _company_service = CompanyService()
    return _company_service
