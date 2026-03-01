"""Analytics aggregation engine. All queries derive from audit_checkpoint_category."""

from datetime import date

from sqlalchemy import Select, case, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.audit_schema import (
    AuditCheckpointCategorySchema,
    AuditCheckpointSchema,
    AuditSchema,
)
from src.database.postgres.schema.facility_schema import FacilitySchema
from src.database.postgres.schema.zone_schema import ZoneSchema
from src.database.repositories.schemas.dashboard_schema import (
    AuditTrendsResponse,
    CategoryBreakdownResponse,
    CategoryComplianceItem,
    CheckpointFailureItem,
    CountrySummaryResponse,
    FacilityRankingItem,
    FacilitySummaryResponse,
    MonthlyTrendItem,
    ShiftPerformanceItem,
    TopIssuesResponse,
    TrendDataPoint,
    ZoneSummaryResponse,
)
from src.business_services.base import BaseBusinessService
from src.exceptions.domain_exceptions import ForbiddenError

ACC = AuditCheckpointCategorySchema
ACP = AuditCheckpointSchema
A = AuditSchema
F = FacilitySchema
Z = ZoneSchema


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

    def _require_initialized(self) -> None:
        if self._session_factory is None:
            raise RuntimeError("DashboardService not initialized")

    # ---- reusable scope filter ----

    def _apply_scope_filters(
        self,
        q: Select,
        payload: dict,
        zone_id: str | None = None,
        facility_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> Select:
        """Apply RBAC scope + optional filters to any query that selects from AuditSchema."""
        role = payload.get("role_type")

        if role == "SUPER_ADMIN":
            pass
        elif role == "STELLANTIS_ADMIN":
            country_id = payload.get("country_id")
            if not country_id:
                raise ForbiddenError("STELLANTIS_ADMIN requires country_id in token")
            country_fac = (
                select(F.id)
                .join(Z, F.zone_id == Z.id)
                .where(Z.country_id == country_id)
            )
            q = q.where(A.facility_id.in_(country_fac))
        elif role in ("DEALERSHIP", "EMPLOYEE"):
            user_facility = payload.get("facility_id")
            if not user_facility:
                raise ForbiddenError("Facility-scoped user requires facility_id in token")
            q = q.where(A.facility_id == user_facility)
        else:
            raise ForbiddenError("Access denied")

        if facility_id:
            q = q.where(A.facility_id == facility_id)
        if zone_id:
            zone_fac = select(F.id).where(F.zone_id == zone_id)
            q = q.where(A.facility_id.in_(zone_fac))
        if date_from:
            q = q.where(A.shift_date >= date_from)
        if date_to:
            q = q.where(A.shift_date <= date_to)
        if shift_type:
            q = q.where(A.shift_type == shift_type)
        return q

    # ---- helpers ----

    def _compliance(self, completed: int, total: int) -> float:
        return round(completed / total * 100.0, 2) if total > 0 else 0.0

    def _base_join(self) -> Select:
        """Base select joining audit -> audit_checkpoint -> audit_checkpoint_category."""
        return (
            select(A, ACP, ACC)
            .join(ACP, ACP.audit_id == A.id)
            .join(ACC, ACC.audit_checkpoint_id == ACP.id)
        )

    # ================================================================
    # 1. Country Summary
    # ================================================================

    async def country_summary(
        self,
        payload: dict,
        zone_id: str | None = None,
        facility_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> CountrySummaryResponse:
        self._require_initialized()
        async with self._session_factory() as session:
            base = (
                select(
                    func.count(func.distinct(A.id)).label("total_audits"),
                    func.count(func.distinct(A.facility_id)).label("total_facilities"),
                    func.sum(case((A.status_type == "COMPLETED", 1), else_=0)).label("audits_completed_raw"),
                    func.sum(case((A.status_type == "IN_PROGRESS", 1), else_=0)).label("audits_in_progress_raw"),
                    func.count(ACC.id).label("total_cat"),
                    func.sum(case((ACC.is_completed.is_(True), 1), else_=0)).label("completed_cat"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
            )
            base = self._apply_scope_filters(base, payload, zone_id, facility_id, date_from, date_to, shift_type)
            row = (await session.execute(base)).one_or_none()

            total_audits = (row.total_audits or 0) if row else 0
            total_facilities = (row.total_facilities or 0) if row else 0
            total_cat = (row.total_cat or 0) if row else 0
            completed_cat = (row.completed_cat or 0) if row else 0
            compliance = self._compliance(completed_cat, total_cat)

            audits_completed_raw = (row.audits_completed_raw or 0) if row else 0
            audits_in_progress_raw = (row.audits_in_progress_raw or 0) if row else 0

            status_q = (
                select(
                    A.status_type,
                    func.count(func.distinct(A.id)).label("cnt"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
                .group_by(A.status_type)
            )
            status_q = self._apply_scope_filters(status_q, payload, zone_id, facility_id, date_from, date_to, shift_type)
            status_rows = (await session.execute(status_q)).all()
            status_map = {r.status_type: r.cnt for r in status_rows}
            audits_completed = status_map.get("COMPLETED", 0) + status_map.get("FINALIZED", 0)
            audits_in_progress = status_map.get("IN_PROGRESS", 0)

            trend_q = (
                select(
                    func.to_char(A.shift_date, text("'YYYY-MM'")).label("month"),
                    func.count(ACC.id).label("total_cat"),
                    func.sum(case((ACC.is_completed.is_(True), 1), else_=0)).label("completed_cat"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
                .group_by(text("month"))
                .order_by(text("month"))
            )
            trend_q = self._apply_scope_filters(trend_q, payload, zone_id, facility_id, date_from, date_to, shift_type)
            trend_rows = (await session.execute(trend_q)).all()

        monthly_trend = [
            MonthlyTrendItem(
                month=r.month,
                compliance_percent=self._compliance(r.completed_cat or 0, r.total_cat or 0),
            )
            for r in trend_rows
        ]
        return CountrySummaryResponse(
            total_audits=total_audits,
            total_facilities=total_facilities,
            audits_completed=audits_completed,
            audits_in_progress=audits_in_progress,
            compliance_percent=compliance,
            monthly_trend=monthly_trend,
        )

    # ================================================================
    # 2. Zone Summary
    # ================================================================

    async def zone_summary(
        self,
        payload: dict,
        zone_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> ZoneSummaryResponse:
        self._require_initialized()
        async with self._session_factory() as session:
            zone_row = (await session.execute(select(Z).where(Z.id == zone_id))).scalar_one_or_none()
            if zone_row and zone_row.country_id:
                role = payload.get("role_type")
                if role == "STELLANTIS_ADMIN" and payload.get("country_id") != zone_row.country_id:
                    raise ForbiddenError("Access denied to this zone")

            agg_q = (
                select(
                    func.count(func.distinct(A.id)).label("audit_count"),
                    func.count(ACC.id).label("total_cat"),
                    func.sum(case((ACC.is_completed.is_(True), 1), else_=0)).label("completed_cat"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
            )
            agg_q = self._apply_scope_filters(agg_q, payload, zone_id=zone_id, date_from=date_from, date_to=date_to, shift_type=shift_type)
            row = (await session.execute(agg_q)).one_or_none()
            audit_count = (row.audit_count or 0) if row else 0
            total_cat = (row.total_cat or 0) if row else 0
            completed_cat = (row.completed_cat or 0) if row else 0

            rank_q = (
                select(
                    A.facility_id,
                    F.name.label("facility_name"),
                    func.count(ACC.id).label("total_cat"),
                    func.sum(case((ACC.is_completed.is_(True), 1), else_=0)).label("completed_cat"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
                .join(F, A.facility_id == F.id)
                .group_by(A.facility_id, F.name)
            )
            rank_q = self._apply_scope_filters(rank_q, payload, zone_id=zone_id, date_from=date_from, date_to=date_to, shift_type=shift_type)
            rank_rows = (await session.execute(rank_q)).all()

        facility_ranking = sorted(
            [
                FacilityRankingItem(
                    facility_id=r.facility_id,
                    facility_name=r.facility_name,
                    compliance_percent=self._compliance(r.completed_cat or 0, r.total_cat or 0),
                )
                for r in rank_rows
            ],
            key=lambda x: x.compliance_percent,
            reverse=True,
        )
        return ZoneSummaryResponse(
            zone_id=zone_id,
            audit_count=audit_count,
            compliance_percent=self._compliance(completed_cat, total_cat),
            facility_ranking=facility_ranking,
        )

    # ================================================================
    # 3. Facility Summary
    # ================================================================

    async def facility_summary(
        self,
        payload: dict,
        facility_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> FacilitySummaryResponse:
        self._require_initialized()
        async with self._session_factory() as session:
            # A) Shift performance
            shift_q = (
                select(
                    A.shift_type,
                    func.count(ACC.id).label("total_cat"),
                    func.sum(case((ACC.is_completed.is_(True), 1), else_=0)).label("completed_cat"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
                .group_by(A.shift_type)
            )
            shift_q = self._apply_scope_filters(shift_q, payload, facility_id=facility_id, date_from=date_from, date_to=date_to, shift_type=shift_type)
            shift_rows = (await session.execute(shift_q)).all()

            # B) Category compliance
            cat_q = (
                select(
                    ACC.category_name,
                    func.count(ACC.id).label("total_occ"),
                    func.sum(case((ACC.is_completed.is_(True), 1), else_=0)).label("completed"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
                .group_by(ACC.category_name)
            )
            cat_q = self._apply_scope_filters(cat_q, payload, facility_id=facility_id, date_from=date_from, date_to=date_to, shift_type=shift_type)
            cat_rows = (await session.execute(cat_q)).all()

            # C) Failure rate per checkpoint
            cp_q = (
                select(
                    ACP.checkpoint_name,
                    func.count(ACC.id).label("total_cat"),
                    func.sum(case((ACC.is_completed.is_(False), 1), else_=0)).label("not_completed"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
                .group_by(ACP.checkpoint_name)
            )
            cp_q = self._apply_scope_filters(cp_q, payload, facility_id=facility_id, date_from=date_from, date_to=date_to, shift_type=shift_type)
            cp_rows = (await session.execute(cp_q)).all()

        shift_performance = [
            ShiftPerformanceItem(
                shift_type=r.shift_type,
                total_categories=r.total_cat or 0,
                completed_categories=r.completed_cat or 0,
                compliance_percent=self._compliance(r.completed_cat or 0, r.total_cat or 0),
            )
            for r in shift_rows
        ]
        category_compliance = [
            CategoryComplianceItem(
                category_name=r.category_name,
                total_occurrences=r.total_occ or 0,
                completed=r.completed or 0,
                compliance_percent=self._compliance(r.completed or 0, r.total_occ or 0),
            )
            for r in cat_rows
        ]
        failure_rate_per_checkpoint = [
            CheckpointFailureItem(
                checkpoint_name=r.checkpoint_name,
                total_categories=r.total_cat or 0,
                not_completed=r.not_completed or 0,
                failure_rate=self._compliance(r.not_completed or 0, r.total_cat or 0),
            )
            for r in cp_rows
        ]
        return FacilitySummaryResponse(
            facility_id=facility_id,
            shift_performance=shift_performance,
            category_compliance=category_compliance,
            failure_rate_per_checkpoint=failure_rate_per_checkpoint,
        )

    # ================================================================
    # 4. Trends
    # ================================================================

    async def trends(
        self,
        payload: dict,
        period: str = "monthly",
        zone_id: str | None = None,
        facility_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> AuditTrendsResponse:
        self._require_initialized()
        trunc_arg = "month"
        if period == "daily":
            trunc_arg = "day"
        elif period == "weekly":
            trunc_arg = "week"

        fmt = "'YYYY-MM'" if trunc_arg == "month" else "'YYYY-MM-DD'"

        async with self._session_factory() as session:
            q = (
                select(
                    func.to_char(func.date_trunc(trunc_arg, A.shift_date), text(fmt)).label("period_label"),
                    func.count(ACC.id).label("total_cat"),
                    func.sum(case((ACC.is_completed.is_(True), 1), else_=0)).label("completed_cat"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
                .group_by(text("period_label"))
                .order_by(text("period_label"))
            )
            q = self._apply_scope_filters(q, payload, zone_id, facility_id, date_from, date_to, shift_type)
            rows = (await session.execute(q)).all()

        data = [
            TrendDataPoint(
                period=r.period_label,
                total_categories=r.total_cat or 0,
                completed_categories=r.completed_cat or 0,
                compliance_percent=self._compliance(r.completed_cat or 0, r.total_cat or 0),
            )
            for r in rows
        ]
        return AuditTrendsResponse(period=period, data=data)

    # ================================================================
    # 5. Category Breakdown
    # ================================================================

    async def category_breakdown(
        self,
        payload: dict,
        zone_id: str | None = None,
        facility_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> list[CategoryBreakdownResponse]:
        self._require_initialized()
        async with self._session_factory() as session:
            q = (
                select(
                    ACC.category_name,
                    func.count(ACC.id).label("total_occ"),
                    func.sum(case((ACC.is_completed.is_(True), 1), else_=0)).label("completed"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
                .group_by(ACC.category_name)
                .order_by(func.count(ACC.id).desc())
            )
            q = self._apply_scope_filters(q, payload, zone_id, facility_id, date_from, date_to, shift_type)
            rows = (await session.execute(q)).all()

        return [
            CategoryBreakdownResponse(
                category_name=r.category_name,
                total_occurrences=r.total_occ or 0,
                compliance_percent=self._compliance(r.completed or 0, r.total_occ or 0),
            )
            for r in rows
        ]

    # ================================================================
    # 6. Top Issues
    # ================================================================

    async def top_issues(
        self,
        payload: dict,
        zone_id: str | None = None,
        facility_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
        limit: int = 10,
    ) -> list[TopIssuesResponse]:
        self._require_initialized()
        async with self._session_factory() as session:
            q = (
                select(
                    ACP.checkpoint_name,
                    ACC.category_name,
                    func.count(ACC.id).label("total_occ"),
                    func.sum(case((ACC.is_completed.is_(False), 1), else_=0)).label("failure_count"),
                )
                .select_from(A)
                .join(ACP, ACP.audit_id == A.id)
                .join(ACC, ACC.audit_checkpoint_id == ACP.id)
                .group_by(ACP.checkpoint_name, ACC.category_name)
                .having(func.sum(case((ACC.is_completed.is_(False), 1), else_=0)) > 0)
                .order_by(func.sum(case((ACC.is_completed.is_(False), 1), else_=0)).desc())
                .limit(limit)
            )
            q = self._apply_scope_filters(q, payload, zone_id, facility_id, date_from, date_to, shift_type)
            rows = (await session.execute(q)).all()

        return [
            TopIssuesResponse(
                checkpoint_name=r.checkpoint_name,
                category_name=r.category_name,
                failure_count=r.failure_count or 0,
                total_occurrences=r.total_occ or 0,
                failure_rate=self._compliance(r.failure_count or 0, r.total_occ or 0),
            )
            for r in rows
        ]


_dashboard_service: DashboardService | None = None


def get_dashboard_service() -> DashboardService:
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service
