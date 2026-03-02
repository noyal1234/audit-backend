from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.media_schema import MediaEvidenceSchema
from src.database.repositories.base_repository import BasePostgresRepository
from src.database.repositories.schemas.media_schema import MediaEvidenceResponse


class MediaRepository(BasePostgresRepository[MediaEvidenceSchema]):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory, MediaEvidenceSchema)

    def _schema_to_media(self, row: MediaEvidenceSchema) -> MediaEvidenceResponse:
        return MediaEvidenceResponse.model_validate(row)

    async def get_by_id(self, id: str) -> MediaEvidenceResponse | None:
        row = await self._get_by_id_raw(id)
        return self._schema_to_media(row) if row else None

    async def create(self, audit_id: str, checkpoint_id: str, file_path: str) -> MediaEvidenceResponse:
        async with self._session_factory() as session:
            row = MediaEvidenceSchema(
                id=str(uuid4()),
                audit_id=audit_id,
                checkpoint_id=checkpoint_id,
                file_path=file_path,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_media(row)

    async def list_by_audit(self, audit_id: str) -> list[MediaEvidenceResponse]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(MediaEvidenceSchema).where(MediaEvidenceSchema.audit_id == audit_id)
            )
            rows = result.scalars().all()
        return [self._schema_to_media(r) for r in rows]

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(MediaEvidenceSchema).where(MediaEvidenceSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def update_ai_result(
        self,
        id: str,
        *,
        ai_status: str,
        ai_compliant: bool | None,
        ai_confidence: float | None,
        ai_observations: str | None,
        ai_summary: str | None,
        ai_analyzed_at,
    ) -> bool:
        """Persist AI analysis outcome onto the media_evidence row. Returns True if found and updated."""
        async with self._session_factory() as session:
            result = await session.execute(select(MediaEvidenceSchema).where(MediaEvidenceSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            row.ai_status = ai_status
            row.ai_compliant = ai_compliant
            row.ai_confidence = ai_confidence
            row.ai_observations = ai_observations
            row.ai_summary = ai_summary
            row.ai_analyzed_at = ai_analyzed_at
            await session.commit()
            return True

