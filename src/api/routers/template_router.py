"""Audit checklist: categories, subcategories, checkpoints. Mount under /audit."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireStellantisAdmin, get_current_user_payload
from src.business_services.template_service import get_template_service
from src.database.repositories.schemas.template_schema import (
    CategoryCreate,
    CategoryUpdate,
    CheckpointCreate,
    CheckpointUpdate,
    SubcategoryCreate,
    SubcategoryUpdate,
)
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginationParams

router = APIRouter(prefix="/audit", tags=["audit-checklist"])

# --- Categories ---
@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
):
    return await template_service.create_category(body, payload)


@router.get("/categories")
async def list_categories(
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
):
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await template_service.list_categories(payload, params=params)


@router.get("/categories/{id}")
async def get_category(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
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
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.update_category(id, body, payload)
    if not row:
        raise NotFoundError("Category", id)
    return row


@router.delete("/categories/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
):
    ok = await template_service.delete_category(id, payload)
    if not ok:
        raise NotFoundError("Category", id)

# --- Subcategories ---
@router.post("/subcategories", status_code=status.HTTP_201_CREATED)
async def create_subcategory(
    body: SubcategoryCreate,
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
):
    return await template_service.create_subcategory(body, payload)


@router.get("/subcategories")
async def list_subcategories(
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
    category_id: str | None = None,
):
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await template_service.list_subcategories(payload, category_id=category_id, params=params)


@router.get("/subcategories/{id}")
async def get_subcategory(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.get_subcategory(id, payload)
    if not row:
        raise NotFoundError("Subcategory", id)
    return row


@router.patch("/subcategories/{id}")
async def update_subcategory(
    id: str,
    body: SubcategoryUpdate,
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.update_subcategory(id, body, payload)
    if not row:
        raise NotFoundError("Subcategory", id)
    return row


@router.delete("/subcategories/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subcategory(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
):
    ok = await template_service.delete_subcategory(id, payload)
    if not ok:
        raise NotFoundError("Subcategory", id)

# --- Checkpoints ---
@router.post("/checkpoints", status_code=status.HTTP_201_CREATED)
async def create_checkpoint(
    body: CheckpointCreate,
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
):
    return await template_service.create_checkpoint(body, payload)


@router.get("/checkpoints")
async def list_checkpoints(
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
    facility_id: str | None = None,
    subcategory_id: str | None = None,
):
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await template_service.list_checkpoints(
        payload, facility_id=facility_id, subcategory_id=subcategory_id, params=params
    )


@router.get("/checkpoints/{id}")
async def get_checkpoint(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
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
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
):
    row = await template_service.update_checkpoint(id, body, payload)
    if not row:
        raise NotFoundError("Checkpoint", id)
    return row


@router.delete("/checkpoints/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_checkpoint(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
    template_service: Annotated[any, Depends(get_template_service)],
):
    ok = await template_service.delete_checkpoint(id, payload)
    if not ok:
        raise NotFoundError("Checkpoint", id)
