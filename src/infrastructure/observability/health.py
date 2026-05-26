"""
Health check functions.

Provides liveness, readiness, and dependency health checks for the
application, database, and Redis services.
"""

from __future__ import annotations

import time
from typing import Any

# Module-level start time for uptime calculation
_start_time = time.monotonic()


async def check_database(session_factory: Any) -> dict[str, Any]:
    """Check database connectivity.

    Args:
        session_factory: Async session factory (async_sessionmaker).

    Returns:
        Health check result dict.
    """
    try:
        from sqlalchemy import text
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "service": "postgresql"}
    except Exception as e:
        return {"status": "unhealthy", "service": "postgresql", "error": str(e)}


async def check_redis(redis_client: Any) -> dict[str, Any]:
    """Check Redis connectivity.

    Args:
        redis_client: RedisClient instance.

    Returns:
        Health check result dict.
    """
    try:
        is_healthy = await redis_client.ping()
        status = "healthy" if is_healthy else "unhealthy"
        return {"status": status, "service": "redis"}
    except Exception as e:
        return {"status": "unhealthy", "service": "redis", "error": str(e)}


async def check_all(
    session_factory: Any, redis_client: Any
) -> dict[str, Any]:
    """Run all health checks and aggregate results.

    Args:
        session_factory: Async session factory.
        redis_client: RedisClient instance.

    Returns:
        Aggregated health check result.
    """
    db_check = await check_database(session_factory)
    redis_check = await check_redis(redis_client)

    checks = {"database": db_check, "redis": redis_check}
    all_healthy = all(c["status"] == "healthy" for c in checks.values())

    uptime = time.monotonic() - _start_time

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "uptime_seconds": round(uptime, 2),
        "checks": checks,
    }
