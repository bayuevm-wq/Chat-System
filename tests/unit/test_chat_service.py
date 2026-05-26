import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from src.application.services.chat_service import ChatService
from src.domain.exceptions import AuthorizationError, EntityNotFoundError
from src.infrastructure.database.models import MessageModel, RoomMemberModel

@pytest.fixture
def mock_message_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def mock_room_repo():
    repo = AsyncMock()
    repo.is_member = AsyncMock(return_value=True)
    return repo

@pytest.fixture
def mock_event_bus():
    bus = AsyncMock()
    return bus

@pytest.fixture
def mock_cache_service():
    cache = AsyncMock()
    return cache

@pytest.fixture
def chat_service(mock_message_repo, mock_room_repo, mock_event_bus, mock_cache_service):
    return ChatService(
        message_repo=mock_message_repo,
        room_repo=mock_room_repo,
        event_bus=mock_event_bus,
        cache_service=mock_cache_service
    )

@pytest.mark.asyncio
async def test_send_message_success(chat_service, mock_room_repo, mock_message_repo, mock_event_bus):
    room_id = uuid.uuid4()
    sender_id = uuid.uuid4()
    
    mock_msg = MagicMock(spec=MessageModel)
    mock_msg.id = 123
    mock_msg.room_id = room_id
    mock_msg.sender_id = sender_id
    mock_msg.content = "hello"
    mock_msg.message_type = "text"
    mock_msg.reply_to = None
    mock_message_repo.create = AsyncMock(return_value=mock_msg)
    
    # Mock members
    m1 = MagicMock(spec=RoomMemberModel)
    m1.user_id = sender_id
    m2 = MagicMock(spec=RoomMemberModel)
    m2.user_id = uuid.uuid4()
    mock_room_repo.get_members = AsyncMock(return_value=[m1, m2])

    result = await chat_service.send_message(
        room_id=room_id,
        sender_id=sender_id,
        content="hello",
    )

    assert result["message_id"] == 123
    assert result["content"] == "hello"
    mock_message_repo.create.assert_called_once()
    mock_event_bus.publish_message.assert_called_once()
    mock_message_repo.create_delivery.assert_called_once_with(123, m2.user_id, status="pending")

@pytest.mark.asyncio
async def test_send_message_not_member(chat_service, mock_room_repo):
    mock_room_repo.is_member = AsyncMock(return_value=False)
    
    with pytest.raises(AuthorizationError):
        await chat_service.send_message(
            room_id=uuid.uuid4(),
            sender_id=uuid.uuid4(),
            content="hello"
        )

@pytest.mark.asyncio
async def test_get_messages_paginated(chat_service, mock_message_repo):
    room_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    m1 = MagicMock(spec=MessageModel)
    m1.id = 1
    m1.room_id = room_id
    m1.sender_id = user_id
    m1.content = "msg1"
    m1.message_type = "text"
    m1.reply_to = None
    m1.is_edited = False
    m1.created_at = datetime.utcnow()

    mock_message_repo.get_by_room = AsyncMock(return_value=[m1])

    result = await chat_service.get_messages(room_id, user_id, limit=10)
    assert len(result) == 1
    assert result[0]["message_id"] == 1
    assert result[0]["content"] == "msg1"

@pytest.mark.asyncio
async def test_mark_read_updates_delivery(chat_service, mock_message_repo, mock_room_repo, mock_event_bus):
    room_id = uuid.uuid4()
    user_id = uuid.uuid4()
    message_id = 123

    await chat_service.mark_read(room_id, message_id, user_id)
    
    mock_message_repo.update_delivery_status.assert_called_once()
    mock_room_repo.update_last_read.assert_called_once()
    mock_event_bus.publish_message.assert_called_once()

@pytest.mark.asyncio
async def test_delete_message_by_sender(chat_service, mock_message_repo):
    user_id = uuid.uuid4()
    message_id = 123
    
    mock_msg = MagicMock(spec=MessageModel)
    mock_msg.id = message_id
    mock_msg.sender_id = user_id
    mock_message_repo.get_by_id = AsyncMock(return_value=mock_msg)
    mock_message_repo.soft_delete = AsyncMock(return_value=True)

    result = await chat_service.delete_message(message_id, user_id)
    assert result is True
    mock_message_repo.soft_delete.assert_called_once_with(message_id)

@pytest.mark.asyncio
async def test_delete_message_by_other(chat_service, mock_message_repo):
    user_id = uuid.uuid4()
    other_id = uuid.uuid4()
    message_id = 123
    
    mock_msg = MagicMock(spec=MessageModel)
    mock_msg.id = message_id
    mock_msg.sender_id = other_id
    mock_message_repo.get_by_id = AsyncMock(return_value=mock_msg)

    with pytest.raises(AuthorizationError):
        await chat_service.delete_message(message_id, user_id)

@pytest.mark.asyncio
async def test_edit_message_by_sender(chat_service, mock_message_repo):
    user_id = uuid.uuid4()
    message_id = 123
    
    mock_msg = MagicMock(spec=MessageModel)
    mock_msg.id = message_id
    mock_msg.sender_id = user_id
    mock_msg.content = "old"
    mock_message_repo.get_by_id = AsyncMock(return_value=mock_msg)
    
    updated_msg = MagicMock(spec=MessageModel)
    updated_msg.id = message_id
    updated_msg.content = "new"
    updated_msg.edited_at = datetime.utcnow()
    mock_message_repo.mark_edited = AsyncMock(return_value=updated_msg)

    result = await chat_service.edit_message(message_id, user_id, "new")
    assert result["content"] == "new"
    mock_message_repo.mark_edited.assert_called_once_with(message_id, "new")

@pytest.mark.asyncio
async def test_edit_message_by_other(chat_service, mock_message_repo):
    user_id = uuid.uuid4()
    other_id = uuid.uuid4()
    message_id = 123
    
    mock_msg = MagicMock(spec=MessageModel)
    mock_msg.id = message_id
    mock_msg.sender_id = other_id
    mock_message_repo.get_by_id = AsyncMock(return_value=mock_msg)

    with pytest.raises(AuthorizationError):
        await chat_service.edit_message(message_id, user_id, "new")
