"""Timezone list endpoint. Uses Python zoneinfo (no DB storage)."""

from fastapi import APIRouter
from zoneinfo import available_timezones

router = APIRouter(prefix="/timezones", tags=["Timezones"])


@router.get("")
async def list_timezones() -> list[dict]:
    """Return valid regional timezones (e.g. Asia/Kolkata, Europe/London). Sorted. No auth required."""
    tz_list = [tz for tz in available_timezones() if "/" in tz]
    return [{"id": tz, "label": tz} for tz in sorted(tz_list)]
