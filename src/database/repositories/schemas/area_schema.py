"""Area, sub_area, checkpoint Pydantic models (facility hierarchy)."""

from datetime import datetime

from pydantic import BaseModel, Field


class AreaCreate(BaseModel):
    facility_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=255)


class AreaUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)


class AreaResponse(BaseModel):
    id: str
    facility_id: str
    name: str
    created_at: datetime
    model_config = {"from_attributes": True}


class SubAreaCreate(BaseModel):
    area_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=255)


class SubAreaUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)


class SubAreaResponse(BaseModel):
    id: str
    area_id: str
    name: str
    created_at: datetime
    model_config = {"from_attributes": True}


class CheckpointCreate(BaseModel):
    sub_area_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class CheckpointUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class CheckpointResponse(BaseModel):
    id: str
    sub_area_id: str
    name: str
    description: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class AreaWithChildrenResponse(BaseModel):
    id: str
    facility_id: str
    name: str
    created_at: datetime
    sub_areas: list["SubAreaWithCheckpointsResponse"] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class SubAreaWithCheckpointsResponse(BaseModel):
    id: str
    area_id: str
    name: str
    created_at: datetime
    checkpoints: list[CheckpointResponse] = Field(default_factory=list)
    model_config = {"from_attributes": True}


AreaWithChildrenResponse.model_rebuild()
