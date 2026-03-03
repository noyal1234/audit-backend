"""Facility-scoped hierarchy: areas, sub_areas, checkpoints."""

from src.api.dependencies import require_facility_access
from src.business_services.base import BaseBusinessService
from src.database.repositories.area_repository import AreaRepository
from src.database.repositories.checkpoint_repository import CheckpointRepository
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.sub_area_repository import SubAreaRepository
from src.database.repositories.schemas.area_schema import (
    AreaCreate,
    AreaResponse,
    AreaUpdate,
    AreaWithChildrenResponse,
    CheckpointCreate,
    CheckpointResponse,
    CheckpointUpdate,
    SubAreaCreate,
    SubAreaResponse,
    SubAreaUpdate,
)
from src.exceptions.domain_exceptions import ConflictError, NotFoundError, ValidationError


class TemplateService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._area_repo: AreaRepository | None = None
        self._sub_area_repo: SubAreaRepository | None = None
        self._checkpoint_repo: CheckpointRepository | None = None
        self._facility_repo: FacilityRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._area_repo = AreaRepository(factory)
        self._sub_area_repo = SubAreaRepository(factory)
        self._checkpoint_repo = CheckpointRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self.logger.info("[OK] TemplateService initialized")

    def _close_service(self) -> None:
        self._area_repo = None
        self._sub_area_repo = None
        self._checkpoint_repo = None
        self._facility_repo = None

    def _resolve_facility_id(self, payload: dict, explicit_facility_id: str | None = None) -> str:
        if explicit_facility_id:
            return explicit_facility_id
        fid = payload.get("facility_id")
        if fid:
            return fid
        raise ValidationError("facility_id is required")

    # --- Areas ---

    async def list_areas(self, payload: dict, facility_id: str | None = None) -> list[AreaResponse]:
        if self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        fid = self._resolve_facility_id(payload, facility_id)
        facility = await self._facility_repo.get_by_id(fid)
        if not facility:
            raise NotFoundError("Facility", fid)
        require_facility_access(fid, payload)
        return await self._area_repo.list_by_facility(fid)

    async def get_facility_hierarchy(self, payload: dict, facility_id: str) -> list[AreaWithChildrenResponse]:
        if self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        facility = await self._facility_repo.get_by_id(facility_id)
        if not facility:
            raise NotFoundError("Facility", facility_id)
        require_facility_access(facility_id, payload)
        return await self._area_repo.get_facility_hierarchy(facility_id)

    async def create_area(self, data: AreaCreate, payload: dict) -> AreaResponse:
        if self._area_repo is None or self._facility_repo is None:
            raise RuntimeError("TemplateService not initialized")
        fid = self._resolve_facility_id(payload, data.facility_id)
        facility = await self._facility_repo.get_by_id(fid)
        if not facility:
            raise NotFoundError("Facility", fid)
        require_facility_access(fid, payload)
        areas = await self._area_repo.list_by_facility(fid)
        if any(a.name == data.name for a in areas):
            raise ConflictError(f"Area '{data.name}' already exists in this facility")
        return await self._area_repo.create(AreaCreate(facility_id=fid, name=data.name))

    async def get_area(self, id: str, payload: dict) -> AreaResponse | None:
        if self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._area_repo.get_by_id(id)
        if not row:
            return None
        require_facility_access(row.facility_id, payload)
        return row

    async def update_area(self, id: str, data: AreaUpdate, payload: dict) -> AreaResponse | None:
        if self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._area_repo.get_by_id(id)
        if not row:
            return None
        require_facility_access(row.facility_id, payload)
        return await self._area_repo.update(id, data)

    async def delete_area(self, id: str, payload: dict) -> bool:
        if self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._area_repo.get_by_id(id)
        if not row:
            return False
        require_facility_access(row.facility_id, payload)
        return await self._area_repo.delete(id)

    # --- Sub-areas ---

    async def list_sub_areas(self, area_id: str, payload: dict) -> list[SubAreaResponse]:
        if self._sub_area_repo is None or self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        area = await self._area_repo.get_by_id(area_id)
        if not area:
            raise NotFoundError("Area", area_id)
        require_facility_access(area.facility_id, payload)
        return await self._sub_area_repo.list_by_area(area_id)

    async def create_sub_area(self, data: SubAreaCreate, payload: dict) -> SubAreaResponse:
        if self._sub_area_repo is None or self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        area = await self._area_repo.get_by_id(data.area_id)
        if not area:
            raise NotFoundError("Area", data.area_id)
        require_facility_access(area.facility_id, payload)
        existing = await self._sub_area_repo.list_by_area(data.area_id)
        if any(s.name == data.name for s in existing):
            raise ConflictError(f"Sub-area '{data.name}' already exists in this area")
        return await self._sub_area_repo.create(data)

    async def get_sub_area(self, id: str, payload: dict) -> SubAreaResponse | None:
        if self._sub_area_repo is None or self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._sub_area_repo.get_by_id(id)
        if not row:
            return None
        area = await self._area_repo.get_by_id(row.area_id)
        if not area:
            return None
        require_facility_access(area.facility_id, payload)
        return row

    async def update_sub_area(self, id: str, data: SubAreaUpdate, payload: dict) -> SubAreaResponse | None:
        if self._sub_area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._sub_area_repo.get_by_id(id)
        if not row:
            return None
        area = await self._area_repo.get_by_id(row.area_id)
        if not area:
            return None
        require_facility_access(area.facility_id, payload)
        return await self._sub_area_repo.update(id, data)

    async def delete_sub_area(self, id: str, payload: dict) -> bool:
        if self._sub_area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._sub_area_repo.get_by_id(id)
        if not row:
            return False
        area = await self._area_repo.get_by_id(row.area_id)
        if not area:
            return False
        require_facility_access(area.facility_id, payload)
        return await self._sub_area_repo.delete(id)

    # --- Checkpoints ---

    async def list_checkpoints(self, sub_area_id: str, payload: dict) -> list[CheckpointResponse]:
        if self._checkpoint_repo is None or self._sub_area_repo is None or self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        sub = await self._sub_area_repo.get_by_id(sub_area_id)
        if not sub:
            raise NotFoundError("SubArea", sub_area_id)
        area = await self._area_repo.get_by_id(sub.area_id)
        if not area:
            raise NotFoundError("Area", sub.area_id)
        require_facility_access(area.facility_id, payload)
        return await self._checkpoint_repo.list_by_sub_area(sub_area_id)

    async def create_checkpoint(self, data: CheckpointCreate, payload: dict) -> CheckpointResponse:
        if self._checkpoint_repo is None or self._sub_area_repo is None or self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        sub = await self._sub_area_repo.get_by_id(data.sub_area_id)
        if not sub:
            raise NotFoundError("SubArea", data.sub_area_id)
        area = await self._area_repo.get_by_id(sub.area_id)
        if not area:
            raise NotFoundError("Area", sub.area_id)
        require_facility_access(area.facility_id, payload)
        existing = await self._checkpoint_repo.list_by_sub_area(data.sub_area_id)
        if any(c.name == data.name for c in existing):
            raise ConflictError(f"Checkpoint '{data.name}' already exists in this sub-area")
        return await self._checkpoint_repo.create(data)

    async def get_checkpoint(self, id: str, payload: dict) -> CheckpointResponse | None:
        if self._checkpoint_repo is None or self._sub_area_repo is None or self._area_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._checkpoint_repo.get_by_id(id)
        if not row:
            return None
        sub = await self._sub_area_repo.get_by_id(row.sub_area_id)
        if not sub:
            return None
        area = await self._area_repo.get_by_id(sub.area_id)
        if not area:
            return None
        require_facility_access(area.facility_id, payload)
        return row

    async def update_checkpoint(self, id: str, data: CheckpointUpdate, payload: dict) -> CheckpointResponse | None:
        if self._checkpoint_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._checkpoint_repo.get_by_id(id)
        if not row:
            return None
        sub = await self._sub_area_repo.get_by_id(row.sub_area_id)
        if not sub:
            return None
        area = await self._area_repo.get_by_id(sub.area_id)
        if not area:
            return None
        require_facility_access(area.facility_id, payload)
        return await self._checkpoint_repo.update(id, data)

    async def delete_checkpoint(self, id: str, payload: dict) -> bool:
        if self._checkpoint_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._checkpoint_repo.get_by_id(id)
        if not row:
            return False
        sub = await self._sub_area_repo.get_by_id(row.sub_area_id)
        if not sub:
            return False
        area = await self._area_repo.get_by_id(sub.area_id)
        if not area:
            return False
        require_facility_access(area.facility_id, payload)
        return await self._checkpoint_repo.delete(id)


_template_service: TemplateService | None = None


def get_template_service() -> TemplateService:
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service
