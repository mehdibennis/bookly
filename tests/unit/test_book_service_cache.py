from unittest.mock import AsyncMock, MagicMock

import pytest
from tests.mocks.cache_service import MockCacheService

from app.db.session import get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.entities import BookEntity
from app.domain.value_objects import PaginationParams, PaginationMeta, PaginatedResult
from app.main import app
from app.repositories.book_repository import BookRepository
from app.services.book_service import BookService


@pytest.mark.asyncio
async def test_list_books_cache_hit(test_author_id):
    # Use the raw dependency override session generator
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)

        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        fake_cache = MagicMock()
        fake_cache.connect = AsyncMock(return_value=None)
        fake_cache.close = AsyncMock(return_value=None)
        
        # Create a cached PaginatedResult
        cached_book = BookEntity(
            id=999,
            title="Cached Book",
            authors=[test_author_id],
        )
        cached_result = PaginatedResult(
            data=[cached_book],
            meta=PaginationMeta(total=1, page=1, size=10, count=1),
        )
        fake_cache.get_books_page = AsyncMock(return_value=cached_result)
        fake_cache.set_books_page = AsyncMock()
        service.cache = fake_cache
        # Should hit the cache branch and return cached payload
        result = await service.list_books_by_page(page=1, size=10)
        # Result is now PaginatedResult[BookEntity]
        assert len(result.data) > 0
        assert result.data[0].title == "Cached Book"
        # set_books_page should not be called on cache hit
        fake_cache.set_books_page.assert_not_called()
        break
