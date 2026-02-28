"""Audit execution: create (one per shift per facility), record checkpoint, finalize, reopen."""

from datetime import date, datetime

from src.api.dependencies import require_country_access, require_facility_access
from src.database.repositories.audit_repository import AuditCheckpointResultRepository, AuditRepository
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.zone_repository import ZoneRepository
from src.database.repositories.schemas.audit_schema import (
    AuditCreate,
    AuditResponse,
    CheckpointResultCreate,
    CheckpointResultResponse,
)
from src.business_services.base import BaseBusinessService
from src.business_services.shift_service import get_shift_service
from src.exceptions.domain_exceptions import ConflictError, ForbiddenError, NotFoundError
from src.utils.datetime_utils import today_utc, utc_now
from src.utils.pagination import PaginatedResponse, PaginationParams


class AuditService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._audit_repo: AuditRepository | None = None
        self._checkpoint_result_repo: AuditCheckpointResultRepository | None = None
        self._facility_repo: FacilityRepository | None = None
        self._zone_repo: ZoneRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._audit_repo = AuditRepository(factory)
        self._checkpoint_result_repo = AuditCheckpointResultRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self._zone_repo = ZoneRepository(factory)
        self.logger.info("[OK] AuditService initialized")

    def _close_service(self) -> None:
        self._audit_repo = None
        self._checkpoint_result_repo = None
        self._facility_repo = None
        self._zone_repo = None

    async def _ensure_facility_in_country(self, facility_id: str, payload: dict) -> None:
        """Raise ForbiddenError if STELLANTIS_ADMIN and facility is not in their country."""
        if not payload.get("country_id"):
            return
        if self._facility_repo is None or self._zone_repo is None:
            return
        fac = await self._facility_repo.get_by_id(facility_id)
        if not fac:
            return
        zone = await self._zone_repo.get_by_id(fac.zone_id)
        if zone and zone.country_id:
            require_country_access(zone.country_id, payload)

    def _scope_facility_ids(self, payload: dict, facility_id: str | None, zone_id: str | None) -> list[str] | None:
        """Return list of facility ids the user can see, or None for no filter (super admin / STELLANTIS_ADMIN uses country_id in repo)."""
        if payload.get("role_type") == "SUPER_ADMIN":
            return None
        if payload.get("facility_id"):
            return [payload["facility_id"]] if (not facility_id or facility_id == payload["facility_id"]) else []
        if payload.get("country_id"):
            return None
        return []

    async def create(self, data: AuditCreate, user_id: str, payload: dict) -> AuditResponse:
        if self._audit_repo is None or self._facility_repo is None:
            raise RuntimeError("AuditService not initialized")
        facility = await self._facility_repo.get_by_id(data.facility_id)
        if not facility:
            raise NotFoundError("Facility", data.facility_id)
        require_facility_access(data.facility_id, payload)
        await self._ensure_facility_in_country(data.facility_id, payload)
        shift_svc = get_shift_service()
        current = await shift_svc.get_current_shift()
        if not current:
            raise ConflictError("No shift config or current shift not determined")
        if not current.is_current:
            raise ConflictError("Audit can only be created for the current shift")
        if data.shift_date != current.shift_date or data.shift_type != current.shift_type:
            raise ConflictError("Audit must be for current shift date and type")
        existing = await self._audit_repo.find_by_facility_shift_date(
            data.facility_id, data.shift_type, data.shift_date
        )
        if existing:
            raise ConflictError("Only one audit per shift per facility allowed")
        return await self._audit_repo.create(data, created_by=user_id, status_type="IN_PROGRESS")

    async def get_by_id(self, id: str, payload: dict) -> AuditResponse | None:
        if self._audit_repo is None:
            raise RuntimeError("AuditService not initialized")
        audit = await self._audit_repo.get_by_id(id)
        if not audit:
            return None
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        return audit

    async def list_audits(
        self,
        payload: dict,
        zone_id: str | None = None,
        facility_id: str | None = None,
        shift_type: str | None = None,
        shift_date: date | None = None,
        status_type: str | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[AuditResponse]:
        if self._audit_repo is None:
            raise RuntimeError("AuditService not initialized")
        params = params or PaginationParams()
        facility_ids = self._scope_facility_ids(payload, facility_id, zone_id)
        scope_country_id = payload.get("country_id") if payload.get("role_type") == "STELLANTIS_ADMIN" else None
        if facility_ids is not None and facility_ids == []:
            return PaginatedResponse.build([], 0, params.page, params.limit)
        items, total = await self._audit_repo.list_audits(
            zone_id=zone_id,
            country_id=scope_country_id,
            facility_id=facility_id,
            facility_ids=facility_ids,
            shift_type=shift_type,
            shift_date=shift_date,
            status_type=status_type,
            offset=params.offset,
            limit=params.limit,
            sort=params.sort,
            order=params.order,
        )
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def record_checkpoint(
        self,
        audit_id: str,
        checkpoint_id: str,
        data: CheckpointResultCreate,
        payload: dict,
    ) -> CheckpointResultResponse:
        if self._audit_repo is None or self._checkpoint_result_repo is None:
            raise RuntimeError("AuditService not initialized")
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        if audit.status_type == "FINALIZED":
            raise ConflictError("Cannot modify finalized audit")
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        return await self._checkpoint_result_repo.get_or_create_result(audit_id, checkpoint_id, data)

    async def upload_image_ai_status(
        self,
        audit_id: str,
        checkpoint_id: str,
        image_path: str,
        payload: dict,
    ) -> CheckpointResultResponse | None:
        if self._checkpoint_result_repo is None:
            raise RuntimeError("AuditService not initialized")
        audit = await self._audit_repo.get_by_id(audit_id) if self._audit_repo else None
        if not audit:
            raise NotFoundError("Audit", audit_id)
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        return await self._checkpoint_result_repo.update_ai_status(
            audit_id, checkpoint_id, "AI_PENDING", None
        )

    async def get_ai_result(
        self,
        audit_id: str,
        checkpoint_id: str,
        payload: dict,
    ) -> CheckpointResultResponse | None:
        if self._audit_repo is None or self._checkpoint_result_repo is None:
            raise RuntimeError("AuditService not initialized")
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            return None
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        return await self._checkpoint_result_repo.get_result(audit_id, checkpoint_id)

    async def finalize(self, audit_id: str, payload: dict) -> AuditResponse | None:
        if self._audit_repo is None:
            raise RuntimeError("AuditService not initialized")
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            return None
        if audit.status_type == "FINALIZED":
            raise ConflictError("Audit already finalized")
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        return await self._audit_repo.finalize(audit_id, utc_now())

    async def reopen(self, audit_id: str, payload: dict) -> AuditResponse | None:
        if self._audit_repo is None:
            raise RuntimeError("AuditService not initialized")
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            return None
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        return await self._audit_repo.reopen(audit_id)


_audit_service: AuditService | None = None


def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
