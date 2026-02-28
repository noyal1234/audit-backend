"""AI placeholder: return advisory result, do not override human decision."""

from src.database.repositories.schemas.ai_schema import AIResultResponse


def get_ai_result_placeholder() -> AIResultResponse:
    """Return placeholder AI result. Human decision overrides."""
    return AIResultResponse(
        status="AI_PENDING",
        compliant=None,
        confidence=None,
        message="Placeholder AI result; human decision overrides.",
    )


def get_ai_service():
    """Placeholder getter for DI."""
    return None
