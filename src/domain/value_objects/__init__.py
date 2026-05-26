"""Value objects — immutable domain primitives."""

from __future__ import annotations

from src.domain.value_objects.encryption import KeyPair
from src.domain.value_objects.message_id import MessageId
from src.domain.value_objects.user_status import UserPresence

__all__ = ["KeyPair", "MessageId", "UserPresence"]
