import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.infrastructure.websocket.manager import ConnectionManager, ConnectionInfo

@pytest.fixture
def manager():
    return ConnectionManager()

@pytest.fixture
def mock_websocket():
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_bytes = AsyncMock()
    ws.close = AsyncMock()
    return ws

@pytest.mark.asyncio
async def test_connect_creates_queue(manager, mock_websocket):
    user_id = "user-123"
    device_id = "device-1"

    conn = await manager.connect(mock_websocket, user_id, device_id)
    
    assert isinstance(conn, ConnectionInfo)
    assert conn.user_id == user_id
    assert conn.device_id == device_id
    assert conn.queue.maxsize == manager._queue_size
    assert conn.send_task is not None
    assert manager.connection_count == 1
    assert manager.is_user_connected(user_id) is True

    # Clean up background task
    await manager.disconnect(user_id, device_id)

@pytest.mark.asyncio
async def test_disconnect_cleanup(manager, mock_websocket):
    user_id = "user-123"
    device_id = "device-1"

    conn = await manager.connect(mock_websocket, user_id, device_id)
    send_task = conn.send_task
    
    await manager.disconnect(user_id, device_id)
    
    assert manager.connection_count == 0
    assert manager.is_user_connected(user_id) is False
    assert send_task.cancelled() is True
    mock_websocket.close.assert_called_once()

@pytest.mark.asyncio
async def test_send_to_user(manager, mock_websocket):
    user_id = "user-123"
    device_id = "device-1"
    
    conn = await manager.connect(mock_websocket, user_id, device_id)
    
    message = {"text": "hello"}
    await manager.send_to_user(user_id, message)
    
    # Wait for queue and send loop
    await asyncio.sleep(0.01)
    mock_websocket.send_bytes.assert_called_once()
    
    await manager.disconnect(user_id, device_id)

@pytest.mark.asyncio
async def test_send_to_room(manager, mock_websocket):
    user_id_1 = "user-1"
    user_id_2 = "user-2"
    room_id = "room-99"

    ws1 = MagicMock()
    ws1.accept = AsyncMock()
    ws1.send_bytes = AsyncMock()
    ws1.close = AsyncMock()

    ws2 = MagicMock()
    ws2.accept = AsyncMock()
    ws2.send_bytes = AsyncMock()
    ws2.close = AsyncMock()

    await manager.connect(ws1, user_id_1, "device-1")
    await manager.connect(ws2, user_id_2, "device-2")

    manager.add_to_room(user_id_1, room_id)
    manager.add_to_room(user_id_2, room_id)

    message = {"text": "hello room"}
    await manager.send_to_room(room_id, message)

    await asyncio.sleep(0.01)
    ws1.send_bytes.assert_called_once()
    ws2.send_bytes.assert_called_once()

    await manager.disconnect(user_id_1, "device-1")
    await manager.disconnect(user_id_2, "device-2")

@pytest.mark.asyncio
async def test_send_to_room_excludes_sender(manager, mock_websocket):
    user_id_1 = "user-1"
    user_id_2 = "user-2"
    room_id = "room-99"

    ws2 = MagicMock()
    ws2.accept = AsyncMock()
    ws2.send_bytes = AsyncMock()
    ws2.close = AsyncMock()

    await manager.connect(mock_websocket, user_id_1, "device-1")
    await manager.connect(ws2, user_id_2, "device-2")

    manager.add_to_room(user_id_1, room_id)
    manager.add_to_room(user_id_2, room_id)

    message = {"text": "hello room"}
    await manager.send_to_room(room_id, message, exclude_user=user_id_1)

    await asyncio.sleep(0.01)
    mock_websocket.send_bytes.assert_not_called()
    ws2.send_bytes.assert_called_once()

    await manager.disconnect(user_id_1, "device-1")
    await manager.disconnect(user_id_2, "device-2")

@pytest.mark.asyncio
async def test_backpressure_drops_oldest(manager, mock_websocket):
    # Set small queue size for test
    manager._queue_size = 2
    user_id = "user-123"
    
    # We create connection but cancel send loop so queue fills up
    conn = await manager.connect(mock_websocket, user_id, "device-1")
    conn.send_task.cancel()
    
    manager._enqueue(conn, b"msg1")
    manager._enqueue(conn, b"msg2")
    assert conn.queue.full() is True
    
    # This should drop "msg1" and keep "msg2" and add "msg3"
    manager._enqueue(conn, b"msg3")
    
    assert conn.queue.get_nowait() == b"msg2"
    assert conn.queue.get_nowait() == b"msg3"
    
    await manager.disconnect(user_id, "device-1")

@pytest.mark.asyncio
async def test_max_connections_per_user(manager, mock_websocket):
    manager._max_per_user = 2
    user_id = "user-123"
    
    ws1 = MagicMock()
    ws1.accept = AsyncMock()
    ws1.close = AsyncMock()
    
    ws2 = MagicMock()
    ws2.accept = AsyncMock()
    ws2.close = AsyncMock()
    
    ws3 = MagicMock()
    ws3.accept = AsyncMock()
    ws3.close = AsyncMock()

    await manager.connect(ws1, user_id, "d1")
    await manager.connect(ws2, user_id, "d2")
    assert manager.connection_count == 2
    
    # Connecting 3rd should evict "d1"
    await manager.connect(ws3, user_id, "d3")
    assert manager.connection_count == 2
    assert "d1" not in manager._connections[user_id]
    ws1.close.assert_called_once()
    
    await manager.disconnect(user_id, "d2")
    await manager.disconnect(user_id, "d3")
