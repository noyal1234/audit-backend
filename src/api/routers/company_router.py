"""Zones API. Mount at /zones."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireStellantisAdmin, get_current_user_payload
from src.business_services.company_service import get_company_service
from src.database.repositories.schemas.company_schema import ZoneCreate, ZoneUpdate
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginatedResponse, PaginationParams

router = APIRouter(prefix="/zones", tags=["zones"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_zone(
    body: ZoneCreate,
    payload: Annotated[dict, RequireStellantisAdmin],
    company_service: Annotated[any, Depends(get_company_service)],
):
    """Create a zone. Super Admin or Stellantis Admin."""
    return await company_service.create(body, payload)


@router.get("")
async def list_zones(
    payload: Annotated[dict, RequireStellantisAdmin],
    company_service: Annotated[any, Depends(get_company_service)],
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
    country_id: str | None = None,
):
    """List zones with pagination and optional country filter."""
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await company_service.list_zones(payload, country_id=country_id, params=params)


@router.get("/{id}")
async def get_zone(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
    company_service: Annotated[any, Depends(get_company_service)],
):
    """Get zone by ID."""
    zone = await company_service.get_by_id(id, payload)
    if not zone:
        raise NotFoundError("Zone", id)
    return zone


@router.patch("/{id}")
async def update_zone(
    id: str,
    body: ZoneUpdate,
    payload: Annotated[dict, RequireStellantisAdmin],
    company_service: Annotated[any, Depends(get_company_service)],
):
    """Update zone."""
    zone = await company_service.update(id, body, payload)
    if not zone:
        raise NotFoundError("Zone", id)
    return zone


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
    company_service: Annotated[any, Depends(get_company_service)],
):
    """Delete zone."""
    ok = await company_service.delete(id, payload)
    if not ok:
        raise NotFoundError("Zone", id)
