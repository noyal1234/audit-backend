from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload

from src.database.postgres.schema.audit_schema import (
    AuditCheckpointCategorySchema,
    AuditCheckpointSchema,
    AuditSchema,
)
from src.database.postgres.schema.facility_schema import FacilitySchema
from src.database.postgres.schema.zone_schema import ZoneSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.audit_schema import (
    AuditCheckpointCategoryResponse,
    AuditCheckpointResponse,
    AuditCreate,
    AuditDetailResponse,
    AuditProgressResponse,
    AuditResponse,
)


class AuditRepository(BasePostgresRepository[AuditSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, AuditSchema)

    def _schema_to_audit(self, row: AuditSchema) -> AuditResponse:
        return AuditResponse.model_validate(row)

    def _schema_to_detail(self, row: AuditSchema) -> AuditDetailResponse:
        checkpoints = []
        for acp in row.audit_checkpoints:
            cats = [AuditCheckpointCategoryResponse.model_validate(c) for c in acp.categories]
            checkpoints.append(AuditCheckpointResponse(
                id=acp.id,
                audit_id=acp.audit_id,
                checkpoint_id=acp.checkpoint_id,
                checkpoint_name=acp.checkpoint_name,
                image_url=acp.image_url,
                status_type=acp.status_type,
                created_at=acp.created_at,
                categories=cats,
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
            audit_checkpoints=checkpoints,
        )

    async def get_by_id(self, id: str) -> AuditResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_audit(row) if row else None

    async def get_detail(self, id: str) -> AuditDetailResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditSchema)
                .options(
                    selectinload(AuditSchema.audit_checkpoints)
                    .selectinload(AuditCheckpointSchema.categories)
                )
                .where(AuditSchema.id == id)
            )
            row = result.scalar_one_or_none()
        if not row:
            return None
        return self._schema_to_detail(row)

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
        checkpoints_with_categories: list[dict],
    ) -> AuditDetailResponse:
        """Create audit + snapshot all checkpoints and their categories in a single transaction."""
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
            for cp in checkpoints_with_categories:
                acp_id = str(uuid4())
                acp = AuditCheckpointSchema(
                    id=acp_id,
                    audit_id=audit_id,
                    checkpoint_id=cp["checkpoint_id"],
                    checkpoint_name=cp["checkpoint_name"],
                    image_url=cp["image_url"],
                    status_type="PENDING",
                )
                session.add(acp)
                for cat in cp.get("categories", []):
                    acc = AuditCheckpointCategorySchema(
                        id=str(uuid4()),
                        audit_checkpoint_id=acp_id,
                        category_id=cat["category_id"],
                        category_name=cat["category_name"],
                        is_completed=False,
                    )
                    session.add(acc)
            await session.commit()
            result = await session.execute(
                select(AuditSchema)
                .options(
                    selectinload(AuditSchema.audit_checkpoints)
                    .selectinload(AuditCheckpointSchema.categories)
                )
                .where(AuditSchema.id == audit_id)
            )
            row = result.scalar_one()
        return self._schema_to_detail(row)

    async def delete(self, audit_id: str) -> bool:
        """Delete audit by id. Cascade removes audit_checkpoint and audit_checkpoint_category. Returns False if not found."""
        async with self._session_factory() as session:
            result = await session.execute(select(AuditSchema).where(AuditSchema.id == audit_id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def update_status(self, id: str, status_type: str, finalized_at: datetime | None = None) -> AuditResponse | None:
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
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditSchema)
                .options(
                    selectinload(AuditSchema.audit_checkpoints)
                    .selectinload(AuditCheckpointSchema.categories)
                )
                .where(AuditSchema.id == id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            total_cp = len(row.audit_checkpoints)
            completed_cp = sum(1 for cp in row.audit_checkpoints if cp.status_type == "COMPLETED")
            total_cat = sum(len(cp.categories) for cp in row.audit_checkpoints)
            completed_cat = sum(
                1 for cp in row.audit_checkpoints for c in cp.categories if c.is_completed
            )
            pct = (completed_cat / total_cat * 100.0) if total_cat > 0 else 0.0
        return AuditProgressResponse(
            audit_id=row.id,
            status_type=row.status_type,
            total_checkpoints=total_cp,
            completed_checkpoints=completed_cp,
            total_categories=total_cat,
            completed_categories=completed_cat,
            completion_percentage=round(pct, 2),
        )


class AuditCheckpointCategoryRepository:
    """Handles completion of individual audit checkpoint categories."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_id(self, id: str) -> AuditCheckpointCategoryResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointCategorySchema).where(AuditCheckpointCategorySchema.id == id)
            )
            row = result.scalar_one_or_none()
        return AuditCheckpointCategoryResponse.model_validate(row) if row else None

    async def get_audit_checkpoint_for_category(self, category_id: str) -> AuditCheckpointResponse | None:
        """Return the audit checkpoint snapshot that owns this category (for ownership checks and AI context)."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointCategorySchema)
                .options(selectinload(AuditCheckpointCategorySchema.audit_checkpoint))
                .where(AuditCheckpointCategorySchema.id == category_id)
            )
            cat_row = result.scalar_one_or_none()
            if not cat_row or not cat_row.audit_checkpoint:
                return None
            cp = cat_row.audit_checkpoint
        return AuditCheckpointResponse(
            id=cp.id,
            audit_id=cp.audit_id,
            checkpoint_id=cp.checkpoint_id,
            checkpoint_name=cp.checkpoint_name,
            image_url=cp.image_url,
            status_type=cp.status_type,
            created_at=cp.created_at,
            categories=[],
        )

    async def get_with_checkpoint(self, id: str) -> tuple[AuditCheckpointCategorySchema | None, AuditCheckpointSchema | None]:
        """Return both the category row and its parent checkpoint (for status computation)."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointCategorySchema)
                .options(
                    selectinload(AuditCheckpointCategorySchema.audit_checkpoint)
                    .selectinload(AuditCheckpointSchema.categories)
                )
                .where(AuditCheckpointCategorySchema.id == id)
            )
            cat_row = result.scalar_one_or_none()
            if not cat_row:
                return None, None
            return cat_row, cat_row.audit_checkpoint

    async def mark_complete(
        self,
        id: str,
        completed_by: str,
        completed_at: datetime,
        remarks: str | None = None,
    ) -> AuditCheckpointCategoryResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointCategorySchema).where(AuditCheckpointCategorySchema.id == id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            row.is_completed = True
            row.completed_by = completed_by
            row.completed_at = completed_at
            if remarks is not None:
                row.remarks = remarks
            await session.commit()
            await session.refresh(row)
            return AuditCheckpointCategoryResponse.model_validate(row)

    async def mark_uncomplete(self, id: str) -> AuditCheckpointCategoryResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointCategorySchema).where(AuditCheckpointCategorySchema.id == id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            row.is_completed = False
            row.completed_by = None
            row.completed_at = None
            row.remarks = None
            await session.commit()
            await session.refresh(row)
            return AuditCheckpointCategoryResponse.model_validate(row)

    async def update_remarks(self, id: str, remarks: str | None) -> AuditCheckpointCategoryResponse | None:
        """Update only the remarks field. Does not change is_completed or completed_by/completed_at."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointCategorySchema).where(AuditCheckpointCategorySchema.id == id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            row.remarks = remarks
            await session.commit()
            await session.refresh(row)
            return AuditCheckpointCategoryResponse.model_validate(row)

    async def update_checkpoint_status(self, audit_checkpoint_id: str) -> str:
        """Recompute checkpoint status based on its categories. Returns new status."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointSchema)
                .options(selectinload(AuditCheckpointSchema.categories))
                .where(AuditCheckpointSchema.id == audit_checkpoint_id)
            )
            cp = result.scalar_one_or_none()
            if not cp:
                return "PENDING"
            all_done = all(c.is_completed for c in cp.categories) if cp.categories else False
            new_status = "COMPLETED" if all_done else "PENDING"
            if cp.status_type != new_status:
                cp.status_type = new_status
                await session.commit()
            return new_status

    async def recompute_audit_status(self, audit_id: str) -> str:
        """Recompute audit status based on all checkpoints. Returns new status."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditSchema)
                .options(selectinload(AuditSchema.audit_checkpoints))
                .where(AuditSchema.id == audit_id)
            )
            audit = result.scalar_one_or_none()
            if not audit:
                return "PENDING"
            if audit.status_type == "FINALIZED":
                return "FINALIZED"
            cps = audit.audit_checkpoints
            if not cps:
                return audit.status_type
            completed = sum(1 for cp in cps if cp.status_type == "COMPLETED")
            if completed == 0:
                new_status = "PENDING"
            elif completed == len(cps):
                new_status = "COMPLETED"
            else:
                new_status = "IN_PROGRESS"
            if audit.status_type == "REOPENED" and new_status in ("PENDING", "IN_PROGRESS"):
                new_status = "REOPENED"
            if audit.status_type != new_status:
                audit.status_type = new_status
                await session.commit()
            return new_status
