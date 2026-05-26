import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.services.auth_service import AuthService
from src.domain.exceptions import AuthenticationError, DuplicateEntityError
from src.infrastructure.security.jwt_handler import JWTHandler
from src.infrastructure.security.password import PasswordHasher
from src.infrastructure.security.encryption import EncryptionService
from src.infrastructure.database.models import UserModel

@pytest.fixture
def mock_user_repo():
    repo = AsyncMock()
    repo.exists = AsyncMock(return_value=False)
    return repo

@pytest.fixture
def mock_cache_service():
    cache = AsyncMock()
    cache.get_session = AsyncMock(return_value=None)
    cache.store_session = AsyncMock(return_value=True)
    return cache

@pytest.fixture
def jwt_handler(mock_cache_service):
    return JWTHandler(cache_service=mock_cache_service)

@pytest.fixture
def password_hasher():
    return PasswordHasher()

@pytest.fixture
def encryption_service():
    return EncryptionService()

@pytest.fixture
def auth_service(mock_user_repo, jwt_handler, password_hasher, mock_cache_service, encryption_service):
    return AuthService(
        user_repo=mock_user_repo,
        jwt_handler=jwt_handler,
        password_hasher=password_hasher,
        cache_service=mock_cache_service,
        encryption_service=encryption_service
    )

@pytest.mark.asyncio
async def test_register_success(auth_service, mock_user_repo):
    # Setup mock user return
    mock_user = MagicMock(spec=UserModel)
    mock_user.id = "user-id-123"
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.display_name = "testuser"
    mock_user_repo.create = AsyncMock(return_value=mock_user)

    result = await auth_service.register(
        username="testuser",
        email="test@example.com",
        password="securepassword",
        display_name="testuser"
    )

    assert result["user"]["username"] == "testuser"
    assert result["user"]["email"] == "test@example.com"
    assert "access_token" in result
    assert "refresh_token" in result
    mock_user_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_register_duplicate_username(auth_service, mock_user_repo):
    mock_user_repo.exists = AsyncMock(side_effect=lambda username=None, email=None: username == "testuser")

    with pytest.raises(DuplicateEntityError) as exc_info:
        await auth_service.register(
            username="testuser",
            email="test@example.com",
            password="securepassword"
        )
    assert "username" in str(exc_info.value)

@pytest.mark.asyncio
async def test_register_duplicate_email(auth_service, mock_user_repo):
    mock_user_repo.exists = AsyncMock(side_effect=lambda username=None, email=None: email == "test@example.com")

    with pytest.raises(DuplicateEntityError) as exc_info:
        await auth_service.register(
            username="testuser",
            email="test@example.com",
            password="securepassword"
        )
    assert "email" in str(exc_info.value)

@pytest.mark.asyncio
async def test_login_success(auth_service, mock_user_repo, password_hasher):
    hashed = password_hasher.hash_password("securepassword")
    
    mock_user = MagicMock(spec=UserModel)
    mock_user.id = "user-id-123"
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.display_name = "testuser"
    mock_user.avatar_url = None
    mock_user.password_hash = hashed
    mock_user.is_active = True
    
    mock_user_repo.get_by_email = AsyncMock(return_value=mock_user)

    result = await auth_service.login("test@example.com", "securepassword")

    assert result["user"]["id"] == "user-id-123"
    assert "access_token" in result
    assert "refresh_token" in result

@pytest.mark.asyncio
async def test_login_wrong_password(auth_service, mock_user_repo, password_hasher):
    hashed = password_hasher.hash_password("securepassword")
    
    mock_user = MagicMock(spec=UserModel)
    mock_user.password_hash = hashed
    mock_user.is_active = True
    
    mock_user_repo.get_by_email = AsyncMock(return_value=mock_user)

    with pytest.raises(AuthenticationError):
        await auth_service.login("test@example.com", "wrongpassword")

@pytest.mark.asyncio
async def test_login_nonexistent_email(auth_service, mock_user_repo):
    mock_user_repo.get_by_email = AsyncMock(return_value=None)

    with pytest.raises(AuthenticationError):
        await auth_service.login("test@example.com", "securepassword")

@pytest.mark.asyncio
async def test_login_deactivated_account(auth_service, mock_user_repo, password_hasher):
    hashed = password_hasher.hash_password("securepassword")
    
    mock_user = MagicMock(spec=UserModel)
    mock_user.password_hash = hashed
    mock_user.is_active = False
    
    mock_user_repo.get_by_email = AsyncMock(return_value=mock_user)

    with pytest.raises(AuthenticationError):
        await auth_service.login("test@example.com", "securepassword")

@pytest.mark.asyncio
async def test_refresh_token_success(auth_service, jwt_handler, mock_cache_service):
    refresh_token = jwt_handler.create_refresh_token("user-123")
    mock_cache_service.get_session = AsyncMock(return_value=None) # Token not blacklisted

    result = await auth_service.refresh_token(refresh_token)
    assert "access_token" in result

@pytest.mark.asyncio
async def test_refresh_with_access_token(auth_service, jwt_handler, mock_cache_service):
    access_token = jwt_handler.create_access_token("user-123")
    mock_cache_service.get_session = AsyncMock(return_value=None)

    with pytest.raises(AuthenticationError) as exc_info:
        await auth_service.refresh_token(access_token)
    assert "not a refresh token" in str(exc_info.value)

@pytest.mark.asyncio
async def test_logout_blacklists_token(auth_service, mock_cache_service):
    await auth_service.logout("jti-123")
    mock_cache_service.store_session.assert_called_once()
    # Check that key starts with blacklist prefix
    args, kwargs = mock_cache_service.store_session.call_args
    assert "jti-123" in args[0]
