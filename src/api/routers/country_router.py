"""Country APIs (future-ready)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireStellantisAdmin
from src.business_services.country_service import get_country_service
from src.database.repositories.schemas.country_schema import CountryCreate, CountryUpdate
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginationParams

router = APIRouter(prefix="/countries", tags=["countries"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_country(
    body: CountryCreate,
    payload: Annotated[dict, RequireStellantisAdmin],
    country_service: Annotated[any, Depends(get_country_service)],
):
    return await country_service.create(body)


@router.get("")
async def list_countries(
    payload: Annotated[dict, RequireStellantisAdmin],
    country_service: Annotated[any, Depends(get_country_service)],
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
):
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await country_service.list_countries(params=params)


@router.get("/{id}")
async def get_country(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
    country_service: Annotated[any, Depends(get_country_service)],
):
    row = await country_service.get_by_id(id)
    if not row:
        raise NotFoundError("Country", id)
    return row


@router.patch("/{id}")
async def update_country(
    id: str,
    body: CountryUpdate,
    payload: Annotated[dict, RequireStellantisAdmin],
    country_service: Annotated[any, Depends(get_country_service)],
):
    row = await country_service.update(id, body)
    if not row:
        raise NotFoundError("Country", id)
    return row


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_country(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
    country_service: Annotated[any, Depends(get_country_service)],
):
    ok = await country_service.delete(id)
    if not ok:
        raise NotFoundError("Country", id)

