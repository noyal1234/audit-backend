"""Facility-scoped categories, checkpoints, and checkpoint-category assignments."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from src.api.dependencies import RequireDealership, RequireEmployee
from src.business_services.template_service import get_template_service
from src.database.repositories.schemas.template_schema import (
    CategoryCreate,
    CategoryUpdate,
    CheckpointCategoryCreate,
    CheckpointUpdate,
)
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginationParams

router = APIRouter(tags=["categories-checkpoints"])


# --- Categories ---

@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """Create a facility-scoped category. DEALERSHIP or above."""
    return await template_service.create_category(body, payload)


@router.get("/categories")
async def list_categories(
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
    facility_id: str | None = None,
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
):
    """List categories, optionally filtered by facility_id."""
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await template_service.list_categories(payload, facility_id=facility_id, params=params)


@router.get("/categories/{id}")
async def get_category(
    id: str,
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.get_category(id, payload)
    if not row:
        raise NotFoundError("Category", id)
    return row


@router.patch("/categories/{id}")
async def update_category(
    id: str,
    body: CategoryUpdate,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.update_category(id, body, payload)
    if not row:
        raise NotFoundError("Category", id)
    return row


@router.delete("/categories/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    id: str,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    ok = await template_service.delete_category(id, payload)
    if not ok:
        raise NotFoundError("Category", id)


# --- Checkpoints ---

@router.post("/checkpoints", status_code=status.HTTP_201_CREATED)
async def create_checkpoint(
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
    name: str = Form(...),
    file: UploadFile = File(...),
    facility_id: str | None = Form(None),
):
    """Create a checkpoint with required image upload. DEALERSHIP or above."""
    content = await file.read()
    return await template_service.create_checkpoint(
        name=name,
        file_content=content,
        filename=file.filename or "image.jpg",
        content_type=file.content_type,
        payload=payload,
        facility_id=facility_id,
    )


@router.get("/checkpoints")
async def list_checkpoints(
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
    facility_id: str | None = None,
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
):
    """List checkpoints, optionally filtered by facility_id."""
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await template_service.list_checkpoints(payload, facility_id=facility_id, params=params)


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


# --- Checkpoint-Category assignments ---

@router.post("/checkpoints/{id}/categories", status_code=status.HTTP_201_CREATED)
async def assign_category_to_checkpoint(
    id: str,
    body: CheckpointCategoryCreate,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """Assign a category to a checkpoint (same facility required). DEALERSHIP or above."""
    return await template_service.assign_category_to_checkpoint(id, body, payload)


@router.get("/checkpoints/{id}/categories")
async def list_checkpoint_categories(
    id: str,
    payload: Annotated[dict, RequireEmployee],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """List categories assigned to a checkpoint."""
    return await template_service.list_checkpoint_categories(id, payload)


@router.delete("/checkpoints/{id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_category_from_checkpoint(
    id: str,
    category_id: str,
    payload: Annotated[dict, RequireDealership],
    template_service: Annotated[any, Depends(get_template_service)],
):
    """Remove a category from a checkpoint. DEALERSHIP or above."""
    ok = await template_service.remove_category_from_checkpoint(id, category_id, payload)
    if not ok:
        raise NotFoundError("CheckpointCategory", f"{id}/{category_id}")
