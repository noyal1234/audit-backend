from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.user_schema import UserSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.user_schema import (
    UserCreate,
    UserResponse,
    UserUpdate,
)


class UserRepository(BasePostgresRepository[UserSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, UserSchema)

    def _schema_to_user(self, row: UserSchema) -> UserResponse:
        return UserResponse.model_validate(row)

    async def get_by_id(self, id: str) -> UserResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_user(row) if row else None

    async def get_by_email(self, email: str) -> UserSchema | None:
        async with self._session_factory() as session:
            result = await session.execute(select(UserSchema).where(UserSchema.email == email))
            return result.scalar_one_or_none()

    async def create(self, data: UserCreate, password_hash: str) -> UserResponse:
        async with self._session_factory() as session:
            row = UserSchema(
                id=str(uuid4()),
                email=data.email,
                password_hash=password_hash,
                role_type=data.role_type,
                facility_id=data.facility_id,
                country_id=data.country_id,
                is_active=True,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_user(row)

    async def update(self, id: str, data: UserUpdate) -> UserResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(UserSchema).where(UserSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.email is not None:
                row.email = data.email
            if data.facility_id is not None:
                row.facility_id = data.facility_id
            if data.country_id is not None:
                row.country_id = data.country_id
            await session.commit()
            await session.refresh(row)
            return self._schema_to_user(row)

    async def list_users(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[UserResponse], int]:
        from sqlalchemy import func
        async with self._session_factory() as session:
            count_q = select(func.count()).select_from(UserSchema)
            total = (await session.execute(count_q)).scalar() or 0
            order_col = getattr(UserSchema, sort, UserSchema.created_at)
            q = select(UserSchema).order_by(
                order_col.desc() if order == "desc" else order_col.asc()
            ).offset(offset).limit(limit)
            result = await session.execute(q)
            rows = result.scalars().all()
        return [self._schema_to_user(r) for r in rows], total
