import pytest
import asyncio
import orjson
from unittest.mock import AsyncMock, MagicMock
from src.infrastructure.websocket.manager import ConnectionManager
from src.infrastructure.redis.pubsub import EventBus
from src.infrastructure.redis.client import RedisClient

@pytest.mark.asyncio
async def test_cross_node_sync_flow():
    # 1. Initialize two separate Redis clients (simulating two application nodes)
    # If not running in docker, our global patch uses MockRedisClient
    client_1 = RedisClient("redis://localhost:6379/0")
    client_2 = RedisClient("redis://localhost:6379/0")
    
    await client_1.connect()
    await client_2.connect()

    # 2. Instantiate EventBuses for both nodes
    bus_1 = EventBus(client_1, node_id="node-1")
    bus_2 = EventBus(client_2, node_id="node-2")
    bus_2._running = True  # Enable subscription listener loops

    # 3. Instantiate ConnectionManagers for both nodes
    mgr_1 = ConnectionManager()
    mgr_2 = ConnectionManager()

    # 4. Connect User 1 to Node 1
    ws1 = MagicMock()
    ws1.accept = AsyncMock()
    ws1.send_bytes = AsyncMock()
    await mgr_1.connect(ws1, "user-1", "device-1")
    mgr_1.add_to_room("user-1", "room-100")

    # 5. Connect User 2 to Node 2
    ws2 = MagicMock()
    ws2.accept = AsyncMock()
    ws2.send_bytes = AsyncMock()
    await mgr_2.connect(ws2, "user-2", "device-2")
    mgr_2.add_to_room("user-2", "room-100")

    # 6. Subscribe Node 2 to "room-100" messages via Redis EventBus
    # When a message is received, deliver it to local connections in the room
    async def on_sync_msg(event_dict):
        await mgr_2.send_to_room("room-100", event_dict)

    sub_task = await bus_2.subscribe_room("room-100", on_sync_msg)

    # 7. User 1 sends message via Node 1 EventBus
    message_payload = {"text": "Hello from Node 1"}
    await bus_1.publish_message("room-100", message_payload)

    # 8. Wait for Redis pub/sub processing
    await asyncio.sleep(0.05)

    # 9. Verify User 2 on Node 2 received the message
    assert ws2.send_bytes.called is True
    sent_data = ws2.send_bytes.call_args[0][0]
    sent_json = orjson.loads(sent_data)
    assert sent_json["text"] == "Hello from Node 1"

    # 10. Clean up connections, subscription tasks, and Redis clients
    await bus_2.stop()
    await mgr_1.disconnect("user-1", "device-1")
    await mgr_2.disconnect("user-2", "device-2")
    await client_1.disconnect()
    await client_2.disconnect()
