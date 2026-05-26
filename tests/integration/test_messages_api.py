import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.models import MessageModel

@pytest.mark.asyncio
async def test_messages_rest_endpoints(http_client: AsyncClient, db_session: AsyncSession):
    # 1. Register user and create room
    reg_res = await http_client.post("/api/auth/register", json={
        "username": "msgtester",
        "email": "msg@example.com",
        "password": "password123"
    })
    assert reg_res.status_code == 201
    user = reg_res.json()["user"]
    user_id = uuid.UUID(user["id"])
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    room_res = await http_client.post("/api/rooms/", json={
        "name": "Msg Room",
        "type": "public"
    }, headers=headers)
    assert room_res.status_code == 201
    room_id = uuid.UUID(room_res.json()["id"])

    # 2. Seed a message directly into the database session
    db_msg = MessageModel(
        room_id=room_id,
        sender_id=user_id,
        content="This is a test message for searching and editing.",
        message_type="text"
    )
    db_session.add(db_msg)
    await db_session.commit()
    message_id = db_msg.id

    # 3. Retrieve room history via REST
    history_res = await http_client.get(f"/api/messages/{room_id}", headers=headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 1
    assert history[0]["message_id"] == message_id
    assert history[0]["content"] == "This is a test message for searching and editing."

    # 4. Search room messages via REST
    search_res = await http_client.get(f"/api/messages/{room_id}/search?q=searching", headers=headers)
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) == 1
    assert results[0]["message_id"] == message_id

    # 5. Edit the message via REST
    edit_res = await http_client.patch(
        f"/api/messages/{message_id}",
        json={"content": "This is an edited message."},
        headers=headers
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["content"] == "This is an edited message."
    assert edit_res.json()["is_edited"] is True

    # 6. Soft-delete the message via REST
    del_res = await http_client.delete(f"/api/messages/{message_id}", headers=headers)
    assert del_res.status_code == 204

    # 7. Verify history is empty (soft deleted messages are filtered out)
    history_after_del = await http_client.get(f"/api/messages/{room_id}", headers=headers)
    assert history_after_del.status_code == 200
    assert len(history_after_del.json()) == 0
