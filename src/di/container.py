from typing import Any

from src.infra_services.postgres_service import PostgresService


class Container:
    """Holds singleton services. Configure at startup, then initialize/close."""

    def __init__(self) -> None:
        self._postgres_service: PostgresService | None = None
        self._business_services: list[Any] = []

    def get_postgres_service(self) -> PostgresService:
        if self._postgres_service is None:
            self._postgres_service = PostgresService()
            self._postgres_service._initialize_service()
        return self._postgres_service

    def register_business_service(self, service: Any) -> None:
        self._business_services.append(service)

    def initialize_all_services(self) -> None:
        if self._postgres_service is None:
            self.get_postgres_service()
        for svc in self._business_services:
            if hasattr(svc, "_initialize_service"):
                svc._initialize_service()

    def close_all_services(self) -> None:
        for svc in reversed(self._business_services):
            if hasattr(svc, "_close_service"):
                svc._close_service()
        if self._postgres_service is not None and hasattr(self._postgres_service, "_close_service"):
            self._postgres_service._close_service()
            self._postgres_service = None


_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container


def configure_container() -> None:
    get_container()
