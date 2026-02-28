from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.country_schema import CountrySchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.country_schema import (
    CountryCreate,
    CountryResponse,
    CountryUpdate,
)


class CountryRepository(BasePostgresRepository[CountrySchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, CountrySchema)

    def _schema_to_country(self, row: CountrySchema) -> CountryResponse:
        return CountryResponse.model_validate(row)

    async def get_by_id(self, id: str) -> CountryResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_country(row) if row else None

    async def get_by_code(self, code: str) -> CountryResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(CountrySchema).where(CountrySchema.code == code))
            row = result.scalar_one_or_none()
            return self._schema_to_country(row) if row else None

    async def list_countries(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[CountryResponse], int]:
        async with self._session_factory() as session:
            count_q = select(func.count()).select_from(CountrySchema)
            total = (await session.execute(count_q)).scalar() or 0
            order_col = getattr(CountrySchema, sort, CountrySchema.created_at)
            q = select(CountrySchema).order_by(
                order_col.desc() if order == "desc" else order_col.asc()
            ).offset(offset).limit(limit)
            result = await session.execute(q)
            rows = result.scalars().all()
        return [self._schema_to_country(r) for r in rows], total

    async def create(self, data: CountryCreate) -> CountryResponse:
        async with self._session_factory() as session:
            row = CountrySchema(
                id=str(uuid4()),
                name=data.name,
                code=data.code,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_country(row)

    async def update(self, id: str, data: CountryUpdate) -> CountryResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(CountrySchema).where(CountrySchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            if data.code is not None:
                row.code = data.code
            await session.commit()
            await session.refresh(row)
            return self._schema_to_country(row)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(CountrySchema).where(CountrySchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
