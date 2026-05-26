import pytest
import uuid
from datetime import datetime, timedelta
from src.domain.entities.message import Message
from src.domain.entities.user import User
from src.domain.entities.session import UserSession
from src.shared.constants import MessageType, UserStatus

def test_message_soft_delete():
    room_id = uuid.uuid4()
    sender_id = uuid.uuid4()
    msg = Message(room_id=room_id, sender_id=sender_id, content="hello")
    
    assert msg.is_deleted is False
    assert msg.deleted_at is None
    
    msg.soft_delete()
    
    assert msg.is_deleted is True
    assert isinstance(msg.deleted_at, datetime)

def test_message_edit():
    room_id = uuid.uuid4()
    sender_id = uuid.uuid4()
    msg = Message(room_id=room_id, sender_id=sender_id, content="original content")
    
    assert msg.is_edited is False
    assert msg.edited_at is None
    
    msg.edit("new content")
    
    assert msg.content == "new content"
    assert msg.is_edited is True
    assert isinstance(msg.edited_at, datetime)

def test_message_to_dict():
    room_id = uuid.uuid4()
    sender_id = uuid.uuid4()
    msg = Message(room_id=room_id, sender_id=sender_id, content="hello", id=999)
    
    d = msg.to_dict()
    assert d["id"] == 999
    assert d["room_id"] == str(room_id)
    assert d["sender_id"] == str(sender_id)
    assert d["content"] == "hello"
    assert d["message_type"] == "text"
    assert d["is_deleted"] is False

def test_user_session_expiry():
    from src.shared.utils import utc_now
    user_id = uuid.uuid4()
    expires_at = utc_now() + timedelta(seconds=10)
    session = UserSession(
        user_id=user_id,
        device_id="device-abc",
        node_id="node-1",
        token_hash="tokenhash",
        expires_at=expires_at
    )
    
    assert session.is_expired() is False
    
    session.expires_at = utc_now() - timedelta(seconds=1)
    assert session.is_expired() is True

def test_user_to_dict():
    user_id = uuid.uuid4()
    user = User(
        username="john_doe",
        email="john@example.com",
        password_hash="secret_hash",
        id=user_id,
        display_name="John Doe",
        status=UserStatus.ONLINE
    )
    
    d = user.to_dict()
    assert d["id"] == str(user_id)
    assert d["username"] == "john_doe"
    assert d["email"] == "john@example.com"
    assert d["status"] == "online"
    # Make sure password hash is NOT leaked
    assert "password_hash" not in d
