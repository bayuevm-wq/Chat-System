"""MessageId value object — typed wrapper for message identifiers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MessageId:
    """Immutable message identifier.

    Wraps a raw integer ID with validation to ensure positive values.
    """

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValueError(f"MessageId must be positive, got {self.value}")

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return self.value
