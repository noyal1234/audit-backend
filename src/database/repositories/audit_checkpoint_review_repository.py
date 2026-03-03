"""Append-only audit checkpoint reviews. Effective = latest per checkpoint (DISTINCT ON)."""

from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.database.postgres.schema.audit_checkpoint_review_schema import AuditCheckpointReviewSchema
from src.database.repositories.schemas.review_schema import AuditCheckpointReviewResponse


class AuditCheckpointReviewRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def insert(
        self,
        audit_checkpoint_id: str,
        review_type: str,
        compliant: bool,
        score: float,
        confidence: float | None = None,
        remarks: str | None = None,
        model_version: str | None = None,
        created_by: str | None = None,
    ) -> AuditCheckpointReviewResponse:
        async with self._session_factory() as session:
            row = AuditCheckpointReviewSchema(
                id=str(uuid4()),
                audit_checkpoint_id=audit_checkpoint_id,
                review_type=review_type,
                compliant=compliant,
                score=score,
                confidence=confidence,
                remarks=remarks,
                model_version=model_version,
                created_by=created_by,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return AuditCheckpointReviewResponse.model_validate(row)

    async def get_effective_reviews_for_audit(self, audit_id: str) -> list[AuditCheckpointReviewResponse]:
        """Latest review per audit_checkpoint (effective). DISTINCT ON (audit_checkpoint_id) ORDER BY created_at DESC."""
        async with self._session_factory() as session:
            stmt = text("""
                SELECT DISTINCT ON (r.audit_checkpoint_id)
                    r.id, r.audit_checkpoint_id, r.review_type, r.compliant, r.score, r.confidence,
                    r.remarks, r.model_version, r.created_by, r.created_at
                FROM audit_checkpoint_review r
                JOIN audit_checkpoint cp ON cp.id = r.audit_checkpoint_id
                JOIN audit_sub_area sa ON sa.id = cp.audit_sub_area_id
                JOIN audit_area aa ON aa.id = sa.audit_area_id
                WHERE aa.audit_id = :audit_id
                ORDER BY r.audit_checkpoint_id, r.created_at DESC
            """)
            result = await session.execute(stmt, {"audit_id": audit_id})
            rows = result.mappings().all()
        return [
            AuditCheckpointReviewResponse(
                id=r["id"],
                audit_checkpoint_id=r["audit_checkpoint_id"],
                review_type=r["review_type"],
                compliant=r["compliant"],
                score=r["score"],
                confidence=r["confidence"],
                remarks=r["remarks"],
                model_version=r["model_version"],
                created_by=r["created_by"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def get_latest_for_checkpoint(self, audit_checkpoint_id: str) -> AuditCheckpointReviewResponse | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditCheckpointReviewSchema)
                .where(AuditCheckpointReviewSchema.audit_checkpoint_id == audit_checkpoint_id)
                .order_by(AuditCheckpointReviewSchema.created_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
        return AuditCheckpointReviewResponse.model_validate(row) if row else None
