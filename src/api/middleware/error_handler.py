"""
Global error handling middleware.

Maps domain exceptions to HTTP status codes and returns
structured JSON error responses.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from src.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DomainError,
    DuplicateEntityError,
    EntityNotFoundError,
    RateLimitExceededError,
    RoomFullError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Domain exception → HTTP status code mapping
_STATUS_MAP: dict[type[Exception], int] = {
    ValidationError: 400,
    DuplicateEntityError: 409,
    AuthenticationError: 401,
    AuthorizationError: 403,
    EntityNotFoundError: 404,
    RoomFullError: 409,
    RateLimitExceededError: 429,
    DomainError: 400,  # Fallback for any domain error
}


async def domain_exception_handler(
    request: Request, exc: DomainError
) -> JSONResponse:
    """Handle domain exceptions with structured JSON responses.

    Args:
        request: The incoming request.
        exc: The domain exception.

    Returns:
        JSON response with appropriate status code and error details.
    """
    status_code = 400
    for exc_type, code in _STATUS_MAP.items():
        if isinstance(exc, exc_type):
            status_code = code
            break

    error_body: dict[str, Any] = {
        "error": {
            "code": type(exc).__name__,
            "message": str(exc),
        }
    }

    if isinstance(exc, ValidationError):
        error_body["error"]["field"] = exc.field

    logger.warning(
        "Domain error",
        extra={"error_type": type(exc).__name__, "message": str(exc), "status": status_code},
    )

    return JSONResponse(status_code=status_code, content=error_body)


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle unhandled exceptions with a generic 500 response.

    Logs the full traceback for debugging while returning
    a safe error message to the client.
    """
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            }
        },
    )
