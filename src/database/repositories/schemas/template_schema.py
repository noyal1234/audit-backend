"""Category, checkpoint, and checkpoint-category Pydantic models (facility-scoped)."""

from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    facility_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class CategoryResponse(BaseModel):
    id: str
    facility_id: str
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckpointCreate(BaseModel):
    facility_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=255)
    image_url: str = Field(..., min_length=1, max_length=512)


class CheckpointUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    image_url: str | None = Field(None, min_length=1, max_length=512)


class CheckpointResponse(BaseModel):
    id: str
    facility_id: str
    name: str
    image_url: str
    created_at: datetime
    updated_at: datetime
    categories: list[CategoryResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CheckpointCategoryCreate(BaseModel):
    category_id: str = Field(..., min_length=1)


class CheckpointCategoryResponse(BaseModel):
    id: str
    checkpoint_id: str
    category_id: str

    model_config = {"from_attributes": True}
