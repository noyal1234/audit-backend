"""Audit, audit area/sub_area/checkpoint snapshot, and progress Pydantic models."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from src.database.repositories.schemas.review_schema import EffectiveReviewResponse


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


class AuditAreaResponse(BaseModel):
    id: str
    audit_id: str
    area_name: str
    created_at: datetime
    sub_areas: list["AuditSubAreaResponse"] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class AuditSubAreaResponse(BaseModel):
    id: str
    audit_area_id: str
    sub_area_name: str
    created_at: datetime
    checkpoints: list["AuditCheckpointResponse"] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class AuditCheckpointResponse(BaseModel):
    id: str
    audit_sub_area_id: str
    checkpoint_name: str
    description: str | None
    is_completed: bool
    created_at: datetime
    updated_at: datetime
    effective_review: EffectiveReviewResponse | None = None
    model_config = {"from_attributes": True}


class AuditDetailResponse(BaseModel):
    """Audit with snapshot tree: audit_areas -> sub_areas -> checkpoints (with optional effective_review)."""
    id: str
    facility_id: str
    shift_type: str
    shift_date: date
    status_type: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    finalized_at: datetime | None
    audit_areas: list[AuditAreaResponse] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class CheckpointCompleteRequest(BaseModel):
    remarks: str | None = None


class AuditProgressResponse(BaseModel):
    audit_id: str
    status_type: str
    total_checkpoints: int
    completed_checkpoints: int
    completion_percentage: float
    compliant_checkpoints: int = 0
    compliance_percentage: float = 0.0


AuditAreaResponse.model_rebuild()
AuditSubAreaResponse.model_rebuild()
AuditCheckpointResponse.model_rebuild()
