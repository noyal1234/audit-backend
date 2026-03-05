"""Snapshot-based shift audit: lazy creation, checkpoint completion, manual review, finalize, reopen, delete, rebuild."""

import os
from datetime import date

from src.api.dependencies import require_country_access, require_facility_access
from src.database.repositories.audit_repository import AuditRepository
from src.database.repositories.audit_checkpoint_review_repository import AuditCheckpointReviewRepository
from src.database.repositories.area_repository import AreaRepository
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.media_repository import MediaRepository
from src.database.repositories.zone_repository import ZoneRepository
from src.database.repositories.schemas.audit_schema import (
    AuditCreate,
    AuditDetailResponse,
    AuditProgressResponse,
    AuditQualityScoreResponse,
    AuditResponse,
    CheckpointCompleteRequest,
)
from src.database.repositories.schemas.review_schema import ManualReviewRequest
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
        self._review_repo: AuditCheckpointReviewRepository | None = None
        self._area_repo: AreaRepository | None = None
        self._facility_repo: FacilityRepository | None = None
        self._media_repo: MediaRepository | None = None
        self._zone_repo: ZoneRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._audit_repo = AuditRepository(factory)
        self._review_repo = AuditCheckpointReviewRepository(factory)
        self._audit_repo.set_review_repository(self._review_repo)
        self._area_repo = AreaRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self._media_repo = MediaRepository(factory)
        self._zone_repo = ZoneRepository(factory)
        self.logger.info("[OK] AuditService initialized")

    def _close_service(self) -> None:
        self._audit_repo = None
        self._review_repo = None
        self._area_repo = None
        self._facility_repo = None
        self._media_repo = None
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
        facility, is_active = await self._facility_repo.get_by_id_with_active(facility_id)
        if not facility:
            raise NotFoundError("Facility", facility_id)
        if not is_active:
            raise ConflictError("Facility is inactive")
        require_facility_access(facility_id, payload)
        await self._ensure_facility_in_country(facility_id, payload)

        shift_svc = get_shift_service()
        current = await shift_svc.get_current_shift(facility_id)
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
        hierarchy = await self._area_repo.get_facility_hierarchy(facility_id)
        data = AuditCreate(facility_id=facility_id, shift_type=shift_type, shift_date=shift_date)
        return await self._audit_repo.create_with_snapshot(data, created_by, hierarchy)

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

    async def get_quality_score(self, audit_id: str, payload: dict) -> AuditQualityScoreResponse:
        """Average compliance score from effective reviews. Checkpoints without a review are excluded."""
        self._require_initialized()
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        result = await self._audit_repo.get_quality_score(audit_id)
        if result is None:
            raise NotFoundError("Audit", audit_id)
        return result

    # --- Auto status: COMPLETED when all checkpoints done; IN_PROGRESS when not ---

    async def _recalculate_status(self, audit_id: str) -> None:
        """Set audit to COMPLETED if all checkpoints completed, else to IN_PROGRESS. Never touch FINALIZED."""
        if self._audit_repo is None:
            return
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            return
        if audit.status_type == "FINALIZED":
            return
        progress = await self._audit_repo.get_progress(audit_id)
        if not progress:
            return
        total = progress.total_checkpoints
        completed = progress.completed_checkpoints
        if total == 0:
            return
        if completed == total:
            if audit.status_type != "COMPLETED":
                await self._audit_repo.update_status(audit_id, "COMPLETED", None)
        else:
            if audit.status_type in ("PENDING", "COMPLETED", "REOPENED"):
                await self._audit_repo.update_status(audit_id, "IN_PROGRESS", None)

    # --- Checkpoint completion (EMPLOYEE+) ---

    async def mark_checkpoint_completed(
        self,
        audit_id: str,
        checkpoint_id: str,
        data: CheckpointCompleteRequest | None,
        payload: dict,
    ) -> AuditDetailResponse:
        self._require_initialized()
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        if audit.status_type not in EDITABLE_STATUSES:
            raise ConflictError(f"Cannot modify audit in {audit.status_type} state")
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)

        cp = await self._audit_repo.get_checkpoint_by_id(checkpoint_id, audit_id)
        if not cp:
            raise NotFoundError("AuditCheckpoint", checkpoint_id)

        ok = await self._audit_repo.mark_checkpoint_completed(
            checkpoint_id, (data.remarks if data else None)
        )
        if not ok:
            raise NotFoundError("AuditCheckpoint", checkpoint_id)
        await self._recalculate_status(audit_id)
        detail = await self._audit_repo.get_detail(audit_id)
        if not detail:
            raise NotFoundError("Audit", audit_id)
        return detail

    async def mark_checkpoint_incomplete(
        self,
        audit_id: str,
        checkpoint_id: str,
        payload: dict,
    ) -> AuditDetailResponse:
        self._require_initialized()
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        if audit.status_type not in EDITABLE_STATUSES:
            raise ConflictError(f"Cannot modify audit in {audit.status_type} state")
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)

        cp = await self._audit_repo.get_checkpoint_by_id(checkpoint_id, audit_id)
        if not cp:
            raise NotFoundError("AuditCheckpoint", checkpoint_id)

        ok = await self._audit_repo.mark_checkpoint_incomplete(checkpoint_id)
        if not ok:
            raise NotFoundError("AuditCheckpoint", checkpoint_id)
        await self._recalculate_status(audit_id)
        detail = await self._audit_repo.get_detail(audit_id)
        if not detail:
            raise NotFoundError("Audit", audit_id)
        return detail

    # --- Manual review (DEALERSHIP+); block if FINALIZED ---

    async def submit_manual_review(
        self,
        audit_id: str,
        checkpoint_id: str,
        data: ManualReviewRequest,
        payload: dict,
    ) -> AuditDetailResponse:
        self._require_initialized()
        if self._review_repo is None:
            raise RuntimeError("AuditService not initialized")
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        if audit.status_type == "FINALIZED":
            raise ConflictError("Cannot add or change review on a finalized audit")
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)

        cp = await self._audit_repo.get_checkpoint_by_id(checkpoint_id, audit_id)
        if not cp:
            raise NotFoundError("AuditCheckpoint", checkpoint_id)

        existing_media = await self._media_repo.get_by_audit_checkpoint_id(checkpoint_id) if self._media_repo else None
        await self._review_repo.insert(
            audit_checkpoint_id=checkpoint_id,
            review_type="MANUAL",
            compliant=data.compliant,
            score=data.score,
            confidence=None,
            remarks=data.remarks,
            model_version=None,
            created_by=payload["sub"],
            media_id=existing_media.id if existing_media else None,
        )
        detail = await self._audit_repo.get_detail(audit_id)
        if not detail:
            raise NotFoundError("Audit", audit_id)
        return detail

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

    # --- Delete / Rebuild ---

    async def delete_audit(self, audit_id: str, payload: dict) -> None:
        """Delete audit and its media. FINALIZED audits cannot be deleted. Removes DB rows and physical files."""
        self._require_initialized()
        if self._media_repo is None:
            raise RuntimeError("AuditService not initialized")
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        if audit.status_type == "FINALIZED":
            raise ConflictError("Finalized audits cannot be deleted.")
        file_paths = await self._media_repo.delete_by_audit(audit_id)
        deleted = await self._audit_repo.delete(audit_id)
        if not deleted:
            raise NotFoundError("Audit", audit_id)
        for fp in file_paths:
            try:
                os.remove(fp)
            except FileNotFoundError:
                self.logger.warning("[WARNING] Audit delete: file not found %s", fp)
            except OSError as e:
                self.logger.warning("[WARNING] Audit delete: could not remove file %s: %s", fp, e)

    async def rebuild_audit(self, audit_id: str, payload: dict) -> AuditDetailResponse:
        """Delete the audit and create a fresh one for same facility/shift with current hierarchy snapshot."""
        self._require_initialized()
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        if audit.status_type == "FINALIZED":
            raise ConflictError("Finalized audits cannot be deleted.")
        facility_id = audit.facility_id
        shift_type = audit.shift_type
        shift_date = audit.shift_date
        await self.delete_audit(audit_id, payload)
        return await self._create_shift_audit_snapshot(
            facility_id=facility_id,
            shift_type=shift_type,
            shift_date=shift_date,
            created_by=payload["sub"],
        )


_audit_service: AuditService | None = None


def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
