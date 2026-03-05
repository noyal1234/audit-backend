"""Audit repository: snapshot tree (audit_area -> audit_sub_area -> audit_checkpoint)."""

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload

from src.database.postgres.schema.audit_schema import AuditSchema
from src.database.postgres.schema.audit_area_schema import AuditAreaSchema
from src.database.postgres.schema.audit_sub_area_schema import AuditSubAreaSchema
from src.database.postgres.schema.audit_checkpoint_schema import AuditCheckpointSchema
from src.database.postgres.schema.facility_schema import FacilitySchema
from src.database.postgres.schema.zone_schema import ZoneSchema
from src.database.repositories.schemas.audit_schema import (
    AuditCreate,
    AuditDetailResponse,
    AuditProgressResponse,
    AuditQualityScoreResponse,
    AuditResponse,
    AuditAreaResponse,
    AuditSubAreaResponse,
    AuditCheckpointResponse,
)
from src.database.repositories.schemas.area_schema import AreaWithChildrenResponse
from src.database.repositories.schemas.review_schema import AuditCheckpointReviewResponse, EffectiveReviewResponse
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.audit_checkpoint_review_repository import AuditCheckpointReviewRepository


class AuditRepository(BasePostgresRepository[AuditSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, AuditSchema)
        self._review_repo: AuditCheckpointReviewRepository | None = None

    def set_review_repository(self, repo: AuditCheckpointReviewRepository) -> None:
        self._review_repo = repo

    def _schema_to_audit(self, row: AuditSchema) -> AuditResponse:
        return AuditResponse.model_validate(row)

    def _build_detail(
        self,
        row: AuditSchema,
        effective_reviews: list[AuditCheckpointReviewResponse] | None = None,
    ) -> AuditDetailResponse:
        review_by_cp = {r.audit_checkpoint_id: r for r in (effective_reviews or [])}
        areas_out = []
        for aa in row.audit_areas:
            sub_areas_out = []
            for sa in aa.sub_areas:
                checkpoints_out = []
                for cp in sa.checkpoints:
                    er = review_by_cp.get(cp.id)
                    effective_review = (
                        EffectiveReviewResponse(
                            review_id=er.id,
                            review_type=er.review_type,
                            media_id=er.media_id,
                            compliant=er.compliant,
                            score=er.score,
                            remarks=er.remarks,
                            confidence=er.confidence,
                        )
                        if er else None
                    )
                    checkpoints_out.append(AuditCheckpointResponse(
                        id=cp.id,
                        audit_sub_area_id=cp.audit_sub_area_id,
                        checkpoint_name=cp.checkpoint_name,
                        description=cp.description,
                        is_completed=cp.is_completed,
                        created_at=cp.created_at,
                        updated_at=cp.updated_at,
                        effective_review=effective_review,
                    ))
                sub_areas_out.append(AuditSubAreaResponse(
                    id=sa.id,
                    audit_area_id=sa.audit_area_id,
                    sub_area_name=sa.sub_area_name,
                    created_at=sa.created_at,
                    checkpoints=checkpoints_out,
                ))
            areas_out.append(AuditAreaResponse(
                id=aa.id,
                audit_id=aa.audit_id,
                area_name=aa.area_name,
                created_at=aa.created_at,
                sub_areas=sub_areas_out,
            ))
        return AuditDetailResponse(
            id=row.id,
            facility_id=row.facility_id,
            shift_type=row.shift_type,
            shift_date=row.shift_date,
            status_type=row.status_type,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
            finalized_at=row.finalized_at,
            audit_areas=areas_out,
        )

    async def get_by_id(self, id: str) -> AuditResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_audit(row) if row else None

    async def get_detail(self, id: str) -> AuditDetailResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditSchema)
                .options(
                    selectinload(AuditSchema.audit_areas)
                    .selectinload(AuditAreaSchema.sub_areas)
                    .selectinload(AuditSubAreaSchema.checkpoints)
                )
                .where(AuditSchema.id == id)
            )
            row = result.scalar_one_or_none()
        if not row:
            return None
        effective = []
        if self._review_repo:
            effective = await self._review_repo.get_effective_reviews_for_audit(id)
        return self._build_detail(row, effective)

    async def find_by_facility_shift_date(
        self,
        facility_id: str,
        shift_type: str,
        shift_date: date,
    ) -> AuditResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditSchema).where(
                    AuditSchema.facility_id == facility_id,
                    AuditSchema.shift_type == shift_type,
                    AuditSchema.shift_date == shift_date,
                )
            )
            row = result.scalar_one_or_none()
        return self._schema_to_audit(row) if row else None

    async def list_audits(
        self,
        *,
        zone_id: str | None = None,
        country_id: str | None = None,
        facility_id: str | None = None,
        shift_type: str | None = None,
        shift_date: date | None = None,
        status_type: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
        facility_ids: list[str] | None = None,
    ) -> tuple[list[AuditResponse], int]:
        async with self._session_factory() as session:
            q = select(AuditSchema)
            count_q = select(func.count()).select_from(AuditSchema)
            if facility_ids is not None:
                q = q.where(AuditSchema.facility_id.in_(facility_ids))
                count_q = count_q.where(AuditSchema.facility_id.in_(facility_ids))
            if facility_id:
                q = q.where(AuditSchema.facility_id == facility_id)
                count_q = count_q.where(AuditSchema.facility_id == facility_id)
            if zone_id:
                subq = select(FacilitySchema.id).where(FacilitySchema.zone_id == zone_id)
                q = q.where(AuditSchema.facility_id.in_(subq))
                count_q = count_q.where(AuditSchema.facility_id.in_(subq))
            if country_id:
                subq = (
                    select(FacilitySchema.id)
                    .select_from(FacilitySchema)
                    .join(ZoneSchema, FacilitySchema.zone_id == ZoneSchema.id)
                    .where(ZoneSchema.country_id == country_id)
                )
                q = q.where(AuditSchema.facility_id.in_(subq))
                count_q = count_q.where(AuditSchema.facility_id.in_(subq))
            if shift_type:
                q = q.where(AuditSchema.shift_type == shift_type)
                count_q = count_q.where(AuditSchema.shift_type == shift_type)
            if shift_date:
                q = q.where(AuditSchema.shift_date == shift_date)
                count_q = count_q.where(AuditSchema.shift_date == shift_date)
            if status_type:
                q = q.where(AuditSchema.status_type == status_type)
                count_q = count_q.where(AuditSchema.status_type == status_type)
            total = (await session.execute(count_q)).scalar() or 0
            order_col = getattr(AuditSchema, sort, AuditSchema.created_at)
            q = q.order_by(order_col.desc() if order == "desc" else order_col.asc())
            q = q.offset(offset).limit(limit)
            result = await session.execute(q)
            rows = result.scalars().all()
        return [self._schema_to_audit(r) for r in rows], total

    async def create_with_snapshot(
        self,
        data: AuditCreate,
        created_by: str,
        hierarchy: list[AreaWithChildrenResponse],
    ) -> AuditDetailResponse:
        """Create audit + snapshot full tree (areas -> sub_areas -> checkpoints). No review rows."""
        async with self._session_factory() as session:
            audit_id = str(uuid4())
            audit = AuditSchema(
                id=audit_id,
                facility_id=data.facility_id,
                shift_type=data.shift_type,
                shift_date=data.shift_date,
                status_type="PENDING",
                created_by=created_by,
            )
            session.add(audit)
            for area in hierarchy:
                aa_id = str(uuid4())
                aa = AuditAreaSchema(id=aa_id, audit_id=audit_id, area_name=area.name)
                session.add(aa)
                for sub in area.sub_areas:
                    sa_id = str(uuid4())
                    sa = AuditSubAreaSchema(id=sa_id, audit_area_id=aa_id, sub_area_name=sub.name)
                    session.add(sa)
                    for cp in sub.checkpoints:
                        acp = AuditCheckpointSchema(
                            id=str(uuid4()),
                            audit_sub_area_id=sa_id,
                            checkpoint_name=cp.name,
                            description=cp.description,
                            is_completed=False,
                        )
                        session.add(acp)
            await session.commit()
        detail = await self.get_detail(audit_id)
        if not detail:
            raise RuntimeError("Audit created but get_detail returned None")
        return detail

    async def delete(self, audit_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(AuditSchema).where(AuditSchema.id == audit_id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def update_status(
        self, id: str, status_type: str, finalized_at: datetime | None = None
    ) -> AuditResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(AuditSchema).where(AuditSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            row.status_type = status_type
            row.finalized_at = finalized_at
            await session.commit()
            await session.refresh(row)
            return self._schema_to_audit(row)

    async def get_progress(self, id: str) -> AuditProgressResponse | None:
        detail = await self.get_detail(id)
        if not detail:
            return None
        total = 0
        completed = 0
        for aa in detail.audit_areas:
            for sa in aa.sub_areas:
                for cp in sa.checkpoints:
                    total += 1
                    if cp.is_completed:
                        completed += 1
        pct = (completed / total * 100.0) if total > 0 else 0.0
        compliant_count = 0
        scores: list[float] = []
        for aa in detail.audit_areas:
            for sa in aa.sub_areas:
                for cp in sa.checkpoints:
                    if cp.effective_review and cp.effective_review.compliant:
                        compliant_count += 1
                    if cp.effective_review is not None and cp.effective_review.score is not None:
                        scores.append(cp.effective_review.score)
        compliance_pct = (compliant_count / total * 100.0) if total > 0 else 0.0
        reviewed = len(scores)
        average_score = round(sum(scores) / reviewed, 2) if reviewed > 0 else 0.0
        return AuditProgressResponse(
            audit_id=id,
            status_type=detail.status_type,
            total_checkpoints=total,
            completed_checkpoints=completed,
            completion_percentage=round(pct, 2),
            compliant_checkpoints=compliant_count,
            compliance_percentage=round(compliance_pct, 2),
            reviewed_checkpoints=reviewed,
            average_score=average_score,
        )

    async def get_quality_score(self, audit_id: str) -> AuditQualityScoreResponse | None:
        """Average score from effective reviews. Checkpoints without a review are excluded."""
        detail = await self.get_detail(audit_id)
        if not detail:
            return None
        scores: list[float] = []
        for aa in detail.audit_areas:
            for sa in aa.sub_areas:
                for cp in sa.checkpoints:
                    if cp.effective_review is not None and cp.effective_review.score is not None:
                        scores.append(cp.effective_review.score)
        reviewed = len(scores)
        average_score = round(sum(scores) / reviewed, 2) if reviewed > 0 else 0.0
        return AuditQualityScoreResponse(
            audit_id=audit_id,
            reviewed_checkpoints=reviewed,
            average_score=average_score,
        )

    async def get_checkpoint_by_id(self, checkpoint_id: str, audit_id: str) -> AuditCheckpointSchema | None:
        """Return audit_checkpoint if it belongs to this audit (for PATCH review / AI context). Loads audit_sub_area and audit_area for hierarchy names."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointSchema)
                .options(
                    selectinload(AuditCheckpointSchema.audit_sub_area).selectinload(AuditSubAreaSchema.audit_area)
                )
                .join(AuditSubAreaSchema, AuditCheckpointSchema.audit_sub_area_id == AuditSubAreaSchema.id)
                .join(AuditAreaSchema, AuditSubAreaSchema.audit_area_id == AuditAreaSchema.id)
                .where(
                    AuditCheckpointSchema.id == checkpoint_id,
                    AuditAreaSchema.audit_id == audit_id,
                )
            )
            return result.scalar_one_or_none()

    async def mark_checkpoint_completed(
        self, audit_checkpoint_id: str, remarks: str | None = None
    ) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointSchema).where(AuditCheckpointSchema.id == audit_checkpoint_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            row.is_completed = True
            await session.commit()
            return True

    async def mark_checkpoint_incomplete(self, audit_checkpoint_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointSchema).where(AuditCheckpointSchema.id == audit_checkpoint_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            row.is_completed = False
            await session.commit()
            return True
