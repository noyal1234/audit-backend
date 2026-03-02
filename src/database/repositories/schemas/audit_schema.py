"""Audit, audit checkpoint snapshot, and audit checkpoint category Pydantic models."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class AuditCreate(BaseModel):
    facility_id: str = Field(..., min_length=1)
    shift_type: str = Field(..., min_length=1)
    shift_date: date


class AuditResponse(BaseModel):
    id: str
    facility_id: str
    shift_type: str
    shift_date: date
    status_type: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    finalized_at: datetime | None

    model_config = {"from_attributes": True}


class AuditCheckpointCategoryResponse(BaseModel):
    id: str
    audit_checkpoint_id: str
    category_id: str
    category_name: str
    is_completed: bool
    completed_by: str | None
    completed_at: datetime | None
    remarks: str | None
    ai_status: str | None = None
    ai_compliant: bool | None = None
    ai_summary: str | None = None
    ai_latest_media_id: str | None = None

    model_config = {"from_attributes": True}


class AuditCheckpointResponse(BaseModel):
    id: str
    audit_id: str
    checkpoint_id: str
    checkpoint_name: str
    image_url: str
    status_type: str
    created_at: datetime
    categories: list[AuditCheckpointCategoryResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AuditDetailResponse(BaseModel):
    """Audit with its snapshotted checkpoints and categories."""
    id: str
    facility_id: str
    shift_type: str
    shift_date: date
    status_type: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    finalized_at: datetime | None
    audit_checkpoints: list[AuditCheckpointResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CategoryCompleteRequest(BaseModel):
    remarks: str | None = None


class CategoryRemarksUpdate(BaseModel):
    """Update only the remarks (review text) for a category result. Does not change completion state."""
    remarks: str | None = None


class AuditProgressResponse(BaseModel):
    audit_id: str
    status_type: str
    total_checkpoints: int
    completed_checkpoints: int
    total_categories: int
    completed_categories: int
    completion_percentage: float
