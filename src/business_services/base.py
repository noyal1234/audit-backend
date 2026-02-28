from abc import ABC

from src.logging import get_logger


class BaseBusinessService(ABC):
    """Base for business services. Override _initialize_service and _close_service."""

    def __init__(self) -> None:
        self.logger = get_logger()

    def _initialize_service(self) -> None:
        pass

    def _close_service(self) -> None:
        pass
