"""Analytics aggregation. DB aggregation where possible."""

from datetime import date
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.api.dependencies import require_country_access
from src.database.postgres.schema.audit_schema import AuditCheckpointResultSchema, AuditSchema
from src.database.postgres.schema.facility_schema import FacilitySchema
from src.database.postgres.schema.zone_schema import ZoneSchema
from src.database.repositories.schemas.dashboard_schema import (
    CategoryBreakdownResponse,
    CountrySummaryResponse,
    FacilitySummaryResponse,
    TopIssuesResponse,
    ZoneSummaryResponse,
)
from src.business_services.base import BaseBusinessService


class DashboardService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        self._session_factory = get_container().get_postgres_service().get_session_factory()
        self.logger.info("[OK] DashboardService initialized")

    def _close_service(self) -> None:
        self._session_factory = None

    async def country_summary(
        self,
        payload: dict,
        country_id: str | None = None,
        zone_id: str | None = None,
        facility_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> CountrySummaryResponse:
        if self._session_factory is None:
            raise RuntimeError("DashboardService not initialized")
        scope_country = country_id or payload.get("country_id")
        async with self._session_factory() as session:
            q = select(
                func.count(AuditSchema.id).label("total_audits"),
            ).select_from(AuditSchema)
            if date_from:
                q = q.where(AuditSchema.shift_date >= date_from)
            if date_to:
                q = q.where(AuditSchema.shift_date <= date_to)
            if shift_type:
                q = q.where(AuditSchema.shift_type == shift_type)
            if facility_id:
                q = q.where(AuditSchema.facility_id == facility_id)
            if zone_id:
                subq = select(FacilitySchema.id).where(FacilitySchema.zone_id == zone_id)
                q = q.where(AuditSchema.facility_id.in_(subq))
            if scope_country:
                subq = (
                    select(FacilitySchema.id)
                    .select_from(FacilitySchema)
                    .join(ZoneSchema, FacilitySchema.zone_id == ZoneSchema.id)
                    .where(ZoneSchema.country_id == scope_country)
                )
                q = q.where(AuditSchema.facility_id.in_(subq))
            r = (await session.execute(q)).one_or_none()
        total = r[0] if r else 0
        compliance = 0.0
        return CountrySummaryResponse(
            total_audits=total,
            compliance_percent=compliance,
            monthly_trend=[],
        )

    async def zone_summary(
        self,
        payload: dict,
        zone_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> ZoneSummaryResponse:
        if self._session_factory is None:
            raise RuntimeError("DashboardService not initialized")
        async with self._session_factory() as session:
            zone_row = (await session.execute(select(ZoneSchema).where(ZoneSchema.id == zone_id))).scalar_one_or_none()
            if zone_row and zone_row.country_id:
                require_country_access(zone_row.country_id, payload)
        async with self._session_factory() as session:
            subq = select(FacilitySchema.id).where(FacilitySchema.zone_id == zone_id)
            q = select(func.count(AuditSchema.id)).select_from(AuditSchema).where(AuditSchema.facility_id.in_(subq))
            if date_from:
                q = q.where(AuditSchema.shift_date >= date_from)
            if date_to:
                q = q.where(AuditSchema.shift_date <= date_to)
            if shift_type:
                q = q.where(AuditSchema.shift_type == shift_type)
            r = (await session.execute(q)).scalar() or 0
        return ZoneSummaryResponse(
            zone_id=zone_id,
            facility_ranking=[],
            compliance_percent=0.0,
            audit_count=r,
        )

    async def facility_summary(
        self,
        payload: dict,
        facility_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> FacilitySummaryResponse:
        if self._session_factory is None:
            raise RuntimeError("DashboardService not initialized")
        return FacilitySummaryResponse(
            facility_id=facility_id,
            shift_performance=[],
            category_compliance=[],
            failure_rate_per_checkpoint=[],
        )

    async def category_breakdown(
        self,
        payload: dict,
        zone_id: str | None = None,
        facility_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[CategoryBreakdownResponse]:
        return []

    async def top_issues(
        self,
        payload: dict,
        zone_id: str | None = None,
        facility_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 10,
    ) -> list[TopIssuesResponse]:
        return []


_dashboard_service: DashboardService | None = None


def get_dashboard_service() -> DashboardService:
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service
