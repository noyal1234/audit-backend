"""Audit and checkpoint result Pydantic models."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class AuditCreate(BaseModel):
    facility_id: str = Field(..., min_length=1)
    shift_type: str = Field(..., min_length=1)
    shift_date: date


class AuditUpdate(BaseModel):
    status_type: str | None = None


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


class CheckpointResultCreate(BaseModel):
    compliant: bool
    manual_override: bool = False
    image_path: str | None = None
    ai_status_type: str | None = None
    ai_result: str | None = None


class CheckpointResultUpdate(BaseModel):
    compliant: bool | None = None
    manual_override: bool | None = None
    image_path: str | None = None
    ai_status_type: str | None = None
    ai_result: str | None = None


class CheckpointResultResponse(BaseModel):
    id: str
    audit_id: str
    checkpoint_id: str
    compliant: bool
    manual_override: bool
    image_path: str | None
    ai_status_type: str | None
    ai_result: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
