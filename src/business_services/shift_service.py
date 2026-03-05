"""Shift config: 2-shift 24h coverage (DAY + NIGHT), validation, current shift detection."""

from datetime import time
from zoneinfo import ZoneInfo

from src.database.repositories.schemas.shift_schema import (
    CurrentShiftResponse,
    ShiftConfigCreate,
    ShiftConfigResponse,
    ShiftConfigUpdate,
)
from src.database.repositories.shift_repository import ShiftRepository
from src.database.repositories.facility_repository import FacilityRepository
from src.business_services.base import BaseBusinessService
from src.exceptions.domain_exceptions import ConflictError, NotFoundError, ValidationError
from src.utils.datetime_utils import time_in_shift, utc_now

DEFAULT_SHIFTS = [
    ShiftConfigCreate(name="DAY", start_time=time(6, 0), end_time=time(18, 0)),
    ShiftConfigCreate(name="NIGHT", start_time=time(18, 0), end_time=time(6, 0)),
]


def _shift_minutes(start: time, end: time) -> int:
    """Total minutes covered by a shift. Handles overnight (end < start)."""
    s = start.hour * 60 + start.minute
    e = end.hour * 60 + end.minute
    if e > s:
        return e - s
    return (24 * 60 - s) + e


def _is_overnight(start: time, end: time) -> bool:
    return end <= start


def _overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    """Check if two shift ranges overlap. Handles overnight shifts."""
    def _to_ranges(s: time, e: time) -> list[tuple[int, int]]:
        sm = s.hour * 60 + s.minute
        em = e.hour * 60 + e.minute
        if em > sm:
            return [(sm, em)]
        return [(sm, 24 * 60), (0, em)]

    for a in _to_ranges(a_start, a_end):
        for b in _to_ranges(b_start, b_end):
            if a[0] < b[1] and b[0] < a[1]:
                return True
    return False


class ShiftService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._shift_repo: ShiftRepository | None = None
        self._facility_repo: FacilityRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._shift_repo = ShiftRepository(factory)
        self._facility_repo = FacilityRepository(factory)
        self.logger.info("[OK] ShiftService initialized")

    def _close_service(self) -> None:
        self._shift_repo = None
        self._facility_repo = None

    def _require_initialized(self) -> None:
        if self._shift_repo is None:
            raise RuntimeError("ShiftService not initialized")

    # ---- Seeding ----

    async def ensure_default_shifts(self) -> None:
        """Seed default shift configs if the table is empty. Idempotent."""
        self._require_initialized()
        existing = await self._shift_repo.list_all()
        if existing:
            self.logger.info("[INFO] Shift configs already exist, skipping seed")
            return
        for shift in DEFAULT_SHIFTS:
            await self._shift_repo.create(shift)
        self.logger.info("[OK] Default shifts seeded (DAY + NIGHT)")

    # ---- Validation ----

    def _validate_shift_set(self, configs: list[ShiftConfigResponse]) -> None:
        """Validate that the shift set provides full 24h coverage with no overlaps."""
        if len(configs) != 2:
            raise ValidationError("Exactly 2 shifts required for full 24-hour coverage")

        overnight_count = sum(1 for c in configs if _is_overnight(c.start_time, c.end_time))
        if overnight_count > 1:
            raise ValidationError("At most one overnight shift allowed")

        a, b = configs[0], configs[1]
        if _overlaps(a.start_time, a.end_time, b.start_time, b.end_time):
            raise ConflictError("Shift times overlap")

        total = _shift_minutes(a.start_time, a.end_time) + _shift_minutes(b.start_time, b.end_time)
        if total != 24 * 60:
            raise ValidationError(f"Shifts must cover exactly 24 hours, current coverage is {total} minutes")

    async def validate_shift_configuration(self) -> None:
        """Load and validate all shifts. Raises on invalid configuration."""
        self._require_initialized()
        configs = await self._shift_repo.list_all()
        if not configs:
            raise ValidationError("Shift configuration missing")
        self._validate_shift_set(configs)

    # ---- Current Shift ----

    async def get_current_shift(self, facility_id: str) -> CurrentShiftResponse:
        """Current active shift in facility's timezone. facility_id is required."""
        self._require_initialized()
        if self._facility_repo is None:
            raise RuntimeError("ShiftService not initialized")
        facility, is_active = await self._facility_repo.get_by_id_with_active(facility_id)
        if not facility:
            raise NotFoundError("Facility", facility_id)
        if not is_active:
            raise ConflictError("Facility is inactive")
        configs = await self._shift_repo.list_all()
        if not configs:
            raise ConflictError("Shift configuration missing. Contact system administrator.")

        now_utc = utc_now()
        facility_tz = ZoneInfo(facility.timezone)
        local_now = now_utc.astimezone(facility_tz)
        shift_date = local_now.date().isoformat()
        for cfg in configs:
            if time_in_shift(cfg.start_time, cfg.end_time, local_now):
                return CurrentShiftResponse(
                    shift_type=cfg.name,
                    shift_date=shift_date,
                    start_time=cfg.start_time,
                    end_time=cfg.end_time,
                    is_current=True,
                )
        raise ConflictError("Shift configuration invalid. No active shift detected.")

    # ---- CRUD ----

    async def get_config(self) -> list[ShiftConfigResponse]:
        self._require_initialized()
        return await self._shift_repo.list_all()

    async def update_config(self, id: str, data: ShiftConfigUpdate) -> ShiftConfigResponse:
        self._require_initialized()
        existing = await self._shift_repo.get_by_id(id)
        if not existing:
            raise NotFoundError("ShiftConfig", id)
        result = await self._shift_repo.update(id, data)
        if not result:
            raise NotFoundError("ShiftConfig", id)
        all_configs = await self._shift_repo.list_all()
        self._validate_shift_set(all_configs)
        return result

    async def delete_config(self, id: str) -> None:
        self._require_initialized()
        existing = await self._shift_repo.get_by_id(id)
        if not existing:
            raise NotFoundError("ShiftConfig", id)
        all_configs = await self._shift_repo.list_all()
        remaining = [c for c in all_configs if c.id != id]
        if len(remaining) < 2:
            raise ConflictError("Cannot delete shift: minimum 2 shifts required for 24-hour coverage")
        await self._shift_repo.delete(id)


_shift_service: ShiftService | None = None


def get_shift_service() -> ShiftService:
    global _shift_service
    if _shift_service is None:
        _shift_service = ShiftService()
    return _shift_service
