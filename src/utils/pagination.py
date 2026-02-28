"""Pagination params and response shape."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query params for list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort: str = Field(default="created_at", description="Sort field")
    order: str = Field(default="desc", description="Sort order: asc or desc")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""

    items: list[T]
    total: int
    page: int
    limit: int
    total_pages: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, limit: int) -> "PaginatedResponse[T]":
        total_pages = max(1, (total + limit - 1) // limit)
        return cls(items=items, total=total, page=page, limit=limit, total_pages=total_pages)
