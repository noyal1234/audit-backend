"""AI placeholder response models."""

from pydantic import BaseModel


class AIResultResponse(BaseModel):
    status: str = "AI_PENDING"
    compliant: bool | None = None
    confidence: float | None = None
    message: str = "Placeholder AI result; human decision overrides."
