"""Date/time helpers for shifts and audits."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")


def utc_now() -> datetime:
    """Current UTC datetime."""
    return datetime.now(UTC)


def today_utc() -> date:
    """Today's date in UTC."""
    return utc_now().date()


def time_in_shift(shift_start: time, shift_end: time, t: datetime | None = None) -> bool:
    """Return True if given time (or now) falls within [shift_start, shift_end)."""
    if t is None:
        t = utc_now()
    # Compare as time (ignore date)
    now_time = t.time()
    if shift_start <= shift_end:
        return shift_start <= now_time < shift_end
    # Overnight shift
    return now_time >= shift_start or now_time < shift_end
