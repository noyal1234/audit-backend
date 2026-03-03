"""Facility hierarchy: areas, sub_areas, checkpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireDealership, RequireEmployee
from src.business_services.template_service import get_template_service
from src.database.repositories.schemas.area_schema import (
    AreaCreate,
    AreaUpdate,
    CheckpointCreate,
    CheckpointUpdate,
    SubAreaCreate,
    SubAreaUpdate,
)
from src.exceptions.domain_exceptions import NotFoundError

router = APIRouter(tags=["facility-hierarchy"])


# --- Areas ---

@router.get("/facilities/{facility_id}/areas")
async def list_areas(
    facility_id: str,
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """List areas for a facility."""
    return await template_service.list_areas(payload, facility_id=facility_id)


@router.get("/facilities/{facility_id}/hierarchy")
async def get_facility_hierarchy(
    facility_id: str,
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """Get full hierarchy: areas -> sub_areas -> checkpoints (for audit snapshot)."""
    return await template_service.get_facility_hierarchy(payload, facility_id)


@router.post("/areas", status_code=status.HTTP_201_CREATED)
async def create_area(
    body: AreaCreate,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """Create an area. DEALERSHIP or above."""
    return await template_service.create_area(body, payload)


@router.get("/areas/{id}")
async def get_area(
    id: str,
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.get_area(id, payload)
    if not row:
        raise NotFoundError("Area", id)
    return row


@router.patch("/areas/{id}")
async def update_area(
    id: str,
    body: AreaUpdate,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.update_area(id, body, payload)
    if not row:
        raise NotFoundError("Area", id)
    return row


@router.delete("/areas/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_area(
    id: str,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    ok = await template_service.delete_area(id, payload)
    if not ok:
        raise NotFoundError("Area", id)


# --- Sub-areas ---

@router.get("/areas/{area_id}/sub-areas")
async def list_sub_areas(
    area_id: str,
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """List sub-areas for an area."""
    return await template_service.list_sub_areas(area_id, payload)


@router.post("/sub-areas", status_code=status.HTTP_201_CREATED)
async def create_sub_area(
    body: SubAreaCreate,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """Create a sub-area under an area. DEALERSHIP or above."""
    return await template_service.create_sub_area(body, payload)


@router.get("/sub-areas/{id}")
async def get_sub_area(
    id: str,
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.get_sub_area(id, payload)
    if not row:
        raise NotFoundError("SubArea", id)
    return row


@router.patch("/sub-areas/{id}")
async def update_sub_area(
    id: str,
    body: SubAreaUpdate,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.update_sub_area(id, body, payload)
    if not row:
        raise NotFoundError("SubArea", id)
    return row


@router.delete("/sub-areas/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sub_area(
    id: str,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    ok = await template_service.delete_sub_area(id, payload)
    if not ok:
        raise NotFoundError("SubArea", id)


# --- Checkpoints ---

@router.get("/sub-areas/{sub_area_id}/checkpoints")
async def list_checkpoints(
    sub_area_id: str,
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """List checkpoints for a sub-area."""
    return await template_service.list_checkpoints(sub_area_id, payload)


@router.post("/checkpoints", status_code=status.HTTP_201_CREATED)
async def create_checkpoint(
    body: CheckpointCreate,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """Create a checkpoint under a sub-area. DEALERSHIP or above."""
    return await template_service.create_checkpoint(body, payload)


@router.get("/checkpoints/{id}")
async def get_checkpoint(
    id: str,
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.get_checkpoint(id, payload)
    if not row:
        raise NotFoundError("Checkpoint", id)
    return row


@router.patch("/checkpoints/{id}")
async def update_checkpoint(
    id: str,
    body: CheckpointUpdate,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.update_checkpoint(id, body, payload)
    if not row:
        raise NotFoundError("Checkpoint", id)
    return row


@router.delete("/checkpoints/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_checkpoint(
    id: str,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    ok = await template_service.delete_checkpoint(id, payload)
    if not ok:
        raise NotFoundError("Checkpoint", id)
