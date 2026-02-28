"""Shift config and current shift. Validates shift before audit creation."""

from datetime import time

from src.database.repositories.schemas.shift_schema import CurrentShiftResponse, ShiftConfigResponse, ShiftConfigUpdate
from src.database.repositories.shift_repository import ShiftRepository
from src.business_services.base import BaseBusinessService
from src.utils.datetime_utils import today_utc, time_in_shift, utc_now


class ShiftService(BaseBusinessService):
    def __init__(self) -> None:
        super().__init__()
        self._shift_repo: ShiftRepository | None = None

    def _initialize_service(self) -> None:
        from src.di.container import get_container
        factory = get_container().get_postgres_service().get_session_factory()
        self._shift_repo = ShiftRepository(factory)
        self.logger.info("[OK] ShiftService initialized")

    def _close_service(self) -> None:
        self._shift_repo = None

    async def get_current_shift(self) -> CurrentShiftResponse | None:
        if self._shift_repo is None:
            raise RuntimeError("ShiftService not initialized")
        configs = await self._shift_repo.list_all()
        if not configs:
            return None
        now = utc_now()
        today = today_utc().isoformat()
        for cfg in configs:
            if time_in_shift(cfg.start_time, cfg.end_time, now):
                return CurrentShiftResponse(
                    shift_type=cfg.name,
                    shift_date=today,
                    start_time=cfg.start_time,
                    end_time=cfg.end_time,
                    is_current=True,
                )
        if configs:
            cfg = configs[0]
            return CurrentShiftResponse(
                shift_type=cfg.name,
                shift_date=today,
                start_time=cfg.start_time,
                end_time=cfg.end_time,
                is_current=False,
            )
        return None

    async def get_config(self) -> list[ShiftConfigResponse]:
        if self._shift_repo is None:
            raise RuntimeError("ShiftService not initialized")
        return await self._shift_repo.list_all()

    async def update_config(self, id: str, data: ShiftConfigUpdate) -> ShiftConfigResponse | None:
        if self._shift_repo is None:
            raise RuntimeError("ShiftService not initialized")
        return await self._shift_repo.update(id, data)


_shift_service: ShiftService | None = None


def get_shift_service() -> ShiftService:
    global _shift_service
    if _shift_service is None:
        _shift_service = ShiftService()
    return _shift_service
