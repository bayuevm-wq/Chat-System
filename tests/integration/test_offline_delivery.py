import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.application.services.notification_service import NotificationService
from src.infrastructure.workers.message_worker import OfflineMessageWorker
from src.infrastructure.websocket.manager import ConnectionManager
from src.infrastructure.redis.streams import StreamProcessor
from src.infrastructure.redis.client import RedisClient

@pytest.mark.asyncio
async def test_offline_message_delivery_flow():
    # 1. Setup mock infrastructure
    redis_client = RedisClient("redis://localhost:6379/0")
    await redis_client.connect()
    
    cache_service = MagicMock()
    stream_processor = StreamProcessor(redis_client, "workers", "worker-1")
    connection_manager = ConnectionManager()
    
    notif_service = NotificationService(stream_processor, cache_service)
    worker = OfflineMessageWorker(stream_processor, connection_manager, cache_service)
    worker._base_delay = 0.01  # Set small delay for testing fast retries

    # 2. Define offline user and message
    user_id = "user-offline-123"
    message_data = {
        "room_id": "room-123",
        "sender_id": "sender-456",
        "content": "Hey! Read this when you're back online."
    }

    # 3. User is offline (no connections in manager)
    assert connection_manager.is_user_connected(user_id) is False

    # 4. Queue the offline message via notification service
    # This writes a stream entry in `stream:offline`
    await notif_service.notify_offline_user(user_id, message_data)

    # 5. Connect the user (simulate user coming online / reconnecting)
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_bytes = AsyncMock()
    await connection_manager.connect(ws, user_id, "device-1")
    assert connection_manager.is_user_connected(user_id) is True

    # 6. Dequeue and process the offline message via worker
    # We retrieve the enqueued message from the stream using stream_processor
    # We patch/mock xreadgroup behavior dynamically or dequeue directly
    # Since we are using MockRedis or real Redis, dequeue will return the message
    # Let's override xreadgroup in mock redis client to pop the stream messages:
    if hasattr(redis_client.client, "streams"):
        # Unit test environment (MockRedis)
        client = redis_client.client
        if "stream:offline" in client.streams and client.streams["stream:offline"]:
            entry_id, fields = client.streams["stream:offline"].pop(0)
            import orjson
            data = orjson.loads(fields["data"])
            
            # Run the worker process_message logic directly on the popped data
            await worker._process_message(entry_id, data)
    else:
        # Integration test environment (real Redis)
        messages = await stream_processor.dequeue("stream:offline", count=1)
        if messages:
            msg_id, data = messages[0]
            await worker._process_message(msg_id, data)

    # 7. Verify the message was sent to the user's WebSocket
    await asyncio.sleep(0.01)
    assert ws.send_bytes.called is True
    sent_data = ws.send_bytes.call_args[0][0]
    import orjson
    sent_json = orjson.loads(sent_data)
    assert sent_json["content"] == "Hey! Read this when you're back online."

    # 8. Cleanup
    await connection_manager.disconnect(user_id, "device-1")
    await redis_client.disconnect()
