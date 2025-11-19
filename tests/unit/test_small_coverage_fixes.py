from typing import cast

import pytest
from fastapi import HTTPException

from app.api.v1.routes import admin_users
from app.core.cache_service import RedisCacheService
from app.core.config import settings
from app.core.keycloak_auth import KeycloakUser
from tests.helpers import DummyUser


def test_require_realm_mgmt_without_roles_raises(monkeypatch):
    # Ensure no service account is configured
    monkeypatch.setattr(settings, "KEYCLOAK_CLIENT_SECRET", "")

    user = cast(KeycloakUser, DummyUser())

    with pytest.raises(HTTPException):
        # function is synchronous
        admin_users.require_realm_mgmt(user)


@pytest.mark.asyncio
async def test_redis_cache_methods_no_connection_do_not_raise(monkeypatch):
    # Create a RedisCacheService but do not call connect() so _redis stays None.
    # Ensure any attempt to create a real redis client is intercepted by
    # providing a fake `redis.asyncio` module in sys.modules that exposes
    # the `from_url` factory. This is robust across redis package versions.

    monkeypatch.setattr("redis.asyncio.from_url", lambda url, **kw: None)
    cache = RedisCacheService(redis_url="redis://127.0.0.1:6379/0", ttl=1)

    assert isinstance(cache, RedisCacheService)
    # Methods should return None or simply not raise when no connection exists
    assert await cache.get_books_page(1, 10) is None
    assert await cache.get_authors_page(1, 10) is None

    # Invalidate methods are no-op when not connected
    await cache.invalidate_books_cache()
    await cache.invalidate_authors_cache()
