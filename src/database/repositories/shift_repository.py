from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.shift_schema import ShiftConfigSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.shift_schema import (
    ShiftConfigCreate,
    ShiftConfigResponse,
    ShiftConfigUpdate,
)


class ShiftRepository(BasePostgresRepository[ShiftConfigSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, ShiftConfigSchema)

    def _schema_to_shift(self, row: ShiftConfigSchema) -> ShiftConfigResponse:
        return ShiftConfigResponse.model_validate(row)

    async def get_by_id(self, id: str) -> ShiftConfigResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_shift(row) if row else None

    async def list_all(self) -> list[ShiftConfigResponse]:
        async with self._session_factory() as session:
            result = await session.execute(select(ShiftConfigSchema).order_by(ShiftConfigSchema.start_time))
            rows = result.scalars().all()
        return [self._schema_to_shift(r) for r in rows]

    async def create(self, data: ShiftConfigCreate) -> ShiftConfigResponse:
        async with self._session_factory() as session:
            row = ShiftConfigSchema(
                id=str(uuid4()),
                name=data.name,
                start_time=data.start_time,
                end_time=data.end_time,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_shift(row)

    async def update(self, id: str, data: ShiftConfigUpdate) -> ShiftConfigResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(ShiftConfigSchema).where(ShiftConfigSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            if data.start_time is not None:
                row.start_time = data.start_time
            if data.end_time is not None:
                row.end_time = data.end_time
            await session.commit()
            await session.refresh(row)
            return self._schema_to_shift(row)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(ShiftConfigSchema).where(ShiftConfigSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
