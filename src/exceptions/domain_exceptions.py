"""Domain-level exceptions for business rule violations."""


class DomainError(Exception):
    """Base domain error."""

    pass


class NotFoundError(DomainError):
    """Entity not found."""

    def __init__(self, entity: str, identifier: str) -> None:
        self.entity = entity
        self.identifier = identifier
        super().__init__(f"{entity} not found: {identifier}")


class UnauthorizedError(DomainError):
    """Authentication required."""

    pass


class ForbiddenError(DomainError):
    """Permission denied."""

    pass


class ConflictError(DomainError):
    """Business logic conflict (e.g. duplicate audit per shift)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ValidationError(DomainError):
    """Validation failed."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
