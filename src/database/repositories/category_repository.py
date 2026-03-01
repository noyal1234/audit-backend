from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.category_schema import CategorySchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.template_schema import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)


class CategoryRepository(BasePostgresRepository[CategorySchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, CategorySchema)

    def _schema_to_category(self, row: CategorySchema) -> CategoryResponse:
        return CategoryResponse.model_validate(row)

    async def get_by_id(self, id: str) -> CategoryResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_category(row) if row else None

    async def get_by_facility_and_name(self, facility_id: str, name: str) -> CategoryResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CategorySchema).where(
                    CategorySchema.facility_id == facility_id,
                    CategorySchema.name == name,
                )
            )
            row = result.scalar_one_or_none()
        return self._schema_to_category(row) if row else None

    async def list_categories(
        self,
        *,
        facility_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[CategoryResponse], int]:
        async with self._session_factory() as session:
            q = select(CategorySchema)
            count_q = select(func.count()).select_from(CategorySchema)
            if facility_id:
                q = q.where(CategorySchema.facility_id == facility_id)
                count_q = count_q.where(CategorySchema.facility_id == facility_id)
            total = (await session.execute(count_q)).scalar() or 0
            order_col = getattr(CategorySchema, sort, CategorySchema.created_at)
            q = q.order_by(order_col.desc() if order == "desc" else order_col.asc())
            q = q.offset(offset).limit(limit)
            result = await session.execute(q)
            rows = result.scalars().all()
        return [self._schema_to_category(r) for r in rows], total

    async def create(self, data: CategoryCreate) -> CategoryResponse:
        async with self._session_factory() as session:
            row = CategorySchema(
                id=str(uuid4()),
                facility_id=data.facility_id,
                name=data.name,
                description=data.description,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_category(row)

    async def update(self, id: str, data: CategoryUpdate) -> CategoryResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(CategorySchema).where(CategorySchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            if data.description is not None:
                row.description = data.description
            await session.commit()
            await session.refresh(row)
            return self._schema_to_category(row)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(CategorySchema).where(CategorySchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
