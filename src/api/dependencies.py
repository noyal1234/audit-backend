from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.business_services.auth_service import (
    AuthService,
    ROLE_DEALERSHIP,
    ROLE_EMPLOYEE,
    ROLE_STELLANTIS_ADMIN,
    ROLE_SUPER_ADMIN,
    get_auth_service,
)
from src.exceptions.domain_exceptions import ForbiddenError, UnauthorizedError

security = HTTPBearer(auto_error=False)


async def get_current_user_payload(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    authorization: Annotated[str | None, Header()] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> dict:
    """Decode JWT and return payload (sub, email, role_type, facility_id, country_id). Raises 401 if invalid."""
    token = None
    if credentials:
        token = credentials.credentials
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = auth_service.decode_access_token(token)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return payload


def require_roles(*allowed_roles: str):
    """Dependency factory: require current user to have one of the given roles."""

    async def _require(
        payload: Annotated[dict, Depends(get_current_user_payload)],
    ) -> dict:
        role = payload.get("role_type")
        if role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return payload

    return _require


RequireSuperAdmin = Depends(require_roles(ROLE_SUPER_ADMIN))
RequireStellantisAdmin = Depends(require_roles(ROLE_SUPER_ADMIN, ROLE_STELLANTIS_ADMIN))
RequireDealership = Depends(require_roles(ROLE_SUPER_ADMIN, ROLE_STELLANTIS_ADMIN, ROLE_DEALERSHIP))
RequireEmployee = Depends(require_roles(ROLE_SUPER_ADMIN, ROLE_STELLANTIS_ADMIN, ROLE_DEALERSHIP, ROLE_EMPLOYEE))


def require_country_access(country_id: str, payload: dict) -> None:
    """Raise ForbiddenError if user cannot access the country. STELLANTIS_ADMIN must match country_id."""
    if payload.get("role_type") == ROLE_SUPER_ADMIN:
        return
    if payload.get("role_type") == ROLE_STELLANTIS_ADMIN:
        if payload.get("country_id") == country_id:
            return
        raise ForbiddenError("Access denied to this country")
    raise ForbiddenError("Access denied to this country")


def require_facility_access(facility_id: str, payload: dict) -> None:
    """Raise ForbiddenError if user cannot access the facility. SUPER_ADMIN and STELLANTIS_ADMIN (country-scoped) allowed; service layer validates facility is in user's country for STELLANTIS_ADMIN."""
    if payload.get("role_type") == ROLE_SUPER_ADMIN:
        return
    if payload.get("facility_id") == facility_id:
        return
    if payload.get("country_id"):
        return
    raise ForbiddenError("Access denied to this facility")
