from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
import bcrypt
from src.configs.settings import get_instance
from src.database.repositories.auth_repository import AuthRepository
from src.database.repositories.schemas.auth_schema import LoginRequest, TokenResponse
from src.database.repositories.schemas.user_schema import UserResponse
from src.exceptions.domain_exceptions import UnauthorizedError, ForbiddenError
from src.business_services.base import BaseBusinessService
from src.utils.datetime_utils import utc_now


ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_STELLANTIS_ADMIN = "STELLANTIS_ADMIN"
ROLE_DEALERSHIP = "DEALERSHIP"
ROLE_EMPLOYEE = "EMPLOYEE"


class AuthService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._auth_repo: AuthRepository | None = None
        self._user_repo: Any = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        from src.database.repositories.user_repository import UserRepository
        factory = get_container().get_postgres_service().get_session_factory()
        self._auth_repo = AuthRepository(factory)
        self._user_repo = UserRepository(factory)
        self.logger.info("[OK] AuthService initialized")

    def _close_service(self) -> None:
        self._auth_repo = None
        self._user_repo = None

    def _get_settings(self) -> Any:
        return get_instance()

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    def _create_access_token(self, user_id: str, email: str, role_type: str, facility_id: str | None, country_id: str | None) -> tuple[str, int]:
        settings = self._get_settings()
        expire = utc_now() + timedelta(minutes=settings.jwt_access_expire_minutes)
        payload = {
            "sub": user_id,
            "email": email,
            "role_type": role_type,
            "facility_id": facility_id,
            "country_id": country_id,
            "exp": expire,
            "iat": utc_now(),
            "type": "access",
        }
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        return token, settings.jwt_access_expire_minutes * 60

    def _create_refresh_token(self, user_id: str) -> tuple[str, datetime]:
        settings = self._get_settings()
        expire = utc_now() + timedelta(days=settings.jwt_refresh_expire_days)
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": utc_now(),
            "type": "refresh",
        }
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        return token, expire

    async def login(self, data: LoginRequest) -> TokenResponse:
        if self._auth_repo is None:
            raise RuntimeError("AuthService not initialized")
        user = await self._auth_repo.get_user_by_email(data.email)
        if not user or not self._verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        if not getattr(user, "is_active", True):
            raise UnauthorizedError("Account is inactive")
        access_token, expires_in = self._create_access_token(
            user.id,
            user.email,
            user.role_type,
            user.facility_id,
            user.country_id,
        )
        refresh_token, expires_at = self._create_refresh_token(user.id)
        await self._auth_repo.create_session(user.id, None, refresh_token, expires_at)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        if self._auth_repo is None or self._user_repo is None:
            raise RuntimeError("AuthService not initialized")
        settings = self._get_settings()
        try:
            payload = jwt.decode(
                refresh_token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except JWTError:
            raise UnauthorizedError("Invalid or expired refresh token")
        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token")
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("User not found")
        session = await self._auth_repo.find_session_by_refresh_token(refresh_token)
        if not session:
            raise UnauthorizedError("Session not found or expired")
        access_token, expires_in = self._create_access_token(
            user.id,
            user.email,
            user.role_type,
            user.facility_id,
            user.country_id,
        )
        new_refresh, expires_at = self._create_refresh_token(user.id)
        await self._auth_repo.create_session(user.id, None, new_refresh, expires_at)
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=expires_in,
        )

    async def logout(self, user_id: str) -> None:
        if self._auth_repo is None:
            raise RuntimeError("AuthService not initialized")
        await self._auth_repo.invalidate_sessions_by_user(user_id)

    def decode_access_token(self, token: str) -> dict[str, Any]:
        settings = self._get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except JWTError:
            raise UnauthorizedError("Invalid or expired token")
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        return payload

    def is_super_admin(self, payload: dict[str, Any]) -> bool:
        return payload.get("role_type") == ROLE_SUPER_ADMIN


_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
