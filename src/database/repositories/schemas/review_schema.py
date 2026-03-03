"""Audit checkpoint review Pydantic models."""

from datetime import datetime

from pydantic import BaseModel, Field


class AuditCheckpointReviewResponse(BaseModel):
    id: str
    audit_checkpoint_id: str
    review_type: str
    compliant: bool
    score: float
    confidence: float | None
    remarks: str | None
    model_version: str | None
    created_by: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ManualReviewRequest(BaseModel):
    compliant: bool = Field(...)
    score: float = Field(..., ge=0.0, le=100.0)
    remarks: str | None = None
