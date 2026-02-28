"""API-level exception handling and response format. Never expose raw SQL or stack traces."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

from src.exceptions.domain_exceptions import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from src.logging import get_logger

logger = get_logger()


ERROR_CODES = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
}


def error_response(
    status_code: int,
    message: str,
    code: str | None = None,
) -> JSONResponse:
    """Return standardized error JSON: { \"error\": { \"code\": \"...\", \"message\": \"...\" } }."""
    error_code = code or ERROR_CODES.get(status_code, "ERROR")
    body = {"error": {"code": error_code, "message": message}}
    return JSONResponse(status_code=status_code, content=body)


async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Map domain exceptions to HTTP status and standardized response."""
    if isinstance(exc, NotFoundError):
        return error_response(status_code=status.HTTP_404_NOT_FOUND, message=str(exc), code="NOT_FOUND")
    if isinstance(exc, UnauthorizedError):
        return error_response(status_code=status.HTTP_401_UNAUTHORIZED, message=str(exc), code="UNAUTHORIZED")
    if isinstance(exc, ForbiddenError):
        return error_response(status_code=status.HTTP_403_FORBIDDEN, message=str(exc), code="FORBIDDEN")
    if isinstance(exc, ConflictError):
        return error_response(status_code=status.HTTP_409_CONFLICT, message=exc.message, code="CONFLICT")
    if isinstance(exc, ValidationError):
        return error_response(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, message=exc.message, code="VALIDATION_ERROR")
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred",
        code="INTERNAL_ERROR",
    )


def _interpret_integrity_error(exc: IntegrityError) -> tuple[int, str]:
    """Map IntegrityError to (status_code, safe_message). Never expose raw DB text."""
    try:
        msg = (getattr(exc, "orig", None) and getattr(exc.orig, "args", (None,)) and exc.orig.args[0] or str(exc))
    except Exception:
        msg = str(exc)
    msg = (msg or "").lower()
    if "unique constraint" in msg or "duplicate key" in msg or "already exists" in msg:
        if "email" in msg or "user" in msg or "ix_user_email" in msg:
            return status.HTTP_409_CONFLICT, "Email already in use"
        if "country" in msg or "code" in msg or "ix_country_code" in msg:
            return status.HTTP_409_CONFLICT, "Country code already in use"
        return status.HTTP_409_CONFLICT, "Resource already exists"
    if "foreign key" in msg or "violates foreign key" in msg or "referential" in msg:
        return status.HTTP_400_BAD_REQUEST, "Invalid reference (missing or invalid related entity)"
    return status.HTTP_409_CONFLICT, "Data conflict"


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Catch SQLAlchemy IntegrityError; return 409/400 with safe message. Never leak DB details."""
    status_code, message = _interpret_integrity_error(exc)
    code = "CONFLICT" if status_code == 409 else "BAD_REQUEST"
    logger.warning("[WARNING] IntegrityError mapped to %s: %s", code, message)
    return error_response(status_code=status_code, message=message, code=code)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Map FastAPI request validation errors to standardized 422 response."""
    errors = exc.errors() if callable(getattr(exc, "errors", None)) else getattr(exc, "errors", ())
    parts = []
    for e in errors:
        loc = e.get("loc", ())
        msg = e.get("msg", "validation error")
        if len(loc) >= 2 and loc[0] == "body":
            parts.append(f"{loc[1]}: {msg}")
        else:
            parts.append(msg)
    message = "; ".join(parts) if parts else "Request validation failed"
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message=message,
        code="VALIDATION_ERROR",
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log stack trace internally; return generic 500. Never expose tracebacks or raw errors."""
    logger.exception("[ERROR] Unhandled exception: %s", exc)
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred",
        code="INTERNAL_ERROR",
    )
