"""Image delete (Admin)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireStellantisAdmin
from src.business_services.media_service import get_media_service
from src.exceptions.domain_exceptions import NotFoundError

router = APIRouter(tags=["images"])


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
