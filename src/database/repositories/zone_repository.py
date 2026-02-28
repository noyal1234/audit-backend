from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.postgres.schema.zone_schema import ZoneSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.company_schema import (
    ZoneCreate,
    ZoneResponse,
    ZoneUpdate,
)


class ZoneRepository(BasePostgresRepository[ZoneSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, ZoneSchema)

    def _schema_to_zone(self, row: ZoneSchema) -> ZoneResponse:
        return ZoneResponse.model_validate(row)

    async def get_by_id(self, id: str) -> ZoneResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_zone(row) if row else None

    async def list_zones(
        self,
        *,
        country_id: str | None = None,
        zone_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[ZoneResponse], int]:
        async with self._session_factory() as session:
            q = select(ZoneSchema)
            count_q = select(func.count()).select_from(ZoneSchema)
            if zone_id:
                q = q.where(ZoneSchema.id == zone_id)
                count_q = count_q.where(ZoneSchema.id == zone_id)
            if country_id:
                q = q.where(ZoneSchema.country_id == country_id)
                count_q = count_q.where(ZoneSchema.country_id == country_id)
            total = (await session.execute(count_q)).scalar() or 0
            order_col = getattr(ZoneSchema, sort, ZoneSchema.created_at)
            q = q.order_by(order_col.desc() if order == "desc" else order_col.asc())
            q = q.offset(offset).limit(limit)
            result = await session.execute(q)
            rows = result.scalars().all()
        return [self._schema_to_zone(r) for r in rows], total

    async def create(self, data: ZoneCreate) -> ZoneResponse:
        async with self._session_factory() as session:
            row = ZoneSchema(
                id=str(uuid4()),
                name=data.name,
                country_id=data.country_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_zone(row)

    async def update(self, id: str, data: ZoneUpdate) -> ZoneResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(ZoneSchema).where(ZoneSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            if data.country_id is not None:
                row.country_id = data.country_id
            await session.commit()
            await session.refresh(row)
            return self._schema_to_zone(row)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(ZoneSchema).where(ZoneSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
