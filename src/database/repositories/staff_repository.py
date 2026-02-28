from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.orm import aliased

from src.database.postgres.schema.staff_schema import StaffSchema
from src.database.postgres.schema.user_schema import UserSchema
from src.database.postgres.schema.facility_schema import FacilitySchema
from src.database.postgres.schema.zone_schema import ZoneSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.staff_schema import StaffResponse, StaffUpdate


class StaffRepository(BasePostgresRepository[StaffSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, StaffSchema)

    def _row_to_response(self, row: StaffSchema, user_email: str | None = None) -> StaffResponse:
        return StaffResponse(
            id=row.id,
            facility_id=row.facility_id,
            user_id=row.user_id,
            name=row.name,
            email=user_email,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_id(self, id: str) -> StaffResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(StaffSchema, UserSchema.email)
                .outerjoin(UserSchema, StaffSchema.user_id == UserSchema.id)
                .where(StaffSchema.id == id)
            )
            row = result.one_or_none()
            if not row:
                return None
            staff_row, user_email = row[0], row[1]
            return self._row_to_response(staff_row, user_email)

    async def list_staff(
        self,
        *,
        facility_id: str | None = None,
        country_id: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[StaffResponse], int]:
        async with self._session_factory() as session:
            User = aliased(UserSchema)
            q = select(StaffSchema, User.email).outerjoin(User, StaffSchema.user_id == User.id)
            if search:
                pattern = f"%{search}%"
                search_pred = or_(StaffSchema.name.ilike(pattern), User.email.ilike(pattern))
                count_q = select(func.count()).select_from(StaffSchema).outerjoin(User, StaffSchema.user_id == User.id).where(search_pred)
            else:
                count_q = select(func.count()).select_from(StaffSchema)
            if facility_id:
                q = q.where(StaffSchema.facility_id == facility_id)
                count_q = count_q.where(StaffSchema.facility_id == facility_id)
            if country_id:
                subq = (
                    select(FacilitySchema.id)
                    .select_from(FacilitySchema)
                    .join(ZoneSchema, FacilitySchema.zone_id == ZoneSchema.id)
                    .where(ZoneSchema.country_id == country_id)
                )
                q = q.where(StaffSchema.facility_id.in_(subq))
                count_q = count_q.where(StaffSchema.facility_id.in_(subq))
            if search:
                q = q.where(search_pred)
            total = (await session.execute(count_q)).scalar() or 0
            order_col = getattr(StaffSchema, sort, StaffSchema.created_at)
            q = q.order_by(order_col.desc() if order == "desc" else order_col.asc())
            q = q.offset(offset).limit(limit)
            result = await session.execute(q)
            rows = result.all()
        return [self._row_to_response(r[0], r[1]) for r in rows], total

    async def create_record(self, facility_id: str, user_id: str, name: str) -> StaffResponse:
        """Create staff profile (no email; login via user)."""
        async with self._session_factory() as session:
            row = StaffSchema(
                id=str(uuid4()),
                facility_id=facility_id,
                user_id=user_id,
                name=name,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._row_to_response(row, None)

    async def update(self, id: str, data: StaffUpdate) -> StaffResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(StaffSchema).where(StaffSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            if data.user_id is not None:
                row.user_id = data.user_id
            await session.commit()
            await session.refresh(row)
            user_email = None
            if row.user_id:
                u = await session.get(UserSchema, row.user_id)
                user_email = u.email if u else None
            return self._row_to_response(row, user_email)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(StaffSchema).where(StaffSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
