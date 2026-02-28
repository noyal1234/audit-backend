"""Super Admin: Stellantis admin CRUD, system stats, rebuild analytics."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireSuperAdmin
from src.business_services.user_service import get_user_service
from src.database.repositories.schemas.user_schema import UserCreate, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/stellantis", status_code=status.HTTP_201_CREATED)
async def create_stellantis_admin(
    body: UserCreate,
    payload: Annotated[dict, RequireSuperAdmin],
    user_service: Annotated[any, Depends(get_user_service)],
):
    """Create Stellantis Admin (country-scoped). Requires country_id. Returns 409 if email already in use."""
    from src.business_services.auth_service import get_auth_service
    auth_svc = get_auth_service()
    password_hash = auth_svc._hash_password(body.password)
    body_with_role = UserCreate(
        email=body.email,
        password=body.password,
        role_type="STELLANTIS_ADMIN",
        facility_id=None,
        country_id=body.country_id,
    )
    return await user_service.create_user(body_with_role, password_hash)


@router.get("/stellantis")
async def list_stellantis_admins(
    payload: Annotated[dict, RequireSuperAdmin],
    page: int = 1,
    limit: int = 20,
):
    """Get all Stellantis Admins. Placeholder: returns all users filtered by role in service."""
    from src.database.repositories.user_repository import UserRepository
    from src.di.container import get_container
    from src.utils.pagination import PaginationParams, PaginatedResponse
    factory = get_container().get_postgres_service().get_session_factory()
    repo = UserRepository(factory)
    params = PaginationParams(page=page, limit=limit)
    items, total = await repo.list_users(offset=params.offset, limit=params.limit, sort="created_at", order="desc")
    items = [i for i in items if i.role_type == "STELLANTIS_ADMIN"]
    total = len(items)
    return PaginatedResponse.build(items, total, params.page, params.limit)


@router.get("/stellantis/{id}")
async def get_stellantis_admin(
    id: str,
    payload: Annotated[dict, RequireSuperAdmin],
    user_service: Annotated[any, Depends(get_user_service)],
):
    """Get Stellantis Admin by ID."""
    from src.exceptions.domain_exceptions import NotFoundError
    user = await user_service.get_by_id(id)
    if not user or user.role_type != "STELLANTIS_ADMIN":
        raise NotFoundError("Stellantis Admin", id)
    return user


@router.patch("/stellantis/{id}")
async def update_stellantis_admin(
    id: str,
    body: UserUpdate,
    payload: Annotated[dict, RequireSuperAdmin],
    user_service: Annotated[any, Depends(get_user_service)],
):
    """Update Stellantis Admin."""
    from src.exceptions.domain_exceptions import NotFoundError
    user = await user_service.get_by_id(id)
    if not user or user.role_type != "STELLANTIS_ADMIN":
        raise NotFoundError("Stellantis Admin", id)
    return await user_service.update(id, body)


@router.delete("/stellantis/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stellantis_admin(
    id: str,
    payload: Annotated[dict, RequireSuperAdmin],
    user_service: Annotated[any, Depends(get_user_service)],
):
    """Delete Stellantis Admin. Placeholder: implement delete in UserService if needed."""
    from src.exceptions.domain_exceptions import NotFoundError
    user = await user_service.get_by_id(id)
    if not user or user.role_type != "STELLANTIS_ADMIN":
        raise NotFoundError("Stellantis Admin", id)


@router.get("/system-stats")
async def system_stats(payload: Annotated[dict, RequireSuperAdmin]):
    """System statistics. Placeholder."""
    return {"zones": 0, "facilities": 0, "audits": 0, "users": 0}


@router.post("/rebuild-analytics")
async def rebuild_analytics(payload: Annotated[dict, RequireSuperAdmin]):
    """Force analytics rebuild. Placeholder."""
    return {"message": "Analytics rebuild requested"}
