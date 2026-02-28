"""Category, subcategory, checkpoint (checklist template) Pydantic models."""

from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubcategoryCreate(BaseModel):
    category_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class SubcategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category_id: str | None = None


class SubcategoryResponse(BaseModel):
    id: str
    category_id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CheckpointCreate(BaseModel):
    subcategory_id: str = Field(..., min_length=1)
    facility_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    requires_photo: bool = False
    active: bool = True


class CheckpointUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    requires_photo: bool | None = None
    active: bool | None = None


class CheckpointResponse(BaseModel):
    id: str
    subcategory_id: str
    facility_id: str
    name: str
    description: str | None
    requires_photo: bool
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
