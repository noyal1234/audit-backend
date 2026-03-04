"""Media storage and listing. Local path for now. AI analysis inserts audit_checkpoint_review (AI)."""

import asyncio
from pathlib import Path
from uuid import uuid4

from src.api.dependencies import require_country_access, require_facility_access
from src.database.repositories.audit_repository import AuditRepository
from src.database.repositories.audit_checkpoint_review_repository import AuditCheckpointReviewRepository
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.media_repository import MediaRepository
from src.database.repositories.zone_repository import ZoneRepository
from src.database.repositories.schemas.media_schema import MediaEvidenceResponse
from src.business_services.base import BaseBusinessService
from src.configs.settings import get_instance
from src.exceptions.domain_exceptions import NotFoundError, ValidationError


class MediaService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._media_repo: MediaRepository | None = None
        self._audit_repo: AuditRepository | None = None
        self._review_repo: AuditCheckpointReviewRepository | None = None
        self._facility_repo: FacilityRepository | None = None
        self._zone_repo: ZoneRepository | None = None
        self._session_factory = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._media_repo = MediaRepository(factory)
        self._audit_repo = AuditRepository(factory)
        self._review_repo = AuditCheckpointReviewRepository(factory)
        self._audit_repo.set_review_repository(self._review_repo)
        self._facility_repo = FacilityRepository(factory)
        self._zone_repo = ZoneRepository(factory)
        self._session_factory = factory
        Path(get_instance().storage_path).mkdir(parents=True, exist_ok=True)
        self.logger.info("[OK] MediaService initialized")

    def _close_service(self) -> None:
        self._media_repo = None
        self._audit_repo = None
        self._review_repo = None
        self._facility_repo = None
        self._zone_repo = None
        self._session_factory = None

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

    async def save_upload(
        self,
        audit_id: str,
        audit_checkpoint_id: str,
        file_content: bytes,
        filename: str,
        content_type: str | None,
        payload: dict,
    ) -> MediaEvidenceResponse:
        if self._media_repo is None or self._audit_repo is None or self._review_repo is None:
            raise RuntimeError("MediaService not initialized")
        from src.utils.validators import validate_image_filename, validate_image_content_type
        if not validate_image_filename(filename) or not validate_image_content_type(content_type):
            raise ValidationError("Invalid image file type")

        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)

        cp = await self._audit_repo.get_checkpoint_by_id(audit_checkpoint_id, audit_id)
        if not cp:
            raise NotFoundError("AuditCheckpoint", audit_checkpoint_id)

        storage_path = get_instance().storage_path
        ext = Path(filename).suffix.lower() or ".jpg"
        safe_name = f"{audit_id}_{audit_checkpoint_id}_{uuid4().hex}{ext}"
        path = Path(storage_path) / safe_name

        existing = await self._media_repo.get_by_audit_checkpoint_id(audit_checkpoint_id)
        if existing:
            old_path = Path(existing.file_path)
            if old_path.exists():
                old_path.unlink(missing_ok=True)
            path.write_bytes(file_content)
            updated = await self._media_repo.update_file_and_reset_ai(existing.id, str(path))
            media_row = updated if updated else existing
        else:
            path.write_bytes(file_content)
            media_row = await self._media_repo.create(audit_id, audit_checkpoint_id, str(path))

        sa = cp.audit_sub_area
        aa = sa.audit_area
        asyncio.create_task(
            self._run_ai_analysis(
                media_id=media_row.id,
                audit_checkpoint_id=audit_checkpoint_id,
                image_path=str(path),
                level1_name=aa.area_name,
                level1_description=None,
                subcategory_name=sa.sub_area_name,
                subcategory_description=None,
                checkpoint_name=cp.checkpoint_name,
                checkpoint_description=cp.description,
                shift_type=audit.shift_type,
                shift_date=str(audit.shift_date),
            )
        )
        return media_row

    async def _run_ai_analysis(
        self,
        *,
        media_id: str,
        audit_checkpoint_id: str,
        image_path: str,
        level1_name: str,
        level1_description: str | None,
        subcategory_name: str,
        subcategory_description: str | None,
        checkpoint_name: str,
        checkpoint_description: str | None,
        shift_type: str,
        shift_date: str,
    ) -> None:
        """Background: call AI, update media row, insert audit_checkpoint_review (review_type=AI)."""
        self.logger.info("[AI] Background analysis started for media %s (%s)", media_id, checkpoint_name)
        if self._media_repo is None or self._review_repo is None:
            return
        try:
            from src.business_services.ai_service import get_ai_service

            ai_svc = get_ai_service()
            result = await ai_svc.analyze_image(
                image_path=image_path,
                level1_name=level1_name,
                level1_description=level1_description,
                subcategory_name=subcategory_name,
                subcategory_description=subcategory_description,
                checkpoint_name=checkpoint_name,
                checkpoint_description=checkpoint_description,
                shift_type=shift_type,
                shift_date=shift_date,
            )

            await self._media_repo.update_ai_result(
                media_id,
                ai_status=result.status,
                ai_compliant=result.compliant,
                ai_confidence=result.confidence,
                ai_observations=result.observations,
                ai_summary=result.summary,
                ai_analyzed_at=result.analyzed_at,
                ai_compliance_score=result.compliance_score,
            )
            if result.status == "COMPLETED":
                await self._review_repo.insert(
                    audit_checkpoint_id=audit_checkpoint_id,
                    review_type="AI",
                    compliant=result.compliant,
                    score=result.compliance_score,
                    confidence=result.confidence,
                    remarks=result.summary,
                    model_version=get_instance().litellm_vision_model,
                    created_by=None,
                    media_id=media_id,
                )
            self.logger.info("[AI] Analysis %s for media %s", result.status, media_id)
        except Exception as exc:  # noqa: BLE001
            self.logger.error("[AI] Background analysis error for media %s: %s", media_id, exc)
            await self._media_repo.update_ai_result(
                media_id,
                ai_status="FAILED",
                ai_compliant=None,
                ai_confidence=None,
                ai_observations=None,
                ai_summary=None,
                ai_analyzed_at=None,
                ai_compliance_score=None,
            )

    async def get_image_ai_result(self, image_id: str, payload: dict) -> MediaEvidenceResponse | None:
        if self._media_repo is None or self._audit_repo is None:
            raise RuntimeError("MediaService not initialized")
        row = await self._media_repo.get_by_id(image_id)
        if not row:
            return None
        audit = await self._audit_repo.get_by_id(row.audit_id)
        if audit:
            require_facility_access(audit.facility_id, payload)
            await self._ensure_facility_in_country(audit.facility_id, payload)
        return row

    async def list_audit_images(self, audit_id: str, payload: dict) -> list[MediaEvidenceResponse]:
        if self._audit_repo is None or self._media_repo is None:
            raise RuntimeError("MediaService not initialized")
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        return await self._media_repo.list_by_audit(audit_id)

    async def get_image_file(self, image_id: str, payload: dict) -> tuple[str, str] | None:
        """Return (absolute_file_path, media_type) for streaming the image. None if not found or access denied. Path is validated to be under storage_path."""
        if self._media_repo is None or self._audit_repo is None:
            raise RuntimeError("MediaService not initialized")
        row = await self._media_repo.get_by_id(image_id)
        if not row:
            return None
        audit = await self._audit_repo.get_by_id(row.audit_id)
        if audit:
            require_facility_access(audit.facility_id, payload)
            await self._ensure_facility_in_country(audit.facility_id, payload)
        storage_root = Path(get_instance().storage_path).resolve()
        path = Path(row.file_path).resolve()
        if not path.is_file():
            return None
        try:
            path.relative_to(storage_root)
        except ValueError:
            return None
        ext = path.suffix.lower()
        media_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".heic": "image/heic",
            ".heif": "image/heif",
        }.get(ext, "image/jpeg")
        return (str(path), media_type)

    async def delete_image(self, image_id: str, payload: dict) -> bool:
        if self._media_repo is None:
            raise RuntimeError("MediaService not initialized")
        row = await self._media_repo.get_by_id(image_id)
        if not row:
            return False
        audit = await self._audit_repo.get_by_id(row.audit_id) if self._audit_repo else None
        if audit:
            require_facility_access(audit.facility_id, payload)
            await self._ensure_facility_in_country(audit.facility_id, payload)
        return await self._media_repo.delete(image_id)


_media_service: MediaService | None = None


def get_media_service() -> MediaService:
    global _media_service
    if _media_service is None:
        _media_service = MediaService()
    return _media_service
