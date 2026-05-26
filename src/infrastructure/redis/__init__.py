"""Redis infrastructure layer for the Distributed Chat System.

Provides the core Redis integration including:
- Connection pooling and client management (:mod:`client`)
- Hybrid Pub/Sub + Streams event bus for real-time messaging (:mod:`pubsub`)
- Cache service for sessions, presence, typing, and room membership (:mod:`cache`)
- Stream-based durable queue processor with consumer groups (:mod:`streams`)

Usage::

    from src.infrastructure.redis.client import get_redis_client
    from src.infrastructure.redis.pubsub import EventBus
    from src.infrastructure.redis.cache import CacheService
    from src.infrastructure.redis.streams import StreamProcessor
"""
