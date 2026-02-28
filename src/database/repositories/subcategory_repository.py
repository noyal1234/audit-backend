from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.category_schema import SubcategorySchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.template_schema import (
    SubcategoryCreate,
    SubcategoryResponse,
    SubcategoryUpdate,
)


class SubcategoryRepository(BasePostgresRepository[SubcategorySchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, SubcategorySchema)

    def _schema_to_subcategory(self, row: SubcategorySchema) -> SubcategoryResponse:
        return SubcategoryResponse.model_validate(row)

    async def get_by_id(self, id: str) -> SubcategoryResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_subcategory(row) if row else None

    async def list_subcategories(
        self,
        *,
        category_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[SubcategoryResponse], int]:
        async with self._session_factory() as session:
            q = select(SubcategorySchema)
            count_q = select(func.count()).select_from(SubcategorySchema)
            if category_id:
                q = q.where(SubcategorySchema.category_id == category_id)
                count_q = count_q.where(SubcategorySchema.category_id == category_id)
            total = (await session.execute(count_q)).scalar() or 0
            order_col = getattr(SubcategorySchema, sort, SubcategorySchema.created_at)
            q = q.order_by(order_col.desc() if order == "desc" else order_col.asc())
            q = q.offset(offset).limit(limit)
            result = await session.execute(q)
            rows = result.scalars().all()
        return [self._schema_to_subcategory(r) for r in rows], total

    async def create(self, data: SubcategoryCreate) -> SubcategoryResponse:
        async with self._session_factory() as session:
            row = SubcategorySchema(
                id=str(uuid4()),
                category_id=data.category_id,
                name=data.name,
                description=data.description,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_subcategory(row)

    async def update(self, id: str, data: SubcategoryUpdate) -> SubcategoryResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(SubcategorySchema).where(SubcategorySchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            if data.description is not None:
                row.description = data.description
            if data.category_id is not None:
                row.category_id = data.category_id
            await session.commit()
            await session.refresh(row)
            return self._schema_to_subcategory(row)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(SubcategorySchema).where(SubcategorySchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
