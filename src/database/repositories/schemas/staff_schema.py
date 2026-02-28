"""Staff (employee) Pydantic models. Login via user table (email/password)."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class StaffCreate(BaseModel):
    facility_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)


class StaffUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    user_id: str | None = None


class StaffResponse(BaseModel):
    id: str
    facility_id: str
    user_id: str | None
    name: str
    email: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
