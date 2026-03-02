"""Image upload, AI result retrieval, and admin delete endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireEmployee, RequireStellantisAdmin
from src.business_services.media_service import get_media_service
from src.exceptions.domain_exceptions import NotFoundError

router = APIRouter(tags=["images"])


@router.get("/images/{id}/ai-result")
async def get_image_ai_result(
    id: str,
    payload: Annotated[dict, RequireEmployee],
    media_service: Annotated[any, Depends(get_media_service)],
):
    """
    Get the AI compliance analysis result for a specific uploaded image.

    - `ai_status`: PENDING (analysis running) | COMPLETED | FAILED
    - `ai_compliant`: true/false once completed
    - `ai_confidence`: 0.0–1.0 confidence score
    - `ai_observations`: bullet-point findings from the model
    - `ai_summary`: one-sentence verdict
    """
    row = await media_service.get_image_ai_result(id, payload)
    if not row:
        raise NotFoundError("Image", id)
    return row


@router.delete("/images/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    id: str,
    payload: Annotated[dict, RequireStellantisAdmin],
    media_service: Annotated[any, Depends(get_media_service)],
):
    """Delete image (Admin)."""
    ok = await media_service.delete_image(id, payload)
    if not ok:
        raise NotFoundError("Image", id)
