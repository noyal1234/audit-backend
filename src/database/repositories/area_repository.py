from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload

from src.database.postgres.schema.area_schema import AreaSchema
from src.database.postgres.schema.sub_area_schema import SubAreaSchema
from src.database.postgres.schema.checkpoint_schema import CheckpointSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.area_schema import (
    AreaCreate,
    AreaResponse,
    AreaUpdate,
    AreaWithChildrenResponse,
    CheckpointResponse,
    SubAreaWithCheckpointsResponse,
)


class AreaRepository(BasePostgresRepository[AreaSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, AreaSchema)

    async def create(self, data: AreaCreate) -> AreaResponse:
        async with self._session_factory() as session:
            row = AreaSchema(id=str(uuid4()), facility_id=data.facility_id, name=data.name)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return AreaResponse.model_validate(row)

    async def get_by_id(self, id: str) -> AreaResponse | None:
        row = await self._get_by_id_raw(id)
        return AreaResponse.model_validate(row) if row else None

    async def list_by_facility(self, facility_id: str) -> list[AreaResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AreaSchema).where(AreaSchema.facility_id == facility_id).order_by(AreaSchema.name)
            )
            rows = result.scalars().all()
        return [AreaResponse.model_validate(r) for r in rows]

    async def get_facility_hierarchy(self, facility_id: str) -> list[AreaWithChildrenResponse]:
        """Load full tree: areas -> sub_areas -> checkpoints for snapshot creation."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AreaSchema)
                .options(
                    selectinload(AreaSchema.sub_areas).selectinload(SubAreaSchema.checkpoints)
                )
                .where(AreaSchema.facility_id == facility_id)
                .order_by(AreaSchema.name)
            )
            areas = result.scalars().unique().all()
        out = []
        for a in areas:
            sub_areas_out = []
            for sa in sorted(a.sub_areas, key=lambda x: x.name):
                checkpoints = [CheckpointResponse.model_validate(c) for c in sorted(sa.checkpoints, key=lambda x: x.name)]
                sub_areas_out.append(SubAreaWithCheckpointsResponse(
                    id=sa.id,
                    area_id=sa.area_id,
                    name=sa.name,
                    created_at=sa.created_at,
                    checkpoints=checkpoints,
                ))
            out.append(AreaWithChildrenResponse(
                id=a.id,
                facility_id=a.facility_id,
                name=a.name,
                created_at=a.created_at,
                sub_areas=sub_areas_out,
            ))
        return out

    async def update(self, id: str, data: AreaUpdate) -> AreaResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(AreaSchema).where(AreaSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            await session.commit()
            await session.refresh(row)
            return AreaResponse.model_validate(row)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(AreaSchema).where(AreaSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
