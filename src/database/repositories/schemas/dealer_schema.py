"""Facility (dealership) Pydantic models."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CountryMini(BaseModel):
    id: str
    name: str


class ZoneMini(BaseModel):
    id: str
    name: str
    country: CountryMini | None = None

# Basic phone pattern: optional +, digits, spaces, hyphens, parentheses
PHONE_PATTERN = r"^\+?[\d\s\-\(\)]{8,50}$"


class FacilityCreate(BaseModel):
    zone_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=255)
    code: str | None = None
    address: str | None = None
    dealer_name: str = Field(..., min_length=2, max_length=255)
    dealer_phone: str = Field(..., min_length=8, max_length=50, pattern=PHONE_PATTERN)
    dealer_email: EmailStr
    dealer_designation: str | None = Field(None, max_length=100)
    email: EmailStr = Field(..., description="Dealership login email")
    password: str = Field(..., min_length=8, description="Dealership login password")


class FacilityUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = None
    address: str | None = None
    zone_id: str | None = None
    user_id: str | None = None
    dealer_name: str | None = Field(None, min_length=2, max_length=255)
    dealer_phone: str | None = Field(None, min_length=8, max_length=50, pattern=PHONE_PATTERN)
    dealer_email: EmailStr | None = None
    dealer_designation: str | None = Field(None, max_length=100)


class FacilityResponse(BaseModel):
    id: str
    zone_id: str
    zone: ZoneMini | None = None
    user_id: str | None
    name: str
    code: str | None
    address: str | None
    dealer_name: str | None
    dealer_phone: str | None
    dealer_email: str | None
    dealer_designation: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DealerContactResponse(BaseModel):
    """Dealer contact details for GET /dealerships/{id}/contact."""

    dealer_name: str | None
    dealer_phone: str | None
    dealer_email: str | None
    dealer_designation: str | None


class DealerContactUpdate(BaseModel):
    """Partial update for PATCH /dealerships/{id}/contact."""

    dealer_name: str | None = Field(None, min_length=2, max_length=255)
    dealer_phone: str | None = Field(None, min_length=8, max_length=50, pattern=PHONE_PATTERN)
    dealer_email: EmailStr | None = None
    dealer_designation: str | None = Field(None, min_length=1, max_length=100)
