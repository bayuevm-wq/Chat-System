"""
Rate limiting middleware using slowapi.

Provides per-user and per-IP rate limiting with configurable
limits from application settings.
"""

from __future__ import annotations

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import get_settings


def _key_func(request: Request) -> str:
    """Extract rate limit key — user ID from JWT, or fallback to IP.

    Args:
        request: The incoming FastAPI request.

    Returns:
        Rate limit key string.
    """
    # Try to extract user from authorization header
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            from src.infrastructure.security.jwt_handler import JWTHandler
            handler = JWTHandler()
            payload = handler.decode_token(auth[7:])
            return f"user:{payload.get('sub', 'unknown')}"
        except Exception:
            pass
    return f"ip:{get_remote_address(request)}"


settings = get_settings()
limiter = Limiter(
    key_func=_key_func,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> Response:
    """Custom handler for rate limit exceeded errors.

    Returns:
        429 JSON response with retry-after header.
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please slow down.",
                "detail": str(exc.detail),
            }
        },
        headers={"Retry-After": str(60)},
    )
