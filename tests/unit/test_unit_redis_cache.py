import pytest

from app.core.redis_cache import RedisCache  # Note: reloaded per-test when needed
from tests.helpers import FakeRedis


@pytest.mark.asyncio
async def test_redis_cache_connect_fallback(monkeypatch):
    cache = RedisCache("redis://invalid:6379/0")

    # Simulate redis.from_url raising exception
    class _R:
        @staticmethod
        def from_url(url):
            raise RuntimeError("connect fail")

    import app.core.redis_cache as rc

    monkeypatch.setattr(rc, "redis", _R)
    await cache.connect()
    # In fallback mode, redis is None
    assert cache.redis is None


@pytest.mark.asyncio
async def test_redis_cache_set_authors_page_exception(monkeypatch):
    cache = RedisCache("redis://test")
    fake = FakeRedis()
    fake.fail_set = True
    monkeypatch.setattr(cache, "redis", fake)

    # Should not raise despite set failing
    await cache.set_authors_page(1, 10, {"data": [], "meta": {}})


@pytest.mark.asyncio
async def test_redis_cache_get_miss_and_hit(monkeypatch):
    # Reload module to get an unpatched RedisCache class (bypasses autouse monkeypatch)
    import importlib

    import app.core.redis_cache as rc_mod

    rc_mod = importlib.reload(rc_mod)

    cache = rc_mod.RedisCache("redis://test")
    fake = FakeRedis()
    monkeypatch.setattr(cache, "redis", fake)

    # Miss
    val = await cache.get_books_page(1, 5)
    assert val is None

    # Hit: directly seed the fake store to avoid set() serialization differences
    key = "books:page:1:size:5"
    fake.store[key] = {"data": [1], "meta": {}}
    val = await cache.get_books_page(1, 5)
    assert val == {"data": [1], "meta": {}}
