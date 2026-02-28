import bcrypt

from src.business_services.base import BaseBusinessService
from src.database.repositories.user_repository import UserRepository
from src.database.repositories.schemas.user_schema import UserCreate, UserResponse, UserUpdate, UserChangePassword
from src.exceptions.domain_exceptions import ConflictError, NotFoundError, ValidationError
from src.utils.pagination import PaginatedResponse, PaginationParams


class UserService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._user_repo: UserRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._user_repo = UserRepository(factory)
        self.logger.info("[OK] UserService initialized")

    def _close_service(self) -> None:
        self._user_repo = None

    async def get_by_id(self, id: str) -> UserResponse | None:
        if self._user_repo is None:
            raise RuntimeError("UserService not initialized")
        return await self._user_repo.get_by_id(id)

    async def get_by_id_or_raise(self, id: str) -> UserResponse:
        user = await self.get_by_id(id)
        if not user:
            raise NotFoundError("User", id)
        return user

    async def list_users(self, params: PaginationParams | None = None) -> PaginatedResponse[UserResponse]:
        if self._user_repo is None:
            raise RuntimeError("UserService not initialized")
        params = params or PaginationParams()
        items, total = await self._user_repo.list_users(
            offset=params.offset,
            limit=params.limit,
            sort=params.sort,
            order=params.order,
        )
        return PaginatedResponse.build(items, total, params.page, params.limit)

    async def create_user(self, data: UserCreate, password_hash: str) -> UserResponse:
        """Create user. Validates role vs country_id/facility_id. Raises ConflictError if email already in use."""
        if self._user_repo is None:
            raise RuntimeError("UserService not initialized")
        if data.role_type == "STELLANTIS_ADMIN":
            if not data.country_id:
                raise ValidationError("country_id is required for STELLANTIS_ADMIN")
            from src.database.repositories.country_repository import CountryRepository
            from src.di.container import get_container
            factory = get_container().get_postgres_service().get_session_factory()
            country_repo = CountryRepository(factory)
            country = await country_repo.get_by_id(data.country_id)
            if not country:
                raise NotFoundError("Country", data.country_id or "")
        if data.role_type == "SUPER_ADMIN" and data.country_id:
            raise ValidationError("SUPER_ADMIN cannot have country_id")
        if data.role_type in ("EMPLOYEE", "DEALERSHIP") and data.country_id:
            raise ValidationError("Only STELLANTIS_ADMIN can have country_id")
        existing = await self._user_repo.get_by_email(data.email)
        if existing:
            raise ConflictError("Email already in use")
        return await self._user_repo.create(data, password_hash)

    async def update(self, id: str, data: UserUpdate) -> UserResponse | None:
        if self._user_repo is None:
            raise RuntimeError("UserService not initialized")
        return await self._user_repo.update(id, data)

    async def change_password(self, user_id: str, data: UserChangePassword) -> None:
        if self._user_repo is None:
            raise RuntimeError("UserService not initialized")
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        from src.database.repositories.auth_repository import AuthRepository
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        auth_repo = AuthRepository(factory)
        user_row = await auth_repo.get_user_by_email(user.email)
        if not user_row or not bcrypt.checkpw(data.current_password.encode("utf-8"), user_row.password_hash.encode("utf-8")):
            raise ValidationError("Current password is incorrect")
        new_hash = bcrypt.hashpw(data.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        from sqlalchemy import select
        from src.database.postgres.schema.user_schema import UserSchema
        async with factory() as session:
            result = await session.execute(select(UserSchema).where(UserSchema.id == user_id))
            row = result.scalar_one_or_none()
            if row:
                row.password_hash = new_hash
                await session.commit()


_user_service: UserService | None = None


def get_user_service() -> UserService:
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
