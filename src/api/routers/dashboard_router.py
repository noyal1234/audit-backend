"""Analytics endpoints. Aggregated queries, chart-friendly JSON."""

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
    """Country-level summary: total audits, compliance %, monthly trend. STELLANTIS_ADMIN scoped by country_id."""
    country_id = payload.get("country_id") if payload.get("role_type") == "STELLANTIS_ADMIN" else None
    return await dashboard_service.country_summary(
        payload, country_id=country_id, zone_id=zone_id, facility_id=facility_id,
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
    """Zone summary: facility ranking, compliance %, audit count."""
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
    """Facility summary: shift performance, category compliance, failure rate."""
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
    period: str = "monthly",
):
    """Audit trends. Period: daily or monthly."""
    from src.database.repositories.schemas.dashboard_schema import AuditTrendsResponse
    return AuditTrendsResponse(period=period, data=[])


@router.get("/category-breakdown")
async def category_breakdown(
    payload: Annotated[dict, RequireEmployee],
    dashboard_service: Annotated[any, Depends(get_dashboard_service)],
    zone_id: str | None = None,
    facility_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    """Category compliance breakdown."""
    return await dashboard_service.category_breakdown(
        payload, zone_id=zone_id, facility_id=facility_id,
        date_from=date_from, date_to=date_to,
    )


@router.get("/top-issues")
async def top_issues(
    payload: Annotated[dict, RequireEmployee],
    dashboard_service: Annotated[any, Depends(get_dashboard_service)],
    zone_id: str | None = None,
    facility_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    """Top non-compliant checkpoints."""
    return await dashboard_service.top_issues(
        payload, zone_id=zone_id, facility_id=facility_id,
        date_from=date_from, date_to=date_to,
    )
