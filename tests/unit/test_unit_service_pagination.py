from uuid import uuid4

import pytest
from tests.mocks.cache_service import MockCacheService

from app.db.session import get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.main import app
from app.repositories.book_repository import BookRepository
from app.services.book_service import BookService


@pytest.mark.asyncio
async def test_service_pagination_edges_previous_next_last_page(test_author_id):
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        # Create 3 books to ensure at least 2 pages with size=2
        titles = [f"PageBook {uuid4()}" for _ in range(3)]
        for t in titles:
            from app.domain.entities import BookEntity

            book_entity = BookEntity(id=None, title=t, authors=[test_author_id])
            await repo.create(book_entity)

        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        page1 = await service.list_books_by_page(page=1, size=2)
        assert page1.meta.page == 1
        assert page1.meta.size == 2
        last_page = page1.meta.last_page
        assert last_page >= 2
        assert page1.meta.next_page == 2
        assert page1.meta.previous_page is None

        page2 = await service.list_books_by_page(page=2, size=2)
        assert page2.meta.page == 2
        assert page2.meta.previous_page == 1

        # Jump to last page to cover next_page None branch
        last = await service.list_books_by_page(page=last_page, size=2)
        assert last.meta.next_page is None
