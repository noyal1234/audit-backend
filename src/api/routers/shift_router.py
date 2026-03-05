"""Shift: current shift, config CRUD. SUPER_ADMIN for mutations, EMPLOYEE+ for reads."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireEmployee, RequireSuperAdmin
from src.business_services.shift_service import get_shift_service
from src.database.repositories.schemas.shift_schema import ShiftConfigUpdate
from src.exceptions.domain_exceptions import ConflictError

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.get("/current")
async def get_current_shift(
    payload: Annotated[dict, RequireEmployee],
    shift_service: Annotated[any, Depends(get_shift_service)],
):
    """Get current active shift for the user's facility. Uses facility timezone. Facility-scoped users only."""
    facility_id = payload.get("facility_id")
    if not facility_id:
        raise ConflictError("Only facility-scoped users can get current shift")
    return await shift_service.get_current_shift(facility_id)


@router.get("/config")
async def get_shift_config(
    payload: Annotated[dict, RequireEmployee],
    shift_service: Annotated[any, Depends(get_shift_service)],
):
    """Get shift configuration list."""
    return await shift_service.get_config()


@router.patch("/config/{id}")
async def update_shift_config(
    id: str,
    body: ShiftConfigUpdate,
    payload: Annotated[dict, RequireSuperAdmin],
    shift_service: Annotated[any, Depends(get_shift_service)],
):
    """Update shift config. Validates 24h coverage after update. SUPER_ADMIN only."""
    return await shift_service.update_config(id, body)


@router.delete("/config/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shift_config(
    id: str,
    payload: Annotated[dict, RequireSuperAdmin],
    shift_service: Annotated[any, Depends(get_shift_service)],
):
    """Delete shift config. Rejected if it would break 24h coverage. SUPER_ADMIN only."""
    await shift_service.delete_config(id)
