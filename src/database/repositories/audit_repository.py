from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.audit_schema import AuditCheckpointResultSchema, AuditSchema
from src.database.postgres.schema.facility_schema import FacilitySchema
from src.database.postgres.schema.zone_schema import ZoneSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.audit_schema import (
    AuditCreate,
    AuditResponse,
    CheckpointResultCreate,
    CheckpointResultResponse,
)


class AuditRepository(BasePostgresRepository[AuditSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, AuditSchema)

    def _schema_to_audit(self, row: AuditSchema) -> AuditResponse:
        return AuditResponse.model_validate(row)

    async def get_by_id(self, id: str) -> AuditResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_audit(row) if row else None

    async def get_audit_schema_by_id(self, id: str) -> AuditSchema | None:
        return await self._get_by_id_raw(id)

    async def find_by_facility_shift_date(
        self,
        facility_id: str,
        shift_type: str,
        shift_date: date,
    ) -> AuditSchema | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditSchema).where(
                    AuditSchema.facility_id == facility_id,
                    AuditSchema.shift_type == shift_type,
                    AuditSchema.shift_date == shift_date,
                )
            )
            return result.scalar_one_or_none()

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

    async def create(self, data: AuditCreate, created_by: str, status_type: str = "IN_PROGRESS") -> AuditResponse:
        async with self._session_factory() as session:
            row = AuditSchema(
                id=str(uuid4()),
                facility_id=data.facility_id,
                shift_type=data.shift_type,
                shift_date=data.shift_date,
                status_type=status_type,
                created_by=created_by,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_audit(row)

    async def finalize(self, id: str, finalized_at: datetime) -> AuditResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(AuditSchema).where(AuditSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            row.status_type = "FINALIZED"
            row.finalized_at = finalized_at
            await session.commit()
            await session.refresh(row)
            return self._schema_to_audit(row)

    async def reopen(self, id: str) -> AuditResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(AuditSchema).where(AuditSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            row.status_type = "IN_PROGRESS"
            row.finalized_at = None
            await session.commit()
            await session.refresh(row)
            return self._schema_to_audit(row)


class AuditCheckpointResultRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def _schema_to_result(self, row: AuditCheckpointResultSchema) -> CheckpointResultResponse:
        return CheckpointResultResponse.model_validate(row)

    async def get_or_create_result(
        self,
        audit_id: str,
        checkpoint_id: str,
        data: CheckpointResultCreate,
    ) -> CheckpointResultResponse:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointResultSchema).where(
                    AuditCheckpointResultSchema.audit_id == audit_id,
                    AuditCheckpointResultSchema.checkpoint_id == checkpoint_id,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                row.compliant = data.compliant
                row.manual_override = data.manual_override
                if data.image_path is not None:
                    row.image_path = data.image_path
                if data.ai_status_type is not None:
                    row.ai_status_type = data.ai_status_type
                if data.ai_result is not None:
                    row.ai_result = data.ai_result
                await session.commit()
                await session.refresh(row)
                return self._schema_to_result(row)
            row = AuditCheckpointResultSchema(
                id=str(uuid4()),
                audit_id=audit_id,
                checkpoint_id=checkpoint_id,
                compliant=data.compliant,
                manual_override=data.manual_override,
                image_path=data.image_path,
                ai_status_type=data.ai_status_type,
                ai_result=data.ai_result,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_result(row)

    async def update_ai_status(
        self,
        audit_id: str,
        checkpoint_id: str,
        ai_status_type: str,
        ai_result: str | None = None,
    ) -> CheckpointResultResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointResultSchema).where(
                    AuditCheckpointResultSchema.audit_id == audit_id,
                    AuditCheckpointResultSchema.checkpoint_id == checkpoint_id,
                )
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            row.ai_status_type = ai_status_type
            if ai_result is not None:
                row.ai_result = ai_result
            await session.commit()
            await session.refresh(row)
            return self._schema_to_result(row)

    async def get_result(self, audit_id: str, checkpoint_id: str) -> CheckpointResultResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointResultSchema).where(
                    AuditCheckpointResultSchema.audit_id == audit_id,
                    AuditCheckpointResultSchema.checkpoint_id == checkpoint_id,
                )
            )
            row = result.scalar_one_or_none()
            return self._schema_to_result(row) if row else None
