"""Audit execution: create, list, get, record checkpoint, upload image, finalize, reopen."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from src.business_services.media_service import get_media_service

from src.api.dependencies import RequireEmployee, get_current_user_payload
from src.business_services.audit_service import get_audit_service
from src.business_services.media_service import get_media_service
from src.database.repositories.schemas.audit_schema import AuditCreate, CheckpointResultCreate
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginationParams

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_audit(
    body: AuditCreate,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Create audit for current shift. One per shift per facility."""
    return await audit_service.create(body, payload["sub"], payload)


@router.get("")
async def list_audits(
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
    page: int = 1,
    limit: int = 20,
    sort: str = "created_at",
    order: str = "desc",
    zone_id: str | None = None,
    facility_id: str | None = None,
    shift: str | None = None,
    date: date | None = None,
    status_type: str | None = None,
):
    """List audits with filters and pagination."""
    params = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await audit_service.list_audits(
        payload,
        zone_id=zone_id,
        facility_id=facility_id,
        shift_type=shift,
        shift_date=date,
        status_type=status_type,
        params=params,
    )


@router.get("/{id}")
async def get_audit(
    id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Get audit by ID."""
    audit = await audit_service.get_by_id(id, payload)
    if not audit:
        raise NotFoundError("Audit", id)
    return audit


@router.post("/{audit_id}/checkpoints/{checkpoint_id}")
async def record_checkpoint_result(
    audit_id: str,
    checkpoint_id: str,
    body: CheckpointResultCreate,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Record checkpoint result (compliant/non-compliant, optional manual override)."""
    return await audit_service.record_checkpoint(audit_id, checkpoint_id, body, payload)


@router.post("/{audit_id}/checkpoints/{checkpoint_id}/image")
async def upload_checkpoint_image(
    audit_id: str,
    checkpoint_id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
    media_service: Annotated[any, Depends(get_media_service)],
    file: UploadFile = File(...),
):
    """Upload image for checkpoint. Sets AI_PENDING; returns placeholder AI response."""
    content = await file.read()
    media = await media_service.save_upload(
        audit_id,
        checkpoint_id,
        content,
        file.filename or "image.jpg",
        file.content_type,
        payload,
    )
    await audit_service.upload_image_ai_status(audit_id, checkpoint_id, media.file_path, payload)
    from src.database.repositories.schemas.ai_schema import AIResultResponse
    return AIResultResponse(status="AI_PENDING", message="Placeholder AI result; human decision overrides.")


@router.get("/{audit_id}/checkpoints/{checkpoint_id}/ai-result")
async def get_ai_result(
    audit_id: str,
    checkpoint_id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Get AI result for checkpoint (placeholder)."""
    result = await audit_service.get_ai_result(audit_id, checkpoint_id, payload)
    if not result:
        raise NotFoundError("Checkpoint result", f"{audit_id}/{checkpoint_id}")
    from src.database.repositories.schemas.ai_schema import AIResultResponse
    return AIResultResponse(
        status=result.ai_status_type or "AI_PENDING",
        compliant=result.compliant,
        message="Human decision overrides AI.",
    )


@router.patch("/{id}/finalize")
async def finalize_audit(
    id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Finalize audit. Immutable after this."""
    audit = await audit_service.finalize(id, payload)
    if not audit:
        raise NotFoundError("Audit", id)
    return audit


@router.patch("/{id}/reopen")
async def reopen_audit(
    id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Reopen audit (Admin only)."""
    audit = await audit_service.reopen(id, payload)
    if not audit:
        raise NotFoundError("Audit", id)
    return audit


@router.get("/{audit_id}/images")
async def get_audit_images(
    audit_id: str,
    payload: Annotated[dict, RequireEmployee],
    media_service: Annotated[any, Depends(get_media_service)],
):
    """Get images for an audit."""
    return await media_service.list_audit_images(audit_id, payload)
