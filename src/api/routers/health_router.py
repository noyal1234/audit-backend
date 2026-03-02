"""Health and readiness."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Liveness check."""
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    """Readiness check: DB connectivity + valid shift configuration."""
    try:
        from src.di.container import get_container
        get_container().get_postgres_service().get_session_factory()
    except Exception:
        return JSONResponse(content={"status": "not_ready", "reason": "Database not available"}, status_code=503)
    try:
        from src.business_services.shift_service import get_shift_service
        await get_shift_service().validate_shift_configuration()
    except Exception as e:
        return JSONResponse(
            content={"status": "not_ready", "reason": str(e)},
            status_code=503,
        )
    return {"status": "ready"}
