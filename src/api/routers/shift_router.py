"""Shift: current shift, config, history."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import RequireEmployee, RequireStellantisAdmin
from src.business_services.shift_service import get_shift_service
from src.database.repositories.schemas.shift_schema import ShiftConfigUpdate

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.get("/current")
async def get_current_shift(
    shift_service: Annotated[any, Depends(get_shift_service)],
):
    """Get current shift (and whether we are in it)."""
    return await shift_service.get_current_shift()


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
    payload: Annotated[dict, RequireStellantisAdmin],
    shift_service: Annotated[any, Depends(get_shift_service)],
):
    """Update shift config (Admin)."""
    return await shift_service.update_config(id, body)


@router.get("/history")
async def get_shift_history(
    date: str | None = None,
    payload: Annotated[dict, RequireEmployee] = None,
    shift_service: Annotated[any, Depends(get_shift_service)] = None,
):
    """Get shift history for a date. Placeholder."""
    return {"date": date, "shifts": []}
