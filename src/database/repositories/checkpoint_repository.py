from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.checkpoint_schema import CheckpointSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.template_schema import (
    CheckpointCreate,
    CheckpointResponse,
    CheckpointUpdate,
)


class CheckpointRepository(BasePostgresRepository[CheckpointSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, CheckpointSchema)

    def _schema_to_checkpoint(self, row: CheckpointSchema) -> CheckpointResponse:
        return CheckpointResponse.model_validate(row)

    async def get_by_id(self, id: str) -> CheckpointResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_checkpoint(row) if row else None

    async def list_checkpoints(
        self,
        *,
        facility_id: str | None = None,
        subcategory_id: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[CheckpointResponse], int]:
        async with self._session_factory() as session:
            q = select(CheckpointSchema)
            count_q = select(func.count()).select_from(CheckpointSchema)
            if facility_id:
                q = q.where(CheckpointSchema.facility_id == facility_id)
                count_q = count_q.where(CheckpointSchema.facility_id == facility_id)
            if subcategory_id:
                q = q.where(CheckpointSchema.subcategory_id == subcategory_id)
                count_q = count_q.where(CheckpointSchema.subcategory_id == subcategory_id)
            total = (await session.execute(count_q)).scalar() or 0
            order_col = getattr(CheckpointSchema, sort, CheckpointSchema.created_at)
            q = q.order_by(order_col.desc() if order == "desc" else order_col.asc())
            q = q.offset(offset).limit(limit)
            result = await session.execute(q)
            rows = result.scalars().all()
        return [self._schema_to_checkpoint(r) for r in rows], total

    async def create(self, data: CheckpointCreate) -> CheckpointResponse:
        async with self._session_factory() as session:
            row = CheckpointSchema(
                id=str(uuid4()),
                subcategory_id=data.subcategory_id,
                facility_id=data.facility_id,
                name=data.name,
                description=data.description,
                requires_photo=data.requires_photo,
                active=data.active,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_checkpoint(row)

    async def update(self, id: str, data: CheckpointUpdate) -> CheckpointResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(select(CheckpointSchema).where(CheckpointSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            if data.name is not None:
                row.name = data.name
            if data.description is not None:
                row.description = data.description
            if data.requires_photo is not None:
                row.requires_photo = data.requires_photo
            if data.active is not None:
                row.active = data.active
            await session.commit()
            await session.refresh(row)
            return self._schema_to_checkpoint(row)

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(CheckpointSchema).where(CheckpointSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True
