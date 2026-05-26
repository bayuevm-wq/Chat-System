import pytest
import jwt
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from src.infrastructure.security.jwt_handler import JWTHandler

@pytest.fixture
def mock_cache_service():
    cache = AsyncMock()
    cache.get_session = AsyncMock(return_value=None)
    cache.store_session = AsyncMock(return_value=True)
    return cache

@pytest.fixture
def jwt_handler(mock_cache_service):
    return JWTHandler(cache_service=mock_cache_service)

def test_create_access_token(jwt_handler):
    token = jwt_handler.create_access_token("user-1")
    payload = jwt_handler.decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload

def test_create_refresh_token(jwt_handler):
    token = jwt_handler.create_refresh_token("user-2")
    payload = jwt_handler.decode_token(token)
    assert payload["sub"] == "user-2"
    assert payload["type"] == "refresh"

def test_create_ws_token(jwt_handler):
    token = jwt_handler.create_ws_token("user-3")
    payload = jwt_handler.decode_token(token)
    assert payload["sub"] == "user-3"
    assert payload["type"] == "ws"

def test_decode_invalid_token(jwt_handler):
    with pytest.raises(jwt.InvalidTokenError):
        jwt_handler.decode_token("invalid.token.here")

def test_decode_expired_token(jwt_handler):
    # Artificially set access token expiry to negative value to test expiration
    jwt_handler._access_ttl = timedelta(seconds=-5)
    token = jwt_handler.create_access_token("user-1")
    
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt_handler.decode_token(token)

@pytest.mark.asyncio
async def test_blacklist_and_check(jwt_handler, mock_cache_service):
    token_id = "test-jti-123"
    
    # First check: not blacklisted
    assert await jwt_handler.is_blacklisted(token_id) is False
    
    # Blacklist it
    await jwt_handler.blacklist_token(token_id, ttl=10)
    mock_cache_service.store_session.assert_called_once_with(f"blacklist:{token_id}", {"revoked": True}, 10)
    
    # Second check: simulate it is blacklisted in cache
    mock_cache_service.get_session = AsyncMock(return_value={"revoked": True})
    assert await jwt_handler.is_blacklisted(token_id) is True
