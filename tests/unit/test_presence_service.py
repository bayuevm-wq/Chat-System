import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from src.application.services.presence_service import PresenceService
from src.shared.constants import UserStatus, WSEventType
from src.infrastructure.database.models import UserModel

@pytest.fixture
def mock_cache_service():
    cache = AsyncMock()
    cache.get_presence = AsyncMock(return_value="online")
    cache.get_online_users = AsyncMock(return_value=["user-123"])
    return cache

@pytest.fixture
def mock_event_bus():
    bus = AsyncMock()
    return bus

@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def presence_service(mock_cache_service, mock_event_bus, mock_user_repo):
    return PresenceService(
        cache_service=mock_cache_service,
        event_bus=mock_event_bus,
        user_repo=mock_user_repo
    )

@pytest.mark.asyncio
async def test_set_online(presence_service, mock_cache_service, mock_event_bus):
    user_id = str(uuid.uuid4())
    node_id = "node-1"
    device_id = "device-1"

    await presence_service.set_online(user_id, node_id, device_id)
    
    mock_cache_service.set_presence.assert_called_once()
    mock_event_bus.publish_presence.assert_called_once()
    args = mock_event_bus.publish_presence.call_args[0][0]
    assert args["status"] == UserStatus.ONLINE
    assert args["user_id"] == user_id

@pytest.mark.asyncio
async def test_set_offline(presence_service, mock_cache_service, mock_event_bus, mock_user_repo):
    user_id = str(uuid.uuid4())

    await presence_service.set_offline(user_id)
    
    mock_cache_service.remove_presence.assert_called_once_with(user_id)
    mock_user_repo.update_last_seen.assert_called_once()
    mock_event_bus.publish_presence.assert_called_once()
    args = mock_event_bus.publish_presence.call_args[0][0]
    assert args["status"] == UserStatus.OFFLINE
    assert args["user_id"] == user_id

@pytest.mark.asyncio
async def test_heartbeat(presence_service, mock_cache_service):
    user_id = "user-123"
    await presence_service.heartbeat(user_id)
    mock_cache_service.heartbeat.assert_called_once()

@pytest.mark.asyncio
async def test_update_status(presence_service, mock_cache_service, mock_event_bus):
    from unittest.mock import ANY
    user_id = "user-123"
    await presence_service.update_status(user_id, UserStatus.AWAY)
    mock_cache_service.set_presence.assert_called_once_with(user_id, UserStatus.AWAY, ttl=ANY)
    mock_event_bus.publish_presence.assert_called_once()

@pytest.mark.asyncio
async def test_get_status_online(presence_service, mock_cache_service):
    user_id = "user-123"
    mock_cache_service.get_presence = AsyncMock(return_value=UserStatus.ONLINE)
    
    result = await presence_service.get_status(user_id)
    assert result["status"] == UserStatus.ONLINE

@pytest.mark.asyncio
async def test_get_status_offline_with_last_seen(presence_service, mock_cache_service, mock_user_repo):
    user_id = str(uuid.uuid4())
    mock_cache_service.get_presence = AsyncMock(return_value=None)
    
    mock_user = MagicMock(spec=UserModel)
    mock_user.last_seen_at = datetime_val = MagicMock()
    datetime_val.isoformat = MagicMock(return_value="2026-05-26T00:00:00")
    mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

    result = await presence_service.get_status(user_id)
    assert result["status"] == UserStatus.OFFLINE
    assert result["last_seen_at"] == "2026-05-26T00:00:00"

@pytest.mark.asyncio
async def test_set_typing(presence_service, mock_cache_service, mock_event_bus):
    user_id = "user-1"
    room_id = "room-1"
    
    await presence_service.set_typing(user_id, room_id, is_typing=True)
    mock_cache_service.set_typing.assert_called_once()
    mock_event_bus.publish_message.assert_called_once()
