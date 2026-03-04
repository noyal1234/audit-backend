"""Analytics aggregation. Uses audit -> audit_area -> audit_sub_area -> audit_checkpoint and effective review (latest per checkpoint). Completion = is_completed; compliance = latest review.compliant."""

from datetime import date

from sqlalchemy import Select, case, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.audit_schema import AuditSchema
from src.database.postgres.schema.audit_area_schema import AuditAreaSchema
from src.database.postgres.schema.audit_sub_area_schema import AuditSubAreaSchema
from src.database.postgres.schema.audit_checkpoint_schema import AuditCheckpointSchema
from src.database.postgres.schema.facility_schema import FacilitySchema
from src.database.postgres.schema.zone_schema import ZoneSchema
from src.database.repositories.audit_checkpoint_review_repository import get_latest_review_per_checkpoint_subquery
from src.database.repositories.schemas.dashboard_schema import (
    AuditTrendsResponse,
    CheckpointBreakdownResponse,
    CheckpointComplianceItem,
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

A = AuditSchema
AA = AuditAreaSchema
SA = AuditSubAreaSchema
ACP = AuditCheckpointSchema
F = FacilitySchema
Z = ZoneSchema


def _pct(num: int | float, denom: int | float) -> float:
    return round((num / denom * 100.0), 2) if denom and denom > 0 else 0.0


def _avg_score(val) -> float:
    return round(float(val), 2) if val is not None else 0.0


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
        role = payload.get("role_type")
        if role == "SUPER_ADMIN":
            pass
        elif role == "STELLANTIS_ADMIN":
            country_id = payload.get("country_id")
            if not country_id:
                raise ForbiddenError("STELLANTIS_ADMIN requires country_id in token")
            country_fac = select(F.id).join(Z, F.zone_id == Z.id).where(Z.country_id == country_id)
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
        LR = get_latest_review_per_checkpoint_subquery()
        async with self._session_factory() as session:
            base = (
                select(
                    func.count(func.distinct(A.id)).label("total_audits"),
                    func.count(func.distinct(A.facility_id)).label("total_facilities"),
                    func.sum(case((A.status_type == "COMPLETED", 1), (A.status_type == "FINALIZED", 1), else_=0)).label("audits_done"),
                    func.sum(case((A.status_type == "IN_PROGRESS", 1), else_=0)).label("audits_in_progress"),
                    func.count(ACP.id).label("total_cp"),
                    func.sum(case((ACP.is_completed.is_(True), 1), else_=0)).label("completed_cp"),
                    func.sum(case((LR.c.compliant.is_(True), 1), else_=0)).label("compliant_cp"),
                    func.avg(LR.c.score).label("avg_score"),
                )
                .select_from(A)
                .join(AA, AA.audit_id == A.id)
                .join(SA, SA.audit_area_id == AA.id)
                .join(ACP, ACP.audit_sub_area_id == SA.id)
                .outerjoin(LR, ACP.id == LR.c.audit_checkpoint_id)
            )
            base = self._apply_scope_filters(base, payload, zone_id, facility_id, date_from, date_to, shift_type)
            row = (await session.execute(base)).one_or_none()
            total_audits = (row.total_audits or 0) if row else 0
            total_facilities = (row.total_facilities or 0) if row else 0
            total_cp = (row.total_cp or 0) if row else 0
            completed_cp = (row.completed_cp or 0) if row else 0
            compliant_cp = (row.compliant_cp or 0) if row else 0
            completion_pct = _pct(completed_cp, total_cp)
            compliance_pct = _pct(compliant_cp, total_cp)
            avg_score = _avg_score(row.avg_score if row else None)
            audits_completed = (row.audits_done or 0) if row else 0
            audits_in_progress = (row.audits_in_progress or 0) if row else 0

            trend_q = (
                select(
                    func.to_char(A.shift_date, text("'YYYY-MM'")).label("month"),
                    func.count(ACP.id).label("total_cp"),
                    func.sum(case((ACP.is_completed.is_(True), 1), else_=0)).label("completed_cp"),
                    func.sum(case((LR.c.compliant.is_(True), 1), else_=0)).label("compliant_cp"),
                )
                .select_from(A)
                .join(AA, AA.audit_id == A.id)
                .join(SA, SA.audit_area_id == AA.id)
                .join(ACP, ACP.audit_sub_area_id == SA.id)
                .outerjoin(LR, ACP.id == LR.c.audit_checkpoint_id)
                .group_by(func.to_char(A.shift_date, text("'YYYY-MM'")))
                .order_by(func.to_char(A.shift_date, text("'YYYY-MM'")))
            )
            trend_q = self._apply_scope_filters(trend_q, payload, zone_id, facility_id, date_from, date_to, shift_type)
            trend_rows = (await session.execute(trend_q)).all()

        monthly_trend = [
            MonthlyTrendItem(
                month=r.month,
                completion_percent=_pct(r.completed_cp or 0, r.total_cp or 0),
                compliance_percent=_pct(r.compliant_cp or 0, r.total_cp or 0),
            )
            for r in trend_rows
        ]
        return CountrySummaryResponse(
            total_audits=total_audits,
            total_facilities=total_facilities,
            audits_completed=audits_completed,
            audits_in_progress=audits_in_progress,
            completion_percent=completion_pct,
            compliance_percent=compliance_pct,
            average_score=avg_score,
            monthly_trend=monthly_trend,
        )

    async def zone_summary(
        self,
        payload: dict,
        zone_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> ZoneSummaryResponse:
        self._require_initialized()
        LR = get_latest_review_per_checkpoint_subquery()
        async with self._session_factory() as session:
            zone_row = (await session.execute(select(Z).where(Z.id == zone_id))).scalar_one_or_none()
            if zone_row and zone_row.country_id:
                role = payload.get("role_type")
                if role == "STELLANTIS_ADMIN" and payload.get("country_id") != zone_row.country_id:
                    raise ForbiddenError("Access denied to this zone")

            agg_q = (
                select(
                    func.count(func.distinct(A.id)).label("audit_count"),
                    func.count(ACP.id).label("total_cp"),
                    func.sum(case((ACP.is_completed.is_(True), 1), else_=0)).label("completed_cp"),
                    func.sum(case((LR.c.compliant.is_(True), 1), else_=0)).label("compliant_cp"),
                    func.avg(LR.c.score).label("avg_score"),
                )
                .select_from(A)
                .join(AA, AA.audit_id == A.id)
                .join(SA, SA.audit_area_id == AA.id)
                .join(ACP, ACP.audit_sub_area_id == SA.id)
                .outerjoin(LR, ACP.id == LR.c.audit_checkpoint_id)
            )
            agg_q = self._apply_scope_filters(agg_q, payload, zone_id=zone_id, date_from=date_from, date_to=date_to, shift_type=shift_type)
            row = (await session.execute(agg_q)).one_or_none()
            audit_count = (row.audit_count or 0) if row else 0
            total_cp = (row.total_cp or 0) if row else 0
            completed_cp = (row.completed_cp or 0) if row else 0
            compliant_cp = (row.compliant_cp or 0) if row else 0
            completion_pct = _pct(completed_cp, total_cp)
            compliance_pct = _pct(compliant_cp, total_cp)
            zone_avg_score = _avg_score(row.avg_score if row else None)

            rank_q = (
                select(
                    A.facility_id,
                    F.name.label("facility_name"),
                    func.count(ACP.id).label("total_cp"),
                    func.sum(case((ACP.is_completed.is_(True), 1), else_=0)).label("completed_cp"),
                    func.sum(case((LR.c.compliant.is_(True), 1), else_=0)).label("compliant_cp"),
                    func.avg(LR.c.score).label("avg_score"),
                )
                .select_from(A)
                .join(AA, AA.audit_id == A.id)
                .join(SA, SA.audit_area_id == AA.id)
                .join(ACP, ACP.audit_sub_area_id == SA.id)
                .join(F, A.facility_id == F.id)
                .outerjoin(LR, ACP.id == LR.c.audit_checkpoint_id)
                .group_by(A.facility_id, F.name)
            )
            rank_q = self._apply_scope_filters(rank_q, payload, zone_id=zone_id, date_from=date_from, date_to=date_to, shift_type=shift_type)
            rank_rows = (await session.execute(rank_q)).all()

        facility_ranking = sorted(
            [
                FacilityRankingItem(
                    facility_id=r.facility_id,
                    facility_name=r.facility_name,
                    compliance_percent=_pct(r.compliant_cp or 0, r.total_cp or 0),
                    average_score=_avg_score(r.avg_score),
                )
                for r in rank_rows
            ],
            key=lambda x: x.compliance_percent,
            reverse=True,
        )
        return ZoneSummaryResponse(
            zone_id=zone_id,
            audit_count=audit_count,
            completion_percent=completion_pct,
            compliance_percent=compliance_pct,
            average_score=zone_avg_score,
            facility_ranking=facility_ranking,
        )

    async def facility_summary(
        self,
        payload: dict,
        facility_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> FacilitySummaryResponse:
        self._require_initialized()
        LR = get_latest_review_per_checkpoint_subquery()
        async with self._session_factory() as session:
            shift_q = (
                select(
                    A.shift_type,
                    func.count(ACP.id).label("total_cp"),
                    func.sum(case((ACP.is_completed.is_(True), 1), else_=0)).label("completed_cp"),
                    func.sum(case((LR.c.compliant.is_(True), 1), else_=0)).label("compliant_cp"),
                    func.avg(LR.c.score).label("avg_score"),
                )
                .select_from(A)
                .join(AA, AA.audit_id == A.id)
                .join(SA, SA.audit_area_id == AA.id)
                .join(ACP, ACP.audit_sub_area_id == SA.id)
                .outerjoin(LR, ACP.id == LR.c.audit_checkpoint_id)
                .group_by(A.shift_type)
            )
            shift_q = self._apply_scope_filters(shift_q, payload, facility_id=facility_id, date_from=date_from, date_to=date_to, shift_type=shift_type)
            shift_rows = (await session.execute(shift_q)).all()

            cp_compliance_q = (
                select(
                    ACP.checkpoint_name,
                    func.count(ACP.id).label("total_occ"),
                    func.sum(case((ACP.is_completed.is_(True), 1), else_=0)).label("completed"),
                    func.sum(case((LR.c.compliant.is_(True), 1), else_=0)).label("compliant"),
                    func.avg(LR.c.score).label("avg_score"),
                )
                .select_from(A)
                .join(AA, AA.audit_id == A.id)
                .join(SA, SA.audit_area_id == AA.id)
                .join(ACP, ACP.audit_sub_area_id == SA.id)
                .outerjoin(LR, ACP.id == LR.c.audit_checkpoint_id)
                .group_by(ACP.checkpoint_name)
            )
            cp_compliance_q = self._apply_scope_filters(cp_compliance_q, payload, facility_id=facility_id, date_from=date_from, date_to=date_to, shift_type=shift_type)
            cp_compliance_rows = (await session.execute(cp_compliance_q)).all()

            failure_q = (
                select(
                    ACP.checkpoint_name,
                    func.count(ACP.id).label("total_cp"),
                    func.sum(case((LR.c.compliant.is_(False), 1), else_=0)).label("non_compliant"),
                )
                .select_from(A)
                .join(AA, AA.audit_id == A.id)
                .join(SA, SA.audit_area_id == AA.id)
                .join(ACP, ACP.audit_sub_area_id == SA.id)
                .outerjoin(LR, ACP.id == LR.c.audit_checkpoint_id)
                .group_by(ACP.checkpoint_name)
            )
            failure_q = self._apply_scope_filters(failure_q, payload, facility_id=facility_id, date_from=date_from, date_to=date_to, shift_type=shift_type)
            failure_rows = (await session.execute(failure_q)).all()

        shift_performance = [
            ShiftPerformanceItem(
                shift_type=r.shift_type,
                total_checkpoints=r.total_cp or 0,
                completed_checkpoints=r.completed_cp or 0,
                compliant_checkpoints=r.compliant_cp or 0,
                completion_percent=_pct(r.completed_cp or 0, r.total_cp or 0),
                compliance_percent=_pct(r.compliant_cp or 0, r.total_cp or 0),
                average_score=_avg_score(r.avg_score),
            )
            for r in shift_rows
        ]
        checkpoint_compliance = [
            CheckpointComplianceItem(
                checkpoint_name=r.checkpoint_name,
                total_occurrences=r.total_occ or 0,
                completed=r.completed or 0,
                compliant=r.compliant or 0,
                completion_percent=_pct(r.completed or 0, r.total_occ or 0),
                compliance_percent=_pct(r.compliant or 0, r.total_occ or 0),
                average_score=_avg_score(r.avg_score),
            )
            for r in cp_compliance_rows
        ]
        failure_rate_per_checkpoint = [
            CheckpointFailureItem(
                checkpoint_name=r.checkpoint_name,
                total_checkpoints=r.total_cp or 0,
                non_compliant_count=r.non_compliant or 0,
                failure_rate=_pct(r.non_compliant or 0, r.total_cp or 0),
            )
            for r in failure_rows
        ]
        return FacilitySummaryResponse(
            facility_id=facility_id,
            shift_performance=shift_performance,
            checkpoint_compliance=checkpoint_compliance,
            failure_rate_per_checkpoint=failure_rate_per_checkpoint,
        )

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
        LR = get_latest_review_per_checkpoint_subquery()
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
                    func.count(ACP.id).label("total_cp"),
                    func.sum(case((ACP.is_completed.is_(True), 1), else_=0)).label("completed_cp"),
                    func.sum(case((LR.c.compliant.is_(True), 1), else_=0)).label("compliant_cp"),
                )
                .select_from(A)
                .join(AA, AA.audit_id == A.id)
                .join(SA, SA.audit_area_id == AA.id)
                .join(ACP, ACP.audit_sub_area_id == SA.id)
                .outerjoin(LR, ACP.id == LR.c.audit_checkpoint_id)
                .group_by(text("period_label"))
                .order_by(text("period_label"))
            )
            q = self._apply_scope_filters(q, payload, zone_id, facility_id, date_from, date_to, shift_type)
            rows = (await session.execute(q)).all()

        data = [
            TrendDataPoint(
                period=r.period_label,
                completion_percent=_pct(r.completed_cp or 0, r.total_cp or 0),
                compliance_percent=_pct(r.compliant_cp or 0, r.total_cp or 0),
                total_checkpoints=r.total_cp or 0,
                completed_checkpoints=r.completed_cp or 0,
                compliant_checkpoints=r.compliant_cp or 0,
            )
            for r in rows
        ]
        return AuditTrendsResponse(period=period, data=data)

    async def category_breakdown(
        self,
        payload: dict,
        zone_id: str | None = None,
        facility_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        shift_type: str | None = None,
    ) -> list[CheckpointBreakdownResponse]:
        self._require_initialized()
        LR = get_latest_review_per_checkpoint_subquery()
        async with self._session_factory() as session:
            q = (
                select(
                    ACP.checkpoint_name,
                    func.count(ACP.id).label("total_occ"),
                    func.sum(case((LR.c.compliant.is_(True), 1), else_=0)).label("compliant"),
                    func.avg(LR.c.score).label("avg_score"),
                )
                .select_from(A)
                .join(AA, AA.audit_id == A.id)
                .join(SA, SA.audit_area_id == AA.id)
                .join(ACP, ACP.audit_sub_area_id == SA.id)
                .outerjoin(LR, ACP.id == LR.c.audit_checkpoint_id)
                .group_by(ACP.checkpoint_name)
                .order_by(func.count(ACP.id).desc())
            )
            q = self._apply_scope_filters(q, payload, zone_id, facility_id, date_from, date_to, shift_type)
            rows = (await session.execute(q)).all()

        return [
            CheckpointBreakdownResponse(
                checkpoint_name=r.checkpoint_name,
                compliance_percent=_pct(r.compliant or 0, r.total_occ or 0),
                total_occurrences=r.total_occ or 0,
                average_score=_avg_score(r.avg_score),
            )
            for r in rows
        ]

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
        LR = get_latest_review_per_checkpoint_subquery()
        async with self._session_factory() as session:
            q = (
                select(
                    ACP.checkpoint_name,
                    func.count(ACP.id).label("total_occ"),
                    func.sum(case((LR.c.compliant.is_(False), 1), else_=0)).label("non_compliant_count"),
                )
                .select_from(A)
                .join(AA, AA.audit_id == A.id)
                .join(SA, SA.audit_area_id == AA.id)
                .join(ACP, ACP.audit_sub_area_id == SA.id)
                .outerjoin(LR, ACP.id == LR.c.audit_checkpoint_id)
                .group_by(ACP.checkpoint_name)
                .having(func.sum(case((LR.c.compliant.is_(False), 1), else_=0)) > 0)
                .order_by(func.sum(case((LR.c.compliant.is_(False), 1), else_=0)).desc())
                .limit(limit)
            )
            q = self._apply_scope_filters(q, payload, zone_id, facility_id, date_from, date_to, shift_type)
            rows = (await session.execute(q)).all()

        return [
            TopIssuesResponse(
                checkpoint_name=r.checkpoint_name,
                non_compliant_count=r.non_compliant_count or 0,
                total_occurrences=r.total_occ or 0,
                failure_rate=_pct(r.non_compliant_count or 0, r.total_occ or 0),
            )
            for r in rows
        ]


_dashboard_service: DashboardService | None = None


def get_dashboard_service() -> DashboardService:
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service
