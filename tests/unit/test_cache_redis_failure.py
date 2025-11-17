import pytest

from app.core.cache_service import RedisCacheService
from tests.helpers import FakeRedis


def test_redis_connect_failure(monkeypatch):
    """When redis client ping fails, connect should raise and leave _redis as None."""
    called = {}

    def fake_from_url(url, decode_responses=True):
        called["url"] = url
        return FakeRedis(fail_ping=True)

    monkeypatch.setattr("app.core.cache_service.redis.from_url", fake_from_url)

    svc = RedisCacheService(redis_url="redis://localhost:6379", ttl=1)

    with pytest.raises(Exception):
        # connect raises because ping failed
        import asyncio

        asyncio.get_event_loop().run_until_complete(svc.connect())

    # ensure _redis is cleared on failure
    assert svc._redis is None
