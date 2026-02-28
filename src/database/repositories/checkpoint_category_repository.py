from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload

from src.database.postgres.schema.category_schema import CategorySchema
from src.database.postgres.schema.checkpoint_category_schema import CheckpointCategorySchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.template_schema import (
    CategoryResponse,
    CheckpointCategoryResponse,
)


class CheckpointCategoryRepository(BasePostgresRepository[CheckpointCategorySchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, CheckpointCategorySchema)

    async def assign(self, checkpoint_id: str, category_id: str) -> CheckpointCategoryResponse:
        async with self._session_factory() as session:
            row = CheckpointCategorySchema(
                id=str(uuid4()),
                checkpoint_id=checkpoint_id,
                category_id=category_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return CheckpointCategoryResponse.model_validate(row)

    async def find_link(self, checkpoint_id: str, category_id: str) -> CheckpointCategoryResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CheckpointCategorySchema).where(
                    CheckpointCategorySchema.checkpoint_id == checkpoint_id,
                    CheckpointCategorySchema.category_id == category_id,
                )
            )
            row = result.scalar_one_or_none()
        return CheckpointCategoryResponse.model_validate(row) if row else None

    async def remove(self, checkpoint_id: str, category_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CheckpointCategorySchema).where(
                    CheckpointCategorySchema.checkpoint_id == checkpoint_id,
                    CheckpointCategorySchema.category_id == category_id,
                )
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def list_categories_for_checkpoint(self, checkpoint_id: str) -> list[CategoryResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CheckpointCategorySchema)
                .options(selectinload(CheckpointCategorySchema.category))
                .where(CheckpointCategorySchema.checkpoint_id == checkpoint_id)
            )
            rows = result.scalars().all()
        return [CategoryResponse.model_validate(r.category) for r in rows if r.category]
