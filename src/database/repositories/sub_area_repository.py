from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.sub_area_schema import SubAreaSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.area_schema import SubAreaCreate, SubAreaResponse, SubAreaUpdate


class SubAreaRepository(BasePostgresRepository[SubAreaSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, SubAreaSchema)

    async def create(self, data: SubAreaCreate) -> SubAreaResponse:
        async with self._session_factory() as session:
            row = SubAreaSchema(id=str(uuid4()), area_id=data.area_id, name=data.name)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return SubAreaResponse.model_validate(row)

    async def get_by_id(self, id: str) -> SubAreaResponse | None:
        row = await self._get_by_id_raw(id)
        return SubAreaResponse.model_validate(row) if row else None

    async def list_by_area(self, area_id: str) -> list[SubAreaResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(SubAreaSchema).where(SubAreaSchema.area_id == area_id).order_by(SubAreaSchema.name)
            )
            rows = result.scalars().all()
        return [SubAreaResponse.model_validate(r) for r in rows]

    async def update(self, id: str, data: SubAreaUpdate) -> SubAreaResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(SubAreaSchema).where(SubAreaSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            await session.commit()
            await session.refresh(row)
            return SubAreaResponse.model_validate(row)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(SubAreaSchema).where(SubAreaSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
