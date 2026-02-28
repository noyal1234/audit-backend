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
    """Readiness check (DB connectivity)."""
    try:
        from src.di.container import get_container
        get_container().get_postgres_service().get_session_factory()
        return {"status": "ready"}
    except Exception:
        return JSONResponse(content={"status": "not ready"}, status_code=503)
