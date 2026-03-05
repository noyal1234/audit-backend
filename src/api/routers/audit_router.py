"""Audit execution: current (lazy), list, get, progress, checkpoint complete/uncomplete, manual review, finalize, reopen, delete, rebuild."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status

from src.api.dependencies import RequireDealership, RequireEmployee
from src.business_services.audit_service import get_audit_service
from src.business_services.media_service import get_media_service
from src.business_services.report_service import get_report_service
from src.database.repositories.schemas.audit_schema import AuditQualityScoreResponse, CheckpointCompleteRequest
from src.database.repositories.schemas.review_schema import ManualReviewRequest
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginationParams

router = APIRouter(prefix="/audits", tags=["audits"])


# --- Static / specific paths first ---

@router.get("/current")
async def get_current_audit(
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Get or lazily create the audit for the current shift. Snapshots area -> sub_area -> checkpoint hierarchy."""
    return await audit_service.get_or_create_current_audit(payload)


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


# --- Multi-segment routes (more specific than /{audit_id}) ---

@router.get("/{audit_id}/progress")
async def get_audit_progress(
    audit_id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Get audit progress: checkpoint completion and compliance (effective review)."""
    return await audit_service.get_progress(audit_id, payload)


@router.get("/{audit_id}/quality-score", response_model=AuditQualityScoreResponse)
async def get_audit_quality_score(
    audit_id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Get average compliance score from effective reviews. Checkpoints without a review are excluded."""
    return await audit_service.get_quality_score(audit_id, payload)


@router.post("/{audit_id}/checkpoints/{checkpoint_id}/complete")
async def complete_checkpoint(
    audit_id: str,
    checkpoint_id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
    body: CheckpointCompleteRequest | None = None,
):
    """Mark an audit checkpoint as completed (is_completed=true). EMPLOYEE+."""
    return await audit_service.mark_checkpoint_completed(audit_id, checkpoint_id, body, payload)


@router.post("/{audit_id}/checkpoints/{checkpoint_id}/uncomplete")
async def uncomplete_checkpoint(
    audit_id: str,
    checkpoint_id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Unmark an audit checkpoint (is_completed=false). EMPLOYEE+."""
    return await audit_service.mark_checkpoint_incomplete(audit_id, checkpoint_id, payload)


@router.patch("/{audit_id}/checkpoints/{checkpoint_id}/review")
async def patch_checkpoint_review(
    audit_id: str,
    checkpoint_id: str,
    body: ManualReviewRequest,
    payload: Annotated[dict, RequireDealership],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Insert a manual review for the checkpoint (append-only). Blocked if audit is FINALIZED. DEALERSHIP+."""
    return await audit_service.submit_manual_review(audit_id, checkpoint_id, body, payload)


@router.post("/{audit_id}/checkpoints/{checkpoint_id}/image")
async def upload_checkpoint_image(
    audit_id: str,
    checkpoint_id: str,
    payload: Annotated[dict, RequireEmployee],
    media_service: Annotated[any, Depends(get_media_service)],
    file: UploadFile = File(...),
):
    """Upload an evidence image for an audit checkpoint. Triggers background AI analysis (inserts AI review when done)."""
    content = await file.read()
    return await media_service.save_upload(
        audit_id=audit_id,
        audit_checkpoint_id=checkpoint_id,
        file_content=content,
        filename=file.filename or "image.jpg",
        content_type=file.content_type,
        payload=payload,
    )


@router.get("/{audit_id}/images")
async def list_audit_images(
    audit_id: str,
    payload: Annotated[dict, RequireEmployee],
    media_service: Annotated[any, Depends(get_media_service)],
):
    """List all evidence images for the audit (with checkpoint names from snapshot)."""
    return await media_service.list_audit_images(audit_id, payload)


@router.patch("/{audit_id}/finalize")
async def finalize_audit(
    audit_id: str,
    payload: Annotated[dict, RequireDealership],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Finalize audit. Immutable after this. DEALERSHIP+ required."""
    audit = await audit_service.finalize(audit_id, payload)
    if not audit:
        raise NotFoundError("Audit", audit_id)
    return audit


@router.patch("/{audit_id}/reopen")
async def reopen_audit(
    audit_id: str,
    payload: Annotated[dict, RequireDealership],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Reopen a COMPLETED audit. DEALERSHIP+ required. FINALIZED requires SUPER_ADMIN."""
    audit = await audit_service.reopen(audit_id, payload)
    if not audit:
        raise NotFoundError("Audit", audit_id)
    return audit


@router.post("/{audit_id}/rebuild")
async def rebuild_audit(
    audit_id: str,
    payload: Annotated[dict, RequireDealership],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Delete the audit and create a fresh one for same facility/shift with current hierarchy. FINALIZED not allowed. DEALERSHIP+."""
    return await audit_service.rebuild_audit(audit_id, payload)


@router.get("/{audit_id}/report")
async def get_audit_report(
    audit_id: str,
    payload: Annotated[dict, RequireDealership],
    report_service: Annotated[any, Depends(get_report_service)],
):
    """
    Generate a full AI compliance report for the given audit.
    Uses effective review (latest per checkpoint) for executive summary.
    DEALERSHIP+.
    """
    return await report_service.generate_report(audit_id, payload)


# --- DELETE before GET for same path /{audit_id} ---

@router.delete("/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(
    audit_id: str,
    payload: Annotated[dict, RequireDealership],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Delete audit and its media. FINALIZED audits cannot be deleted. DEALERSHIP+ required."""
    await audit_service.delete_audit(audit_id, payload)


@router.get("/{audit_id}")
async def get_audit(
    audit_id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Get audit by ID with full snapshot (areas -> sub_areas -> checkpoints) and effective reviews."""
    audit = await audit_service.get_by_id(audit_id, payload)
    if not audit:
        raise NotFoundError("Audit", audit_id)
    return audit
