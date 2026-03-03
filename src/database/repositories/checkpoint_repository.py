"""Checkpoint under sub_area (new hierarchy)."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.checkpoint_schema import CheckpointSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.area_schema import (
    CheckpointCreate,
    CheckpointResponse,
    CheckpointUpdate,
)


class CheckpointRepository(BasePostgresRepository[CheckpointSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, CheckpointSchema)

    async def create(self, data: CheckpointCreate) -> CheckpointResponse:
        async with self._session_factory() as session:
            row = CheckpointSchema(
                id=str(uuid4()),
                sub_area_id=data.sub_area_id,
                name=data.name,
                description=data.description,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return CheckpointResponse.model_validate(row)

    async def get_by_id(self, id: str) -> CheckpointResponse | None:
        row = await self._get_by_id_raw(id)
        return CheckpointResponse.model_validate(row) if row else None

    async def list_by_sub_area(self, sub_area_id: str) -> list[CheckpointResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(CheckpointSchema).where(CheckpointSchema.sub_area_id == sub_area_id).order_by(CheckpointSchema.name)
            )
            rows = result.scalars().all()
        return [CheckpointResponse.model_validate(r) for r in rows]

    async def update(self, id: str, data: CheckpointUpdate) -> CheckpointResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(CheckpointSchema).where(CheckpointSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            if data.description is not None:
                row.description = data.description
            await session.commit()
            await session.refresh(row)
            return CheckpointResponse.model_validate(row)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(CheckpointSchema).where(CheckpointSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
