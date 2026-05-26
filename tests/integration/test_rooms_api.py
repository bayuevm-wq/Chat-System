import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_rooms_rest_workflow(http_client: AsyncClient):
    # 1. Register User 1 and User 2
    u1_reg = await http_client.post("/api/auth/register", json={
        "username": "roomowner",
        "email": "owner@example.com",
        "password": "password123"
    })
    u2_reg = await http_client.post("/api/auth/register", json={
        "username": "roomguest",
        "email": "guest@example.com",
        "password": "password123"
    })
    
    assert u1_reg.status_code == 201
    assert u2_reg.status_code == 201
    
    t1 = u1_reg.json()["access_token"]
    t2 = u2_reg.json()["access_token"]
    
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}

    # 2. User 1 creates a public room
    room_payload = {
        "name": "General Chat",
        "type": "public",
        "description": "General discussions",
        "max_members": 100
    }
    create_res = await http_client.post("/api/rooms/", json=room_payload, headers=h1)
    assert create_res.status_code == 201
    room = create_res.json()
    room_id = room["id"]
    assert room["name"] == "General Chat"

    # 3. User 1 lists their rooms (should contain "General Chat")
    list_res1 = await http_client.get("/api/rooms/", headers=h1)
    assert list_res1.status_code == 200
    rooms1 = list_res1.json()
    assert len(rooms1) == 1
    assert rooms1[0]["id"] == room_id

    # 4. User 2 lists their rooms (should be empty)
    list_res2 = await http_client.get("/api/rooms/", headers=h2)
    assert list_res2.status_code == 200
    assert len(list_res2.json()) == 0

    # 5. User 2 joins the room
    join_res = await http_client.post(f"/api/rooms/{room_id}/join", headers=h2)
    assert join_res.status_code == 200
    assert join_res.json()["status"] == "joined"

    # 6. User 2 gets room details
    get_res = await http_client.get(f"/api/rooms/{room_id}", headers=h2)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "General Chat"

    # 7. User 2 gets room members (should see both)
    members_res = await http_client.get(f"/api/rooms/{room_id}/members", headers=h2)
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 2
    user_ids = {m["user_id"] for m in members}
    assert u1_reg.json()["user"]["id"] in user_ids
    assert u2_reg.json()["user"]["id"] in user_ids

    # 8. User 2 leaves the room
    leave_res = await http_client.post(f"/api/rooms/{room_id}/leave", headers=h2)
    assert leave_res.status_code == 204

    # 9. User 2 gets room details again (should fail with 403 / AuthorizationError)
    get_fail_res = await http_client.get(f"/api/rooms/{room_id}", headers=h2)
    assert get_fail_res.status_code == 403
