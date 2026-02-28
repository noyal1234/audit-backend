"""Facility (dealership) business service. Enforces hierarchy. Dealership login via user table."""

from src.api.dependencies import require_country_access, require_facility_access
from src.business_services.base import BaseBusinessService
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.schemas.dealer_schema import (
    DealerContactResponse,
    DealerContactUpdate,
    FacilityCreate,
    FacilityResponse,
    FacilityUpdate,
)
from src.database.repositories.schemas.user_schema import UserCreate
from src.database.repositories.user_repository import UserRepository
from src.database.repositories.zone_repository import ZoneRepository
from src.exceptions.domain_exceptions import ConflictError, NotFoundError
from src.utils.pagination import PaginatedResponse, PaginationParams


class DealerService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._facility_repo: FacilityRepository | None = None
        self._zone_repo: ZoneRepository | None = None
        self._user_repo: UserRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._facility_repo = FacilityRepository(factory)
        self._zone_repo = ZoneRepository(factory)
        self._user_repo = UserRepository(factory)
        self.logger.info("[OK] DealerService initialized")

    def _close_service(self) -> None:
        self._facility_repo = None
        self._zone_repo = None
        self._user_repo = None

    def _scope_country_id(self, payload: dict) -> str | None:
        if payload.get("role_type") == "SUPER_ADMIN":
            return None
        return payload.get("country_id")

    def _scope_facility_id(self, payload: dict) -> str | None:
        if payload.get("role_type") == "SUPER_ADMIN":
            return None
        return payload.get("facility_id")

    async def get_by_id(self, id: str, payload: dict) -> FacilityResponse | None:
        if self._facility_repo is None:
            raise RuntimeError("DealerService not initialized")
        require_facility_access(id, payload)
        fac = await self._facility_repo.get_by_id(id)
        if not fac:
            return None
        if self._scope_country_id(payload):
            zone = await self._zone_repo.get_by_id(fac.zone_id)
            if not zone or zone.country_id != self._scope_country_id(payload):
                return None
        return fac

    async def list_facilities(
        self,
        payload: dict,
        zone_id: str | None = None,
        search: str | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[FacilityResponse]:
        if self._facility_repo is None:
            raise RuntimeError("DealerService not initialized")
        params = params or PaginationParams()
        scope_country = self._scope_country_id(payload)
        scope_fac = self._scope_facility_id(payload)
        if scope_fac:
            fac = await self._facility_repo.get_by_id(scope_fac)
            items = [fac] if fac else []
            total = 1 if fac else 0
        else:
            items, total = await self._facility_repo.list_facilities(
                zone_id=zone_id,
                country_id=scope_country,
                search=search,
                offset=params.offset,
                limit=params.limit,
                sort=params.sort,
                order=params.order,
            )
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def create(self, data: FacilityCreate, payload: dict) -> FacilityResponse:
        if self._facility_repo is None or self._zone_repo is None or self._user_repo is None:
            raise RuntimeError("DealerService not initialized")
        zone = await self._zone_repo.get_by_id(data.zone_id)
        if not zone:
            raise NotFoundError("Zone", data.zone_id)
        if self._scope_country_id(payload):
            require_country_access(zone.country_id or "", payload)
        existing = await self._user_repo.get_by_email(data.email)
        if existing:
            raise ConflictError("Email already in use")
        fac = await self._facility_repo.create(data)
        from src.business_services.auth_service import get_auth_service
        password_hash = get_auth_service()._hash_password(data.password)
        user_create = UserCreate(
            email=data.email,
            password=data.password,
            role_type="DEALERSHIP",
            facility_id=fac.id,
            country_id=None,
        )
        user = await self._user_repo.create(user_create, password_hash)
        updated = await self._facility_repo.update(fac.id, FacilityUpdate(user_id=user.id))
        return updated or fac

    async def update(self, id: str, data: FacilityUpdate, payload: dict) -> FacilityResponse | None:
        if self._facility_repo is None:
            raise RuntimeError("DealerService not initialized")
        require_facility_access(id, payload)
        fac = await self._facility_repo.get_by_id(id)
        if not fac:
            return None
        if self._scope_country_id(payload):
            zone = await self._zone_repo.get_by_id(fac.zone_id)
            if not zone or zone.country_id != self._scope_country_id(payload):
                return None
        return await self._facility_repo.update(id, data)

    async def get_contact(self, id: str, payload: dict) -> DealerContactResponse | None:
        """Get dealer contact details. Returns None if facility not found or access denied."""
        fac = await self.get_by_id(id, payload)
        if not fac:
            return None
        return DealerContactResponse(
            dealer_name=fac.dealer_name,
            dealer_phone=fac.dealer_phone,
            dealer_email=fac.dealer_email,
            dealer_designation=fac.dealer_designation,
        )

    async def update_contact(self, id: str, data: DealerContactUpdate, payload: dict) -> FacilityResponse | None:
        """Update only dealer contact details. Employee forbidden (enforced by RequireDealership)."""
        fac = await self.get_by_id(id, payload)
        if not fac:
            return None
        update_data = FacilityUpdate(
            dealer_name=data.dealer_name,
            dealer_phone=data.dealer_phone,
            dealer_email=data.dealer_email,
            dealer_designation=data.dealer_designation,
        )
        return await self._facility_repo.update(id, update_data)

    async def delete(self, id: str, payload: dict) -> bool:
        if self._facility_repo is None:
            raise RuntimeError("DealerService not initialized")
        require_facility_access(id, payload)
        fac = await self._facility_repo.get_by_id(id)
        if not fac:
            return False
        if self._scope_country_id(payload):
            zone = await self._zone_repo.get_by_id(fac.zone_id)
            if not zone or zone.country_id != self._scope_country_id(payload):
                return False
        return await self._facility_repo.delete(id)


_dealer_service: DealerService | None = None


def get_dealer_service() -> DealerService:
    global _dealer_service
    if _dealer_service is None:
        _dealer_service = DealerService()
    return _dealer_service
