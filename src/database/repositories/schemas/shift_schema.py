"""Shift config Pydantic models."""

from datetime import datetime, time

from pydantic import BaseModel, Field


class ShiftConfigUpdate(BaseModel):
    name: str | None = Field(None, max_length=50)
    start_time: time | None = None
    end_time: time | None = None


class ShiftConfigResponse(BaseModel):
    id: str
    name: str
    start_time: time
    end_time: time
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CurrentShiftResponse(BaseModel):
    shift_type: str
    shift_date: str
    start_time: time
    end_time: time
    is_current: bool
