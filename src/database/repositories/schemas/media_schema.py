"""Media evidence Pydantic models (extended with AI analysis fields)."""

from datetime import datetime

from pydantic import BaseModel


class MediaEvidenceResponse(BaseModel):
    id: str
    audit_id: str
    audit_checkpoint_id: str | None = None
    file_path: str
    created_at: datetime

    # Populated by list queries that JOIN through to the snapshot
    checkpoint_name: str | None = None

    # AI analysis fields (populated asynchronously after upload)
    ai_status: str = "PENDING"              # PENDING | COMPLETED | FAILED
    ai_compliant: bool | None = None
    ai_confidence: float | None = None
    ai_observations: str | None = None
    ai_summary: str | None = None
    ai_analyzed_at: datetime | None = None
    ai_compliance_score: float | None = None

    model_config = {"from_attributes": True}
