import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from src.application.services.room_service import RoomService
from src.domain.exceptions import AuthorizationError, EntityNotFoundError, RoomFullError
from src.infrastructure.database.models import RoomModel, RoomMemberModel
from src.shared.constants import RoomType

@pytest.fixture
def mock_room_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def mock_cache_service():
    cache = AsyncMock()
    return cache

@pytest.fixture
def mock_event_bus():
    bus = AsyncMock()
    return bus

@pytest.fixture
def room_service(mock_room_repo, mock_cache_service, mock_event_bus):
    return RoomService(
        room_repo=mock_room_repo,
        cache_service=mock_cache_service,
        event_bus=mock_event_bus
    )

@pytest.mark.asyncio
async def test_create_room(room_service, mock_room_repo, mock_cache_service, mock_event_bus):
    creator_id = uuid.uuid4()
    
    mock_room = MagicMock(spec=RoomModel)
    mock_room.id = uuid.uuid4()
    mock_room.name = "Public Chat"
    mock_room.type = RoomType.PUBLIC
    mock_room.description = "Test Desc"
    mock_room.max_members = 500
    mock_room.created_by = creator_id
    
    mock_room_repo.create = AsyncMock(return_value=mock_room)

    result = await room_service.create_room("Public Chat", RoomType.PUBLIC, creator_id, description="Test Desc")
    
    assert result["name"] == "Public Chat"
    assert result["type"] == RoomType.PUBLIC
    mock_room_repo.create.assert_called_once()
    mock_room_repo.add_member.assert_called_once_with(mock_room.id, creator_id, role="owner")
    mock_cache_service.invalidate_room_members.assert_called_once_with(str(mock_room.id))
    mock_event_bus.publish_system.assert_called_once()

@pytest.mark.asyncio
async def test_join_room_success(room_service, mock_room_repo, mock_cache_service, mock_event_bus):
    room_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_room = MagicMock(spec=RoomModel)
    mock_room.id = room_id
    mock_room.type = RoomType.PUBLIC
    mock_room.max_members = 10
    mock_room_repo.get_by_id = AsyncMock(return_value=mock_room)
    
    mock_room_repo.get_members = AsyncMock(return_value=[MagicMock()]*5)
    mock_room_repo.is_member = AsyncMock(return_value=False)

    result = await room_service.join_room(room_id, user_id)
    assert result["status"] == "joined"
    mock_room_repo.add_member.assert_called_once_with(room_id, user_id)
    mock_cache_service.invalidate_room_members.assert_called_once_with(str(room_id))
    mock_event_bus.publish_message.assert_called_once()

@pytest.mark.asyncio
async def test_join_room_full(room_service, mock_room_repo):
    room_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_room = MagicMock(spec=RoomModel)
    mock_room.id = room_id
    mock_room.type = RoomType.PUBLIC
    mock_room.max_members = 5
    mock_room_repo.get_by_id = AsyncMock(return_value=mock_room)
    mock_room_repo.get_members = AsyncMock(return_value=[MagicMock()]*5)

    with pytest.raises(RoomFullError):
        await room_service.join_room(room_id, user_id)

@pytest.mark.asyncio
async def test_join_direct_room_fails(room_service, mock_room_repo):
    room_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_room = MagicMock(spec=RoomModel)
    mock_room.id = room_id
    mock_room.type = RoomType.DIRECT
    mock_room_repo.get_by_id = AsyncMock(return_value=mock_room)

    with pytest.raises(AuthorizationError):
        await room_service.join_room(room_id, user_id)

@pytest.mark.asyncio
async def test_leave_room(room_service, mock_room_repo, mock_cache_service, mock_event_bus):
    room_id = uuid.uuid4()
    user_id = uuid.uuid4()

    await room_service.leave_room(room_id, user_id)
    
    mock_room_repo.remove_member.assert_called_once_with(room_id, user_id)
    mock_cache_service.invalidate_room_members.assert_called_once_with(str(room_id))
    mock_event_bus.publish_message.assert_called_once()

@pytest.mark.asyncio
async def test_get_room_not_member(room_service, mock_room_repo):
    room_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_room = MagicMock(spec=RoomModel)
    mock_room_repo.get_by_id = AsyncMock(return_value=mock_room)
    mock_room_repo.is_member = AsyncMock(return_value=False)

    with pytest.raises(AuthorizationError):
        await room_service.get_room(room_id, user_id)

@pytest.mark.asyncio
async def test_get_or_create_dm(room_service, mock_room_repo):
    user1 = uuid.uuid4()
    user2 = uuid.uuid4()
    
    mock_room = MagicMock(spec=RoomModel)
    mock_room.id = uuid.uuid4()
    mock_room.name = None
    mock_room.type = RoomType.DIRECT
    mock_room_repo.get_or_create_direct_room = AsyncMock(return_value=mock_room)

    result = await room_service.get_or_create_dm(user1, user2)
    assert result["type"] == RoomType.DIRECT
    mock_room_repo.get_or_create_direct_room.assert_called_once_with(user1, user2)
