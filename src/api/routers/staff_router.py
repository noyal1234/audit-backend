"""Employees (staff) API."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireDealership, get_current_user_payload
from src.business_services.staff_service import get_staff_service
from src.database.repositories.schemas.staff_schema import StaffCreate, StaffUpdate
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginationParams

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_employee(
    body: StaffCreate,
    payload: Annotated[dict, RequireDealership],
    staff_service: Annotated[any, Depends(get_staff_service)],
):
    """Create an employee (staff) under a dealership."""
    return await staff_service.create(body, payload)


@router.get("")
async def list_employees(
    payload: Annotated[dict, RequireDealership],
    staff_service: Annotated[any, Depends(get_staff_service)],
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
    dealership_id: str | None = None,
    search: str | None = None,
):
    """List employees with optional dealership filter and search."""
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await staff_service.list_staff(payload, dealership_id=dealership_id, search=search, params=params)


@router.get("/{id}")
async def get_employee(
    id: str,
    payload: Annotated[dict, RequireDealership],
    staff_service: Annotated[any, Depends(get_staff_service)],
):
    """Get employee by ID."""
    row = await staff_service.get_by_id(id, payload)
    if not row:
        raise NotFoundError("Employee", id)
    return row


@router.patch("/{id}")
async def update_employee(
    id: str,
    body: StaffUpdate,
    payload: Annotated[dict, RequireDealership],
    staff_service: Annotated[any, Depends(get_staff_service)],
):
    """Update employee."""
    row = await staff_service.update(id, body, payload)
    if not row:
        raise NotFoundError("Employee", id)
    return row


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    id: str,
    payload: Annotated[dict, RequireDealership],
    staff_service: Annotated[any, Depends(get_staff_service)],
):
    """Delete employee."""
    ok = await staff_service.delete(id, payload)
    if not ok:
        raise NotFoundError("Employee", id)
