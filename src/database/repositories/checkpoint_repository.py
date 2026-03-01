from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload

from src.database.postgres.schema.category_schema import CategorySchema
from src.database.postgres.schema.checkpoint_category_schema import CheckpointCategorySchema
from src.database.postgres.schema.checkpoint_schema import CheckpointSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.template_schema import (
    CategoryResponse,
    CheckpointCreate,
    CheckpointResponse,
    CheckpointUpdate,
)


class CheckpointRepository(BasePostgresRepository[CheckpointSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, CheckpointSchema)

    def _schema_to_checkpoint(self, row: CheckpointSchema, categories: list[CategoryResponse] | None = None) -> CheckpointResponse:
        return CheckpointResponse(
            id=row.id,
            facility_id=row.facility_id,
            name=row.name,
            image_url=row.image_url,
            created_at=row.created_at,
            updated_at=row.updated_at,
            categories=categories or [],
        )

    async def get_by_id(self, id: str) -> CheckpointResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CheckpointSchema)
                .options(selectinload(CheckpointSchema.category_links).selectinload(CheckpointCategorySchema.category))
                .where(CheckpointSchema.id == id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            cats = [
                CategoryResponse.model_validate(link.category)
                for link in row.category_links if link.category
            ]
            return self._schema_to_checkpoint(row, cats)

    async def get_by_facility_and_name(self, facility_id: str, name: str) -> CheckpointResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CheckpointSchema).where(
                    CheckpointSchema.facility_id == facility_id,
                    CheckpointSchema.name == name,
                )
            )
            row = result.scalar_one_or_none()
        return self._schema_to_checkpoint(row) if row else None

    async def list_checkpoints(
        self,
        *,
        facility_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[CheckpointResponse], int]:
        async with self._session_factory() as session:
            count_q = select(func.count()).select_from(CheckpointSchema)
            if facility_id:
                count_q = count_q.where(CheckpointSchema.facility_id == facility_id)
            total = (await session.execute(count_q)).scalar() or 0

            q = (
                select(CheckpointSchema)
                .options(selectinload(CheckpointSchema.category_links).selectinload(CheckpointCategorySchema.category))
            )
            if facility_id:
                q = q.where(CheckpointSchema.facility_id == facility_id)
            order_col = getattr(CheckpointSchema, sort, CheckpointSchema.created_at)
            q = q.order_by(order_col.desc() if order == "desc" else order_col.asc())
            q = q.offset(offset).limit(limit)
            result = await session.execute(q)
            rows = result.scalars().unique().all()

        items = []
        for row in rows:
            cats = [
                CategoryResponse.model_validate(link.category)
                for link in row.category_links if link.category
            ]
            items.append(self._schema_to_checkpoint(row, cats))
        return items, total

    async def create(self, data: CheckpointCreate) -> CheckpointResponse:
        async with self._session_factory() as session:
            row = CheckpointSchema(
                id=str(uuid4()),
                facility_id=data.facility_id,
                name=data.name,
                image_url=data.image_url,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_checkpoint(row)

    async def update(self, id: str, data: CheckpointUpdate) -> CheckpointResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CheckpointSchema)
                .options(selectinload(CheckpointSchema.category_links).selectinload(CheckpointCategorySchema.category))
                .where(CheckpointSchema.id == id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            if data.image_url is not None:
                row.image_url = data.image_url
            await session.commit()
            await session.refresh(row)
            cats = [
                CategoryResponse.model_validate(link.category)
                for link in row.category_links if link.category
            ]
            return self._schema_to_checkpoint(row, cats)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(CheckpointSchema).where(CheckpointSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
