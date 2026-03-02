"""Media storage and listing. Local path for now."""

import asyncio
from pathlib import Path
from uuid import uuid4

from src.api.dependencies import require_country_access, require_facility_access
from src.database.repositories.audit_repository import AuditCheckpointCategoryRepository, AuditRepository
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
        self._audit_category_repo: AuditCheckpointCategoryRepository | None = None
        self._facility_repo: FacilityRepository | None = None
        self._zone_repo: ZoneRepository | None = None
        self._session_factory = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._media_repo = MediaRepository(factory)
        self._audit_repo = AuditRepository(factory)
        self._audit_category_repo = AuditCheckpointCategoryRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self._zone_repo = ZoneRepository(factory)
        self._session_factory = factory
        Path(get_instance().storage_path).mkdir(parents=True, exist_ok=True)
        self.logger.info("[OK] MediaService initialized")

    def _close_service(self) -> None:
        self._media_repo = None
        self._audit_repo = None
        self._audit_category_repo = None
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
        audit_checkpoint_category_id: str,
        file_content: bytes,
        filename: str,
        content_type: str | None,
        payload: dict,
    ) -> MediaEvidenceResponse:
        if self._audit_repo is None or self._media_repo is None or self._audit_category_repo is None:
            raise RuntimeError("MediaService not initialized")
        from src.utils.validators import validate_image_filename, validate_image_content_type
        if not validate_image_filename(filename) or not validate_image_content_type(content_type):
            raise ValidationError("Invalid image file type")

        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)

        # Verify the category belongs to this audit and collect AI context
        audit_cp = await self._audit_category_repo.get_audit_checkpoint_for_category(audit_checkpoint_category_id)
        if not audit_cp or audit_cp.audit_id != audit_id:
            raise NotFoundError("AuditCheckpointCategory", audit_checkpoint_category_id)

        acc = await self._audit_category_repo.get_by_id(audit_checkpoint_category_id)
        if not acc:
            raise NotFoundError("AuditCheckpointCategory", audit_checkpoint_category_id)

        storage_path = get_instance().storage_path
        ext = Path(filename).suffix.lower() or ".jpg"
        safe_name = f"{audit_id}_{audit_checkpoint_category_id}_{uuid4().hex}{ext}"
        path = Path(storage_path) / safe_name
        path.write_bytes(file_content)

        media_row = await self._media_repo.create(audit_id, audit_checkpoint_category_id, str(path))

        # Fire-and-forget: run AI image analysis in background (non-blocking)
        asyncio.create_task(
            self._run_ai_analysis(
                media_id=media_row.id,
                image_path=str(path),
                checkpoint_name=audit_cp.checkpoint_name,
                reference_image_path=audit_cp.image_url,
                category_id=acc.category_id,
                category_name=acc.category_name,
                shift_type=audit.shift_type,
                shift_date=str(audit.shift_date),
            )
        )
        return media_row

    async def _run_ai_analysis(
        self,
        *,
        media_id: str,
        image_path: str,
        checkpoint_name: str,
        reference_image_path: str,
        category_id: str,
        category_name: str,
        shift_type: str,
        shift_date: str,
    ) -> None:
        """Background coroutine: fetch category description, call AI, persist result."""
        self.logger.info("[AI] Background analysis started for media %s (%s)", media_id, category_name)
        try:
            from src.business_services.ai_service import get_ai_service
            from src.database.postgres.schema.category_schema import CategorySchema
            from sqlalchemy import select

            if self._session_factory is None or self._media_repo is None:
                return

            # Fetch live category description (snapshot stores only name, not description)
            category_description: str | None = None
            async with self._session_factory() as session:
                cat_result = await session.execute(
                    select(CategorySchema).where(CategorySchema.id == category_id)
                )
                cat_row = cat_result.scalar_one_or_none()
                if cat_row:
                    category_description = cat_row.description

            ai_svc = get_ai_service()
            result = await ai_svc.analyze_image(
                image_path=image_path,
                checkpoint_name=checkpoint_name,
                category_name=category_name,
                category_description=category_description,
                shift_type=shift_type,
                shift_date=shift_date,
                reference_image_path=reference_image_path if Path(reference_image_path).exists() else None,
            )

            await self._media_repo.update_ai_result(
                media_id,
                ai_status=result.status,
                ai_compliant=result.compliant,
                ai_confidence=result.confidence,
                ai_observations=result.observations,
                ai_summary=result.summary,
                ai_analyzed_at=result.analyzed_at,
            )
            self.logger.info("[AI] Analysis %s for media %s", result.status, media_id)
        except Exception as exc:  # noqa: BLE001
            self.logger.error("[AI] Background analysis error for media %s: %s", media_id, exc)

    async def get_image_ai_result(self, image_id: str, payload: dict) -> MediaEvidenceResponse | None:
        """Return the current AI analysis state for a specific uploaded image."""
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
