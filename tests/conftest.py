import asyncio
import logging
import os
import random
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
import sqlalchemy
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.keycloak_auth import KeycloakUser, get_current_user
from app.core.redis_cache import RedisCache
from app.db.session import Base, get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.main import app
from app.repositories.author_repository import AuthorRepository
from app.schemas.author_schema import AuthorCreate

# ========== Pytest Fixtures ==========


@pytest_asyncio.fixture(scope="function")
async def test_author_id(client):
    """Create a test author and return its ID for use in book tests."""
    async for session in app.dependency_overrides[get_session]():
        repo = AuthorRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        # Use a random name to avoid conflicts
        first_name = f"Test{random.randint(1000, 9999)}"
        last_name = f"Author{random.randint(1000, 9999)}"
        author_in = AuthorCreate(first_name=first_name, last_name=last_name)
        author = await repo.get_by_full_name(first_name, last_name)
        if not author:
            async with uow:
                author = await repo.create(author_in)
        return author.id


# ========== Test Utilities ==========
def get_mock_token() -> str:
    """Get a mock token for testing."""
    return "mock_valid_token"


def get_auth_headers(token: str | None = None) -> dict:
    """Get authorization headers for API requests."""
    if token is None:
        token = get_mock_token()
    return {"Authorization": f"Bearer {token}"}


def get_rate_limit_headers(
    token: str | None = None, ip_suffix: int | None = None
) -> dict:
    """Get headers with rate limiting IP for testing."""
    if token is None:
        token = get_mock_token()
    if ip_suffix is None:
        ip_suffix = (uuid4().int % 250) + 2
    return {
        "Authorization": f"Bearer {token}",
        "X-Forwarded-For": f"198.51.100.{ip_suffix}",
    }


def get_unique_rate_headers(
    ip_range: str = "198.51.100", token: str | None = None
) -> dict:
    """Get headers with unique rate limiting IP for testing different ranges."""
    if token is None:
        token = get_mock_token()
    ip_suffix = (uuid4().int % 250) + 2
    return {
        "Authorization": f"Bearer {token}",
        "X-Forwarded-For": f"{ip_range}.{ip_suffix}",
    }


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def ensure_worker_schema_objects():
    """Create tables in the per-worker schema when running under xdist.

    Uses a synchronous engine with the worker's schema set as search_path
    to create all tables once per test session.
    """
    worker = os.getenv("PYTEST_XDIST_WORKER")
    if worker:
        sync_engine = sqlalchemy.create_engine(settings.SYNC_DATABASE_URL)
        with sync_engine.connect() as conn:
            schema = settings.TEST_SCHEMA
            conn.execute(sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            conn.execute(sqlalchemy.text(f"SET search_path TO {schema}"))
            Base.metadata.create_all(bind=conn)
            conn.commit()


@pytest_asyncio.fixture
async def client():
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
        isolation_level="AUTOCOMMIT",
    )
    # When running under xdist, ensure every new DB-API connection uses the worker schema
    if os.getenv("PYTEST_XDIST_WORKER"):

        @event.listens_for(test_engine.sync_engine, "connect")
        def _set_search_path(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute(f"SET search_path TO {settings.TEST_SCHEMA}")
            cursor.close()

    TestSessionLocal = sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_session():
        async with TestSessionLocal() as session:
            # If running under xdist, ensure this test session uses the per-worker schema
            worker = os.getenv("PYTEST_XDIST_WORKER")
            if worker:
                try:
                    await session.execute(
                        text(f"SET search_path TO {settings.TEST_SCHEMA}")
                    )
                except Exception:
                    # best-effort; tests should proceed even if we can't set search_path here
                    pass
            yield session

    # Temporarily override get_session, preserving any existing override
    _prev_get_session = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = override_get_session

    class _DummyUser:
        username = "test-user"
        email = "test@example.com"
        roles = ["user"]
        is_admin = False

    app.dependency_overrides[get_current_user] = lambda: _DummyUser()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac
    # Restore previous get_session override if any
    if _prev_get_session is not None:
        app.dependency_overrides[get_session] = _prev_get_session
    else:
        app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture(scope="function")
async def auth_for_class(request, client):
    from app.core.keycloak_auth import get_current_user

    class FakeUser:
        username = "admin"

    app.dependency_overrides[get_current_user] = lambda: FakeUser()
    if hasattr(request, "cls") and request.cls is not None:
        request.cls.auth_headers = {"Authorization": "Bearer faketoken"}
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_user():
    return KeycloakUser(
        {
            "sub": "12345",
            "preferred_username": "testuser",
            "email": "testuser@example.com",
        },
        None,
    )


@pytest_asyncio.fixture
def override_keycloak(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ========== Redis Mock & DB Cleanup ==========
@pytest.fixture(autouse=True)
def mock_redis_cache(monkeypatch):
    monkeypatch.setattr(RedisCache, "connect", AsyncMock())
    monkeypatch.setattr(RedisCache, "close", AsyncMock())
    monkeypatch.setattr(RedisCache, "get_books_page", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "set_books_page", AsyncMock())


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db():
    """
    Cleanup database after each test to ensure test isolation.

    This fixture creates a short-lived async engine and executes a
    TRUNCATE on the `books` table after each test. Using an independent
    engine avoids relying on `app.dependency_overrides` which some tests
    temporarily modify.
    """
    yield
    # Perform cleanup using a fresh engine to avoid dependency override races
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
    )
    # Ensure cleanup targets the correct worker schema
    if os.getenv("PYTEST_XDIST_WORKER"):

        @event.listens_for(engine.sync_engine, "connect")
        def _set_search_path(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute(f"SET search_path TO {settings.TEST_SCHEMA}")
            cursor.close()

    try:
        async with engine.begin() as conn:
            try:
                await conn.execute(
                    text("TRUNCATE TABLE books RESTART IDENTITY CASCADE")
                )
                await conn.execute(
                    text("TRUNCATE TABLE authors RESTART IDENTITY CASCADE")
                )
            except Exception as e:
                # Log but do not fail the test teardown
                logging.getLogger(__name__).warning("DB cleanup error: %s", e)
    finally:
        # Dispose the engine resources
        await engine.dispose()


# Provide a global override for get_session so tests that don't use the `client`
# fixture can still access a database session via app.dependency_overrides[get_session].
@pytest_asyncio.fixture(scope="session", autouse=True)
async def override_db_session_for_all_tests():
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
        isolation_level="AUTOCOMMIT",
    )

    if os.getenv("PYTEST_XDIST_WORKER"):

        @event.listens_for(test_engine.sync_engine, "connect")
        def _set_search_path(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute(f"SET search_path TO {settings.TEST_SCHEMA}")
            cursor.close()

    TestSessionLocal = sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_session():
        async with TestSessionLocal() as session:
            worker = os.getenv("PYTEST_XDIST_WORKER")
            if worker:
                try:
                    await session.execute(
                        text(f"SET search_path TO {settings.TEST_SCHEMA}")
                    )
                except Exception:
                    pass
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)
        await test_engine.dispose()
