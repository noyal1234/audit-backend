"""User Pydantic models."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role_type: str = Field(..., min_length=1)
    facility_id: str | None = None
    country_id: str | None = None


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    facility_id: str | None = None
    country_id: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    role_type: str
    facility_id: str | None
    country_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
