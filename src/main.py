"""
FastAPI application factory and entry point.

Creates the FastAPI application with lifespan management for startup/shutdown
of all infrastructure services, middleware registration, and router mounting.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from slowapi.errors import RateLimitExceeded

from src.api.middleware.error_handler import domain_exception_handler, generic_exception_handler
from src.api.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from src.api.rest.auth_router import router as auth_router
from src.api.rest.health_router import router as health_router
from src.api.rest.messages_router import router as messages_router
from src.api.rest.rooms_router import router as rooms_router
from src.api.rest.users_router import router as users_router
from src.api.websocket.ws_router import router as ws_router
from src.config import get_settings
from src.domain.exceptions import DomainError
from src.infrastructure.observability.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — manages startup and shutdown of all services.

    Startup:
    1. Configure structured logging
    2. Connect to Redis
    3. Initialize database
    4. Create shared service instances
    5. Register this node in the cluster
    6. Start background workers
    7. Start Redis pub/sub subscriptions

    Shutdown:
    1. Stop background workers
    2. Deregister node
    3. Disconnect Redis
    4. Close database connections
    """
    settings = get_settings()

    # ── Startup ─────────────────────────────────────────────────
    setup_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)
    logger.info(
        "Starting Distributed Chat System",
        extra={"node_id": settings.NODE_ID, "environment": settings.ENVIRONMENT},
    )

    # Connect Redis
    from src.infrastructure.redis.client import RedisClient
    redis_client = RedisClient(
        url=settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
    )
    await redis_client.connect()
    app.state.redis_client = redis_client

    # Initialize database
    from src.infrastructure.database.connection import init_db
    await init_db()

    # Create shared services
    from src.infrastructure.redis.pubsub import EventBus
    from src.infrastructure.redis.cache import CacheService
    from src.infrastructure.redis.streams import StreamProcessor
    from src.infrastructure.websocket.manager import ConnectionManager

    cache_service = CacheService(redis_client)
    event_bus = EventBus(redis_client, settings.NODE_ID)
    stream_processor = StreamProcessor(
        redis_client,
        consumer_group=f"chat-workers-{settings.NODE_ID}",
        consumer_name=settings.NODE_ID,
    )
    connection_manager = ConnectionManager()

    app.state.cache_service = cache_service
    app.state.event_bus = event_bus
    app.state.stream_processor = stream_processor
    app.state.connection_manager = connection_manager

    # Register node in cluster
    await cache_service.register_node(settings.NODE_ID, {
        "host": settings.HOST,
        "port": settings.PORT,
        "node_id": settings.NODE_ID,
    })

    # Start background workers
    from src.infrastructure.workers.message_worker import OfflineMessageWorker
    from src.infrastructure.workers.notification_worker import NotificationWorker

    msg_worker = OfflineMessageWorker(stream_processor, connection_manager, cache_service)
    notif_worker = NotificationWorker(stream_processor, connection_manager)
    await msg_worker.start()
    await notif_worker.start()
    app.state.workers = [msg_worker, notif_worker]

    # Start Redis subscriptions for cross-node message routing
    async def on_room_message(room_id: str, message_data: str) -> None:
        """Callback for Redis pub/sub room messages — deliver to local connections."""
        import orjson
        try:
            data = orjson.loads(message_data) if isinstance(message_data, (str, bytes)) else message_data
            await connection_manager.send_to_room(room_id, data)
        except Exception as e:
            logger.error("Room message delivery error", extra={"error": str(e)})

    async def on_presence_event(event_data: str) -> None:
        """Callback for presence events from other nodes."""
        import orjson
        try:
            data = orjson.loads(event_data) if isinstance(event_data, (str, bytes)) else event_data
            # Broadcast presence change to all local connections
            await connection_manager.broadcast(data)
        except Exception as e:
            logger.error("Presence event error", extra={"error": str(e)})

    await event_bus.subscribe_presence(on_presence_event)
    await event_bus.subscribe_node(settings.NODE_ID, on_presence_event)

    logger.info("All services started", extra={"node_id": settings.NODE_ID})

    yield

    # ── Shutdown ────────────────────────────────────────────────
    logger.info("Shutting down...", extra={"node_id": settings.NODE_ID})

    # Stop workers
    for worker in app.state.workers:
        await worker.stop()

    # Stop event bus subscriptions
    await event_bus.stop()

    # Deregister node (TTL will expire naturally, but clean up explicitly)
    try:
        await redis_client.client.delete(f"node:{settings.NODE_ID}")
    except Exception:
        pass

    # Disconnect Redis
    await redis_client.disconnect()

    # Close database
    from src.infrastructure.database.connection import close_db
    await close_db()

    logger.info("Shutdown complete", extra={"node_id": settings.NODE_ID})


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="Distributed Chat System",
        description=(
            "Production-grade distributed chat backend with real-time messaging, "
            "multi-node synchronization, and fault tolerance."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # ── Middleware ───────────────────────────────────────────────

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Error handling
    app.add_exception_handler(DomainError, domain_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]

    # ── Routers ─────────────────────────────────────────────────
    app.include_router(auth_router)
    app.include_router(rooms_router)
    app.include_router(messages_router)
    app.include_router(users_router)
    app.include_router(health_router)
    app.include_router(ws_router)

    # ── Prometheus Metrics ──────────────────────────────────────
    if settings.METRICS_ENABLED:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    return app


# Module-level app instance for uvicorn
app = create_app()
