"""
Health check REST API router.

Provides liveness, readiness, and full dependency health endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.infrastructure.observability.health import check_all

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("/live")
async def liveness():
    """Liveness probe — always returns 200 if the process is running."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness(request: Request):
    """Readiness probe — checks database and Redis connectivity."""
    from src.infrastructure.database.connection import async_session_factory

    redis_client = getattr(request.app.state, "redis_client", None)
    result = await check_all(async_session_factory, redis_client)
    status_code = 200 if result["status"] == "healthy" else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(content=result, status_code=status_code)


@router.get("/")
async def full_health(request: Request):
    """Full health check with all dependency statuses."""
    from src.infrastructure.database.connection import async_session_factory

    redis_client = getattr(request.app.state, "redis_client", None)
    conn_manager = getattr(request.app.state, "connection_manager", None)

    result = await check_all(async_session_factory, redis_client)
    result["websocket_connections"] = conn_manager.connection_count if conn_manager else 0
    return result
