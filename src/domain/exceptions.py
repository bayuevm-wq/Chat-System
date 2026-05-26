"""
Domain exception hierarchy.

Provides a structured set of domain-specific exceptions that allow
upper layers (application, infrastructure) to handle business-rule
violations without coupling to implementation details.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base exception for all domain-layer errors.

    Every domain exception inherits from this class so that callers
    can catch broad categories of business-rule violations with a
    single ``except DomainError`` clause.
    """

    def __init__(self, message: str = "A domain error occurred") -> None:
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class EntityNotFoundError(DomainError):
    """Raised when a requested entity does not exist.

    Attributes:
        entity_type: The type/name of the entity (e.g. ``"User"``).
        entity_id: The identifier that was looked up.
    """

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            f"{entity_type} with id '{entity_id}' not found"
        )

    def __str__(self) -> str:
        return f"{self.entity_type} with id '{self.entity_id}' not found"


class AuthenticationError(DomainError):
    """Raised when authentication credentials are invalid or missing."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class AuthorizationError(DomainError):
    """Raised when the authenticated user lacks permission for the operation."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message)


class ValidationError(DomainError):
    """Raised when a domain-level validation rule is violated.

    Attributes:
        field: The name of the field that failed validation.
        message: A human-readable explanation of the violation.
    """

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"Validation error on '{field}': {message}")

    def __str__(self) -> str:
        return f"Validation error on '{self.field}': {self.message}"


class DuplicateEntityError(DomainError):
    """Raised when an entity with a conflicting unique field already exists.

    Attributes:
        entity_type: The type/name of the entity (e.g. ``"User"``).
        field: The unique field that caused the conflict (e.g. ``"email"``).
    """

    def __init__(self, entity_type: str, field: str) -> None:
        self.entity_type = entity_type
        self.field = field
        super().__init__(
            f"{entity_type} with duplicate '{field}' already exists"
        )

    def __str__(self) -> str:
        return (
            f"{self.entity_type} with duplicate '{self.field}' already exists"
        )


class RoomFullError(DomainError):
    """Raised when a room has reached its maximum member capacity."""

    def __init__(self, message: str = "Room has reached maximum capacity") -> None:
        super().__init__(message)


class RateLimitExceededError(DomainError):
    """Raised when a client exceeds the allowed request rate."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message)


class MessageDeliveryError(DomainError):
    """Raised when a message cannot be delivered to its intended recipients."""

    def __init__(self, message: str = "Message delivery failed") -> None:
        super().__init__(message)
