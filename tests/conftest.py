import asyncio
import logging
import os
import random
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
import sqlalchemy
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.keycloak_auth import KeycloakUser, get_current_user
from app.db.session import Base, get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.value_objects import AuthorCreateData
from app.main import app
from app.repositories.author_repository import AuthorRepository

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
        author_in = AuthorCreateData(first_name=first_name, last_name=last_name)
        author = await repo.get_by_full_name(first_name, last_name)
        if not author:
            async with uow:
                author = await repo.create(author_in)
        return author.id

    # If the override generator produced no session (shouldn't happen when
    # `client` fixture runs and sets the override), make the failure explicit
    # so linters and future readers don't assume an implicit `None` return.
    raise RuntimeError("test_author_id: could not obtain a DB session from override")


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
    """
    AsyncClient fixture that overrides the DB session dependency to use
    a test database schema, and provides a KeycloakUser mock for auth.
    """
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

    TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)

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

    from tests.helpers import DummyUser

    app.dependency_overrides[get_current_user] = lambda: DummyUser()
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
    from tests.helpers import DummyUser

    app.dependency_overrides[get_current_user] = lambda: DummyUser(username="admin")
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
            # Include realm_access.roles so KeycloakUser.is_admin returns True
            "realm_access": {"roles": ["admin"]},
        },
        None,
    )


@pytest.fixture
def override_keycloak(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_redis_client():
    """Reusable mock for the low-level redis client (AsyncIO client).

    Unit tests that exercise `redis.asyncio` client behavior can request
    this fixture. It mirrors the Async methods the code expects so tests
    can assert awaited calls.
    """
    mock = AsyncMock()
    mock.ping = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock()
    mock.delete = AsyncMock()
    mock.keys = AsyncMock(return_value=[])
    return mock


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

    TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_get_session():
        async with TestSessionLocal() as session:
            worker = os.getenv("PYTEST_XDIST_WORKER")
            if worker:
                try:
                    await session.execute(
                        text(f"SET search_path TO {settings.TEST_SCHEMA}")
                    )
                except Exception as e:
                    logging.getLogger(__name__).warning(
                        "Failed to set search_path: %s", e
                    )
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)
        await test_engine.dispose()


@pytest.fixture
def mock_keycloak_auth(monkeypatch):
    from app.core.keycloak_auth import keycloak_auth

    class MockKeycloakOpenID:
        def public_key(self):
            return "fake_public_key"

        def userinfo(self, token):
            return {"email": "test@example.com", "sub": "user123"}

    monkeypatch.setattr(keycloak_auth, "keycloak_openid", MockKeycloakOpenID())

    fake_token_info = {
        "preferred_username": "admin",
        "realm_access": {"roles": ["admin", "user"]},
        "email": "admin@example.com",
        "exp": 9999999999,
    }

    with patch("app.core.keycloak_auth.jwt.decode", return_value=fake_token_info):
        yield


@pytest.fixture
def override_author_service():
    """Fixture that overrides the `get_author_service` dependency with a
    lightweight fake implementation returning a small PaginatedResult.

    Use this in integration tests that only need the API layer exercised and
    don't want to rely on DB setup for authors.
    """
    from app.api.dependencies import get_author_service
    from app.domain.entities import AuthorEntity
    from app.domain.value_objects import PaginatedResult, PaginationMeta

    class FakeAuthorService:
        async def list_authors_by_page(self, page, size, search):
            author = AuthorEntity(id=1, first_name="Jane", last_name="Doe")
            meta = PaginationMeta(total=1, page=page, size=size, count=1)
            return PaginatedResult(data=[author], meta=meta)

    _prev = app.dependency_overrides.get(get_author_service)
    app.dependency_overrides[get_author_service] = lambda: FakeAuthorService()
    try:
        yield
    finally:
        if _prev is not None:
            app.dependency_overrides[get_author_service] = _prev
        else:
            app.dependency_overrides.pop(get_author_service, None)


@pytest.fixture
def mock_repo():
    """Project-wide mock repository fixture for unit tests.

    Many unit tests create a simple AsyncMock repository. Exposing a
    shared `mock_repo` fixture in `conftest.py` avoids duplication and keeps
    unit tests concise.
    """
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_uow():
    """Project-wide mock unit-of-work fixture for unit tests.

    Provides a MagicMock implementing async context manager methods so
    unit tests can `async with uow:` without touching a real DB.
    """
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=None)
    uow.__aexit__ = AsyncMock(return_value=None)
    return uow


# ========== Keycloak test helpers ==========


@pytest.fixture
def settings_stub(monkeypatch):
    from app.core import config

    monkeypatch.setattr(
        config.settings, "KEYCLOAK_SERVER_URL", "https://kc-test.example.com/"
    )
    monkeypatch.setattr(config.settings, "KEYCLOAK_REALM", "test-realm")
    monkeypatch.setattr(config.settings, "KEYCLOAK_CLIENT_ID", "test-client")
    monkeypatch.setattr(config.settings, "KEYCLOAK_CLIENT_SECRET", "secret")


@pytest.fixture
def keycloak_urls(settings_stub):
    """Return common Keycloak URLs built from current settings.

    Tests that need to mock multiple Keycloak endpoints can depend on this
    fixture. Note: if a test needs to override settings, include the
    `settings_stub` fixture (defined in the relevant test modules) so the
    URLs are constructed from the patched values.
    """
    from app.core import config

    base = config.settings.KEYCLOAK_SERVER_URL.rstrip("/")
    realm = config.settings.KEYCLOAK_REALM
    return {
        "token_url": f"{base}/realms/{realm}/protocol/openid-connect/token",
        "introspect_url": f"{base}/realms/{realm}/protocol/openid-connect/token/introspect",
        "userinfo_url": f"{base}/realms/{realm}/protocol/openid-connect/userinfo",
        "base_admin": f"{base}/admin/realms/{realm}/",
        "reset_password_url": f"{base}/admin/realms/{realm}/users/{{user_id}}/reset-password",
    }


@pytest.fixture
def mock_keycloak_token(respx_mock, keycloak_urls):
    """Register a default successful token endpoint using `respx_mock`.

    Depends on `settings_stub` to ensure test-specific settings are applied
    before the URL is computed. Returns a small dict with helpful values so
    tests can access `base_admin` or the payload if needed.
    """
    token_payload = {"access_token": "fake-token", "expires_in": 3600}
    respx_mock.post(keycloak_urls["token_url"]).respond(
        status_code=200, json=token_payload
    )
    return {
        "token_url": keycloak_urls["token_url"],
        "base_admin": keycloak_urls["base_admin"],
        "token_payload": token_payload,
    }
