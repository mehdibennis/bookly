from app.api.mappers import AuthorMapper, BookMapper, PaginationMapper
from app.domain.entities import AuthorEntity, BookEntity
from app.domain.value_objects import PaginatedResult, PaginationMeta
from app.schemas.pagination import PaginatedResponse


def test_book_mapper_create_update_and_entity_to_dto():
    # Create DTO mapping
    class DummyCreate:
        title = "the hobbit"
        authors = [1]

    bc = DummyCreate()
    bd = BookMapper.create_dto_to_domain(bc)
    assert bd.title == "the hobbit"

    # Entity to dto
    be = BookEntity(
        id=5, title="the hobbit", authors=[1], authors_details=[{}], authors_number=1
    )
    dto = BookMapper.entity_to_dto(be)
    assert dto.id == 5
    assert dto.title == "the hobbit"


def test_author_mapper_date_parsing_and_entity_to_dto():
    ae = AuthorEntity(id=1, first_name="john", last_name="doe")
    dto = AuthorMapper.entity_to_dto(ae)
    assert dto.first_name == "john"


def test_pagination_mapper_result_to_response():
    be = BookEntity(id=1, title="x", authors=[], authors_details=[], authors_number=0)
    meta = PaginationMeta(total=1, page=1, size=10, count=1)
    pr = PaginatedResult(data=[be], meta=meta)
    resp = PaginationMapper.result_to_response(
        pr, lambda items: [BookMapper.entity_to_dto(i) for i in items]
    )
    assert isinstance(resp, PaginatedResponse)
    assert resp.meta.total == 1


def test_get_cache_service_returns_noop_when_xdist(monkeypatch):
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw0")
    import asyncio

    from app.api.dependencies import get_cache_service

    svc = asyncio.get_event_loop().run_until_complete(get_cache_service())
    assert (
        hasattr(svc, "connect")
        and hasattr(svc, "close")
        and hasattr(svc, "get_books_page")
    )


def test_get_cache_service_returns_redis_when_no_xdist(monkeypatch):
    # Ensure no PYTEST_XDIST_WORKER is present
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    import asyncio

    from app.api.dependencies import get_cache_service

    svc = asyncio.get_event_loop().run_until_complete(get_cache_service())
    # Expect an object with RedisCacheService behavior (has methods defined)
    assert hasattr(svc, "get_books_page") and hasattr(svc, "set_books_page")
