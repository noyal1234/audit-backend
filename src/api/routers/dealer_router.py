"""Dealerships (facilities) API."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireDealership, get_current_user_payload
from src.business_services.dealer_service import get_dealer_service
from src.database.repositories.schemas.dealer_schema import (
    DealerContactResponse,
    DealerContactUpdate,
    FacilityCreate,
    FacilityResponse,
    FacilityUpdate,
)
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginationParams

router = APIRouter(prefix="/dealerships", tags=["dealerships"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_dealership(
    body: FacilityCreate,
    payload: Annotated[dict, RequireDealership],
    dealer_service: Annotated[any, Depends(get_dealer_service)],
):
    """Create a dealership (facility). Requires dealer_name, dealer_phone, dealer_email."""
    return await dealer_service.create(body, payload)


@router.get("")
async def list_dealerships(
    payload: Annotated[dict, RequireDealership],
    dealer_service: Annotated[any, Depends(get_dealer_service)],
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
    zone_id: str | None = None,
    search: str | None = None,
):
    """List dealerships with pagination, zone filter, and search."""
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await dealer_service.list_facilities(payload, zone_id=zone_id, search=search, params=params)


@router.get("/{id}")
async def get_dealership(
    id: str,
    payload: Annotated[dict, RequireDealership],
    dealer_service: Annotated[any, Depends(get_dealer_service)],
):
    """Get dealership by ID."""
    fac = await dealer_service.get_by_id(id, payload)
    if not fac:
        raise NotFoundError("Dealership", id)
    return fac


@router.patch("/{id}")
async def update_dealership(
    id: str,
    body: FacilityUpdate,
    payload: Annotated[dict, RequireDealership],
    dealer_service: Annotated[any, Depends(get_dealer_service)],
):
    """Update dealership."""
    fac = await dealer_service.update(id, body, payload)
    if not fac:
        raise NotFoundError("Dealership", id)
    return fac


@router.get("/{id}/contact", response_model=DealerContactResponse)
async def get_dealer_contact(
    id: str,
    payload: Annotated[dict, RequireDealership],
    dealer_service: Annotated[any, Depends(get_dealer_service)],
):
    """Get dealer contact details. Super Admin, Stellantis Admin, Dealership only; Employee forbidden."""
    contact = await dealer_service.get_contact(id, payload)
    if not contact:
        raise NotFoundError("Dealership", id)
    return contact


@router.patch("/{id}/contact", response_model=FacilityResponse)
async def update_dealer_contact(
    id: str,
    body: DealerContactUpdate,
    payload: Annotated[dict, RequireDealership],
    dealer_service: Annotated[any, Depends(get_dealer_service)],
):
    """Update dealer contact details (partial). Super Admin, Stellantis Admin, Dealership only."""
    fac = await dealer_service.update_contact(id, body, payload)
    if not fac:
        raise NotFoundError("Dealership", id)
    return fac


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dealership(
    id: str,
    payload: Annotated[dict, RequireDealership],
    dealer_service: Annotated[any, Depends(get_dealer_service)],
):
    """Delete dealership."""
    ok = await dealer_service.delete(id, payload)
    if not ok:
        raise NotFoundError("Dealership", id)
