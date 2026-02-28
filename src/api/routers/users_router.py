"""User management (Admin)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireStellantisAdmin, get_current_user_payload
from src.business_services.user_service import get_user_service
from src.database.repositories.schemas.user_schema import UserUpdate, UserChangePassword
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginationParams

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(
    payload: Annotated[dict, RequireStellantisAdmin],
    user_service: Annotated[any, Depends(get_user_service)],
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
):
    """Get all users (Admin). Pagination."""
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await user_service.list_users(params=params)


@router.get("/{id}")
async def get_user(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
    user_service: Annotated[any, Depends(get_user_service)],
):
    """Get user by ID."""
    user = await user_service.get_by_id(id)
    if not user:
        raise NotFoundError("User", id)
    return user


@router.patch("/{id}")
async def update_user(
    id: str,
    body: UserUpdate,
    payload: Annotated[dict, RequireStellantisAdmin],
    user_service: Annotated[any, Depends(get_user_service)],
):
    """Update user."""
    user = await user_service.update(id, body)
    if not user:
        raise NotFoundError("User", id)
    return user


@router.patch("/change-password")
async def change_password(
    body: UserChangePassword,
    payload: Annotated[dict, Depends(get_current_user_payload)],
    user_service: Annotated[any, Depends(get_user_service)],
):
    """Change current user password."""
    await user_service.change_password(payload["sub"], body)
    return {"message": "Password updated"}
