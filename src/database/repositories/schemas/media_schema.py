"""Media evidence Pydantic models."""

from datetime import datetime

from pydantic import BaseModel


class MediaEvidenceResponse(BaseModel):
    id: str
    audit_id: str
    checkpoint_id: str
    file_path: str
    created_at: datetime

    model_config = {"from_attributes": True}
