import asyncio
import os
import sys
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.types import TypeDecorator, CHAR, JSON as SqliteJSON
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Check if we are running integration tests targeting PostgreSQL Docker
IS_INTEGRATION = os.getenv("INTEGRATION_TEST") == "1"

# ── Part 1: PostgreSQL Dialect Compatibility Patching for SQLite ──
if not IS_INTEGRATION:
    class SQLiteUUID(TypeDecorator):
        """Custom UUID mapper for SQLite in-memory database."""
        impl = CHAR(36)
        cache_ok = True

        def __init__(self, *args, **kwargs):
            super().__init__()

        def process_bind_param(self, value, dialect):
            if value is None:
                return None
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

        def process_result_value(self, value, dialect):
            if value is None:
                return None
            try:
                return uuid.UUID(value)
            except ValueError:
                return value

    # Patch UUID and JSON in PostgreSQL dialect module to compile under SQLite
    pg.UUID = SQLiteUUID
    pg.JSON = SqliteJSON

# ── Part 2: Mock Redis Client for Unit Tests ──
class MockRedis:
    def __init__(self):
        self.store = {}
        self.ttls = {}
        self.streams = {}
        self.pubsub_channels = {}

    async def ping(self):
        return True

    async def get(self, key):
        val = self.store.get(key)
        if isinstance(val, bytes):
            return val.decode("utf-8")
        return val

    async def set(self, key, value, ex=None, px=None, nx=False, xx=False):
        if nx and key in self.store:
            return False
        if xx and key not in self.store:
            return False
        self.store[key] = value
        return True

    async def delete(self, *keys):
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                count += 1
        return count

    async def exists(self, key):
        return key in self.store

    async def hset(self, name, key=None, value=None, mapping=None):
        if name not in self.store:
            self.store[name] = {}
        if mapping:
            for k, v in mapping.items():
                self.store[name][k] = str(v)
            return len(mapping)
        self.store[name][key] = str(value)
        return 1

    async def hget(self, name, key):
        val = self.store.get(name, {}).get(key)
        return val

    async def hgetall(self, name):
        return self.store.get(name, {})

    async def hdel(self, name, *keys):
        count = 0
        if name in self.store:
            for k in keys:
                if k in self.store[name]:
                    del self.store[name][k]
                    count += 1
        return count

    async def expire(self, key, time):
        if key in self.store:
            self.ttls[key] = time
            return True
        return False

    async def publish(self, channel, message):
        if channel in self.pubsub_channels:
            for cb in self.pubsub_channels[channel]:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(message))
                else:
                    cb(message)
        return 1

    async def xadd(self, name, fields, id="*", maxlen=None, approximate=True):
        if name not in self.streams:
            self.streams[name] = []
        entry_id = f"{len(self.streams[name]) + 1}-0"
        self.streams[name].append((entry_id, fields))
        return entry_id

    async def xrevrange(self, name, max="+", min="-", count=None):
        if name not in self.streams:
            return []
        items = list(self.streams[name])
        items.reverse()
        if count:
            items = items[:count]
        return items

    async def xreadgroup(self, groupname, consumername, streams, count=None, block=None, noack=False):
        return []

    async def xgroup_create(self, name, groupname, id="$", mkstream=False):
        return True

    async def xack(self, name, groupname, *ids):
        return len(ids)

    def pubsub(self):
        return MockPubSub(self)

class MockPubSub:
    def __init__(self, mock_redis):
        self.redis = mock_redis
        self.channels = []
        self.queue = asyncio.Queue()

    async def subscribe(self, *channels):
        for ch in channels:
            self.channels.append(ch)
            if ch not in self.redis.pubsub_channels:
                self.redis.pubsub_channels[ch] = []
            self.redis.pubsub_channels[ch].append(self.put_message)

    def put_message(self, data):
        self.queue.put_nowait(data)

    async def unsubscribe(self, *channels):
        for ch in channels:
            if ch in self.redis.pubsub_channels and self.put_message in self.redis.pubsub_channels[ch]:
                self.redis.pubsub_channels[ch].remove(self.put_message)

    async def get_message(self, ignore_subscribe_messages=False, timeout=1.0):
        try:
            data = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            return {"type": "message", "data": data}
        except asyncio.TimeoutError:
            return None

    async def aclose(self):
        pass

class MockRedisClient:
    _shared_client = MockRedis()

    def __init__(self, url=None, max_connections=None):
        self._client = MockRedisClient._shared_client

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def ping(self):
        return True

    @property
    def client(self):
        return self._client

    async def publish(self, channel, message):
        return await self._client.publish(channel, message)

    async def subscribe(self, channel):
        ps = self._client.pubsub()
        await ps.subscribe(channel)
        return ps

# Apply Redis Mocks globally for Unit Tests
if not IS_INTEGRATION:
    import src.infrastructure.redis.client as redis_client_module
    redis_client_module.RedisClient = MockRedisClient
    
    # Mock database init/close in lifespan
    import src.infrastructure.database.connection as db_conn_module
    db_conn_module.init_db = AsyncMock()
    db_conn_module.close_db = AsyncMock()

# Now import model metadata and dependencies
from src.infrastructure.database.models import MessageModel
from src.api.dependencies import get_db_session

# Remove GIN index that fails on SQLite during unit tests
if not IS_INTEGRATION:
    for index in list(MessageModel.__table__.indexes):
        if index.name == "ix_messages_content_fts":
            MessageModel.__table__.indexes.remove(index)

# ── Part 3: Pytest Async/Lifespan Fixtures ──

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
async def db_engine():
    if IS_INTEGRATION:
        from src.config import get_settings
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL)
        yield engine
        await engine.dispose()
    else:
        engine = create_async_engine("sqlite+aiosqlite://")
        yield engine
        await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    """Provide a database session wrapped in a transaction that rolls back after each test."""
    if IS_INTEGRATION:
        async_session_factory = async_sessionmaker(
            bind=db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_factory() as session:
            # Wrap in nested transaction
            async with session.begin():
                yield session
                await session.rollback()
    else:
        async with db_engine.connect() as conn:
            from src.infrastructure.database.connection import Base
            # Create schema dynamically for this test connection
            await conn.run_sync(Base.metadata.create_all)
            
            if conn.in_transaction():
                await conn.commit()
            
            # Start transaction
            trans = await conn.begin()
            session = AsyncSession(bind=conn, expire_on_commit=False)
            
            yield session
            
            await session.close()
            await trans.rollback()

@pytest.fixture
def override_db_session(db_session):
    """Injected FastAPI override for get_db_session."""
    async def _override():
        yield db_session
    return _override

@pytest.fixture
async def test_app(override_db_session):
    """FastAPI test app with database dependencies overridden."""
    from src.main import create_app
    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session
    
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        yield app

@pytest.fixture
async def http_client(test_app):
    """HTTP client bound to the test app for REST endpoint tests."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client

# ── Part 4: Factory Helpers for Generating Mock Entities ──
@pytest.fixture
def user_factory():
    def _create(username="testuser", email="test@example.com", password_hash="hash"):
        from src.infrastructure.database.models import UserModel
        return UserModel(
            id=uuid.uuid4(),
            username=username,
            email=email,
            password_hash=password_hash,
            status="offline",
            is_active=True
        )
    return _create

@pytest.fixture
def room_factory():
    def _create(name="Test Room", type="public", created_by=None):
        from src.infrastructure.database.models import RoomModel
        return RoomModel(
            id=uuid.uuid4(),
            name=name,
            type=type,
            created_by=created_by,
            max_members=500,
            is_active=True
        )
    return _create

@pytest.fixture
def message_factory():
    def _create(room_id, sender_id, content="hello world"):
        from src.infrastructure.database.models import MessageModel
        return MessageModel(
            room_id=room_id,
            sender_id=sender_id,
            content=content,
            message_type="text",
            is_edited=False,
            is_deleted=False
        )
    return _create
