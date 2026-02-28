"""Staff (employee) business service. Enforces facility scope. Employee login via user table."""

from uuid import uuid4

from src.api.dependencies import require_country_access, require_facility_access
from src.business_services.base import BaseBusinessService
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.staff_repository import StaffRepository
from src.database.repositories.schemas.staff_schema import StaffCreate, StaffResponse, StaffUpdate
from src.database.repositories.user_repository import UserRepository
from src.database.repositories.zone_repository import ZoneRepository
from src.database.postgres.schema.staff_schema import StaffSchema
from src.database.postgres.schema.user_schema import UserSchema
from src.exceptions.domain_exceptions import ConflictError, NotFoundError
from src.utils.pagination import PaginatedResponse, PaginationParams


class StaffService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._staff_repo: StaffRepository | None = None
        self._facility_repo: FacilityRepository | None = None
        self._zone_repo: ZoneRepository | None = None
        self._user_repo: UserRepository | None = None
        self._session_factory = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._session_factory = factory
        self._staff_repo = StaffRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self._zone_repo = ZoneRepository(factory)
        self._user_repo = UserRepository(factory)
        self.logger.info("[OK] StaffService initialized")

    def _close_service(self) -> None:
        self._staff_repo = None
        self._facility_repo = None
        self._zone_repo = None
        self._user_repo = None
        self._session_factory = None

    def _scope_facility_id(self, payload: dict) -> str | None:
        if payload.get("role_type") == "SUPER_ADMIN":
            return None
        return payload.get("facility_id")

    def _scope_country_id(self, payload: dict) -> str | None:
        if payload.get("role_type") == "SUPER_ADMIN":
            return None
        return payload.get("country_id")

    async def get_by_id(self, id: str, payload: dict) -> StaffResponse | None:
        if self._staff_repo is None:
            raise RuntimeError("StaffService not initialized")
        row = await self._staff_repo.get_by_id(id)
        if not row:
            return None
        require_facility_access(row.facility_id, payload)
        if self._scope_country_id(payload):
            fac = await self._facility_repo.get_by_id(row.facility_id)
            if fac and self._zone_repo:
                zone = await self._zone_repo.get_by_id(fac.zone_id)
                if zone and zone.country_id:
                    require_country_access(zone.country_id, payload)
        return row

    async def list_staff(
        self,
        payload: dict,
        dealership_id: str | None = None,
        search: str | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[StaffResponse]:
        if self._staff_repo is None:
            raise RuntimeError("StaffService not initialized")
        params = params or PaginationParams()
        scope_fac = self._scope_facility_id(payload)
        scope_country = self._scope_country_id(payload)
        facility_id = dealership_id or scope_fac
        if scope_fac and dealership_id and dealership_id != scope_fac:
            return PaginatedResponse.build([], 0, params.page, params.limit)
        items, total = await self._staff_repo.list_staff(
            facility_id=facility_id,
            country_id=scope_country,
            search=search,
            offset=params.offset,
            limit=params.limit,
            sort=params.sort,
            order=params.order,
        )
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def create(self, data: StaffCreate, payload: dict) -> StaffResponse:
        if self._staff_repo is None or self._facility_repo is None or self._user_repo is None or self._session_factory is None:
            raise RuntimeError("StaffService not initialized")
        facility = await self._facility_repo.get_by_id(data.facility_id)
        if not facility:
            raise NotFoundError("Facility", data.facility_id)
        require_facility_access(data.facility_id, payload)
        if self._scope_country_id(payload) and self._zone_repo:
            zone = await self._zone_repo.get_by_id(facility.zone_id)
            if zone and zone.country_id:
                require_country_access(zone.country_id, payload)
        existing = await self._user_repo.get_by_email(data.email)
        if existing:
            raise ConflictError("Email already in use")
        from src.business_services.auth_service import get_auth_service
        password_hash = get_auth_service()._hash_password(data.password)
        async with self._session_factory() as session:
            user_row = UserSchema(
                id=str(uuid4()),
                email=data.email,
                password_hash=password_hash,
                role_type="EMPLOYEE",
                facility_id=data.facility_id,
                country_id=None,
                is_active=True,
            )
            session.add(user_row)
            await session.flush()
            staff_row = StaffSchema(
                id=str(uuid4()),
                facility_id=data.facility_id,
                user_id=user_row.id,
                name=data.name,
            )
            session.add(staff_row)
            await session.commit()
            await session.refresh(staff_row)
        return StaffResponse(
            id=staff_row.id,
            facility_id=staff_row.facility_id,
            user_id=staff_row.user_id,
            name=staff_row.name,
            email=data.email,
            created_at=staff_row.created_at,
            updated_at=staff_row.updated_at,
        )

    async def update(self, id: str, data: StaffUpdate, payload: dict) -> StaffResponse | None:
        if self._staff_repo is None:
            raise RuntimeError("StaffService not initialized")
        row = await self._staff_repo.get_by_id(id)
        if not row:
            return None
        require_facility_access(row.facility_id, payload)
        if self._scope_country_id(payload) and self._zone_repo:
            fac = await self._facility_repo.get_by_id(row.facility_id)
            if fac:
                zone = await self._zone_repo.get_by_id(fac.zone_id)
                if zone and zone.country_id:
                    require_country_access(zone.country_id, payload)
        return await self._staff_repo.update(id, data)

    async def delete(self, id: str, payload: dict) -> bool:
        if self._staff_repo is None:
            raise RuntimeError("StaffService not initialized")
        row = await self._staff_repo.get_by_id(id)
        if not row:
            return False
        require_facility_access(row.facility_id, payload)
        if self._scope_country_id(payload) and self._zone_repo:
            fac = await self._facility_repo.get_by_id(row.facility_id)
            if fac:
                zone = await self._zone_repo.get_by_id(fac.zone_id)
                if zone and zone.country_id:
                    require_country_access(zone.country_id, payload)
        return await self._staff_repo.delete(id)


_staff_service: StaffService | None = None


def get_staff_service() -> StaffService:
    global _staff_service
    if _staff_service is None:
        _staff_service = StaffService()
    return _staff_service
