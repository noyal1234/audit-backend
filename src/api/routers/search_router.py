"""Global search: dealership, employee, audit. Pagination and role-based restriction."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import RequireEmployee
from src.business_services.dealer_service import get_dealer_service
from src.business_services.staff_service import get_staff_service
from src.business_services.audit_service import get_audit_service
from src.utils.pagination import PaginationParams

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def unified_search(
    payload: Annotated[dict, RequireEmployee],
    dealer_service: Annotated[any, Depends(get_dealer_service)],
    staff_service: Annotated[any, Depends(get_staff_service)],
    audit_service: Annotated[any, Depends(get_audit_service)],
    query: str,
    type: str = "dealership",
    page: int = 1,
    limit: int = 20,
):
    """Unified search. type: dealership, employee, audit. Partial match (ILIKE), pagination."""
    params = PaginationParams(page=page, limit=limit)
    if type == "dealership":
        result = await dealer_service.list_facilities(payload, search=query, params=params)
        return result
    if type == "employee":
        result = await staff_service.list_staff(payload, search=query, params=params)
        return result
    if type == "audit":
        result = await audit_service.list_audits(payload, params=params)
        return result
    return {"items": [], "total": 0, "page": page, "limit": limit, "total_pages": 0}
