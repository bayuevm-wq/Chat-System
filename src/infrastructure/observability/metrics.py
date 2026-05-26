"""
Prometheus metrics collector.

Defines application metrics for monitoring WebSocket connections,
message throughput, latency, and system health.
"""

from __future__ import annotations

from functools import lru_cache

from prometheus_client import Counter, Gauge, Histogram


class MetricsCollector:
    """Singleton collection of Prometheus metrics for the chat system."""

    def __init__(self) -> None:
        # ── WebSocket Metrics ───────────────────────────────────
        self.ws_connections_total = Counter(
            "ws_connections_total", "Total WebSocket connections established"
        )
        self.ws_connections_active = Gauge(
            "ws_connections_active", "Currently active WebSocket connections"
        )
        self.ws_messages_received = Counter(
            "ws_messages_received_total", "Total WebSocket messages received from clients"
        )

        # ── Messaging Metrics ───────────────────────────────────
        self.messages_sent_total = Counter(
            "messages_sent_total", "Total messages sent", ["room_type"]
        )
        self.messages_delivered_total = Counter(
            "messages_delivered_total", "Total messages delivered"
        )
        self.message_latency_seconds = Histogram(
            "message_latency_seconds",
            "Message delivery latency in seconds",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )

        # ── HTTP Metrics ────────────────────────────────────────
        self.http_requests_total = Counter(
            "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
        )
        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration",
            ["method", "path"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
        )

        # ── Infrastructure Metrics ──────────────────────────────
        self.redis_operations_total = Counter(
            "redis_operations_total", "Total Redis operations", ["operation"]
        )
        self.db_query_duration_seconds = Histogram(
            "db_query_duration_seconds",
            "Database query duration",
            buckets=[0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
        )

        # ── Queue Metrics ───────────────────────────────────────
        self.offline_queue_size = Gauge(
            "offline_queue_size", "Current size of the offline message queue"
        )
        self.active_rooms = Gauge(
            "active_rooms", "Number of rooms with active connections"
        )


@lru_cache(maxsize=1)
def get_metrics() -> MetricsCollector:
    """Get the singleton metrics collector instance."""
    return MetricsCollector()
