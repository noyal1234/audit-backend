"""Snapshot-based shift audit: lazy creation, category completion, auto-status, reopen."""

from datetime import date

from src.api.dependencies import require_country_access, require_facility_access
from src.database.repositories.audit_repository import AuditCheckpointCategoryRepository, AuditRepository
from src.database.repositories.checkpoint_repository import CheckpointRepository
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.zone_repository import ZoneRepository
from src.database.repositories.schemas.audit_schema import (
    AuditCheckpointCategoryResponse,
    AuditCreate,
    AuditDetailResponse,
    AuditProgressResponse,
    AuditResponse,
    CategoryCompleteRequest,
)
from src.business_services.base import BaseBusinessService
from src.business_services.shift_service import get_shift_service
from src.exceptions.domain_exceptions import ConflictError, NotFoundError
from src.utils.datetime_utils import utc_now
from src.utils.pagination import PaginatedResponse, PaginationParams

VALID_TRANSITIONS = {
    "PENDING": {"IN_PROGRESS"},
    "IN_PROGRESS": {"COMPLETED", "FINALIZED"},
    "COMPLETED": {"REOPENED", "FINALIZED"},
    "REOPENED": {"IN_PROGRESS", "COMPLETED", "FINALIZED"},
}
EDITABLE_STATUSES = {"PENDING", "IN_PROGRESS", "REOPENED"}


class AuditService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._audit_repo: AuditRepository | None = None
        self._category_result_repo: AuditCheckpointCategoryRepository | None = None
        self._checkpoint_repo: CheckpointRepository | None = None
        self._facility_repo: FacilityRepository | None = None
        self._zone_repo: ZoneRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._audit_repo = AuditRepository(factory)
        self._category_result_repo = AuditCheckpointCategoryRepository(factory)
        self._checkpoint_repo = CheckpointRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self._zone_repo = ZoneRepository(factory)
        self.logger.info("[OK] AuditService initialized")

    def _close_service(self) -> None:
        self._audit_repo = None
        self._category_result_repo = None
        self._checkpoint_repo = None
        self._facility_repo = None
        self._zone_repo = None

    async def _ensure_facility_in_country(self, facility_id: str, payload: dict) -> None:
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
        if payload.get("role_type") == "SUPER_ADMIN":
            return None
        if payload.get("facility_id"):
            return [payload["facility_id"]] if (not facility_id or facility_id == payload["facility_id"]) else []
        if payload.get("country_id"):
            return None
        return []

    def _require_initialized(self) -> None:
        if self._audit_repo is None:
            raise RuntimeError("AuditService not initialized")

    # --- Lazy creation / current audit ---

    async def get_or_create_current_audit(self, payload: dict) -> AuditDetailResponse:
        """Get or lazily create the audit for the current shift for the user's facility."""
        self._require_initialized()
        facility_id = payload.get("facility_id")
        if not facility_id:
            raise ConflictError("Only facility-scoped users can access current audit")
        facility = await self._facility_repo.get_by_id(facility_id)
        if not facility:
            raise NotFoundError("Facility", facility_id)
        require_facility_access(facility_id, payload)
        await self._ensure_facility_in_country(facility_id, payload)

        shift_svc = get_shift_service()
        current = await shift_svc.get_current_shift()
        if not current:
            raise ConflictError("No shift config or current shift not determined")
        if not current.is_current:
            raise ConflictError("No active shift currently running")

        existing = await self._audit_repo.find_by_facility_shift_date(
            facility_id, current.shift_type, date.fromisoformat(current.shift_date)
        )
        if existing:
            detail = await self._audit_repo.get_detail(existing.id)
            if detail:
                return detail

        return await self._create_shift_audit_snapshot(
            facility_id=facility_id,
            shift_type=current.shift_type,
            shift_date=date.fromisoformat(current.shift_date),
            created_by=payload["sub"],
        )

    async def _create_shift_audit_snapshot(
        self,
        facility_id: str,
        shift_type: str,
        shift_date: date,
        created_by: str,
    ) -> AuditDetailResponse:
        checkpoints, _ = await self._checkpoint_repo.list_checkpoints(
            facility_id=facility_id, offset=0, limit=1000
        )
        snapshot = []
        for cp in checkpoints:
            cats = [
                {"category_id": cat.id, "category_name": cat.name}
                for cat in cp.categories
            ]
            snapshot.append({
                "checkpoint_id": cp.id,
                "checkpoint_name": cp.name,
                "image_url": cp.image_url,
                "categories": cats,
            })
        data = AuditCreate(facility_id=facility_id, shift_type=shift_type, shift_date=shift_date)
        return await self._audit_repo.create_with_snapshot(data, created_by, snapshot)

    # --- Read ---

    async def get_by_id(self, id: str, payload: dict) -> AuditDetailResponse | None:
        self._require_initialized()
        audit = await self._audit_repo.get_by_id(id)
        if not audit:
            return None
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        return await self._audit_repo.get_detail(id)

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
        self._require_initialized()
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

    async def get_progress(self, audit_id: str, payload: dict) -> AuditProgressResponse:
        self._require_initialized()
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        progress = await self._audit_repo.get_progress(audit_id)
        if not progress:
            raise NotFoundError("Audit", audit_id)
        return progress

    # --- Category completion ---

    async def complete_category(
        self,
        audit_id: str,
        category_result_id: str,
        data: CategoryCompleteRequest,
        payload: dict,
    ) -> AuditCheckpointCategoryResponse:
        self._require_initialized()
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        if audit.status_type not in EDITABLE_STATUSES:
            raise ConflictError(f"Cannot modify audit in {audit.status_type} state")
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)

        cat_row, cp_row = await self._category_result_repo.get_with_checkpoint(category_result_id)
        if not cat_row or not cp_row:
            raise NotFoundError("AuditCheckpointCategory", category_result_id)
        if cp_row.audit_id != audit_id:
            raise NotFoundError("AuditCheckpointCategory", category_result_id)

        result = await self._category_result_repo.mark_complete(
            category_result_id, payload["sub"], utc_now(), data.remarks
        )
        if not result:
            raise NotFoundError("AuditCheckpointCategory", category_result_id)

        await self._category_result_repo.update_checkpoint_status(cp_row.id)
        await self._category_result_repo.recompute_audit_status(audit_id)
        return result

    async def uncomplete_category(
        self,
        audit_id: str,
        category_result_id: str,
        payload: dict,
    ) -> AuditCheckpointCategoryResponse:
        self._require_initialized()
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        if audit.status_type not in EDITABLE_STATUSES:
            raise ConflictError(f"Cannot modify audit in {audit.status_type} state")
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)

        cat_row, cp_row = await self._category_result_repo.get_with_checkpoint(category_result_id)
        if not cat_row or not cp_row:
            raise NotFoundError("AuditCheckpointCategory", category_result_id)
        if cp_row.audit_id != audit_id:
            raise NotFoundError("AuditCheckpointCategory", category_result_id)

        result = await self._category_result_repo.mark_uncomplete(category_result_id)
        if not result:
            raise NotFoundError("AuditCheckpointCategory", category_result_id)

        await self._category_result_repo.update_checkpoint_status(cp_row.id)
        await self._category_result_repo.recompute_audit_status(audit_id)
        return result

    # --- Finalize / Reopen ---

    async def finalize(self, audit_id: str, payload: dict) -> AuditResponse | None:
        self._require_initialized()
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            return None
        if audit.status_type == "FINALIZED":
            raise ConflictError("Audit already finalized")
        if audit.status_type not in ("IN_PROGRESS", "COMPLETED", "REOPENED"):
            raise ConflictError(f"Cannot finalize audit in {audit.status_type} state")
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        return await self._audit_repo.update_status(audit_id, "FINALIZED", utc_now())

    async def reopen(self, audit_id: str, payload: dict) -> AuditResponse | None:
        self._require_initialized()
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            return None
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        if audit.status_type == "FINALIZED":
            if payload.get("role_type") != "SUPER_ADMIN":
                raise ConflictError("Only SUPER_ADMIN can reopen a finalized audit")
        elif audit.status_type != "COMPLETED":
            raise ConflictError(f"Cannot reopen audit in {audit.status_type} state")
        return await self._audit_repo.update_status(audit_id, "REOPENED", None)


_audit_service: AuditService | None = None


def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
