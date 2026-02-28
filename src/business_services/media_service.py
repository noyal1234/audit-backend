"""Media storage and listing. Local path for now."""

from pathlib import Path
from uuid import uuid4

from src.api.dependencies import require_country_access, require_facility_access
from src.database.repositories.audit_repository import AuditRepository
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
        self._facility_repo: FacilityRepository | None = None
        self._zone_repo: ZoneRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._media_repo = MediaRepository(factory)
        self._audit_repo = AuditRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self._zone_repo = ZoneRepository(factory)
        Path(get_instance().storage_path).mkdir(parents=True, exist_ok=True)
        self.logger.info("[OK] MediaService initialized")

    def _close_service(self) -> None:
        self._media_repo = None
        self._audit_repo = None
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

    async def save_upload(
        self,
        audit_id: str,
        checkpoint_id: str,
        file_content: bytes,
        filename: str,
        content_type: str | None,
        payload: dict,
    ) -> MediaEvidenceResponse:
        if self._audit_repo is None or self._media_repo is None:
            raise RuntimeError("MediaService not initialized")
        from src.utils.validators import validate_image_filename, validate_image_content_type
        if not validate_image_filename(filename) or not validate_image_content_type(content_type):
            raise ValidationError("Invalid image file type")
        audit = await self._audit_repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit", audit_id)
        require_facility_access(audit.facility_id, payload)
        await self._ensure_facility_in_country(audit.facility_id, payload)
        storage_path = get_instance().storage_path
        ext = Path(filename).suffix.lower() or ".jpg"
        safe_name = f"{audit_id}_{checkpoint_id}_{uuid4().hex}{ext}"
        path = Path(storage_path) / safe_name
        path.write_bytes(file_content)
        return await self._media_repo.create(audit_id, checkpoint_id, str(path))

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
