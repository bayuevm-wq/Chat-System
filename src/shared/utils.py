"""
Shared utility functions used across the application.

Provides common helpers for ID generation, time handling,
pagination, and data serialization.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any


def generate_id() -> uuid.UUID:
    """Generate a new UUID v4 identifier.

    Returns:
        A new UUID4 instance.
    """
    return uuid.uuid4()


def utc_now() -> datetime:
    """Get current UTC timestamp with timezone awareness.

    Returns:
        Timezone-aware datetime in UTC.
    """
    return datetime.now(UTC)


def to_iso_string(dt: datetime | None) -> str | None:
    """Convert datetime to ISO 8601 string.

    Args:
        dt: Datetime to convert, or None.

    Returns:
        ISO format string, or None if input is None.
    """
    if dt is None:
        return None
    return dt.isoformat()


def from_iso_string(s: str) -> datetime:
    """Parse an ISO 8601 string to datetime.

    Args:
        s: ISO format datetime string.

    Returns:
        Parsed timezone-aware datetime.
    """
    return datetime.fromisoformat(s)


def clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamp a value between min and max bounds.

    Args:
        value: The value to clamp.
        minimum: Lower bound.
        maximum: Upper bound.

    Returns:
        Clamped value.
    """
    return max(minimum, min(value, maximum))


def sanitize_input(text: str, max_length: int = 10_000) -> str:
    """Sanitize user input by stripping and truncating.

    Args:
        text: Raw user input.
        max_length: Maximum allowed length.

    Returns:
        Sanitized text string.
    """
    return text.strip()[:max_length]


def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """Mask a sensitive string, showing only the last N characters.

    Args:
        value: String to mask.
        visible_chars: Number of trailing characters to show.

    Returns:
        Masked string like "****abcd".
    """
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def build_pagination_meta(
    total: int,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Build pagination metadata for paginated responses.

    Args:
        total: Total number of items.
        page: Current page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        Dictionary with pagination metadata.
    """
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
