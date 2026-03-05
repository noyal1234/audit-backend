from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.facility_schema import FacilitySchema
from src.database.postgres.schema.zone_schema import ZoneSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.dealer_schema import (
    CountryMini,
    FacilityCreate,
    FacilityResponse,
    FacilityUpdate,
    ZoneMini,
)


class FacilityRepository(BasePostgresRepository[FacilitySchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, FacilitySchema)

    def _row_to_facility_response(self, row: FacilitySchema) -> FacilityResponse:
        zone_mini: ZoneMini | None = None
        if getattr(row, "zone", None) and row.zone is not None:
            country_mini = None
            if getattr(row.zone, "country", None) and row.zone.country is not None:
                country_mini = CountryMini(id=row.zone.country.id, name=row.zone.country.name)
            zone_mini = ZoneMini(
                id=row.zone.id,
                name=row.zone.name,
                country=country_mini,
            )
        return FacilityResponse(
            id=row.id,
            zone_id=row.zone_id,
            zone=zone_mini,
            user_id=row.user_id,
            name=row.name,
            code=row.code,
            address=row.address,
            dealer_name=row.dealer_name,
            dealer_phone=row.dealer_phone,
            dealer_email=row.dealer_email,
            dealer_designation=row.dealer_designation,
            timezone=getattr(row, "timezone", "Asia/Kolkata"),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_id(self, id: str) -> FacilityResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(FacilitySchema)
                .options(
                    selectinload(FacilitySchema.zone).selectinload(ZoneSchema.country),
                )
                .where(FacilitySchema.id == id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return self._row_to_facility_response(row)

    async def list_facilities(
        self,
        *,
        zone_id: str | None = None,
        country_id: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[FacilityResponse], int]:
        async with self._session_factory() as session:
            q = (
                select(FacilitySchema)
                .options(
                    selectinload(FacilitySchema.zone).selectinload(ZoneSchema.country),
                )
            )
            count_q = select(func.count()).select_from(FacilitySchema)
            if zone_id:
                q = q.where(FacilitySchema.zone_id == zone_id)
                count_q = count_q.where(FacilitySchema.zone_id == zone_id)
            if country_id:
                subq = select(ZoneSchema.id).where(ZoneSchema.country_id == country_id)
                q = q.where(FacilitySchema.zone_id.in_(subq))
                count_q = count_q.where(FacilitySchema.zone_id.in_(subq))
            if search:
                pattern = f"%{search}%"
                pred = or_(FacilitySchema.name.ilike(pattern), FacilitySchema.code.ilike(pattern))
                q = q.where(pred)
                count_q = count_q.where(pred)
            total = (await session.execute(count_q)).scalar() or 0
            order_col = getattr(FacilitySchema, sort, FacilitySchema.created_at)
            q = q.order_by(order_col.desc() if order == "desc" else order_col.asc())
            q = q.offset(offset).limit(limit)
            result = await session.execute(q)
            rows = result.scalars().all()
            items = [self._row_to_facility_response(r) for r in rows]
        return items, total

    async def create(self, data: FacilityCreate) -> FacilityResponse:
        async with self._session_factory() as session:
            row = FacilitySchema(
                id=str(uuid4()),
                zone_id=data.zone_id,
                user_id=None,
                name=data.name,
                code=data.code,
                address=data.address,
                dealer_name=data.dealer_name,
                dealer_phone=data.dealer_phone,
                dealer_email=data.dealer_email,
                dealer_designation=data.dealer_designation,
            )
            session.add(row)
            await session.commit()
        return await self.get_by_id(row.id)

    async def update(self, id: str, data: FacilityUpdate) -> FacilityResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(FacilitySchema).where(FacilitySchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            if data.code is not None:
                row.code = data.code
            if data.address is not None:
                row.address = data.address
            if data.zone_id is not None:
                row.zone_id = data.zone_id
            if data.user_id is not None:
                row.user_id = data.user_id
            if data.dealer_name is not None:
                row.dealer_name = data.dealer_name
            if data.dealer_phone is not None:
                row.dealer_phone = data.dealer_phone
            if data.dealer_email is not None:
                row.dealer_email = data.dealer_email
            if data.dealer_designation is not None:
                row.dealer_designation = data.dealer_designation
            await session.commit()
        return await self.get_by_id(id)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(FacilitySchema).where(FacilitySchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
