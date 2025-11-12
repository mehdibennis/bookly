from app.core.cache_service import RedisCacheService
from app.domain.entities import BookEntity


def test_book_entity_dict_roundtrip():
    svc = RedisCacheService(redis_url="redis://localhost:6379", ttl=1)
    be = BookEntity(
        id=10,
        title="My Book",
        authors=[1, 2],
        authors_details=[{"id": 1}],
        authors_number=2,
    )
    d = svc._book_entity_to_dict(be)
    assert d["id"] == 10
    be2 = svc._dict_to_book_entity(d)
    assert be2.title == "My Book"


def test_cache_methods_no_redis_return_none():
    svc = RedisCacheService(redis_url="redis://localhost:6379", ttl=1)
    import asyncio

    # _redis is None by default; these methods should return/exit gracefully
    assert (
        asyncio.get_event_loop().run_until_complete(svc.get_books_page(1, 10)) is None
    )
    assert (
        asyncio.get_event_loop().run_until_complete(svc.get_authors_page(1, 10)) is None
    )
    # search helpers
    assert (
        asyncio.get_event_loop().run_until_complete(
            svc.get_authors_page_search(1, 10, "x")
        )
        is None
    )
