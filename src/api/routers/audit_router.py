"""Audit execution: current (lazy), list, get, progress, complete/uncomplete category, finalize, reopen."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencies import RequireDealership, RequireEmployee
from src.business_services.audit_service import get_audit_service
from src.business_services.report_service import get_report_service
from src.database.repositories.schemas.audit_schema import CategoryCompleteRequest, CategoryRemarksUpdate
from src.exceptions.domain_exceptions import NotFoundError
from src.utils.pagination import PaginationParams

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get("/current")
async def get_current_audit(
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Get or lazily create the audit for the current shift. Auto-snapshots all checkpoints and categories."""
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


@router.get("/{id}")
async def get_audit(
    id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Get audit by ID with full snapshot detail."""
    audit = await audit_service.get_by_id(id, payload)
    if not audit:
        raise NotFoundError("Audit", id)
    return audit


@router.get("/{audit_id}/progress")
async def get_audit_progress(
    audit_id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Get audit progress: completion counts and percentage."""
    return await audit_service.get_progress(audit_id, payload)


@router.post("/{audit_id}/checkpoint-categories/{id}/complete")
async def complete_category(
    audit_id: str,
    id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
    body: CategoryCompleteRequest | None = None,
):
    """Mark an audit checkpoint category as completed. Auto-updates checkpoint and audit status."""
    data = body or CategoryCompleteRequest()
    return await audit_service.complete_category(audit_id, id, data, payload)


@router.post("/{audit_id}/checkpoint-categories/{id}/uncomplete")
async def uncomplete_category(
    audit_id: str,
    id: str,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Unmark an audit checkpoint category. Reverses completion."""
    return await audit_service.uncomplete_category(audit_id, id, payload)


@router.patch("/{audit_id}/checkpoint-categories/{id}")
async def update_category_remarks(
    audit_id: str,
    id: str,
    body: CategoryRemarksUpdate,
    payload: Annotated[dict, RequireEmployee],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Update the remarks (review text) for a category. Does not change completion state. Use when audit is PENDING, IN_PROGRESS, or REOPENED."""
    return await audit_service.update_category_remarks(audit_id, id, body, payload)


@router.patch("/{id}/finalize")
async def finalize_audit(
    id: str,
    payload: Annotated[dict, RequireDealership],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Finalize audit. Immutable after this. DEALERSHIP+ required."""
    audit = await audit_service.finalize(id, payload)
    if not audit:
        raise NotFoundError("Audit", id)
    return audit


@router.patch("/{id}/reopen")
async def reopen_audit(
    id: str,
    payload: Annotated[dict, RequireDealership],
    audit_service: Annotated[any, Depends(get_audit_service)],
):
    """Reopen a COMPLETED audit. DEALERSHIP+ required. FINALIZED requires SUPER_ADMIN."""
    audit = await audit_service.reopen(id, payload)
    if not audit:
        raise NotFoundError("Audit", id)
    return audit


@router.get("/{id}/report")
async def get_audit_report(
    id: str,
    payload: Annotated[dict, RequireDealership],
    report_service: Annotated[any, Depends(get_report_service)],
):
    """
    Generate a full AI compliance report for the given audit.

    The report includes:
    - Executive summary
    - Compliance highlights
    - Risk areas and non-compliances
    - Root-cause observations
    - Corrective action recommendations
    - Shift pattern notes

    Requires DEALERSHIP role or above. Report is generated on-demand (not cached).
    """
    return await report_service.generate_report(id, payload)

