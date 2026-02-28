"""Auth: login, refresh, logout, me."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_current_user_payload
from src.business_services.auth_service import get_auth_service
from src.business_services.user_service import get_user_service
from src.database.repositories.schemas.auth_schema import LoginRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth_service: Annotated[any, Depends(get_auth_service)],
):
    """Login with email and password. All roles (SUPER_ADMIN, STELLANTIS_ADMIN, DEALERSHIP, EMPLOYEE) use this endpoint. Returns access and refresh tokens."""
    return await auth_service.login(body)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    auth_service: Annotated[any, Depends(get_auth_service)],
):
    """Exchange refresh token for new access and refresh tokens."""
    return await auth_service.refresh_token(body.refresh_token)


@router.post("/logout")
async def logout(
    payload: Annotated[dict, Depends(get_current_user_payload)],
    auth_service: Annotated[any, Depends(get_auth_service)],
):
    """Invalidate refresh sessions for the current user."""
    await auth_service.logout(payload["sub"])
    return {"message": "Logged out"}


@router.get("/me")
async def me(
    payload: Annotated[dict, Depends(get_current_user_payload)],
    user_service: Annotated[any, Depends(get_user_service)],
):
    """Return current user info from JWT payload."""
    user = await user_service.get_by_id(payload["sub"])
    if not user:
        return {"id": payload["sub"], "email": payload.get("email"), "role_type": payload.get("role_type")}
    return user
