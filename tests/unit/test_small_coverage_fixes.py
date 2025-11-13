import pytest
from fastapi import HTTPException

from app.api.v1.routes import admin_users
from app.core.cache_service import RedisCacheService
from app.core.config import settings


from tests.helpers import DummyUser


def test_require_realm_mgmt_without_roles_raises(monkeypatch):
    # Ensure no service account is configured
    monkeypatch.setattr(settings, "KEYCLOAK_CLIENT_SECRET", "")

    user = DummyUser()

    with pytest.raises(HTTPException):
        # function is synchronous
        admin_users.require_realm_mgmt(user)


@pytest.mark.asyncio
async def test_redis_cache_methods_no_connection_do_not_raise():
    # Create a RedisCacheService but do not call connect() so _redis stays None.
    cache = RedisCacheService(redis_url="redis://127.0.0.1:6379/0", ttl=1)

    # Methods should return None or simply not raise when no connection exists
    assert await cache.get_books_page(1, 10) is None
    assert await cache.get_authors_page(1, 10) is None

    # Invalidate methods are no-op when not connected
    await cache.invalidate_books_cache()
    await cache.invalidate_authors_cache()
