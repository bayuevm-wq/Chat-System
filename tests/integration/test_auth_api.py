import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_auth_full_flow(http_client: AsyncClient):
    # 1. Register a new user
    register_payload = {
        "username": "integrationuser",
        "email": "integration@example.com",
        "password": "supersecurepassword123",
        "display_name": "Integration User"
    }
    
    reg_response = await http_client.post("/api/auth/register", json=register_payload)
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert reg_data["user"]["username"] == "integrationuser"
    assert "access_token" in reg_data
    assert "refresh_token" in reg_data
    
    access_token = reg_data["access_token"]
    refresh_token = reg_data["refresh_token"]

    # 2. Try to register with duplicate username
    dup_response = await http_client.post("/api/auth/register", json=register_payload)
    assert dup_response.status_code == 409  # Conflict / Duplicate

    # 3. Login
    login_payload = {
        "email": "integration@example.com",
        "password": "supersecurepassword123"
    }
    login_response = await http_client.post("/api/auth/login", json=login_payload)
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    
    # 4. Refresh token
    refresh_payload = {
        "refresh_token": refresh_token
    }
    refresh_response = await http_client.post("/api/auth/refresh", json=refresh_payload)
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert "access_token" in refresh_data
    new_access_token = refresh_data["access_token"]

    # 5. Get WS Token (requires authentication)
    headers = {"Authorization": f"Bearer {new_access_token}"}
    ws_tok_response = await http_client.post("/api/auth/ws-token", headers=headers)
    assert ws_tok_response.status_code == 200
    assert "ws_token" in ws_tok_response.json()

    # 6. Logout
    logout_response = await http_client.post("/api/auth/logout", headers=headers)
    assert logout_response.status_code == 204

    # 7. Access protected endpoint after logout (should fail because token is blacklisted)
    blocked_response = await http_client.post("/api/auth/ws-token", headers=headers)
    assert blocked_response.status_code == 401
