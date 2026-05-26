from fastapi.testclient import TestClient

def test_websocket_lifecycle(test_app):
    client = TestClient(test_app)
    
    # 1. Register a user to get the authentication token
    reg_response = client.post("/api/auth/register", json={
        "username": "wsflowuser",
        "email": "wsflow@example.com",
        "password": "password123"
    })
    assert reg_response.status_code == 201
    token = reg_response.json()["access_token"]
    
    # 2. Fetch a short-lived WebSocket token
    ws_tok_res = client.post("/api/auth/ws-token", headers={"Authorization": f"Bearer {token}"})
    assert ws_tok_res.status_code == 200
    ws_token = ws_tok_res.json()["ws_token"]
    
    # 3. Establish the WebSocket connection
    with client.websocket_connect(f"/ws?token={ws_token}") as websocket:
        # Upon connection, the server sends a connected confirmation event
        conn_event = websocket.receive_json()
        assert conn_event["type"] == "connected"
        assert conn_event["session_id"] is not None
        
        # 4. Create a chat room via REST API
        room_res = client.post(
            "/api/rooms/",
            json={"name": "WS Flow Room", "type": "public"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert room_res.status_code == 201
        room_id = room_res.json()["id"]
        
        # 5. Join the room via WebSocket
        websocket.send_json({
            "type": "room.join",
            "room_id": room_id
        })
        join_ack = websocket.receive_json()
        assert join_ack["type"] == "room.updated"
        assert join_ack["event"] == "joined"
        assert join_ack["room_id"] == room_id
        
        # 6. Send a message to the room via WebSocket
        websocket.send_json({
            "type": "message.send",
            "room_id": room_id,
            "content": "Hello world from WebSocket!"
        })
        msg_ack = websocket.receive_json()
        assert msg_ack["type"] == "message.ack"
        assert msg_ack["status"] == "sent"
        assert "message_id" in msg_ack
        
        # 7. Send a heartbeat to keep connection alive
        websocket.send_json({
            "type": "presence.heartbeat"
        })
        pong = websocket.receive_json()
        assert pong["type"] == "pong"
