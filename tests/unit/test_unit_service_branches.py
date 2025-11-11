from uuid import uuid4

import pytest

from app.db.session import get_session
from app.db.unit_of_work import SqlAlchemyUnitOfWork
from app.domain.entities import BookEntity
from app.domain.exceptions import ConflictException, NotFoundException
from app.domain.value_objects import BookCreateData, BookUpdateData
from app.main import app
from app.repositories.book_repository import BookRepository
from app.services.book_service import BookService
from tests.mocks.cache_service import MockCacheService


@pytest.mark.asyncio
async def test_list_books_pagination_edges(test_author_id):
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        # Seed a known batch large enough for at least 2 pages
        seed_count = 15
        for i in range(seed_count):
            await repo.create(
                BookEntity(
                    id=None, title=f"Seed {i} {uuid4()}", authors=[test_author_id]
                )
            )
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        page_size = 10
        page1 = await service.list_books_by_page(page=1, size=page_size)
        assert page1.meta.page == 1
        assert page1.meta.size == page_size
        assert page1.meta.count <= page_size
        assert page1.meta.previous_page is None
        # second page
        page2 = await service.list_books_by_page(page=2, size=page_size)
        assert page2.meta.page == 2
        # Count should be remaining items (could be page_size if previous data existed)
        remaining = page1.meta.total - page_size
        assert page2.meta.count == max(0, min(page_size, remaining))
        assert page2.meta.previous_page == 1
        # last_page calculation consistency
        expected_last = (
            (page1.meta.total - 1) // page_size + 1 if page1.meta.total > 0 else 1
        )
        assert page2.meta.last_page == expected_last


@pytest.mark.asyncio
async def test_create_book_success_and_conflict(test_author_id):
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        base_title = f"Conflict Seed {uuid4()}"
        created = await service.create_book(
            BookCreateData(title=base_title, authors=[test_author_id])
        )
        assert created.id is not None
        # Duplicate (case/space variation) should raise ConflictException
        with pytest.raises(ConflictException):
            await service.create_book(
                BookCreateData(title=base_title.upper(), authors=[test_author_id])
            )


@pytest.mark.asyncio
async def test_update_book_success_and_conflict(test_author_id):
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        t1 = f"Update Base {uuid4()}"
        t2 = f"Other Base {uuid4()}"
        b1 = await service.create_book(
            BookCreateData(title=t1, authors=[test_author_id])
        )
        # Create another book to cause a conflict when updating title to t2
        await service.create_book(BookCreateData(title=t2, authors=[test_author_id]))
        # Successful update: update title only (normalize case and trim)
        updated = await service.update_book(
            b1.id, BookUpdateData(title=f"  {t1.lower()}  ")
        )
        assert updated.title == t1.title()
        # Conflict update (set title to another existing book's title)
        with pytest.raises(ConflictException):
            await service.update_book(b1.id, BookUpdateData(title=t2))


@pytest.mark.asyncio
async def test_delete_book_success_and_not_found(test_author_id):
    async for session in app.dependency_overrides[get_session]():
        repo = BookRepository(session)
        uow = SqlAlchemyUnitOfWork(session)
        cache = MockCacheService()
        service = BookService(repo, uow, cache)
        title = f"Delete Me {uuid4()}"
        book = await service.create_book(
            BookCreateData(title=title, authors=[test_author_id])
        )
        ok = await service.delete_book(book.id)
        assert ok is True
        # Deleting again should raise NotFoundException
        with pytest.raises(NotFoundException):
            await service.delete_book(book.id)
