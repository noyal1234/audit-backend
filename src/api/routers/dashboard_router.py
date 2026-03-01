"""Analytics endpoints. Real aggregate queries from snapshot-based audit model."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import RequireEmployee
from src.business_services.dashboard_service import get_dashboard_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/country-summary")
async def country_summary(
    payload: Annotated[dict, RequireEmployee],
    dashboard_service: Annotated[any, Depends(get_dashboard_service)],
    zone_id: str | None = None,
    facility_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    shift_type: str | None = None,
):
    """Country-level summary: total audits, facilities, completion counts, compliance %, monthly trend."""
    return await dashboard_service.country_summary(
        payload, zone_id=zone_id, facility_id=facility_id,
        date_from=date_from, date_to=date_to, shift_type=shift_type,
    )


@router.get("/zone-summary")
async def zone_summary(
    payload: Annotated[dict, RequireEmployee],
    dashboard_service: Annotated[any, Depends(get_dashboard_service)],
    zone_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
    shift_type: str | None = None,
):
    """Zone summary: audit count, compliance %, facility ranking by compliance."""
    return await dashboard_service.zone_summary(
        payload, zone_id=zone_id,
        date_from=date_from, date_to=date_to, shift_type=shift_type,
    )


@router.get("/facility-summary")
async def facility_summary(
    payload: Annotated[dict, RequireEmployee],
    dashboard_service: Annotated[any, Depends(get_dashboard_service)],
    facility_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
    shift_type: str | None = None,
):
    """Facility summary: shift performance, category compliance, failure rate per checkpoint."""
    return await dashboard_service.facility_summary(
        payload, facility_id=facility_id,
        date_from=date_from, date_to=date_to, shift_type=shift_type,
    )


@router.get("/trends")
async def audit_trends(
    payload: Annotated[dict, RequireEmployee],
    dashboard_service: Annotated[any, Depends(get_dashboard_service)],
    zone_id: str | None = None,
    facility_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    shift_type: str | None = None,
    period: str = "monthly",
):
    """Audit compliance trends. Period: daily, weekly, or monthly."""
    return await dashboard_service.trends(
        payload, period=period, zone_id=zone_id, facility_id=facility_id,
        date_from=date_from, date_to=date_to, shift_type=shift_type,
    )


@router.get("/category-breakdown")
async def category_breakdown(
    payload: Annotated[dict, RequireEmployee],
    dashboard_service: Annotated[any, Depends(get_dashboard_service)],
    zone_id: str | None = None,
    facility_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    shift_type: str | None = None,
):
    """Category compliance breakdown across all audits."""
    return await dashboard_service.category_breakdown(
        payload, zone_id=zone_id, facility_id=facility_id,
        date_from=date_from, date_to=date_to, shift_type=shift_type,
    )


@router.get("/top-issues")
async def top_issues(
    payload: Annotated[dict, RequireEmployee],
    dashboard_service: Annotated[any, Depends(get_dashboard_service)],
    zone_id: str | None = None,
    facility_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    shift_type: str | None = None,
    limit: int = 10,
):
    """Top non-completed checkpoint+category combinations by failure count."""
    return await dashboard_service.top_issues(
        payload, zone_id=zone_id, facility_id=facility_id,
        date_from=date_from, date_to=date_to, shift_type=shift_type, limit=limit,
    )
