"""Validation helpers."""

import re
from typing import Any

ALLOWED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})
ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp"}
)


def validate_image_filename(filename: str) -> bool:
    """Return True if filename has an allowed image extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return f".{ext}" in ALLOWED_IMAGE_EXTENSIONS


def validate_image_content_type(content_type: str | None) -> bool:
    """Return True if content type is an allowed image type."""
    if not content_type:
        return False
    return content_type.lower().strip() in ALLOWED_IMAGE_CONTENT_TYPES


def sanitize_sort_field(value: str, allowed: set[str]) -> str:
    """Return value if it is in allowed, else first allowed or 'created_at'."""
    if value in allowed:
        return value
    return "created_at" if "created_at" in allowed else next(iter(allowed), "created_at")


def sanitize_order(value: str) -> str:
    """Return 'asc' or 'desc'."""
    if (value or "").lower() == "asc":
        return "asc"
    return "desc"
