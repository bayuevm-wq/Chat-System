"""
Base domain event.

All domain events inherit from :class:`DomainEvent`, which provides
automatic event IDs, ISO timestamps, JSON serialization, and
deserialization.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.shared.utils import generate_id, utc_now


@dataclass
class DomainEvent:
    """Immutable record of something that happened in the domain.

    Attributes:
        event_id: Globally unique event identifier (UUID v4 string).
        event_type: Dot-separated event type name (e.g. ``"message.sent"``).
        timestamp: ISO 8601 UTC timestamp of when the event was created.
        payload: Arbitrary JSON-safe data associated with the event.
        source_node: Identifier of the cluster node that originated the event.
    """

    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(generate_id()))
    timestamp: str = field(default_factory=lambda: utc_now().isoformat())
    source_node: str | None = None

    # ── serialization ────────────────────────────────────────────

    def to_json(self) -> str:
        """Serialize the event to a JSON string.

        Returns:
            A compact JSON representation of the event.
        """
        return json.dumps(
            {
                "event_id": self.event_id,
                "event_type": self.event_type,
                "timestamp": self.timestamp,
                "payload": self.payload,
                "source_node": self.source_node,
            },
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, data: str) -> DomainEvent:
        """Deserialize a JSON string into a :class:`DomainEvent`.

        Args:
            data: A JSON string previously produced by :meth:`to_json`.

        Returns:
            A reconstituted ``DomainEvent`` instance.
        """
        obj = json.loads(data)
        return cls(
            event_id=obj["event_id"],
            event_type=obj["event_type"],
            timestamp=obj["timestamp"],
            payload=obj.get("payload", {}),
            source_node=obj.get("source_node"),
        )
