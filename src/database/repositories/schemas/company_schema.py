"""Zone (company) Pydantic models."""

from datetime import datetime

from pydantic import BaseModel, Field


class ZoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    country_id: str | None = None


class ZoneUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    country_id: str | None = None


class ZoneResponse(BaseModel):
    id: str
    name: str
    country_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
