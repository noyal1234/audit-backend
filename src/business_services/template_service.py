"""Checklist config: categories, subcategories, checkpoints. Enforces hierarchy for checkpoints."""

from src.api.dependencies import require_facility_access
from src.business_services.base import BaseBusinessService
from src.database.repositories.category_repository import CategoryRepository
from src.database.repositories.checkpoint_repository import CheckpointRepository
from src.database.repositories.facility_repository import FacilityRepository
from src.database.repositories.subcategory_repository import SubcategoryRepository
from src.database.repositories.schemas.template_schema import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    CheckpointCreate,
    CheckpointResponse,
    CheckpointUpdate,
    SubcategoryCreate,
    SubcategoryResponse,
    SubcategoryUpdate,
)
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginatedResponse, PaginationParams


class TemplateService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._category_repo: CategoryRepository | None = None
        self._subcategory_repo: SubcategoryRepository | None = None
        self._checkpoint_repo: CheckpointRepository | None = None
        self._facility_repo: FacilityRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._category_repo = CategoryRepository(factory)
        self._subcategory_repo = SubcategoryRepository(factory)
        self._checkpoint_repo = CheckpointRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self.logger.info("[OK] TemplateService initialized")

    def _close_service(self) -> None:
        self._category_repo = None
        self._subcategory_repo = None
        self._checkpoint_repo = None
        self._facility_repo = None

    async def get_category(self, id: str, payload: dict) -> CategoryResponse | None:
        if self._category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        return await self._category_repo.get_by_id(id)

    async def list_categories(
        self,
        payload: dict,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[CategoryResponse]:
        if self._category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        params = params or PaginationParams()
        items, total = await self._category_repo.list_categories(
            offset=params.offset,
            limit=params.limit,
            sort=params.sort,
            order=params.order,
        )
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def create_category(self, data: CategoryCreate, payload: dict) -> CategoryResponse:
        if self._category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        return await self._category_repo.create(data)

    async def update_category(self, id: str, data: CategoryUpdate, payload: dict) -> CategoryResponse | None:
        if self._category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        return await self._category_repo.update(id, data)

    async def delete_category(self, id: str, payload: dict) -> bool:
        if self._category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        return await self._category_repo.delete(id)

    async def get_subcategory(self, id: str, payload: dict) -> SubcategoryResponse | None:
        if self._subcategory_repo is None:
            raise RuntimeError("TemplateService not initialized")
        return await self._subcategory_repo.get_by_id(id)

    async def list_subcategories(
        self,
        payload: dict,
        category_id: str | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[SubcategoryResponse]:
        if self._subcategory_repo is None:
            raise RuntimeError("TemplateService not initialized")
        params = params or PaginationParams()
        items, total = await self._subcategory_repo.list_subcategories(
            category_id=category_id,
            offset=params.offset,
            limit=params.limit,
            sort=params.sort,
            order=params.order,
        )
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def create_subcategory(self, data: SubcategoryCreate, payload: dict) -> SubcategoryResponse:
        if self._subcategory_repo is None or self._category_repo is None:
            raise RuntimeError("TemplateService not initialized")
        category = await self._category_repo.get_by_id(data.category_id)
        if not category:
            raise NotFoundError("Category", data.category_id)
        return await self._subcategory_repo.create(data)

    async def update_subcategory(self, id: str, data: SubcategoryUpdate, payload: dict) -> SubcategoryResponse | None:
        if self._subcategory_repo is None:
            raise RuntimeError("TemplateService not initialized")
        return await self._subcategory_repo.update(id, data)

    async def delete_subcategory(self, id: str, payload: dict) -> bool:
        if self._subcategory_repo is None:
            raise RuntimeError("TemplateService not initialized")
        return await self._subcategory_repo.delete(id)

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
        subcategory_id: str | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[CheckpointResponse]:
        if self._checkpoint_repo is None:
            raise RuntimeError("TemplateService not initialized")
        params = params or PaginationParams()
        if payload.get("role_type") != "SUPER_ADMIN" and payload.get("facility_id"):
            facility_id = facility_id or payload.get("facility_id")
        items, total = await self._checkpoint_repo.list_checkpoints(
            facility_id=facility_id,
            subcategory_id=subcategory_id,
            offset=params.offset,
            limit=params.limit,
            sort=params.sort,
            order=params.order,
        )
        if payload.get("role_type") != "SUPER_ADMIN" and payload.get("facility_id"):
            items = [i for i in items if i.facility_id == payload["facility_id"]]
            total = len(items)
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def create_checkpoint(self, data: CheckpointCreate, payload: dict) -> CheckpointResponse:
        if self._checkpoint_repo is None or self._subcategory_repo is None or self._facility_repo is None:
            raise RuntimeError("TemplateService not initialized")
        subcategory = await self._subcategory_repo.get_by_id(data.subcategory_id)
        if not subcategory:
            raise NotFoundError("Subcategory", data.subcategory_id)
        facility = await self._facility_repo.get_by_id(data.facility_id)
        if not facility:
            raise NotFoundError("Facility", data.facility_id)
        require_facility_access(data.facility_id, payload)
        return await self._checkpoint_repo.create(data)

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


_template_service: TemplateService | None = None


def get_template_service() -> TemplateService:
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service
