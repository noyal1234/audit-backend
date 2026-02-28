"""Country Pydantic models (future-ready)."""

from datetime import datetime

from pydantic import BaseModel, Field


class CountryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=10)


class CountryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=10)


class CountryResponse(BaseModel):
    id: str
    name: str
    code: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
