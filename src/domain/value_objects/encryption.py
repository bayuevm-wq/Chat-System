"""KeyPair value object — RSA key pair for simplified E2E encryption."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class KeyPair:
    """Immutable RSA key pair holder.

    Stores PEM-encoded public and private keys for the
    simplified end-to-end encryption simulation.
    """

    public_key: str
    private_key: str
    created_at: datetime

    def __str__(self) -> str:
        return f"KeyPair(created_at={self.created_at.isoformat()})"

    def __repr__(self) -> str:
        # Never expose private key in repr
        return f"KeyPair(public_key='{self.public_key[:40]}...', created_at={self.created_at!r})"
