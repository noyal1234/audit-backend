"""Facility-scoped categories, checkpoints, and checkpoint-category assignments."""

from pathlib import Path
from uuid import uuid4

from src.api.dependencies import require_facility_access
from src.business_services.base import BaseBusinessService
from src.configs.settings import get_instance
from src.database.repositories.category_repository import CategoryRepository
from src.database.repositories.checkpoint_category_repository import CheckpointCategoryRepository
from src.database.repositories.checkpoint_repository import CheckpointRepository
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.schemas.template_schema import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    CheckpointCategoryCreate,
    CheckpointCategoryResponse,
    CheckpointCreate,
    CheckpointResponse,
    CheckpointUpdate,
)
from src.exceptions.domain_exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from src.utils.pagination import PaginatedResponse, PaginationParams
from src.utils.validators import validate_image_content_type, validate_image_filename


class TemplateService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._category_repo: CategoryRepository | None = None
        self._checkpoint_repo: CheckpointRepository | None = None
        self._checkpoint_category_repo: CheckpointCategoryRepository | None = None
        self._facility_repo: FacilityRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._category_repo = CategoryRepository(factory)
        self._checkpoint_repo = CheckpointRepository(factory)
        self._checkpoint_category_repo = CheckpointCategoryRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self.logger.info("[OK] TemplateService initialized")

    def _close_service(self) -> None:
        self._category_repo = None
        self._checkpoint_repo = None
        self._checkpoint_category_repo = None
        self._facility_repo = None

    def _resolve_facility_id(self, payload: dict, explicit_facility_id: str | None = None) -> str:
        """Resolve facility_id: DEALERSHIP/EMPLOYEE use their own; higher roles must supply one."""
        if explicit_facility_id:
            return explicit_facility_id
        fid = payload.get("facility_id")
        if fid:
            return fid
        raise ValidationError("facility_id is required")

    # --- Categories ---

    async def create_category(self, data: CategoryCreate, payload: dict) -> CategoryResponse:
        if self._category_repo is None or self._facility_repo is None:
            raise RuntimeError("TemplateService not initialized")
        facility_id = self._resolve_facility_id(payload, data.facility_id)
        facility = await self._facility_repo.get_by_id(facility_id)
        if not facility:
            raise NotFoundError("Facility", facility_id)
        require_facility_access(facility_id, payload)
        existing = await self._category_repo.get_by_facility_and_name(facility_id, data.name)
        if existing:
            raise ConflictError(f"Category '{data.name}' already exists in this facility")
        create_data = CategoryCreate(facility_id=facility_id, name=data.name, description=data.description)
        return await self._category_repo.create(create_data)

    async def get_category(self, id: str, payload: dict) -> CategoryResponse | None:
        if self._category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        cat = await self._category_repo.get_by_id(id)
        if not cat:
            return None
        require_facility_access(cat.facility_id, payload)
        return cat

    async def list_categories(
        self,
        payload: dict,
        facility_id: str | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[CategoryResponse]:
        if self._category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        params = params or PaginationParams()
        effective_facility = facility_id or payload.get("facility_id")
        items, total = await self._category_repo.list_categories(
            facility_id=effective_facility,
            offset=params.offset,
            limit=params.limit,
            sort=params.sort,
            order=params.order,
        )
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def update_category(self, id: str, data: CategoryUpdate, payload: dict) -> CategoryResponse | None:
        if self._category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        cat = await self._category_repo.get_by_id(id)
        if not cat:
            return None
        require_facility_access(cat.facility_id, payload)
        if data.name is not None and data.name != cat.name:
            existing = await self._category_repo.get_by_facility_and_name(cat.facility_id, data.name)
            if existing:
                raise ConflictError(f"Category '{data.name}' already exists in this facility")
        return await self._category_repo.update(id, data)

    async def delete_category(self, id: str, payload: dict) -> bool:
        if self._category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        cat = await self._category_repo.get_by_id(id)
        if not cat:
            return False
        require_facility_access(cat.facility_id, payload)
        return await self._category_repo.delete(id)

    # --- Checkpoints ---

    async def create_checkpoint(
        self,
        name: str,
        file_content: bytes,
        filename: str,
        content_type: str | None,
        payload: dict,
        facility_id: str | None = None,
    ) -> CheckpointResponse:
        if self._checkpoint_repo is None or self._facility_repo is None:
            raise RuntimeError("TemplateService not initialized")
        fid = self._resolve_facility_id(payload, facility_id)
        facility = await self._facility_repo.get_by_id(fid)
        if not facility:
            raise NotFoundError("Facility", fid)
        require_facility_access(fid, payload)
        if not file_content:
            raise ValidationError("Image file is required when creating a checkpoint")
        if not validate_image_filename(filename) or not validate_image_content_type(content_type):
            raise ValidationError("Invalid image file type")
        storage_path = get_instance().storage_path
        Path(storage_path).mkdir(parents=True, exist_ok=True)
        ext = Path(filename).suffix.lower() or ".jpg"
        safe_name = f"checkpoint_{uuid4().hex}{ext}"
        path = Path(storage_path) / safe_name
        path.write_bytes(file_content)
        image_url = str(path)
        create_data = CheckpointCreate(facility_id=fid, name=name, image_url=image_url)
        return await self._checkpoint_repo.create(create_data)

    async def get_checkpoint(self, id: str, payload: dict) -> CheckpointResponse | None:
        if self._checkpoint_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._checkpoint_repo.get_by_id(id)
        if not row:
            return None
        require_facility_access(row.facility_id, payload)
        return row

    async def list_checkpoints(
        self,
        payload: dict,
        facility_id: str | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[CheckpointResponse]:
        if self._checkpoint_repo is None:
            raise RuntimeError("TemplateService not initialized")
        params = params or PaginationParams()
        effective_facility = facility_id or payload.get("facility_id")
        items, total = await self._checkpoint_repo.list_checkpoints(
            facility_id=effective_facility,
            offset=params.offset,
            limit=params.limit,
            sort=params.sort,
            order=params.order,
        )
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def update_checkpoint(self, id: str, data: CheckpointUpdate, payload: dict) -> CheckpointResponse | None:
        if self._checkpoint_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._checkpoint_repo.get_by_id(id)
        if not row:
            return None
        require_facility_access(row.facility_id, payload)
        return await self._checkpoint_repo.update(id, data)

    async def delete_checkpoint(self, id: str, payload: dict) -> bool:
        if self._checkpoint_repo is None:
            raise RuntimeError("TemplateService not initialized")
        row = await self._checkpoint_repo.get_by_id(id)
        if not row:
            return False
        require_facility_access(row.facility_id, payload)
        return await self._checkpoint_repo.delete(id)

    # --- Checkpoint-Category assignments ---

    async def assign_category_to_checkpoint(
        self, checkpoint_id: str, data: CheckpointCategoryCreate, payload: dict
    ) -> CheckpointCategoryResponse:
        if self._checkpoint_repo is None or self._category_repo is None or self._checkpoint_category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        checkpoint = await self._checkpoint_repo.get_by_id(checkpoint_id)
        if not checkpoint:
            raise NotFoundError("Checkpoint", checkpoint_id)
        require_facility_access(checkpoint.facility_id, payload)
        category = await self._category_repo.get_by_id(data.category_id)
        if not category:
            raise NotFoundError("Category", data.category_id)
        if category.facility_id != checkpoint.facility_id:
            raise ForbiddenError("Category and checkpoint must belong to the same facility")
        existing = await self._checkpoint_category_repo.find_link(checkpoint_id, data.category_id)
        if existing:
            raise ConflictError("Category already assigned to this checkpoint")
        return await self._checkpoint_category_repo.assign(checkpoint_id, data.category_id)

    async def list_checkpoint_categories(self, checkpoint_id: str, payload: dict) -> list[CategoryResponse]:
        if self._checkpoint_repo is None or self._checkpoint_category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        checkpoint = await self._checkpoint_repo.get_by_id(checkpoint_id)
        if not checkpoint:
            raise NotFoundError("Checkpoint", checkpoint_id)
        require_facility_access(checkpoint.facility_id, payload)
        return await self._checkpoint_category_repo.list_categories_for_checkpoint(checkpoint_id)

    async def remove_category_from_checkpoint(
        self, checkpoint_id: str, category_id: str, payload: dict
    ) -> bool:
        if self._checkpoint_repo is None or self._checkpoint_category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        checkpoint = await self._checkpoint_repo.get_by_id(checkpoint_id)
        if not checkpoint:
            raise NotFoundError("Checkpoint", checkpoint_id)
        require_facility_access(checkpoint.facility_id, payload)
        return await self._checkpoint_category_repo.remove(checkpoint_id, category_id)


_template_service: TemplateService | None = None


def get_template_service() -> TemplateService:
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service
