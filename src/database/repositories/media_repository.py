from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload

from src.database.postgres.schema.audit_checkpoint_schema import AuditCheckpointSchema
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

    async def create(
        self,
        audit_id: str,
        audit_checkpoint_id: str,
        file_path: str,
    ) -> MediaEvidenceResponse:
        async with self._session_factory() as session:
            row = MediaEvidenceSchema(
                id=str(uuid4()),
                audit_id=audit_id,
                audit_checkpoint_id=audit_checkpoint_id,
                file_path=file_path,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return self._schema_to_media(row)

    async def list_by_audit(self, audit_id: str) -> list[MediaEvidenceResponse]:
        """Return all media for an audit, with checkpoint_name from snapshot."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(MediaEvidenceSchema)
                .options(selectinload(MediaEvidenceSchema.audit_checkpoint))
                .where(MediaEvidenceSchema.audit_id == audit_id)
            )
            rows = result.scalars().all()

        items = []
        for r in rows:
            cp = r.audit_checkpoint
            items.append(MediaEvidenceResponse(
                id=r.id,
                audit_id=r.audit_id,
                audit_checkpoint_id=r.audit_checkpoint_id,
                checkpoint_name=cp.checkpoint_name if cp else None,
                file_path=r.file_path,
                created_at=r.created_at,
                ai_status=r.ai_status,
                ai_compliant=r.ai_compliant,
                ai_confidence=r.ai_confidence,
                ai_observations=r.ai_observations,
                ai_summary=r.ai_summary,
                ai_analyzed_at=r.ai_analyzed_at,
                ai_compliance_score=r.ai_compliance_score,
            ))
        return items

    async def delete(self, id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(select(MediaEvidenceSchema).where(MediaEvidenceSchema.id == id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def delete_by_audit(self, audit_id: str) -> list[str]:
        """Delete all media_evidence rows for the audit. Returns list of file_paths that were stored."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(MediaEvidenceSchema).where(MediaEvidenceSchema.audit_id == audit_id)
            )
            rows = result.scalars().all()
            paths = [r.file_path for r in rows]
            for row in rows:
                await session.delete(row)
            await session.commit()
            return paths

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
        ai_compliance_score: float | None = None,
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
            if ai_compliance_score is not None:
                row.ai_compliance_score = ai_compliance_score
            await session.commit()
            return True